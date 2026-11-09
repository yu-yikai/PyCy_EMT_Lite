"""Independent travelling-wave physics for the finite-R Bergeron example.

The oracle scatters four voltage waves at three resistive boundaries. It never
reads candidate stamps, delay histories, source helpers, or commercial output.
Illegal fixed-grid/construction cases remain covered by test_line_models.py.
"""

import json
import runpy
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from pycy_emt_lite import Circuit, Simulator

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = runpy.run_path(str(ROOT / "examples/27_finite_r_bergeron_line.py"))
PROTOCOL = json.loads((ROOT / "validation/cases/finite_r_bergeron/manifest.json").read_text(encoding="utf-8"))
ACCEPT = PROTOCOL["internal_acceptance"]
Z = 201.0
HALF_DELAY = 150e-6
STOP = .006
RESISTORS = {
    "Rs": ("src", "send", 100.0),
    "Rleft": ("send", "line1_send", 25.0),
    "Rmiddle": ("line1_recv", "line2_send", 50.0),
    "Rright": ("line2_recv", "recv", 25.0),
    "Rload": ("recv", "0", 400.0),
}


def simulate(step=1e-6):
    case = EXAMPLE["define_case"]()
    return Simulator(Circuit.from_components(case.name, case.components),
                     replace(case.config, time_step=step), events=case.events).run()


@pytest.fixture(scope="module")
def baseline():
    return simulate()


@pytest.fixture(scope="module")
def data(baseline):
    return {name: baseline.series(name) for name in baseline.columns}


def source_voltage(time):
    """Frozen source equation, independent of the example's source callable."""
    return 1000 * np.clip((time - .0005) / .0001, 0, 1)


def independent_ports(step):
    """v=a+b, i_into=(b-a)/Z; the opposite outgoing wave arrives after tau.

    Solve the source+125 ohm boundary, the central50 ohm boundary, and the
    receiving425 ohm boundary directly. No nodal stamp or Norton history is
    borrowed from the candidate. Four columns are B1 left/right, B2 left/right.
    """
    time = np.arange(round(STOP / step) + 1) * step
    source = source_voltage(time)
    delay = round(HALF_DELAY / step)
    outgoing = np.zeros((len(time), 4))
    incoming = np.zeros_like(outgoing)
    for k, voltage in enumerate(source):
        a = outgoing[k - delay, [1, 0, 3, 2]] if k >= delay else np.zeros(4)
        incoming[k] = a
        middle_current = 2 * (a[1] - a[2]) / (50 + 2 * Z)
        outgoing[k] = [
            (Z * voltage + (125 - Z) * a[0]) / (125 + Z),
            a[1] - Z * middle_current,
            a[2] + Z * middle_current,
            (425 - Z) * a[3] / (425 + Z),
        ]
    voltage = incoming + outgoing
    current = (outgoing - incoming) / Z
    left, middle, right = current[:, 0], current[:, 2], -current[:, 3]
    expected = {
        "time": time, "v:src": source, "v:send": source - 100 * left,
        "v:line1_send": voltage[:, 0], "v:line1_recv": voltage[:, 1],
        "v:line2_send": voltage[:, 2], "v:line2_recv": voltage[:, 3],
        "v:recv": 400 * right, "i:Vdc": -left, "i:Rs": left,
        "i:Rleft": left, "i:Rmiddle": middle, "i:Rright": right,
        "i:Rload": right,
    }
    for index, name in enumerate(["B1:sending", "B1:receiving", "B2:sending", "B2:receiving"]):
        expected["i:" + name] = current[:, index]
    return expected


def exact_product_integral(time, left, right):
    """Exact integral of two piecewise-linear factors, including first interval."""
    increments = np.diff(time) / 6 * (
        2 * left[:-1] * right[:-1] + left[:-1] * right[1:]
        + left[1:] * right[:-1] + 2 * left[1:] * right[1:]
    )
    return np.r_[0., np.cumsum(increments)]


def line_energies(values):
    """Energy in each half-line is the last tau of both outgoing wave powers."""
    time = values["time"]
    delay = round(HALF_DELAY / (time[1] - time[0]))
    previous = np.maximum(0, np.arange(len(time)) - delay)
    energies = []
    for name, sending, receiving in [("B1", "line1_send", "line1_recv"),
                                     ("B2", "line2_send", "line2_recv")]:
        waves = [(values["v:" + node] + Z * values[f"i:{name}:{port}"]) / 2
                 for node, port in [(sending, "sending"), (receiving, "receiving")]]
        cumulative = sum(exact_product_integral(time, wave, wave) for wave in waves) / Z
        energies.append(cumulative - cumulative[previous])
    return energies


def test_zero_history_source_and_causal_first_arrival(data):
    time = data["time"]
    assert time[0] == 0 and time[-1] == STOP and len(time) == 6001
    for name, values in data.items():
        if name != "time":
            np.testing.assert_allclose(values[time <= .0005], 0, atol=1e-12, rtol=0, err_msg=name)
    np.testing.assert_allclose(data["v:src"], source_voltage(time), atol=1e-8, rtol=0)
    for node, arrival in [("send", .000501), ("line1_recv", .000651),
                          ("line2_send", .000651), ("recv", .000801)]:
        first = time[np.flatnonzero(np.abs(data["v:" + node]) > 1e-9)[0]]
        assert first == pytest.approx(arrival, abs=1e-15), node
    assert all(energy[0] == 0 for energy in line_energies(data))


