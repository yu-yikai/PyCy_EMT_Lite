"""Buck physics and sampled-control timing, independent of commercial data.

The two-state oracle eliminates the midpoint voltage using KCL. It does not use
production stamps, reference CSVs or a fitted PWM phase. Switching energy uses
the trapezoidal endpoint identity, including the endpoint power covariance.
"""

import runpy
from dataclasses import replace
from fractions import Fraction
from pathlib import Path

import numpy as np
import pytest
from scipy.linalg import expm

from pycy_emt_lite import Capacitor, Circuit, CurrentSource, Inductor, Simulator
from pycy_emt_lite.components import IdealSwitch

EXAMPLE = runpy.run_path(str(Path(__file__).resolve().parents[1] / "examples/26_synchronous_buck.py"))
L, C, R = 1e-3, 22e-6, 3.75
SNUBBER_G, PARALLEL_G = 1e-5, 1e-4


def simulate(step=50e-9, stop=10e-3):
    case = EXAMPLE["define_case"]()
    return Simulator(Circuit.from_components(case.name, case.components),
                     replace(case.config, time_step=step, stop_time=stop),
                     events=tuple(event for event in case.events if event.time <= stop),
                     on_step=case.on_step).run()


def constant_mode(upper, step, stop, pulse=0.0, event=None):
    """Only gate/input/initial-state overrides; the candidate topology is reused."""
    case = EXAMPLE["define_case"]()
    components = []
    for item in case.components:
        if isinstance(item, IdealSwitch):
            item = replace(item, closed=upper if item.name == "Supper" else not upper)
        elif isinstance(item, Inductor):
            item = replace(item, initial_current=3.0)
        elif isinstance(item, Capacitor):
            item = replace(item, initial_voltage=15.0)
        elif isinstance(item, CurrentSource):
            item = replace(item, current=pulse)
        components.append(item)
    return Simulator(Circuit.from_components(case.name, components),
                     replace(case.config, time_step=step, stop_time=stop),
                     events=() if event is None else (event,)).run()


def state_equations(upper, pulse=0.0):
    """x=[iL, UC], Vm=(30*gu+gp*UC-iL)/(gu+gl+gp)."""
    gu, gl = (10 + SNUBBER_G, SNUBBER_G) if upper else (SNUBBER_G, 10 + SNUBBER_G)
    total = gu + gl + PARALLEL_G
    matrix = np.array([
        [-1 / (total * L), -(gu + gl) / (total * L)],
        [(1 - PARALLEL_G / total) / C,
         (PARALLEL_G**2 / total - PARALLEL_G - 1 / R) / C],
    ])
    source = np.array([30 * gu / (total * L), (30 * PARALLEL_G * gu / total - pulse) / C])
    return matrix, source


@pytest.fixture(scope="module")
def baseline():
    return simulate()


@pytest.fixture(scope="module")
def signals(baseline):
    # Build once: all full-run tests share this 200001-point record.
    values = {name: np.array([row[name] for row in baseline.rows]) for name in baseline.rows[0]}
    time = values["time"]
    # CurrentSource has no output column. This is the declared load schedule,
    # checked against the independent output-node KCL below.
    values["load_current"] = 2.0 * (((time >= .0025) & (time < .005))
                                  | ((time >= .0075) & (time < .01)))
    return values


def powers(q):
    mid, output = q["v:mid"], q["v:out"]
    delivered = -30 * q["i:Vdc"]
    loss = ((30 - mid)**2 * SNUBBER_G + mid**2 * SNUBBER_G
            + (mid - output)**2 * PARALLEL_G + output**2 / R
            + .1 * (q["i:Supper"]**2 + q["i:Slower"]**2))
    return delivered, loss, output * q["load_current"]


def test_initial_storage_is_exact_blocked_dc_division():
    lower = 1 / (Fraction(1, 100000) + Fraction(4, 15))
    output = 30 * lower / (100000 + lower)
    current = output / Fraction(15, 4)
    assert EXAMPLE["initial_storage"]() == pytest.approx((float(current), float(output)), rel=1e-15)
    result = simulate(stop=0)
    row = result.rows[0]
    assert row["v:out"] == pytest.approx(float(output), abs=1e-14)
    assert row["v:mid"] == pytest.approx(float(output), abs=1e-14)
    assert row["i:L"] == pytest.approx(float(current), abs=1e-14)
    assert abs(row["i:C"]) < 1e-14
    assert row["state:Supper"] == row["state:Slower"] == 0
    assert row["filtered_error"] == row["integral_term"] == 0
    assert row["duty"] == .01
    assert -row["i:Vdc"] == pytest.approx(float((30 - output) / 100000), abs=1e-14)


