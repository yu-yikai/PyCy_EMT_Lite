"""Check the two stations' initial conditions, sampling and signed power."""

import json
import math
import runpy
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from pycy_emt_lite.cases import OutputOptions, run_case

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples/34_two_terminal_vsc_hvdc.py"
PROTOCOL = ROOT / "validation/cases/two_terminal_vsc_hvdc/candidate_protocol.json"
STEPS = (5e-6, 2.5e-6)
STOP = .012005


@pytest.fixture(scope="module")
def define_case():
    return runpy.run_path(str(EXAMPLE))["define_case"]


@pytest.fixture(scope="module", params=STEPS)
def short_run(define_case, request):
    step = request.param
    case = define_case(time_step=step, stop_time=STOP)
    return step, run_case(replace(case, plots=(), summary=None, output=OutputOptions(show_figure=False)))


def test_precharged_caps_parked_gates_and_signed_rail_currents(short_run):
    step, result = short_run
    time = result.series("time")
    assert len(time) == round(STOP / step) + 1
    np.testing.assert_allclose(time, np.arange(len(time)) * step, atol=2e-12, rtol=0)

    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    profile = next(grid for grid in protocol["grids"].values() if grid["step_s"] == step)
    initial = result.rows[0]
    for rail, voltage in profile["initial_capacitor_voltage_v"].items():
        assert initial[f"v:{rail}"] == pytest.approx(voltage, abs=1e-8)
    for branch, current in profile["initial_link_current_a"].items():
        assert initial[f"i:I_{branch}"] == pytest.approx(current, abs=1e-10)
    assert initial["i:Rload"] == pytest.approx(initial["b_vdc_v"] / 400, abs=1e-10)
    for site, half, name in (("a", "am", "dc_sent_w"), ("b", "mb", "dc_received_w")):
        expected = sum(initial[f"v:{site}_{pole}"] * initial[f"i:I_{pole}_{half}"] for pole in "pn")
        assert expected > 0
        assert initial[name] == pytest.approx(expected, abs=1e-12)

    for site in "ab":
        assert initial[f"{site}_theta"] == pytest.approx(1.5 * math.pi)
        assert initial[f"{site}_dc_pi_integrator"] == initial[f"{site}_outer_enabled"] == 0
        for phase in "abc":
            assert initial[f"v:{site}_grid_{phase}"] - initial[f"v:{site}_star"] == pytest.approx(0, abs=1e-9)
            assert initial[f"i:{site}_L{phase}"] == pytest.approx(0, abs=1e-9)
            assert initial[f"i:{site}_Lg{phase}"] == pytest.approx(0, abs=1e-9)
            assert initial[f"state:{site}_S{phase}_upper"] == 0
            assert initial[f"state:{site}_S{phase}_lower"] == 1


def test_both_stations_apply_solved_sample_at_the_next_gate_row(short_run):
    step, result = short_run
    ticks = np.arange(len(result.rows))
    inner, outer, gate = (round(period / step) for period in (100e-6, 1e-3, 5e-6))
    sample_ticks = ticks[(ticks != 0) & (ticks % inner == 0)]
    outer_ticks = ticks[(ticks != 0) & (ticks % outer == 0)]
    sampled = np.maximum(0, (ticks - gate) // inner * inner)
    carrier = np.abs((ticks // gate) % 200 - 100) / 50 - 1
    midpoints = ticks[ticks % gate != 0]

    for site in "ab":
        np.testing.assert_array_equal(np.flatnonzero(result.series(f"{site}_sample_update")), sample_ticks)
        np.testing.assert_array_equal(np.flatnonzero(result.series(f"{site}_outer_due")), outer_ticks)
        np.testing.assert_array_equal(result.series(f"{site}_gate_tick"), ticks // gate)
        pending = np.column_stack([result.series(f"{site}_pending_{phase}") for phase in "abc"])
        assert np.max(np.abs(pending[inner])) > .002
        for column, phase in enumerate("abc"):
            applied = result.series(f"{site}_applied_{phase}")
            np.testing.assert_array_equal(applied, pending[sampled, column])
            upper = result.series(f"state:{site}_S{phase}_upper")
            lower = result.series(f"state:{site}_S{phase}_lower")
            np.testing.assert_array_equal(upper, applied >= carrier)
            np.testing.assert_array_equal(lower, 1 - upper)
            np.testing.assert_array_equal(upper[midpoints], upper[midpoints - 1])
            np.testing.assert_array_equal(lower[midpoints], lower[midpoints - 1])


def test_b_regulates_voltage_while_a_keeps_zero_power_request(short_run):
    step, result = short_run
    indexes = np.array([round(t / step) for t in (.011, .012)])
    for site in "ab":
        np.testing.assert_array_equal(np.flatnonzero(result.series(f"{site}_outer_enabled")), indexes)
    row = result.rows[indexes[0]]
    assert row["a_p_ref_w"] == row["a_ip_ref_a"] == row["a_dc_pi_integrator"] == 0
    assert row["a_q_ref_var"] == row["b_q_ref_var"] == 0
    error_v = 400 - row["b_vdc_v"]
    assert error_v > 0
    integral = 4.96 * .001 * error_v
    assert row["b_dc_pi_integrator"] == pytest.approx(integral)
    assert row["b_ip_ref_a"] == pytest.approx(.276 * error_v + integral)


def test_perturbing_one_station_keeps_the_other_controller_state(short_run, define_case):
    step, result = short_run
    initial = result.rows[0]
    measured = result.rows[round(100e-6 / step)]
    perturbed = {**measured, "v:a_grid_b": measured["v:a_grid_b"] + .2}
    clean = define_case(time_step=step, stop_time=STOP).on_step
    changed = define_case(time_step=step, stop_time=STOP).on_step
    assert clean is not None and changed is not None
    clean(initial)
    changed(initial)
    expected, altered = clean(measured), changed(perturbed)
    assert altered["a_pll_omega"] != expected["a_pll_omega"]
    assert altered["a_pending_b"] != expected["a_pending_b"]
    for key, value in expected.items():
        if key.startswith("b_"):
            assert altered[key] == value
