"""演示单相双绕组变压器教学模型。

变压器一次侧接 50 Hz 交流电源，二次侧带电阻负载。`turns_ratio` 定义为
一次电压与二次电压之比 `Vp / Vs`；漏阻抗折算在一次侧，可选的励磁支路
并联在一次侧。`i:T1:primary` 只含漏阻抗/理想变比支路电流，不含励磁电流；
电源输入变压器的总电流为 `-i:V1`。二次电流正方向流入变压器，因此与负载电流反号。
零初值的理想励磁电感保留直流分量，不能只用正弦相量计算电源总电流 RMS。
"""

import math

import numpy as np

from pycy_emt_lite import Resistor, SimulationConfig, SinglePhaseTransformer, VoltageSource
from pycy_emt_lite.analysis import mean_value, rms
from pycy_emt_lite.cases import CaseDefinition, OutputOptions, PlotSpec, run_case
from pycy_emt_lite.io.results import SimulationResult

SAVE_RESULT_DATA = 0
SAVE_RESULT_FIGURE = 0
SHOW_FIGURE = True

FREQUENCY = 50.0
SOURCE_RMS = 230.0
TURNS_RATIO = 2.0             # 理想绕组变比，一次/二次
LEAKAGE_RESISTANCE = 0.5      # Ω，折算到一次侧
LEAKAGE_INDUCTANCE = 5e-3     # H，折算到一次侧
MAGNETIZING_INDUCTANCE = 1.0  # H，一次侧并联理想电感
LOAD_RESISTANCE = 50.0        # Ω
TIME_STEP = 1e-4              # s
STOP_TIME = 0.06              # s
STEADY_START = 0.02           # s，漏感暂态已衰减；励磁 DC 分量仍保留


def source_voltage(time: float) -> float:
    """返回一次侧电源瞬时电压（230 V 有效值、50 Hz 正弦）。"""

    return math.sqrt(2.0) * SOURCE_RMS * math.sin(2.0 * math.pi * FREQUENCY * time)


def print_summary(result: SimulationResult) -> None:
    """比较带载电压及电源总电流，并核对输入、负载和铜损功率。"""

    omega = 2.0 * math.pi * FREQUENCY
    primary_current = SOURCE_RMS / complex(
        LEAKAGE_RESISTANCE + TURNS_RATIO**2 * LOAD_RESISTANCE, omega * LEAKAGE_INDUCTANCE,
    )
    secondary_voltage = TURNS_RATIO * LOAD_RESISTANCE * primary_current
    magnetizing_current = SOURCE_RMS / (1j * omega * MAGNETIZING_INDUCTANCE)
    magnetizing_dc = math.sqrt(2.0) * abs(magnetizing_current)
    expected_input_rms = math.sqrt(abs(primary_current + magnetizing_current)**2 + magnetizing_dc**2)
    primary_rms = rms(result, "v:pri", start_time=STEADY_START, end_time=STOP_TIME)
    secondary_rms = rms(result, "v:sec", start_time=STEADY_START, end_time=STOP_TIME)
    input_rms = rms(result, "i:V1", start_time=STEADY_START, end_time=STOP_TIME)
    measured_dc = mean_value(result, "i:T1:magnetizing", start_time=STEADY_START, end_time=STOP_TIME)
    print(f"统计窗口：{STEADY_START:g}–{STOP_TIME:g} s；保留零初值励磁电流的直流分量。")
    print(f"二次电压：{secondary_rms:.6f} V RMS，相量解 {abs(secondary_voltage):.6f} V RMS；"
          f"带载端电压比 {primary_rms / secondary_rms:.6f}，理想绕组变比 {TURNS_RATIO:g}")
    print(f"电源总电流：{input_rms:.6f} A RMS，含直流分量的解析值 {expected_input_rms:.6f} A RMS")
    print(f"励磁电流均值：{measured_dc:.6f} A，解析值 {magnetizing_dc:.6f} A")

    time = result.series("time")
    window = (time >= STEADY_START) & (time <= STOP_TIME)
    time = time[window]
    voltage = result.series("v:pri")[window]
    current = -result.series("i:V1")[window]
    # 按两条分段线性信号的乘积积分，与 RMS 的重建约定一致。
    input_power = np.sum(np.diff(time) * (
        2 * voltage[:-1] * current[:-1] + voltage[:-1] * current[1:]
        + voltage[1:] * current[:-1] + 2 * voltage[1:] * current[1:]
    ) / 6.0) / (time[-1] - time[0])
    load_power = secondary_rms**2 / LOAD_RESISTANCE
    copper_loss = LEAKAGE_RESISTANCE * rms(result, "i:T1:primary", start_time=STEADY_START, end_time=STOP_TIME)**2
    print(f"输入有功：{input_power:.6f} W；负载有功：{load_power:.6f} W；铜损：{copper_loss:.6f} W；"
          f"平衡残差 {input_power - load_power - copper_loss:.2e} W")


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
            turns_ratio=TURNS_RATIO,
            leakage_resistance=LEAKAGE_RESISTANCE,
            leakage_inductance=LEAKAGE_INDUCTANCE,
            magnetizing_inductance=MAGNETIZING_INDUCTANCE,
        ),
        Resistor("LOAD", "sec", "0", LOAD_RESISTANCE),
    )

    config = SimulationConfig(
        time_step=TIME_STEP,
        stop_time=STOP_TIME,
        method="trapezoidal",
    )

    plots = (
        PlotSpec(
            columns=("v:pri", "v:sec"),
            figure_name="voltages.png",
            title="Transformer: primary and secondary voltages (V)",
        ),
        PlotSpec(
            columns=("i:T1:primary", "i:T1:secondary", "i:T1:magnetizing"),
            figure_name="currents.png",
            title="Transformer: winding and magnetizing currents (A)",
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
        summary=print_summary,
    )


def main() -> None:
    """按统一算例流程运行仿真。"""

    case = define_case()
    run_case(case)


if __name__ == "__main__":
    main()
