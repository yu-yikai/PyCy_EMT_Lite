"""三端两电平 VSC-HVDC 综合算例，参考 DIgSILENT 发布的 Simulink Benchmark。

先读 docs/three_terminal_vsc_hvdc.md：此例保留核心电路与控制职责，
理想双向开关、控制增益、初始化与采样方式有明确差异，不是商业模型的精确复现。
默认 FAST；修改 MODE 选择 FULL 或 BENCHMARK。默认只显示，不保存。
"""

from collections.abc import Mapping
from dataclasses import dataclass
import math
from time import perf_counter

import numpy as np

from pycy_emt_lite import (Capacitor, Fault, FaultApplyEvent, FaultClearEvent,
                         IdealSwitch, Inductor, Resistor, SimulationConfig,
                         ThreePhaseSource)
from pycy_emt_lite.cases import CaseDefinition, OutputOptions, PlotSpec, run_case
from pycy_emt_lite.components.three_phase import ThreePhaseLine
from pycy_emt_lite.components.transformers import ThreePhaseTransformer
from pycy_emt_lite.controls.vsc import VSCControlConfig, VSCController

SAVE_RESULT_DATA = 0
SAVE_RESULT_FIGURE = 0
SHOW_FIGURE = True
MODE = "BENCHMARK"  # FAST, FULL, BENCHMARK

# 来自本地 SLX + 参数脚本。容量为换流变铭牌，不能当作本例已验证的输送功率。
RATED_POWER = 1500e6
CONVERTER_VOLTAGE = 230e3  # line-line RMS / V
GRID_RESISTANCE = 4.59  # ohm / phase, HV side
GRID_REACTANCE = 26.04  # ohm at each grid's nominal frequency
TRANSFORMER_REACTANCE_PU = 0.10  # 两绕组各 0.05 pu 合计；一次侧折算
NEUTRAL_RESISTANCE = 1e6
POLE_CAPACITANCE = 300e-6  # 每极对地；两极串联等效 150 uF
LINE_HALF_R = 7.0
LINE_HALF_L = 0.596
LINE_MID_C = 26e-6
SWITCH_RON = 0.005
SWITCH_GOFF = 1e-6
FILTER_Q_VAR = 75e6
FILTER_TUNING_HZ = 450.0
FILTER_QUALITY = 0.08
FAULT_RESISTANCE = 5.0
FAULT_SNUBBER_RESISTANCE = 1e6  # SLX Fault 的电阻缓冲支路；清除后保留有限电流通路
# PyCy-adjusted：故障母线的有限 RC 缓冲，避免原纯电阻支路在电流连续清除时产生 GV 峰值。
# 保留原 1 Mohm 支路；这组 RC 不是 Reference 参数，不用于预测设备开断过电压。
FAULT_SNUBBER_R = 200.0
FAULT_SNUBBER_C = 0.5e-6
STATIONS = (("S1", 60.0, 420e3, None), ("S2", 50.0, 420e3, 200e6),
            ("S3", 50.0, 500e3, -200e6))


@dataclass(frozen=True, slots=True)
class RunMode:
    time_step: float
    stop_time: float
    fault_on: float
    fault_off: float
    switching_frequency: float
    record_every: int


MODES = {
    "FAST": RunMode(20e-6, 0.8, 0.3, 0.45, 1000.0, 1),
    "FULL": RunMode(5e-6, 2.5, 1.5, 1.65, 1980.0, 10),
    "BENCHMARK": RunMode(2e-6, 2.5, 1.5, 1.65, 1980.0, 25),
}