def test_explicit_parasitics_and_external_limit_keep_the_original_topology():
    case = EXAMPLE["define_case"]()
    items = {item.name: item for item in case.components}
    assert len(items) == 10
    for name in ("Supper", "Slower"):
        assert items[name].closed_resistance == .1
        assert items[name].open_conductance == 0  # Leakage is the separate snubber.
    assert items["Rupper"].resistance == items["Rlower"].resistance == 100000
    assert items["Rparallel"].resistance == 10000
    assert (items["L"].positive, items["L"].negative) == ("mid", "out")
    assert items["L"].inductance == L and items["C"].capacitance == C
    assert items["Rload"].resistance == R
    control = EXAMPLE["VoltageControl"]()
    assert control.pi.lower is None and control.pi.upper is None
    assert control.limiter.lower == .01 and control.limiter.upper == .95
    assert not case.output.save_data and not case.output.save_figure


@pytest.mark.parametrize("upper", [False, True], ids=["lower_on", "upper_on"])
def test_constant_modes_match_independent_exponential_and_second_order(upper):
    matrix, source = state_equations(upper)
    augmented = np.zeros((3, 3))
    augmented[:2, :2], augmented[:2, 2] = matrix, source
    stop = 100e-6
    exact = (expm(stop * augmented) @ np.array([3.0, 15.0, 1.0]))[:2]
    errors = []
    for step in (100e-9, 50e-9):
        result = constant_mode(upper, step, stop)
        actual = np.array([result.rows[-1]["i:L"], result.rows[-1]["v:out"]])
        error = np.abs(actual - exact)
        assert error[0] < 1e-7 and error[1] < 1e-6
        errors.append(error)
    ratio = errors[0] / errors[1]
    assert np.all((ratio > 3.7) & (ratio < 4.3)), ratio


@pytest.mark.parametrize(("before", "after"), [(0.0, 2.0), (2.0, 0.0)])
def test_load_edge_keeps_storage_and_changes_capacitor_current_only(before, after):
    stop = 20e-6
    event = EXAMPLE["LoadCurrentStep"](stop, "Ipulse", value=after)
    left = constant_mode(True, 50e-9, stop, pulse=before).rows[-1]
    result = constant_mode(True, 50e-9, stop, pulse=before, event=event)
    right = result.rows[-1]
    for name in ("i:L", "v:out", "v:mid"):
        assert right[name] == pytest.approx(left[name], abs=1e-11)
    assert right["i:C"] - left["i:C"] == pytest.approx(before - after, abs=1e-11)
    for row, expected in ((left, before), (right, after)):
        actual_load = row["i:L"] + row["i:Rparallel"] - row["i:C"] - row["v:out"] / R
        assert actual_load == pytest.approx(expected, abs=1e-11)
    assert len(result.event_log) == 1
    assert result.event_log[0]["before"] == before and result.event_log[0]["after"] == after


@pytest.mark.slow
def test_full_record_independent_midpoint_and_three_node_kcl(signals):
    q = signals
    gu, gl = SNUBBER_G + 10 * q["state:Supper"], SNUBBER_G + 10 * q["state:Slower"]
    expected_mid = (30 * gu + PARALLEL_G * q["v:out"] - q["i:L"]) / (gu + gl + PARALLEL_G)
    assert np.max(np.abs(q["v:mid"] - expected_mid)) < 1e-9
    residuals = (
        q["i:Vdc"] + q["i:Supper"] + q["i:Rupper"],
        q["i:Supper"] + q["i:Rupper"] - q["i:Slower"] - q["i:Rlower"] - q["i:L"] - q["i:Rparallel"],
        q["i:L"] + q["i:Rparallel"] - q["i:C"] - q["v:out"] / R - q["load_current"],
    )
    assert max(np.max(np.abs(value)) for value in residuals) < 1e-9


