"""Independent full-network physics; no vendor files or candidate initializer oracle.

The oracle is a seven-unknown complex nodal system: six physical voltages and
the ideal transformer's primary current. It uses the original nameplate inputs,
not the candidate's backward impedance recursion or the frozen export phasors.
"""

import cmath
import json
import math
import runpy
from dataclasses import replace
from itertools import pairwise
from pathlib import Path

import numpy as np
import pytest

from pycy_emt_lite import (
    Capacitor,
    Circuit,
    Inductor,
    Resistor,
    Simulator,
    SinglePhaseTransformer,
    VoltageSource,
)

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = runpy.run_path(str(ROOT / "examples/25_source_line_transformer_network.py"))
PROTOCOL = json.loads((ROOT / "validation/cases/source_line_transformer/manifest.json").read_text(encoding="utf-8"))
ACCEPT = PROTOCOL["internal_acceptance"]
OMEGA = 2 * math.pi * 60
PRIMARY_RMS = 735000 / math.sqrt(3)
SECONDARY_RMS = 315000 / math.sqrt(3)
SOURCE_PEAK = math.sqrt(2) * PRIMARY_RMS
RATIO = 735 / 315
PRIMARY_BASE = PRIMARY_RMS**2 / 250e6
SECONDARY_BASE = SECONDARY_RMS**2 / 250e6

# Convert independently from original per-km, pu and single-phase P/Q ratings.
LINE_Z = complex(.011, OMEGA * .8674e-3)
LINE_Y = 1j * OMEGA * 13.41e-9
GAMMA = cmath.sqrt(LINE_Z * LINE_Y)
ZC = cmath.sqrt(LINE_Z / LINE_Y)
SECTION_Z = ZC * cmath.sinh(GAMMA * 75)
SECTION_Y = 2 / ZC * cmath.tanh(GAMMA * 75 / 2)
COMP_Z = PRIMARY_RMS**2 / complex(110e6 / 300, -110e6)
R2 = .001 * SECONDARY_BASE
RZ1 = .734
RESISTANCE = {
    "Rs": 2.0, "Rline1": SECTION_Z.real, "Rline2": SECTION_Z.real,
    "Gsend": 2 / SECTION_Y.real, "Gmid": 1 / SECTION_Y.real, "Grecv": 2 / SECTION_Y.real,
    "Rcomp_s": COMP_Z.real, "Rcomp_r": COMP_Z.real,
    "Rp": .001 * PRIMARY_BASE, "Rm": 500 * PRIMARY_BASE,
    "Rsec": R2 + RZ1, "Rzs": 11.0, "Rload": SECONDARY_RMS**2 / 200e6,
}
INDUCTANCE = {
    "Lline1": SECTION_Z.imag / OMEGA, "Lline2": SECTION_Z.imag / OMEGA,
    "Lcomp_s": COMP_Z.imag / OMEGA, "Lcomp_r": COMP_Z.imag / OMEGA,
    "Lp": .15 * PRIMARY_BASE / OMEGA, "Lm": 500 * PRIMARY_BASE / OMEGA,
    "Lz1": .02085, "Lzs": .2925,
}
CAPACITANCE = {
    "Csend": SECTION_Y.imag / OMEGA / 2, "Cmid": SECTION_Y.imag / OMEGA,
    "Crecv": SECTION_Y.imag / OMEGA / 2, "Cload": 50e6 / (OMEGA * SECONDARY_RMS**2),
}
CAP_NODES = {"Csend": "send", "Cmid": "mid", "Crecv": "recv", "Cload": "load"}


