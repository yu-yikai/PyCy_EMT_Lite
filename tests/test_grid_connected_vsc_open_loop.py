"""Independent timing and circuit physics for the open-loop grid-connected VSC.

The gate oracle uses integer ticks and an integer triangle, not the example's
PWM helpers. The short electrical oracle eliminates the floating DC neutral
from the three identical R/L equations; no candidate stamps are reused.
"""

import json
import math
import runpy
from collections import Counter
from decimal import Decimal as D
from pathlib import Path

import numpy as np
import pytest

from pycy_emt_lite import Circuit, Inductor, Resistor, Simulator, VoltageSource
from pycy_emt_lite.components import IdealSwitch

ROOT = Path(__file__).resolve().parents[1]
CASE_DIR = ROOT / "validation/cases/grid_connected_vsc_open_loop"
PARAMETERS = json.loads((CASE_DIR / "parameters.json").read_text(encoding="utf-8"))
PROTOCOL = json.loads((CASE_DIR / "reference_protocol.json").read_text(encoding="utf-8"))
LIMITS = PROTOCOL["physical_residual_budgets"]
STEPS = (5e-6, 2.5e-6)
PHASES = ("a", "b", "c")
SHIFTS = np.array([0., -2 * np.pi / 3, 2 * np.pi / 3])
SHORT_STOP = .003


@pytest.fixture(scope="module")
def example():
    return runpy.run_path(str(ROOT / "examples/28_grid_connected_vsc_open_loop.py"))


