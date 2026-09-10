"""
文件名称：context.py
文件作用：定义 stamp 阶段需要共享的上下文信息。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from pycy_emt_lite.core.nodes import NodeManager
from pycy_emt_lite.core.stamping import _InitialConditions

IntegrationMethod = Literal["trapezoidal", "backward_euler"]


@dataclass(frozen=True, slots=True)
class StampContext:
    """MNA stamp 上下文。

    该对象把节点编号、支路变量偏移、当前时间和积分方法统一传给元件，避免元件
    直接依赖仿真器内部实现。
    """

    node_manager: NodeManager
    branch_offset: int
    time: float
    time_step: float
    method: IntegrationMethod
    _initial: _InitialConditions | None = None

    def node_index(self, node: str) -> int | None:
        """返回节点在 MNA 矩阵中的行列号；参考节点返回 None。"""

        return self.node_manager.index(node)
