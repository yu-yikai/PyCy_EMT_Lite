"""单相交流电压源驱动串联 RLC，观察启动暂态与正弦稳态。

接线：V1 正端 src -> R1 -> n1 -> L1 -> out -> C1 -> 地 0；V1 负端接地。
电流正方向沿 R1、L1、C1 流向地。电源参数用有效值，波形函数返回瞬时值。
电容电压和电感电流从零开始；最后两个周期用 Z = R + j(wL - 1/wC)
核对电流有效值与相对电源的相位。正相位表示电流超前电压。
"""

import math

import numpy as np

from pycy_emt_lite import Capacitor, Inductor, Resistor, SimulationConfig, VoltageSource
from pycy_emt_lite.analysis import rms
from pycy_emt_lite.cases import CaseDefinition, OutputOptions, PlotSpec, run_case
from pycy_emt_lite.io.results import SimulationResult

SAVE_RESULT_DATA = 0
SAVE_RESULT_FIGURE = 0
SHOW_FIGURE = True

SOURCE_RMS = 220.0       # V
FREQUENCY = 50.0         # Hz
INITIAL_PHASE = 0.0      # rad
RESISTANCE = 20.0        # ohm
INDUCTANCE = 50e-3       # H
CAPACITANCE = 100e-6     # F
TIME_STEP = 20e-6        # s，每个工频周期 1000 步
STOP_TIME = 0.12         # s
STEADY_START = 0.08      # s，默认参数的启动暂态已衰减


def source_voltage(time: float) -> float:
    """VoltageSource 接收函数本身，每个时刻调用它取得瞬时电压。"""

    return math.sqrt(2.0) * SOURCE_RMS * math.sin(2.0 * math.pi * FREQUENCY * time + INITIAL_PHASE)


def print_summary(result: SimulationResult) -> None:
    """比较完整周期窗口内的有效值、基波相位与交流阻抗解析值。"""

    omega = 2.0 * math.pi * FREQUENCY
    impedance = complex(RESISTANCE, omega * INDUCTANCE - 1.0 / (omega * CAPACITANCE))
    expected_rms = SOURCE_RMS / abs(impedance)
    expected_phase = -math.degrees(math.atan2(impedance.imag, impedance.real))
    measured_rms = rms(result, "i:L1", start_time=STEADY_START, end_time=STOP_TIME)
    source_rms = rms(result, "v:src", start_time=STEADY_START, end_time=STOP_TIME)

    # 用整周期的正弦/余弦投影读出相对于电源的基波相位。
    time = result.series("time")
    window = (time >= STEADY_START) & (time <= STOP_TIME)
    time = time[window]
    current = result.series("i:L1")[window]
    angle = omega * time + INITIAL_PHASE
    sine = np.trapezoid(current * np.sin(angle), time)
    cosine = np.trapezoid(current * np.cos(angle), time)
    measured_phase = math.degrees(math.atan2(cosine, sine))

    print(f"稳态统计窗口：{STEADY_START:g}–{STOP_TIME:g} s")
    print(f"电源有效值：{source_rms:.6f} V，设定值 {SOURCE_RMS:.6f} V")
    print(f"电流有效值：{measured_rms:.6f} A，阻抗解析值 {expected_rms:.6f} A")
    print(f"电流相对电源相位：{measured_phase:+.6f}°，解析值 {expected_phase:+.6f}°（正值超前）")


def define_case() -> CaseDefinition:
    """用已有基础元件定义单相交流串联 RLC。"""

    components = (
        VoltageSource("V1", "src", "0", source_voltage),
        Resistor("R1", "src", "n1", RESISTANCE),
        Inductor("L1", "n1", "out", INDUCTANCE, initial_current=0.0),
        Capacitor("C1", "out", "0", CAPACITANCE, initial_voltage=0.0),
    )
    config = SimulationConfig(time_step=TIME_STEP, stop_time=STOP_TIME, method="trapezoidal")
    plots = (
        PlotSpec(
            columns=("v:src", "v:L1", "v:C1"),
            figure_name="voltages.png",
            title="Single-phase AC series RLC: voltages (V)",
        ),
        PlotSpec(
            columns=("i:L1",),
            figure_name="current.png",
            title="Single-phase AC series RLC: current (A)",
        ),
    )
    output = OutputOptions(
        save_data=bool(SAVE_RESULT_DATA),
        save_figure=bool(SAVE_RESULT_FIGURE),
        show_figure=SHOW_FIGURE,
    )
    return CaseDefinition(
        name="single_phase_ac_rlc", components=components, config=config,
        plots=plots, output=output, summary=print_summary,
    )


def main() -> None:
    """按统一算例流程运行仿真。"""

    case = define_case()
    run_case(case)


if __name__ == "__main__":
    main()