def expected_upper(indices, step):
    """Frozen equations at integer gate/ref ticks, independently vectorized."""
    gate = np.asarray(indices) // round(PARAMETERS["gate_hold_s"] / step)
    held_time = (gate // 20) * PARAMETERS["reference_hold_s"]
    reference = PARAMETERS["modulation"] * np.clip(held_time / PARAMETERS["ramp_s"], 0, 1)[:, None] * np.sin(
        2 * np.pi * PARAMETERS["frequency_Hz"] * held_time[:, None] + SHIFTS - np.pi / 36,
    )
    carrier = np.abs(gate % 200 - 100) / 50 - 1
    return reference >= carrier[:, None]


def expected_source(time):
    time = np.asarray(time)
    return np.sqrt(2) * PARAMETERS["grid_phase_rms_V"] * np.clip(time / PARAMETERS["ramp_s"], 0, 1)[:, None] * np.sin(
        2 * np.pi * PARAMETERS["frequency_Hz"] * time[:, None] + SHIFTS,
    )


def switches(components):
    by_name = {part.name: part for part in components}
    return [by_name[f"S{phase}_{side}"] for phase in PHASES for side in ("upper", "lower")]


@pytest.fixture(scope="module", params=STEPS, ids=("5us", "2.5us"))
def gate_grid(request, example):
    step = request.param
    parts = example["create_components"](step)
    count = round(PARAMETERS["acquisition_stop_s"] / step) + 1
    actual = np.array([[switch.closed(k * step) for switch in switches(parts)] for k in range(count)])
    return step, parts, actual


def test_sixteen_components_and_frozen_directions(example):
    parts = example["create_components"]()
    assert Counter(type(part) for part in parts) == {VoltageSource: 4, Resistor: 3, Inductor: 3, IdealSwitch: 6}
    by_name = {part.name: part for part in parts}
    assert len(by_name) == len(parts) == 16
    dc = by_name["Vdc"]
    assert (dc.positive, dc.negative, dc.voltage) == ("dc_p", "dc_n", 400.)
    for phase in PHASES:
        source, resistor, inductor = (by_name[prefix + phase] for prefix in ("V", "R", "L"))
        assert (source.positive, source.negative) == (f"grid_{phase}", "0")
        assert (resistor.positive, resistor.negative, resistor.resistance) == (f"grid_{phase}", f"r_{phase}", 1.)
        assert (inductor.positive, inductor.negative, inductor.inductance, inductor.initial_current) == (
            f"r_{phase}", f"pole_{phase}", .01, 0.,
        )
        for side, endpoints in [("upper", ("dc_p", f"pole_{phase}")), ("lower", (f"pole_{phase}", "dc_n"))]:
            switch = by_name[f"S{phase}_{side}"]
            assert (switch.positive, switch.negative) == endpoints
            assert callable(switch.closed)
            assert (switch.closed_resistance, switch.open_conductance) == (.001, 1e-9)
    case = example["define_case"]()
    assert (case.config.time_step, case.config.stop_time, case.config.method) == (5e-6, .2, "trapezoidal")
    assert case.config.record_every == 1 and case.events == () and case.on_step is None
    for step in STEPS:
        validation = example["define_case"](time_step=step, stop_time=.200005)
        assert round(validation.config.stop_time / validation.config.time_step) + 1 == (40002 if step == 5e-6 else 80003)


def test_attached_gates_on_every_original_grid_point(gate_grid):
    step, parts, actual = gate_grid
    expected = expected_upper(np.arange(len(actual)), step)
    np.testing.assert_array_equal(actual[:, ::2], expected)
    np.testing.assert_array_equal(actual[:, 1::2], ~expected)
    np.testing.assert_array_equal(actual[0], [False, True] * 3)  # Upper000, lower111.
    assert actual.dtype == np.bool_
    assert all((part.last_current, part.last_state) == (0., False) for part in switches(parts))
    # Finite resistance is selected from the actual attached state and constants.
    resistance = np.column_stack([
        np.where(actual[:, k], switch.closed_resistance, float(D(1) / D(str(switch.open_conductance))))
        for k, switch in enumerate(switches(parts))
    ])
    assert np.isfinite(resistance).all()
    for switch in switches(parts):
        off_resistance = D(1) / D(str(switch.open_conductance))
        assert float(D(1) / off_resistance) == switch.open_conductance
    np.testing.assert_array_equal(resistance[:, ::2], np.where(expected, .001, 1e9))
    if step == 2.5e-6:
        np.testing.assert_array_equal(actual[1::2], actual[:-1:2])
        np.testing.assert_array_equal(actual[::2, ::2], expected_upper(np.arange(40002), 5e-6))


def test_attached_callbacks_are_pure_and_accept_only_the_declared_grid(gate_grid):
    step, parts, actual = gate_grid
    indices = [len(actual)-1, 51, 20, 0, 3999, 50, 19, 40, 1, 51]
    for k in indices:
        for j, switch in enumerate(switches(parts)):
            for time in [k * step, math.nextafter(k * step, math.inf)]:
                value = switch.closed(time)
                assert type(value) is bool and value == actual[k, j]
            if k:
                assert switch.closed(k * step - 1e-12) == actual[k, j]
                assert switch.closed(k * step + 1e-12) == actual[k, j]
    for time in [step/4, .001 + 3e-12, -step, math.nan, math.inf, True, "0"]:
        for switch in switches(parts):
            with pytest.raises(ValueError):
                switch.closed(time)


@pytest.mark.parametrize("step", STEPS)
def test_actual_callbacks_use_the_held_reference_function(example, monkeypatch, step):
    namespace = example["create_components"].__globals__
    original = namespace["held_reference"]
    calls = []

    def observed(held_time, shift):
        value = original(held_time, shift)
        calls.append((held_time, shift, value))
        return value

    monkeypatch.setitem(namespace, "held_reference", observed)
    parts = example["create_components"](step)
    for k in [0, 19, 20, 39, 40, 41, 8001]:
        calls.clear()
        for switch in switches(parts):
            switch.closed(k * step)
        assert len(calls) == 6
        held_time = ((k // round(5e-6/step)) // 20) * 100e-6
        for (actual_time, shift, value), expected_shift in zip(calls, np.repeat(SHIFTS, 2), strict=True):
            assert actual_time == held_time and shift == expected_shift
            expected = .85 * min(held_time/.02, 1) * np.sin(2*np.pi*60*held_time + expected_shift - np.pi/36)
            assert value == pytest.approx(expected, abs=1e-14)


@pytest.mark.parametrize("step", [1e-6, 1e-5, 0., -5e-6, math.nan, math.inf, True])
def test_unsupported_electrical_steps_are_rejected_before_construction(example, step):
    for create in [example["create_components"], example["define_case"]]:
        with pytest.raises(ValueError):
            create(time_step=step)


def test_grid_sources_are_continuous_and_keep_the_whole_phase_convention(example):
    parts = {part.name: part for part in example["create_components"]()}
    time = np.array([0., 12.34567e-6, 97.5e-6, 99.999e-6, .0199999, .02, .0200001, .1, .200005])
    expected = expected_source(time)
    actual = np.array([[parts["V" + phase].voltage(t) for phase in PHASES] for t in time])
    np.testing.assert_allclose(actual, expected, rtol=0, atol=2e-12)
    np.testing.assert_allclose(np.sum(actual, axis=1), 0, rtol=0, atol=2e-12)
    assert np.max(np.abs(actual[2]-actual[3])) > 1e-5  # No100us hold on the AC sources.


@pytest.fixture(scope="module", params=STEPS, ids=("5us", "2.5us"))
def short_run(request, example):
    step = request.param
    case = example["define_case"](time_step=step, stop_time=SHORT_STOP)
    result = Simulator(Circuit.from_components(case.name, case.components), case.config, events=case.events).run()
    data = {name: result.series(name) for name in result.columns}
    return step, data


def independent_currents(time, step):
    """L di/dt+(R+z)i=P(e-E), P=I-11'/3; exact discrete TR reduction."""
    upper = expected_upper(np.arange(len(time)), step)
    gon, goff = 1 / PARAMETERS["Ron_ohm"], PARAMETERS["Goff_S"]
    total = gon + goff
    bridge_emf = PARAMETERS["dc_V"] * np.where(upper, gon, goff) / total
    driving = expected_source(time) - bridge_emf
    driving -= np.mean(driving, axis=1)[:, None]
    alpha = 2 * PARAMETERS["L_H"] / step
    resistance = PARAMETERS["R_ohm"] + 1 / total
    current = np.zeros_like(driving)
    for k in range(1, len(time)):
        current[k] = ((alpha-resistance)*current[k-1] + driving[k] + driving[k-1]) / (alpha+resistance)
    return current


def test_short_electrical_solution_matches_independent_tr_reduction(short_run):
    step, data = short_run
    time = data["time"]
    assert len(time) == round(SHORT_STOP / step) + 1
    np.testing.assert_allclose(time, np.arange(len(time))*step, rtol=0, atol=2e-12)
    current = np.column_stack([data["i:L"+phase] for phase in PHASES])
    np.testing.assert_allclose(current, independent_currents(time, step), rtol=0,
                               atol=LIMITS["conditional_reduced_TR_current_A"])
    np.testing.assert_allclose(current[0], 0, rtol=0, atol=LIMITS["initial_phase_current_with_tokens_A"])
    leakage = -3 * 400 / (1e9 + .001)
    assert data["i:Vdc"][0] == pytest.approx(leakage, rel=0, abs=LIMITS["initial_DC_leakage_with_tokens_A"])
    for p, phase in enumerate(PHASES):
        np.testing.assert_allclose(data["i:R"+phase], current[:, p], rtol=0, atol=LIMITS["three_line_KCL_with_tokens_A"])
        for side, expected in [("upper", expected_upper(np.arange(len(time)), step)[:, p]),
                               ("lower", ~expected_upper(np.arange(len(time)), step)[:, p])]:
            np.testing.assert_array_equal(data[f"state:S{phase}_{side}"], expected)


def test_short_electrical_kcl_kvl_commonmode_and_tr_energy(short_run):
    step, data = short_run
    current = np.column_stack([data["i:L"+p] for p in PHASES])
    e = np.column_stack([data["v:grid_"+p] for p in PHASES])
    pole = np.column_stack([data["v:pole_"+p] for p in PHASES])
    vl = np.column_stack([data["v:L"+p] for p in PHASES])
    iu = np.column_stack([data[f"i:S{p}_upper"] for p in PHASES])
    il = np.column_stack([data[f"i:S{p}_lower"] for p in PHASES])
    assert np.max(np.abs(np.sum(current, axis=1))) <= LIMITS["three_line_KCL_with_tokens_A"]
    assert np.max(np.abs(current+iu-il)) <= LIMITS["pole_KCL_with_tokens_A"]
    assert np.max(np.abs(data["i:Vdc"]+np.sum(iu, axis=1))) <= LIMITS["DC_rail_KCL_with_tokens_A"]
    assert np.max(np.abs(e-current-vl-pole)) <= LIMITS["phase_KVL_with_tokens_V"]
    tr = .02/step*np.diff(current, axis=0) - vl[1:] - vl[:-1]
    assert np.max(np.abs(tr)) <= LIMITS["full_TR_with_tokens_V"]
    upper = expected_upper(np.arange(len(current)), step)
    total = 1000 + 1e-9
    emf = 400*np.where(upper, 1000, 1e-9)/total
    neutral = np.mean(e-emf-(1+1/total)*current, axis=1)
    assert np.max(np.abs(data["v:dc_n"]-neutral)) <= LIMITS["commonmode_with_tokens_V"]
    energy = .005*np.sum(current**2, axis=1)
    work = np.r_[0., np.cumsum(step/4*np.sum((vl[1:]+vl[:-1])*(current[1:]+current[:-1]), axis=1))]
    assert np.max(np.abs(energy-energy[0]-work)) <= LIMITS["prefix_TR_energy_with_tokens_J"]
    switch_power = np.sum((data["v:dc_p"][:, None]-pole)*iu+(pole-data["v:dc_n"][:, None])*il, axis=1)
    residual = 400*data["i:Vdc"] + np.sum(current**2+vl*current-e*current, axis=1) + switch_power
    assert np.max(np.abs(residual)) <= LIMITS["instantaneous_power_with_tokens_W"]
