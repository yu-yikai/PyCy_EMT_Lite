"""
文件名称：results.py
文件作用：定义仿真结果对象以及 CSV、JSON、NPZ 保存和读入功能。
"""

from __future__ import annotations

import csv
import json
import math
from numbers import Real
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

_NPZ_RESERVED = {"__meta__", "__columns__", "file", "allow_pickle"}


def _checked_rows(rows, columns=None) -> tuple[list[str], list[dict[str, float]]]:
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        raise ValueError("rows 必须为结果行字典列表。")
    columns = list(dict.fromkeys(key for row in rows for key in row)) if columns is None else columns
    if (not isinstance(columns, list) or any(not isinstance(c, str) or not c for c in columns)
            or len(set(columns)) != len(columns)):
        raise ValueError("columns 必须为非空字符串组成的无重复列表。")
    normalized = []
    previous_time = -math.inf
    for index, row in enumerate(rows, 1):
        if row.keys() - set(columns):
            raise ValueError(f"结果行 {index} 含 columns 未声明的字段。")
        values = {}
        for column in columns:
            value = row.get(column)
            if value is None:
                value = math.nan
            elif isinstance(value, str) and value in {"Infinity", "+Infinity", "-Infinity", "NaN"}:
                value = float(value)
            if isinstance(value, bool) or not isinstance(value, Real):
                raise ValueError(f"结果行 {index} 字段 {column!r} 必须为实数或缺失值。")
            try:
                values[column] = float(value)
            except (ValueError, TypeError, OverflowError) as exc:
                raise ValueError(f"结果行 {index} 字段 {column!r} 超出支持的实数范围。") from exc
        time = values.get("time", math.nan)
        if not math.isfinite(time) or time < 0 or time <= previous_time:
            raise ValueError(f"结果行 {index} 的 time 必须为有限、非负且严格递增的时间。")
        previous_time = time
        normalized.append(values)
    return columns, normalized


