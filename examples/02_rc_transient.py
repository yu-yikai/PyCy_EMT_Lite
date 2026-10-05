"""演示 RC 一阶充电暂态过程。

在项目根目录运行：uv run python examples/02_rc_transient.py

电路连接（0 为参考地；电源正端接 src）：
    src o---[R1=1000 ohm]---o out
        |                  |
     [V1=1 V]          [C1=1 uF]
        |                  |
    0 --+------------------+

电容电压按时间常数 `tau = R*C` 指数趋近电源电压，可用于理解动态元件
历史项等效模型与梯形积分法。运行后把仿真结果与解析解
`v(t) = V(1 - exp(-t/tau))` 对比，验证数值积分精度。
观察：v:out 从 0 V 开始；tau=1 ms，1 ms 时约 0.6321 V，5 ms 时约 0.9933 V。
练习：将 CAPACITANCE 从 1e-6 改为 2e-6 F，时间常数变为 2 ms，充电更慢。
长期极限仍为 1 V，但原来的 5 ms 终点会离它更远；观察后恢复原值。
源码：pycy_emt_lite/components/basic.py 的 Capacitor._companion() 计算等效参数，
stamp() 写入矩阵，update_state() 在求解后保存电压和电流，供下一步使用。
"""

import math

from pycy_emt_lite import Capacitor, Resistor, SimulationConfig, VoltageSource
from pycy_emt_lite.cases import CaseDefinition, OutputOptions, PlotSpec, run_case
from pycy_emt_lite.io.results import SimulationResult

SAVE_RESULT_DATA = 0
SAVE_RESULT_FIGURE = 0
SHOW_FIGURE = True

SOURCE_VOLTAGE = 1.0  # V
RESISTANCE = 1000.0  # ohm
CAPACITANCE = 1e-6  # F，等于 1 uF


def print_summary(result: SimulationResult) -> None:
    """打印 RC 暂态结果，并与解析解对比。"""

    time = result.series("time")
    voltage = result.series("v:out")
    time_constant = RESISTANCE * CAPACITANCE
    theoretical = SOURCE_VOLTAGE * (1.0 - math.exp(-time[-1] / time_constant))
    error = abs(voltage[-1] - theoretical)
    print(f"最终电容电压：{voltage[-1]:.6f} V，解析解 {theoretical:.6f} V，绝对误差 {error:.2e} V")


def define_case() -> CaseDefinition:
    """定义 RC 暂态算例。"""

    components = (
        VoltageSource("V1", "src", "0", SOURCE_VOLTAGE),
        Resistor("R1", "src", "out", RESISTANCE),
        Capacitor("C1", "out", "0", CAPACITANCE),
    )

    config = SimulationConfig(
        time_step=1e-5,
        stop_time=5e-3,
        method="trapezoidal",
    )

    plots = (
        PlotSpec(
            columns=("v:out",),
            figure_name="voltage.png",
            title="RC transient: capacitor voltage / V",
        ),
    )

    output = OutputOptions(
        save_data=bool(SAVE_RESULT_DATA),
        save_figure=bool(SAVE_RESULT_FIGURE),
        show_figure=SHOW_FIGURE,
    )

    return CaseDefinition(
        name="rc_transient",
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
