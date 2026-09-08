"""
文件名称：basic.py
文件作用：实现阶段 1 所需的基础电气元件模型。

主要内容：
1. 电阻、电流源、电压源的 MNA stamp
2. 电容的梯形积分和后退欧拉等效电导模型
3. 电感的支路电流变量和离散化电压方程
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Iterable

import numpy as np

from pycy_emt_lite.components.base import Component
from pycy_emt_lite.core.context import StampContext
from pycy_emt_lite.core.nodes import NodeManager
from pycy_emt_lite.core.stamping import add_conductance, add_current_source, add_voltage_probe
from pycy_emt_lite.core.variables import VariableManager

TimeValue = float | Callable[[float], float]

def _value_at(value: TimeValue, time: float, *, name: str | None = None) -> float:
    """返回常数或时间函数在当前时刻的数值。"""

    if callable(value):
        result = float(value(time))
    else:
        result = float(value)
    if not np.isfinite(result):
        source_name = f" {name!r}" if name is not None else ""
        raise ValueError(f"源{source_name} 在 time={time:g} 的值必须为有限数。")
    return result

@dataclass(slots=True)
class Resistor(Component):
    """线性电阻。

    电阻采用电导 `G = 1 / R` 直接写入 MNA 矩阵。
    """

    name: str
    positive: str
    negative: str
    resistance: float

    def __post_init__(self) -> None:
        if not np.isfinite(self.resistance):
            raise ValueError(f"电阻 {self.name} 的阻值必须为有限数。")
        if self.resistance <= 0:
            raise ValueError(f"电阻 {self.name} 的阻值必须大于 0。")

    def nodes(self) -> Iterable[str]:
        return (self.positive, self.negative)

    def stamp(self, context: StampContext, matrix: np.ndarray, rhs: np.ndarray) -> None:
        """写入电阻 stamp。

        对连接在 p、n 两节点之间的电阻，有 `i = G * (v_p - v_n)`。根据 KCL，
        该电导会分别加到 p、n 的自导纳位置，并在互导纳位置写入负值。
        """

        add_conductance(matrix, context.node_index(self.positive), context.node_index(self.negative), 1.0 / self.resistance)

    def outputs(self, context: StampContext, solution: np.ndarray) -> dict[str, float]:
        """根据两端电压计算电阻电流并记录。"""

        voltage = add_voltage_probe(solution, context.node_index(self.positive), context.node_index(self.negative))
        return {f"i:{self.name}": voltage / self.resistance}

@dataclass(slots=True)
class CurrentSource(Component):
    """理想电流源。

    `current` 定义为从 `positive` 节点流向 `negative` 节点的电流。按照 MNA
    右端向量注入约定，正向电流会从 positive 节点流出、注入 negative 节点。
    """

    name: str
    positive: str
    negative: str
    current: TimeValue

    def __post_init__(self) -> None:
        if not callable(self.current) and not np.isfinite(float(self.current)):
            raise ValueError(f"电流源 {self.name} 的常数电流必须为有限数。")

    def nodes(self) -> Iterable[str]:
        return (self.positive, self.negative)

    def stamp(self, context: StampContext, matrix: np.ndarray, rhs: np.ndarray) -> None:
        """写入理想电流源 stamp。

        电流源不改变 MNA 矩阵，只改变右端项。方向定义为从 positive 流向 negative，
        因此 positive 节点 KCL 中表现为流出，negative 节点表现为注入。
        """

        add_current_source(
            rhs,
            context.node_index(self.positive),
            context.node_index(self.negative),
            _value_at(self.current, context.time, name=self.name),
        )

@dataclass(slots=True)
class VoltageSource(Component):
    """理想电压源。

    MNA 无法只用节点电压处理理想电压源，因此需要额外增加一个支路电流未知量。
    方程形式为 `V_positive - V_negative = voltage`。
    """

    name: str
    positive: str
    negative: str
    voltage: TimeValue
    branch_index: int | None = field(default=None, init=False)

    def __post_init__(self) -> None:
        if not callable(self.voltage) and not np.isfinite(float(self.voltage)):
            raise ValueError(f"电压源 {self.name} 的常数电压必须为有限数。")

    def nodes(self) -> Iterable[str]:
        return (self.positive, self.negative)

    def register(self, node_manager: NodeManager, variable_manager: VariableManager) -> None:
        """为理想电压源注册支路电流未知量。

        只用节点电压无法直接表达理想电压源的电流，因此 MNA 增加一个电压源支路
        电流变量。该变量同时参与节点 KCL 和电压源约束方程。
        """

        self.branch_index = variable_manager.add_branch_current(self.name)

    def stamp(self, context: StampContext, matrix: np.ndarray, rhs: np.ndarray) -> None:
        """写入理想电压源 stamp。

        stamp 包含两部分：

        1. 在节点 KCL 方程中写入支路电流对 positive、negative 节点的贡献。
        2. 增加约束方程 `V_positive - V_negative = voltage`。
        """

        if self.branch_index is None:
            raise RuntimeError(f"电压源 {self.name} 尚未注册支路电流变量。")
        branch = context.branch_offset + self.branch_index
        p = context.node_index(self.positive)
        n = context.node_index(self.negative)
        if p is not None:
            matrix[p, branch] += 1.0
            matrix[branch, p] += 1.0
        if n is not None:
            matrix[n, branch] -= 1.0
            matrix[branch, n] -= 1.0
        rhs[branch] += _value_at(self.voltage, context.time, name=self.name)

    def outputs(self, context: StampContext, solution: np.ndarray) -> dict[str, float]:
        """记录电压源支路电流。"""

        if self.branch_index is None:
            return {}
        return {f"i:{self.name}": float(solution[context.branch_offset + self.branch_index])}

@dataclass(slots=True)
class Capacitor(Component):
    """线性电容。

    对电容电流 `i = C dv/dt` 进行离散化后，可得到一个并联等效电导和历史电流源。
    这里的电流方向定义为从 `positive` 流向 `negative`。
    """

    name: str
    positive: str
    negative: str
    capacitance: float
    initial_voltage: float = 0.0
    previous_voltage: float = field(init=False)
    previous_current: float = field(default=0.0, init=False)
    last_current: float = field(default=0.0, init=False)

    def __post_init__(self) -> None:
        if not np.isfinite(self.capacitance):
            raise ValueError(f"电容 {self.name} 的电容值必须为有限数。")
        if self.capacitance <= 0:
            raise ValueError(f"电容 {self.name} 的电容值必须大于 0。")
        if not np.isfinite(self.initial_voltage):
            raise ValueError(f"电容 {self.name} 的初始电压必须为有限数。")
        self.previous_voltage = float(self.initial_voltage)

    def nodes(self) -> Iterable[str]:
        return (self.positive, self.negative)

    def stamp(self, context: StampContext, matrix: np.ndarray, rhs: np.ndarray) -> None:
        """写入电容离散化 stamp。

        电容通过积分方法等效为“并联电导 + 历史电流源”。电导进入 MNA 矩阵，
        历史电流源进入右端项。这样动态元件就能放入当前时间步的线性方程。
        """

        conductance, history_current = self._companion(context)
        p = context.node_index(self.positive)
        n = context.node_index(self.negative)
        add_conductance(matrix, p, n, conductance)
        add_current_source(rhs, p, n, history_current)

    def update_state(self, context: StampContext, solution: np.ndarray) -> None:
        """更新电容历史电压和历史电流。

        求解后可得到当前电容电压 `v_k`，再用本步等效模型计算当前电流 `i_k`。
        这两个量会在下一时间步构造历史源。
        """

        voltage = add_voltage_probe(solution, context.node_index(self.positive), context.node_index(self.negative))
        conductance, history_current = self._companion(context)
        self.last_current = conductance * voltage + history_current
        self.previous_voltage = voltage
        self.previous_current = self.last_current

    def outputs(self, context: StampContext, solution: np.ndarray) -> dict[str, float]:
        """记录电容两端电压和电容电流。"""

        voltage = add_voltage_probe(solution, context.node_index(self.positive), context.node_index(self.negative))
        return {f"v:{self.name}": voltage, f"i:{self.name}": self.last_current}

    def _companion(self, context: StampContext) -> tuple[float, float]:
        """计算电容 companion model 的等效电导和历史电流源。

        梯形积分：

        `i_k = G v_k + I_hist`

        其中 `G = 2C / dt`，`I_hist = -i_{k-1} - G v_{k-1}`。
        """

        if context.method == "trapezoidal":
            conductance = 2.0 * self.capacitance / context.time_step
            history_current = -self.previous_current - conductance * self.previous_voltage
        elif context.method == "backward_euler":
            conductance = self.capacitance / context.time_step
            history_current = -conductance * self.previous_voltage
        else:
            raise ValueError(f"不支持的积分方法：{context.method}")
        return conductance, history_current

@dataclass(slots=True)
class Inductor(Component):
    """线性电感。

    电感电流作为 MNA 额外未知量。离散化后得到支路方程：
    `V_positive - V_negative - R_eq * i = history_voltage`。
    """

    name: str
    positive: str
    negative: str
    inductance: float
    initial_current: float = 0.0
    branch_index: int | None = field(default=None, init=False)
    previous_current: float = field(init=False)
    previous_voltage: float = field(default=0.0, init=False)
    last_voltage: float = field(default=0.0, init=False)

    def __post_init__(self) -> None:
        if not np.isfinite(self.inductance):
            raise ValueError(f"电感 {self.name} 的电感值必须为有限数。")
        if self.inductance <= 0:
            raise ValueError(f"电感 {self.name} 的电感值必须大于 0。")
        if not np.isfinite(self.initial_current):
            raise ValueError(f"电感 {self.name} 的初始电流必须为有限数。")
        self.previous_current = float(self.initial_current)

    def nodes(self) -> Iterable[str]:
        return (self.positive, self.negative)

    def register(self, node_manager: NodeManager, variable_manager: VariableManager) -> None:
        """为电感注册支路电流未知量。

        电感电压由电流变化率决定，采用支路电流作为未知量后，可以把电感方程写成
        MNA 中的一条支路约束方程。
        """

        self.branch_index = variable_manager.add_branch_current(self.name)

    def stamp(self, context: StampContext, matrix: np.ndarray, rhs: np.ndarray) -> None:
        """写入电感离散化 stamp。

        电感的离散方程写成 `v_p - v_n - R_eq * i = V_hist`。其中支路电流 `i`
        是 MNA 未知量，因此该方程会占用电感自己的支路变量行。
        """

        if self.branch_index is None:
            raise RuntimeError(f"电感 {self.name} 尚未注册支路电流变量。")
        branch = context.branch_offset + self.branch_index
        p = context.node_index(self.positive)
        n = context.node_index(self.negative)
        resistance, history_voltage = self._companion(context)

        if p is not None:
            matrix[p, branch] += 1.0
            matrix[branch, p] += 1.0
        if n is not None:
            matrix[n, branch] -= 1.0
            matrix[branch, n] -= 1.0
        matrix[branch, branch] -= resistance
        rhs[branch] += history_voltage

    def update_state(self, context: StampContext, solution: np.ndarray) -> None:
        """更新电感历史电流和历史电压。"""

        if self.branch_index is None:
            return
        branch = context.branch_offset + self.branch_index
        current = float(solution[branch])
        voltage = add_voltage_probe(solution, context.node_index(self.positive), context.node_index(self.negative))
        self.previous_current = current
        self.previous_voltage = voltage
        self.last_voltage = voltage

    def outputs(self, context: StampContext, solution: np.ndarray) -> dict[str, float]:
        """记录电感支路电流和两端电压。"""

        if self.branch_index is None:
            return {}
        current = float(solution[context.branch_offset + self.branch_index])
        return {f"i:{self.name}": current, f"v:{self.name}": self.last_voltage}

    def _companion(self, context: StampContext) -> tuple[float, float]:
        """计算电感 companion model 的等效电阻和历史电压源。"""

        if context.method == "trapezoidal":
            resistance = 2.0 * self.inductance / context.time_step
            history_voltage = -resistance * self.previous_current - self.previous_voltage
        elif context.method == "backward_euler":
            resistance = self.inductance / context.time_step
            history_voltage = -resistance * self.previous_current
        else:
            raise ValueError(f"不支持的积分方法：{context.method}")
        return resistance, history_voltage
