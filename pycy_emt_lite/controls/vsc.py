"""三端示例使用的跟网型两电平 VSC 控制；电气网络仍由现有元件求解。

电流以 AC -> converter 为正，P 同向；Q>0 表示从 AC 吸收感性无功。
本模块使用幅值不变、d 对齐电压的 Park 变换，所有电气量采用 SI 单位。
"""

from collections.abc import Mapping
from dataclasses import dataclass
import math

from pycy_emt_lite.controls.blocks import PIController, FirstOrderLowPass, _finite_real
from pycy_emt_lite.controls.pll import SRFPLL
from pycy_emt_lite.controls.pwm import carrier_compare, triangular_carrier
from pycy_emt_lite.controls.transforms import abc_to_alpha_beta, abc_to_dq, dq_to_abc


@dataclass(frozen=True, slots=True)
class VSCControlConfig:
    """示例共用增益与限制；不是原 Simulink 控制参数的直接换算。"""

    dc_voltage: float = 400e3
    reactor_inductance: float = 72.4e-3
    current_kp: float = 60.0  # V/A
    current_ki: float = 6000.0  # V/(A s)
    dc_kp: float = 0.05  # A/V
    dc_ki: float = 1.1  # A/(V s)
    ac_kp: float = 10000.0  # A/pu
    ac_ki: float = 400000.0  # A/(pu s)
    pll_kp: float = 80.0
    pll_ki: float = 1000.0
    current_limit: float = 1500.0  # dq vector magnitude / A
    modulation_limit: float = 0.98
    measurement_tau: float = 1e-3
    current_measurement_tau: float = 0.2e-3
    ramp_start: float = 0.02
    ramp_duration: float = 0.10

    def __post_init__(self) -> None:
        for name in self.__dataclass_fields__:
            _finite_real(getattr(self, name), f"VSCControlConfig.{name}", positive=name != "ramp_start")
        if self.ramp_start < 0 or self.modulation_limit > 1:
            raise ValueError("ramp_start 必须非负，modulation_limit 必须在 (0, 1] 内。")