def _checked_meta(meta, rows) -> dict:
    if not isinstance(meta, dict):
        raise ValueError("元数据必须为字典。")
    for field_name in ("circuit_name", "method"):
        if not isinstance(meta.get(field_name), str):
            raise ValueError(f"元数据 {field_name} 必须为字符串。")
    for field_name in ("time_step", "stop_time"):
        value = meta.get(field_name)
        try:
            valid = not isinstance(value, bool) and isinstance(value, Real) and math.isfinite(float(value)) and value >= 0
        except (ValueError, TypeError, OverflowError):
            valid = False
        if not valid:
            raise ValueError(f"元数据 {field_name} 必须为有限非负实数。")
    if rows and rows[-1]["time"] > meta["stop_time"] + 8 * math.ulp(meta["stop_time"]):
        raise ValueError("实际 time 超过元数据 stop_time。")
    events = meta.get("event_log", [])
    if not isinstance(events, list) or any(not isinstance(record, dict) for record in events):
        raise ValueError("event_log 必须为事件字典列表。")
    for index, record in enumerate(events, 1):
        if "time" not in record:
            raise ValueError(f"event_log 第 {index} 条缺少 time。")
        for key, value in record.items():
            if not isinstance(key, str) or not isinstance(value, (str, Real)) or isinstance(value, bool):
                raise ValueError(f"event_log 第 {index} 条字段 {key!r} 类型非法。")
            if isinstance(value, Real) and not math.isfinite(value):
                raise ValueError(f"event_log 第 {index} 条字段 {key!r} 必须有限。")
        for key in ("time", "scheduled_time"):
            if key in record and (not isinstance(record[key], Real) or record[key] < 0):
                raise ValueError(f"event_log 第 {index} 条字段 {key!r} 必须为非负时间。")
    return {"circuit_name": meta["circuit_name"], "method": meta["method"],
            "time_step": float(meta["time_step"]), "stop_time": float(meta["stop_time"]),
            "event_log": [{key: float(value) if isinstance(value, Real) else value for key, value in record.items()} for record in events]}


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

        return list(dict.fromkeys(key for row in self.rows for key in row))

    def series(self, column: str) -> np.ndarray:
        """读取某一列数据。"""

        if column not in self.columns:
            raise KeyError(f"结果中不存在字段 {column!r}。")
        return np.array([row.get(column, np.nan) for row in self.rows], dtype=float)

    def to_csv(self, path: str | Path) -> None:
        """保存 CSV；缺失信号写为空字段，读回为 NaN。"""

        columns, rows = _checked_rows(self.rows)
        _checked_meta(self._metadata(), rows)
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=columns)
            writer.writeheader()
            for row in rows:
                writer.writerow({key: "" if math.isnan(value) else value for key, value in row.items()})

    def to_json(self, path: str | Path) -> None:
        """保存标准 JSON；缺失/NaN 为 null，正负无穷为字符串 Infinity/-Infinity。

        无穷可表示模型中缺省的电阻支路；读回恢复对应浮点值，分析仍拒绝非有限信号。
        """

        columns, rows = _checked_rows(self.rows)
        meta = _checked_meta(self._metadata(), rows)
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        encoded_rows = [{key: None if math.isnan(value) else "Infinity" if value == math.inf else
                         "-Infinity" if value == -math.inf else value for key, value in row.items()} for row in rows]
        payload = meta | {"columns": columns, "rows": encoded_rows}
        target.write_text(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")

    def to_npz(self, path: str | Path) -> None:
        """保存 NPZ；无 .npz 后缀时 NumPy 自动追加 .npz。本方法不返回路径。"""

        columns, rows = _checked_rows(self.rows)
        collisions = set(columns) & _NPZ_RESERVED
        if collisions:
            raise ValueError(f"NPZ 字段使用保留名：{', '.join(sorted(collisions))}；请重命名业务字段。")
        meta = _checked_meta(self._metadata(), rows)
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        arrays = {column: self.series(column) for column in columns}
        arrays["__columns__"] = np.array(columns, dtype=str)
        arrays["__meta__"] = np.array(
            json.dumps(
                meta,
                ensure_ascii=False,
                allow_nan=False,
            )
        )
        np.savez(target, **arrays)

    def _metadata(self) -> dict:
        return {"circuit_name": self.circuit_name, "method": self.method, "time_step": self.time_step,
                "stop_time": self.stop_time, "event_log": self.event_log}

    @classmethod
    def from_json(cls, path: str | Path) -> "SimulationResult":
        """从 JSON 文件读入仿真结果。"""

        try:
            payload = json.loads(Path(path).read_text(encoding="utf-8"))
            _, rows = _checked_rows(payload["rows"], payload.get("columns"))
            return cls(**_checked_meta(payload, rows), rows=rows)
        except (ValueError, TypeError, KeyError, OverflowError) as exc:
            raise ValueError(f"JSON {path} 读入失败：{exc}") from exc

    @classmethod
    def from_csv(cls, path: str | Path, *, circuit_name: str = "csv_result", method: str = "unknown") -> "SimulationResult":
        """从 CSV 文件读入仿真结果。

        CSV 本身不保存完整元数据，因此需要调用者补充电路名和积分方法。
        """

        try:
            with Path(path).open("r", newline="", encoding="utf-8") as file:
                reader = csv.DictReader(file)
                columns = reader.fieldnames or []
                rows = []
                for row in reader:
                    parsed = {}
                    for key, value in row.items():
                        try:
                            if key is None or value is None or isinstance(value, list):
                                raise ValueError("字段数量与表头不一致")
                            parsed[key] = math.nan if value == "" else float(value)
                        except (ValueError, TypeError) as exc:
                            raise ValueError(f"行 {reader.line_num} 字段 {key!r}：{exc}") from exc
                    rows.append(parsed)
            _, rows = _checked_rows(rows, columns)
        except (ValueError, TypeError, OverflowError) as exc:
            raise ValueError(f"CSV {path} 读入失败：{exc}") from exc
        stop_time = rows[-1]["time"] if rows else 0.0
        time_step = rows[1]["time"] - rows[0]["time"] if len(rows) > 1 else 0.0
        meta = _checked_meta(dict(circuit_name=circuit_name, method=method, time_step=time_step, stop_time=stop_time), rows)
        return cls(**meta, rows=rows)

    @classmethod
    def from_npz(cls, path: str | Path) -> "SimulationResult":
        """从 NPZ 文件读入仿真结果。"""

        try:
            with np.load(Path(path), allow_pickle=False) as data:
                raw_columns = data["__columns__"]
                if raw_columns.ndim != 1 or raw_columns.dtype.kind not in "US":
                    raise ValueError("__columns__ 必须为一维字符串数组。")
                columns = [c.decode("utf-8") if isinstance(c, bytes) else str(c) for c in raw_columns]
                _checked_rows([], columns)
                if set(columns) & _NPZ_RESERVED:
                    raise ValueError("__columns__ 含 NPZ 保留名。")
                meta_array = data["__meta__"]
                if meta_array.ndim != 0 or meta_array.dtype.kind not in "US":
                    raise ValueError("__meta__ 必须为 JSON 字符串标量。")
                meta_text = meta_array.item()
                meta = json.loads(meta_text.decode("utf-8") if isinstance(meta_text, bytes) else meta_text)
                arrays = {column: data[column] for column in columns}
            length = arrays["time"].size if "time" in arrays else 0
            for column, array in arrays.items():
                if array.ndim != 1 or array.dtype.kind not in "fiu" or array.size != length:
                    raise ValueError(f"字段 {column!r} 必须为与 time 等长的一维实数数组。")
            rows = [{column: float(arrays[column][index]) for column in columns} for index in range(length)]
            _, rows = _checked_rows(rows, columns)
            return cls(**_checked_meta(meta, rows), rows=rows)
        except (ValueError, TypeError, KeyError, OverflowError) as exc:
            raise ValueError(f"NPZ {path} 读入失败：{exc}") from exc