def station_components(control: VSCController) -> tuple:
    """一个站的源、阻抗、换流变、高通滤波器、电抗器和六开关桥。"""

    s, cfg = control.name, control.config
    omega = 2 * math.pi * control.frequency
    ratio = control.grid_voltage / CONVERTER_VOLTAGE
    components = [
        ThreePhaseSource(f"{s}:grid", f"{s}:source", control.grid_voltage / math.sqrt(3), control.frequency),
        ThreePhaseLine(f"{s}:grid_Z", f"{s}:source", f"{s}:hv", GRID_RESISTANCE, GRID_REACTANCE / omega),
        ThreePhaseTransformer(f"{s}:transformer", f"{s}:hv", f"{s}:lv", ratio,
                              secondary_neutral=f"{s}:neutral",
                              leakage_inductance=TRANSFORMER_REACTANCE_PU * control.grid_voltage**2 / RATED_POWER / omega),
        Resistor(f"{s}:neutral_R", f"{s}:neutral", "0", NEUTRAL_RESISTANCE),
        ThreePhaseLine(f"{s}:reactor", f"{s}:lv", f"{s}:bridge", 0.0, cfg.reactor_inductance),
        Capacitor(f"{s}:Cdc_p", f"{s}:dc_p", "0", POLE_CAPACITANCE, cfg.dc_voltage / 2),
        Capacitor(f"{s}:Cdc_n", "0", f"{s}:dc_n", POLE_CAPACITANCE, cfg.dc_voltage / 2),
    ]
    # 二阶高通：C 串联 (L || R)，每相接地。参数由 SLX 的 Qc/fr/q 换算。
    capacitance = FILTER_Q_VAR * (1 - (control.frequency / FILTER_TUNING_HZ)**2) / (omega * CONVERTER_VOLTAGE**2)
    inductance = 1 / ((2 * math.pi * FILTER_TUNING_HZ)**2 * capacitance)
    resistance = FILTER_QUALITY * math.sqrt(inductance / capacitance)
    for k, phase in enumerate("abc"):
        components.extend((
            Resistor(f"{s}:fault_snubber:{phase}", f"{s}:hv:{phase}", "0", FAULT_SNUBBER_RESISTANCE),
            IdealSwitch(f"{s}:{phase}_top", f"{s}:dc_p", f"{s}:bridge:{phase}",
                        control.gate(k), SWITCH_RON, SWITCH_GOFF),
            IdealSwitch(f"{s}:{phase}_bottom", f"{s}:bridge:{phase}", f"{s}:dc_n",
                        control.gate(k, False), SWITCH_RON, SWITCH_GOFF),
            Capacitor(f"{s}:filter_C:{phase}", f"{s}:lv:{phase}", f"{s}:filter:{phase}", capacitance,
                      math.sqrt(2 / 3) * CONVERTER_VOLTAGE * math.sin(-k * 2 * math.pi / 3)),
            Inductor(f"{s}:filter_L:{phase}", f"{s}:filter:{phase}", "0", inductance),
            Resistor(f"{s}:filter_R:{phase}", f"{s}:filter:{phase}", "0", resistance),
        ))
    return tuple(components)


def dc_link_components(first: str, second: str, dc_voltage: float) -> tuple:
    """双极 T 型线路，每极 R-L / 接地 C / R-L；支路正向 first -> second。"""

    components = []
    for pole, sign in (("p", 1), ("n", -1)):
        stem = f"{first}_{second}:{pole}"
        for side, begin, end in (("from", f"{first}:dc_{pole}", f"{stem}:mid"),
                                 ("to", f"{stem}:mid", f"{second}:dc_{pole}")):
            components.extend((Resistor(f"{stem}:R_{side}", begin, f"{stem}:r_{side}", LINE_HALF_R),
                               Inductor(f"{stem}:L_{side}", f"{stem}:r_{side}", end, LINE_HALF_L)))
        components.append(Capacitor(f"{stem}:C", f"{stem}:mid", "0", LINE_MID_C, sign * dc_voltage / 2))
    return tuple(components)


