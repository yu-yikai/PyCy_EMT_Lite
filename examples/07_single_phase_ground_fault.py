"""演示三相系统中的单相接地故障。

单相接地是不对称故障的典型代表，对比故障相与非故障相的电压，
并理解故障元件的分相接入方式。"""

from pycy_emt_lite import (
    Fault,
    FaultApplyEvent,
    FaultClearEvent,
    SimulationConfig,
    ThreePhaseLine,
    ThreePhaseLoad,
    ThreePhaseSource,
)
from pycy_emt_lite.cases import CaseDefinition, OutputOptions, PlotSpec, run_case
from pycy_emt_lite.analysis import peak_abs, three_phase_rms
from pycy_emt_lite.io.results import SimulationResult

SAVE_RESULT_DATA = 0
SAVE_RESULT_FIGURE = 0
SHOW_FIGURE = True


def print_summary(result: SimulationResult) -> None:
    """用避开事件边界的完整 50 Hz 周期比较故障前、中、后三相 RMS。"""

    for label, start, end in (("故障前", 0.01, 0.03), ("故障中", 0.05, 0.07), ("故障后", 0.09, 0.11)):
        values = three_phase_rms(result, ("v:load:a", "v:load:b", "v:load:c"), start_time=start, end_time=end)
        print(f"{label} [{start:.2f}, {end:.2f}] s：" + ", ".join(f"{name}={value:.2f} V RMS" for name, value in values.items()))
    peak = peak_abs(result, "i:FA_G", start_time=0.05, end_time=0.07)
    print(f"故障中 [0.05, 0.07] s：A 相故障电流峰值={peak:.2f} A")


def define_case() -> CaseDefinition:
    """定义单相接地故障算例。"""

    components = (
        ThreePhaseSource("VS", "source", phase_rms=230.0, frequency=50.0),
        ThreePhaseLine("LINE", "source", "load", resistance=0.8),
        ThreePhaseLoad("LOAD", "load", resistance=50.0),
        Fault("FA_G", "load:a", resistance=0.1),
    )

    config = SimulationConfig(
        time_step=1e-4,
        stop_time=0.12,
        method="trapezoidal",
    )

    events = (
        FaultApplyEvent(0.04, "FA_G", "A 相接地故障投入"),
        FaultClearEvent(0.08, "FA_G", "A 相接地故障清除"),
    )

    plots = (
        PlotSpec(
            columns=("v:load:a", "v:load:b", "v:load:c"),
            kind="three_phase",
            title="单相接地故障负荷端电压",
        ),
    )

    output = OutputOptions(
        save_data=bool(SAVE_RESULT_DATA),
        save_figure=bool(SAVE_RESULT_FIGURE),
        show_figure=SHOW_FIGURE,
    )

    return CaseDefinition(
        name="single_phase_ground_fault",
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