@pytest.mark.slow
def test_full_record_instantaneous_power_and_diode_inactivity(signals):
    q = signals
    source, loss, load = powers(q)
    storage_power = (q["v:mid"] - q["v:out"]) * q["i:L"] + q["v:out"] * q["i:C"]
    assert np.max(np.abs(source - loss - load - storage_power)) < 1e-8
    assert np.all(loss >= 0) and np.mean(source) > 0
    assert np.max(np.abs(q["i:L"])) < 7.99 and np.max(np.abs(q["v:out"])) < 40
    # Body-diode anode/cathode voltages: lower 0->mid, upper mid->dc.
    assert np.min(q["v:mid"]) > -.8 and np.max(q["v:mid"]) < 30.8


@pytest.mark.slow
def test_full_record_control_recurrence_and_unclamped_integral(signals):
    q = signals
    filtered, integral = np.zeros_like(q["time"]), np.zeros_like(q["time"])
    for index, dt in enumerate(np.diff(q["time"]), 1):
        filtered[index] = (filtered[index - 1] + dt / 1e-6 * (15 - q["v:out"][index])) / (1 + dt / 1e-6)
        integral[index] = integral[index - 1] + 200 * filtered[index] * dt
    duty = np.clip(.5 * filtered + integral, .01, .95)
    assert np.max(np.abs(q["filtered_error"] - filtered)) < 1e-12
    assert np.max(np.abs(q["integral_term"] - integral)) < 1e-12
    assert np.max(np.abs(q["duty"] - duty)) < 1e-12
    saturated = (duty[1:] == .95) & (filtered[1:] > 0)
    assert np.any(saturated)
    assert np.all(np.diff(integral)[saturated] > 0)  # No PI anti-windup.


@pytest.mark.slow
def test_full_record_pwm_uses_previous_command_and_current_carrier(signals):
    q = signals
    phase = ((q["time"] + 5e-6) * 50000) % 1
    carrier = np.where(phase < .5, 4 * phase - 1, 3 - 4 * phase)
    expected = 2 * q["duty"][:-1] - 1 >= carrier[1:]
    assert np.array_equal(q["state:Supper"][1:], expected)
    assert np.array_equal(q["state:Slower"][1:], ~expected)
    same_step = 2 * q["duty"][1:] - 1 >= carrier[1:]
    assert np.any(same_step != expected)  # This check detects moving control before the solve.


@pytest.mark.slow
def test_full_record_trapezoidal_energy_with_switching_covariance(baseline, signals):
    q = signals
    time, voltage, current = q["time"], q["v:out"], q["i:L"]
    cap_left, pulse_left = q["i:C"][1:].copy(), q["load_current"][1:].copy()
    assert len(baseline.event_log) == 4
    for event in baseline.event_log:
        index = np.flatnonzero(time == event["time"])[0]
        cap_left[index - 1] += event["after"] - event["before"]
        pulse_left[index - 1] = event["before"]
    source, loss, load = powers(q)
    net_left = source[:-1] - loss[:-1] - load[:-1]
    net_right = source[1:] - loss[1:] - voltage[1:] * pulse_left
    inductor_voltage = q["v:mid"] - voltage
    covariance = (np.diff(inductor_voltage) * np.diff(current)
                  + np.diff(voltage) * (cap_left - q["i:C"][:-1])) / 4
    # TR uses its configured h, after normalizing floating differences of time.
    work = baseline.time_step * ((net_left + net_right) / 2 - covariance)
    stored = .5 * (L * current**2 + C * voltage**2)
    scale = np.max(stored)
    assert np.max(np.abs(np.diff(stored) - work)) / scale < 5e-10
    assert np.max(np.abs(stored[1:] - stored[0] - np.cumsum(work))) / scale < 1e-8


@pytest.mark.slow
def test_half_step_states_over_startup_and_first_load_step(signals):
    fine = simulate(25e-9, 2.6e-3)
    count = len(fine.rows[::2])
    assert np.allclose([row["time"] for row in fine.rows[::2]], signals["time"][:count], atol=1e-18, rtol=0)
    # Reserve half the frozen commercial continuous-state budget for grid error.
    for name, maximum, scale, nrmse in (("v:out", .15, 15, .0025), ("i:L", .075, 8, .005)):
        difference = np.array([row[name] for row in fine.rows[::2]]) - signals[name][:count]
        assert np.max(np.abs(difference)) < maximum
        assert np.sqrt(np.mean(difference**2)) / scale < nrmse