def independent_phasors():
    """Six nodal KCL equations plus Vcore=n*Vsecondary; peak sine convention."""
    matrix = np.zeros((7, 7), dtype=complex)
    rhs = np.zeros(7, dtype=complex)
    # Node order: send, mid, recv, core, secondary, load; last unknown is Jt.
    def branch(p, n, admittance):
        matrix[p, p] += admittance
        if n is not None:
            matrix[n, n] += admittance
            matrix[p, n] -= admittance
            matrix[n, p] -= admittance

    branch(0, None, 1 / RESISTANCE["Rs"])
    rhs[0] = SOURCE_PEAK / RESISTANCE["Rs"]
    for node, gname, cname in ((0, "Gsend", "Csend"), (1, "Gmid", "Cmid"), (2, "Grecv", "Crecv")):
        branch(node, None, 1 / RESISTANCE[gname] + 1j * OMEGA * CAPACITANCE[cname])
    branch(0, None, 1 / COMP_Z)
    branch(2, None, 1 / COMP_Z)
    branch(0, 1, 1 / SECTION_Z)
    branch(1, 2, 1 / SECTION_Z)
    primary_z = complex(RESISTANCE["Rp"], OMEGA * INDUCTANCE["Lp"])
    secondary_z = complex(R2 + RZ1, OMEGA * INDUCTANCE["Lz1"])
    zs = complex(RESISTANCE["Rzs"], OMEGA * INDUCTANCE["Lzs"])
    branch(2, 3, 1 / primary_z)
    branch(3, None, 1 / RESISTANCE["Rm"] + 1 / (1j * OMEGA * INDUCTANCE["Lm"]))
    branch(4, 5, 1 / secondary_z)
    branch(5, None, 1 / zs + 1 / RESISTANCE["Rload"] + 1j * OMEGA * CAPACITANCE["Cload"])
    matrix[3, 6], matrix[4, 6] = 1, -RATIO
    matrix[6, 3], matrix[6, 4] = 1, -RATIO
    values = np.linalg.solve(matrix, rhs)
    assert np.max(np.abs(matrix @ values - rhs)) < 1e-8
    send, mid, recv, core, secondary, load, primary_ideal = values
    q = {f"v:{name}": value for name, value in zip(
        ("send", "mid", "recv", "core", "secondary", "load"), values[:6], strict=True)}
    q.update({
        "v:src": complex(SOURCE_PEAK), "v:load_bus": load,
        "i:Lline1": (send - mid) / SECTION_Z, "i:Lline2": (mid - recv) / SECTION_Z,
        "i:Lcomp_s": send / COMP_Z, "i:Lcomp_r": recv / COMP_Z,
        "i:Lp": (recv - core) / primary_z, "i:Lm": core / (1j * OMEGA * INDUCTANCE["Lm"]),
        "i:Lz1": (secondary - load) / secondary_z, "i:Lzs": load / zs,
        "i:Rs": (SOURCE_PEAK - send) / RESISTANCE["Rs"],
        "i:Iload": load * (1 / RESISTANCE["Rload"] + 1j * OMEGA * CAPACITANCE["Cload"]),
        "i:T:primary": primary_ideal, "i:T:secondary": -RATIO * primary_ideal,
    })
    for name, node in CAP_NODES.items():
        q[f"i:{name}"] = 1j * OMEGA * CAPACITANCE[name] * q[f"v:{node}"]
    for name, node in (("Gsend", "send"), ("Gmid", "mid"), ("Grecv", "recv"), ("Rm", "core"), ("Rload", "load")):
        q[f"i:{name}"] = q[f"v:{node}"] / RESISTANCE[name]
    return q


@pytest.fixture(scope="module")
def oracle():
    return independent_phasors()


def simulate(step=1e-5):
    case = EXAMPLE["define_case"]()
    config = replace(case.config, time_step=step)
    return Simulator(Circuit.from_components(case.name, case.components), config).run()


@pytest.fixture(scope="module")
def baseline():
    return simulate()


@pytest.fixture(scope="module")
def data(baseline):
    return {column: baseline.series(column) for column in baseline.columns}


def exact(q, time):
    return (q * np.exp(1j * OMEGA * time)).imag


