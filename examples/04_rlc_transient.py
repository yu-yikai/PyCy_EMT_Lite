"""演示二阶 RLC 暂态过程。

RLC 串联电路在阶跃激励下可能出现欠阻尼振荡，是理解二阶系统动态特性
和 MNA 状态更新顺序的经典教学算例。运行后把仿真末值与解析解
`v(t) = 1 - exp(-alpha t)(cos(wd t) + alpha/wd sin(wd t))` 对比。"""

import math

from pycy_emt_lite import Capacitor, Inductor, Resistor, SimulationConfig, VoltageSource
from pycy_emt_lite.cases import CaseDefinition, OutputOptions, PlotSpec, run_case
from pycy_emt_lite.io.results import SimulationResult

SAVE_RESULT_DATA = 0
SAVE_RESULT_FIGURE = 0
SHOW_FIGURE = True

SOURCE_VOLTAGE = 1.0
RESISTANCE = 20.0
INDUCTANCE = 10e-3
CAPACITANCE = 10e-6


def print_summary(result: SimulationResult) -> None:
    """打印 RLC 暂态结果，并与欠阻尼二阶系统解析解对比。"""

    time = result.series("time")
    voltage = result.series("v:out")
    # 衰减系数 alpha = R/2L，无阻尼自然频率 w0 = 1/sqrt(LC)，阻尼振荡频率 wd = sqrt(w0^2 - alpha^2)
    alpha = RESISTANCE / (2.0 * INDUCTANCE)
    natural_frequency = 1.0 / math.sqrt(INDUCTANCE * CAPACITANCE)
    damped_frequency = math.sqrt(natural_frequency**2 - alpha**2)
    t_end = time[-1]
    theoretical = SOURCE_VOLTAGE * (
        1.0
        - math.exp(-alpha * t_end)
        * (math.cos(damped_frequency * t_end) + alpha / damped_frequency * math.sin(damped_frequency * t_end))
    )
    error = abs(voltage[-1] - theoretical)
    print(f"最终输出电压：{voltage[-1]:.6f} V，解析解 {theoretical:.6f} V，绝对误差 {error:.2e} V")


def define_case() -> CaseDefinition:
    """定义 RLC 暂态算例。"""

    components = (
        VoltageSource("V1", "src", "0", SOURCE_VOLTAGE),
        Resistor("R1", "src", "n1", RESISTANCE),
        Inductor("L1", "n1", "out", INDUCTANCE),
        Capacitor("C1", "out", "0", CAPACITANCE),
    )

    config = SimulationConfig(
        time_step=2e-6,
        stop_time=10e-3,
        method="trapezoidal",
    )

    plots = (
        PlotSpec(
            columns=("v:out", "i:L1"),
            title="RLC 暂态响应",
        ),
    )

    output = OutputOptions(
        save_data=bool(SAVE_RESULT_DATA),
        save_figure=bool(SAVE_RESULT_FIGURE),
        show_figure=SHOW_FIGURE,
    )

    return CaseDefinition(
        name="rlc_transient",
        components=components,
        config=config,
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
