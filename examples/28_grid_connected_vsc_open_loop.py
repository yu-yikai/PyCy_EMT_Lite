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

from pycy_emt_lite import SimulationConfig
from pycy_emt_lite.analysis import peak_abs
from pycy_emt_lite.cases import CaseDefinition, OutputOptions, PlotSpec, run_case
from pycy_emt_lite.components.base import Component
from pycy_emt_lite.controls import carrier_compare, triangular_carrier
from pycy_emt_lite.converters import _grid_vsc
from pycy_emt_lite.converters._grid_vsc import checked_time_step as _checked_time_step
from pycy_emt_lite.converters._grid_vsc import electrical_index as _electrical_index
from pycy_emt_lite.io.results import SimulationResult

SAVE_RESULT_DATA = 0
SAVE_RESULT_FIGURE = 0
SHOW_FIGURE = True

DC_VOLTAGE = _grid_vsc.DC_VOLTAGE
GRID_PHASE_RMS_VOLTAGE = _grid_vsc.GRID_PHASE_RMS_VOLTAGE
FREQUENCY = _grid_vsc.FREQUENCY
RAMP_TIME = _grid_vsc.RAMP_TIME
RESISTANCE = _grid_vsc.RESISTANCE
INDUCTANCE = _grid_vsc.INDUCTANCE
SWITCH_ON_RESISTANCE = _grid_vsc.SWITCH_ON_RESISTANCE
SWITCH_OFF_CONDUCTANCE = _grid_vsc.SWITCH_OFF_CONDUCTANCE
MODULATION_INDEX = 0.85
DELTA_DEGREES = -5.0               # 调制参考相对于同相电网的相角
SWITCHING_FREQUENCY = 1000.0        # Hz
CARRIER_TIME_SHIFT = -0.0005       # s，首拍载波为+1
REFERENCE_HOLD_TIME = 100e-6        # s
GATE_HOLD_TIME = 5e-6               # s
TIME_STEP = _grid_vsc.TIME_STEP
FINE_TIME_STEP = _grid_vsc.FINE_TIME_STEP
STOP_TIME = 0.2                    # s；验证采集尾点另传stop_time=0.200005
GRID_TIME_TOLERANCE = _grid_vsc.GRID_TIME_TOLERANCE
PHASE_SHIFTS = _grid_vsc.PHASE_SHIFTS.copy()


def phase_voltage(phase_shift: float) -> Callable[[float], float]:
    """交流源使用连续时间，不能用保持后的调制时刻替代。"""
    return _grid_vsc.phase_voltage(
        phase_shift, rms_voltage=GRID_PHASE_RMS_VOLTAGE, frequency=FREQUENCY, ramp_time=RAMP_TIME,
    )


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

    def gate_pair(phase: str) -> tuple[Callable[[float], bool], Callable[[float], bool]]:
        upper = upper_switch_closed(PHASE_SHIFTS[phase], time_step)
        return upper, lower_switch_closed(upper)

    return _grid_vsc.create_bridge(
        gate_pair, make_phase_voltage=phase_voltage, phase_shifts=PHASE_SHIFTS,
        dc_voltage=DC_VOLTAGE, resistance=RESISTANCE, inductance=INDUCTANCE,
        closed_resistance=SWITCH_ON_RESISTANCE, open_conductance=SWITCH_OFF_CONDUCTANCE,
    )


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
