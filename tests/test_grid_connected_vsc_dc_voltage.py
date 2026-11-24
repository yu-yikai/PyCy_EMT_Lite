"""Check DC-link startup, measured-voltage feedback and switch timing."""

import math
import runpy
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from pycy_emt_lite import IdealSwitch
from pycy_emt_lite.cases import OutputOptions, run_case
from pycy_emt_lite.controls import abc_to_dq, dq_to_abc

EXAMPLE = Path(__file__).resolve().parents[1] / "examples/32_grid_connected_vsc_dc_voltage.py"
PHASES = "abc"


@pytest.fixture(scope="module")
def define_case():
    return runpy.run_path(str(EXAMPLE))["define_case"]


@pytest.mark.parametrize("step", [5e-6, 2.5e-6])
def test_load_switch_closes_on_the_400_ms_row(define_case, step):
    case = define_case(time_step=step)
    load_switch = next(part for part in case.components if part.name == "Sload")
    assert isinstance(load_switch, IdealSwitch) and callable(load_switch.closed)
    load_row = round(.4 / step)
    assert [load_switch.closed(j * step) for j in range(load_row - 1, load_row + 2)] == [False, True, True]


@pytest.mark.parametrize("step", [5e-6, 2.5e-6])
def test_startup_uses_solved_voltage_and_publishes_on_the_next_gate_row(define_case, step):
    case = define_case(time_step=step, stop_time=.001005)
    result = run_case(replace(case, plots=(), output=OutputOptions(show_figure=False), summary=None))
    initial = result.rows[0]
    assert initial["v:Cdc"] == pytest.approx(400.0, abs=1e-9)
    assert initial["theta"] == pytest.approx(19 * math.pi / 12)
    assert initial["id_ref"] == initial["dc_pi_integrator"] == initial["state:Sload"] == 0
    assert [initial[f"i:L{phase}"] for phase in PHASES] == pytest.approx([0, 0, 0], abs=1e-9)

    sample_stride, gate_stride = round(100e-6 / step), round(5e-6 / step)
    samples = np.arange(1, 11) * sample_stride
    np.testing.assert_array_equal(np.flatnonzero(result.series("sample_update")), samples)
    np.testing.assert_array_equal(np.flatnonzero(result.series("outer_update")), [samples[-1]])

    sample = result.rows[samples[-1]]
    error = 400.0 - sample["v:Cdc"]
    assert error > .1
    integral = 4.96 * .001 * error
    assert sample["dc_pi_integrator"] == pytest.approx(integral)
    assert sample["id_ref"] == pytest.approx(.276 * error + integral)
    assert sample["iq_ref"] == sample["saturated"] == 0

    # Reconstruct the unsaturated voltage command before scaling it by the live half-bus.
    kp = math.tau * 100 * .01
    omega_l = math.tau * 60 * .01
    vd = sample["ed"] + omega_l * sample["iq"] - kp * (sample["id_ref"] - sample["id"]) - sample["z_d"]
    vq = sample["eq"] - omega_l * sample["id"] + kp * sample["iq"] - sample["z_q"]
    half_bus = sample["v:Cdc"] / 2
    expected = tuple(voltage / half_bus for voltage in dq_to_abc(vd, vq, sample["theta"]))
    assert [sample[f"pending_{p}"] for p in PHASES] == pytest.approx(expected, rel=1e-12, abs=1e-12)

    gate_ticks = np.arange(len(result.rows)) // gate_stride
    carrier = np.abs(gate_ticks % 200 - 100) / 50 - 1
    for phase in PHASES:
        pending = result.series(f"pending_{phase}")
        applied = np.zeros(len(result.rows))
        for j in samples:
            applied[j + gate_stride:] = pending[j]
        np.testing.assert_array_equal(result.series(f"applied_{phase}"), applied)
        upper = applied >= carrier
        np.testing.assert_array_equal(result.series(f"state:S{phase}_upper"), upper)
        np.testing.assert_array_equal(result.series(f"state:S{phase}_lower"), ~upper)

    fresh_case = define_case(time_step=step, stop_time=.001005)
    fresh = run_case(replace(fresh_case, plots=(), output=OutputOptions(show_figure=False), summary=None))
    assert fresh.rows == result.rows


def test_low_bus_voltage_limits_the_command_and_freezes_both_inner_integrators(define_case):
    observe = define_case().on_step
    assert observe is not None
    # This sample needs a voltage above 85.5 V, within the 190 V limit at the nominal bus.
    sample = observe({
        "time": 100e-6, "v:Cdc": 180., "v:dc_p": 150., "v:dc_n": -30.,
        "v:grid_a": 120., "v:grid_b": -60., "v:grid_c": -60.,
        "i:La": 1., "i:Lb": -1., "i:Lc": 0., "i:Rload": 180. / 320., "i:Rstep": 0.,
    })
    assert sample["saturated"] == 1
    assert sample["z_d"] == sample["z_q"] == 0
    modulation = [sample[f"pending_{phase}"] for phase in PHASES]
    assert math.hypot(*abc_to_dq(*modulation, sample["theta"])) == pytest.approx(.95)