def physical_losses(values):
    """Fourteen native physical losses; the folded secondary keeps two terms."""
    return {
        "source": RESISTANCE["Rs"] * values["i:Rs"]**2,
        "line1": RESISTANCE["Rline1"] * values["i:Lline1"]**2,
        "line2": RESISTANCE["Rline2"] * values["i:Lline2"]**2,
        "Gsend": RESISTANCE["Gsend"] * values["i:Gsend"]**2,
        "Gmid": RESISTANCE["Gmid"] * values["i:Gmid"]**2,
        "Grecv": RESISTANCE["Grecv"] * values["i:Grecv"]**2,
        "comp_s": RESISTANCE["Rcomp_s"] * values["i:Lcomp_s"]**2,
        "comp_r": RESISTANCE["Rcomp_r"] * values["i:Lcomp_r"]**2,
        "R1": RESISTANCE["Rp"] * values["i:Lp"]**2,
        "R2": R2 * values["i:Lz1"]**2,
        "Rm": RESISTANCE["Rm"] * values["i:Rm"]**2,
        "Rz1": RZ1 * values["i:Lz1"]**2,
        "Zs": RESISTANCE["Rzs"] * values["i:Lzs"]**2,
        "load": RESISTANCE["Rload"] * values["i:Rload"]**2,
    }


def stored_energy(values):
    return sum(.5 * value * values[f"i:{name}"]**2 for name, value in INDUCTANCE.items()) + sum(
        .5 * value * values[f"v:{CAP_NODES[name]}"]**2 for name, value in CAPACITANCE.items())


def test_complete_network_preserves_independent_unit_conversions_and_meter_topology():
    case = EXAMPLE["define_case"]()
    components = {item.name: item for item in case.components}
    assert len(components) == len(case.components) == 28
    assert case.config.time_step == 1e-5 and case.config.stop_time == .05
    assert case.config.method == "trapezoidal" and case.config.linear_solver_mode == "reuse"
    assert not case.events and case.on_step is None
    for kind, expected, attribute in (
        (Resistor, RESISTANCE, "resistance"), (Inductor, INDUCTANCE, "inductance"),
        (Capacitor, CAPACITANCE, "capacitance"),
    ):
        actual = {item.name: item for item in case.components if isinstance(item, kind)}
        assert actual.keys() == expected.keys()
        for name, value in expected.items():
            assert getattr(actual[name], attribute) == pytest.approx(value, rel=1e-12), name
    # Explicit series topology protects the position of Rm/Lm, both
    # compensators, all three small G branches, and the original RC current meter.
    edges = {
        "Rs": ("src", "send"), "Rline1": ("send", "line1_rl"), "Lline1": ("line1_rl", "mid"),
        "Rline2": ("mid", "line2_rl"), "Lline2": ("line2_rl", "recv"),
        "Rp": ("recv", "primary_rl"), "Lp": ("primary_rl", "core"),
        "Rm": ("core", "0"), "Lm": ("core", "0"),
        "Rsec": ("secondary", "secondary_rl"), "Lz1": ("secondary_rl", "load_bus"),
        "Rcomp_s": ("send", "comp_s_rl"), "Lcomp_s": ("comp_s_rl", "0"),
        "Rcomp_r": ("recv", "comp_r_rl"), "Lcomp_r": ("comp_r_rl", "0"),
        "Rzs": ("load_bus", "zs_rl"), "Lzs": ("zs_rl", "0"),
        "Iload": ("load_bus", "load"), "Rload": ("load", "0"), "Cload": ("load", "0"),
        "Csend": ("send", "0"), "Cmid": ("mid", "0"), "Crecv": ("recv", "0"),
        "Gsend": ("send", "0"), "Gmid": ("mid", "0"), "Grecv": ("recv", "0"),
        "Vs": ("src", "0"),
    }
    for name, terminals in edges.items():
        assert (components[name].positive, components[name].negative) == terminals, name
    transformer = components["T"]
    assert isinstance(transformer, SinglePhaseTransformer)
    assert tuple(transformer.nodes()) == ("core", "0", "secondary", "0")
    assert transformer.turns_ratio == pytest.approx(RATIO)
    assert transformer.leakage_resistance == transformer.leakage_inductance == 0
    assert transformer.magnetizing_inductance is transformer.core_loss_resistance is None
    assert transformer.saturation_knee_flux is transformer.saturated_magnetizing_inductance is None
    meter = components["Iload"]
    assert isinstance(meter, VoltageSource) and meter.voltage == 0
    source = components["Vs"]
    assert isinstance(source, VoltageSource) and callable(source.voltage)
    for time in (0, .003, 1 / 240, .05):
        assert source.voltage(time) == pytest.approx(SOURCE_PEAK * math.sin(OMEGA * time), abs=1e-8)


