"""
文件名称：standard.py
文件作用：实现常用故障和断路器事件。

主要内容：
1. 故障投入事件
2. 故障清除事件
3. 断路器断开和闭合事件
"""

from __future__ import annotations

from dataclasses import dataclass

from pycy_emt_lite.core.circuit import Circuit
from pycy_emt_lite.events.base import EventRecord, SimulationEvent


def _find_component(circuit: Circuit, target: str) -> object:
    """按名称查找事件作用对象。"""

    for component in circuit.components:
        if getattr(component, "name", None) == target:
            return component
    raise KeyError(f"事件目标 {target!r} 不存在。")


def _set_bool_state(circuit: Circuit, target: str, attribute: str, value: bool) -> bool:
    """设置目标元件布尔状态，并返回事件前状态。"""

    component = _find_component(circuit, target)
    if not hasattr(component, attribute):
        raise TypeError(f"事件目标 {target!r} 不支持状态 {attribute!r}。")
    before = bool(getattr(component, attribute))
    setattr(component, attribute, value)
    return before


@dataclass(frozen=True, slots=True)
class FaultApplyEvent(SimulationEvent):
    """故障投入事件。"""

    def apply(self, circuit: Circuit, applied_time: float) -> EventRecord:
        before = _set_bool_state(circuit, self.target, "enabled", True)
        return {
            "time": applied_time,
            "scheduled_time": self.time,
            "type": "fault_apply",
            "target": self.target,
            "before": float(before),
            "after": 1.0,
            "name": self.name,
        }


@dataclass(frozen=True, slots=True)
class FaultClearEvent(SimulationEvent):
    """故障清除事件。"""

    def apply(self, circuit: Circuit, applied_time: float) -> EventRecord:
        before = _set_bool_state(circuit, self.target, "enabled", False)
        return {
            "time": applied_time,
            "scheduled_time": self.time,
            "type": "fault_clear",
            "target": self.target,
            "before": float(before),
            "after": 0.0,
            "name": self.name,
        }


@dataclass(frozen=True, slots=True)
class BreakerOpenEvent(SimulationEvent):
    """断路器断开事件。"""

    def apply(self, circuit: Circuit, applied_time: float) -> EventRecord:
        before = _set_bool_state(circuit, self.target, "closed", False)
        return {
            "time": applied_time,
            "scheduled_time": self.time,
            "type": "breaker_open",
            "target": self.target,
            "before": float(before),
            "after": 0.0,
            "name": self.name,
        }


@dataclass(frozen=True, slots=True)
class BreakerCloseEvent(SimulationEvent):
    """断路器闭合事件。"""

    def apply(self, circuit: Circuit, applied_time: float) -> EventRecord:
        before = _set_bool_state(circuit, self.target, "closed", True)
        return {
            "time": applied_time,
            "scheduled_time": self.time,
            "type": "breaker_close",
            "target": self.target,
            "before": float(before),
            "after": 1.0,
            "name": self.name,
        }
