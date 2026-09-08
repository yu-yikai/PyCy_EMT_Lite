"""
文件名称：power_electronics.py
文件作用：实现阶段 3 所需的电力电子开关简化元件。

主要内容：
1. 理想开关的显式导通/关断电导模型
2. 二极管的一步滞后导通判据
3. IGBT 的门极控制简化模型和反并联二极管近似
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Callable, Iterable

import numpy as np

from pycy_emt_lite.components.base import Component
from pycy_emt_lite.core.context import StampContext
from pycy_emt_lite.core.stamping import add_conductance, add_voltage_probe

BoolTimeValue = bool | Callable[[float], bool]

def _bool_at(value: BoolTimeValue, time: float) -> bool:
    """返回布尔值或时间函数在当前时刻的开关状态。"""

    if callable(value):
        return bool(value(time))
    return bool(value)

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
        if not math.isfinite(self.closed_resistance) or self.closed_resistance <= 0.0:
            raise ValueError(f"开关 {self.name} 的闭合电阻必须为有限正数。")
        if not math.isfinite(self.open_conductance) or self.open_conductance < 0.0:
            raise ValueError(f"开关 {self.name} 的断开电导必须为有限非负数。")

    def nodes(self) -> Iterable[str]:
        return (self.positive, self.negative)

    def stamp(self, context: StampContext, matrix: np.ndarray, rhs: np.ndarray) -> None:
        """按当前控制状态写入开关电导。"""

        self.last_state = _bool_at(self.closed, context.time)
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

@dataclass(slots=True)
class Diode(Component):
    """二极管简化模型。

    二极管使用上一时间步端电压作为导通判据：当 `v_p - v_n > forward_voltage`
    时（严格大于，与 `stamp()` 实现一致），本时间步按 `on_resistance` 导通，
    否则按 `off_conductance` 关断。该模型适合教学和开关逻辑验证，不包含非线性
    伏安迭代。
    """

    name: str
    anode: str
    cathode: str
    forward_voltage: float = 0.0
    on_resistance: float = 1e-3
    off_conductance: float = 1e-9
    previous_voltage: float = 0.0
    last_current: float = 0.0
    last_state: bool = False

    def __post_init__(self) -> None:
        if self.on_resistance <= 0.0:
            raise ValueError(f"二极管 {self.name} 的导通电阻必须大于 0。")
        if self.off_conductance < 0.0:
            raise ValueError(f"二极管 {self.name} 的关断电导不能小于 0。")

    def nodes(self) -> Iterable[str]:
        return (self.anode, self.cathode)

    def stamp(self, context: StampContext, matrix: np.ndarray, rhs: np.ndarray) -> None:
        """根据上一时间步电压写入导通或关断电导。"""

        self.last_state = self.previous_voltage > self.forward_voltage
        conductance = 1.0 / self.on_resistance if self.last_state else self.off_conductance
        if conductance > 0.0:
            add_conductance(matrix, context.node_index(self.anode), context.node_index(self.cathode), conductance)

    def update_state(self, context: StampContext, solution: np.ndarray) -> None:
        """更新二极管端电压和支路电流记录。"""

        voltage = add_voltage_probe(solution, context.node_index(self.anode), context.node_index(self.cathode))
        conductance = 1.0 / self.on_resistance if self.last_state else self.off_conductance
        self.previous_voltage = voltage
        self.last_current = conductance * voltage

    def outputs(self, context: StampContext, solution: np.ndarray) -> dict[str, float]:
        """记录二极管电流和导通状态。"""

        return {f"i:{self.name}": self.last_current, f"state:{self.name}": 1.0 if self.last_state else 0.0}

@dataclass(slots=True)
class IGBTSwitch(Component):
    """IGBT 简化开关模型。

    IGBT 主通道由门极控制；如果 `anti_parallel_diode=True`，反向电压超过二极管
    判据时也会导通，近似表示反并联二极管。第一版同样采用显式电导模型。
    """

    name: str
    collector: str
    emitter: str
    gate: BoolTimeValue = False
    on_resistance: float = 1e-3
    off_conductance: float = 1e-9
    anti_parallel_diode: bool = True
    diode_forward_voltage: float = 0.0
    previous_voltage: float = 0.0
    last_current: float = 0.0
    last_state: bool = False

    def __post_init__(self) -> None:
        if self.on_resistance <= 0.0:
            raise ValueError(f"IGBT {self.name} 的导通电阻必须大于 0。")
        if self.off_conductance < 0.0:
            raise ValueError(f"IGBT {self.name} 的关断电导不能小于 0。")

    def nodes(self) -> Iterable[str]:
        return (self.collector, self.emitter)

    def stamp(self, context: StampContext, matrix: np.ndarray, rhs: np.ndarray) -> None:
        """写入 IGBT 主通道或反并联二极管电导。"""

        gate_on = _bool_at(self.gate, context.time)
        diode_on = self.anti_parallel_diode and self.previous_voltage < -self.diode_forward_voltage
        self.last_state = gate_on or diode_on
        conductance = 1.0 / self.on_resistance if self.last_state else self.off_conductance
        if conductance > 0.0:
            add_conductance(matrix, context.node_index(self.collector), context.node_index(self.emitter), conductance)

    def update_state(self, context: StampContext, solution: np.ndarray) -> None:
        """更新 IGBT 端电压和电流。"""

        voltage = add_voltage_probe(solution, context.node_index(self.collector), context.node_index(self.emitter))
        conductance = 1.0 / self.on_resistance if self.last_state else self.off_conductance
        self.previous_voltage = voltage
        self.last_current = conductance * voltage

    def outputs(self, context: StampContext, solution: np.ndarray) -> dict[str, float]:
        """记录 IGBT 电流和导通状态。"""

        return {f"i:{self.name}": self.last_current, f"state:{self.name}": 1.0 if self.last_state else 0.0}
