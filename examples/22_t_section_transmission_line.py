"""50段对称T线路：耦合、启动传播和集中参数色散。

从仓库根运行：uv run python examples/22_t_section_transmission_line.py

第k段：n(k-1)--R_left--L_left--c(k)--L_right--R_right--n(k)
                                    |
                             C 与 R_shunt 并联
                                    |
                                    0

总长5m、每段0.1m。源10V峰值/200MHz正弦，无串阻，终端50Ω。
全部电感电流与电容电压初值0；50ns内观察完整启动瞬态。
串臂电流一律向右，shunt和负载电流流向地。n15/n25是段右端口，
与电容中点c15/c25不同。原官方绘图把第15段错标成25，参考映射已核定。

25ns是连续线路的名义时间尺度，有限50T梯级存在色散及小反射，
不能把它当作纯延时或Bergeron线路。对应真实参考、独立状态解和验收
在validation/cases/transmission_line；修改参数后原参考验收不再适用。
"""

import math

import numpy as np

from pycy_emt_lite import Capacitor, Inductor, Resistor, SimulationConfig, VoltageSource
from pycy_emt_lite.cases import CaseDefinition, OutputOptions, PlotSpec, run_case
from pycy_emt_lite.io.results import SimulationResult

SAVE_RESULT_DATA = 0
SAVE_RESULT_FIGURE = 0
SHOW_FIGURE = True

NUMBER_OF_SECTIONS = 50
SECTION_LENGTH = 0.1             # m
RESISTANCE_PER_METRE = 0.0067     # ohm/m
INDUCTANCE_PER_METRE = 250e-9    # H/m
CAPACITANCE_PER_METRE = 100e-12  # F/m
CONDUCTANCE_PER_METRE = 5e-6     # S/m
SOURCE_PEAK_VOLTAGE = 10.0
SOURCE_FREQUENCY = 200e6         # Hz
LOAD_RESISTANCE = 50.0           # ohm
TIME_STEP = 10e-12               # s
STOP_TIME = 50e-9                # s


def create_components() -> tuple:
    """逐段保留左右两个电感；使用现有R/L/C，不修改线路核心。"""
    half_r = RESISTANCE_PER_METRE * SECTION_LENGTH / 2
    half_l = INDUCTANCE_PER_METRE * SECTION_LENGTH / 2
    shunt_c = CAPACITANCE_PER_METRE * SECTION_LENGTH
    shunt_r = 1 / (CONDUCTANCE_PER_METRE * SECTION_LENGTH)
    components = [VoltageSource("Vs", "n0", "0", lambda time: SOURCE_PEAK_VOLTAGE * math.sin(
        2 * math.pi * SOURCE_FREQUENCY * time,
    ))]
    for section in range(1, NUMBER_OF_SECTIONS + 1):
        left, center, right = f"n{section - 1}", f"c{section}", f"n{section}"
        components.extend((
            Resistor(f"R{section}_left", left, f"r{section}_left", half_r),
            Inductor(f"L{section}_left", f"r{section}_left", center, half_l, initial_current=0),
            Inductor(f"L{section}_right", center, f"l{section}_right", half_l, initial_current=0),
            Resistor(f"R{section}_right", f"l{section}_right", right, half_r),
            Capacitor(f"C{section}", center, "0", shunt_c, initial_voltage=0),
            Resistor(f"R{section}_shunt", center, "0", shunt_r),
        ))
    components.append(Resistor("Rload", f"n{NUMBER_OF_SECTIONS}", "0", LOAD_RESISTANCE))
    return tuple(components)


def print_summary(result: SimulationResult) -> None:
    """区分名义连续线路尺度与本例有限T梯级响应。"""
    nominal_delay = NUMBER_OF_SECTIONS * SECTION_LENGTH * math.sqrt(
        INDUCTANCE_PER_METRE * CAPACITANCE_PER_METRE,
    )
    print(f"{NUMBER_OF_SECTIONS}个T段，零初值启动；步长{TIME_STEP / 1e-12:g}ps，"
          f"窗口{STOP_TIME / 1e-9:g}ns。")
    print(f"连续线路名义单程尺度：{nominal_delay / 1e-9:g}ns；有限T梯级存在色散，非纯延时。")
    for boundary in (15, 25, NUMBER_OF_SECTIONS):
        print(f"n{boundary}右端口电压峰值：{np.max(np.abs(result.series(f'v:n{boundary}'))):.6f}V")
    print(f"负载电流峰值：{np.max(np.abs(result.series('i:Rload'))):.6f}A；正方向n50→地。")


def define_case() -> CaseDefinition:
    config = SimulationConfig(TIME_STEP, STOP_TIME, method="trapezoidal", linear_solver_mode="reuse")
    plots = (
        PlotSpec(columns=("v:n0", "v:n15", "v:n25", "v:n50"), figure_name="voltages.png",
                 kind="series", title="Finite 50-T line: boundary voltages (V)"),
        PlotSpec(columns=("i:L1_left", "i:Rload"), figure_name="currents.png",
                 kind="series", title="Source-to-line and load currents (A)"),
    )
    return CaseDefinition(
        name="t_section_transmission_line", components=create_components(), config=config,
        events=(), plots=plots,
        output=OutputOptions(save_data=bool(SAVE_RESULT_DATA), save_figure=bool(SAVE_RESULT_FIGURE),
                             show_figure=SHOW_FIGURE),
        summary=print_summary,
    )


def main() -> None:
    run_case(define_case())


if __name__ == "__main__":
    main()
