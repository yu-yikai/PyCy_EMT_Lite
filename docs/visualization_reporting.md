# 可视化与自动报告

[English](visualization_reporting.en.md)

当前版本在基础 `plot_series()` 和 `plot_three_phase()` 之外提供以下结果展示与报告工具。

## 1. 多结果对比

```python
from pycy_emt_lite.visualization import plot_result_comparison

plot_result_comparison([result_a, result_b], "v:out", labels=["A", "B"])
```

该函数适合参数扫描、参考软件复现和控制策略对比。

## 2. 局部放大

```python
from pycy_emt_lite.visualization import plot_zoom_window

plot_zoom_window(result, ["v:load:a"], 0.08, 0.12)
```

该函数用于观察故障投入、故障清除、功率阶跃等局部暂态过程。

## 3. 图像导出

绘图函数都支持 `output_path`，后缀可使用 Matplotlib 支持的 PNG、SVG、PDF 等格式。示例默认仍只显示图，不保存图像；只有 `SAVE_RESULT_FIGURE = 1` 时才写文件。

## 4. Markdown 报告

```python
from pycy_emt_lite.visualization import write_markdown_report

write_markdown_report(
    result,
    "outputs/report.md",
    summary={"最大电压": 1.02},
)
```

第一版报告输出 Markdown，便于课程讲义、实验记录和后续转换为 HTML/PDF。
