"""
文件名称：synchronous.py
文件作用：实现同步电机经典二阶教学模型。

主要内容：
1. 三相内电势后接定子 R-L 支路的 MNA stamp
2. 基于摆动方程的转子角和转速更新
3. 机端电压、电流、电磁功率和机械状态输出
"""

from __future__ import annotations

import math
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field

import numpy as np

from pycy_emt_lite.components.base import Component
from pycy_emt_lite.components.basic import _derivative_at
from pycy_emt_lite.components.three_phase import PHASES, PhaseName, _phase_angle, phase_node
from pycy_emt_lite.core.context import StampContext
from pycy_emt_lite.core.nodes import NodeManager
from pycy_emt_lite.core.stamping import add_conductance, add_voltage_probe
from pycy_emt_lite.core.variables import VariableManager

PowerInput = float | Callable[[float], float]

@dataclass(slots=True)
class _MachineState:
    """同步机历史状态和最近一次输出。"""

    rotor_angle: float
    speed_pu: float
    previous_current: dict[PhaseName, float] = field(default_factory=lambda: {phase: 0.0 for phase in PHASES})
    previous_inductor_voltage: dict[PhaseName, float] = field(default_factory=lambda: {phase: 0.0 for phase in PHASES})
    last_current: dict[PhaseName, float] = field(default_factory=lambda: {phase: 0.0 for phase in PHASES})
    last_terminal_voltage: dict[PhaseName, float] = field(default_factory=lambda: {phase: 0.0 for phase in PHASES})
    last_internal_voltage: dict[PhaseName, float] = field(default_factory=lambda: {phase: 0.0 for phase in PHASES})
    electrical_power: float = 0.0
    mechanical_power: float = 0.0

def _value_at(value: PowerInput, time: float) -> float:
    """返回常数或时间函数在当前时刻的值。"""

    if callable(value):
        return float(value(time))
    return float(value)

def _inductor_companion(
    method: str,
    time_step: float,
    inductance: float,
    previous_current: float,
    previous_inductor_voltage: float,
) -> tuple[float, float]:
    """返回定子电感 companion model 的等效电阻和历史电压。"""

    if time_step == 0.0:
        return 0.0, 0.0
    if method == "trapezoidal":
        resistance = 2.0 * inductance / time_step
        history_voltage = -resistance * previous_current - previous_inductor_voltage
    elif method == "backward_euler":
        resistance = inductance / time_step
        history_voltage = -resistance * previous_current
    else:
        raise ValueError(f"不支持的积分方法：{method}")
    return resistance, history_voltage

