"""并网VSC开环：观察电网、串联R/L与浮置直流桥之间的电流。

三相120V RMS、60Hz电网在20ms内升压，经1Ω/10mH接入六开关桥；
400V直流源跨接dc_p/dc_n，两条直流轨均不接地。交流电流以电网流向桥为正，
i:Vdc以dc_p流向dc_n为正，表示直流源吸收电流。

参考幅值和相角每100µs更新，比较得到的互补门极每5µs更新并保持。
电气步长可选5µs或2.5µs，细网格中点沿用上一门极拍，不重新比较载波。
这是固定调制的开环例子；参数、方向及真实参考见
validation/cases/grid_connected_vsc_open_loop。
"""

import math
from collections.abc import Callable
from numbers import Real

from pycy_emt_lite import Inductor, Resistor, SimulationConfig, VoltageSource
from pycy_emt_lite.analysis import peak_abs
from pycy_emt_lite.cases import CaseDefinition, OutputOptions, PlotSpec, run_case
from pycy_emt_lite.components import IdealSwitch
from pycy_emt_lite.components.base import Component
from pycy_emt_lite.controls import carrier_compare, triangular_carrier
from pycy_emt_lite.io.results import SimulationResult

SAVE_RESULT_DATA = 0
SAVE_RESULT_FIGURE = 0
SHOW_FIGURE = True

DC_VOLTAGE = 400.0                 # V，浮置理想直流源
GRID_PHASE_RMS_VOLTAGE = 120.0      # V，相电压有效值
FREQUENCY = 60.0                   # Hz
RAMP_TIME = 0.02                   # s，交流源与调制参考均从零升幅
RESISTANCE = 1.0                   # ohm，每相串联电阻
INDUCTANCE = 0.01                  # H，每相电感，初始电流为零
SWITCH_ON_RESISTANCE = 1e-3         # ohm
SWITCH_OFF_CONDUCTANCE = 1e-9       # S，保留实际关断漏流
MODULATION_INDEX = 0.85
DELTA_DEGREES = -5.0               # 调制参考相对于同相电网的相角
SWITCHING_FREQUENCY = 1000.0        # Hz
CARRIER_TIME_SHIFT = -0.0005       # s，首拍载波为+1
REFERENCE_HOLD_TIME = 100e-6        # s
GATE_HOLD_TIME = 5e-6               # s
TIME_STEP = 5e-6                   # s，默认电气步长
FINE_TIME_STEP = 2.5e-6             # s，用于同一输入下的细化验证
STOP_TIME = 0.2                    # s；验证采集尾点另传stop_time=0.200005
GRID_TIME_TOLERANCE = 2e-12         # s，只容纳支持网格的浮点表示误差
PHASE_SHIFTS = {"a": 0.0, "b": -2 * math.pi / 3, "c": 2 * math.pi / 3}


def _checked_time_step(time_step: float) -> float:
    if isinstance(time_step, bool) or not isinstance(time_step, Real) or time_step not in (TIME_STEP, FINE_TIME_STEP):
        raise ValueError("本例电气步长仅支持5µs或2.5µs；其他步长需要另行验证。")
    return float(time_step)


def _electrical_index(time: float, time_step: float) -> int:
    """先核实际时间，再使用整数拍号，避免浮点floor在边界错一拍。"""
    if isinstance(time, bool) or not isinstance(time, Real) or not math.isfinite(time) or time < 0:
        raise ValueError("门极时间必须为支持网格上的有限非负实数。")
    ratio = time / time_step
    if not math.isfinite(ratio):
        raise ValueError("门极时间超出可表示的电气网格。")
    index = round(ratio)
    if abs(time - index * time_step) > GRID_TIME_TOLERANCE:
        raise ValueError("门极时间偏离本例电气网格超过2ps。")
    return index


def phase_voltage(phase_shift: float) -> Callable[[float], float]:
    """交流源使用连续时间，不能用保持后的调制时刻替代。"""
    def voltage(time: float) -> float:
        ramp = min(max(time / RAMP_TIME, 0.0), 1.0)
        return math.sqrt(2) * GRID_PHASE_RMS_VOLTAGE * ramp * math.sin(2 * math.pi * FREQUENCY * time + phase_shift)

    return voltage


def held_reference(reference_time: float, phase_shift: float) -> float:
    """在已经保持的100µs参考时刻，同时计算幅值斜坡与相角。"""
    ramp = min(max(reference_time / RAMP_TIME, 0.0), 1.0)
    angle = 2 * math.pi * FREQUENCY * reference_time + phase_shift + math.radians(DELTA_DEGREES)
    return MODULATION_INDEX * ramp * math.sin(angle)


