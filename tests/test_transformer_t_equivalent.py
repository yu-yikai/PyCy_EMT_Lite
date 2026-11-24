"""Independent two-state solution and conservation for the external-T model."""

import runpy
from dataclasses import replace
from itertools import pairwise
from pathlib import Path

import numpy as np
import pytest

from pycy_emt_lite import Circuit, Inductor, Simulator, SinglePhaseTransformer

EXAMPLE = Path(__file__).resolve().parents[1] / "examples/23_transformer_t_equivalent.py"
MATRIX = np.array([[0.11, -0.5], [-0.5, 2.75]])


def exact_solution(time, step_time=2.0):
    # Spectral matrix exponential of the independent physical inductance
    # matrix. Both external resistances are 1 ohm in the frozen protocol.
    eigenvalues, vectors = np.linalg.eigh(MATRIX)
    elapsed = np.maximum(time - step_time, 0)
    steady = np.array([1.0, 0.0])
    state = steady - (np.exp(-elapsed[:, None] / eigenvalues) * (vectors.T @ steady)) @ vectors.T
    state[time <= step_time] = 0
    source = (time >= step_time).astype(float)
    derivative = np.linalg.solve(MATRIX, np.column_stack((source - state[:, 0], -state[:, 1])).T).T
    magnetizing = state[:, 0] - state[:, 1] / 0.2
    primary_voltage = 0.1 * (derivative[:, 0] - derivative[:, 1] / 0.2)
    return state, magnetizing, primary_voltage


def simulate(step=0.001, event_time=2.0, stop=8.0):
    case = runpy.run_path(str(EXAMPLE))["define_case"]()
    event = replace(case.events[0], time=event_time)
    return Simulator(Circuit.from_components(case.name, case.components),
                     replace(case.config, time_step=step, stop_time=stop), events=(event,)).run()


@pytest.fixture(scope="module")
def baseline():
    return simulate()


def test_physical_t_topology_and_passive_independent_state_matrix():
    case = runpy.run_path(str(EXAMPLE))["define_case"]()
    inductors = {item.name: item for item in case.components if isinstance(item, Inductor)}
    assert set(inductors) == {"L1", "L2", "Lm"}
    assert (inductors["Lm"].positive, inductors["Lm"].negative) == ("core_p", "0")
    assert all(item.initial_current == 0 for item in inductors.values())
    ideal = next(item for item in case.components if isinstance(item, SinglePhaseTransformer))
    assert (ideal.primary_positive, ideal.secondary_positive) == ("core_p", "sec_p")
    assert ideal.turns_ratio == 0.2
    assert ideal.leakage_resistance == ideal.leakage_inductance == 0
    assert ideal.magnetizing_inductance is None and ideal.core_loss_resistance is None
    assert np.linalg.eigvalsh(MATRIX)[0] > 0
    assert np.linalg.det(MATRIX) == pytest.approx(0.0525)


def test_three_currents_and_core_voltages_against_full_exact_transient(baseline):
    result = baseline
    state, magnetizing, primary_voltage = exact_solution(result.series("time"))
    assert np.max(np.abs(result.series("i:L1") - state[:, 0])) < 0.001
    assert np.max(np.abs(result.series("i:L2") - state[:, 1])) < 0.0002
    assert np.max(np.abs(result.series("i:Lm") - magnetizing)) < 0.001
    assert np.max(np.abs(result.series("v:core_p") - primary_voltage)) < 0.005
    assert np.max(np.abs(result.series("v:sec_p") - primary_voltage / 0.2)) < 0.025
    for column in ("i:L1", "i:L2", "i:Lm"):
        assert result.series(column)[0] == 0
    assert result.series("i:L2")[-1] == pytest.approx(0.02143977807836, abs=1e-7)
    assert result.series("i:L1")[-1] == pytest.approx(0.9960754915414, abs=1e-7)


def test_ideal_turns_ratio_winding_power_and_magnetizing_kcl(baseline):
    result = baseline
    source_i, load_i, magnetizing_i = (result.series(name) for name in ("i:L1", "i:L2", "i:Lm"))
    primary_i, secondary_i = result.series("i:T1:primary"), result.series("i:T1:secondary")
    primary_v, secondary_v = result.series("v:core_p"), result.series("v:sec_p")
    assert np.max(np.abs(source_i - magnetizing_i - load_i / 0.2)) < 1e-9
    assert np.max(np.abs(primary_i - load_i / 0.2)) < 1e-9
    assert np.max(np.abs(secondary_i + load_i)) < 1e-9
    assert np.max(np.abs(result.series("i:V1") + source_i)) < 1e-9
    assert np.max(np.abs(primary_v - 0.2 * secondary_v)) < 1e-11
    assert np.max(np.abs(primary_v * primary_i + secondary_v * secondary_i)) < 1e-11
    assert np.max(np.abs(result.series("v:load") - load_i)) < 1e-12  # Rload = 1 ohm.


