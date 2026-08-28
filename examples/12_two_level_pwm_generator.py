"""运行两电平 PWM 逆变器驱动的 RL 负载教学算例。

使用理想开关、三角载波和正弦参考生成 SPWM 门极信号，观察负载端
阶梯状相电压与接近正弦的电流波形。"""

import math
from collections.abc import Callable

from pycy_emt_lite import Inductor, Resistor, SimulationConfig, VoltageSource
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
CARRIER_TIME_SHIFT = -0.5 / SWITCHING_FREQUENCY


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

    phase_shifts = {
        "a": math.pi / 2.0,
        "b": -2.0 * math.pi / 3.0 + math.pi / 2.0,
        "c": 2.0 * math.pi / 3.0 + math.pi / 2.0,
    }
    components = [
        VoltageSource("Vdc", "dc_p", "0", DC_VOLTAGE),
    ]

    for phase_name, shift in phase_shifts.items():
        phase_node = f"phase_{phase_name}"
        resistor_node = f"load_{phase_name}_r"
        upper_gate = upper_switch_closed(shift)
        lower_gate = lower_switch_closed(shift)
        components.extend(
            [
                IdealSwitch(f"S{phase_name}_upper", "dc_p", phase_node, upper_gate),
                IdealSwitch(f"S{phase_name}_lower", phase_node, "0", lower_gate),
                Resistor(f"R{phase_name}", phase_node, resistor_node, LOAD_RESISTANCE),
                Inductor(f"L{phase_name}", resistor_node, "load_n", LOAD_INDUCTANCE),
            ]
        )

    return tuple(components)


def transform_result(raw: SimulationResult) -> SimulationResult:
    """把 MNA 原始列整理为教学使用的三相电压、电流列。"""

    rows: list[dict[str, float]] = []
    for row in raw.rows:
        rows.append(
            {
                "time": row["time"],
                "i_a": row["i:La"],
                "i_b": row["i:Lb"],
                "i_c": row["i:Lc"],
                "v_a": row["v:phase_a"],
                "v_b": row["v:phase_b"],
                "v_c": row["v:phase_c"],
            }
        )

    return SimulationResult(
        "two_level_pwm_generator",
        raw.method,
        raw.time_step,
        raw.stop_time,
        rows,
        event_log=list(raw.event_log),
    )


def print_summary(result: SimulationResult) -> None:
    """打印两电平 PWM 算例末值。"""

    print(
        "末值："
        f" i_a={result.rows[-1]['i_a']:.6f} A,"
        f" i_b={result.rows[-1]['i_b']:.6f} A,"
        f" i_c={result.rows[-1]['i_c']:.6f} A"
    )


def define_case() -> CaseDefinition:
    """定义两电平 PWM 逆变器算例。"""

    components = create_components()

    config = SimulationConfig(
        time_step=TIME_STEP,
        stop_time=STOP_TIME,
        method="trapezoidal",
        event_time_policy="require_aligned",
    )

    events = ()

    plots = (
        PlotSpec(
            columns=("i_a", "i_b", "i_c"),
            kind="series",
            title="两电平 PWM 逆变器三相负载电流",
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
        result_transform=transform_result,
    )


def main() -> None:
    """按统一算例流程运行仿真。"""

    case = define_case()
    run_case(case)


if __name__ == "__main__":
    main()
