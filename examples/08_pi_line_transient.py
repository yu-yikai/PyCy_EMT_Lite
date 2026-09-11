"""演示单相 π 型集中参数线路的暂态过程。

π 型线路由一条串联 R-L 支路和两端各 C/2 的并联电容组成，是输电线路
集中参数建模的经典模型。本算例用 50 Hz 交流电源经 π 型线路给电阻负载
供电，观察受端电压幅值与线路电流的相位关系。最后两个完整周期与相量解对照：
Y = 1/Rload + jωC/2，Vr = Vs / (1 + (R + jωL)Y)，Iseries = YVr。
电容参数是两端对地电容之和；相位以电源电压为参考，正值表示超前。
"""

import math

import numpy as np

from pycy_emt_lite import PiLine, Resistor, SimulationConfig, VoltageSource
from pycy_emt_lite.analysis import rms
from pycy_emt_lite.cases import CaseDefinition, OutputOptions, PlotSpec, run_case
from pycy_emt_lite.io.results import SimulationResult

SAVE_RESULT_DATA = 0
SAVE_RESULT_FIGURE = 0
SHOW_FIGURE = True

FREQUENCY = 50.0
SOURCE_RMS = 220.0
RESISTANCE = 2.0          # Ω，线路串联电阻
INDUCTANCE = 20e-3        # H，线路串联电感
CAPACITANCE = 2e-6        # F，两端各 C/2
LOAD_RESISTANCE = 100.0   # Ω
TIME_STEP = 1e-4          # s
STOP_TIME = 0.06          # s
STEADY_START = 0.02       # s，默认参数的暂态已衰减，取后两个完整周期


def source_voltage(time: float) -> float:
    """返回电源瞬时电压（220 V 有效值、50 Hz 正弦）。"""

    return math.sqrt(2.0) * SOURCE_RMS * math.sin(2.0 * math.pi * FREQUENCY * time)


def source_voltage_derivative(time: float) -> float:
    """源直接并联线路电容，一致初始化需要 dv/dt，单位 V/s。"""

    omega = 2.0 * math.pi * FREQUENCY
    return math.sqrt(2.0) * SOURCE_RMS * omega * math.cos(omega * time)


def print_summary(result: SimulationResult) -> None:
    """给出受端电压/串联电流幅相，以及电阻消耗的平均有功。"""

    omega = 2.0 * math.pi * FREQUENCY
    receiving_admittance = complex(1.0 / LOAD_RESISTANCE, omega * CAPACITANCE / 2.0)
    receiving_voltage = SOURCE_RMS / (1.0 + complex(RESISTANCE, omega * INDUCTANCE) * receiving_admittance)
    series_current = receiving_admittance * receiving_voltage
    time = result.series("time")
    window = (time >= STEADY_START) & (time <= STOP_TIME)
    time = time[window]
    sine, cosine = np.sin(omega * time), np.cos(omega * time)
    print(f"稳态统计窗口：{STEADY_START:g}–{STOP_TIME:g} s；相位以电源电压为参考，正值超前。")
    for label, column, unit, expected in (
        ("受端电压", "v:load", "V", receiving_voltage),
        ("线路串联电流", "i:LINE:series", "A", series_current),
    ):
        measured_rms = rms(result, column, start_time=STEADY_START, end_time=STOP_TIME)
        values = result.series(column)[window]
        phase = math.degrees(math.atan2(np.trapezoid(values * cosine, time), np.trapezoid(values * sine, time)))
        expected_phase = math.degrees(math.atan2(expected.imag, expected.real))
        print(f"{label}：{measured_rms:.6f} {unit} RMS，相量解 {abs(expected):.6f} {unit} RMS；"
              f"相位 {phase:+.6f}°，相量解 {expected_phase:+.6f}°")
    load_power = rms(result, "v:load", start_time=STEADY_START, end_time=STOP_TIME)**2 / LOAD_RESISTANCE
    line_loss = RESISTANCE * rms(result, "i:LINE:series", start_time=STEADY_START, end_time=STOP_TIME)**2
    print(f"负载有功：{load_power:.6f} W；线路电阻损耗：{line_loss:.6f} W")


def define_case() -> CaseDefinition:
    """定义 π 型线路暂态算例。"""

    components = (
        VoltageSource("V1", "src", "0", source_voltage, derivative=source_voltage_derivative),
        PiLine("LINE", "src", "load", resistance=RESISTANCE, inductance=INDUCTANCE, capacitance=CAPACITANCE),
        Resistor("LOAD", "load", "0", LOAD_RESISTANCE),
    )

    config = SimulationConfig(
        time_step=TIME_STEP,
        stop_time=STOP_TIME,
        method="trapezoidal",
    )

    plots = (
        PlotSpec(
            columns=("v:src", "v:load"),
            figure_name="voltages.png",
            title="Pi line: sending and receiving voltages (V)",
        ),
        PlotSpec(
            columns=("i:LINE:series", "i:LINE:send_cap", "i:LINE:recv_cap"),
            figure_name="currents.png",
            title="Pi line: series and shunt capacitor currents (A)",
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
        summary=print_summary,
    )


def main() -> None:
    """按统一算例流程运行仿真。"""

    case = define_case()
    run_case(case)


if __name__ == "__main__":
    main()
