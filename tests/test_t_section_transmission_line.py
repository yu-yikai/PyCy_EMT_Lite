"""Independent finite-T state response, KCL, work balance and refinement.

The analytic oracle is not a vendor result. Its physical equations are built
from an incidence matrix and 101 independent states, not production stamps.
"""

import runpy
from dataclasses import replace
from itertools import pairwise
from pathlib import Path

import numpy as np
import pytest
from scipy.linalg import expm

from pycy_emt_lite import Capacitor, Circuit, Inductor, Resistor, Simulator

EXAMPLE = Path(__file__).resolve().parents[1] / "examples/22_t_section_transmission_line.py"
SECTIONS = 50
IMPEDANCE_SCALE = 50.0
NS = 1e-9


def independent_generator():
    """Use the frozen physical protocol, independently of candidate constants.

    State = [50 capacitor voltages, 51 rightward currents * 50 ohm,
             sin(omega*t), cos(omega*t)], and the time unit is ns.
    """
    incidence = np.zeros((SECTIONS, SECTIONS + 1))
    for row in range(SECTIONS):
        incidence[row, row] = 1
        incidence[row, row + 1] = -1
    inductance = np.full(SECTIONS + 1, 25e-9)
    inductance[[0, -1]] /= 2
    resistance = np.full(SECTIONS + 1, 0.00067)
    resistance[[0, -1]] /= 2
    resistance[-1] += 50  # Actual resistive termination, no source resistance.
    generator = np.zeros((103, 103))
    generator[:50, :50] = -np.eye(50) * (0.5e-6 / 10e-12)
    generator[:50, 50:101] = incidence / (10e-12 * IMPEDANCE_SCALE)
    generator[50:101, :50] = -IMPEDANCE_SCALE * incidence.T / inductance[:, None]
    generator[50:101, 50:101] = -np.diag(resistance / inductance)
    generator[50, 101] = IMPEDANCE_SCALE * 10 / inductance[0]
    omega = 2 * np.pi * 200e6
    generator[101, 102], generator[102, 101] = omega, -omega
    return generator * NS


def exact_states(time):
    step = time[1] - time[0]
    assert time[0] == 0
    assert np.max(np.abs(np.diff(time) - step)) < 1e-20
    propagator = expm(independent_generator() * (step / NS))
    state = np.zeros(103)
    state[-1] = 1
    states = np.empty((len(time), 103))
    for index in range(len(time)):
        states[index] = state
        state = propagator @ state
    # Independently verify the exact input oscillator survived propagation.
    assert np.max(np.abs(states[:, -2] - np.sin(2 * np.pi * 200e6 * time))) < 1e-10
    return states[:, :50], states[:, 50:101] / IMPEDANCE_SCALE


def simulate(step=10e-12, method="trapezoidal"):
    case = runpy.run_path(str(EXAMPLE))["define_case"]()
    result = Simulator(Circuit.from_components(case.name, case.components),
                       replace(case.config, time_step=step, method=method)).run()
    # Retain compact arrays rather than six full multi-million-value result
    # dictionaries during the refinement study.
    return {
        "time": result.series("time"),
        "capacitor_voltage": np.column_stack([result.series(f"v:C{k}") for k in range(1, 51)]),
        "capacitor_current": np.column_stack([result.series(f"i:C{k}") for k in range(1, 51)]),
        "left_current": np.column_stack([result.series(f"i:L{k}_left") for k in range(1, 51)]),
        "right_current": np.column_stack([result.series(f"i:L{k}_right") for k in range(1, 51)]),
        "boundary_voltage": np.column_stack([result.series(f"v:n{k}") for k in (0, 15, 25, 50)]),
        "source_current": result.series("i:Vs"),
        "load_current": result.series("i:Rload"),
    }


@pytest.fixture(scope="module")
def baseline():
    return simulate()


def output_errors(data):
    capacitor_voltage, current = exact_states(data["time"])
    expected_voltage = np.column_stack((10 * np.sin(2 * np.pi * 200e6 * data["time"]),
                                       (capacitor_voltage[:, 14] + capacitor_voltage[:, 15]) / 2,
                                       (capacitor_voltage[:, 24] + capacitor_voltage[:, 25]) / 2,
                                       50 * current[:, -1]))
    voltage_error = float(np.max(np.abs(data["boundary_voltage"] - expected_voltage)))
    current_error = float(max(np.max(np.abs(data["left_current"][:, 0] - current[:, 0])),
                              np.max(np.abs(data["load_current"] - current[:, -1]))))
    return voltage_error, current_error


def test_original_fifty_t_topology_parameters_and_zero_initial_storage():
    case = runpy.run_path(str(EXAMPLE))["define_case"]()
    inductors = [item for item in case.components if isinstance(item, Inductor)]
    capacitors = [item for item in case.components if isinstance(item, Capacitor)]
    resistors = [item for item in case.components if isinstance(item, Resistor)]
    assert len(inductors) == 100 and len(capacitors) == 50 and len(resistors) == 151
    assert all(item.inductance == pytest.approx(12.5e-9) and item.initial_current == 0 for item in inductors)
    assert all(item.capacitance == pytest.approx(10e-12) and item.initial_voltage == 0 for item in capacitors)
    assert case.config.linear_solver_mode == "reuse"
    assert case.config.time_step == 10e-12 and case.config.stop_time == 50e-9
    assert not case.events


