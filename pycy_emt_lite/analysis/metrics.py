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
    """数值分析只依赖时间/信号读取，不要求旧行式结果。

    若实现没有 `event_log`，调用者负责只选择不跨事件的平滑时间窗。
    """

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


def _time_and_values(result: SeriesProvider, values: Sequence[float]) -> tuple[np.ndarray, np.ndarray]:
    """读取并验证时间列与等长信号。"""

    time = np.asarray(result.series("time"), dtype=float)
    values_array = np.asarray(values, dtype=float)
    if time.ndim != 1 or values_array.ndim != 1 or time.size != values_array.size:
        raise ValueError("时间列与结果列必须是一维等长序列。")
    if time.size == 0:
        raise ValueError("结果中没有数据。")
    if not np.all(np.isfinite(time)):
        raise ValueError("时间列必须只包含有限数。")
    if not np.all(np.isfinite(values_array)):
        raise ValueError("结果列必须只包含有限数。")
    if np.any(np.diff(time) <= 0.0):
        raise ValueError("时间列必须严格递增。")
    return time, values_array


def _window(result: SeriesProvider, column: str, start_time: float | None, end_time: float | None) -> np.ndarray:
    """按原采样点选择窗口，供峰值指标保留单点语义。"""

    time, values = _time_and_values(result, result.series(column))
    mask = np.ones_like(time, dtype=bool)
    if start_time is not None:
        mask &= time >= start_time
    if end_time is not None:
        mask &= time <= end_time
    selected = values[mask]
    if selected.size == 0:
        raise ValueError("指定时间窗口内没有结果数据。")
    return selected


def _crosses_event(result: SeriesProvider, time: np.ndarray, start_time: float, end_time: float) -> bool:
    """判断积分用到的原始采样区间是否跨过已记录事件。"""

    event_log = getattr(result, "event_log", None)
    if event_log is None:
        return False
    for record in event_log:
        if "time" not in record:
            continue
        event_time = float(record["time"])
        for left, right in zip(time[:-1], time[1:], strict=True):
            overlap = max(float(left), start_time) < min(float(right), end_time)
            if overlap and left < event_time <= right:
                return True
    return False


def _continuous_window(
    result: SeriesProvider,
    values: Sequence[float],
    start_time: float | None,
    end_time: float | None,
) -> tuple[np.ndarray, np.ndarray]:
    """按分段线性重建截取一个连续、无事件跨越的正时长窗口。"""

    time, values_array = _time_and_values(result, values)
    if time.size < 2:
        raise ValueError("连续时间指标至少需要两个采样点。")
    start = float(time[0] if start_time is None else start_time)
    end = float(time[-1] if end_time is None else end_time)
    if not np.isfinite(start) or not np.isfinite(end):
        raise ValueError("时间窗口边界必须为有限数。")
    if start < time[0] or end > time[-1]:
        raise ValueError("时间窗口必须位于结果时间范围内。")
    if end <= start:
        raise ValueError("连续时间指标需要正时长窗口。")
    if _crosses_event(result, time, start, end):
        raise ValueError("时间窗口跨越事件边界；请使用不跨事件的连续窗口。")

    interior = (time > start) & (time < end)
    window_time = np.concatenate(([start], time[interior], [end]))
    window_values = np.concatenate(
        ([np.interp(start, time, values_array)], values_array[interior], [np.interp(end, time, values_array)])
    )
    return window_time, window_values


def _linear_mean(time: np.ndarray, values: np.ndarray) -> float:
    """精确积分分段线性信号并返回时间平均值。"""

    widths = np.diff(time)
    integral = np.sum(widths * (values[:-1] + values[1:]) / 2.0)
    return float(integral / (time[-1] - time[0]))


def _linear_product_mean(time: np.ndarray, left: np.ndarray, right: np.ndarray) -> float:
    """精确积分两条分段线性信号的乘积并返回时间平均值。"""

    widths = np.diff(time)
    a = left[:-1]
    b = left[1:]
    c = right[:-1]
    d = right[1:]
    integral = np.sum(widths * (2.0 * a * c + a * d + b * c + 2.0 * b * d) / 6.0)
    return float(integral / (time[-1] - time[0]))


def rms(result: SeriesProvider, column: str, *, start_time: float | None = None, end_time: float | None = None) -> float:
    """按分段线性重建计算指定连续窗口的均方根值。"""

    time, values = _continuous_window(result, result.series(column), start_time, end_time)
    widths = np.diff(time)
    square_integral = np.sum(
        widths * (values[:-1] ** 2 + values[:-1] * values[1:] + values[1:] ** 2) / 3.0
    )
    return float(np.sqrt(square_integral / (time[-1] - time[0])))


def peak_abs(result: SeriesProvider, column: str, *, start_time: float | None = None, end_time: float | None = None) -> float:
    """计算某一结果列在指定时间窗口内的绝对峰值。"""

    values = _window(result, column, start_time, end_time)
    return float(np.max(np.abs(values)))


def mean_value(result: SeriesProvider, column: str, *, start_time: float | None = None, end_time: float | None = None) -> float:
    """按分段线性重建计算指定连续窗口的时间平均值。"""

    time, values = _continuous_window(result, result.series(column), start_time, end_time)
    return _linear_mean(time, values)


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

    总有功直接逐相求和，因此包含零序功率。无功采用幅值不变 Clarke 变换的
    `q = 1.5(v_beta i_alpha - v_alpha i_beta)`，只表达 alpha-beta 分量。
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

    active_power = va * ia + vb * ib + vc * ic
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
    """返回指定连续窗口内的三相功率时间平均值。

    `reactive_power` 是 alpha-beta 无功；由平均 P/Q 得到的视在功率和功率因数
    适用于平衡正弦场景，不作为不平衡或畸变波形的通用功率质量定义。
    """

    time, va = _continuous_window(result, result.series(voltage_columns[0]), start_time, end_time)
    _, vb = _continuous_window(result, result.series(voltage_columns[1]), start_time, end_time)
    _, vc = _continuous_window(result, result.series(voltage_columns[2]), start_time, end_time)
    _, ia = _continuous_window(result, result.series(current_columns[0]), start_time, end_time)
    _, ib = _continuous_window(result, result.series(current_columns[1]), start_time, end_time)
    _, ic = _continuous_window(result, result.series(current_columns[2]), start_time, end_time)

    p_avg = sum(
        _linear_product_mean(time, voltage, current)
        for voltage, current in ((va, ia), (vb, ib), (vc, ic))
    )
    v_alpha = (2.0 / 3.0) * (va - 0.5 * vb - 0.5 * vc)
    v_beta = (2.0 / 3.0) * ((np.sqrt(3.0) / 2.0) * (vb - vc))
    i_alpha = (2.0 / 3.0) * (ia - 0.5 * ib - 0.5 * ic)
    i_beta = (2.0 / 3.0) * ((np.sqrt(3.0) / 2.0) * (ib - ic))
    q_avg = 1.5 * (
        _linear_product_mean(time, v_beta, i_alpha)
        - _linear_product_mean(time, v_alpha, i_beta)
    )
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
