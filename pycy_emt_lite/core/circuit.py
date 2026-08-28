"""
文件名称：circuit.py
文件作用：定义电路容器，负责收集元件并准备 MNA 变量。
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field

from pycy_emt_lite.components.base import Component
from pycy_emt_lite.core.nodes import NodeManager
from pycy_emt_lite.core.variables import VariableManager


@dataclass(slots=True)
class Circuit:
    """电路模型容器。

    `Circuit` 本身不直接求解电路，而是负责保存“有哪些元件、这些元件连接到
    哪些节点”。仿真器运行前会调用 `prepare()`，把用户可读的节点名和元件
    支路转换成 MNA 方程所需的整数编号。

    标准建模流程：

    1. 创建 `Circuit("case_name")`。
    2. 调用 `add()` 逐个加入电阻、电感、电容、电源等元件。
    3. 将 `Circuit` 交给 `Simulator`。
    4. `Simulator` 调用 `prepare()` 完成节点编号和支路变量注册。
    """

    name: str = "circuit"
    components: list[Component] = field(default_factory=list)
    node_manager: NodeManager = field(default_factory=NodeManager)
    variable_manager: VariableManager = field(default_factory=VariableManager)
    prepared: bool = False

    @classmethod
    def from_components(cls, name: str, components: Iterable[Component]) -> "Circuit":
        """根据用户预先给定的元件对象列表创建电路。

        该方法适合教学和算例脚本使用：用户先把每个元件定义为一个对象，例如
        `Resistor("R1", "n1", "0", 5.0)`，对象中已经包含元件名称、连接节点和
        参数值。随后仿真程序读取这些对象，逐个加入 `Circuit`，形成完整电路。

        示例：

        ```python
        components = [
            VoltageSource("V1", "n1", "0", 10.0),
            Resistor("R1", "n1", "0", 5.0),
        ]
        circuit = Circuit.from_components("r_circuit", components)
        ```
        """

        circuit = cls(name)
        for component in components:
            circuit.add(component)
        return circuit

    def add(self, component: Component) -> None:
        """向电路添加一个元件。

        元件加入时只保存对象本身，不立即组装矩阵。这样做的原因是 MNA 矩阵维度
        依赖所有元件共同决定：普通节点需要节点电压变量，电压源和电感还会额外
        引入支路电流变量。只有收集完全部元件后，才能可靠确定方程规模。
        """

        if self.prepared:
            raise RuntimeError("电路已完成变量准备，不能继续添加元件。")
        self.components.append(component)

    def prepare(self) -> None:
        """建立节点编号和支路变量编号。

        该方法是从“用户电路描述”到“MNA 线性方程”的准备阶段：

        1. 遍历所有元件的 `nodes()`，把非参考节点编号为节点电压未知量。
        2. 再遍历所有元件的 `register()`，让电压源、电感等元件注册支路电流未知量。
        3. 准备完成后，矩阵未知量顺序固定为：
           `[节点电压变量, 支路电流变量]`。
        """

        self._prepare()

    def _prepare(self) -> None:
        """建立 MNA 编号：先编号节点电压变量，再注册支路电流变量。"""

        self._check_component_names()
        self.node_manager = NodeManager()
        self.variable_manager = VariableManager()
        for component in self.components:
            self.node_manager.add_many(component.nodes())
        for component in self.components:
            component.register(self.node_manager, self.variable_manager)
        self.prepared = True

    def _check_component_names(self) -> None:
        """检查元件名称是否唯一，避免结果字段互相覆盖。"""

        names: set[str] = set()
        duplicates: set[str] = set()
        for component in self.components:
            if component.name in names:
                duplicates.add(component.name)
            names.add(component.name)
        if duplicates:
            duplicate_list = ", ".join(sorted(repr(name) for name in duplicates))
            raise ValueError(f"电路中存在重复元件名称：{duplicate_list}。")

    @property
    def size(self) -> int:
        """返回 MNA 线性方程组维度。

        方程维度等于非参考节点电压变量数量加支路电流变量数量。这个值会用于创建
        `A x = z` 中的增广节点导纳矩阵 `A` 和右端项 `z`。
        """

        if not self.prepared:
            raise RuntimeError("请先调用 prepare()。")
        return self.node_manager.count + self.variable_manager.branch_count
