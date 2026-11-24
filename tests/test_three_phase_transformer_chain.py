"""Independent sin+exponential solution, delta incidence and signed energy."""

import json
import math
import runpy
from dataclasses import replace
from itertools import pairwise
from pathlib import Path

import numpy as np
import pytest

from pycy_emt_lite import (
    Circuit,
    Inductor,
    Resistor,
    Simulator,
    VoltageSource,
)
from pycy_emt_lite.analysis import rms
from pycy_emt_lite.components.transformers import ThreePhaseTransformer

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = runpy.run_path(str(ROOT / "examples/24_three_phase_transformer_chain.py"))
PROTOCOL = json.loads((ROOT / "validation/cases/three_phase_transformer_chain/manifest.json").read_text(encoding="utf-8"))
D = np.array([[1.0, -1.0, 0.0], [0.0, 1.0, -1.0], [-1.0, 0.0, 1.0]])
PHASE = np.array([0.0, -2 * np.pi / 3, 2 * np.pi / 3])
OMEGA = 2 * np.pi * 60
N = (13000 / np.sqrt(3)) / 115000
RY = 0.01 * 13000**2 / 100e6
RD = 0.01 * 3 * 115000**2 / 100e6
RUP = RY + N**2 * RD
RDOWN = RD + RY / N**2
RLOAD = 13000**2 / 1000
RS = (13000 * np.sqrt(3 / 2))**2 / 1e6 / np.sqrt(1 + 15**2)
LS = 15 * RS / OMEGA
R = RS + RUP + N**2 * RDOWN + RLOAD


def simulate(step=0.5e-6, stop=0.05):
    case = EXAMPLE["define_case"]()
    return Simulator(Circuit.from_components(case.name, case.components),
                     replace(case.config, time_step=step, stop_time=stop)).run()


def three(result, pattern):
    return np.column_stack([result.series(pattern.format(phase)) for phase in "abc"])


def independent_ports(time):
    # This scalar RL solution is derived from the physical chain, not MNA.
    phasor = 13000 * np.exp(1j * PHASE) / (R + 1j * OMEGA * LS)
    current = (phasor * np.exp(1j * OMEGA * time[:, None])).imag
    current -= phasor.imag * np.exp(-R / LS * time[:, None])
    emf = 13000 * np.sin(OMEGA * time[:, None] + PHASE)
    lv = (RLOAD + RUP + N**2 * RDOWN) * current
    hv = (RLOAD + N**2 * RDOWN) / (3 * N) * (current @ D)
    output = {}
    for index, phase in enumerate("abc"):
        for prefix, values in {
            "v:emf_{}": emf, "v:rl_{}": emf - RS * current,
            "v:lv:{}": lv, "v:hv:{}": hv, "v:load:{}": RLOAD * current,
            "i:Vs_{}": -current, "i:Rs_{}": current, "i:Ls_{}": current,
            "i:Rload_{}": current, "i:Tup:primary:{}": current,
            "i:Tup:secondary:{}": -N * current,
            "i:Tdown:primary:{}": N * current, "i:Tdown:secondary:{}": -current,
            "v:Ls_{}": emf - R * current,
        }.items():
            output[prefix.format(phase)] = values[:, index]
    output["i:DeltaCenter"] = np.zeros_like(time)
    output["v:n_up"] = output["v:n_down"] = np.zeros_like(time)
    return output


@pytest.fixture(scope="module")
def baseline():
    # The complete 50 ms run is shared; refinement runs only cover 40 us.
    return simulate()


@pytest.fixture(scope="module")
def exact(baseline):
    return independent_ports(baseline.series("time"))