def test_explicit_step_preserves_currents_and_solves_unique_right_side_voltage(baseline):
    result = baseline
    time = result.series("time")
    edge = np.flatnonzero(time == 2.0)
    assert len(edge) == 1
    index = edge[0]
    assert len(result.event_log) == 1
    assert result.event_log[0]["time"] == 2
    assert result.event_log[0]["before"] == 0 and result.event_log[0]["after"] == 1
    assert result.series("v:src")[index - 1] == 0 and result.series("v:src")[index] == 1
    for name in ("i:L1", "i:L2", "i:Lm"):
        assert result.series(name)[index - 1] == 0
        assert result.series(name)[index] == 0
        assert result.series(name)[index + 1] > 0
    assert result.series("v:core_p")[index - 1] == 0
    assert result.series("v:core_p")[index] == pytest.approx(10 / 21, abs=1e-11)
    assert result.series("v:sec_p")[index] == pytest.approx(50 / 21, abs=1e-11)
    assert result.series("v:load")[index] == 0


def test_storage_plus_external_resistor_loss_matches_source_work(baseline):
    result = baseline
    time, source_v = result.series("time"), result.series("v:src")
    source_i, load_i, magnetizing_i = (result.series(name) for name in ("i:L1", "i:L2", "i:Lm"))
    stored = 0.5 * (0.01 * source_i**2 + 0.25 * load_i**2 + 0.1 * magnetizing_i**2)
    state = np.column_stack((source_i, load_i))
    assert np.max(np.abs(stored - 0.5 * np.sum(state * (state @ MATRIX.T), axis=1))) < 1e-15
    # The row at the event is right-sided. Recover the left source at the
    # interval ending there before integrating source work.
    left_source = source_v[1:].copy()
    for event in result.event_log:
        index = np.flatnonzero(time == event["time"])[0]
        left_source[index - 1] = event["before"]
    work = np.diff(time) * (2 * source_v[:-1] * source_i[:-1] + source_v[:-1] * source_i[1:]
                           + left_source * source_i[:-1] + 2 * left_source * source_i[1:]) / 6
    loss = np.zeros_like(work)
    for current in (source_i, load_i):
        loss += np.diff(time) * (current[:-1] ** 2 + current[:-1] * current[1:] + current[1:] ** 2) / 3
    assert np.min(loss) >= 0 and np.min(stored) >= 0
    scale = max(np.max(stored), np.sum(np.abs(work)), np.sum(loss))
    assert np.max(np.abs(stored[1:] - stored[0] + np.cumsum(loss - work))) / scale < 0.001
    midpoint_source_i = (source_i[:-1] + source_i[1:]) / 2
    midpoint_load_i = (load_i[:-1] + load_i[1:]) / 2
    midpoint_work = np.diff(time) * ((source_v[:-1] + left_source) / 2 * midpoint_source_i
                                   - midpoint_source_i**2 - midpoint_load_i**2)
    assert np.max(np.abs(np.diff(stored) - midpoint_work)) / scale < 1e-11


def test_two_one_half_millisecond_trapezoidal_refinement(baseline):
    errors = []
    for step in (0.002, 0.001, 0.0005):
        result = baseline if step == 0.001 else simulate(step)
        state, magnetizing, _ = exact_solution(result.series("time"))
        errors.append(float(max(np.max(np.abs(result.series("i:L1") - state[:, 0])),
                                np.max(np.abs(result.series("i:L2") - state[:, 1])),
                                np.max(np.abs(result.series("i:Lm") - magnetizing)))))
    assert all(left / right >= 3 for left, right in pairwise(errors)), errors


def test_off_grid_step_is_inserted_without_smearing_current_initialization():
    edge_time = 0.0205
    result = simulate(event_time=edge_time, stop=0.1)
    time = result.series("time")
    assert len(np.flatnonzero(time == edge_time)) == 1
    edge = np.flatnonzero(time == edge_time)[0]
    assert result.event_log[0]["time"] == edge_time
    assert result.series("i:L1")[edge] == result.series("i:L2")[edge] == result.series("i:Lm")[edge] == 0
    state, _, _ = exact_solution(time, step_time=edge_time)
    assert np.max(np.abs(result.series("i:L1") - state[:, 0])) < 0.001
    assert np.max(np.abs(result.series("i:L2") - state[:, 1])) < 0.0002


def test_finite_eight_second_response_is_distinct_from_asymptotic_dc_limit(baseline):
    eigenvalues = np.linalg.eigvalsh(MATRIX)
    peak_after_step = np.prod(eigenvalues) / np.diff(eigenvalues)[0] * np.log(eigenvalues[1] / eigenvalues[0])
    state, _, _ = exact_solution(np.array([2 + peak_after_step, 8.0, 1000.0]))
    assert state[0, 1] == pytest.approx(0.1702573183845)
    assert state[1, 1] > 0.02  # Finite 8 s record still carries load current.
    assert state[-1] == pytest.approx([1, 0], abs=1e-14)
    peak = np.argmax(baseline.series("i:L2"))
    assert abs(baseline.series("time")[peak] - (2 + peak_after_step)) < 0.0011
