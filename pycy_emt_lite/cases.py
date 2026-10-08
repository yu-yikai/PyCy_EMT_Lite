"""
文件名称：cases.py
文件作用：定义 PyCy_EMT_Lite 统一算例接口。

主要内容：
1. 定义算例绘图、输出和整体算例配置对象
2. 统一执行 Circuit、Simulator、结果保存、事件日志和绘图流程
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path, PureWindowsPath
from typing import Literal

from pycy_emt_lite.components.base import Component
from pycy_emt_lite.core.circuit import Circuit
from pycy_emt_lite.core.simulation import SimulationConfig, Simulator, StepCallback
from pycy_emt_lite.events import SimulationEvent
from pycy_emt_lite.io.results import SimulationResult
from pycy_emt_lite.visualization import plot_series, plot_three_phase

PlotKind = Literal["series", "three_phase"]


@dataclass(frozen=True, slots=True)
class PlotSpec:
    """算例绘图配置。

    `figure_name` 只在需要保存图像时使用，默认留空即可。
    """

    columns: tuple[str, ...]
    figure_name: str = ""
    kind: PlotKind = "series"
    title: str | None = None


@dataclass(frozen=True, slots=True)
class OutputOptions:
    """算例输出配置。"""

    save_data: bool = False
    save_figure: bool = False
    show_figure: bool = True
    output_root: Path = Path("outputs")


@dataclass(frozen=True, slots=True)
class CaseDefinition:
    """统一算例定义。"""

    name: str
    components: tuple[Component, ...]
    config: SimulationConfig
    events: tuple[SimulationEvent, ...] = ()
    plots: tuple[PlotSpec, ...] = ()
    output: OutputOptions = field(default_factory=OutputOptions)
    summary: Callable[[SimulationResult], None] | None = None
    on_step: StepCallback | None = None


def _check_directory(path: Path) -> None:
    for candidate in (path, *path.parents):
        if candidate.exists() and not candidate.is_dir():
            raise ValueError(f"输出目录 {path} 无法创建：{candidate} 已是文件；请更换输出路径。")


def _output_directory(case: CaseDefinition) -> Path:
    """在求解和写文件前检查可静态确认的绘图及路径配置。"""
    name = case.name
    if (not isinstance(name, str) or not name.strip() or name in {".", ".."}
            or "/" in name or "\\" in name or PureWindowsPath(name).drive):
        raise ValueError(f"案例名 {name!r} 必须为单个相对目录名；请去掉绝对路径和路径分隔符。")
    if not isinstance(case.output.output_root, (str, Path)):
        raise ValueError("output_root 必须为字符串或 Path；请设置结果根目录。")
    root = Path(case.output.output_root).resolve()
    output_dir = (root / name).resolve()
    if not output_dir.is_relative_to(root):
        raise ValueError("案例输出目录越过 output_root；请检查目录名和符号链接。")
    if case.output.save_data or case.output.save_figure:
        _check_directory(output_dir)
    for plot in case.plots:
        if not isinstance(plot.kind, str) or plot.kind not in {"series", "three_phase"}:
            raise ValueError(f"PlotSpec.kind={plot.kind!r} 非法；请选择 series 或 three_phase。")
        if (not isinstance(plot.columns, (tuple, list)) or not plot.columns
                or any(not isinstance(c, str) or not c.strip() for c in plot.columns)):
            raise ValueError("PlotSpec.columns 必须为非空字段名称序列。")
        if plot.kind == "three_phase" and len(plot.columns) != 3:
            raise ValueError("三相曲线必须正好包含 3 个字段。")
        if case.output.save_figure:
            figure = plot.figure_name
            if (not isinstance(figure, str) or not figure.strip() or Path(figure).is_absolute()
                    or PureWindowsPath(figure).drive or figure.startswith("\\")):
                raise ValueError("保存图像时 figure_name 必须为非空相对文件名。")
            target = (output_dir / figure).resolve()
            if not target.is_relative_to(output_dir) or target == output_dir:
                raise ValueError(f"图名 {figure!r} 越过案例输出目录；请使用目录内的相对路径。")
            _check_directory(target.parent)
            if target.is_dir():
                raise ValueError(f"图像输出路径 {target} 已是目录；请使用文件路径。")
            from matplotlib.backend_bases import FigureCanvasBase
            suffix = target.suffix.lower().lstrip(".")
            if suffix and suffix not in FigureCanvasBase.get_supported_filetypes():
                raise ValueError(f"图像格式 {suffix!r} 不受支持；请使用 png、svg 等支持的格式。")
    if case.summary is not None and not callable(case.summary):
        raise ValueError("summary 必须为可调用对象或 None。")
    return output_dir


def run_case(case: CaseDefinition) -> SimulationResult:
    """按统一流程运行算例。

    该入口把「元件列表 -> Circuit -> Simulator -> 结果保存 -> 事件日志 -> 绘图」
    整合为一步，供教学算例脚本使用。
    """

    output_dir = _output_directory(case)
    circuit = Circuit.from_components(case.name, case.components)
    simulator = Simulator(circuit, case.config, events=case.events, on_step=case.on_step)
    result = simulator.run()

    print(
        f"仿真完成：{result.circuit_name}，共 {len(result.rows)} 个采样点，"
        f"步长 {result.time_step} s，仿真时长 {result.stop_time} s。"
    )

    should_create_output_dir = case.output.save_data or case.output.save_figure
    if should_create_output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)

    if result.event_log:
        print("事件日志：")
        for record in result.event_log:
            event_time = float(record["time"])
            print(f"  t={event_time:.6f}s {record['type']} -> {record['target']}")

    if case.summary is not None:
        case.summary(result)

    if case.output.save_data:
        result.to_csv(output_dir / "result.csv")
        result.to_json(output_dir / "result.json")
        result.to_npz(output_dir / "result.npz")
        print(f"数据结果已保存到：{output_dir}")

    # kind、列数和图名已在 _output_directory 仿真前校验，此处按校验后的两类直接绘图。
    for plot in case.plots:
        figure_path = output_dir / plot.figure_name if case.output.save_figure else None
        if plot.kind == "series":
            plot_series(
                result,
                plot.columns,
                figure_path,
                show=case.output.show_figure,
                title=plot.title,
            )
        else:
            plot_three_phase(
                result,
                (plot.columns[0], plot.columns[1], plot.columns[2]),
                figure_path,
                show=case.output.show_figure,
                title=plot.title,
            )

    if case.output.save_figure:
        print(f"结果图像已保存到：{output_dir}")

    return result