def test_twelve_nonzero_initial_states_match_independent_nodal_phasors(baseline, oracle):
    components = EXAMPLE["create_components"]()
    scales = {signal["candidate"]: signal["scale"] for signal in PROTOCOL["signals"]}
    checked = 0
    for component in components:
        if isinstance(component, Inductor):
            column, value = f"i:{component.name}", component.initial_current
        elif isinstance(component, Capacitor):
            column, value = f"v:{CAP_NODES[component.name]}", component.initial_voltage
        else:
            continue
        expected = oracle[column].imag
        tolerance = ACCEPT["ideal_transformer_relative_tolerance"] * scales[column]
        assert expected != 0 and value != 0
        assert value == pytest.approx(expected, abs=tolerance, rel=0), column
        assert baseline.series(column)[0] == pytest.approx(expected, abs=tolerance, rel=0), column
        checked += 1
    assert checked == 12
    assert baseline.series("v:src")[0] == pytest.approx(0, abs=1e-10)


def test_all_fourteen_samples_and_continuous_pwl_curves_cover_both_complete_windows(baseline, oracle):
    time = baseline.series("time")
    assert len(time) == 5001 and time[0] == 0 and time[-1] == .05
    assert not baseline.event_log
    for signal in PROTOCOL["signals"]:
        name = signal["candidate"]
        sampled_error = np.abs(baseline.series(name) - exact(oracle[name], time))
        for start, end in PROTOCOL["windows_seconds"]:
            mask = (time >= start) & (time <= end)
            point_error = float(np.max(sampled_error[mask]))
            maximum_gap = float(np.max(np.diff(time[mask])))
            # Linear interpolation of the knot errors stays below their max.
            # Add the exact sine curvature bound to certify EVERY in-between
            # time. L-infinity/scale also rigorously bounds time-weighted NRMSE.
            continuous_bound = point_error + abs(oracle[name]) * OMEGA**2 * maximum_gap**2 / 8
            assert continuous_bound <= signal["max_abs_error"] * ACCEPT["sample_and_piecewise_linear_abs_budget_fraction"], (name, start, continuous_bound)
            assert continuous_bound / signal["scale"] <= signal["max_nrmse"], (name, start, continuous_bound)


def test_kcl_distinguishes_source_line_compensation_transformer_and_load_ports(data):
    def i(name):
        return data[f"i:{name}"]

    residuals = {
        "source": i("Vs") + i("Rs"),
        "send": i("Rs") - i("Lline1") - i("Lcomp_s") - i("Csend") - i("Gsend"),
        "mid": i("Lline1") - i("Lline2") - i("Cmid") - i("Gmid"),
        "recv": i("Lline2") - i("Lp") - i("Lcomp_r") - i("Crecv") - i("Grecv"),
        "core": i("Lp") - i("Lm") - i("Rm") - i("T:primary"),
        "secondary": i("T:secondary") + i("Lz1"),
        "load_bus": i("Lz1") - i("Lzs") - i("Iload"),
        "load": i("Iload") - i("Rload") - i("Cload"),
    }
    for node, residual in residuals.items():
        assert np.max(np.abs(residual)) <= ACCEPT["kcl_abs_tolerance_ampere"], node
    assert np.max(np.abs(i("Rs") - i("Lline1"))) > 100
    assert np.max(np.abs(i("Lline2") - i("Lp"))) > 100
    assert np.max(np.abs(i("Iload") - i("Rload"))) > 100