def upper_switch_closed(phase_shift: float, time_step: float) -> Callable[[float], bool]:
    time_step = _checked_time_step(time_step)
    electrical_steps_per_gate = round(GATE_HOLD_TIME / time_step)
    gate_steps_per_reference = round(REFERENCE_HOLD_TIME / GATE_HOLD_TIME)

    def gate(time: float) -> bool:
        electrical_index = _electrical_index(time, time_step)
        gate_index = electrical_index // electrical_steps_per_gate
        reference_index = gate_index // gate_steps_per_reference
        reference = held_reference(reference_index * REFERENCE_HOLD_TIME, phase_shift)
        gate_time = gate_index * GATE_HOLD_TIME
        carrier = triangular_carrier(gate_time + CARRIER_TIME_SHIFT, SWITCHING_FREQUENCY)
        return bool(carrier_compare(reference, carrier))

    return gate


def lower_switch_closed(upper_gate: Callable[[float], bool]) -> Callable[[float], bool]:
    """互补下管使用同一个纯上管函数，无状态、无调用顺序依赖。"""
    def gate(time: float) -> bool:
        return not upper_gate(time)

    return gate


def create_components(time_step: float = TIME_STEP) -> tuple[Component, ...]:
    """16个元件：浮置DC源，三相源/R/L与上下桥臂；不添加测量支路。"""
    time_step = _checked_time_step(time_step)
    components: list[Component] = [VoltageSource("Vdc", "dc_p", "dc_n", DC_VOLTAGE)]
    for phase, shift in PHASE_SHIFTS.items():
        grid, resistor_out, pole = f"grid_{phase}", f"r_{phase}", f"pole_{phase}"
        upper_gate = upper_switch_closed(shift, time_step)
        components.extend((
            VoltageSource(f"V{phase}", grid, "0", phase_voltage(shift)),
            Resistor(f"R{phase}", grid, resistor_out, RESISTANCE),
            Inductor(f"L{phase}", resistor_out, pole, INDUCTANCE, initial_current=0.0),
            IdealSwitch(f"S{phase}_upper", "dc_p", pole, upper_gate,
                        closed_resistance=SWITCH_ON_RESISTANCE, open_conductance=SWITCH_OFF_CONDUCTANCE),
            IdealSwitch(f"S{phase}_lower", pole, "dc_n", lower_switch_closed(upper_gate),
                        closed_resistance=SWITCH_ON_RESISTANCE, open_conductance=SWITCH_OFF_CONDUCTANCE),
        ))
    return tuple(components)


def print_summary(result: SimulationResult) -> None:
    print(f"并网VSC开环：电气步长{result.time_step * 1e6:g}µs，参考保持100µs，门极保持5µs。")
    print("交流电流以电网流向桥为正；i:Vdc以dc_p流向dc_n为正，表示直流源吸收电流。")
    for phase in PHASE_SHIFTS:
        print(f"{phase.upper()}相电流峰值：{peak_abs(result, f'i:L{phase}'):.6f}A。")
    rail_voltage = result.series("v:dc_p")[-1] - result.series("v:dc_n")[-1]
    print(f"末点直流端电压：{rail_voltage:.6f}V；直流源电流：{result.series('i:Vdc')[-1]:.6f}A。")


def define_case(*, time_step: float = TIME_STEP, stop_time: float = STOP_TIME) -> CaseDefinition:
    """默认运行0.2s；验证入口可保留到0.200005s的采集尾点。"""
    time_step = _checked_time_step(time_step)
    return CaseDefinition(
        name="grid_connected_vsc_open_loop", components=create_components(time_step),
        config=SimulationConfig(time_step, stop_time, method="trapezoidal", linear_solver_mode="reuse",
                                event_time_policy="require_aligned"),
        plots=(
            PlotSpec(("i:La", "i:Lb", "i:Lc"), "currents.png", kind="three_phase",
                     title="Grid-to-bridge phase currents (A)"),
            PlotSpec(("v:grid_a", "v:pole_a"), "phase_a_voltages.png", title="Grid and bridge pole A (V)"),
            PlotSpec(("v:dc_p", "v:dc_n"), "dc_rails.png", title="Floating DC rails relative to ground (V)"),
        ),
        output=OutputOptions(save_data=bool(SAVE_RESULT_DATA), save_figure=bool(SAVE_RESULT_FIGURE),
                             show_figure=SHOW_FIGURE), summary=print_summary,
    )


def main() -> None:
    run_case(define_case())


if __name__ == "__main__":
    main()
