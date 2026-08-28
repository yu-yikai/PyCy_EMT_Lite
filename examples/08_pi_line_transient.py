"""演示单相 π 型集中参数线路的暂态过程。

π 型线路由一条串联 R-L 支路和两端各 C/2 的并联电容组成，是输电线路
集中参数建模的经典模型。本算例用 50 Hz 交流电源经 π 型线路给电阻负载
供电，观察受端电压幅值与线路电流的相位关系。
"""

import math

from pycy_emt_lite import PiLine, Resistor, SimulationConfig, VoltageSource
from pycy_emt_lite.cases import CaseDefinition, OutputOptions, PlotSpec, run_case

SAVE_RESULT_DATA = 0
SAVE_RESULT_FIGURE = 0
SHOW_FIGURE = True

FREQUENCY = 50.0
SOURCE_RMS = 220.0


def source_voltage(time: float) -> float:
    """返回电源瞬时电压（220 V 有效值、50 Hz 正弦）。"""

    return math.sqrt(2.0) * SOURCE_RMS * math.sin(2.0 * math.pi * FREQUENCY * time)


def define_case() -> CaseDefinition:
    """定义 π 型线路暂态算例。"""

    components = (
        VoltageSource("V1", "src", "0", source_voltage),
        PiLine("LINE", "src", "load", resistance=2.0, inductance=20e-3, capacitance=2e-6),
        Resistor("LOAD", "load", "0", 100.0),
    )

    config = SimulationConfig(
        time_step=1e-4,
        stop_time=0.06,
        method="trapezoidal",
    )

    plots = (
        PlotSpec(
            columns=("v:src", "v:load", "i:LINE:series"),
            kind="series",
            title="π 型线路受端电压与线路电流",
        ),
    )

    output = OutputOptions(
        save_data=bool(SAVE_RESULT_DATA),
        save_figure=bool(SAVE_RESULT_FIGURE),
        show_figure=SHOW_FIGURE,
    )

    return CaseDefinition(
        name="pi_line_transient",
        components=components,
        config=config,
        plots=plots,
        output=output,
    )


def main() -> None:
    """按统一算例流程运行仿真。"""

    case = define_case()
    run_case(case)


if __name__ == "__main__":
    main()
