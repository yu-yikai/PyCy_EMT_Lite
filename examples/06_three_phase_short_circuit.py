"""演示三相短路故障投入与清除过程。

利用故障元件和事件系统，观察短路期间三相故障电流的暂态过程，以及故障
清除后的恢复行为。每相线路串联 0.8 Ω 和 5 mH，负荷仍为 50 Ω。
线路电流在故障投入/清除时连续；故障支路电流可以跳变。清除时储能电流转入
负荷，母线会短时过电压。本例不含寄生电容、避雷器或电弧模型。
清除后的时间常数 L/(Rline+Rload) 约 98 μs，采用 10 μs 步长分辨其衰减。
"""

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

SOURCE_RMS = 230.0
FREQUENCY = 50.0
LINE_RESISTANCE = 0.8
LINE_INDUCTANCE = 5e-3  # H，每相；50 Hz 时感抗约 1.57 Ω
LOAD_RESISTANCE = 50.0
FAULT_RESISTANCE = 0.1
TIME_STEP = 10e-6      # s，约为最快 L/R 时间常数的 1/10


def print_summary(result: SimulationResult) -> None:
    """比较不跨事件的周期窗口，并保留短路及清除过电压峰值。"""

    voltages = ("v:fault_bus:a", "v:fault_bus:b", "v:fault_bus:c")
    currents = ("i:LINE:a", "i:LINE:b", "i:LINE:c")
    for label, start, end in (("故障前", 0.01, 0.03), ("故障中", 0.05, 0.07), ("故障后", 0.09, 0.11)):
        voltage_rms = three_phase_rms(result, voltages, start_time=start, end_time=end)
        current_rms = three_phase_rms(result, currents, start_time=start, end_time=end)
        print(f"{label} [{start:.2f}, {end:.2f}] s（完整周期，保留暂态分量）：")
        for phase, voltage, branch in zip("ABC", voltages, currents):
            print(f"  {phase} 相：母线 {voltage_rms[voltage]:.3f} V RMS，线路 {current_rms[branch]:.3f} A RMS，"
                  f"负荷有功 {voltage_rms[voltage]**2 / LOAD_RESISTANCE:.3f} W")
    peak = max(peak_abs(result, column, start_time=0.04, end_time=0.08) for column in ("i:FA", "i:FB", "i:FC"))
    print(f"三相短路故障电流峰值：{peak:.2f} A")
    clearing_peak = max(peak_abs(result, column, start_time=0.08) for column in voltages)
    print(f"清除后母线电压绝对峰值：{clearing_peak:.2f} V（线路储能电流转入电阻负荷）")


def define_case() -> CaseDefinition:
    """定义三相短路故障算例。"""

    components = (
        ThreePhaseSource("VS", "source", phase_rms=SOURCE_RMS, frequency=FREQUENCY),
        ThreePhaseLine("LINE", "source", "fault_bus", resistance=LINE_RESISTANCE, inductance=LINE_INDUCTANCE),
        ThreePhaseLoad("LOAD", "fault_bus", resistance=LOAD_RESISTANCE),
        Fault("FA", "fault_bus:a", resistance=FAULT_RESISTANCE),
        Fault("FB", "fault_bus:b", resistance=FAULT_RESISTANCE),
        Fault("FC", "fault_bus:c", resistance=FAULT_RESISTANCE),
    )

    config = SimulationConfig(
        time_step=TIME_STEP,
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
            figure_name="fault_currents.png",
            title="Three-phase short circuit: fault currents (A)",
        ),
        PlotSpec(
            columns=("i:LINE:a", "i:LINE:b", "i:LINE:c"),
            figure_name="line_currents.png",
            title="Three-phase short circuit: continuous line currents (A)",
        ),
        PlotSpec(
            columns=("v:fault_bus:a", "v:fault_bus:b", "v:fault_bus:c"),
            figure_name="voltages.png",
            title="Fault bus voltages and clearing transient (V)",
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
