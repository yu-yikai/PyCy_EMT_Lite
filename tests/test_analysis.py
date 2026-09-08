"""
文件名称：test_analysis.py
文件作用：验证基础结果分析函数。
"""

import math

import pytest

from pycy_emt_lite.analysis import (
    instantaneous_three_phase_power,
    mean_value,
    peak_abs,
    rms,
    three_phase_power,
    voltage_sag_summary,
)
from pycy_emt_lite.io.results import SimulationResult


def test_basic_analysis_metrics() -> None:
    result = SimulationResult(
        circuit_name="metrics",
        method="test",
        time_step=1.0,
        stop_time=3.0,
        rows=[
            {"time": 0.0, "x": 1.0},
            {"time": 1.0, "x": -1.0},
            {"time": 2.0, "x": 1.0},
            {"time": 3.0, "x": -1.0},
        ],
    )

    assert math.isclose(rms(result, "x"), 1.0 / math.sqrt(3.0))
    assert math.isclose(peak_abs(result, "x"), 1.0)
    assert math.isclose(mean_value(result, "x"), 0.0)


def test_linear_metrics_use_real_time_and_ignore_redundant_samples() -> None:
    sparse = SimulationResult(
        "sparse",
        "test",
        1.0,
        1.0,
        [{"time": 0.0, "x": 0.0}, {"time": 1.0, "x": 1.0}],
    )
    refined = SimulationResult(
        "refined",
        "test",
        1.0,
        1.0,
        [{"time": 0.0, "x": 0.0}, {"time": 0.1, "x": 0.1}, {"time": 1.0, "x": 1.0}],
    )

    for result in (sparse, refined):
        assert math.isclose(mean_value(result, "x"), 0.5, rel_tol=0.0, abs_tol=1e-12)
        assert math.isclose(rms(result, "x"), math.sqrt(1.0 / 3.0), rel_tol=0.0, abs_tol=1e-12)


def test_linear_metrics_interpolate_window_boundaries() -> None:
    result = SimulationResult(
        "window",
        "test",
        1.0,
        1.0,
        [{"time": 0.0, "x": 0.0}, {"time": 1.0, "x": 1.0}],
    )

    assert math.isclose(mean_value(result, "x", start_time=0.2, end_time=0.8), 0.5, abs_tol=1e-12)
    expected_rms = math.sqrt((0.8**3 - 0.2**3) / (3.0 * (0.8 - 0.2)))
    assert math.isclose(rms(result, "x", start_time=0.2, end_time=0.8), expected_rms, abs_tol=1e-12)


@pytest.mark.parametrize(
    ("times", "message"),
    [
        ([0.0, math.nan], "有限"),
        ([0.0, math.inf], "有限"),
        ([0.0, 0.0], "严格递增"),
        ([1.0, 0.0], "严格递增"),
    ],
)
def test_continuous_metrics_reject_invalid_time_axes(times: list[float], message: str) -> None:
    result = SimulationResult("bad_time", "test", 1.0, times[-1], [{"time": t, "x": 1.0} for t in times])

    with pytest.raises(ValueError, match=message):
        rms(result, "x")


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
def test_metrics_reject_nonfinite_signal_values(value: float) -> None:
    result = SimulationResult(
        "bad_signal",
        "test",
        1.0,
        1.0,
        [{"time": 0.0, "x": 1.0}, {"time": 1.0, "x": value}],
    )

    with pytest.raises(ValueError, match="结果列必须只包含有限数"):
        rms(result, "x")


def test_continuous_metrics_reject_invalid_windows_and_single_sample() -> None:
    result = SimulationResult(
        "window",
        "test",
        1.0,
        1.0,
        [{"time": 0.0, "x": 0.0}, {"time": 1.0, "x": 1.0}],
    )

    with pytest.raises(ValueError, match="范围"):
        mean_value(result, "x", start_time=-0.1)
    with pytest.raises(ValueError, match="范围"):
        rms(result, "x", end_time=1.1)
    with pytest.raises(ValueError, match="正时长"):
        rms(result, "x", start_time=0.5, end_time=0.5)
    with pytest.raises(ValueError, match="至少需要两个"):
        mean_value(SimulationResult("one", "test", 1.0, 0.0, [{"time": 0.0, "x": 2.0}]), "x")

    assert peak_abs(result, "x", start_time=1.0, end_time=1.0) == 1.0


def test_continuous_metrics_reject_intervals_that_cross_events() -> None:
    result = SimulationResult(
        "event",
        "test",
        0.1,
        0.2,
        [
            {"time": 0.0, "x": 0.0},
            {"time": 0.1, "x": 0.1},
            {"time": 0.15, "x": 1.0},
            {"time": 0.2, "x": 1.1},
        ],
        event_log=[{"time": 0.15, "type": "fault_apply"}],
    )

    with pytest.raises(ValueError, match="事件"):
        mean_value(result, "x", start_time=0.1, end_time=0.15)
    with pytest.raises(ValueError, match="事件"):
        rms(result, "x", start_time=0.14, end_time=0.2)
    assert math.isclose(mean_value(result, "x", start_time=0.15, end_time=0.2), 1.05, abs_tol=1e-12)


