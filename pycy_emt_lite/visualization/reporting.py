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
import os
import re
from urllib.parse import quote
from typing import Protocol


class ReportableResult(Protocol):
    """报告所需的基本仿真元数据。"""

    method: str
    time_step: float
    stop_time: float


def _text(value: object) -> str:
    return re.sub(r"([\\`*_{}\[\]()#+.!|<>])", r"\\\1", str(value).replace("\n", " ").replace("\r", " "))


def _code(value: object) -> str:
    text = str(value).replace("\n", " ").replace("\r", " ")
    delimiter = "`" * (max((len(run) for run in re.findall(r"`+", text)), default=0) + 1)
    padding = " " if text.startswith("`") or text.endswith("`") else ""
    return f"{delimiter}{padding}{text}{padding}{delimiter}"


def write_markdown_report(
    result: ReportableResult,
    path: str | Path,
    *,
    title: str | None = None,
    summary: dict[str, float | str] | None = None,
    figure_paths: list[str | Path] | None = None,
) -> None:
    """生成仿真结果 Markdown 报告。

    `result` 通常为 `SimulationResult`，也可为提供所需元数据的结果对象。
    事件记录从 `event_log` 读取；缺少该属性时说明未提供事件日志。
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
        f"# {_text(title or case_id)}",
        "",
        "## 仿真信息",
        "",
        f"- 算例名称：{_code(case_id)}",
        f"- 方法：{_code(result.method)}",
        f"- 时间步长：`{result.time_step}` s",
        f"- 终止时间：`{result.stop_time}` s",
        f"- 采样点数：`{sample_count}`",
        "",
    ]
    if summary:
        lines.extend(["## 摘要指标", ""])
        for key, value in summary.items():
            lines.append(f"- {_text(key)}：{_text(value)}")
        lines.append("")
    lines.extend(["## 结果字段", ""])
    for column in signal_names:
        lines.append(f"- {_code(column)}")
    lines.append("")
    if event_log:
        lines.extend(["## 事件日志", ""])
        for record in event_log:
            lines.append(
                f"- t={_text(record.get('time'))} s，类型 {_code(record.get('type'))}，目标 {_code(record.get('target'))}"
            )
        lines.append("")
    elif event_log is None:
        lines.extend(["## 事件日志", "", "- 结果对象未提供事件日志。", ""])
    if figure_paths:
        lines.extend(["## 图像", ""])
        for figure_path in figure_paths:
            figure = Path(figure_path)
            try:
                link = quote(Path(os.path.relpath(figure.resolve(), target.parent.resolve())).as_posix(), safe="/:")
            except ValueError:  # Windows 不同驱动器没有相对路径。
                link = figure.resolve().as_uri()
            lines.append(f"![{_text(figure.stem)}]({link})")
        lines.append("")
    target.write_text("\n".join(lines), encoding="utf-8")
