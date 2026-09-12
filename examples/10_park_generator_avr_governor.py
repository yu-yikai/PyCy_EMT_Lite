"""四阶 Park dq 同步发电机从平衡运行点响应三相负荷阶跃。

忽略定子快速暂态，电流为代数量；观察励磁和调速过程，不用于短路冲击电流。
机电/控制状态用显式欧拉；网络仍通过 CaseDefinition -> Simulator 求解。
电压采用相电压 RMS 基准，功率采用三相总容量基准。"""

import math
from numbers import Real

import numpy as np

from pycy_emt_lite import (
    Breaker,
    BreakerCloseEvent,
    Resistor,
    SimulationConfig,
)
from pycy_emt_lite.cases import CaseDefinition, OutputOptions, PlotSpec, run_case
from pycy_emt_lite.io.results import SimulationResult
from pycy_emt_lite.machines import ParkSynchronousGenerator

SAVE_RESULT_DATA = 0
SAVE_RESULT_FIGURE = 0
SHOW_FIGURE = True

LOAD_STEP_TIME = 0.2
TIME_STEP = 1e-4
STOP_TIME = 0.6
BASE_POWER = 3000.0      # VA，三相总容量
BASE_PHASE_RMS = 100.0  # V，相电压有效值
FREQUENCY = 50.0        # Hz
BASE_LOAD = 30.0        # ohm，每相初始负荷
STEP_LOAD = 18.0        # ohm，每相并入的额外负荷
RS = 0.04              # pu，定子电阻
XD, XQ = 1.8, 1.7      # pu，同步电抗
XD_PRIME, XQ_PRIME = 0.08, 0.3  # pu，暂态电抗


def print_summary(result: SimulationResult) -> None:
    """报告初值、阶跃与功率核对；末值仅表示本次观察终点。"""
    print("模型：四阶 dq 代数定子端口；机电/控制状态使用左端显式欧拉。")
    for label, row in (("初始平衡点", result.rows[0]), ("观察终点", result.rows[-1])):
        print(f"{label} t={row['time']:.3f} s：Vt={row['vt_pu:GEN']:.6f} pu，"
              f"speed={row['speed_pu:GEN']:.6f} pu，Efd={row['efd_pu:GEN']:.6f} pu，"
              f"Pm={BASE_POWER * row['pm_pu:GEN']:.6f} W")
        print(f"  端口输出={row['p:GEN']:.6f} W，铜损={row['p_copper:GEN']:.6f} W，"
              f"气隙功率={row['p_em:GEN']:.6f} W")
    balance = result.series('p_em:GEN') - result.series('p:GEN') - result.series('p_copper:GEN')
    print(f"三相负荷在 {LOAD_STEP_TIME:g} s 投入；全过程功率平衡残差 max={np.max(np.abs(balance)):.3e} W")


def define_case() -> CaseDefinition:
    """用平衡电阻负荷解析式给出 Vt=1 pu、speed=1 pu 的初始运行点。"""

    for name, value in (("BASE_POWER", BASE_POWER), ("BASE_PHASE_RMS", BASE_PHASE_RMS),
                        ("BASE_LOAD", BASE_LOAD), ("STEP_LOAD", STEP_LOAD)):
        if isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(value) or value <= 0:
            raise ValueError(f"{name}={value!r} 非法；请填写有限正数，容量用 VA、电压用 V、负荷用 Ω。")
    for name, value in (("RS", RS), ("XD", XD), ("XQ", XQ), ("XD_PRIME", XD_PRIME), ("XQ_PRIME", XQ_PRIME)):
        if isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(value) or value < 0:
            raise ValueError(f"{name}={value!r} 非法；请填写非负、有限的标幺阻抗。")
    zbase = 3 * BASE_PHASE_RMS**2 / BASE_POWER
    load_pu = BASE_LOAD / zbase
    total_r = load_pu + RS
    current = 1.0 / load_pu
    iq = current * total_r / math.hypot(total_r, XQ)
    id_ = current * XQ / math.hypot(total_r, XQ)
    pm = total_r * current**2  # 机械输入同时供给负荷有功和定子铜损。
    eq = total_r * iq + XD_PRIME * id_
    ed = total_r * id_ - XQ_PRIME * iq
    efd = eq + (XD - XD_PRIME) * id_

    components = (
        ParkSynchronousGenerator(
            "GEN",
            "bus",
            base_power=BASE_POWER,
            base_phase_rms=BASE_PHASE_RMS,
            stator_resistance_pu=RS,
            d_axis_reactance_pu=XD,
            q_axis_reactance_pu=XQ,
            d_axis_transient_reactance_pu=XD_PRIME,
            q_axis_transient_reactance_pu=XQ_PRIME,
            d_axis_open_circuit_time_constant=0.6,
            q_axis_open_circuit_time_constant=0.2,
            inertia_constant=3.5,
            damping=0.3,
            voltage_reference_pu=1.0,
            avr_gain=12.0,
            avr_time_constant=0.04,
            mechanical_power_reference_pu=pm,
            initial_mechanical_power_pu=pm,
            governor_droop=0.05,
            governor_time_constant=0.08,
            frequency=FREQUENCY,
            initial_rotor_angle=math.atan2(id_, iq),
            initial_eq_prime_pu=eq,
            initial_ed_prime_pu=ed,
            initial_efd_pu=efd,
        ),
        Resistor("BASE_A", "bus:a", "0", BASE_LOAD),
        Resistor("BASE_B", "bus:b", "0", BASE_LOAD),
        Resistor("BASE_C", "bus:c", "0", BASE_LOAD),
        Breaker("BRK_A", "bus:a", "step_load:a", closed=False),
        Breaker("BRK_B", "bus:b", "step_load:b", closed=False),
        Breaker("BRK_C", "bus:c", "step_load:c", closed=False),
        Resistor("STEP_A", "step_load:a", "0", STEP_LOAD),
        Resistor("STEP_B", "step_load:b", "0", STEP_LOAD),
        Resistor("STEP_C", "step_load:c", "0", STEP_LOAD),
    )

    config = SimulationConfig(
        time_step=TIME_STEP,
        stop_time=STOP_TIME,
        method="trapezoidal",
    )

    events = (
        BreakerCloseEvent(LOAD_STEP_TIME, "BRK_A", "A 相额外负荷投入"),
        BreakerCloseEvent(LOAD_STEP_TIME, "BRK_B", "B 相额外负荷投入"),
        BreakerCloseEvent(LOAD_STEP_TIME, "BRK_C", "C 相额外负荷投入"),
    )

    plots = (
        PlotSpec(
            columns=("vt_pu:GEN", "efd_pu:GEN"),
            figure_name="voltage_control.png",
            title="Generator terminal and field voltage (pu)",
        ),
        PlotSpec(
            columns=("speed_pu:GEN",),
            figure_name="speed.png",
            title="Generator speed (pu)",
        ),
        PlotSpec(
            columns=("pm_pu:GEN", "p_pu:GEN"),
            figure_name="power.png",
            title="Mechanical input and terminal output (pu, three-phase base)",
        ),
    )

    output = OutputOptions(
        save_data=bool(SAVE_RESULT_DATA),
        save_figure=bool(SAVE_RESULT_FIGURE),
        show_figure=SHOW_FIGURE,
    )

    return CaseDefinition(
        name="park_generator_avr_governor",
        components=components,
        config=config,
        events=events,
        plots=plots,
        output=output,
        summary=print_summary,
    )


def main() -> None:
    """按统一算例流程运行仿真。"""

    case = define_case()
    run_case(case)


if __name__ == "__main__":
    main()
