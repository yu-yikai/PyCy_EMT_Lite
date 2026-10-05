"""演示最简单的直流电阻电路。

在项目根目录运行：uv run python examples/01_r_circuit.py

电路连接（0 为参考地；电源正端接 n1）：
    n1 o----[R1=5 ohm]----o 0
       |                 |
       +----[V1=10 V]----+

观察：电压恒为 10 V，电阻电流 I=V/R=2 A；电源支路电流为 -2 A，
因为其正方向是流入电源正端。关闭电压图后会显示电流图。
练习：只把 RESISTANCE 改为 10.0，保存并重新运行，电流应减为 1 A。
完成后恢复 5.0。函数 define_case() 定义元件和设置，run_case() 负责运行。
源码：pycy_emt_lite/components/basic.py 的 Resistor 和 VoltageSource；
pycy_emt_lite/cases.py 的 run_case() 展开“创建电路 -> 仿真 -> 绘图”的流程。
"""

from pycy_emt_lite import Resistor, SimulationConfig, VoltageSource
from pycy_emt_lite.cases import CaseDefinition, OutputOptions, PlotSpec, run_case
from pycy_emt_lite.io.results import SimulationResult

SAVE_RESULT_DATA = 0
SAVE_RESULT_FIGURE = 0
SHOW_FIGURE = True

SOURCE_VOLTAGE = 10.0  # V
RESISTANCE = 5.0  # ohm


def print_summary(result: SimulationResult) -> None:
    """打印 R 电路关键结果，并与解析值对比。"""

    voltage = result.series("v:n1")[-1]
    print(f"节点 n1 电压：{voltage:.6f} V（解析值 {SOURCE_VOLTAGE:.6f} V）")
    current = result.series("i:R1")[-1]
    source_current = result.series("i:V1")[-1]
    print(f"电阻 R1 电流：{current:.6f} A（解析值 {SOURCE_VOLTAGE / RESISTANCE:.6f} A）")
    print(f"电源 V1 支路电流：{source_current:.6f} A（负号表示电源向外供电）")


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
            columns=("v:n1",),
            figure_name="voltage.png",
            title="R circuit: voltage / V",
        ),
        PlotSpec(
            columns=("i:R1",),
            figure_name="current.png",
            title="R circuit: current / A",
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
