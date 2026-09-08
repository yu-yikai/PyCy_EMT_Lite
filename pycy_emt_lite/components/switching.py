"""
文件名称：switching.py
文件作用：实现阶段 2 所需的故障和断路器简化元件。

主要内容：
1. 可投入和清除的接地故障支路
2. 可开合的断路器电阻支路
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable

import numpy as np

from pycy_emt_lite.components.base import Component
from pycy_emt_lite.core.context import StampContext
from pycy_emt_lite.core.stamping import add_conductance, add_voltage_probe

@dataclass(slots=True)
class Fault(Component):
    """接地故障支路。

    故障支路连接在 `node` 和 `ground` 之间。`enabled=False` 时不写入矩阵，
    表示故障尚未投入；事件系统可在指定时间把它投入或清除。
    """

    name: str
    node: str
    resistance: float
    ground: str = "0"
    enabled: bool = False
    last_current: float = 0.0

    def __post_init__(self) -> None:
        if not math.isfinite(self.resistance) or self.resistance <= 0:
            raise ValueError(f"故障 {self.name} 的故障电阻必须为有限正数。")

    def nodes(self) -> Iterable[str]:
        return (self.node, self.ground)

    def stamp(self, context: StampContext, matrix: np.ndarray, rhs: np.ndarray) -> None:
        """故障投入时写入等效故障电导。"""

        if not self.enabled:
            return
        add_conductance(matrix, context.node_index(self.node), context.node_index(self.ground), 1.0 / self.resistance)

    def update_state(self, context: StampContext, solution: np.ndarray) -> None:
        """记录当前故障电流。"""

        if not self.enabled:
            self.last_current = 0.0
            return
        voltage = add_voltage_probe(solution, context.node_index(self.node), context.node_index(self.ground))
        self.last_current = voltage / self.resistance

    def outputs(self, context: StampContext, solution: np.ndarray) -> dict[str, float]:
        """记录故障电流和投入状态。"""

        return {f"i:{self.name}": self.last_current, f"state:{self.name}": 1.0 if self.enabled else 0.0}

@dataclass(slots=True)
class Breaker(Component):
    """断路器简化模型。

    断路器闭合时按小电阻写入电导，断开时默认完全不写入矩阵。若断开后导致
    下游网络孤立，仿真器会按普通拓扑错误给出奇异矩阵诊断。
    """

    name: str
    positive: str
    negative: str
    closed: bool = True
    closed_resistance: float = 1e-3
    last_current: float = 0.0

    def __post_init__(self) -> None:
        if not math.isfinite(self.closed_resistance) or self.closed_resistance <= 0:
            raise ValueError(f"断路器 {self.name} 的闭合电阻必须为有限正数。")

    def nodes(self) -> Iterable[str]:
        return (self.positive, self.negative)

    def stamp(self, context: StampContext, matrix: np.ndarray, rhs: np.ndarray) -> None:
        """断路器闭合时写入闭合电导。"""

        if self.closed:
            add_conductance(
                matrix,
                context.node_index(self.positive),
                context.node_index(self.negative),
                1.0 / self.closed_resistance,
            )

    def update_state(self, context: StampContext, solution: np.ndarray) -> None:
        """记录断路器电流。"""

        if not self.closed:
            self.last_current = 0.0
            return
        voltage = add_voltage_probe(solution, context.node_index(self.positive), context.node_index(self.negative))
        self.last_current = voltage / self.closed_resistance

    def outputs(self, context: StampContext, solution: np.ndarray) -> dict[str, float]:
        """记录断路器电流和开合状态。"""

        return {f"i:{self.name}": self.last_current, f"state:{self.name}": 1.0 if self.closed else 0.0}
