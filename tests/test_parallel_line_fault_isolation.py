"""Test the three-bus circuit, switch edges and receiving-end backfeed."""

import json
from dataclasses import replace
from pathlib import Path
from runpy import run_path

import numpy as np
import pytest

from pycy_emt_lite import IdealSwitch, OutputOptions, run_case
from validation.cases.parallel_line_fault_isolation.checks import evaluate, load_power
from validation.cases.parallel_line_fault_isolation.compare import trace_from_result

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples/38_parallel_line_fault_isolation.py"
PROTOCOL = ROOT / "validation/cases/parallel_line_fault_isolation/candidate_protocol.json"


@pytest.fixture(scope="module")
def example():
    return run_path(str(EXAMPLE))["define_case"], json.loads(PROTOCOL.read_bytes())


@pytest.mark.parametrize("grid", ("50us", "25us"))
def test_each_pole_has_the_frozen_edge_and_resistance(example, grid):
    define_case, protocol = example
    h = protocol["grids"][grid]["step_s"]
    fixture, timing = (protocol[key] for key in ("fixture", "timing"))
    case = define_case(time_step=h)
    assert case.config.stop_time == timing["duration_s"] and case.events == ()
    parts = {part.name: part for part in case.components}
    for label, first, last, initial, resistance, nodes in (
        ("SF", "open_sf_s", "reclose_s", True, "path_on_ohm", ("src", "fault")),
        ("RF", "open_rf_s", "reclose_s", True, "path_on_ohm", ("recv", "fault")),
        ("Fault", "fault_on_s", "fault_off_s", False, "fault_on_ohm", ("fault", "0")),
    ):
        a, b = timing[first], timing[last]
        for phase in "abc":
            switch = parts[f"{label}_{phase}"]
            positive, negative = (f"{node}:{phase}" if node != "0" else node for node in nodes)
            assert isinstance(switch, IdealSwitch) and callable(switch.closed)
            assert switch.closed_resistance == fixture[resistance]
            assert switch.open_conductance == 1 / fixture["open_ohm"]
            assert (switch.positive, switch.negative) == (positive, negative)
            assert (switch.closed(0), switch.closed(a - h), switch.closed(a),
                    switch.closed(b - h), switch.closed(b)) == (initial, initial, not initial, not initial, initial)


@pytest.mark.parametrize("grid", ("50us", "25us"))
def test_backfeed_isolation_and_receiving_load_restoration(example, grid):
    define_case, protocol = example
    fixture, grid = protocol["fixture"], protocol["grids"][grid]
    h = grid["step_s"]
    case = define_case(time_step=h)
    result = run_case(replace(case, plots=(), output=OutputOptions(show_figure=False)))
    assert len(result.rows) == grid["rows_including_zero"] and result.method == "trapezoidal"
    trace = trace_from_result(result, fixture)
    report = evaluate(trace, h, protocol)
    assert report["passed"], report["checks"]
    assert trace["time_s"][0] == 0 and abs(trace["v_src"][0, 1]) > 100
    np.testing.assert_allclose(result.series("receiving_power_w"), load_power(trace), rtol=0,
                               atol=protocol["physical_limits"]["power_abs_w"])
    windows = report["windows"]
    single, isolated, restored = (windows[key] for key in ("source_end_open", "both_ends_open", "restored"))
    assert single["rf_signed_rms_a"] > 25
    assert abs(isolated["rf_signed_rms_a"]) < 2e-7 and isolated["load_mean_w"] > 1700
    assert restored["rf_signed_rms_a"] < -1
    assert restored["load_mean_w"] == pytest.approx(windows["pre"]["load_mean_w"], rel=0, abs=2e-4)
