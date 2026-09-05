# Visualization and Automated Reporting

[简体中文](visualization_reporting.md)

## Multiple-result comparison

```python
from pycy_emt_lite.visualization import plot_result_comparison
plot_result_comparison([result_a, result_b], "v:out", labels=["A", "B"])
```

This supports parameter sweeps, reference reproduction, and control comparisons.

## Zoomed windows

```python
from pycy_emt_lite.visualization import plot_zoom_window
plot_zoom_window(result, ["v:load:a"], 0.08, 0.12)
```

Use this for fault application, fault clearing, and power-step transients.

## Figure export

Plotting functions accept `output_path` and Matplotlib formats such as PNG, SVG, and PDF. Examples write files only when `SAVE_RESULT_FIGURE = 1`.

## Markdown reports

```python
from pycy_emt_lite.visualization import write_markdown_report
write_markdown_report(result, "outputs/report.md", summary={"maximum voltage": 1.02})
```

Markdown is convenient for lessons, lab records, and later HTML/PDF conversion.

## Result-field conventions

Use exact result column names when comparing or plotting. For a three-phase quantity, pass all phase columns explicitly. For event studies, use a bounded time window so that pre-event and post-event behavior remain visible.

The plotting layer is for inspection and reporting. It must not change the raw `SimulationResult`, apply undocumented normalization, or replace numerical assertions in `pytest`.
