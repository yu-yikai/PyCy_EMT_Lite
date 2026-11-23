"""Check the precharged storage circuit, gate timing and signed power reversal."""

import json
import math
import runpy
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from pycy_emt_lite.cases import OutputOptions, run_case

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples/35_grid_connected_storage.py"
PROTOCOL = ROOT / "validation/cases/grid_connected_storage/candidate_protocol.json"


@pytest.fixture(scope="module")
def define_case():
    return runpy.run_path(str(EXAMPLE))["define_case"]


@pytest.fixture(scope="module")
def protocol():
    return json.loads(PROTOCOL.read_text(encoding="utf-8"))


def run_without_figures(case):
    return run_case(replace(case, plots=(), summary=None, output=OutputOptions(show_figure=False)))


@pytest.mark.parametrize("grid", ("5us", "2p5us"))
def test_precharged_storage_and_next_gate_timing(define_case, protocol, grid):
    profile = protocol["grids"][grid]
    step, stop = profile["step_s"], .002005
    result = run_without_figures(define_case(time_step=step, stop_time=stop))
    initial = result.rows[0]
    assert result.method == "trapezoidal"
    assert len(result.rows) == round(stop / step) + 1
    assert initial["v:Cdc"] == pytest.approx(profile["initial_bus_v"], abs=1e-9, rel=0)
    assert initial["v:C1"] == pytest.approx(profile["initial_polarization_v"], abs=1e-9, rel=0)
    assert initial["i:R0"] == pytest.approx(profile["reference_initial_storage_current_a"], abs=1e-9, rel=0)
    assert initial["v:ocv"] - initial["v:a_n"] == pytest.approx(400.0)
    assert initial["a_theta"] == pytest.approx(1.5 * math.pi)
    assert initial["a_pll_omega"] == pytest.approx(math.tau * 60)
    assert initial["a_pll_xi"] == initial["a_z_d"] == initial["a_z_q"] == 0

    ticks = np.arange(len(result.rows))
    gate, inner, outer = (round(period / step) for period in (5e-6, 100e-6, 1e-3))
    np.testing.assert_allclose(result.series("time"), ticks * step, rtol=0, atol=2e-12)
    np.testing.assert_array_equal(result.series("a_j"), ticks)
    np.testing.assert_array_equal(np.flatnonzero(result.series("a_sample_update")), ticks[inner::inner])
    np.testing.assert_array_equal(np.flatnonzero(result.series("a_outer_due")), ticks[outer::outer])
    np.testing.assert_array_equal(result.series("a_gate_tick"), ticks // gate)
    assert np.max(np.abs([result.rows[inner][f"a_pending_{p}"] for p in "abc"])) > .002

    # The sample can reach the switches only at the next 5 µs gate edge.
    last_published_sample = np.maximum(0, (ticks - gate) // inner * inner)
    carrier_tick = (ticks // gate) % 200
    carrier = np.where(carrier_tick <= 100, 50 - carrier_tick, carrier_tick - 150) / 50
    for phase in "abc":
        assert initial[f"v:a_grid_{phase}"] - initial["v:a_star"] == pytest.approx(0, abs=1e-9)
        assert initial[f"i:a_L{phase}"] == initial[f"i:a_Lg{phase}"] == 0
        assert initial[f"a_pending_{phase}"] == initial[f"a_applied_{phase}"] == 0
        assert initial[f"state:a_S{phase}_upper"] == 0
        assert initial[f"state:a_S{phase}_lower"] == 1
        applied = result.series(f"a_applied_{phase}")
        pending = result.series(f"a_pending_{phase}")
        np.testing.assert_array_equal(applied, pending[last_published_sample])
        np.testing.assert_array_equal(result.series(f"state:a_S{phase}_upper"), applied >= carrier)
        np.testing.assert_array_equal(result.series(f"state:a_S{phase}_lower"), applied < carrier)


@pytest.mark.slow
def test_pcc_and_storage_power_reverse_sign(define_case, protocol):
    result = run_without_figures(define_case())
    step = result.time_step
    assert result.stop_time == protocol["example"]["stop_s"]
    assert len(result.rows) == protocol["grids"]["5us"]["candidate_rows_including_initial"]

    def series(key):
        return np.fromiter((row[key] for row in result.rows), dtype=float, count=len(result.rows))

    def tick(time):
        return round(time / step)

    for time, power in ((.020, 0), (.021, 25), (.030, 250), (.150, 250), (.151, 225),
                        (.159, 25), (.160, 0), (.160995, 0), (.161, -25), (.170, -250)):
        assert result.rows[tick(time)]["a_p_ref_w"] == pytest.approx(power, abs=1e-9)
    assert np.count_nonzero(series("a_q_ref_var")) == 0

    bus_v, polarization_v, storage_i = (series(key) for key in ("v:Cdc", "v:C1", "i:R0"))
    star = series("v:a_star")
    pcc_v = np.array([series(f"v:a_pcc_{p}") - star for p in "abc"])
    phase_i = np.array([series(f"i:a_L{p}") for p in "abc"])
    pcc_p, pcc_q, storage_p = (series(key) for key in ("pcc_p_w", "pcc_q_var", "storage_p_w"))
    np.testing.assert_allclose(pcc_p, np.sum(pcc_v * phase_i, axis=0), rtol=0, atol=1e-9)
    np.testing.assert_allclose(pcc_q, ((pcc_v[1] - pcc_v[2]) * phase_i[0]
                                     + (pcc_v[2] - pcc_v[0]) * phase_i[1]
                                     + (pcc_v[0] - pcc_v[1]) * phase_i[2]) / math.sqrt(3), rtol=0, atol=1e-9)
    np.testing.assert_allclose(storage_p, bus_v * storage_i, rtol=0, atol=1e-9)

    signed_traces = {"pcc_active_mean_w": pcc_p, "storage_absorbed_mean_w": storage_p,
                     "storage_absorbed_mean_a": storage_i, "bus_mean_v": bus_v,
                     "polarization_mean_v": polarization_v}
    for name, (start, stop) in protocol["windows_s"].items():
        window = slice(tick(start), tick(stop))
        limits = protocol["signed_window_limits"][name]
        for field, trace in signed_traces.items():
            low, high = limits[field]
            assert low < np.mean(trace[window]) < high, (name, field)
        assert abs(np.mean(pcc_q[window])) < limits["pcc_reactive_mean_abs_var_max"]
