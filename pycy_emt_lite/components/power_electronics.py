"""
文件名称：power_electronics.py
文件作用：实现由布尔值或时间函数控制的理想开关。

采用显式导通/关断电导模型，不包含半导体器件的非线性求解。
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from numbers import Real
from typing import Callable, Iterable

import numpy as np

from pycy_emt_lite.components.base import Component
from pycy_emt_lite.core.context import StampContext
from pycy_emt_lite.core.stamping import add_conductance, add_voltage_probe

BoolTimeValue = bool | float | Callable[[float], bool | float]

def _bool_at(value: BoolTimeValue, time: float, *, name: str) -> bool:
    """先验证布尔值或数值 0/1，再转换为开关状态。"""

    value = value(time) if callable(value) else value
    if isinstance(value, (bool, np.bool_)) or (isinstance(value, Real) and value in (0, 1)):
        return bool(value)
    raise ValueError(
        f"开关 {name!r} 在仿真时间 {time:g} 的 closed={value!r} 非法；"
        "请使用布尔值或有限数值 0/1，门极时间函数也必须返回这样的标量。"
    )

@dataclass(slots=True)
class IdealSwitch(Component):
    """理想开关的电导近似模型。

    闭合时写入 `closed_resistance` 对应的大电导，断开时写入 `open_conductance`
    对应的小泄漏电导。第一版使用显式控制状态，不引入非线性迭代。
    """

    name: str
    positive: str
    negative: str
    closed: BoolTimeValue = False
    closed_resistance: float = 1e-3
    open_conductance: float = 1e-9
    last_current: float = 0.0
    last_state: bool = False

    def __post_init__(self) -> None:
        if not callable(self.closed):
            _bool_at(self.closed, 0.0, name=self.name)
        if not math.isfinite(self.closed_resistance) or self.closed_resistance <= 0.0:
            raise ValueError(f"开关 {self.name} 的闭合电阻必须为有限正数。")
        if not math.isfinite(self.open_conductance) or self.open_conductance < 0.0:
            raise ValueError(f"开关 {self.name} 的断开电导必须为有限非负数。")

    def nodes(self) -> Iterable[str]:
        return (self.positive, self.negative)

    def stamp(self, context: StampContext, matrix: np.ndarray, rhs: np.ndarray) -> None:
        """按当前控制状态写入开关电导。"""

        self.last_state = _bool_at(self.closed, context.time, name=self.name)
        conductance = 1.0 / self.closed_resistance if self.last_state else self.open_conductance
        if conductance > 0.0:
            add_conductance(matrix, context.node_index(self.positive), context.node_index(self.negative), conductance)

    def update_state(self, context: StampContext, solution: np.ndarray) -> None:
        """记录开关支路电流。"""

        voltage = add_voltage_probe(solution, context.node_index(self.positive), context.node_index(self.negative))
        conductance = 1.0 / self.closed_resistance if self.last_state else self.open_conductance
        self.last_current = conductance * voltage

    def outputs(self, context: StampContext, solution: np.ndarray) -> dict[str, float]:
        """记录开关电流和导通状态。"""

        return {f"i:{self.name}": self.last_current, f"state:{self.name}": 1.0 if self.last_state else 0.0}