def test_topology_preserves_actual_source_parameters_float_stars_and_fixed_load():
    case = EXAMPLE["define_case"]()
    inductors = [item for item in case.components if isinstance(item, Inductor)]
    sources = [item for item in case.components if isinstance(item, VoltageSource)]
    resistors = {item.name: item for item in case.components if isinstance(item, Resistor)}
    transformers = {item.name: item for item in case.components if isinstance(item, ThreePhaseTransformer)}
    assert len(case.components) == 15 and len(inductors) == len(sources) == 3
    assert case.config.time_step == 0.5e-6 and case.config.stop_time == 0.05
    assert case.config.method == "trapezoidal" and case.config.linear_solver_mode == "reuse"
    assert not case.events and case.on_step is None
    assert all(item.initial_current == 0 and item.inductance == pytest.approx(LS) for item in inductors)
    for phase, angle in zip("abc", PHASE, strict=True):
        assert resistors[f"Rs_{phase}"].resistance == pytest.approx(RS)
        load = resistors[f"Rload_{phase}"]
        assert (load.positive, load.negative, load.resistance) == (f"load:{phase}", "0", RLOAD)
        source = next(item for item in sources if item.name == f"Vs_{phase}")
        assert callable(source.voltage)
        assert source.voltage(0) == pytest.approx(13000 * math.sin(angle), abs=1e-10)
    up, down = transformers["Tup"], transformers["Tdown"]
    assert (up.primary_connection, up.secondary_connection) == ("Y", "D")
    assert (down.primary_connection, down.secondary_connection) == ("D", "Y")
    assert up.primary_neutral == "n_up" and down.secondary_neutral == "n_down"
    assert up.turns_ratio == pytest.approx(N) and down.turns_ratio == pytest.approx(1 / N)
    assert up.leakage_resistance == pytest.approx(RUP)
    assert down.leakage_resistance == pytest.approx(RDOWN)
    for transformer in transformers.values():
        assert transformer.leakage_inductance == 0
        assert transformer.magnetizing_inductance is transformer.core_loss_resistance is None
        assert transformer.saturation_knee_flux is None


def test_all_frozen_signals_and_other_ports_match_independent_full_transient(baseline, exact):
    assert len(baseline.rows) == 100001
    formal_names = {signal["candidate"] for signal in PROTOCOL["signals"]}
    for signal in PROTOCOL["signals"]:
        name = signal["candidate"]
        assert np.max(np.abs(baseline.series(name) - exact[name])) <= signal["max_abs_error"], name
    for name, expected in exact.items():
        if name in formal_names:
            continue
        # All winding/source currents and internal source-L voltages are also
        # checked; v:Ls includes the fast physical cold-start transient.
        tolerance = 50.0 if name.startswith("v:") else 0.0003
        if name in {"v:n_up", "v:n_down"}:
            tolerance = 1e-6
        np.testing.assert_allclose(baseline.series(name), expected, atol=tolerance, rtol=0, err_msg=name)


def test_zero_current_initialization_and_source_inductor_continuity(baseline):
    supply = three(baseline, "i:Ls_{}")
    voltage = three(baseline, "v:Ls_{}")
    emf = three(baseline, "v:emf_{}")
    np.testing.assert_allclose(supply[0], 0, atol=1e-12)
    np.testing.assert_allclose(voltage[0], emf[0], atol=1e-7)
    assert abs(emf[0, 1]) > 11000 and abs(emf[0, 2]) > 11000
    for bus in ("lv", "hv", "load"):
        np.testing.assert_allclose(three(baseline, f"v:{bus}:{{}}")[0], 0, atol=1e-6)
    # Integrated vL=L di/dt checks every adjacent pair without a startup jump
    # or a reset hidden inside any transformer.
    dt = np.diff(baseline.series("time"))[:, None]
    np.testing.assert_allclose(LS * np.diff(supply, axis=0), dt * (voltage[:-1] + voltage[1:]) / 2,
                               atol=1e-10, rtol=0)


