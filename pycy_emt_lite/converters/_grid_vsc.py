"""并网 VSC 教学算例共用的物理接线和电气时钟。"""

import math
from collections.abc import Callable, Mapping
from numbers import Real

from pycy_emt_lite.components import IdealSwitch, Inductor, Resistor, VoltageSource
from pycy_emt_lite.components.base import Component

DC_VOLTAGE = 400.0
GRID_PHASE_RMS_VOLTAGE = 120.0
FREQUENCY = 60.0
RAMP_TIME = 0.02
RESISTANCE = 1.0
INDUCTANCE = 0.01
SWITCH_ON_RESISTANCE = 1e-3
SWITCH_OFF_CONDUCTANCE = 1e-9
PHASE_SHIFTS = {"a": 0.0, "b": -2 * math.pi / 3, "c": 2 * math.pi / 3}
TIME_STEP = 5e-6
FINE_TIME_STEP = 2.5e-6
GRID_TIME_TOLERANCE = 2e-12


def checked_time_step(time_step: float) -> float:
    if (isinstance(time_step, bool) or not isinstance(time_step, Real)
            or time_step not in (TIME_STEP, FINE_TIME_STEP)):
        raise ValueError("本例电气步长仅支持5µs或2.5µs；其他步长需要另行验证。")
    return float(time_step)


def electrical_index(time: float, time_step: float) -> int:
    """先核对时间，再取整数拍，避免浮点 floor 在边界错一拍。"""
    if isinstance(time, bool) or not isinstance(time, Real) or not math.isfinite(time) or time < 0:
        raise ValueError("门极时间必须为支持网格上的有限非负实数。")
    ratio = time / time_step
    if not math.isfinite(ratio):
        raise ValueError("门极时间超出可表示的电气网格。")
    index = round(ratio)
    if abs(time - index * time_step) > GRID_TIME_TOLERANCE:
        raise ValueError("门极时间偏离本例电气网格超过2ps。")
    return index


def phase_voltage(
    phase_shift: float,
    *,
    rms_voltage: float = GRID_PHASE_RMS_VOLTAGE,
    frequency: float = FREQUENCY,
    ramp_time: float = RAMP_TIME,
) -> Callable[[float], float]:
    """交流源使用连续时间，升压斜坡和相角均不经过控制保持。"""

    def voltage(time: float) -> float:
        ramp = min(max(time / ramp_time, 0.0), 1.0)
        angle = 2 * math.pi * frequency * time + phase_shift
        return math.sqrt(2) * rms_voltage * ramp * math.sin(angle)

    return voltage


def create_bridge(
    gate_pair: Callable[[str], tuple[Callable[[float], bool], Callable[[float], bool]]],
    *,
    make_phase_voltage: Callable[[float], Callable[[float], float]] = phase_voltage,
    phase_shifts: Mapping[str, float] = PHASE_SHIFTS,
    dc_voltage: float = DC_VOLTAGE,
    resistance: float = RESISTANCE,
    inductance: float = INDUCTANCE,
    closed_resistance: float = SWITCH_ON_RESISTANCE,
    open_conductance: float = SWITCH_OFF_CONDUCTANCE,
    feeder: tuple[float, float] | None = None,
) -> tuple[Component, ...]:
    """浮置直流源、三相源/R/L 与六开关，可在原滤波器前串接馈线。"""
    components: list[Component] = [VoltageSource("Vdc", "dc_p", "dc_n", dc_voltage)]
    for phase, shift in phase_shifts.items():
        grid, resistor_out, pole = f"grid_{phase}", f"r_{phase}", f"pole_{phase}"
        upper, lower = gate_pair(phase)
        components.append(VoltageSource(f"V{phase}", grid, "0", make_phase_voltage(shift)))
        pcc = grid
        if feeder is not None:
            pcc, feeder_midpoint = f"pcc_{phase}", f"rg_out_{phase}"
            feeder_resistance, feeder_inductance = feeder
            components.extend((
                Resistor(f"Rg{phase}", grid, feeder_midpoint, feeder_resistance),
                Inductor(f"Lg{phase}", feeder_midpoint, pcc, feeder_inductance, initial_current=0.0),
            ))
        components.extend((
            Resistor(f"R{phase}", pcc, resistor_out, resistance),
            Inductor(f"L{phase}", resistor_out, pole, inductance, initial_current=0.0),
            IdealSwitch(f"S{phase}_upper", "dc_p", pole, upper,
                        closed_resistance=closed_resistance, open_conductance=open_conductance),
            IdealSwitch(f"S{phase}_lower", pole, "dc_n", lower,
                        closed_resistance=closed_resistance, open_conductance=open_conductance),
        ))
    return tuple(components)
