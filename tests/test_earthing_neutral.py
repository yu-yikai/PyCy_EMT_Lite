"""Independent weighted-neutral KCL, power and right-side resistor events."""

import math
import runpy
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from pycy_emt_lite import Circuit, SimulationConfig, Simulator


@pytest.fixture
def example():
    return runpy.run_path(str(Path(__file__).resolve().parents[1] / "examples/21_earthing_neutral.py"))


def analytic_values(times, a_change=0.05, c_change=0.07):
    """Eliminate the floating node independently; no model stamp or transform."""
    angles = 2 * math.pi * 60 * times[:, None] + np.array([0, -2 * math.pi / 3, 2 * math.pi / 3])
    source = 100 * np.sin(angles)
    resistance = np.column_stack((np.where(times >= a_change, 3.0, 1.0),
                                  np.ones(len(times)), np.where(times >= c_change, 1.5, 1.0)))
    neutral = np.sum(source / resistance, axis=1) / np.sum(1 / resistance, axis=1)
    return source, resistance, neutral


@pytest.mark.parametrize("method", ["trapezoidal", "backward_euler"])
@pytest.mark.parametrize("solver_mode", ["rebuild", "reuse"])
def test_piecewise_phase_voltages_currents_kcl_and_power(example, method, solver_mode):
    case = example["define_case"]()
    result = Simulator(Circuit.from_components(case.name, case.components),
                       replace(case.config, method=method, linear_solver_mode=solver_mode),
                       events=case.events, on_step=case.on_step).run()
    time = result.series("time")
    voltage, resistance, neutral = analytic_values(time)
    np.testing.assert_allclose(result.series("v:floating:n"), neutral, rtol=0, atol=1e-10)
    for group, prefix, source_name, load_voltage in (("grounded", "Rg", "Vg", voltage),
                                                  ("floating", "Rf", "Vf", voltage - neutral[:, None])):
        actual_voltage = np.column_stack([result.series(f"v:{group}:{phase}") for phase in "abc"])
        current = np.column_stack([result.series(f"i:{prefix}:{phase}") for phase in "abc"])
        source_current = np.column_stack([result.series(f"i:{source_name}:{phase}") for phase in "abc"])
        np.testing.assert_allclose(actual_voltage, voltage, rtol=0, atol=1e-10)
        np.testing.assert_allclose(current, load_voltage / resistance, rtol=0, atol=1e-10)
        np.testing.assert_allclose(source_current + current, 0, rtol=0, atol=1e-11)
        losses = np.sum(resistance * current**2, axis=1)
        source_absorbed_power = np.sum(actual_voltage * source_current, axis=1)
        np.testing.assert_allclose(losses + source_absorbed_power, 0, rtol=0, atol=1e-8)
        assert np.all(losses > 0)
        if group == "floating":
            measured = np.column_stack([result.series(f"v:floating_load:{phase}") for phase in "abc"])
            np.testing.assert_allclose(measured, load_voltage, rtol=0, atol=1e-10)
            np.testing.assert_allclose(np.sum(current, axis=1), 0, rtol=0, atol=1e-10)
        else:
            returning = np.sum(current, axis=1)
            np.testing.assert_allclose(result.series("i:grounded:return"), returning, rtol=0, atol=1e-11)
            assert np.max(np.abs(returning[time < 0.05])) < 1e-10
            assert np.max(np.abs(returning[time > 0.05])) > 20
    assert [record["time"] for record in result.event_log] == [0.05, 0.05, 0.07, 0.07]
    assert [record["target"] for record in result.event_log] == ["Rg:a", "Rf:a", "Rg:c", "Rf:c"]
    assert [record["before"] for record in result.event_log] == [1.0] * 4
    assert [record["after"] for record in result.event_log] == [3.0, 3.0, 1.5, 1.5]
    assert len(time) == 1001


@pytest.mark.parametrize("a_change,c_change", [(0.05, 0.07), (0.05005, 0.07005)])
def test_load_events_store_one_right_side_row_with_exact_algebraic_jump(example, a_change, c_change):
    case = example["define_case"]()
    events = tuple(replace(event, time=a_change if event.target.endswith(":a") else c_change)
                   for event in case.events)
    result = Simulator(Circuit.from_components(case.name, case.components),
                       SimulationConfig(1e-4, 0.1), events=events, on_step=case.on_step).run()
    times = result.series("time")
    assert np.all(np.diff(times) > 0)
    for event_time in (a_change, c_change):
        assert np.count_nonzero(times == event_time) == 1
        row = result.rows[int(np.flatnonzero(times == event_time)[0])]
        voltage, resistance, neutral = analytic_values(np.array([event_time]), a_change, c_change)
        assert row["v:floating:n"] == pytest.approx(neutral[0], abs=1e-10)
        for index, phase in enumerate("abc"):
            assert row[f"i:Rg:{phase}"] == pytest.approx(voltage[0, index] / resistance[0, index], abs=1e-10)
            assert row[f"i:Rf:{phase}"] == pytest.approx((voltage[0, index] - neutral[0]) / resistance[0, index], abs=1e-10)
    # At C's change, finite algebraic voltage/current jump is required: no storage to freeze.
    voltage, before_r, before_n = analytic_values(np.array([c_change]), a_change, c_change + 1)
    before_c = (voltage[0, 2] - before_n[0]) / before_r[0, 2]
    # With Ra=3, Rb=1, Rc:1->1.5, the new conductance sum is 2 S.
    # Delta-vn=(-1/3 S)*(vc-vn_before)/(2 S)=-i_c_before/6;
    # i_c_after=(7/9)*i_c_before. These identities avoid a phase-dependent jump bound.
    assert abs(before_c) > 1
    assert row["v:floating:n"] - before_n[0] == pytest.approx(-before_c / 6, abs=1e-10)
    assert row["i:Rf:c"] - before_c == pytest.approx(-2 * before_c / 9, abs=1e-10)


@pytest.mark.parametrize("resistance", [0, -1, math.nan, True])
def test_invalid_resistance_event_fails_before_any_solve(example, resistance):
    case = example["define_case"]()
    simulator = Simulator(Circuit.from_components(case.name, case.components), case.config,
                          events=[example["ResistanceChangeEvent"](0.05, "Rf:a", resistance=resistance)])
    with pytest.raises(ValueError, match="resistance.*有限正实数"):
        simulator.run()
    assert simulator.last_time is None
    assert simulator.solver.solve_count == 0


def test_resistance_event_rejects_source_target_without_mutation(example):
    case = example["define_case"]()
    simulator = Simulator(Circuit.from_components(case.name, case.components), case.config,
                          events=[example["ResistanceChangeEvent"](0.05, "Vg", resistance=3.0)])
    with pytest.raises(ValueError, match="Vg.*Resistor"):
        simulator.run()
    assert simulator.solver.solve_count == 0
