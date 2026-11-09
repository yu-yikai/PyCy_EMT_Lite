"""有限电阻 Bergeron 线路：波前、反射与电阻损耗。

运行：uv run python examples/27_finite_r_bergeron_line.py

Vdc--Rs--send--25Ω--B1(150µs)--50Ω--B2(150µs)--25Ω--recv--Rload--0

两段B1/B2均为Z=201Ω的无损延时线，attenuation=1；总线路电阻100Ω
由三个现有Resistor明确表示，不能用一个衰减系数替代。源在0.5–0.6ms
从0升至1000V，全部负时间端口历史为0，1µs固定步长运行到6ms。
先看300µs传播，再看源端、中心电阻和负载反射的叠加与最终直流值。

send/recv是完整线路的外端口。i:Rs为送端流入，i:Rload为收端流出；
BergeronLine的receiving电流则指向该半线内部，与向右链流方向相反。
冻结参数、PSCAD参考范围及验收见validation/cases/finite_r_bergeron。
"""

from pycy_emt_lite import Resistor, SimulationConfig, VoltageSource
from pycy_emt_lite.cases import CaseDefinition, OutputOptions, PlotSpec, run_case
from pycy_emt_lite.components import BergeronLine
from pycy_emt_lite.components.base import Component
from pycy_emt_lite.io.results import SimulationResult

SAVE_RESULT_DATA = 0
SAVE_RESULT_FIGURE = 0
SHOW_FIGURE = True

SOURCE_FINAL_VOLTAGE = 1000.0     # V
RAMP_START_TIME = 500e-6         # s
RAMP_END_TIME = 600e-6           # s
RAMP_DURATION = RAMP_END_TIME - RAMP_START_TIME  # s
SOURCE_RESISTANCE = 100.0       # ohm
LOAD_RESISTANCE = 400.0         # ohm
LINE_RESISTANCE = 100.0         # ohm, split R/4 + R/2 + R/4
SURGE_IMPEDANCE = 201.0         # ohm, for each lossless half-line
TRAVEL_TIME = 300e-6            # s, total one-way propagation
TIME_STEP = 1e-6                # s, 150 steps per half-line
STOP_TIME = 6e-3                # s


def source_voltage(time: float) -> float:
    """源电压先为零，再线性上升，最后保持。"""
    if time <= RAMP_START_TIME:
        return 0.0
    if time >= RAMP_END_TIME:
        return SOURCE_FINAL_VOLTAGE
    return SOURCE_FINAL_VOLTAGE * (time - RAMP_START_TIME) / RAMP_DURATION


def create_components() -> tuple[Component, ...]:
    """从左到右组网；每次返回新元件，半线历史由现有实现从零开始。"""
    return (
        VoltageSource("Vdc", "src", "0", source_voltage),
        Resistor("Rs", "src", "send", SOURCE_RESISTANCE),
        Resistor("Rleft", "send", "line1_send", LINE_RESISTANCE / 4),
        BergeronLine("B1", "line1_send", "line1_recv", SURGE_IMPEDANCE,
                     TRAVEL_TIME / 2, attenuation=1.0),
        Resistor("Rmiddle", "line1_recv", "line2_send", LINE_RESISTANCE / 2),
        BergeronLine("B2", "line2_send", "line2_recv", SURGE_IMPEDANCE,
                     TRAVEL_TIME / 2, attenuation=1.0),
        Resistor("Rright", "line2_recv", "recv", LINE_RESISTANCE / 4),
        Resistor("Rload", "recv", "0", LOAD_RESISTANCE),
    )


def print_summary(result: SimulationResult) -> None:
    """把传播时间和最终直流关系放在实际运行读数旁边。"""
    time = result.series("time")
    receiving = result.series("v:recv")
    first = next((t for t, v in zip(time, receiving, strict=True) if abs(v) > 1e-9), None)
    print(f"线路R={LINE_RESISTANCE:g}Ω分为25/50/25Ω；两半线Z={SURGE_IMPEDANCE:g}Ω，"
          f"各延迟{TRAVEL_TIME / 2e-6:g}µs，attenuation=1。")
    if first is not None:
        print(f"收端首个非零采样：{first * 1e3:.3f}ms；默认源首个非零采样0.501ms，"
              "单程传播0.300ms。")
    dc_current = SOURCE_FINAL_VOLTAGE / (SOURCE_RESISTANCE + LINE_RESISTANCE + LOAD_RESISTANCE)
    print(f"末点：Vk={result.series('v:send')[-1]:.6f}V，Vm={receiving[-1]:.6f}V，"
          f"Ik={result.series('i:Rs')[-1]:.6f}A，Im_out={result.series('i:Rload')[-1]:.6f}A。")
    print(f"直流极限：I={dc_current:.6f}A，Vk={SOURCE_FINAL_VOLTAGE - SOURCE_RESISTANCE * dc_current:.6f}V，"
          f"Vm={LOAD_RESISTANCE * dc_current:.6f}V。暂态两端电流因行波储能而不同。")


def define_case() -> CaseDefinition:
    plots = (
        PlotSpec(("v:src", "v:send", "v:recv"), "voltages.png",
                 title="Finite-R Bergeron line: source and terminal voltages (V)"),
        PlotSpec(("i:Rs", "i:Rload"), "currents.png",
                 title="Sending input and receiving output currents (A)"),
    )
    return CaseDefinition(
        name="finite_r_bergeron", components=create_components(),
        config=SimulationConfig(TIME_STEP, STOP_TIME, method="trapezoidal", linear_solver_mode="reuse"),
        events=(), plots=plots, summary=print_summary,
        output=OutputOptions(save_data=bool(SAVE_RESULT_DATA), save_figure=bool(SAVE_RESULT_FIGURE),
                             show_figure=SHOW_FIGURE),
    )


def main() -> None:
    run_case(define_case())


if __name__ == "__main__":
    main()
