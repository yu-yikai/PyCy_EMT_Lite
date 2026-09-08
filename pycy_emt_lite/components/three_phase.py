"""
文件名称：three_phase.py
文件作用：实现阶段 2 的三相电源、线路和负荷简化模型。

主要内容：
1. 三相节点命名辅助函数
2. 三相对称正弦电压源
3. 三相串联 RL 线路简化模型
4. 三相星形 RL 负荷简化模型
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Iterable, Literal

import numpy as np

from pycy_emt_lite.components.base import Component
from pycy_emt_lite.core.context import StampContext
from pycy_emt_lite.core.nodes import NodeManager
from pycy_emt_lite.core.stamping import add_conductance, add_current_source, add_voltage_probe
from pycy_emt_lite.core.variables import VariableManager

PhaseName = Literal["a", "b", "c"]
PHASES: tuple[PhaseName, PhaseName, PhaseName] = ("a", "b", "c")

def phase_node(bus: str, phase: PhaseName) -> str:
    """返回三相节点名称。

    阶段 2 采用 `母线:相别` 的命名方式，例如 `source:a`、`load:b`。
    参考地 `"0"`、`"gnd"`、`"ground"` 不附加相别。
    """

    if bus.lower() in {"0", "gnd", "ground"}:
        return bus
    return f"{bus}:{phase}"

def phase_column(prefix: str, phase: PhaseName) -> str:
    """返回三相结果字段名中常用的 `前缀:相别` 片段。"""

    return f"{prefix}:{phase}"

def _phase_angle(phase: PhaseName, initial_angle: float) -> float:
    """返回正序三相的相角。"""

    offsets = {"a": 0.0, "b": -2.0 * math.pi / 3.0, "c": 2.0 * math.pi / 3.0}
    return initial_angle + offsets[phase]

@dataclass(slots=True)
class ThreePhaseSource(Component):
    """三相对称正弦电压源。

    该模型等效为三只相对中性点的理想电压源，默认采用正序 `a-b-c`，
    相电压有效值由 `phase_rms` 给出。
    """

    name: str
    terminal_bus: str
    phase_rms: float
    frequency: float = 50.0
    neutral: str = "0"
    initial_angle: float = 0.0
    branch_indices: dict[PhaseName, int] = field(default_factory=dict, init=False)

    def __post_init__(self) -> None:
        if not math.isfinite(self.phase_rms) or self.phase_rms <= 0:
            raise ValueError(f"三相电源 {self.name} 的相电压有效值必须为有限正数。")
        if not math.isfinite(self.frequency) or self.frequency <= 0:
            raise ValueError(f"三相电源 {self.name} 的频率必须为有限正数。")
        if not math.isfinite(self.initial_angle):
            raise ValueError(f"三相电源 {self.name} 的初相角必须为有限数。")

    def nodes(self) -> Iterable[str]:
        return [phase_node(self.terminal_bus, phase) for phase in PHASES] + [self.neutral]

    def register(self, node_manager: NodeManager, variable_manager: VariableManager) -> None:
        """为三相电源的每一相注册一个支路电流未知量。"""

        self.branch_indices = {phase: variable_manager.add_branch_current(f"{self.name}:{phase}") for phase in PHASES}

    def stamp(self, context: StampContext, matrix: np.ndarray, rhs: np.ndarray) -> None:
        """写入三相理想电压源 stamp。"""

        amplitude = math.sqrt(2.0) * self.phase_rms
        omega = 2.0 * math.pi * self.frequency
        neutral = context.node_index(self.neutral)
        for phase in PHASES:
            branch = context.branch_offset + self.branch_indices[phase]
            phase_index = context.node_index(phase_node(self.terminal_bus, phase))
            if phase_index is not None:
                matrix[phase_index, branch] += 1.0
                matrix[branch, phase_index] += 1.0
            if neutral is not None:
                matrix[neutral, branch] -= 1.0
                matrix[branch, neutral] -= 1.0
            rhs[branch] += amplitude * math.sin(omega * context.time + _phase_angle(phase, self.initial_angle))

    def outputs(self, context: StampContext, solution: np.ndarray) -> dict[str, float]:
        """记录三相电源各相支路电流。"""

        return {
            f"i:{self.name}:{phase}": float(solution[context.branch_offset + self.branch_indices[phase]])
            for phase in PHASES
        }

@dataclass(slots=True)
class _SeriesRlState:
    """三相串联 RL 支路的历史状态。"""

    previous_current: dict[PhaseName, float] = field(default_factory=lambda: {phase: 0.0 for phase in PHASES})
    previous_inductor_voltage: dict[PhaseName, float] = field(default_factory=lambda: {phase: 0.0 for phase in PHASES})
    last_current: dict[PhaseName, float] = field(default_factory=lambda: {phase: 0.0 for phase in PHASES})
    last_voltage: dict[PhaseName, float] = field(default_factory=lambda: {phase: 0.0 for phase in PHASES})

@dataclass(slots=True)
class _ShuntCapacitorState:
    """并联电容 companion model 的历史状态。"""

    previous_voltage: dict[PhaseName, float] = field(default_factory=lambda: {phase: 0.0 for phase in PHASES})
    previous_current: dict[PhaseName, float] = field(default_factory=lambda: {phase: 0.0 for phase in PHASES})
    last_current: dict[PhaseName, float] = field(default_factory=lambda: {phase: 0.0 for phase in PHASES})

def _validate_series_rl(name: str, resistance: float, inductance: float) -> None:
    """检查串联 RL 参数。"""

    if not math.isfinite(resistance) or resistance < 0:
        raise ValueError(f"{name} 的电阻必须为有限非负数。")
    if not math.isfinite(inductance) or inductance < 0:
        raise ValueError(f"{name} 的电感必须为有限非负数。")
    if resistance == 0 and inductance == 0:
        raise ValueError(f"{name} 的电阻和电感不能同时为 0。")

def _companion(method: str, time_step: float, inductance: float, previous_current: float, previous_inductor_voltage: float) -> tuple[float, float]:
    """返回串联电感 companion model 的等效电阻和历史电压。"""

    if method == "trapezoidal":
        resistance = 2.0 * inductance / time_step
        history_voltage = -resistance * previous_current - previous_inductor_voltage
    elif method == "backward_euler":
        resistance = inductance / time_step
        history_voltage = -resistance * previous_current
    else:
        raise ValueError(f"不支持的积分方法：{method}")
    return resistance, history_voltage

def _capacitor_companion(
    method: str,
    time_step: float,
    capacitance: float,
    previous_voltage: float,
    previous_current: float,
) -> tuple[float, float]:
    """返回并联电容 companion model 的等效电导和历史电流。"""

    if method == "trapezoidal":
        conductance = 2.0 * capacitance / time_step
        history_current = -previous_current - conductance * previous_voltage
    elif method == "backward_euler":
        conductance = capacitance / time_step
        history_current = -conductance * previous_voltage
    else:
        raise ValueError(f"不支持的积分方法：{method}")
    return conductance, history_current

@dataclass(slots=True)
class ThreePhaseLine(Component):
    """三相线路简化模型。

    每相线路被建模为从 `from_bus:相别` 到 `to_bus:相别` 的串联 `R-L` 支路。
    `inductance` 可以取 0，此时退化为纯电阻线路。
    """

    name: str
    from_bus: str
    to_bus: str
    resistance: float
    inductance: float = 0.0
    branch_indices: dict[PhaseName, int] = field(default_factory=dict, init=False)
    state: _SeriesRlState = field(default_factory=_SeriesRlState, init=False)

    def __post_init__(self) -> None:
        _validate_series_rl(f"三相线路 {self.name}", self.resistance, self.inductance)

    def nodes(self) -> Iterable[str]:
        nodes: list[str] = []
        for phase in PHASES:
            nodes.append(phase_node(self.from_bus, phase))
            nodes.append(phase_node(self.to_bus, phase))
        return nodes

    def register(self, node_manager: NodeManager, variable_manager: VariableManager) -> None:
        """当线路含电感时，为每相注册一个支路电流未知量。"""

        if self.inductance > 0:
            self.branch_indices = {phase: variable_manager.add_branch_current(f"{self.name}:{phase}") for phase in PHASES}

    def stamp(self, context: StampContext, matrix: np.ndarray, rhs: np.ndarray) -> None:
        """写入三相线路 stamp。"""

        for phase in PHASES:
            p = context.node_index(phase_node(self.from_bus, phase))
            n = context.node_index(phase_node(self.to_bus, phase))
            if self.inductance == 0:
                add_conductance(matrix, p, n, 1.0 / self.resistance)
                continue
            branch = context.branch_offset + self.branch_indices[phase]
            eq_resistance, history_voltage = _companion(
                context.method,
                context.time_step,
                self.inductance,
                self.state.previous_current[phase],
                self.state.previous_inductor_voltage[phase],
            )
            if p is not None:
                matrix[p, branch] += 1.0
                matrix[branch, p] += 1.0
            if n is not None:
                matrix[n, branch] -= 1.0
                matrix[branch, n] -= 1.0
            matrix[branch, branch] -= self.resistance + eq_resistance
            rhs[branch] += history_voltage

    def update_state(self, context: StampContext, solution: np.ndarray) -> None:
        """更新三相线路历史电流和电感电压。"""

        for phase in PHASES:
            p = context.node_index(phase_node(self.from_bus, phase))
            n = context.node_index(phase_node(self.to_bus, phase))
            voltage = add_voltage_probe(solution, p, n)
            if self.inductance > 0:
                current = float(solution[context.branch_offset + self.branch_indices[phase]])
                self.state.previous_current[phase] = current
                self.state.previous_inductor_voltage[phase] = voltage - self.resistance * current
                self.state.last_current[phase] = current
            else:
                self.state.last_current[phase] = voltage / self.resistance
            self.state.last_voltage[phase] = voltage

    def outputs(self, context: StampContext, solution: np.ndarray) -> dict[str, float]:
        """记录线路各相电流和两端电压。"""

        outputs: dict[str, float] = {}
        for phase in PHASES:
            outputs[f"i:{self.name}:{phase}"] = self.state.last_current[phase]
            outputs[f"v:{self.name}:{phase}"] = self.state.last_voltage[phase]
        return outputs

@dataclass(slots=True)
class ThreePhaseParallelRLCLoad(Component):
    """三相接地星形并联 RLC/PQ 负荷模型。

    该模型用于复现 Specialized Power Systems 的 ``Three-Phase Parallel RLC Load``
    常见设置。用户给定三相总有功、感性无功、容性无功和额定线电压后，模型按额定相电压
    换算每相并联电阻、电感和电容。它是固定导纳负荷，不进行恒功率非线性迭代。
    """

    name: str
    bus: str
    nominal_line_voltage: float
    active_power: float
    inductive_power: float = 0.0
    capacitive_power: float = 0.0
    frequency: float = 50.0
    neutral: str = "0"
    inductor_branch_indices: dict[PhaseName, int] = field(default_factory=dict, init=False)
    inductor_state: _SeriesRlState = field(default_factory=_SeriesRlState, init=False)
    capacitor_state: _ShuntCapacitorState = field(default_factory=_ShuntCapacitorState, init=False)
    last_total_current: dict[PhaseName, float] = field(default_factory=lambda: {phase: 0.0 for phase in PHASES}, init=False)
    last_phase_voltage: dict[PhaseName, float] = field(default_factory=lambda: {phase: 0.0 for phase in PHASES}, init=False)

    def __post_init__(self) -> None:
        if not math.isfinite(self.nominal_line_voltage) or self.nominal_line_voltage <= 0.0:
            raise ValueError(f"三相并联负荷 {self.name} 的额定线电压必须为有限正数。")
        if not math.isfinite(self.frequency) or self.frequency <= 0.0:
            raise ValueError(f"三相并联负荷 {self.name} 的频率必须为有限正数。")
        if not math.isfinite(self.active_power) or self.active_power < 0.0:
            raise ValueError(f"三相并联负荷 {self.name} 的有功功率必须为有限非负数。")
        if not math.isfinite(self.inductive_power) or self.inductive_power < 0.0:
            raise ValueError(f"三相并联负荷 {self.name} 的感性无功必须为有限非负数。")
        if not math.isfinite(self.capacitive_power) or self.capacitive_power < 0.0:
            raise ValueError(f"三相并联负荷 {self.name} 的容性无功必须为有限非负数。")
        if self.active_power == 0.0 and self.inductive_power == 0.0 and self.capacitive_power == 0.0:
            raise ValueError(f"三相并联负荷 {self.name} 的 P、QL、QC 不能同时为 0。")

    @property
    def nominal_phase_voltage(self) -> float:
        """返回额定相电压 RMS。"""

        return self.nominal_line_voltage / math.sqrt(3.0)

    @property
    def phase_conductance(self) -> float:
        """返回每相有功支路电导。"""

        phase_power = self.active_power / 3.0
        return phase_power / self.nominal_phase_voltage**2 if phase_power > 0.0 else 0.0

    @property
    def phase_inductance(self) -> float:
        """返回每相感性无功支路电感；无感性无功时返回 0。"""

        phase_reactive_power = self.inductive_power / 3.0
        if phase_reactive_power == 0.0:
            return 0.0
        omega = 2.0 * math.pi * self.frequency
        return self.nominal_phase_voltage**2 / (omega * phase_reactive_power)

    @property
    def phase_capacitance(self) -> float:
        """返回每相容性无功支路电容；无容性无功时返回 0。"""

        phase_reactive_power = self.capacitive_power / 3.0
        if phase_reactive_power == 0.0:
            return 0.0
        omega = 2.0 * math.pi * self.frequency
        return phase_reactive_power / (omega * self.nominal_phase_voltage**2)

    def nodes(self) -> Iterable[str]:
        return [phase_node(self.bus, phase) for phase in PHASES] + [self.neutral]

    def register(self, node_manager: NodeManager, variable_manager: VariableManager) -> None:
        """感性无功支路存在时，为每相并联电感注册支路电流变量。"""

        if self.phase_inductance > 0.0:
            self.inductor_branch_indices = {
                phase: variable_manager.add_branch_current(f"{self.name}:L:{phase}") for phase in PHASES
            }

    def stamp(self, context: StampContext, matrix: np.ndarray, rhs: np.ndarray) -> None:
        """写入三相并联 RLC 负荷的 MNA stamp。"""

        neutral = context.node_index(self.neutral)
        conductance = self.phase_conductance
        inductance = self.phase_inductance
        capacitance = self.phase_capacitance
        for phase in PHASES:
            p = context.node_index(phase_node(self.bus, phase))
            if conductance > 0.0:
                add_conductance(matrix, p, neutral, conductance)
            if inductance > 0.0:
                branch = context.branch_offset + self.inductor_branch_indices[phase]
                eq_resistance, history_voltage = _companion(
                    context.method,
                    context.time_step,
                    inductance,
                    self.inductor_state.previous_current[phase],
                    self.inductor_state.previous_inductor_voltage[phase],
                )
                if p is not None:
                    matrix[p, branch] += 1.0
                    matrix[branch, p] += 1.0
                if neutral is not None:
                    matrix[neutral, branch] -= 1.0
                    matrix[branch, neutral] -= 1.0
                matrix[branch, branch] -= eq_resistance
                rhs[branch] += history_voltage
            if capacitance > 0.0:
                cap_conductance, history_current = _capacitor_companion(
                    context.method,
                    context.time_step,
                    capacitance,
                    self.capacitor_state.previous_voltage[phase],
                    self.capacitor_state.previous_current[phase],
                )
                add_conductance(matrix, p, neutral, cap_conductance)
                add_current_source(rhs, p, neutral, history_current)

    def update_state(self, context: StampContext, solution: np.ndarray) -> None:
        """更新每相并联支路历史状态和总负荷电流。"""

        neutral = context.node_index(self.neutral)
        conductance = self.phase_conductance
        inductance = self.phase_inductance
        capacitance = self.phase_capacitance
        for phase in PHASES:
            p = context.node_index(phase_node(self.bus, phase))
            voltage = add_voltage_probe(solution, p, neutral)
            resistive_current = conductance * voltage
            inductive_current = 0.0
            if inductance > 0.0:
                branch = context.branch_offset + self.inductor_branch_indices[phase]
                inductive_current = float(solution[branch])
                self.inductor_state.previous_current[phase] = inductive_current
                self.inductor_state.previous_inductor_voltage[phase] = voltage
                self.inductor_state.last_current[phase] = inductive_current
                self.inductor_state.last_voltage[phase] = voltage
            capacitive_current = 0.0
            if capacitance > 0.0:
                cap_conductance, history_current = _capacitor_companion(
                    context.method,
                    context.time_step,
                    capacitance,
                    self.capacitor_state.previous_voltage[phase],
                    self.capacitor_state.previous_current[phase],
                )
                capacitive_current = cap_conductance * voltage + history_current
                self.capacitor_state.previous_voltage[phase] = voltage
                self.capacitor_state.previous_current[phase] = capacitive_current
                self.capacitor_state.last_current[phase] = capacitive_current
            self.last_phase_voltage[phase] = voltage
            self.last_total_current[phase] = resistive_current + inductive_current + capacitive_current

    def outputs(self, context: StampContext, solution: np.ndarray) -> dict[str, float]:
        """记录每相负荷电流、电压和额定功率换算得到的 R/L/C 参数。"""

        outputs: dict[str, float] = {
            f"r:{self.name}:phase": 1.0 / self.phase_conductance if self.phase_conductance > 0.0 else math.inf,
            f"l:{self.name}:phase": self.phase_inductance,
            f"c:{self.name}:phase": self.phase_capacitance,
        }
        for phase in PHASES:
            outputs[f"i:{self.name}:{phase}"] = self.last_total_current[phase]
            outputs[f"v:{self.name}:{phase}"] = self.last_phase_voltage[phase]
            outputs[f"i:{self.name}:L:{phase}"] = self.inductor_state.last_current[phase]
            outputs[f"i:{self.name}:C:{phase}"] = self.capacitor_state.last_current[phase]
        return outputs

@dataclass(slots=True)
class ThreePhaseLoad(Component):
    """三相星形 RL 负荷简化模型。

    每相负荷连接在 `bus:相别` 与 `neutral` 之间。第一版用于教学和故障算例，
    暂不考虑三角形接法、互感和频率相关参数。
    """

    name: str
    bus: str
    resistance: float
    inductance: float = 0.0
    neutral: str = "0"
    branch_indices: dict[PhaseName, int] = field(default_factory=dict, init=False)
    state: _SeriesRlState = field(default_factory=_SeriesRlState, init=False)

    def __post_init__(self) -> None:
        _validate_series_rl(f"三相负荷 {self.name}", self.resistance, self.inductance)

    def nodes(self) -> Iterable[str]:
        return [phase_node(self.bus, phase) for phase in PHASES] + [self.neutral]

    def register(self, node_manager: NodeManager, variable_manager: VariableManager) -> None:
        """当负荷含电感时，为每相注册一个支路电流未知量。"""

        if self.inductance > 0:
            self.branch_indices = {phase: variable_manager.add_branch_current(f"{self.name}:{phase}") for phase in PHASES}

    def stamp(self, context: StampContext, matrix: np.ndarray, rhs: np.ndarray) -> None:
        """写入三相星形负荷 stamp。"""

        neutral = context.node_index(self.neutral)
        for phase in PHASES:
            p = context.node_index(phase_node(self.bus, phase))
            if self.inductance == 0:
                add_conductance(matrix, p, neutral, 1.0 / self.resistance)
                continue
            branch = context.branch_offset + self.branch_indices[phase]
            eq_resistance, history_voltage = _companion(
                context.method,
                context.time_step,
                self.inductance,
                self.state.previous_current[phase],
                self.state.previous_inductor_voltage[phase],
            )
            if p is not None:
                matrix[p, branch] += 1.0
                matrix[branch, p] += 1.0
            if neutral is not None:
                matrix[neutral, branch] -= 1.0
                matrix[branch, neutral] -= 1.0
            matrix[branch, branch] -= self.resistance + eq_resistance
            rhs[branch] += history_voltage

    def update_state(self, context: StampContext, solution: np.ndarray) -> None:
        """更新三相负荷历史状态。"""

        neutral = context.node_index(self.neutral)
        for phase in PHASES:
            p = context.node_index(phase_node(self.bus, phase))
            voltage = add_voltage_probe(solution, p, neutral)
            if self.inductance > 0:
                current = float(solution[context.branch_offset + self.branch_indices[phase]])
                self.state.previous_current[phase] = current
                self.state.previous_inductor_voltage[phase] = voltage - self.resistance * current
                self.state.last_current[phase] = current
            else:
                self.state.last_current[phase] = voltage / self.resistance
            self.state.last_voltage[phase] = voltage

    def outputs(self, context: StampContext, solution: np.ndarray) -> dict[str, float]:
        """记录负荷各相电流和相电压。"""

        outputs: dict[str, float] = {}
        for phase in PHASES:
            outputs[f"i:{self.name}:{phase}"] = self.state.last_current[phase]
            outputs[f"v:{self.name}:{phase}"] = self.state.last_voltage[phase]
        return outputs
