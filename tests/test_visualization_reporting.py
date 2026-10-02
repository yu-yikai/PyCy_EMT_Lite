"""
文件名称：test_visualization_reporting.py
文件作用：验证示例绘图、图像保存和结果报告。
"""

from __future__ import annotations

from pathlib import Path
import runpy

import matplotlib
import matplotlib.image
import pytest

from pycy_emt_lite import SimulationResult
from pycy_emt_lite.cases import run_case
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


@pytest.mark.parametrize("filename, images", [
    ("01_r_circuit.py", {"voltage.png", "current.png"}),
    ("02_rc_transient.py", {"voltage.png"}),
    ("03_rl_transient.py", {"current.png"}),
    ("04_rlc_transient.py", {"voltage.png", "current.png"}),
    ("07_single_phase_ground_fault.py", {"voltages.png"}),
])
def test_example_figure_save_switch_creates_readable_images(filename, images, tmp_path, monkeypatch) -> None:
    example = runpy.run_path(str(Path(__file__).resolve().parents[1] / "examples" / filename))
    namespace = example["define_case"].__globals__
    monkeypatch.setitem(namespace, "SAVE_RESULT_FIGURE", 1)
    monkeypatch.setitem(namespace, "SHOW_FIGURE", False)
    monkeypatch.chdir(tmp_path)

    case = example["define_case"]()
    run_case(case)

    paths = list((tmp_path / "outputs" / case.name).iterdir())
    assert {path.name for path in paths} == images
    for path in paths:
        pixels = matplotlib.image.imread(path)
        assert pixels.shape[0] > 0 and pixels.shape[1] > 0
        assert pixels.max() > pixels.min()


@pytest.mark.parametrize("resistance, inductance, capacitance", [
    (100.0, 0.01, 1e-5),  # 原示例改成过阻尼。
    (2.0, 1.0, 1.0),  # 临界阻尼，避免除以零。
])
def test_rlc_example_non_underdamped_summary_still_reaches_plotting(
    resistance, inductance, capacitance, monkeypatch, capsys,
) -> None:
    example = runpy.run_path(str(Path(__file__).resolve().parents[1] / "examples/04_rlc_transient.py"))
    namespace = example["define_case"].__globals__
    for key, value in (("RESISTANCE", resistance), ("INDUCTANCE", inductance), ("CAPACITANCE", capacitance)):
        monkeypatch.setitem(namespace, key, value)
    plotted = []
    monkeypatch.setattr("pycy_emt_lite.cases.plot_series", lambda result, *args, **kwargs: plotted.append(result))

    result = run_case(example["define_case"]())

    assert len(result.rows) == 5001
    assert plotted and all(item is result for item in plotted)
    assert "跳过欠阻尼解析对比" in capsys.readouterr().out
