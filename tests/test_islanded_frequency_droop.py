"""Verify the island circuit and applied-phase causal order without vendor data."""

import json
import math
from dataclasses import replace
from pathlib import Path
from runpy import run_path

import numpy as np
import pytest

from pycy_emt_lite import IdealSwitch, Inductor, OutputOptions, Resistor, run_case
from validation.cases.islanded_frequency_droop.checks import evaluate
from validation.cases.islanded_frequency_droop.compare import trace_from_result

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples/37_islanded_frequency_droop.py"
PROTOCOL = ROOT / "validation/cases/islanded_frequency_droop/candidate_protocol.json"


@pytest.fixture(scope="module")
def example():
    return run_path(str(EXAMPLE))["define_case"], json.loads(PROTOCOL.read_bytes())


def solve(case):
    return run_case(replace(case, output=OutputOptions(show_figure=False), plots=()))


@pytest.mark.parametrize("grid", ("5us", "2p5us"))
def test_feeder_loads_and_exact_integer_edge(example, grid):
    define_case, protocol = example
    step = protocol["grids"][grid]["step_s"]
    fixture = protocol["fixture"]
    case = define_case(time_step=step)
    assert case.config.stop_time == protocol["timing"]["duration_s"] and case.events == ()
    parts = {part.name: part for part in case.components}
    edge = protocol["timing"]["load_step_s"]
    for phase in "abc":
        feeder, base, added = (parts[f"{name}_{phase}"] for name in ("FeederL", "Base", "Added"))
        assert isinstance(feeder, Inductor) and feeder.inductance == fixture["feeder_h"] and feeder.initial_current == 0
        assert isinstance(base, Resistor) and base.resistance == fixture["base_load_ohm"]
        assert isinstance(added, IdealSwitch) and added.closed_resistance == fixture["added_load_ohm"]
        assert added.open_conductance == 1 / fixture["open_load_ohm"]
        assert (base.positive, base.negative) == (added.positive, added.negative) == (f"pcc_{phase}", "0")
        assert callable(added.closed) and not added.closed(edge - step)
        assert added.closed(edge) and added.closed(edge + step)


@pytest.mark.parametrize("grid", ("5us", "2p5us"))
def test_solved_power_updates_only_the_next_angle(example, grid):
    define_case, protocol = example
    step = protocol["grids"][grid]["step_s"]
    result = solve(define_case(time_step=step, stop_time=.004))
    trace = trace_from_result(result, len(result.rows))
    phase, frequency, filtered = (trace[key] for key in ("phase_rad", "frequency_hz", "filtered_w"))
    ctrl, limits = protocol["controller"], protocol["control_limits"]
    assert result.method == "trapezoidal" and len(phase) == round(.004 / step) + 1
    assert phase[0] == 0 and frequency[0] == ctrl["nominal_hz"] and filtered[0] == ctrl["initial_power_w"]
    np.testing.assert_array_equal(trace["feeder_a"][0], 0)
    np.testing.assert_array_equal(trace["source_v"][0], 0)
    power = np.sum(trace["pcc_v"] * trace["feeder_a"], axis=1)
    alpha = step / ctrl["filter_tau_s"]
    np.testing.assert_allclose(trace["meter_w"], power, rtol=0, atol=limits["power_meter_abs_w"])
    np.testing.assert_allclose(filtered[1:], (filtered[:-1] + alpha * power[1:]) / (1 + alpha),
                               rtol=0, atol=limits["filter_recurrence_abs_w"])
    np.testing.assert_allclose(np.diff(phase), math.tau * step * frequency[:-1],
                               rtol=0, atol=limits["angle_recurrence_abs_rad"])


@pytest.mark.slow
def test_added_load_increases_power_and_reduces_frequency(example):
    define_case, protocol = example
    result = solve(define_case())
    trace = trace_from_result(result, len(result.rows))
    report = evaluate(trace, result.time_step, protocol)
    assert report["passed"], report["checks"]
    assert report["windows"]["after"]["power_w"] > report["windows"]["before"]["power_w"]
    assert report["windows"]["after"]["frequency_hz"] < report["windows"]["before"]["frequency_hz"]
    edge = protocol["grids"]["5us"]["load_step_tick"]
    assert trace["load_on"][edge - 1] == 0 and trace["load_on"][edge] == 1
    assert trace["meter_w"][edge] < trace["meter_w"][edge - 1]
