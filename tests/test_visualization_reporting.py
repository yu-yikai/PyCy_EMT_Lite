"""
文件名称：test_visualization_reporting.py
文件作用：验证示例绘图、图像保存和结果报告。
"""

from __future__ import annotations

import runpy
from pathlib import Path

import matplotlib
import matplotlib.image
import pytest

from pycy_emt_lite import SimulationResult
from pycy_emt_lite.cases import run_case
from pycy_emt_lite.visualization import (
    plot_result_comparison,
    plot_zoom_window,
    write_markdown_report,
)

matplotlib.use("Agg")


@pytest.mark.parametrize("bad", ["case_parent", "case_absolute", "figure_parent", "kind", "columns", "root"])
def test_case_output_preflight_rejects_before_simulation(tmp_path, bad) -> None:
    from pycy_emt_lite import CaseDefinition, Resistor, SimulationConfig, VoltageSource
    from pycy_emt_lite.cases import OutputOptions, PlotSpec

    name = "../escape" if bad == "case_parent" else str(tmp_path / "absolute") if bad == "case_absolute" else "valid"
    plot = PlotSpec(("v:in",), figure_name="../../escape.png" if bad == "figure_parent" else "v.png",
                    kind="typo" if bad == "kind" else "three_phase" if bad == "columns" else "series")
    calls = []
    case = CaseDefinition(name, (VoltageSource("V", "in", "0", 1.0), Resistor("R", "in", "0", 1.0)),
                          SimulationConfig(0.1, 0.1), plots=(plot,),
                          output=OutputOptions(True, True, False, 42 if bad == "root" else tmp_path / "outputs"),
                          on_step=lambda row: calls.append(row) or {})
    with pytest.raises(ValueError):
        run_case(case)
    assert calls == []
    assert not (tmp_path / "outputs").exists()


@pytest.mark.parametrize("bad", ["root_file", "root_ancestor", "case_file", "figure_parent", "figure_directory", "suffix"])
def test_unusable_output_path_fails_before_callback(tmp_path, bad) -> None:
    from pycy_emt_lite import CaseDefinition, Resistor, SimulationConfig, VoltageSource
    from pycy_emt_lite.cases import OutputOptions, PlotSpec

    root = tmp_path / "outputs"
    figure = "wave.png"
    if bad in {"root_file", "root_ancestor"}:
        root.write_text("existing file", encoding="utf-8")
        if bad == "root_ancestor":
            root /= "nested"
    elif bad in {"case_file", "figure_parent", "figure_directory"}:
        root.mkdir()
        if bad == "case_file":
            (root / "valid").write_text("existing file", encoding="utf-8")
        else:
            (root / "valid").mkdir()
            if bad == "figure_parent":
                (root / "valid" / "nested").write_text("existing file", encoding="utf-8")
                figure = "nested/wave.png"
            else:
                (root / "valid" / figure).mkdir()
    else:
        figure = "wave.unsupported"
    calls = []
    case = CaseDefinition("valid", (VoltageSource("V", "in", "0", 1.0), Resistor("R", "in", "0", 1.0)),
                          SimulationConfig(0.1, 0.1), plots=(PlotSpec(("v:in",), figure),),
                          output=OutputOptions(False, True, False, root), on_step=lambda row: calls.append(row) or {})
    with pytest.raises(ValueError, match="输出|格式|图像"):
        run_case(case)
    assert calls == []


@pytest.mark.parametrize("kind", ["series", "three_phase", "comparison", "zoom"])
def test_failed_plot_does_not_leak_figures(kind) -> None:
    import matplotlib.pyplot as plt

    from pycy_emt_lite.visualization import plot_series, plot_three_phase

    before = plt.get_fignums()
    result = _result("missing")
    with pytest.raises(KeyError):
        if kind == "series":
            plot_series(result, ("absent",), show=False)
        elif kind == "three_phase":
            plot_three_phase(result, ("v:out", "absent", "v:out"), show=False)
        elif kind == "comparison":
            plot_result_comparison((result,), "absent", show=False)
        else:
            plot_zoom_window(result, ("absent",), 0.0, 0.1, show=False)
    assert plt.get_fignums() == before


def test_failed_save_closes_figure_and_pgf_skips_show(tmp_path, monkeypatch) -> None:
    import matplotlib.pyplot as plt
    from matplotlib.figure import Figure

    from pycy_emt_lite.visualization import plot_series
    from pycy_emt_lite.visualization.plotting import _show_if_interactive

    before = plt.get_fignums()
    def fail(*args, **kwargs):
        raise PermissionError("save failed")
    monkeypatch.setattr(Figure, "savefig", fail)
    with pytest.raises(PermissionError):
        plot_series(_result("save"), ("v:out",), tmp_path / "plot.png", show=False)
    assert plt.get_fignums() == before
    monkeypatch.setattr(matplotlib, "get_backend", lambda: "pgf")
    monkeypatch.setattr(plt, "show", fail)
    _show_if_interactive(True)


def test_report_escapes_text_and_links_relative_to_report(tmp_path) -> None:
    figure = tmp_path / "figures" / "wave [1].png"
    report = tmp_path / "reports" / "report.md"
    result = _result("case`[x]")
    write_markdown_report(result, report, title="Title [x] *special*", figure_paths=[figure], summary={"k[x]": "*value*"})
    text = report.read_text(encoding="utf-8")
    assert "../figures/wave%20%5B1%5D.png" in text
    assert "Title \\[x\\] \\*special\\*" in text
    assert "``case`[x]``" in text


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
