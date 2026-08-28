"""
文件名称：park_generator.py
文件作用：实现带 AVR 和调速器的 Park dq0 同步发电机教学模型。

主要内容：
1. 使用 Park dq0 暂态电势方程更新 d/q 轴内部电势
2. 使用一阶 AVR 和一阶调速器更新励磁电压与机械功率
3. 将 dq 内部电势反变换为 abc 三相内电势并通过定子 R-L 支路接入 MNA
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Iterable

import numpy as np

from pycy_emt_lite.components.base import Component
from pycy_emt_lite.components.three_phase import PHASES, PhaseName, phase_node
from pycy_emt_lite.controls import abc_to_dq, dq_to_abc
from pycy_emt_lite.core.context import StampContext
from pycy_emt_lite.core.nodes import NodeManager
from pycy_emt_lite.core.stamping import add_conductance, add_voltage_probe
from pycy_emt_lite.core.variables import VariableManager

def _companion(
    method: str,
    time_step: float,
    inductance: float,
    previous_current: float,
    previous_inductor_voltage: float,
) -> tuple[float, float]:
    """返回定子电感 companion model 的等效电阻和历史电压。"""

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
class _ParkGeneratorState:
    """Park 发电机动态状态和最近一次输出。"""

    rotor_angle: float
    speed_pu: float
    eq_prime_pu: float
    ed_prime_pu: float
    efd_pu: float
    mechanical_power_pu: float
    previous_current: dict[PhaseName, float] = field(default_factory=lambda: {phase: 0.0 for phase in PHASES})
    previous_inductor_voltage: dict[PhaseName, float] = field(default_factory=lambda: {phase: 0.0 for phase in PHASES})
    last_current: dict[PhaseName, float] = field(default_factory=lambda: {phase: 0.0 for phase in PHASES})
    last_terminal_voltage: dict[PhaseName, float] = field(default_factory=lambda: {phase: 0.0 for phase in PHASES})
    last_internal_voltage: dict[PhaseName, float] = field(default_factory=lambda: {phase: 0.0 for phase in PHASES})
    id_pu: float = 0.0
    iq_pu: float = 0.0
    vd_pu: float = 0.0
    vq_pu: float = 0.0
    terminal_voltage_pu: float = 0.0
    electrical_power: float = 0.0

@dataclass(slots=True)
class ParkSynchronousGenerator(Component):
    """带 AVR 和调速器的 Park dq0 同步发电机教学模型。

    电气部分采用暂态电势形式：

    ```text
    dE'_q/dt = (E_fd - E'_q - (X_d - X'_d) I_d) / T'_do
    dE'_d/dt = (-E'_d + (X_q - X'_q) I_q) / T'_qo
    ```

    机电部分采用摆动方程，励磁和原动机分别采用一阶 AVR、调速器近似。模型适合
    教学和中等复杂度系统暂态算例，不包含阻尼绕组、磁饱和、PSS 和多质量轴系。
    """

    name: str
    terminal_bus: str
    base_power: float
    base_phase_rms: float
    stator_resistance_pu: float
    d_axis_reactance_pu: float
    q_axis_reactance_pu: float
    d_axis_transient_reactance_pu: float
    q_axis_transient_reactance_pu: float
    d_axis_open_circuit_time_constant: float
    q_axis_open_circuit_time_constant: float
    inertia_constant: float
    damping: float = 0.0
    voltage_reference_pu: float = 1.0
    avr_gain: float = 20.0
    avr_time_constant: float = 0.05
    efd_min_pu: float = 0.0
    efd_max_pu: float = 5.0
    mechanical_power_reference_pu: float = 0.0
    governor_droop: float = 0.05
    governor_time_constant: float = 0.2
    mechanical_power_min_pu: float = 0.0
    mechanical_power_max_pu: float = 2.0
    frequency: float = 50.0
    neutral: str = "0"
    initial_rotor_angle: float = 0.0
    initial_speed_pu: float = 1.0
    initial_eq_prime_pu: float = 1.0
    initial_ed_prime_pu: float = 0.0
    initial_efd_pu: float = 1.0
    initial_mechanical_power_pu: float = 0.0
    internal_bus: str | None = None
    source_branch_indices: dict[PhaseName, int] = field(default_factory=dict, init=False)
    stator_branch_indices: dict[PhaseName, int] = field(default_factory=dict, init=False)
    state: _ParkGeneratorState = field(init=False)

    def __post_init__(self) -> None:
        self._validate_parameters()
        self.state = _ParkGeneratorState(
            rotor_angle=self.initial_rotor_angle,
            speed_pu=self.initial_speed_pu,
            eq_prime_pu=self.initial_eq_prime_pu,
            ed_prime_pu=self.initial_ed_prime_pu,
            efd_pu=self.initial_efd_pu,
            mechanical_power_pu=self.initial_mechanical_power_pu,
        )

    @property
    def internal_bus_name(self) -> str:
        """返回内部电势节点母线名。"""

        return self.internal_bus or f"{self.name}_internal"

    @property
    def base_impedance(self) -> float:
        """返回三相系统以相电压 RMS 定义的基准阻抗。"""

        return 3.0 * self.base_phase_rms**2 / self.base_power

    @property
    def stator_resistance(self) -> float:
        """返回定子电阻实际值。"""

        return self.stator_resistance_pu * self.base_impedance

    @property
    def stator_inductance(self) -> float:
        """返回用于 MNA 接口的暂态电抗等效电感。"""

        omega = 2.0 * math.pi * self.frequency
        return self.d_axis_transient_reactance_pu * self.base_impedance / omega

    def nodes(self) -> Iterable[str]:
        nodes: list[str] = [self.neutral]
        for phase in PHASES:
            nodes.append(phase_node(self.terminal_bus, phase))
            nodes.append(phase_node(self.internal_bus_name, phase))
        return nodes

    def register(self, node_manager: NodeManager, variable_manager: VariableManager) -> None:
        """为三相内部受控电势源和含电感定子支路注册支路变量。"""

        self.source_branch_indices = {
            phase: variable_manager.add_branch_current(f"{self.name}:source:{phase}") for phase in PHASES
        }
        if self.stator_inductance > 0.0:
            self.stator_branch_indices = {
                phase: variable_manager.add_branch_current(f"{self.name}:stator:{phase}") for phase in PHASES
            }

    def stamp(self, context: StampContext, matrix: np.ndarray, rhs: np.ndarray) -> None:
        """把 dq 内部电势反变换为 abc 后写入 MNA stamp。"""

        neutral = context.node_index(self.neutral)
        electrical_angle = self._electrical_angle(context.time)
        e_abc_pu = dq_to_abc(self.state.ed_prime_pu, -self.state.eq_prime_pu, electrical_angle)
        amplitude = math.sqrt(2.0) * self.base_phase_rms
        resistance = self.stator_resistance
        inductance = self.stator_inductance
        for phase, internal_voltage_pu in zip(PHASES, e_abc_pu, strict=True):
            internal = context.node_index(phase_node(self.internal_bus_name, phase))
            terminal = context.node_index(phase_node(self.terminal_bus, phase))
            source_branch = context.branch_offset + self.source_branch_indices[phase]
            internal_voltage = amplitude * internal_voltage_pu
            self.state.last_internal_voltage[phase] = internal_voltage

            if internal is not None:
                matrix[internal, source_branch] += 1.0
                matrix[source_branch, internal] += 1.0
            if neutral is not None:
                matrix[neutral, source_branch] -= 1.0
                matrix[source_branch, neutral] -= 1.0
            rhs[source_branch] += internal_voltage

            if inductance == 0.0:
                add_conductance(matrix, internal, terminal, 1.0 / resistance)
                continue

            stator_branch = context.branch_offset + self.stator_branch_indices[phase]
            eq_resistance, history_voltage = _companion(
                context.method,
                context.time_step,
                inductance,
                self.state.previous_current[phase],
                self.state.previous_inductor_voltage[phase],
            )
            if internal is not None:
                matrix[internal, stator_branch] += 1.0
                matrix[stator_branch, internal] += 1.0
            if terminal is not None:
                matrix[terminal, stator_branch] -= 1.0
                matrix[stator_branch, terminal] -= 1.0
            matrix[stator_branch, stator_branch] -= resistance + eq_resistance
            rhs[stator_branch] += history_voltage

    def update_state(self, context: StampContext, solution: np.ndarray) -> None:
        """更新定子历史项、dq0 状态、AVR、调速器和摆动方程。"""

        terminal_voltages: dict[PhaseName, float] = {}
        currents: dict[PhaseName, float] = {}
        electrical_power = 0.0
        neutral = context.node_index(self.neutral)
        resistance = self.stator_resistance
        inductance = self.stator_inductance
        for phase in PHASES:
            internal = context.node_index(phase_node(self.internal_bus_name, phase))
            terminal = context.node_index(phase_node(self.terminal_bus, phase))
            terminal_voltage = add_voltage_probe(solution, terminal, neutral)
            branch_voltage = add_voltage_probe(solution, internal, terminal)
            if inductance > 0.0:
                current = float(solution[context.branch_offset + self.stator_branch_indices[phase]])
                self.state.previous_current[phase] = current
                self.state.previous_inductor_voltage[phase] = branch_voltage - resistance * current
            else:
                current = branch_voltage / resistance
            terminal_voltages[phase] = terminal_voltage
            currents[phase] = current
            self.state.last_terminal_voltage[phase] = terminal_voltage
            self.state.last_current[phase] = current
            electrical_power += terminal_voltage * current

        electrical_angle = self._electrical_angle(context.time)
        vd_raw, vq_raw = abc_to_dq(
            terminal_voltages["a"], terminal_voltages["b"], terminal_voltages["c"], electrical_angle
        )
        id_raw, iq_raw = abc_to_dq(currents["a"], currents["b"], currents["c"], electrical_angle)
        voltage_base_peak = math.sqrt(2.0) * self.base_phase_rms
        current_base_peak = math.sqrt(2.0) * self.base_power / (3.0 * self.base_phase_rms)
        self.state.vd_pu = vd_raw / voltage_base_peak
        self.state.vq_pu = -vq_raw / voltage_base_peak
        self.state.id_pu = id_raw / current_base_peak
        self.state.iq_pu = -iq_raw / current_base_peak
        self.state.terminal_voltage_pu = math.hypot(vd_raw, vq_raw) / voltage_base_peak
        self.state.electrical_power = electrical_power

        self._update_controls_and_machine(context.time_step, electrical_power)

    def outputs(self, context: StampContext, solution: np.ndarray) -> dict[str, float]:
        """记录 Park 发电机电气量、控制量和机械状态。"""

        outputs: dict[str, float] = {}
        for phase in PHASES:
            outputs[f"i:{self.name}:{phase}"] = self.state.last_current[phase]
            outputs[f"v:{self.name}:{phase}"] = self.state.last_terminal_voltage[phase]
            outputs[f"e:{self.name}:{phase}"] = self.state.last_internal_voltage[phase]
        outputs[f"id_pu:{self.name}"] = self.state.id_pu
        outputs[f"iq_pu:{self.name}"] = self.state.iq_pu
        outputs[f"vd_pu:{self.name}"] = self.state.vd_pu
        outputs[f"vq_pu:{self.name}"] = self.state.vq_pu
        outputs[f"vt_pu:{self.name}"] = self.state.terminal_voltage_pu
        outputs[f"eq_prime_pu:{self.name}"] = self.state.eq_prime_pu
        outputs[f"ed_prime_pu:{self.name}"] = self.state.ed_prime_pu
        outputs[f"efd_pu:{self.name}"] = self.state.efd_pu
        outputs[f"pm_pu:{self.name}"] = self.state.mechanical_power_pu
        outputs[f"p:{self.name}"] = self.state.electrical_power
        outputs[f"p_pu:{self.name}"] = self.state.electrical_power / self.base_power
        outputs[f"rotor_angle:{self.name}"] = self.state.rotor_angle
        outputs[f"speed_pu:{self.name}"] = self.state.speed_pu
        return outputs

    def _electrical_angle(self, time: float) -> float:
        """返回当前同步参考角和转子相对角之和。"""

        return 2.0 * math.pi * self.frequency * time + self.state.rotor_angle

    def _update_controls_and_machine(self, time_step: float, electrical_power: float) -> None:
        """按显式欧拉更新 AVR、调速器、暂态电势和摆动方程。"""

        avr_target = self.voltage_reference_pu + self.avr_gain * (
            self.voltage_reference_pu - self.state.terminal_voltage_pu
        )
        d_efd = (avr_target - self.state.efd_pu) / self.avr_time_constant
        self.state.efd_pu = min(self.efd_max_pu, max(self.efd_min_pu, self.state.efd_pu + d_efd * time_step))

        speed_error = self.state.speed_pu - 1.0
        governor_target = self.mechanical_power_reference_pu - speed_error / self.governor_droop
        d_pm = (governor_target - self.state.mechanical_power_pu) / self.governor_time_constant
        self.state.mechanical_power_pu = min(
            self.mechanical_power_max_pu,
            max(self.mechanical_power_min_pu, self.state.mechanical_power_pu + d_pm * time_step),
        )

        d_eq = (
            self.state.efd_pu
            - self.state.eq_prime_pu
            - (self.d_axis_reactance_pu - self.d_axis_transient_reactance_pu) * self.state.id_pu
        ) / self.d_axis_open_circuit_time_constant
        d_ed = (
            -self.state.ed_prime_pu
            + (self.q_axis_reactance_pu - self.q_axis_transient_reactance_pu) * self.state.iq_pu
        ) / self.q_axis_open_circuit_time_constant
        self.state.eq_prime_pu += d_eq * time_step
        self.state.ed_prime_pu += d_ed * time_step

        electrical_pu = electrical_power / self.base_power
        acceleration = (
            self.state.mechanical_power_pu
            - electrical_pu
            - self.damping * (self.state.speed_pu - 1.0)
        ) / (2.0 * self.inertia_constant)
        self.state.speed_pu += acceleration * time_step
        self.state.rotor_angle += 2.0 * math.pi * self.frequency * (self.state.speed_pu - 1.0) * time_step

    def _validate_parameters(self) -> None:
        """检查 Park 发电机模型参数。"""

        if self.base_power <= 0.0:
            raise ValueError(f"Park 发电机 {self.name} 的基准容量必须大于 0。")
        if self.base_phase_rms <= 0.0:
            raise ValueError(f"Park 发电机 {self.name} 的基准相电压 RMS 必须大于 0。")
        if self.stator_resistance_pu < 0.0:
            raise ValueError(f"Park 发电机 {self.name} 的定子电阻标幺值不能小于 0。")
        if self.d_axis_transient_reactance_pu < 0.0:
            raise ValueError(f"Park 发电机 {self.name} 的 d 轴暂态电抗不能小于 0。")
        if self.stator_resistance_pu == 0.0 and self.d_axis_transient_reactance_pu == 0.0:
            raise ValueError(f"Park 发电机 {self.name} 的定子电阻和暂态电抗不能同时为 0。")
        if self.d_axis_reactance_pu < self.d_axis_transient_reactance_pu:
            raise ValueError(f"Park 发电机 {self.name} 的 Xd 不能小于 Xd'。")
        if self.q_axis_reactance_pu < self.q_axis_transient_reactance_pu:
            raise ValueError(f"Park 发电机 {self.name} 的 Xq 不能小于 Xq'。")
        if self.d_axis_open_circuit_time_constant <= 0.0:
            raise ValueError(f"Park 发电机 {self.name} 的 d 轴开路时间常数必须大于 0。")
        if self.q_axis_open_circuit_time_constant <= 0.0:
            raise ValueError(f"Park 发电机 {self.name} 的 q 轴开路时间常数必须大于 0。")
        if self.inertia_constant <= 0.0:
            raise ValueError(f"Park 发电机 {self.name} 的惯性常数必须大于 0。")
        if self.avr_time_constant <= 0.0:
            raise ValueError(f"Park 发电机 {self.name} 的 AVR 时间常数必须大于 0。")
        if self.governor_time_constant <= 0.0:
            raise ValueError(f"Park 发电机 {self.name} 的调速器时间常数必须大于 0。")
        if self.governor_droop <= 0.0:
            raise ValueError(f"Park 发电机 {self.name} 的调速器下垂系数必须大于 0。")
        if self.frequency <= 0.0:
            raise ValueError(f"Park 发电机 {self.name} 的频率必须大于 0。")
        if self.initial_speed_pu <= 0.0:
            raise ValueError(f"Park 发电机 {self.name} 的初始转速标幺值必须大于 0。")
