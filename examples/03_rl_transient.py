"""演示 RL 一阶电流建立过程。

电感电流按时间常数 `tau = L/R` 指数趋近稳态值，用于理解电感的历史项
等效模型与支路电流未知量的引入。运行后把仿真结果与解析解
`i(t) = (V/R)(1 - exp(-t/tau))` 对比。"""

import math

from pycy_emt_lite import Inductor, Resistor, SimulationConfig, VoltageSource
from pycy_emt_lite.cases import CaseDefinition, OutputOptions, PlotSpec, run_case
from pycy_emt_lite.io.results import SimulationResult

SAVE_RESULT_DATA = 0
SAVE_RESULT_FIGURE = 0
SHOW_FIGURE = True

SOURCE_VOLTAGE = 1.0
RESISTANCE = 10.0
INDUCTANCE = 10e-3


def print_summary(result: SimulationResult) -> None:
    """打印 RL 暂态结果，并与解析解对比。"""

    time = result.series("time")
    current = result.series("i:L1")
    time_constant = INDUCTANCE / RESISTANCE
    theoretical = (SOURCE_VOLTAGE / RESISTANCE) * (1.0 - math.exp(-time[-1] / time_constant))
    error = abs(current[-1] - theoretical)
    print(f"最终电感电流：{current[-1]:.6f} A，解析解 {theoretical:.6f} A，绝对误差 {error:.2e} A")


def define_case() -> CaseDefinition:
    """定义 RL 暂态算例。"""

    components = (
        VoltageSource("V1", "src", "0", SOURCE_VOLTAGE),
        Resistor("R1", "src", "mid", RESISTANCE),
        Inductor("L1", "mid", "0", INDUCTANCE),
    )

    config = SimulationConfig(
        time_step=1e-5,
        stop_time=5e-3,
        method="trapezoidal",
    )

    plots = (
        PlotSpec(
            columns=("i:L1",),
            title="RL 暂态电感电流",
        ),
    )

    output = OutputOptions(
        save_data=bool(SAVE_RESULT_DATA),
        save_figure=bool(SAVE_RESULT_FIGURE),
        show_figure=SHOW_FIGURE,
    )

    return CaseDefinition(
        name="rl_transient",
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
