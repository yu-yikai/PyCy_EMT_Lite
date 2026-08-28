"""演示三相系统中的单相接地故障。

单相接地是不对称故障的典型代表，观察故障相电压跌落与非故障相电压抬升，
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
from pycy_emt_lite.io.results import SimulationResult

SAVE_RESULT_DATA = 0
SAVE_RESULT_FIGURE = 0
SHOW_FIGURE = True


def print_summary(result: SimulationResult) -> None:
    """打印单相接地故障期间 A 相故障电流峰值与故障相电压跌落。"""

    fault_current = result.series("i:FA_G")
    phase_voltage = result.series("v:load:a")
    print(f"A 相故障电流峰值：{max(abs(fault_current)):.2f} A")
    print(f"A 相电压最低值：{min(phase_voltage):.2f} V（故障前约 230 V 幅值）")


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
