"""演示三相对称电源、线路和负荷的稳态波形。

使用三相电源、三相线路和三相负荷元件，观察三相电压电流的对称波形，
每相负荷为 20 Ω 串联 50 mH；零电流启动后，电流滞后电压。
稳态按复阻抗 Zload = Rload + jωLload 计算，不能再使用纯电阻分压。"""

import math

from pycy_emt_lite import SimulationConfig, ThreePhaseLine, ThreePhaseLoad, ThreePhaseSource
from pycy_emt_lite.analysis import three_phase_power, three_phase_rms
from pycy_emt_lite.cases import CaseDefinition, OutputOptions, PlotSpec, run_case
from pycy_emt_lite.io.results import SimulationResult

SAVE_RESULT_DATA = 0
SAVE_RESULT_FIGURE = 0
SHOW_FIGURE = True

SOURCE_RMS = 230.0
FREQUENCY = 50.0
LINE_RESISTANCE = 0.5
LOAD_RESISTANCE = 20.0
LOAD_INDUCTANCE = 50e-3  # H，每相；50 Hz 时感抗约 15.7 Ω


def print_summary(result: SimulationResult) -> None:
    """在两个完整周期内比较三相 RMS、复阻抗分压和负荷功率。"""

    voltages = ("v:load:a", "v:load:b", "v:load:c")
    currents = ("i:LOAD:a", "i:LOAD:b", "i:LOAD:c")
    voltage_rms = three_phase_rms(result, voltages, start_time=0.06, end_time=0.1)
    current_rms = three_phase_rms(result, currents, start_time=0.06, end_time=0.1)
    impedance = complex(LOAD_RESISTANCE, 2 * math.pi * FREQUENCY * LOAD_INDUCTANCE)
    current = SOURCE_RMS / (LINE_RESISTANCE + impedance)
    print(f"稳态窗口：0.06–0.10 s；三相正序，每相负荷为 {LOAD_RESISTANCE:g} Ω + {LOAD_INDUCTANCE * 1e3:g} mH。")
    for phase, voltage, branch in zip("ABC", voltages, currents):
        print(f"{phase} 相：负荷电压 {voltage_rms[voltage]:.3f} V RMS，电流 {current_rms[branch]:.3f} A RMS")
    print(f"相量解：负荷电压 {abs(current * impedance):.3f} V RMS，电流 {abs(current):.3f} A RMS；"
          f"电流滞后本相电源电压 {math.degrees(math.atan2(-current.imag, current.real)):.3f}°")
    power = three_phase_power(result, voltages, currents, start_time=0.06, end_time=0.1)
    print(f"负荷三相总有功 {power.active_power:.3f} W，无功 {power.reactive_power:.3f} var，功率因数 {power.power_factor:.4f}")


def define_case() -> CaseDefinition:
    """定义三相稳态算例。"""

    components = (
        ThreePhaseSource("VS", "source", phase_rms=SOURCE_RMS, frequency=FREQUENCY),
        ThreePhaseLine("LINE", "source", "load", resistance=LINE_RESISTANCE),
        ThreePhaseLoad("LOAD", "load", resistance=LOAD_RESISTANCE, inductance=LOAD_INDUCTANCE),
    )

    config = SimulationConfig(
        time_step=1e-4,
        stop_time=0.1,
        method="trapezoidal",
    )

    plots = (
        PlotSpec(
            columns=("v:load:a", "v:load:b", "v:load:c"),
            figure_name="voltages.png",
            title="Balanced RL load: phase voltages (V)",
        ),
        PlotSpec(
            columns=("i:LOAD:a", "i:LOAD:b", "i:LOAD:c"),
            figure_name="currents.png",
            title="Balanced RL load: phase currents (A)",
        ),
    )

    output = OutputOptions(
        save_data=bool(SAVE_RESULT_DATA),
        save_figure=bool(SAVE_RESULT_FIGURE),
        show_figure=SHOW_FIGURE,
    )

    return CaseDefinition(
        name="three_phase_steady_state",
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