def test_delta_winding_line_kcl_and_reference_have_no_return_current(baseline):
    supply, load = three(baseline, "i:Ls_{}"), three(baseline, "i:Rload_{}")
    up1, up2 = three(baseline, "i:Tup:primary:{}"), three(baseline, "i:Tup:secondary:{}")
    down1, down2 = three(baseline, "i:Tdown:primary:{}"), three(baseline, "i:Tdown:secondary:{}")
    reference = baseline.series("i:DeltaCenter")
    for residual in (supply - up1, supply - three(baseline, "i:Rs_{}"),
                     supply + three(baseline, "i:Vs_{}"), down2 + load,
                     up2 + N * up1, down2 + down1 / N,
                     (up2 + down1) @ D + reference[:, None] / 3,
                     up1.sum(axis=1), down2.sum(axis=1)):
        assert np.max(np.abs(residual)) < 1e-8
    hv = three(baseline, "v:hv:{}")
    assert np.max(np.abs(hv.mean(axis=1))) < 1e-6
    assert np.max(np.abs(reference)) < 1e-8
    assert np.max(np.abs(reference * hv.mean(axis=1))) < 1e-10
    np.testing.assert_allclose(-up2 @ D, down1 @ D, atol=1e-8, rtol=0)
    assert np.max(np.abs(up2 @ D - up2)) > 0.003  # Delta winding current is not line current.


def test_positive_copper_loss_and_signed_instantaneous_port_power(baseline):
    supply = three(baseline, "i:Ls_{}")
    emf, lv, hv, load = (
        three(baseline, "v:emf_{}"), three(baseline, "v:lv:{}"),
        three(baseline, "v:hv:{}"), three(baseline, "v:load:{}"))
    up1, up2 = three(baseline, "i:Tup:primary:{}"), three(baseline, "i:Tup:secondary:{}")
    down1, down2 = three(baseline, "i:Tdown:primary:{}"), three(baseline, "i:Tdown:secondary:{}")
    nup, ndown = baseline.series("v:n_up")[:, None], baseline.series("v:n_down")[:, None]
    copper_up = RY * np.sum(up1**2, axis=1) + RD * np.sum(up2**2, axis=1)
    copper_down = RD * np.sum(down1**2, axis=1) + RY * np.sum(down2**2, axis=1)
    port_up = np.sum((lv - nup) * up1 + (hv @ D.T) * up2, axis=1)
    port_down = np.sum((hv @ D.T) * down1 + (load - ndown) * down2, axis=1)
    np.testing.assert_allclose(port_up, copper_up, atol=1e-7, rtol=0)
    np.testing.assert_allclose(port_down, copper_down, atol=1e-7, rtol=0)
    assert np.min(copper_up) >= 0 and np.min(copper_down) >= 0
    assert np.max(copper_up) > 0.00029 and np.max(copper_down) > 0.00029
    source_loss = RS * np.sum(supply**2, axis=1)
    load_loss = np.sum(load**2, axis=1) / RLOAD
    inductor_power = np.sum(three(baseline, "v:Ls_{}") * supply, axis=1)
    source_work_rate = np.sum(emf * supply, axis=1)
    np.testing.assert_allclose(source_work_rate, source_loss + copper_up + copper_down + load_loss + inductor_power,
                               atol=1e-7, rtol=0)


def test_source_work_resistor_loss_and_trapezoidal_discrete_energy(baseline):
    time = baseline.series("time")
    supply, emf = three(baseline, "i:Ls_{}"), three(baseline, "v:emf_{}")
    energy = 0.5 * LS * np.sum(supply**2, axis=1)
    power = np.sum(emf * supply, axis=1)
    loss = R * np.sum(supply**2, axis=1)
    dt = np.diff(time)
    source_work = np.sum(dt * (power[:-1] + power[1:]) / 2)
    resistor_work = np.sum(dt * (loss[:-1] + loss[1:]) / 2)
    denominator = max(abs(source_work), abs(resistor_work), 1e-12)
    continuous_residual = energy[1:] - energy[0] - np.cumsum(dt * (power[:-1] + power[1:] - loss[:-1] - loss[1:]) / 2)
    assert np.max(np.abs(continuous_residual)) / denominator <= 0.001
    mean_current, mean_emf = (supply[:-1] + supply[1:]) / 2, (emf[:-1] + emf[1:]) / 2
    discrete_work = dt * (np.sum(mean_emf * mean_current, axis=1) - R * np.sum(mean_current**2, axis=1))
    assert np.max(np.abs(np.diff(energy) - discrete_work)) / max(np.max(energy), 1e-12) < 1e-7
    assert np.max(np.abs(energy[1:] - energy[0] - np.cumsum(discrete_work))) / denominator < 1e-7


