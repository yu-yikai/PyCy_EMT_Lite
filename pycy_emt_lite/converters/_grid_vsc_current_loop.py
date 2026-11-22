"""并网 VSC 闭环算例共用的电流控制与门极时序。"""

import math
from collections.abc import Callable, Mapping

from pycy_emt_lite.components.base import Component
from pycy_emt_lite.controls import (
    SRFPLL,
    PIController,
    abc_to_dq,
    carrier_compare,
    dq_to_abc,
    triangular_carrier,
)
from pycy_emt_lite.converters import _grid_vsc
from pycy_emt_lite.core.simulation import StepCallback

CONTROL_PERIOD = 100e-6
GATE_PERIOD = 5e-6
SWITCHING_FREQUENCY = 1000.0
CARRIER_TIME_SHIFT = -0.0005  # 首拍载波为 +1
CURRENT_BANDWIDTH = 100.0  # Hz
HALF_DC_VOLTAGE = _grid_vsc.DC_VOLTAGE / 2
VOLTAGE_LIMIT = 0.95 * HALF_DC_VOLTAGE
GRID_ANGULAR_FREQUENCY = 2 * math.pi * _grid_vsc.FREQUENCY
PHASES = tuple(_grid_vsc.PHASE_SHIFTS)

# 参数为求解结果行、整数电气拍和推进至该行的同步角。
ReferenceCallback = Callable[[Mapping[str, float], int, float], tuple[tuple[float, float], Mapping[str, float]]]


