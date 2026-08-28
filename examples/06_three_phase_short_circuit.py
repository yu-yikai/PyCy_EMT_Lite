"""演示三相短路故障投入与清除过程。

利用故障元件和事件系统，观察短路期间三相故障电流的暂态过程，以及故障
清除后的恢复行为。"""

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
    """打印短路期间三相故障电流峰值。"""

    currents = [abs(result.series(column)) for column in ("i:FA", "i:FB", "i:FC")]
    peak = max(max(current) for current in currents)
    print(f"三相短路故障电流峰值：{peak:.2f} A")


def define_case() -> CaseDefinition:
    """定义三相短路故障算例。"""

    components = (
        ThreePhaseSource("VS", "source", phase_rms=230.0, frequency=50.0),
        ThreePhaseLine("LINE", "source", "fault_bus", resistance=0.8),
        ThreePhaseLoad("LOAD", "fault_bus", resistance=50.0),
        Fault("FA", "fault_bus:a", resistance=0.1),
        Fault("FB", "fault_bus:b", resistance=0.1),
        Fault("FC", "fault_bus:c", resistance=0.1),
    )

    config = SimulationConfig(
        time_step=1e-4,
        stop_time=0.12,
        method="trapezoidal",
    )

    events = (
        FaultApplyEvent(0.04, "FA", "A 相故障投入"),
        FaultApplyEvent(0.04, "FB", "B 相故障投入"),
        FaultApplyEvent(0.04, "FC", "C 相故障投入"),
        FaultClearEvent(0.08, "FA", "A 相故障清除"),
        FaultClearEvent(0.08, "FB", "B 相故障清除"),
        FaultClearEvent(0.08, "FC", "C 相故障清除"),
    )

    plots = (
        PlotSpec(
            columns=("i:FA", "i:FB", "i:FC"),
            kind="three_phase",
            title="三相短路故障电流",
        ),
    )

    output = OutputOptions(
        save_data=bool(SAVE_RESULT_DATA),
        save_figure=bool(SAVE_RESULT_FIGURE),
        show_figure=SHOW_FIGURE,
    )

    return CaseDefinition(
        name="three_phase_short_circuit",
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
