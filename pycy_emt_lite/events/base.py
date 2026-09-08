"""
文件名称：base.py
文件作用：定义仿真事件对象和事件队列。

主要内容：
1. 事件抽象基类
2. 按时间排序和触发的事件队列
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from math import isfinite, ulp
from typing import Iterable

from pycy_emt_lite.core.circuit import Circuit

EventRecord = dict[str, float | str]


def _time_tolerance(*values: float) -> float:
    """返回由参与比较的浮点时间量级决定的微小容差。"""

    scale = max((abs(value) for value in values), default=0.0)
    return 8.0 * ulp(scale)


def _time_close(left: float, right: float) -> bool:
    """判断两个时间是否只相差浮点舍入误差。"""

    if left == 0.0 or right == 0.0:
        return left == right
    return abs(left - right) <= _time_tolerance(left, right)


@dataclass(frozen=True, slots=True)
class SimulationEvent(ABC):
    """仿真事件基类。

    事件在固定时间步开始前触发，用于改变故障、断路器等可切换元件的状态。
    第一版事件时间会贴合固定步长：若事件时间不正好落在时间点上，则在第一个
    不早于事件时间的时间点执行。
    """

    time: float
    target: str
    name: str = ""

    def __post_init__(self) -> None:
        if not isfinite(self.time):
            raise ValueError("事件时间必须为有限数。")
        if self.time < 0:
            raise ValueError("事件时间不能小于 0。")

    def validate(self, circuit: Circuit) -> None:
        """在求解前检查事件；自定义事件默认无需标准状态约束。"""

    @abstractmethod
    def apply(self, circuit: Circuit, applied_time: float) -> EventRecord:
        """把事件作用到电路，并返回事件日志。"""


class EventQueue:
    """按时间管理仿真事件的队列。"""

    def __init__(self, events: Iterable[SimulationEvent] = ()) -> None:
        self._events = sorted(list(events), key=lambda event: event.time)
        self._next_index = 0

    @property
    def times(self) -> list[float]:
        """返回队列中所有事件的设定时间。"""

        return [event.time for event in self._events]

    def pop_due(self, time: float, *, tolerance: float | None = None) -> list[SimulationEvent]:
        """弹出所有应该在当前时间点执行的事件。"""

        due: list[SimulationEvent] = []
        while self._next_index < len(self._events):
            event_time = self._events[self._next_index].time
            if event_time > time:
                if time == 0.0:
                    break
                pair_tolerance = _time_tolerance(event_time, time)
                effective_tolerance = pair_tolerance if tolerance is None else min(tolerance, pair_tolerance)
                if event_time - time > effective_tolerance:
                    break
            due.append(self._events[self._next_index])
            self._next_index += 1
        return due

    def skip_until(self, time: float, *, tolerance: float) -> None:
        """跳过所有设定时间不晚于 `time` 的事件。

        当 `SimulationConfig.start_time` 大于 0 时，起始时刻之前的事件已经反映在
        元件状态中，事件队列只应继续处理后续事件，避免把历史事件重复作用到电路。
        """

        while self._next_index < len(self._events) and self._events[self._next_index].time <= time + tolerance:
            self._next_index += 1

    @property
    def remaining_count(self) -> int:
        """返回尚未触发的事件数量。"""

        return len(self._events) - self._next_index
