"""
文件名称：results.py
文件作用：定义仿真结果对象以及 CSV、JSON、NPZ 保存和读入功能。
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np


@dataclass(slots=True, repr=False)
class SimulationResult:
    """仿真结果容器。

    结果按“行”保存，每一行对应一个仿真时刻。字段名使用 `v:节点名`、
    `i:元件名`、`v:元件名` 等形式，便于区分电压和电流。
    """

    circuit_name: str
    method: str
    time_step: float
    stop_time: float
    rows: list[dict[str, float]]
    event_log: list[dict[str, float | str]] = field(default_factory=list)

    def __repr__(self) -> str:
        """返回结果的简洁摘要，方便 `print(result)` 直接查看。

        原始行数据可能很大，这里只展示电路名、仿真设置和规模信息；
        具体波形用 `series()` 读取，全部字段用 `columns` 查看。
        """

        return (
            f"SimulationResult(circuit_name={self.circuit_name!r}, "
            f"method={self.method!r}, time_step={self.time_step}, "
            f"stop_time={self.stop_time}, samples={len(self.rows)}, "
            f"columns={len(self.columns)}, events={len(self.event_log)})"
        )

    @property
    def columns(self) -> list[str]:
        """返回结果字段名，保持首次出现顺序。"""

        columns: list[str] = []
        for row in self.rows:
            for key in row:
                if key not in columns:
                    columns.append(key)
        return columns

    def series(self, column: str) -> np.ndarray:
        """读取某一列数据。"""

        if column not in self.columns:
            raise KeyError(f"结果中不存在字段 {column!r}。")
        return np.array([row.get(column, np.nan) for row in self.rows], dtype=float)

    def to_csv(self, path: str | Path) -> None:
        """保存为 CSV 文件。"""

        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        columns = self.columns
        with target.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=columns)
            writer.writeheader()
            for row in self.rows:
                writer.writerow(row)

    def to_json(self, path: str | Path) -> None:
        """保存结果元数据和行数据为 JSON。"""

        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "circuit_name": self.circuit_name,
            "method": self.method,
            "time_step": self.time_step,
            "stop_time": self.stop_time,
            "columns": self.columns,
            "rows": self.rows,
            "event_log": self.event_log,
        }
        target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def to_npz(self, path: str | Path) -> None:
        """保存为 NPZ 数组文件。"""

        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        columns = self.columns
        arrays = {column: self.series(column) for column in columns}
        arrays["__columns__"] = np.array(columns)
        arrays["__meta__"] = np.array(
            json.dumps(
                {
                    "circuit_name": self.circuit_name,
                    "method": self.method,
                    "time_step": self.time_step,
                    "stop_time": self.stop_time,
                    "event_log": self.event_log,
                },
                ensure_ascii=False,
            )
        )
        np.savez(target, **arrays)

    @classmethod
    def from_json(cls, path: str | Path) -> "SimulationResult":
        """从 JSON 文件读入仿真结果。"""

        payload: dict[str, Any] = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(
            circuit_name=str(payload["circuit_name"]),
            method=str(payload["method"]),
            time_step=float(payload["time_step"]),
            stop_time=float(payload["stop_time"]),
            rows=[{key: float(value) for key, value in row.items()} for row in payload["rows"]],
            event_log=[dict(record) for record in payload.get("event_log", [])],
        )

    @classmethod
    def from_csv(cls, path: str | Path, *, circuit_name: str = "csv_result", method: str = "unknown") -> "SimulationResult":
        """从 CSV 文件读入仿真结果。

        CSV 本身不保存完整元数据，因此需要调用者补充电路名和积分方法。
        """

        with Path(path).open("r", newline="", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            rows = [{key: float(value) for key, value in row.items()} for row in reader]
        stop_time = rows[-1]["time"] if rows else 0.0
        time_step = rows[1]["time"] - rows[0]["time"] if len(rows) > 1 else 0.0
        return cls(circuit_name=circuit_name, method=method, time_step=time_step, stop_time=stop_time, rows=rows)

    @classmethod
    def from_npz(cls, path: str | Path) -> "SimulationResult":
        """从 NPZ 文件读入仿真结果。"""

        data = np.load(Path(path), allow_pickle=False)
        columns = [str(column) for column in data["__columns__"]]
        meta = json.loads(str(data["__meta__"]))
        length = len(data[columns[0]]) if columns else 0
        rows = []
        for index in range(length):
            rows.append({column: float(data[column][index]) for column in columns})
        return cls(
            circuit_name=str(meta["circuit_name"]),
            method=str(meta["method"]),
            time_step=float(meta["time_step"]),
            stop_time=float(meta["stop_time"]),
            rows=rows,
            event_log=[dict(record) for record in meta.get("event_log", [])],
        )
