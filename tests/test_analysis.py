"""
文件名称：test_analysis.py
文件作用：验证基础结果分析函数。
"""

import math

from pycy_emt_lite.analysis import mean_value, peak_abs, rms, three_phase_power, voltage_sag_summary
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

    assert math.isclose(rms(result, "x"), 1.0)
    assert math.isclose(peak_abs(result, "x"), 1.0)
    assert math.isclose(mean_value(result, "x"), 0.0)


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
