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
from pathlib import Path
from typing import Literal

from pycy_emt_lite.components.base import Component
from pycy_emt_lite.core.circuit import Circuit
from pycy_emt_lite.core.simulation import SimulationConfig, Simulator
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


def run_case(case: CaseDefinition) -> SimulationResult:
    """按统一流程运行算例。

    该入口把「元件列表 -> Circuit -> Simulator -> 结果保存 -> 事件日志 -> 绘图」
    整合为一步，供教学算例脚本使用。
    """

    circuit = Circuit.from_components(case.name, case.components)
    simulator = Simulator(circuit, case.config, events=case.events)
    result = simulator.run()

    print(
        f"仿真完成：{result.circuit_name}，共 {len(result.rows)} 个采样点，"
        f"步长 {result.time_step} s，仿真时长 {result.stop_time} s。"
    )

    output_dir = case.output.output_root / case.name
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

    for plot in case.plots:
        figure_path = output_dir / plot.figure_name if case.output.save_figure else None
        if case.output.save_figure and not plot.figure_name:
            raise ValueError("保存图像时每个 PlotSpec 都需要提供 figure_name。")
        if plot.kind == "series":
            plot_series(
                result,
                plot.columns,
                figure_path,
                show=case.output.show_figure,
                title=plot.title,
            )
            continue

        if len(plot.columns) != 3:
            raise ValueError(
                f"三相曲线 {plot.figure_name!r} 必须正好包含 3 个字段，"
                f"当前为 {len(plot.columns)} 个。"
            )
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
