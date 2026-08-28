"""
文件名称：metrics.py
文件作用：提供仿真结果的基础数值分析函数。

主要内容：
1. 单列 RMS、峰值和平均值
2. 三相 RMS 统计
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Protocol

import numpy as np


class SeriesProvider(Protocol):
    """数值分析只依赖时间/信号读取，不要求旧行式结果。"""

    def series(self, column: str) -> Sequence[float]: ...


@dataclass(frozen=True, slots=True)
class ThreePhasePowerSummary:
    """三相功率统计结果。"""

    active_power: float
    reactive_power: float
    apparent_power: float
    power_factor: float


@dataclass(frozen=True, slots=True)
class VoltageSagSummary:
    """电压跌落统计结果。"""

    sag_detected: bool
    worst_column: str
    min_rms: float
    min_pu: float


def _window(result: SeriesProvider, column: str, start_time: float | None, end_time: float | None) -> np.ndarray:
    """按时间窗口读取结果列。"""

    values = np.asarray(result.series(column), dtype=float)
    time = np.asarray(result.series("time"), dtype=float)
    mask = np.ones_like(time, dtype=bool)
    if start_time is not None:
        mask &= time >= start_time
    if end_time is not None:
        mask &= time <= end_time
    selected = values[mask]
    if selected.size == 0:
        raise ValueError("指定时间窗口内没有结果数据。")
    return selected


def rms(result: SeriesProvider, column: str, *, start_time: float | None = None, end_time: float | None = None) -> float:
    """计算某一结果列在指定时间窗口内的均方根值。"""

    values = _window(result, column, start_time, end_time)
    return float(np.sqrt(np.mean(values * values)))


def peak_abs(result: SeriesProvider, column: str, *, start_time: float | None = None, end_time: float | None = None) -> float:
    """计算某一结果列在指定时间窗口内的绝对峰值。"""

    values = _window(result, column, start_time, end_time)
    return float(np.max(np.abs(values)))


def mean_value(result: SeriesProvider, column: str, *, start_time: float | None = None, end_time: float | None = None) -> float:
    """计算某一结果列在指定时间窗口内的平均值。"""

    values = _window(result, column, start_time, end_time)
    return float(np.mean(values))


def three_phase_rms(
    result: SeriesProvider,
    columns: Iterable[str],
    *,
    start_time: float | None = None,
    end_time: float | None = None,
) -> dict[str, float]:
    """计算三相字段的 RMS 值。

    `columns` 通常传入 `["v:load:a", "v:load:b", "v:load:c"]`。
    """

    return {column: rms(result, column, start_time=start_time, end_time=end_time) for column in columns}


def instantaneous_three_phase_power(
    result: SeriesProvider,
    voltage_columns: tuple[str, str, str],
    current_columns: tuple[str, str, str],
) -> tuple[np.ndarray, np.ndarray]:
    """计算三相瞬时有功和无功功率序列。

    采用幅值不变 Clarke 变换，并使用：
    `p = 1.5(v_alpha i_alpha + v_beta i_beta)`，
    `q = 1.5(v_beta i_alpha - v_alpha i_beta)`。
    """

    va = np.asarray(result.series(voltage_columns[0]), dtype=float)
    vb = np.asarray(result.series(voltage_columns[1]), dtype=float)
    vc = np.asarray(result.series(voltage_columns[2]), dtype=float)
    ia = np.asarray(result.series(current_columns[0]), dtype=float)
    ib = np.asarray(result.series(current_columns[1]), dtype=float)
    ic = np.asarray(result.series(current_columns[2]), dtype=float)

    v_alpha = (2.0 / 3.0) * (va - 0.5 * vb - 0.5 * vc)
    v_beta = (2.0 / 3.0) * ((np.sqrt(3.0) / 2.0) * (vb - vc))
    i_alpha = (2.0 / 3.0) * (ia - 0.5 * ib - 0.5 * ic)
    i_beta = (2.0 / 3.0) * ((np.sqrt(3.0) / 2.0) * (ib - ic))

    active_power = 1.5 * (v_alpha * i_alpha + v_beta * i_beta)
    reactive_power = 1.5 * (v_beta * i_alpha - v_alpha * i_beta)
    return active_power, reactive_power


def three_phase_power(
    result: SeriesProvider,
    voltage_columns: tuple[str, str, str],
    current_columns: tuple[str, str, str],
    *,
    start_time: float | None = None,
    end_time: float | None = None,
) -> ThreePhasePowerSummary:
    """返回指定时间窗口内的平均三相有功、无功、视在功率和功率因数。"""

    active, reactive = instantaneous_three_phase_power(result, voltage_columns, current_columns)
    time = np.asarray(result.series("time"), dtype=float)
    mask = np.ones_like(time, dtype=bool)
    if start_time is not None:
        mask &= time >= start_time
    if end_time is not None:
        mask &= time <= end_time
    if not np.any(mask):
        raise ValueError("指定时间窗口内没有结果数据。")

    p_avg = float(np.mean(active[mask]))
    q_avg = float(np.mean(reactive[mask]))
    apparent = float(np.hypot(p_avg, q_avg))
    power_factor = 0.0 if apparent == 0.0 else p_avg / apparent
    return ThreePhasePowerSummary(p_avg, q_avg, apparent, power_factor)


def voltage_sag_summary(
    result: SeriesProvider,
    voltage_columns: Iterable[str],
    nominal_rms: float,
    *,
    threshold_pu: float = 0.9,
    start_time: float | None = None,
    end_time: float | None = None,
) -> VoltageSagSummary:
    """按窗口 RMS 判断电压跌落。

    该函数面向阶段 4 的教学算例：先统计每个电压字段在窗口内的 RMS，
    再找出最低标幺值并判断是否低于阈值。
    """

    if nominal_rms <= 0.0:
        raise ValueError("额定 RMS 电压必须大于 0。")
    if threshold_pu <= 0.0:
        raise ValueError("电压跌落阈值必须大于 0。")

    rms_values = {
        column: rms(result, column, start_time=start_time, end_time=end_time)
        for column in voltage_columns
    }
    if not rms_values:
        raise ValueError("至少需要提供一个电压字段。")
    worst_column = min(rms_values, key=rms_values.__getitem__)
    min_rms = rms_values[worst_column]
    min_pu = min_rms / nominal_rms
    return VoltageSagSummary(min_pu < threshold_pu, worst_column, min_rms, min_pu)
