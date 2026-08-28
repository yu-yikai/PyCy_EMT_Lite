"""演示最简单的直流电阻电路。

本算例展示 PyCy_EMT_Lite 最基本的建模流程：定义元件对象列表 ->
形成电路 -> 配置仿真 -> 运行 -> 绘图。"""

from pycy_emt_lite import Resistor, SimulationConfig, VoltageSource
from pycy_emt_lite.cases import CaseDefinition, OutputOptions, PlotSpec, run_case
from pycy_emt_lite.io.results import SimulationResult

SAVE_RESULT_DATA = 0
SAVE_RESULT_FIGURE = 0
SHOW_FIGURE = True

SOURCE_VOLTAGE = 10.0
RESISTANCE = 5.0


def print_summary(result: SimulationResult) -> None:
    """打印 R 电路关键结果，并与解析值对比。"""

    voltage = result.series("v:n1")[-1]
    print(f"节点 n1 电压：{voltage:.6f} V（解析值 {SOURCE_VOLTAGE:.6f} V）")


def define_case() -> CaseDefinition:
    """定义 R 电路算例。"""

    components = (
        VoltageSource("V1", "n1", "0", SOURCE_VOLTAGE),
        Resistor("R1", "n1", "0", RESISTANCE),
    )

    config = SimulationConfig(
        time_step=1e-4,
        stop_time=1e-3,
        method="trapezoidal",
    )

    plots = (
        PlotSpec(
            columns=("v:n1", "i:R1"),
            title="R 电路电压与电流",
        ),
    )

    output = OutputOptions(
        save_data=bool(SAVE_RESULT_DATA),
        save_figure=bool(SAVE_RESULT_FIGURE),
        show_figure=SHOW_FIGURE,
    )

    return CaseDefinition(
        name="r_circuit",
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