def test_startup_two_one_half_microsecond_trapezoidal_refinement(baseline):
    errors = []
    for step in (2e-6, 1e-6, 0.5e-6):
        result = baseline if step == 0.5e-6 else simulate(step, stop=40e-6)
        time = result.series("time")
        startup = time <= 40e-6
        current = three(result, "i:Ls_{}")[startup]
        exact = independent_ports(time[startup])
        expected = np.column_stack([exact[f"i:Ls_{phase}"] for phase in "abc"])
        errors.append(float(np.max(np.abs(current - expected))))
    assert all(left / right >= 3 for left, right in pairwise(errors)), errors


def test_startup_piecewise_linear_output_matches_continuous_exact_solution(baseline):
    # The comparator reconstructs between production samples. A sample-point
    # check alone misses the first interval's curved, four-microsecond startup.
    fine_time = np.linspace(0, 40e-6, 4001)  # 10 ns; no phase or amplitude adjustment.
    expected = independent_ports(fine_time)
    time = baseline.series("time")
    stop = int(np.searchsorted(time, fine_time[-1], side="left")) + 1
    startup_rows = baseline.rows[:stop]
    for signal in PROTOCOL["signals"]:
        name = signal["candidate"]
        sampled = np.array([row[name] for row in startup_rows])
        reconstructed = np.interp(fine_time, time[:stop], sampled)
        error = np.max(np.abs(reconstructed - expected[name]))
        assert error <= signal["max_abs_error"], (name, float(error))


def fundamental(result, column):
    start, end = 1 / 60, 0.05
    time = result.series("time")
    window_time = np.concatenate(([start], time[(time > start) & (time < end)], [end]))
    values = np.interp(window_time, time, result.series(column))
    return 2j * np.trapezoid(values * np.exp(-1j * OMEGA * window_time), window_time) / (end - start)


def test_steady_rms_and_clock_shifts_refer_to_low_voltage_terminal(baseline):
    current_phasor = 13000 / (R + 1j * OMEGA * LS)
    expected_rms = {
        "i:Ls_{}": abs(current_phasor) / np.sqrt(2),
        "i:Rload_{}": abs(current_phasor) / np.sqrt(2),
        "v:lv:{}": (RLOAD + RUP + N**2 * RDOWN) * abs(current_phasor) / np.sqrt(2),
        "v:load:{}": RLOAD * abs(current_phasor) / np.sqrt(2),
        "v:hv:{}": (RLOAD + N**2 * RDOWN) / (np.sqrt(3) * N) * abs(current_phasor) / np.sqrt(2),
    }
    for pattern, expected in expected_rms.items():
        for phase in "abc":
            assert rms(baseline, pattern.format(phase), start_time=1 / 60, end_time=0.05) == pytest.approx(expected, rel=0.001)
    for phase in "abc":
        primary = fundamental(baseline, f"v:lv:{phase}")
        assert np.angle(fundamental(baseline, f"v:hv:{phase}") / primary, deg=True) == pytest.approx(-30, abs=0.05)
        assert np.angle(fundamental(baseline, f"v:load:{phase}") / primary, deg=True) == pytest.approx(0, abs=0.05)
    assert 1490 < sum(rms(baseline, f"v:load:{phase}", start_time=1 / 60, end_time=0.05)**2 / RLOAD
                      for phase in "abc") < 1500
