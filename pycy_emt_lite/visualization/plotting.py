"""
文件名称：plotting.py
文件作用：提供基础波形、三相波形、多结果对比和局部放大绘图函数。
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Protocol

import numpy as np


class PlottableResult(Protocol):
    """绘图只依赖时间/信号读取，不要求旧行式结果。"""

    def series(self, column: str) -> Sequence[float]: ...


def plot_series(
    result: PlottableResult,
    columns: Iterable[str],
    output_path: str | Path | None = None,
    *,
    show: bool = True,
    title: str | None = None,
) -> None:
    """绘制一个或多个结果字段随时间变化的曲线。

    示例算例默认显示图形窗口，便于学习者直接观察波形。`output_path` 仅作为可选
    参数保留给报告生成、批量仿真等需要保存图片的场景。
    """

    import matplotlib.pyplot as plt

    time = np.asarray(result.series("time"), dtype=float)
    figure, axes = plt.subplots()
    for column in columns:
        axes.plot(time, result.series(column), label=column)
    axes.set_xlabel("time / s")
    axes.set_ylabel("value")
    if title is not None:
        axes.set_title(title)
    axes.grid(True)
    axes.legend()
    if output_path is not None:
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        figure.savefig(target, dpi=150, bbox_inches="tight")
    _show_if_interactive(show)
    plt.close(figure)


def plot_result_comparison(
    results: Iterable[PlottableResult],
    column: str,
    labels: Iterable[str] | None = None,
    output_path: str | Path | None = None,
    *,
    show: bool = True,
) -> None:
    """绘制多个仿真结果的同一字段对比曲线。"""

    import matplotlib.pyplot as plt

    result_list = list(results)
    if not result_list:
        raise ValueError("结果对比至少需要一个 SimulationResult。")
    label_list = list(labels) if labels is not None else [_result_label(result) for result in result_list]
    if len(label_list) != len(result_list):
        raise ValueError("对比标签数量必须与结果数量一致。")

    figure, axes = plt.subplots()
    for result, label in zip(result_list, label_list, strict=True):
        axes.plot(result.series("time"), result.series(column), label=label)
    axes.set_xlabel("time / s")
    axes.set_ylabel(column)
    axes.grid(True)
    axes.legend()
    _save_show_close(figure, output_path, show)


def plot_zoom_window(
    result: PlottableResult,
    columns: Iterable[str],
    start_time: float,
    end_time: float,
    output_path: str | Path | None = None,
    *,
    show: bool = True,
    title: str | None = None,
) -> None:
    """绘制指定时间窗内的局部放大波形。"""

    if start_time >= end_time:
        raise ValueError("局部放大起始时间必须小于结束时间。")
    import matplotlib.pyplot as plt

    time = np.asarray(result.series("time"), dtype=float)
    mask = (time >= start_time) & (time <= end_time)
    if not mask.any():
        raise ValueError("指定局部放大时间窗内没有结果采样点。")
    figure, axes = plt.subplots()
    for column in columns:
        values = np.asarray(result.series(column), dtype=float)
        axes.plot(time[mask], values[mask], label=column)
    axes.set_xlabel("time / s")
    axes.set_ylabel("value")
    if title is not None:
        axes.set_title(title)
    axes.grid(True)
    axes.legend()
    _save_show_close(figure, output_path, show)


def plot_three_phase(
    result: PlottableResult,
    columns: tuple[str, str, str],
    output_path: str | Path | None = None,
    *,
    show: bool = True,
    title: str | None = None,
) -> None:
    """绘制三相波形。

    三相字段按 a、b、c 的顺序传入，例如：
    `("v:load:a", "v:load:b", "v:load:c")`。函数本身不假设字段前缀，
    因而可用于电压、电流或其他三相分析量。
    """

    import matplotlib.pyplot as plt

    time = np.asarray(result.series("time"), dtype=float)
    figure, axes = plt.subplots()
    labels = ("A 相", "B 相", "C 相")
    for column, label in zip(columns, labels, strict=True):
        axes.plot(time, result.series(column), label=f"{label} {column}")
    axes.set_xlabel("time / s")
    axes.set_ylabel("value")
    if title is not None:
        axes.set_title(title)
    axes.grid(True)
    axes.legend()
    _save_show_close(figure, output_path, show)


def _save_show_close(figure, output_path: str | Path | None, show: bool) -> None:
    """保存、显示并关闭 Matplotlib 图形。"""

    import matplotlib.pyplot as plt

    if output_path is not None:
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        figure.savefig(target, dpi=150, bbox_inches="tight")
    _show_if_interactive(show)
    plt.close(figure)


def _show_if_interactive(show: bool) -> None:
    """仅在交互式图形后端下显示窗口。

    无显示环境（例如服务器、CI 或 `MPLBACKEND=Agg`）下调用 `plt.show()` 只会
    产生警告而不会真正显示窗口，这里直接跳过，保证算例在任何环境都能安静运行。
    """

    if not show:
        return
    import matplotlib

    backend = (matplotlib.get_backend() or "").lower()
    non_interactive = {"agg", "pdf", "ps", "svg", "cairo", "template"}
    if backend not in non_interactive:
        import matplotlib.pyplot as plt

        plt.show()


def _result_label(result: PlottableResult) -> str:
    """返回结果电路名用于图例。"""

    circuit_name = getattr(result, "circuit_name", None)
    if isinstance(circuit_name, str):
        return circuit_name
    return "result"