@dataclass(slots=True)
class SynchronousMachine(Component):
    """同步电机经典二阶教学模型。

    模型采用三相对称内电势后接定子电阻和同步电感的形式：

    `e_phase - v_terminal = R_s i + L_s di/dt`

    转子机电动态采用经典摆动方程：

    `dω_pu/dt = (P_m - P_e - D(ω_pu - 1)) / (2H)`

    该模型适合教学、负荷流初始化趋势复现和系统级暂态入门算例。它不包含励磁
    绕组、阻尼绕组、磁饱和、AVR、PSS 和调速器等高保真结构。
    """

    name: str
    terminal_bus: str
    internal_phase_rms: float
    stator_resistance: float
    stator_inductance: float
    base_power: float
    inertia_constant: float
    mechanical_power: PowerInput = 0.0
    damping: float = 0.0
    frequency: float = 50.0
    neutral: str = "0"
    initial_rotor_angle: float = 0.0
    initial_speed_pu: float = 1.0
    internal_bus: str | None = None
    source_branch_indices: dict[PhaseName, int] = field(default_factory=dict, init=False)
    stator_branch_indices: dict[PhaseName, int] = field(default_factory=dict, init=False)
    state: _MachineState = field(init=False)

    def __post_init__(self) -> None:
        if self.internal_phase_rms <= 0:
            raise ValueError(f"同步机 {self.name} 的内电势相电压 RMS 必须大于 0。")
        if self.stator_resistance < 0:
            raise ValueError(f"同步机 {self.name} 的定子电阻不能小于 0。")
        if self.stator_inductance < 0:
            raise ValueError(f"同步机 {self.name} 的定子电感不能小于 0。")
        if self.stator_resistance == 0 and self.stator_inductance == 0:
            raise ValueError(f"同步机 {self.name} 的定子电阻和定子电感不能同时为 0。")
        if self.base_power <= 0:
            raise ValueError(f"同步机 {self.name} 的基准容量必须大于 0。")
        if self.inertia_constant <= 0:
            raise ValueError(f"同步机 {self.name} 的惯性常数必须大于 0。")
        if self.frequency <= 0:
            raise ValueError(f"同步机 {self.name} 的频率必须大于 0。")
        if self.initial_speed_pu <= 0:
            raise ValueError(f"同步机 {self.name} 的初始转速标幺值必须大于 0。")
        self.state = _MachineState(self.initial_rotor_angle, self.initial_speed_pu)

    @property
    def internal_bus_name(self) -> str:
        """返回内部电势节点母线名。"""

        return self.internal_bus or f"{self.name}_internal"

    def nodes(self) -> Iterable[str]:
        nodes: list[str] = [self.neutral]
        for phase in PHASES:
            nodes.append(phase_node(self.terminal_bus, phase))
            nodes.append(phase_node(self.internal_bus_name, phase))
        return nodes

    def register(self, node_manager: NodeManager, variable_manager: VariableManager) -> None:
        """为三相内电势源和含电感定子支路注册支路变量。"""

        self.source_branch_indices = {
            phase: variable_manager.add_branch_current(f"{self.name}:source:{phase}") for phase in PHASES
        }
        if self.stator_inductance > 0:
            self.stator_branch_indices = {
                phase: variable_manager.add_branch_current(f"{self.name}:stator:{phase}") for phase in PHASES
            }

    def stamp(self, context: StampContext, matrix: np.ndarray, rhs: np.ndarray) -> None:
        """写入同步机内电势源和定子阻抗 stamp。"""

        neutral = context.node_index(self.neutral)
        amplitude = math.sqrt(2.0) * self.internal_phase_rms
        omega_sync = 2.0 * math.pi * self.frequency
        for phase in PHASES:
            internal = context.node_index(phase_node(self.internal_bus_name, phase))
            terminal = context.node_index(phase_node(self.terminal_bus, phase))
            source_branch = context.branch_offset + self.source_branch_indices[phase]
            internal_voltage = amplitude * math.sin(
                omega_sync * context.time + self.state.rotor_angle + _phase_angle(phase, 0.0)
            )
            self.state.last_internal_voltage[phase] = internal_voltage

            if internal is not None:
                matrix[internal, source_branch] += 1.0
                matrix[source_branch, internal] += 1.0
            if neutral is not None:
                matrix[neutral, source_branch] -= 1.0
                matrix[source_branch, neutral] -= 1.0
            rhs[source_branch] += internal_voltage
            if context._initial is not None:
                # 仅覆盖固定机电状态的直接一致求解；不猜测耦合源导数。
                context._initial.source_derivatives.append(({source_branch: 1.0}, lambda:
                    _derivative_at(None, None, context.time, self.name)
                ))

            if self.stator_inductance == 0:
                add_conductance(matrix, internal, terminal, 1.0 / self.stator_resistance)
                continue

            stator_branch = context.branch_offset + self.stator_branch_indices[phase]
            if context._initial is not None:
                context._initial.inductors.append((stator_branch, self.stator_inductance, self.state.previous_current[phase]))
            eq_resistance, history_voltage = _inductor_companion(
                context.method,
                context.time_step,
                self.stator_inductance,
                self.state.previous_current[phase],
                self.state.previous_inductor_voltage[phase],
            )
            if internal is not None:
                matrix[internal, stator_branch] += 1.0
                matrix[stator_branch, internal] += 1.0
            if terminal is not None:
                matrix[terminal, stator_branch] -= 1.0
                matrix[stator_branch, terminal] -= 1.0
            matrix[stator_branch, stator_branch] -= self.stator_resistance + eq_resistance
            rhs[stator_branch] += history_voltage

    def update_state(self, context: StampContext, solution: np.ndarray) -> None:
        """更新定子支路历史项和转子摆动方程状态。"""

        electrical_power = 0.0
        for phase in PHASES:
            internal = context.node_index(phase_node(self.internal_bus_name, phase))
            terminal = context.node_index(phase_node(self.terminal_bus, phase))
            terminal_voltage = add_voltage_probe(solution, terminal, context.node_index(self.neutral))
            branch_voltage = add_voltage_probe(solution, internal, terminal)
            if self.stator_inductance > 0:
                current = float(solution[context.branch_offset + self.stator_branch_indices[phase]])
                self.state.previous_current[phase] = current
                self.state.previous_inductor_voltage[phase] = branch_voltage - self.stator_resistance * current
            else:
                current = branch_voltage / self.stator_resistance
            self.state.last_current[phase] = current
            self.state.last_terminal_voltage[phase] = terminal_voltage
            electrical_power += terminal_voltage * current

        self.state.electrical_power = electrical_power
        self.state.mechanical_power = _value_at(self.mechanical_power, context.time)
        mechanical_pu = self.state.mechanical_power / self.base_power
        electrical_pu = electrical_power / self.base_power
        acceleration = (mechanical_pu - electrical_pu - self.damping * (self.state.speed_pu - 1.0)) / (
            2.0 * self.inertia_constant
        )
        self.state.speed_pu += acceleration * context.time_step
        self.state.rotor_angle += 2.0 * math.pi * self.frequency * (self.state.speed_pu - 1.0) * context.time_step

    def outputs(self, context: StampContext, solution: np.ndarray) -> dict[str, float]:
        """记录同步机电气量和机械状态。"""

        outputs: dict[str, float] = {}
        for phase in PHASES:
            outputs[f"i:{self.name}:{phase}"] = self.state.last_current[phase]
            outputs[f"v:{self.name}:{phase}"] = self.state.last_terminal_voltage[phase]
            outputs[f"e:{self.name}:{phase}"] = self.state.last_internal_voltage[phase]
        outputs[f"p:{self.name}"] = self.state.electrical_power
        outputs[f"p_pu:{self.name}"] = self.state.electrical_power / self.base_power
        outputs[f"pm:{self.name}"] = self.state.mechanical_power
        outputs[f"rotor_angle:{self.name}"] = self.state.rotor_angle
        outputs[f"speed_pu:{self.name}"] = self.state.speed_pu
        return outputs
