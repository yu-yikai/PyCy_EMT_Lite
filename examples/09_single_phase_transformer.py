"""演示单相双绕组变压器教学模型。

变压器一次侧接 50 Hz 交流电源，二次侧带电阻负载。`turns_ratio` 定义为
一次电压与二次电压之比 `Vp / Vs`；漏阻抗折算在一次侧，可选的励磁支路
并联在一次侧。观察二次电压的幅值变化和一次电流中的励磁分量。
"""

import math

from pycy_emt_lite import Resistor, SimulationConfig, SinglePhaseTransformer, VoltageSource
from pycy_emt_lite.cases import CaseDefinition, OutputOptions, PlotSpec, run_case

SAVE_RESULT_DATA = 0
SAVE_RESULT_FIGURE = 0
SHOW_FIGURE = True

FREQUENCY = 50.0
SOURCE_RMS = 230.0


def source_voltage(time: float) -> float:
    """返回一次侧电源瞬时电压（230 V 有效值、50 Hz 正弦）。"""

    return math.sqrt(2.0) * SOURCE_RMS * math.sin(2.0 * math.pi * FREQUENCY * time)


def define_case() -> CaseDefinition:
    """定义单相变压器算例。"""

    components = (
        VoltageSource("V1", "pri", "0", source_voltage),
        SinglePhaseTransformer(
            "T1",
            "pri",
            "0",
            "sec",
            "0",
            turns_ratio=2.0,
            leakage_resistance=0.5,
            leakage_inductance=5e-3,
            magnetizing_inductance=1.0,
        ),
        Resistor("LOAD", "sec", "0", 50.0),
    )

    config = SimulationConfig(
        time_step=1e-4,
        stop_time=0.06,
        method="trapezoidal",
    )

    plots = (
        PlotSpec(
            columns=("v:pri", "v:sec", "i:T1:primary", "i:T1:secondary"),
            kind="series",
            title="单相变压器一二次电压与电流",
        ),
    )

    output = OutputOptions(
        save_data=bool(SAVE_RESULT_DATA),
        save_figure=bool(SAVE_RESULT_FIGURE),
        show_figure=SHOW_FIGURE,
    )

    return CaseDefinition(
        name="single_phase_transformer",
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