class HVDCControl:
    """统一步后回调，合并三站测量及 DC 网络功率/储能账。"""

    def __init__(self, controllers: tuple[VSCController, ...], links: tuple[tuple[str, str], ...]):
        self.controllers, self.links = controllers, links

    def __call__(self, row: Mapping[str, float]) -> dict[str, float]:
        extra = {}
        energy, loss, dc_in, cap_power = 0.0, 0.0, 0.0, 0.0
        for control in self.controllers:
            s = control.name
            extra.update(control.sample(row))
            vp, vn = row[f"v:{s}:dc_p"], row[f"v:{s}:dc_n"]
            # 上管正向 DC+ -> AC，下管正向 AC -> DC-。
            pdc = -vp * sum(row[f"i:{s}:{p}_top"] for p in "abc") + vn * sum(row[f"i:{s}:{p}_bottom"] for p in "abc")
            extra[f"{s}:Pdc"] = pdc  # converter -> DC network
            dc_in += pdc
            e = 0.5 * POLE_CAPACITANCE * (vp**2 + vn**2)
            extra[f"{s}:Edc"] = e
            energy += e
            cap_power += vp * row[f"i:{s}:Cdc_p"] - vn * row[f"i:{s}:Cdc_n"]
        inductor_power = 0.0
        for first, second in self.links:
            for pole in ("p", "n"):
                stem = f"{first}_{second}:{pole}"
                for side in ("from", "to"):
                    current = row[f"i:{stem}:L_{side}"]
                    loss += LINE_HALF_R * current**2
                    energy += 0.5 * LINE_HALF_L * current**2
                    inductor_power += row[f"v:{stem}:L_{side}"] * current
                voltage = row[f"v:{stem}:mid"]
                energy += 0.5 * LINE_MID_C * voltage**2
                cap_power += voltage * row[f"i:{stem}:C"]
        extra.update({"DC:energy": energy, "DC:loss": loss, "DC:power_in": dc_in,
                      "DC:storage_power": cap_power + inductor_power,
                      "DC:balance_residual": dc_in - loss - cap_power - inductor_power})
        return extra


def validation_summary(result, mode: RunMode) -> dict[str, float]:
    """按固定物理窗口核对稳态与恢复；原始信号先转数组，避免反复遍历大结果。"""

    columns = list(result.rows[0])
    data = np.array([[row[c] for c in columns] for row in result.rows])
    a = {c: data[:, k] for k, c in enumerate(columns)}
    metrics = {"all_finite": float(np.isfinite(data).all()),
               "dc_balance_residual_W": float(np.max(np.abs(a["DC:balance_residual"])))}
    for label, start, end in (("pre", mode.fault_on - 0.12, mode.fault_on - 0.02),
                              ("post", mode.stop_time - 0.1, mode.stop_time)):
        window = (a["time"] >= start) & (a["time"] <= end)
        t = a["time"][window]
        if len(t) < 2:
            raise ValueError("仿真结果未覆盖要求的稳态/恢复窗口。")
        def mean(key):
            return float(np.trapezoid(a[key][window], t) / (t[-1] - t[0]))
        for s, frequency, _, _ in STATIONS:
            metrics[f"{label}:{s}:Vdc_kV"] = mean(f"{s}:Vdc") / 1e3
            metrics[f"{label}:{s}:P_MW"] = mean(f"{s}:P") / 1e6
            metrics[f"{label}:{s}:Q_Mvar"] = mean(f"{s}:Q") / 1e6
            metrics[f"{label}:{s}:Vac_pu"] = mean(f"{s}:Vac_pu")
            metrics[f"{label}:{s}:PLL_error_Hz"] = abs(mean(f"{s}:PLL_frequency_Hz") - frequency)
            metrics[f"{label}:{s}:PLL_Vq_pu"] = abs(mean(f"{s}:PLL_Vq_pu"))
            for axis in ("Id", "Iq"):
                metrics[f"{label}:{s}:{axis}_mean_error_A"] = abs(mean(f"{s}:{axis}") - mean(f"{s}:{axis}_ref"))
        metrics[f"{label}:DC:power_in_MW"] = mean("DC:power_in") / 1e6
        metrics[f"{label}:DC:loss_MW"] = mean("DC:loss") / 1e6
        metrics[f"{label}:DC:storage_power_MW"] = mean("DC:storage_power") / 1e6
    fault = (a["time"] >= mode.fault_on + 0.02) & (a["time"] <= mode.fault_off - 0.02)
    metrics["fault:S3:Vac_pu_mean"] = float(np.mean(a["S3:Vac_pu"][fault]))
    metrics["Vdc_min_kV"] = min(float(a[f"{s}:Vdc"].min()) / 1e3 for s, *_ in STATIONS)
    metrics["Vdc_max_kV"] = max(float(a[f"{s}:Vdc"].max()) / 1e3 for s, *_ in STATIONS)
    return metrics