def test_transformer_magnetizing_location_ratio_signed_power_and_ideal_ammeter(data):
    tolerance = ACCEPT["ideal_transformer_relative_tolerance"]
    core, secondary = data["v:core"], data["v:secondary"]
    primary_i, secondary_i = data["i:T:primary"], data["i:T:secondary"]
    assert np.max(np.abs(core - RATIO * secondary)) / np.max(np.abs(core)) <= tolerance
    assert np.max(np.abs(secondary_i + RATIO * primary_i)) / np.max(np.abs(secondary_i)) <= tolerance
    power = core * primary_i + secondary * secondary_i
    assert np.max(np.abs(power)) / np.max(np.abs(core * primary_i)) <= tolerance
    assert np.max(np.abs(data["v:load_bus"] - data["v:load"])) <= 1e-9
    assert np.max(np.abs((data["v:load_bus"] - data["v:load"]) * data["i:Iload"])) <= 1e-7
    np.testing.assert_allclose(data["v:Lp"], data["v:recv"] - RESISTANCE["Rp"] * data["i:Lp"] - core, atol=1e-7, rtol=0)
    np.testing.assert_allclose(data["v:Lm"], core, atol=1e-7, rtol=0)
    np.testing.assert_allclose(data["v:Lz1"], secondary - (R2 + RZ1) * data["i:Lz1"] - data["v:load_bus"], atol=1e-7, rtol=0)


def test_fourteen_positive_losses_include_small_corrected_shunts_and_core_loss(data, oracle):
    time = data["time"]
    losses = physical_losses(data)
    expected = physical_losses({name: abs(value) / math.sqrt(2) for name, value in oracle.items()})
    assert len(losses) == len(expected) == 14
    for name, power in losses.items():
        assert np.min(power) >= 0 and expected[name] > 0, name
        average = np.trapezoid(power, time) / (time[-1] - time[0])
        assert average == pytest.approx(expected[name], rel=ACCEPT["power_rms_phase_relative_tolerance"]), name
    # The fixed load is at a different actual voltage from its nominal P/Q
    # rating. The G and Rm losses must be present even when a waveform gate
    # might tolerate deleting these small branches.
    assert expected["load"] < 200e6
    assert sum(expected[name] for name in ("Gsend", "Gmid", "Grecv")) > 3000
    assert expected["Rm"] > 300000
    expected_source = .5 * (oracle["v:src"] * oracle["i:Rs"].conjugate()).real
    assert sum(expected.values()) == pytest.approx(expected_source, rel=1e-10)
    # Both originals share one current but retain distinct resistive losses.
    np.testing.assert_allclose(losses["R2"] / R2, losses["Rz1"] / RZ1, atol=1e-8, rtol=1e-12)


def test_all_twelve_storage_branches_obey_trapezoidal_constitutive_laws_including_first_interval(data):
    dt = np.diff(data["time"])
    for name, inductance in INDUCTANCE.items():
        current, voltage = data[f"i:{name}"], data[f"v:{name}"]
        change = inductance * np.diff(current)
        integrated = dt * (voltage[:-1] + voltage[1:]) / 2
        # Voltage-seconds, not an ampere tolerance accidentally applied to Ldi.
        np.testing.assert_allclose(change, integrated, atol=1e-8, rtol=1e-9, err_msg=name)
    for name, capacitance in CAPACITANCE.items():
        voltage, current = data[f"v:{CAP_NODES[name]}"], data[f"i:{name}"]
        charge = capacitance * np.diff(voltage)
        integrated = dt * (current[:-1] + current[1:]) / 2
        np.testing.assert_allclose(charge, integrated, atol=1e-10, rtol=1e-9, err_msg=name)


def energy_account(data):
    time = data["time"]
    energy = stored_energy(data)
    source_power = data["v:src"] * data["i:Rs"]
    loss = sum(physical_losses(data).values())
    denominator = max(float(energy[0]), float(np.trapezoid(np.abs(source_power), time)),
                      float(np.trapezoid(loss, time)), 1.0)
    return energy, source_power, loss, denominator


def test_continuous_source_work_all_loss_and_nonzero_initial_energy_balance(data):
    energy, source, loss, denominator = energy_account(data)
    dt = np.diff(data["time"])
    assert energy[0] > 0 and np.min(energy) > 0 and denominator > 1
    # Continuous instantaneous powers integrated with endpoint trapezoidal
    # quadrature. This is NOT the exact TR average-endpoint power identity.
    increments = dt * (source[:-1] + source[1:] - loss[:-1] - loss[1:]) / 2
    residual = energy[1:] - energy[0] - np.cumsum(increments)
    assert np.max(np.abs(residual)) / denominator <= ACCEPT["continuous_energy_balance_relative_tolerance"]


