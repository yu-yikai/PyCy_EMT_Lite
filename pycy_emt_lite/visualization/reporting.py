"""
文件名称：reporting.py
文件作用：生成仿真结果 Markdown 报告。

主要内容：
1. 输出算例基本信息
2. 输出结果字段和事件日志
3. 输出用户指定的摘要指标
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol


class ReportableResult(Protocol):
    """报告只依赖结果元数据与信号读取，稳定列式与旧行式结果都满足。"""

    method: str
    time_step: float
    stop_time: float


def write_markdown_report(
    result: ReportableResult,
    path: str | Path,
    *,
    title: str | None = None,
    summary: dict[str, float | str] | None = None,
    figure_paths: list[str | Path] | None = None,
) -> None:
    """生成仿真结果 Markdown 报告。

    `result` 可以是稳定列式 `RuntimeResult` 或旧行式 `SimulationResult`。事件日志只在
    旧行式结果存在时输出；稳定结果不携带事件日志，会输出明确的说明。
    """

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)

    case_id = getattr(result, "case_id", None) or getattr(result, "circuit_name", "unknown")
    sample_count = getattr(result, "sample_count", None)
    if sample_count is None:
        sample_count = len(getattr(result, "rows", ()))
    signals = getattr(result, "signals", None)
    if signals is not None:
        signal_names = list(signals)
    else:
        signal_names = list(getattr(result, "columns", ()))
    event_log = getattr(result, "event_log", None)

    lines = [
        f"# {title or case_id}",
        "",
        "## 仿真信息",
        "",
        f"- 算例名称：`{case_id}`",
        f"- 方法：`{result.method}`",
        f"- 时间步长：`{result.time_step}` s",
        f"- 终止时间：`{result.stop_time}` s",
        f"- 采样点数：`{sample_count}`",
        "",
    ]
    if summary:
        lines.extend(["## 摘要指标", ""])
        for key, value in summary.items():
            lines.append(f"- {key}：{value}")
        lines.append("")
    lines.extend(["## 结果字段", ""])
    for column in signal_names:
        lines.append(f"- `{column}`")
    lines.append("")
    if event_log:
        lines.extend(["## 事件日志", ""])
        for record in event_log:
            lines.append(
                f"- t={record.get('time')} s，类型 `{record.get('type')}`，目标 `{record.get('target')}`"
            )
        lines.append("")
    elif event_log is None:
        lines.extend(["## 事件日志", "", "- 稳定列式结果不保存事件日志，请通过 `SimulationSession.event_log` 读取。", ""])
    if figure_paths:
        lines.extend(["## 图像", ""])
        for figure_path in figure_paths:
            figure = Path(figure_path)
            lines.append(f"![{figure.stem}]({figure.as_posix()})")
        lines.append("")
    target.write_text("\n".join(lines), encoding="utf-8")