def create_current_loop(
    time_step: float, *, scenario: str = "main", pll: SRFPLL | None = None,
    feeder: tuple[float, float] | None = None, reference: ReferenceCallback | None = None,
) -> tuple[tuple[Component, ...], StepCallback]:
    """给桥接线装上电流控制，并可接入求解后执行的外环参考。"""
    steps_per_gate = round(GATE_PERIOD / time_step)
    steps_per_sample = round(CONTROL_PERIOD / time_step)
    d_step = round(0.04 / time_step)
    q_step = round(0.08 / time_step)

    bandwidth = 2 * math.pi * CURRENT_BANDWIDTH
    resistance, inductance = _grid_vsc.RESISTANCE, _grid_vsc.INDUCTANCE
    if feeder is not None:
        resistance += feeder[0]
        inductance += feeder[1]
    cross_coupling = GRID_ANGULAR_FREQUENCY * inductance
    d_pi = PIController(inductance * bandwidth, resistance * bandwidth)
    q_pi = PIController(inductance * bandwidth, resistance * bandwidth)
    previous = pending = (0.0, 0.0, 0.0)
    last_sample_tick = 0
    id_ref = iq_ref = 0.0
    saturated = False
    angle_error = 0.0
    if pll is not None:
        angle_error = math.degrees(math.remainder(pll.angle + math.pi / 2, math.tau))

    def applied_reference(gate_tick: int) -> tuple[float, float, float]:
        # 在采样所在的门极拍内，仍然使用刚才求解所用的指令。
        return pending if gate_tick > last_sample_tick else previous

    def carrier_at(gate_tick: int) -> float:
        return triangular_carrier(gate_tick * GATE_PERIOD + CARRIER_TIME_SHIFT, SWITCHING_FREQUENCY)

    def gate_pair(phase: str) -> tuple[Callable[[float], bool], Callable[[float], bool]]:
        phase_index = PHASES.index(phase)

        def upper(time: float) -> bool:
            gate_tick = _grid_vsc.electrical_index(time, time_step) // steps_per_gate
            reference = applied_reference(gate_tick)[phase_index]
            return bool(carrier_compare(reference, carrier_at(gate_tick)))

        def lower(time: float) -> bool:
            return not upper(time)

        return upper, lower

    def observe(row: Mapping[str, float]) -> Mapping[str, float]:
        nonlocal previous, pending, last_sample_tick, id_ref, iq_ref, saturated, angle_error
        time = row["time"]
        index = _grid_vsc.electrical_index(time, time_step)
        gate_tick = index // steps_per_gate
        applied = applied_reference(gate_tick)
        sample_update = index > 0 and index % steps_per_sample == 0

        grid_angle = GRID_ANGULAR_FREQUENCY * time - math.pi / 2
        grid_voltage = row["v:grid_a"], row["v:grid_b"], row["v:grid_c"]
        pll_error = 0.0
        if pll is not None and sample_update:
            # PLL 与电流控制使用同一电气采样行。两次采样之间保持角度。
            if abs(pll.frequency * CONTROL_PERIOD) >= math.pi:
                raise ValueError("PLL 一次采样的角度增量必须小于半周。")
            state = pll.step(grid_voltage, CONTROL_PERIOD)
            theta = state.angle
            ed, eq = state.d_axis_voltage, state.q_axis_voltage
            pll_error = eq / max(abs(ed), abs(eq), 1.0)
            angle_error = math.degrees(math.remainder(theta - grid_angle, math.tau))
        else:
            theta = grid_angle if pll is None else pll.angle
            ed, eq = abc_to_dq(*grid_voltage, theta)

        requested = None
        reference_measurements: Mapping[str, float] = {}
        if reference is not None:
            row_angle = theta
            if pll is not None:
                row_angle += pll.frequency * (index % steps_per_sample) * time_step
            requested, reference_measurements = reference(row, index, row_angle)
        id_, iq = abc_to_dq(row["i:La"], row["i:Lb"], row["i:Lc"], theta)
        if sample_update:
            previous, last_sample_tick = applied, gate_tick
            if requested is None:
                id_ref = 2.0 if index >= d_step else 0.0
                iq_ref = 1.5 if scenario == "main" and index >= q_step else 0.0
            else:
                id_ref, iq_ref = requested
            integrators = d_pi.integrator, q_pi.integrator
            ud = d_pi.step(id_ref - id_, CONTROL_PERIOD)
            uq = q_pi.step(iq_ref - iq, CONTROL_PERIOD)
            vd = ed + cross_coupling * iq - ud
            vq = eq - cross_coupling * id_ - uq
            magnitude = math.hypot(vd, vq)
            saturated = magnitude > VOLTAGE_LIMIT
            if saturated:
                # 限幅改变了电压矢量，保留两个电流积分器的上次状态。
                scale = VOLTAGE_LIMIT / magnitude
                vd *= scale
                vq *= scale
                d_pi.integrator, q_pi.integrator = integrators
            va, vb, vc = dq_to_abc(vd, vq, theta)
            pending = va / HALF_DC_VOLTAGE, vb / HALF_DC_VOLTAGE, vc / HALF_DC_VOLTAGE

        measurements = {
            "j": float(index),
            "sample_update": float(sample_update),
            "gate_tick": float(gate_tick),
            "theta": theta,
            "ed": ed, "eq": eq,
            "id": id_, "iq": iq,
            "id_ref": id_ref, "iq_ref": iq_ref,
            "carrier_applied": carrier_at(gate_tick),
            "saturated": float(saturated),
            "z_d": d_pi.integrator, "z_q": q_pi.integrator,
            **{f"applied_{phase}": value for phase, value in zip(PHASES, applied, strict=True)},
            **{f"pending_{phase}": value for phase, value in zip(PHASES, pending, strict=True)},
            **reference_measurements,
        }
        if pll is not None:
            measurements.update({
                "pll_omega": pll.frequency,
                "pll_xi": pll.integrator,
                "pll_error": pll_error,
                "pll_angle_error_deg": angle_error,
                "pll_frequency_hz": pll.frequency / math.tau,
                "grid_frequency_hz": _grid_vsc.FREQUENCY,
            })
        return measurements

    return _grid_vsc.create_bridge(gate_pair, feeder=feeder), observe