def test_tr_average_endpoint_energy_identity_is_distinct_from_endpoint_power_trap(data):
    energy, source, loss, denominator = energy_account(data)
    dt = np.diff(data["time"])
    averages = {name: (values[:-1] + values[1:]) / 2 for name, values in data.items() if name != "time"}
    average_source = averages["v:src"] * averages["i:Rs"]
    average_loss = sum(physical_losses(averages).values())
    increments = dt * (average_source - average_loss)
    tolerance = ACCEPT["trapezoidal_average_endpoint_energy_relative_tolerance"]
    assert np.max(np.abs(np.diff(energy) - increments)) / denominator <= tolerance
    assert np.max(np.abs(energy[1:] - energy[0] - np.cumsum(increments))) / denominator <= tolerance
    endpoint_work = dt * (source[:-1] + source[1:] - loss[:-1] - loss[1:]) / 2
    # For each resistor, mean(i^2)-mean(i)^2=(delta_i)^2/4. This establishes
    # why averaging endpoint instantaneous powers is a different quantity.
    squared_differences = {name: np.diff(values) / 2 for name, values in data.items() if name != "time"}
    loss_difference = sum(physical_losses(squared_differences).values())
    endpoint_loss = (loss[:-1] + loss[1:]) / 2
    np.testing.assert_allclose(endpoint_loss - average_loss, loss_difference, atol=1e-6, rtol=1e-8)
    assert np.max(np.abs(endpoint_work - increments)) > 1e-6


def test_twenty_ten_five_microsecond_trapezoidal_refinement_against_nodal_oracle(baseline, oracle):
    errors = {signal["candidate"]: [] for signal in PROTOCOL["signals"]}
    for step in ACCEPT["trapezoidal_step_refinement_seconds"]:
        result = baseline if step == 1e-5 else simulate(step)
        time = result.series("time")
        assert time[0] == 0 and time[-1] == .05
        for name in errors:
            errors[name].append(float(np.max(np.abs(result.series(name) - exact(oracle[name], time)))))
    # Use actual knot errors for order, rather than the h^2 interpolation
    # bound, which would produce a factor of four by construction.
    for name, values in errors.items():
        assert all(left / right >= ACCEPT["minimum_refinement_error_ratio"] for left, right in pairwise(values)), (name, values)


def fundamental(time, values):
    return 2j * np.trapezoid(values * np.exp(-1j * OMEGA * time), time) / (time[-1] - time[0])


def test_three_cycle_rms_phase_and_single_phase_source_and_load_pq(data, oracle):
    time = data["time"]
    relative = ACCEPT["power_rms_phase_relative_tolerance"]
    observed = {}
    for signal in PROTOCOL["signals"]:
        name = signal["candidate"]
        values, q = data[name], oracle[name]
        rms = math.sqrt(float(np.trapezoid(values**2, time) / (time[-1] - time[0])))
        assert rms == pytest.approx(abs(q) / math.sqrt(2), rel=relative), name
        observed[name] = fundamental(time, values)
        phase_difference = math.degrees(cmath.phase(observed[name] / q))
        assert abs(phase_difference) <= ACCEPT["phase_abs_tolerance_degrees"], name
    # Fixed-frequency Fourier projection is a feature measurement; it does
    # not shift or rescale either waveform before the whole-window tests.
    for voltage, current in (("v:src", "i:Rs"), ("v:load", "i:Iload")):
        voltage_q = fundamental(time, data[voltage])
        current_q = observed[current]
        pq = .5 * voltage_q * current_q.conjugate()
        expected = .5 * oracle[voltage] * oracle[current].conjugate()
        assert pq.real == pytest.approx(expected.real, rel=relative)
        assert pq.imag == pytest.approx(expected.imag, rel=relative)
        mean_power = np.trapezoid(data[voltage] * data[current], time) / (time[-1] - time[0])
        assert mean_power == pytest.approx(expected.real, rel=relative)
    assert (.5 * oracle["v:load"] * oracle["i:Iload"].conjugate()).imag < 0  # Fixed RC load.
