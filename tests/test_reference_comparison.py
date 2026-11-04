"""Independent arithmetic and failure cases for cross-platform comparison tools."""

import math

import pytest

from pycy_emt_lite.io.results import SimulationResult
from validation.common.comparison import SignalSpec, compare_signals


def result(times, values, events=()):
    return SimulationResult("fixture", "manual", 1.0, times[-1],
                            [{"time": t, "x": x} for t, x in zip(times, values, strict=True)], list(events))


def test_nonuniform_sampling_integrates_linear_error_and_clipped_window():
    candidate = result([0.0, 0.1, 1.0], [0.0, 0.2, 2.0])
    reference = result([0.0, 0.7, 1.0], [0.0, 0.7, 1.0])
    spec = SignalSpec("x", "x", "V", 2.0, 0.4, 0.8)
    report = compare_signals(candidate, reference, [spec], start=0.2, end=0.8)
    metrics = report["signals"]["x"]
    assert metrics["rmse"] == pytest.approx(math.sqrt(0.28))
    assert metrics["nrmse"] == pytest.approx(math.sqrt(0.28) / 2)
    assert metrics["max_abs_error"] == pytest.approx(0.8)
    assert metrics["reference_mean"] == pytest.approx(0.5)
    assert report["passed"]


def test_power_direction_error_fails_without_amplitude_or_time_fitting():
    candidate = result([0.0, 1.0], [-5.0, -5.0])
    reference = result([0.0, 1.0], [5.0, 5.0])
    report = compare_signals(candidate, reference, [SignalSpec("x", "x", "W", 5.0, 0.05, 0.5)], start=0, end=1)
    assert not report["passed"]
    assert report["signals"]["x"]["nrmse"] == 2


@pytest.mark.parametrize("times,values", [([0, 0], [1, 1]), ([0, 1], [1, math.nan]), ([0, math.inf], [1, 1])])
def test_rejects_invalid_data(times, values):
    with pytest.raises(ValueError):
        compare_signals(result(times, values), result([0, 1], [1, 1]),
                        [SignalSpec("x", "x", "V", 1, 0.1, 0.1)], start=0, end=1)


def test_rejects_extrapolation_and_cross_event_interpolation():
    spec = [SignalSpec("x", "x", "V", 1, 0.1, 0.1)]
    reference = result([0, 1], [1, 1])
    with pytest.raises(ValueError, match="extrapolation"):
        compare_signals(reference, reference, spec, start=-0.1, end=1)
    event_result = result([0, 0.5, 1], [0, 1, 1], [{"time": 0.5}])
    with pytest.raises(ValueError, match="event"):
        compare_signals(event_result, reference, spec, start=0.2, end=0.8)
    assert compare_signals(event_result, reference, spec, start=0.5, end=1)["passed"]


@pytest.mark.parametrize("scale,limit", [(0, 0.1), (math.inf, 0.1), (1, -1), (True, 0.1)])
def test_rejects_invalid_engineering_scales_and_limits(scale, limit):
    with pytest.raises(ValueError):
        SignalSpec("x", "x", "V", scale, limit, 0.1)
