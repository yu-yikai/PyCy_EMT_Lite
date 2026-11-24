"""Analytic fixtures test feature mathematics, never vendor reference evidence."""

import copy
import json
import math
from pathlib import Path

import numpy as np
import pytest

from pycy_emt_lite.io.results import SimulationResult
from validation.cases.two_level_pwm.compare import (
    add_feature_report,
    compare_features,
    current_features,
)


def manifest():
    path = Path(__file__).resolve().parents[1] / "validation/cases/two_level_pwm/manifest.json"
    return json.loads(path.read_text(encoding="utf-8"))


def sine_result(*, factor=1.0, phase_degrees=0.0, reference=False, count=12001):
    time = np.linspace(0, 0.2, count)
    columns = ("i_a", "i_b", "i_c") if reference else ("i:La", "i:Lb", "i:Lc")
    values = {
        column: factor * 100 * math.sqrt(2) * np.sin(2 * math.pi * 60 * time + math.radians(shift + phase_degrees))
        for column, shift in zip(columns, (170, 50, -70), strict=True)
    }
    rows = [{"time": t, **{key: array[index] for key, array in values.items()}} for index, t in enumerate(time)]
    return SimulationResult("synthetic analytic fixture", "analytic", time[1], time[-1], rows)


def test_fixed_frequency_projection_matches_analytic_sine_rms_and_phase():
    result = sine_result(phase_degrees=25)
    actual = current_features(result, "i:La", start=0.1, end=0.2, frequency=60)
    assert actual["total_rms_ampere"] == pytest.approx(100, rel=4e-6)
    assert actual["fundamental_rms_ampere"] == pytest.approx(100, rel=4e-6)
    assert actual["fundamental_phase_degrees"] == pytest.approx(-165, abs=1e-9)
    assert actual["mean_ampere"] == pytest.approx(0, abs=1e-12)


def test_piecewise_linear_projection_integrates_nonuniform_ramp_exactly():
    # i=t on 0..1 s: integral(t*sin(2*pi*t))=-1/(2*pi), integral(t*cos(...))=0.
    result = SimulationResult("analytic ramp", "linear", 0.0, 1.0,
                              [{"time": t, "i": t} for t in (0.0, 0.13, 0.8, 1.0)])
    actual = current_features(result, "i", start=0, end=1, frequency=1)
    assert actual["total_rms_ampere"] == pytest.approx(1 / math.sqrt(3))
    assert actual["mean_ampere"] == pytest.approx(0.5)
    assert actual["fundamental_rms_ampere"] == pytest.approx(1 / (math.sqrt(2) * math.pi))
    assert abs(actual["fundamental_phase_degrees"]) == pytest.approx(180)


def test_known_three_phase_load_rms_and_mean_dissipation():
    report = compare_features(sine_result(), sine_result(reference=True, count=16001), manifest(), 1.0)
    assert report["passed"]
    assert report["load_mean_power"]["candidate_watt"] == pytest.approx(30000, rel=7e-6)
    assert report["load_mean_power"]["positive_absorption"]
    assert all(phase["fundamental_phase_error_degrees"] < 1e-9 for phase in report["phases"].values())


def test_reversed_current_fails_phase_even_though_rms_and_dissipation_match():
    report = add_feature_report({"passed": True}, sine_result(factor=-1), sine_result(reference=True), manifest(), 1)
    assert report["waveform_passed"]
    assert not report["passed"]
    assert report["features"]["load_mean_power"]["passed"]
    for phase in report["features"]["phases"].values():
        assert phase["relative_rms_error"] == pytest.approx(0)
        assert phase["fundamental_phase_error_degrees"] == pytest.approx(180)
        assert not phase["passed"]


def test_load_power_limit_is_independent_of_phase_rms_limit():
    report = compare_features(sine_result(factor=1.03), sine_result(reference=True), manifest(), 1)
    assert all(phase["passed"] for phase in report["phases"].values())
    assert report["load_mean_power"]["relative_error"] == pytest.approx(1.03**2 - 1)
    assert not report["load_mean_power"]["passed"]
    assert not report["passed"]


def test_phase_error_wraps_across_minus_and_plus_180_degrees():
    report = compare_features(sine_result(phase_degrees=11),
                              sine_result(reference=True, phase_degrees=9), manifest(), 1)
    assert report["passed"]
    assert report["phases"]["i:La"]["candidate_features"]["fundamental_phase_degrees"] < -170
    assert report["phases"]["i:La"]["reference_features"]["fundamental_phase_degrees"] > 170
    assert report["phases"]["i:La"]["fundamental_phase_error_degrees"] == pytest.approx(2)


@pytest.mark.parametrize("start,end,frequency", [(0.1, 0.19, 60), (-0.1, 0.2, 60), (0.1, 0.2, 0)])
def test_rejects_fractional_cycles_extrapolation_or_invalid_frequency(start, end, frequency):
    with pytest.raises(ValueError):
        current_features(sine_result(), "i:La", start=start, end=end, frequency=frequency)


def test_feature_failure_cannot_leave_waveform_only_pass():
    bad_manifest = copy.deepcopy(manifest())
    bad_manifest["feature_criteria"]["fundamental_hz"] = 0
    report = {"passed": True}
    with pytest.raises(ValueError):
        add_feature_report(report, sine_result(), sine_result(reference=True), bad_manifest, 1)
    assert report["waveform_passed"]
    assert not report["passed"]
    assert "ValueError" in report["feature_evaluation_error"]
