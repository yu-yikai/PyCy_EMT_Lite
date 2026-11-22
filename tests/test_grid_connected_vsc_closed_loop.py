"""Check closed-loop teaching timing and PI state without the native archive."""

import math
import runpy
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from pycy_emt_lite.cases import OutputOptions, run_case

EXAMPLE = Path(__file__).resolve().parents[1] / "examples/29_grid_connected_vsc_closed_loop.py"
PHASES = "abc"


@pytest.fixture(scope="module")
def define_case():
    return runpy.run_path(str(EXAMPLE))["define_case"]


@pytest.mark.parametrize("step", [5e-6, 2.5e-6])
def test_sample_uses_measured_row_before_next_gate_update(define_case, step):
    case = define_case(time_step=step, stop_time=.00031)
    result = run_case(replace(case, plots=(), output=OutputOptions(show_figure=False), summary=None))
    samples = round(100e-6 / step)
    gate_hold = round(5e-6 / step)
    count = len(result.series("time"))
    row = np.arange(count)
    sample_rows = row[(row > 0) & (row % samples == 0)]
    np.testing.assert_array_equal(np.flatnonzero(result.series("sample_update")), sample_rows)
    for phase in PHASES:
        pending = np.asarray(result.series(f"pending_{phase}"))
        applied = np.asarray(result.series(f"applied_{phase}"))
        expected = np.zeros(count)
        for sample in sample_rows:
            expected[sample + gate_hold:] = pending[sample]
        np.testing.assert_array_equal(applied, expected)
        carrier = np.abs((row // gate_hold) % 200 - 100) / 50 - 1
        upper = applied >= carrier
        np.testing.assert_array_equal(result.series(f"state:S{phase}_upper"), upper)
        np.testing.assert_array_equal(result.series(f"state:S{phase}_lower"), ~upper)
    assert any(result.series(f"pending_{phase}")[samples] != 0 for phase in PHASES)


def measured_row(time, *, ed=30., eq=0., id_=-1., iq=2.):
    """Construct a balanced row from the inverse projection equations."""
    angle = 2 * math.pi * 60 * time - math.pi / 2
    row = {"time": time}
    for phase, shift in zip(PHASES, (0., -2 * math.pi / 3, 2 * math.pi / 3), strict=True):
        c, s = math.cos(angle + shift), math.sin(angle + shift)
        row[f"v:grid_{phase}"] = c*ed - s*eq
        row[f"i:L{phase}"] = c*id_ - s*iq
    return row


def test_vector_limit_rolls_back_both_integrators_and_recovers(define_case):
    case = define_case()
    sample = case.on_step
    assert sample is not None
    sample(measured_row(0.))
    ordinary = sample(measured_row(.0001))
    limited = sample(measured_row(.0002, ed=400.))
    recovered = sample(measured_row(.0003))
    assert ordinary["saturated"] == recovered["saturated"] == 0
    assert limited["saturated"] == 1
    increment = 2 * math.pi * 100 * .0001
    for name, error in (("z_d", 1.), ("z_q", -2.)):
        assert ordinary[name] == pytest.approx(error*increment)
        assert limited[name] == ordinary[name]
        assert recovered[name] == pytest.approx(2*error*increment)
    limited_modulation = math.sqrt(sum(limited[f"pending_{p}"]**2 for p in PHASES)*2/3)
    assert limited_modulation == pytest.approx(.95)

    independent = define_case().on_step
    assert independent is not None
    initial = independent(measured_row(0.))
    assert initial["z_d"] == initial["z_q"] == initial["saturated"] == 0
    assert all(initial[f"pending_{p}"] == initial[f"applied_{p}"] == 0 for p in PHASES)


@pytest.mark.parametrize("step", [5e-6, 2.5e-6])
@pytest.mark.parametrize(("scenario", "q_at_second_step"), [("main", 1.5), ("d_only", 0.)])
def test_command_updates_on_the_frozen_sampling_rows(define_case, step, scenario, q_at_second_step):
    sample = define_case(scenario=scenario, time_step=step).on_step
    assert sample is not None
    for time, expected in [(0., (0., 0.)), (.04 - step, (0., 0.)), (.04, (2., 0.)),
                           (.08 - step, (2., 0.)), (.08, (2., q_at_second_step))]:
        row = sample(measured_row(time))
        assert (row["id_ref"], row["iq_ref"]) == expected


def test_scenarios_and_steps_are_checked(define_case):
    with pytest.raises(ValueError):
        define_case(scenario="q_only")
    with pytest.raises(ValueError):
        define_case(time_step=1e-6)
