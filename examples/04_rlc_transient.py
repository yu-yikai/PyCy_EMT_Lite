"""演示二阶 RLC 暂态过程。

在项目根目录运行：uv run python examples/04_rlc_transient.py

电路连接（0 为参考地；电源正端接 src）：
    src o---[R1=20 ohm]---o n1---[L1=10 mH]---o out
        |                                   |
     [V1=1 V]                           [C1=10 uF]
        |                                   |
    0 --+-----------------------------------+

RLC 串联电路在阶跃激励下可能出现欠阻尼振荡，是理解二阶系统动态特性
和 MNA 状态更新顺序的经典教学算例。欠阻尼时把仿真末值与解析解
`v(t) = V(1 - exp(-alpha t)(cos(wd t) + alpha/wd sin(wd t)))` 对比。
观察：电容电压 v:out 和电感电流 i:L1 都从零开始；电压先超过 1 V，
随后振荡衰减并接近 1 V。电流的正方向为 n1 -> out。
练习：将 RESISTANCE 从 20.0 改为 40.0 ohm，第一处电压峰值应降低。
改成 100.0 ohm 后为过阻尼，仍会仿真和绘图，摘要提示跳过欠阻尼解析对比。
观察后恢复原值。研究步长误差时应对照整段暂态，不能只看已接近稳态的末值。
源码：pycy_emt_lite/core/simulation.py 的 Simulator.run() 组织求解和状态更新；
docs/component_derivations.md 第 5 节给出一个完整 RLC 矩阵的手算与运行核对。
"""

import math

from pycy_emt_lite import Capacitor, Inductor, Resistor, SimulationConfig, VoltageSource
from pycy_emt_lite.cases import CaseDefinition, OutputOptions, PlotSpec, run_case
from pycy_emt_lite.io.results import SimulationResult

SAVE_RESULT_DATA = 0
SAVE_RESULT_FIGURE = 0
SHOW_FIGURE = True

SOURCE_VOLTAGE = 1.0  # V
RESISTANCE = 20.0  # ohm
INDUCTANCE = 10e-3  # H，等于 10 mH
CAPACITANCE = 10e-6  # F，等于 10 uF


def print_summary(result: SimulationResult) -> None:
    """打印 RLC 暂态结果，并与欠阻尼二阶系统解析解对比。"""

    time = result.series("time")
    voltage = result.series("v:out")
    # 衰减系数 alpha = R/2L，无阻尼自然频率 w0 = 1/sqrt(LC)，阻尼振荡频率 wd = sqrt(w0^2 - alpha^2)
    alpha = RESISTANCE / (2.0 * INDUCTANCE)
    natural_frequency = 1.0 / math.sqrt(INDUCTANCE * CAPACITANCE)
    if alpha >= natural_frequency:
        print(f"最终输出电压：{voltage[-1]:.6f} V；当前参数为临界阻尼或过阻尼，跳过欠阻尼解析对比。")
        return
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
            columns=("v:out",),
            figure_name="voltage.png",
            title="RLC transient: capacitor voltage / V",
        ),
        PlotSpec(
            columns=("i:L1",),
            figure_name="current.png",
            title="RLC transient: inductor current / A",
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
