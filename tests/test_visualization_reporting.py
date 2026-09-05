"""
文件名称：test_visualization_reporting.py
文件作用：验证阶段 6 可视化增强和自动报告。
"""

from __future__ import annotations

import matplotlib

from pycy_emt_lite import SimulationResult
from pycy_emt_lite.visualization import plot_result_comparison, plot_zoom_window, write_markdown_report

matplotlib.use("Agg")


def _result(name: str, scale: float = 1.0) -> SimulationResult:
    rows = [
        {"time": 0.0, "v:out": 0.0},
        {"time": 0.1, "v:out": scale},
        {"time": 0.2, "v:out": 2.0 * scale},
    ]
    return SimulationResult(name, "manual", 0.1, 0.2, rows)


def test_plot_result_comparison_and_zoom_export(tmp_path) -> None:
    comparison_path = tmp_path / "comparison.png"
    zoom_path = tmp_path / "zoom.svg"

    plot_result_comparison([_result("a"), _result("b", 2.0)], "v:out", output_path=comparison_path, show=False)
    plot_zoom_window(_result("zoom"), ["v:out"], 0.05, 0.15, output_path=zoom_path, show=False)

    assert comparison_path.exists()
    assert zoom_path.exists()


def test_write_markdown_report(tmp_path) -> None:
    path = tmp_path / "report.md"

    write_markdown_report(_result("report"), path, summary={"最大值": 2.0})

    content = path.read_text(encoding="utf-8")
    assert "## 仿真信息" in content
    assert "`v:out`" in content
    assert "最大值" in content