def test_initial_launch_first_flight_gain_and_physical_reflection_coefficients(data):
    time = data["time"]
    launch = (time > .0005) & (time <= .0008)
    np.testing.assert_allclose(data["v:send"][launch], (Z + 25) * data["i:Rs"][launch],
                               atol=1e-7, rtol=0)
    flight = (time > .0008) & (time <= .0011)
    # Source launch, central transmission, and receiving load division. This
    # interval precedes the next central/source/load round-trip contribution.
    gain = (201 / 326) * (402 / 452) * (800 / 626)
    np.testing.assert_allclose(data["v:recv"][flight], gain * source_voltage(time[flight] - .0003),
                               atol=1e-7, rtol=0)
    a_center = (data["v:line1_recv"] - Z * data["i:B1:receiving"]) / 2
    b_center = (data["v:line1_recv"] + Z * data["i:B1:receiving"]) / 2
    no_load_return = (time > .00065) & (time <= .00095)
    np.testing.assert_allclose(b_center[no_load_return], (50 / 452) * a_center[no_load_return],
                               atol=1e-7, rtol=0)
    a_load = (data["v:line2_recv"] - Z * data["i:B2:receiving"]) / 2
    b_load = (data["v:line2_recv"] + Z * data["i:B2:receiving"]) / 2
    np.testing.assert_allclose(b_load, ((425 - Z) / (425 + Z)) * a_load, atol=1e-7, rtol=0)


@pytest.mark.parametrize("step", [2e-6, 1e-6, .5e-6])
def test_full_grid_and_refinement_match_independent_scattering(step, baseline):
    result = baseline if step == 1e-6 else simulate(step)
    expected = independent_ports(step)
    for name, values in expected.items():
        tolerance = 2e-18 if name == "time" else (
            ACCEPT["max_voltage_error_versus_independent_V"] if name.startswith("v:")
            else ACCEPT["max_current_error_versus_independent_A"]
        )
        np.testing.assert_allclose(result.series(name), values, atol=tolerance, rtol=0, err_msg=name)
    # These grids align every delay and source breakpoint. Roundoff agreement
    # is allowed; an artificial second-order ratio is not required.
    for name in ["v:send", "v:recv", "i:Rs", "i:Rload"]:
        coarse = result.series(name) if step >= 1e-6 else result.series(name)[::2]
        fine = baseline.series(name)[::2] if step == 2e-6 else baseline.series(name)
        tolerance = 1e-7 if name.startswith("v:") else 1e-9
        np.testing.assert_allclose(coarse, fine, atol=tolerance, rtol=0)


def test_every_junction_and_resistor_obeys_kcl_kvl_and_port_directions(data):
    for names in [("Vdc", "Rs"), ("Rs", "Rleft"), ("Rleft", "B1:sending"),
                  ("B1:receiving", "Rmiddle"), ("Rmiddle", "B2:sending"),
                  ("B2:receiving", "Rright"), ("Rright", "Rload")]:
        first, second = [data["i:" + name] for name in names]
        residual = first + second if names[0] in {"Vdc", "B1:receiving", "B2:receiving"} else first - second
        np.testing.assert_allclose(residual, 0, atol=ACCEPT["kcl_abs_tolerance_A"], rtol=0, err_msg=str(names))
    for name, (positive, negative, resistance) in RESISTORS.items():
        drop = data["v:" + positive] - (data["v:" + negative] if negative != "0" else 0)
        np.testing.assert_allclose(drop, resistance * data["i:" + name],
                                   atol=ACCEPT["kvl_abs_tolerance_V"], rtol=0, err_msg=name)
    assert np.max(data["i:B1:receiving"]) <= 1e-12
    assert np.max(data["i:B2:receiving"]) <= 1e-12


def test_all_five_resistive_losses_are_positive_and_final_dc_limit_is_correct(data):
    for name, (positive, negative, _) in RESISTORS.items():
        drop = data["v:" + positive] - (data["v:" + negative] if negative != "0" else 0)
        power = drop * data["i:" + name]
        assert np.min(power) >= -1e-10, name
        assert exact_product_integral(data["time"], drop, data["i:" + name])[-1] > 0, name
    dc_current = 1000 / (100 + 25 + 50 + 25 + 400)
    for name in RESISTORS:
        assert data["i:" + name][-1] == pytest.approx(dc_current, abs=1e-9)
    assert data["v:send"][-1] == pytest.approx(1000 - 100 * dc_current, abs=1e-7)
    assert data["v:recv"][-1] == pytest.approx(400 * dc_current, abs=1e-7)


def test_two_half_line_energies_balance_source_work_and_all_resistive_losses(data):
    time = data["time"]
    energies = line_energies(data)
    assert all(energy[0] == 0 and np.min(energy) >= 0 and np.max(energy) > 0 for energy in energies)
    source_current = -data["i:Vdc"]
    assert np.min(data["v:src"]) >= 0 and np.min(source_current) >= -1e-12
    work = exact_product_integral(time, data["v:src"], source_current)
    losses = sum(resistance * exact_product_integral(time, data["i:" + name], data["i:" + name])
                 for name, (_, _, resistance) in RESISTORS.items())
    energy = sum(energies)
    # Vs and its supplied current stay nonnegative, so work is also the exact
    # integral(abs(source_power)) in the protocol's dimensioned denominator.
    denominator = max(1., float(work[-1]), float(losses[-1]), float(np.max(energy)))
    tolerance = ACCEPT["energy_balance_abs_tolerance_J"] + ACCEPT["energy_balance_relative_tolerance"] * denominator
    residual = work - losses - (energy - energy[0])
    assert np.max(np.abs(residual)) <= tolerance