class VSCController:
    """每站独立 PLL、Vdc/P 外环、Vac 外环、电流 PI 与 SPWM。

    `sample(row)` 在网络求解后调用；门极 callable 只读取已保持的调制量，
    不在 stamp 或重复的事件一致求解中推进控制器。
    name 同时是示例的站节点/元件前缀，例如 S1，命名映射见示例文档。
    """

    def __init__(self, name: str, frequency: float, grid_voltage: float,
                 converter_voltage: float, active_power: float | None,
                 switching_frequency: float, config: VSCControlConfig | None = None) -> None:
        self.name = name
        self.config = config or VSCControlConfig()
        self.frequency = _finite_real(frequency, "VSCController.frequency", positive=True)
        self.grid_voltage = _finite_real(grid_voltage, "VSCController.grid_voltage", positive=True)
        self.converter_voltage = _finite_real(converter_voltage, "VSCController.converter_voltage", positive=True)
        self.active_power = None if active_power is None else _finite_real(active_power, "VSCController.active_power")
        self.switching_frequency = _finite_real(switching_frequency, "VSCController.switching_frequency", positive=True)
        cfg = self.config
        omega = 2 * math.pi * self.frequency
        self.pll = SRFPLL(cfg.pll_kp, cfg.pll_ki, omega, -math.pi / 2,
                          omega - 2 * math.pi * 10, omega + 2 * math.pi * 10)
        self.dc_pi = PIController(cfg.dc_kp, cfg.dc_ki, -cfg.current_limit, cfg.current_limit)
        self.ac_pi = PIController(cfg.ac_kp, cfg.ac_ki, -cfg.current_limit, cfg.current_limit)
        voltage_limit = cfg.dc_voltage / 2
        self.d_pi = PIController(cfg.current_kp, cfg.current_ki, -voltage_limit, voltage_limit)
        self.q_pi = PIController(cfg.current_kp, cfg.current_ki, -voltage_limit, voltage_limit)
        self.vac_filter = FirstOrderLowPass(cfg.measurement_tau, 1.0)
        self.vdc_filter = FirstOrderLowPass(cfg.measurement_tau, cfg.dc_voltage)
        self.voltage_filters = (FirstOrderLowPass(cfg.measurement_tau), FirstOrderLowPass(cfg.measurement_tau))
        self.current_filters = (FirstOrderLowPass(cfg.current_measurement_tau), FirstOrderLowPass(cfg.current_measurement_tau))
        self.last_time: float | None = None
        self.modulation = (0.0, 0.0, 0.0)

    def gate(self, phase: int, upper: bool = True):
        """无死区互补门极；载波按 EMT 网格采样，不定位连续时间交点。"""

        def closed(time: float) -> bool:
            top = bool(carrier_compare(self.modulation[phase], triangular_carrier(time, self.switching_frequency)))
            return top if upper else not top

        return closed

    def sample(self, row: Mapping[str, float]) -> dict[str, float]:
        """读取同刻测量，生成下一步使用的调制；t=0 只初始化。"""

        name, cfg = self.name, self.config
        time = row["time"]
        dt = 0.0 if self.last_time is None else time - self.last_time
        if (self.last_time is None and time != 0) or (self.last_time is not None and dt <= 0):
            raise ValueError("VSCController 须从 t=0 开始，每个递增求解时刻只采样一次。")
        hv = tuple(row[f"v:{name}:hv:{p}"] for p in "abc")
        lv = tuple(row[f"v:{name}:lv:{p}"] for p in "abc")
        current = tuple(row[f"i:{name}:reactor:{p}"] for p in "abc")
        vdc = row[f"v:{name}:dc_p"] - row[f"v:{name}:dc_n"]
        alpha, beta = abc_to_alpha_beta(*hv)
        vac = math.hypot(alpha, beta) / (math.sqrt(2 / 3) * self.grid_voltage)
        if self.last_time is None:
            if vac > 0.2:
                self.pll.reset(math.atan2(beta, alpha))
            self.vac_filter.reset(vac)
            self.vdc_filter.reset(vdc)
        else:
            self.pll.step(hv, dt)
            self.vac_filter.step(vac, dt)
            self.vdc_filter.step(vdc, dt)
        theta = self.pll.angle
        vd, vq = abc_to_dq(*lv, theta)
        id_meas, iq_meas = abc_to_dq(*current, theta)
        for filters, values in ((self.voltage_filters, (vd, vq)), (self.current_filters, (id_meas, iq_meas))):
            for filt, value in zip(filters, values):
                if dt == 0:
                    filt.reset(value)
                else:
                    filt.step(value, dt)
        vd_control, vq_control = (f.state for f in self.voltage_filters)
        id_control, iq_control = (f.state for f in self.current_filters)
        pll_vd, pll_vq = abc_to_dq(*hv, theta)
        # P 的测量面在 reactor 的交流端；它与桥 AC 端功率之差是 reactor 储能变化。
        pac = sum(v * i for v, i in zip(lv, current))
        qac = 1.5 * (vq * id_meas - vd * iq_meas)
        ramp = min(max((time - cfg.ramp_start) / cfg.ramp_duration, 0.0), 1.0)
        pref = 0.0 if self.active_power is None else self.active_power * ramp
        id_ref, iq_ref = 0.0, 0.0
        if dt > 0:
            if self.active_power is None:
                id_ref = self.dc_pi.step(cfg.dc_voltage - self.vdc_filter.state, dt)
            else:
                # Reference 的恒 P 算法：P*/(1.5 Vd)，电压下限仅防除零；随后限流。
                id_ref = pref / (1.5 * max(vd_control, 0.2 * math.sqrt(2 / 3) * self.converter_voltage))
            previous_ac_integrator = self.ac_pi.integrator
            iq_ref = self.ac_pi.step(1.0 - self.vac_filter.state, dt)
        id_ref = min(max(id_ref, -cfg.current_limit), cfg.current_limit)
        q_limit = math.sqrt(max(cfg.current_limit**2 - id_ref**2, 0.0))
        limited_iq_ref = min(max(iq_ref, -q_limit), q_limit)
        if dt > 0 and limited_iq_ref != iq_ref:
            self.ac_pi.integrator = previous_ac_integrator
        iq_ref = limited_iq_ref
        # i 正向 AC -> converter：L did/dt = vg_d - vc_d + omega L iq，
        # L diq/dt = vg_q - vc_q - omega L id。PI 输出从 vg 中减去。
        previous_integrators = self.d_pi.integrator, self.q_pi.integrator
        ud = self.d_pi.step(id_ref - id_control, dt) if dt > 0 else 0.0
        uq = self.q_pi.step(iq_ref - iq_control, dt) if dt > 0 else 0.0
        vcd = vd_control + self.pll.frequency * cfg.reactor_inductance * iq_control - ud
        vcq = vq_control - self.pll.frequency * cfg.reactor_inductance * id_control - uq
        # 用当前真实 Vdc 归一化并按 dq 矢量限幅，避免逐相削顶改变电压角度。
        available = cfg.modulation_limit * max(vdc, 0.1 * cfg.dc_voltage) / 2
        scale = min(1.0, available / max(math.hypot(vcd, vcq), 1.0))
        if scale < 1:
            # 最终电压饱和时也冻结电流积分；现有 PI 本身只知道自身输出限制。
            self.d_pi.integrator, self.q_pi.integrator = previous_integrators
        next_modulation = tuple(2 * v * scale / max(vdc, 0.1 * cfg.dc_voltage)
                                for v in dq_to_abc(vcd, vcq, theta))
        traces = {
            "Vdc": vdc, "Vac_pu": vac, "P": pac, "Q": qac, "P_ref": pref,
            "Id": id_meas, "Iq": iq_meas, "Id_ref": id_ref, "Iq_ref": iq_ref,
            "PLL_theta": theta, "PLL_frequency_Hz": self.pll.frequency / (2 * math.pi),
            "PLL_Vq": pll_vq, "PLL_Vq_pu": pll_vq / max(abs(pll_vd), 1.0),
            "carrier": triangular_carrier(time, self.switching_frequency),
            "modulation_magnitude": math.sqrt(sum(m*m for m in self.modulation) * 2/3),
            # m 是刚完成求解所用参考，m_next 是本次控制生成的下一步参考。
            **{f"m{p}": self.modulation[k] for k, p in enumerate("abc")},
            **{f"m{p}_next": next_modulation[k] for k, p in enumerate("abc")},
        }
        self.modulation = next_modulation
        self.last_time = time
        return {f"{name}:{key}": value for key, value in traces.items()}