def test_instantaneous_three_phase_power_includes_zero_sequence() -> None:
    result = SimulationResult(
        "zero_sequence",
        "test",
        1.0,
        1.0,
        [
            {"time": 0.0, "v:a": 1.0, "v:b": 1.0, "v:c": 1.0, "i:a": 1.0, "i:b": 1.0, "i:c": 1.0},
            {"time": 1.0, "v:a": 1.0, "v:b": 1.0, "v:c": 1.0, "i:a": 1.0, "i:b": 1.0, "i:c": 1.0},
        ],
    )

    active, reactive = instantaneous_three_phase_power(
        result,
        ("v:a", "v:b", "v:c"),
        ("i:a", "i:b", "i:c"),
    )

    assert active.tolist() == [3.0, 3.0]
    assert reactive.tolist() == [0.0, 0.0]


def test_three_phase_power_average_uses_real_time() -> None:
    result = SimulationResult(
        "power_time",
        "test",
        1.0,
        1.0,
        [
            {"time": 0.0, "v:a": 0.0, "v:b": 0.0, "v:c": 0.0, "i:a": 1.0, "i:b": 0.0, "i:c": 0.0},
            {"time": 0.1, "v:a": 1.0, "v:b": 0.0, "v:c": 0.0, "i:a": 1.0, "i:b": 0.0, "i:c": 0.0},
            {"time": 1.0, "v:a": 1.0, "v:b": 0.0, "v:c": 0.0, "i:a": 1.0, "i:b": 0.0, "i:c": 0.0},
        ],
    )

    summary = three_phase_power(result, ("v:a", "v:b", "v:c"), ("i:a", "i:b", "i:c"))

    assert math.isclose(summary.active_power, 0.95, rel_tol=0.0, abs_tol=1e-12)


def test_three_phase_power_integrates_linear_voltage_current_products_exactly() -> None:
    def result_at(times: list[float]) -> SimulationResult:
        return SimulationResult(
            "linear_power",
            "test",
            1.0,
            1.0,
            [
                {
                    "time": time,
                    "v:a": time,
                    "v:b": 0.0,
                    "v:c": 0.0,
                    "i:a": time,
                    "i:b": 0.0,
                    "i:c": 0.0,
                }
                for time in times
            ],
        )

    for result in (result_at([0.0, 1.0]), result_at([0.0, 0.1, 1.0])):
        summary = three_phase_power(result, ("v:a", "v:b", "v:c"), ("i:a", "i:b", "i:c"))
        windowed = three_phase_power(
            result,
            ("v:a", "v:b", "v:c"),
            ("i:a", "i:b", "i:c"),
            start_time=0.2,
            end_time=0.8,
        )

        assert math.isclose(summary.active_power, 1.0 / 3.0, rel_tol=0.0, abs_tol=1e-12)
        assert math.isclose(windowed.active_power, 0.28, rel_tol=0.0, abs_tol=1e-12)


def test_three_phase_power_reports_balanced_active_power() -> None:
    rows = []
    for index in range(200):
        time = index * 1e-4
        angle = 2.0 * math.pi * 50.0 * time
        rows.append(
            {
                "time": time,
                "v:a": math.sqrt(2.0) * 230.0 * math.sin(angle),
                "v:b": math.sqrt(2.0) * 230.0 * math.sin(angle - 2.0 * math.pi / 3.0),
                "v:c": math.sqrt(2.0) * 230.0 * math.sin(angle + 2.0 * math.pi / 3.0),
                "i:a": math.sqrt(2.0) * 10.0 * math.sin(angle),
                "i:b": math.sqrt(2.0) * 10.0 * math.sin(angle - 2.0 * math.pi / 3.0),
                "i:c": math.sqrt(2.0) * 10.0 * math.sin(angle + 2.0 * math.pi / 3.0),
            }
        )
    result = SimulationResult("power", "test", 1e-4, 0.0199, rows)

    summary = three_phase_power(result, ("v:a", "v:b", "v:c"), ("i:a", "i:b", "i:c"))

    assert math.isclose(summary.active_power, 6900.0, rel_tol=1e-3)
    assert abs(summary.reactive_power) < 1e-9
    assert math.isclose(summary.power_factor, 1.0, rel_tol=1e-9)


def test_voltage_sag_summary_finds_worst_phase() -> None:
    result = SimulationResult(
        "sag",
        "test",
        1e-3,
        2e-3,
        [
            {"time": 0.0, "v:a": 230.0, "v:b": 120.0, "v:c": 230.0},
            {"time": 1e-3, "v:a": 230.0, "v:b": 120.0, "v:c": 230.0},
        ],
    )

    summary = voltage_sag_summary(result, ("v:a", "v:b", "v:c"), nominal_rms=230.0)

    assert summary.sag_detected
    assert summary.worst_column == "v:b"