def define_case(mode: str = MODE, *, fault: bool = True) -> CaseDefinition:
    """创建新实例；每次运行的元件与控制器都独立。"""

    settings = MODES[mode]
    control_config = VSCControlConfig()
    controllers = tuple(VSCController(s, f, hv, CONVERTER_VOLTAGE, power,
                                      settings.switching_frequency, control_config) for s, f, hv, power in STATIONS)
    links = (("S1", "S2"), ("S1", "S3"))
    components = [component for control in controllers for component in station_components(control)]
    for first, second in links:
        components.extend(dc_link_components(first, second, control_config.dc_voltage))
    events = []
    for phase in "abc":
        name = f"S3:fault:{phase}"
        components.append(Fault(name, f"S3:hv:{phase}", FAULT_RESISTANCE))
        components.extend((
            Resistor(f"S3:snubber_R:{phase}", f"S3:hv:{phase}", f"S3:snubber:{phase}", FAULT_SNUBBER_R),
            Capacitor(f"S3:snubber_C:{phase}", f"S3:snubber:{phase}", "0", FAULT_SNUBBER_C,
                      math.sqrt(2/3) * STATIONS[2][2] * math.sin(-"abc".index(phase) * 2*math.pi/3)),
        ))
        if fault:
            events.extend((FaultApplyEvent(settings.fault_on, name), FaultClearEvent(settings.fault_off, name)))
    plots = []
    for key, title in (("Vdc", "DC voltages / V"), ("P", "AC to converter active power / W"),
                       ("Q", "Absorbed reactive power / var"), ("Vac_pu", "PCC voltage magnitude / pu"),
                       ("PLL_frequency_Hz", "Independent PLL frequencies / Hz")):
        plots.append(PlotSpec(tuple(f"{s}:{key}" for s, *_ in STATIONS), f"{key}.png", title=title))
    for s, *_ in STATIONS:
        for axis in ("Id", "Iq"):
            plots.append(PlotSpec((f"{s}:{axis}", f"{s}:{axis}_ref"), f"{s}_{axis}.png", title=f"{s} {axis} tracking / A"))
    plots.extend((PlotSpec(tuple(f"v:S3:hv:{p}" for p in "abc"), "fault_voltage.png", title="S3 HV voltage / V"),
                  PlotSpec(tuple(f"i:S3:reactor:{p}" for p in "abc"), "fault_current.png", title="S3 phase current / A"),
                  PlotSpec(("i:S1_S2:p:L_from", "i:S1_S3:p:L_from"), "dc_current.png", title="Positive pole line currents, S1 to S2/S3 / A")))
    config = SimulationConfig(settings.time_step, settings.stop_time, method="backward_euler",
                              event_time_policy="require_aligned", record_every=settings.record_every)
    def summary(result):
        for key, value in validation_summary(result, settings).items():
            print(f"{key}: {value:.6g}")
    return CaseDefinition("three_terminal_vsc_hvdc_" + mode.lower(), tuple(components), config,
                          tuple(events), tuple(plots),
                          OutputOptions(bool(SAVE_RESULT_DATA), bool(SAVE_RESULT_FIGURE), SHOW_FIGURE),
                          summary=summary, on_step=HVDCControl(controllers, links))


def main() -> None:
    case = define_case()
    start = perf_counter()
    result = run_case(case)
    elapsed = perf_counter() - start
    print(f"{MODE}: simulation + reporting {elapsed:.2f} s; result samples {len(result.rows)}")
    # 门极与载波只展示一个短窗口；保存跟随统一开关。
    from pycy_emt_lite.visualization import plot_zoom_window
    output_dir = case.output.output_root / case.name
    plot_zoom_window(result, ("S1:ma", "S1:carrier", "state:S1:a_top", "state:S1:a_bottom"),
                     0.2, 0.203, output_path=output_dir / "pwm_zoom.png" if case.output.save_figure else None,
                     show=case.output.show_figure)


if __name__ == "__main__":
    main()
