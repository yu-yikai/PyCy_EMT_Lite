"""运行两电平 PWM 逆变器驱动的 RL 负载教学算例。

使用理想开关、三角载波和正弦参考生成 SPWM 门极信号，观察负载端
阶梯状相电压与接近正弦的电流波形。门极在仿真网格上采样，不自动定位开关边沿。
整周期窗口报告总 RMS 与基波，平均模型只作为线性调制范围内的基波参考。
相位差以各相未经过零阶保持的正弦参考为准；总 RMS 还含开关纹波。
"""

import math
from collections.abc import Callable

import numpy as np

from pycy_emt_lite import Inductor, Resistor, SimulationConfig, VoltageSource
from pycy_emt_lite.analysis import rms
from pycy_emt_lite.cases import CaseDefinition, OutputOptions, PlotSpec, run_case
from pycy_emt_lite.components import IdealSwitch
from pycy_emt_lite.controls import carrier_compare, triangular_carrier
from pycy_emt_lite.io.results import SimulationResult

SAVE_RESULT_DATA = 0
SAVE_RESULT_FIGURE = 0
SHOW_FIGURE = True

TIME_STEP = 5e-6
STOP_TIME = 0.2
SWITCHING_FREQUENCY = 1000.0
CONTROL_SAMPLE_TIME = 1.0 / (10.0 * SWITCHING_FREQUENCY)
FUNDAMENTAL_FREQUENCY = 60.0
DC_VOLTAGE = 400.0
MODULATION_INDEX = 0.8
LOAD_RESISTANCE = 1.0
LOAD_INDUCTANCE = 1e-3
SWITCH_ON_RESISTANCE = 1e-3
CARRIER_TIME_SHIFT = -0.5 / SWITCHING_FREQUENCY
STEADY_START = 0.1  # s，默认统计窗口含 6 个基波周期与 100 个载波周期
PHASE_SHIFTS = {
    "a": math.pi / 2.0,
    "b": -2.0 * math.pi / 3.0 + math.pi / 2.0,
    "c": 2.0 * math.pi / 3.0 + math.pi / 2.0,
}


def held_reference(time: float, phase_shift: float) -> float:
    """返回零阶保持后的 SPWM 调制参考波。"""

    sample_index = math.floor((time + 1e-15) / CONTROL_SAMPLE_TIME)
    sample_time = sample_index * CONTROL_SAMPLE_TIME
    angle = 2.0 * math.pi * FUNDAMENTAL_FREQUENCY * sample_time
    return MODULATION_INDEX * math.sin(angle + phase_shift)


def upper_switch_closed(phase_shift: float) -> Callable[[float], bool]:
    """构造某一相上桥臂的门极函数。"""

    def gate(time: float) -> bool:
        reference = held_reference(time, phase_shift)
        carrier = triangular_carrier(time + CARRIER_TIME_SHIFT, SWITCHING_FREQUENCY)
        return bool(carrier_compare(reference, carrier))

    return gate


def lower_switch_closed(phase_shift: float) -> Callable[[float], bool]:
    """构造某一相下桥臂的互补门极函数。"""

    upper_gate = upper_switch_closed(phase_shift)

    def gate(time: float) -> bool:
        return not upper_gate(time)

    return gate


def create_components() -> tuple:
    """搭建三相两电平 PWM 逆变器和浮置星形 R-L 负载。"""

    components = [
        VoltageSource("Vdc", "dc_p", "0", DC_VOLTAGE),
    ]

    for phase_name, shift in PHASE_SHIFTS.items():
        phase_node = f"phase_{phase_name}"
        resistor_node = f"load_{phase_name}_r"
        upper_gate = upper_switch_closed(shift)
        lower_gate = lower_switch_closed(shift)
        components.extend(
            [
                IdealSwitch(f"S{phase_name}_upper", "dc_p", phase_node, upper_gate, closed_resistance=SWITCH_ON_RESISTANCE),
                IdealSwitch(f"S{phase_name}_lower", phase_node, "0", lower_gate, closed_resistance=SWITCH_ON_RESISTANCE),
                Resistor(f"R{phase_name}", phase_node, resistor_node, LOAD_RESISTANCE),
                Inductor(f"L{phase_name}", resistor_node, "load_n", LOAD_INDUCTANCE),
            ]
        )

    return tuple(components)


def print_summary(result: SimulationResult) -> None:
    """在整周期窗口提取三相电流基波，区别平均模型和开关波形。"""

    omega = 2.0 * math.pi * FUNDAMENTAL_FREQUENCY
    hold = np.sinc(FUNDAMENTAL_FREQUENCY * CONTROL_SAMPLE_TIME) * np.exp(-1j * omega * CONTROL_SAMPLE_TIME / 2.0)
    reference = MODULATION_INDEX * DC_VOLTAGE / (2.0 * math.sqrt(2.0)) * hold / complex(
        LOAD_RESISTANCE + SWITCH_ON_RESISTANCE, omega * LOAD_INDUCTANCE,
    )
    time = result.series("time")
    window = (time >= STEADY_START) & (time <= STOP_TIME)
    time = time[window]
    duration = time[-1] - time[0]
    sine, cosine = np.sin(omega * time), np.cos(omega * time)
    print(f"统计窗口：{STEADY_START:g}–{STOP_TIME:g} s；门极按 {result.time_step:g} s 网格采样。")
    print(f"基波平均模型参考：{abs(reference):.6f} A RMS，相位差 {math.degrees(np.angle(reference)):+.6f}°"
          "（含参考保持延迟与导通电阻，忽略开关纹波）。")
    for phase, shift in PHASE_SHIFTS.items():
        current = result.series(f"i:L{phase}")[window]
        fundamental = math.sqrt(2.0) * complex(np.trapezoid(current * sine, time), np.trapezoid(current * cosine, time)) / duration
        total_rms = rms(result, f"i:L{phase}", start_time=STEADY_START, end_time=STOP_TIME)
        relative_phase = math.degrees(np.angle(fundamental * np.exp(-1j * shift)))
        print(f"{phase.upper()} 相：总 RMS {total_rms:.6f} A，基波 {abs(fundamental):.6f} A RMS，相位差 {relative_phase:+.6f}°")


def define_case() -> CaseDefinition:
    """定义两电平 PWM 逆变器算例。"""

    components = create_components()

    config = SimulationConfig(
        time_step=TIME_STEP,
        stop_time=STOP_TIME,
        method="trapezoidal",
        event_time_policy="require_aligned",  # 仅约束显式 events，不自动对齐门极边沿
    )

    events = ()

    plots = (
        PlotSpec(
            columns=("i:La", "i:Lb", "i:Lc"),
            figure_name="currents.png",
            kind="series",
            title="Two-level PWM inverter: phase currents (A)",
        ),
    )

    output = OutputOptions(
        save_data=bool(SAVE_RESULT_DATA),
        save_figure=bool(SAVE_RESULT_FIGURE),
        show_figure=SHOW_FIGURE,
    )

    return CaseDefinition(
        name="two_level_pwm_generator",
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
