"""
文件名称：base.py
文件作用：定义电气元件的基础接口。

主要内容：
1. 定义元件节点声明接口
2. 定义 MNA 分支变量注册接口
3. 定义 stamp、状态更新与输出接口
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterable

import numpy as np

from pycy_emt_lite.core.context import StampContext
from pycy_emt_lite.core.nodes import NodeManager
from pycy_emt_lite.core.variables import VariableManager


class Component(ABC):
    """所有电气元件的抽象基类。

    元件通过 `stamp` 方法把自身数学模型写入 MNA 矩阵。动态元件还需要在
    每个时间步求解后调用 `update_state`，把本步电压、电流保存为下一步的历史项。

    一个元件在仿真中的生命周期为：

    1. `nodes()` 声明它连接到哪些节点。
    2. `register()` 按需注册支路电流变量。
    3. `stamp()` 在每个时间步写入 MNA 矩阵和右端项。
    4. `update_state()` 在求解后更新历史状态。
    5. `outputs()` 把需要记录的量返回给结果对象。
    """

    name: str
    _circuit_owner: object | None = None

    @abstractmethod
    def nodes(self) -> Iterable[str]:
        """返回元件连接的节点名称。

        `Circuit.prepare()` 会收集所有元件的节点名，并为非参考节点分配节点电压
        未知量。参考节点通常写作 `"0"`、`"gnd"` 或 `"ground"`。
        """

    def register(self, node_manager: NodeManager, variable_manager: VariableManager) -> None:
        """注册元件所需变量。

        电阻、电容、电流源等只需要节点电压变量，不需要额外注册。电压源和电感
        需要支路电流作为未知量，因此会在派生类中重写该方法。
        """

    @abstractmethod
    def stamp(self, context: StampContext, matrix: np.ndarray, rhs: np.ndarray) -> None:
        """把元件等效模型写入 MNA 矩阵和右端向量。

        `matrix` 对应方程 `A x = z` 中的 `A`，`rhs` 对应右端项 `z`。每个元件
        只修改与自身节点和支路变量相关的行列，这种局部写入过程称为 stamp。
        """

    def update_state(self, context: StampContext, solution: np.ndarray) -> None:
        """根据当前求解结果更新元件内部状态。

        静态元件通常不需要更新。电容、电感等动态元件会在这里保存当前电压或电流，
        供下一时间步计算历史源。
        """

    def outputs(self, context: StampContext, solution: np.ndarray) -> dict[str, float]:
        """返回需要记录的元件输出量。

        返回字典会合并到 `SimulationResult` 的当前行中。例如 `{"i:R1": 2.0}`
        表示当前时刻电阻 R1 电流为 2 A。
        """

        return {}