@pytest.mark.parametrize("frequency", [1e6, 200e6, 400e6])
def test_state_frequency_response_matches_independent_exact_t_abcd(frequency):
    impedance = 0.00067 + 2j * np.pi * frequency * 25e-9
    admittance = 0.5e-6 + 2j * np.pi * frequency * 10e-12
    cell = np.array([[1 + impedance * admittance / 2, impedance * (1 + impedance * admittance / 4)],
                     [admittance, 1 + impedance * admittance / 2]])
    assert np.linalg.det(cell) == pytest.approx(1, abs=1e-14)
    chain = np.linalg.matrix_power(cell, 50)
    transfer_abcd = 1 / (chain[0, 0] + chain[0, 1] / 50)
    generator = independent_generator()
    response = np.linalg.solve(2j * np.pi * frequency * NS * np.eye(101) - generator[:101, :101],
                               generator[:101, 101] / 10)
    transfer_state = response[100] * 50 / IMPEDANCE_SCALE
    assert transfer_state == pytest.approx(transfer_abcd, rel=1e-11, abs=1e-11)


@pytest.mark.slow
def test_all_storage_states_exact_transient_kcl_and_physical_directions(baseline):
    data = baseline
    expected_v, expected_i = exact_states(data["time"])
    assert np.max(np.abs(data["capacitor_voltage"] - expected_v)) < 0.05
    assert np.max(np.abs(data["left_current"] - expected_i[:, :-1])) < 0.001
    assert np.max(np.abs(data["right_current"] - expected_i[:, 1:])) < 0.001
    voltage_error, current_error = output_errors(data)
    assert voltage_error < 0.05 and current_error < 0.001
    assert np.max(np.abs(data["capacitor_voltage"][0])) == 0
    assert np.max(np.abs(data["left_current"][0])) == 0
    assert np.max(np.abs(data["right_current"][0])) == 0
    kcl = (data["left_current"] - data["right_current"] - data["capacitor_current"]
           - data["capacitor_voltage"] / 2e6)
    assert np.max(np.abs(kcl)) < 1e-8
    assert np.max(np.abs(data["left_current"][:, 1:] - data["right_current"][:, :-1])) < 1e-8
    assert np.max(np.abs(data["source_current"] + data["left_current"][:, 0])) < 1e-8
    assert np.max(np.abs(data["load_current"] - data["right_current"][:, -1])) < 1e-8
    assert np.max(np.abs(data["boundary_voltage"][:, -1] / 50 - data["load_current"])) < 1e-12
    assert data["left_current"][1, 0] > 0  # Initially rising source drives current rightward.


def square_work(values, time):
    return np.diff(time) * np.sum(values[:-1] ** 2 + values[:-1] * values[1:] + values[1:] ** 2, axis=1) / 3


@pytest.mark.slow
def test_stored_energy_source_work_and_positive_dissipative_losses(baseline):
    data = baseline
    time, v = data["time"], data["capacitor_voltage"]
    arms = np.column_stack((data["left_current"], data["right_current"]))
    source_v, source_i = data["boundary_voltage"][:, 0], data["left_current"][:, 0]
    load_i = data["load_current"]
    stored = 0.5 * 10e-12 * np.sum(v**2, axis=1) + 0.5 * 12.5e-9 * np.sum(arms**2, axis=1)
    loss = (0.000335 * square_work(arms, time) + square_work(v, time) / 2e6
            + 50 * square_work(load_i[:, None], time))
    source_work = np.diff(time) * (2 * source_v[:-1] * source_i[:-1] + source_v[:-1] * source_i[1:]
                                  + source_v[1:] * source_i[:-1] + 2 * source_v[1:] * source_i[1:]) / 6
    scale = max(np.max(stored), np.sum(np.abs(source_work)), np.sum(loss))
    assert scale > 0 and np.min(stored) >= 0 and np.min(loss) >= 0
    balance = stored[1:] - stored[0] + np.cumsum(loss - source_work)
    assert np.max(np.abs(balance)) / scale < 0.005

    # TR's exact discrete energy identity uses products of endpoint means,
    # not the trapezoid of sampled instantaneous powers.
    mid_v = (v[:-1] + v[1:]) / 2
    mid_arms = (arms[:-1] + arms[1:]) / 2
    midpoint_net_power = ((source_v[:-1] + source_v[1:]) * (source_i[:-1] + source_i[1:]) / 4
                          - 0.000335 * np.sum(mid_arms**2, axis=1) - np.sum(mid_v**2, axis=1) / 2e6
                          - 50 * ((load_i[:-1] + load_i[1:]) / 2) ** 2)
    assert np.max(np.abs(np.diff(stored) - np.diff(time) * midpoint_net_power)) / scale < 1e-8


@pytest.mark.slow
def test_trapezoidal_twenty_ten_five_picosecond_refinement(baseline):
    errors = []
    for step in (20e-12, 10e-12, 5e-12):
        data = baseline if step == 10e-12 else simulate(step)
        v_error, i_error = output_errors(data)
        errors.append(max(v_error / 10, i_error / 0.2))
    assert all(left / right >= 3 for left, right in pairwise(errors)), errors


@pytest.mark.slow
def test_backward_euler_first_order_demonstration_against_exact_transient():
    errors = []
    for step in (20e-12, 10e-12, 5e-12):
        data = simulate(step, "backward_euler")
        v_error, i_error = output_errors(data)
        errors.append(max(v_error / 10, i_error / 0.2))
    assert all(1.7 < left / right < 2.3 for left, right in pairwise(errors)), errors
