"""
文件名称：park_generator.py
文件作用：实现带 AVR 和调速器的四阶 Park dq 同步发电机教学模型。

主要内容：
1. 使用四阶 Park dq 暂态电势方程更新 d/q 轴内部电势
2. 使用一阶 AVR 和一阶调速器更新励磁电压与机械功率
3. 将两轴暂态电抗写入代数端口，经 abc 变换接入同一 MNA 网络
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
from pycy_emt_lite.core.stamping import add_voltage_probe
from pycy_emt_lite.core.variables import VariableManager
from pycy_emt_lite.machines.synchronous import _finite_parameter

@dataclass(slots=True)
class _ParkGeneratorState:
    """Park 发电机动态状态和最近一次输出。"""

    rotor_angle: float
    speed_pu: float
    eq_prime_pu: float
    ed_prime_pu: float
    efd_pu: float
    mechanical_power_pu: float
    last_current: dict[PhaseName, float] = field(default_factory=lambda: {phase: 0.0 for phase in PHASES})
    last_terminal_voltage: dict[PhaseName, float] = field(default_factory=lambda: {phase: 0.0 for phase in PHASES})
    last_internal_voltage: dict[PhaseName, float] = field(default_factory=lambda: {phase: 0.0 for phase in PHASES})
    id_pu: float = 0.0
    iq_pu: float = 0.0
    vd_pu: float = 0.0
    vq_pu: float = 0.0
    terminal_voltage_pu: float = 0.0
    electrical_power: float = 0.0
    electromagnetic_power: float = 0.0
    copper_loss: float = 0.0
    time: float = 0.0

@dataclass(slots=True)
class ParkSynchronousGenerator(Component):
    """带 AVR 和调速器的四阶 Park dq 同步发电机教学模型。

    电气部分采用暂态电势形式：

    ```text
    dE'_q/dt = (E_fd - E'_q - (X_d - X'_d) I_d) / T'_do
    dE'_d/dt = (-E'_d + (X_q - X'_q) I_q) / T'_qo
    ```

    转子角、转速、两轴暂态电势加一阶 AVR/调速器共六个动态状态，均使用
    左端反馈显式欧拉。忽略定子快速暂态，d=-cos(theta)、q=sin(theta)，
    适用于平衡、近工频负荷与机电调节教学，不用于短路直流偏置、不平衡故障、
    次暂态或饱和分析。零序端口仅剩定子电阻，不代表完整 dq0 电机。
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

    def nodes(self) -> Iterable[str]:
        nodes: list[str] = [self.neutral]
        for phase in PHASES:
            nodes.append(phase_node(self.terminal_bus, phase))
            nodes.append(phase_node(self.internal_bus_name, phase))
        return nodes

    def register(self, node_manager: NodeManager, variable_manager: VariableManager) -> None:
        """为三相内部电势源和代数定子支路注册变量。"""

        self.source_branch_indices = {
            phase: variable_manager.add_branch_current(f"{self.name}:source:{phase}") for phase in PHASES
        }
        self.stator_branch_indices = {
            phase: variable_manager.add_branch_current(f"{self.name}:stator:{phase}") for phase in PHASES
        }

    def stamp(self, context: StampContext, matrix: np.ndarray, rhs: np.ndarray) -> None:
        """先用左端反馈推进机电状态，再写入本时刻的代数 dq 端口。"""
        if context.time_step > 0 and context.time > self.state.time:
            self._update_controls_and_machine(context.time_step)
            self.state.time = context.time
        angle = self._electrical_angle(context.time)
        # 发电机约定：d=-cos(theta)，q=sin(theta)；两者均为幅值不变轴。
        basis = np.array([dq_to_abc(-1.0, 0.0, angle), dq_to_abc(0.0, -1.0, angle)]).T
        e_abc = math.sqrt(2.0) * self.base_phase_rms * (basis @ np.array([
            self.state.ed_prime_pu, self.state.eq_prime_pu]))
        reactance = np.array([[0.0, -self.q_axis_transient_reactance_pu],
                              [self.d_axis_transient_reactance_pu, 0.0]])
        # E_d - V_d = Rs*Id - Xq'*Iq; E_q - V_q = Xd'*Id + Rs*Iq.
        impedance = self.stator_resistance * np.eye(3) + self.base_impedance * basis @ reactance @ (2.0 / 3.0 * basis.T)
        branches = [context.branch_offset + self.stator_branch_indices[p] for p in PHASES]
        neutral = context.node_index(self.neutral)
        for index, phase in enumerate(PHASES):
            internal = context.node_index(phase_node(self.internal_bus_name, phase))
            terminal = context.node_index(phase_node(self.terminal_bus, phase))
            source = context.branch_offset + self.source_branch_indices[phase]
            branch = branches[index]
            self.state.last_internal_voltage[phase] = float(e_abc[index])
            if internal is not None:
                matrix[internal, source] += 1.0
                matrix[source, internal] += 1.0
                matrix[internal, branch] += 1.0
                matrix[branch, internal] += 1.0
            if neutral is not None:
                matrix[neutral, source] -= 1.0
                matrix[source, neutral] -= 1.0
            if terminal is not None:
                matrix[terminal, branch] -= 1.0
                matrix[branch, terminal] -= 1.0
            rhs[source] += e_abc[index]
            matrix[branch, branches] -= impedance[index]
            if context._initial is not None:
                # 耦合场电势导数尚不支持理想约束消元；普通端口无需它。
                context._initial.source_derivatives.append(({source: 1.0}, self._source_derivative))

    def _source_derivative(self) -> float:
        raise ValueError(f"Park 发电机 {self.name} 尚不支持受理想约束的内部电势导数；"
                         "请解除内部电势节点的理想约束，并通过带有限阻抗的机端连接外部电路。")

    def update_state(self, context: StampContext, solution: np.ndarray) -> None:
        """记录代数端口及功率；t=0/事件右侧不推进控制或转子状态。"""
        voltage = []
        current = []
        neutral = context.node_index(self.neutral)
        for phase in PHASES:
            v = add_voltage_probe(solution, context.node_index(phase_node(self.terminal_bus, phase)), neutral)
            i = float(solution[context.branch_offset + self.stator_branch_indices[phase]])
            self.state.last_terminal_voltage[phase] = v
            self.state.last_current[phase] = i
            voltage.append(v)
            current.append(i)
        angle = self._electrical_angle(context.time)
        vd, vq = abc_to_dq(*voltage, angle)
        id_, iq = abc_to_dq(*current, angle)
        voltage_base = math.sqrt(2.0) * self.base_phase_rms
        current_base = math.sqrt(2.0) * self.base_power / (3.0 * self.base_phase_rms)
        self.state.vd_pu, self.state.vq_pu = -vd / voltage_base, -vq / voltage_base
        self.state.id_pu, self.state.iq_pu = -id_ / current_base, -iq / current_base
        self.state.terminal_voltage_pu = math.hypot(vd, vq) / voltage_base
        self.state.electrical_power = sum(v * i for v, i in zip(voltage, current))
        self.state.copper_loss = self.stator_resistance * sum(i * i for i in current)
        # 定子快速储能已忽略；气隙功率包含铜损和凸极磁阻转矩项。
        self.state.electromagnetic_power = self.state.electrical_power + self.state.copper_loss

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
        outputs[f"p_em:{self.name}"] = self.state.electromagnetic_power
        outputs[f"p_copper:{self.name}"] = self.state.copper_loss
        outputs[f"rotor_angle:{self.name}"] = self.state.rotor_angle
        outputs[f"speed_pu:{self.name}"] = self.state.speed_pu
        return outputs

    def _electrical_angle(self, time: float) -> float:
        """返回当前同步参考角和转子相对角之和。"""

        return 2.0 * math.pi * self.frequency * time + self.state.rotor_angle

    def _update_controls_and_machine(self, time_step: float) -> None:
        """六个状态均用同一左端值显式欧拉推进；随后对励磁和功率限幅。"""
        state = self.state
        speed_error = state.speed_pu - 1.0
        avr_target = self.initial_efd_pu + self.avr_gain * (self.voltage_reference_pu - state.terminal_voltage_pu)
        governor_target = self.mechanical_power_reference_pu - speed_error / self.governor_droop
        d_eq = (state.efd_pu - state.eq_prime_pu
                - (self.d_axis_reactance_pu - self.d_axis_transient_reactance_pu) * state.id_pu) / self.d_axis_open_circuit_time_constant
        d_ed = (-state.ed_prime_pu
                + (self.q_axis_reactance_pu - self.q_axis_transient_reactance_pu) * state.iq_pu) / self.q_axis_open_circuit_time_constant
        acceleration = (state.mechanical_power_pu - state.electromagnetic_power / self.base_power
                        - self.damping * speed_error) / (2.0 * self.inertia_constant * state.speed_pu)
        state.rotor_angle += 2.0 * math.pi * self.frequency * speed_error * time_step
        state.speed_pu += acceleration * time_step
        state.eq_prime_pu += d_eq * time_step
        state.ed_prime_pu += d_ed * time_step
        efd = state.efd_pu + (avr_target - state.efd_pu) / self.avr_time_constant * time_step
        pm = state.mechanical_power_pu + (governor_target - state.mechanical_power_pu) / self.governor_time_constant * time_step
        if not all(math.isfinite(value) for value in (
            state.rotor_angle, state.speed_pu, state.eq_prime_pu, state.ed_prime_pu, efd, pm
        )) or state.speed_pu <= 0:
            raise ValueError(f"Park 发电机 {self.name} 的状态失效；请减小 time_step 并检查功率、惯性、控制时间常数和初值。")
        state.efd_pu = min(self.efd_max_pu, max(self.efd_min_pu, efd))
        state.mechanical_power_pu = min(self.mechanical_power_max_pu, max(self.mechanical_power_min_pu, pm))

    def _validate_parameters(self) -> None:
        """检查有限数、物理范围和控制限幅；报错指出修复方法。"""
        positive = ("base_power", "base_phase_rms", "d_axis_open_circuit_time_constant",
                    "q_axis_open_circuit_time_constant", "inertia_constant", "voltage_reference_pu",
                    "avr_time_constant", "governor_droop", "governor_time_constant", "frequency", "initial_speed_pu")
        nonnegative = ("stator_resistance_pu", "d_axis_reactance_pu", "q_axis_reactance_pu",
                       "d_axis_transient_reactance_pu", "q_axis_transient_reactance_pu", "damping", "avr_gain")
        other = ("initial_rotor_angle", "initial_eq_prime_pu", "initial_ed_prime_pu", "initial_efd_pu",
                 "initial_mechanical_power_pu", "mechanical_power_reference_pu", "efd_min_pu", "efd_max_pu",
                 "mechanical_power_min_pu", "mechanical_power_max_pu")
        for parameter in positive + nonnegative + other:
            value = getattr(self, parameter)
            _finite_parameter(self.name, parameter, value)
            if parameter in positive and value <= 0:
                raise ValueError(f"Park 发电机 {self.name} 的 {parameter}={value!r} 非法；请设置大于 0 的值。")
            if parameter in nonnegative and value < 0:
                raise ValueError(f"Park 发电机 {self.name} 的 {parameter}={value!r} 非法；请设置非负值。")
        for axis in ("d", "q"):
            transient = f"{axis}_axis_transient_reactance_pu"
            steady = f"{axis}_axis_reactance_pu"
            if getattr(self, transient) > getattr(self, steady):
                raise ValueError(f"Park 发电机 {self.name} 的 {transient} 不能超过 {steady}；请减小暂态电抗或增大同步电抗。")
        if self.stator_resistance_pu == 0 and (self.d_axis_transient_reactance_pu == 0 or self.q_axis_transient_reactance_pu == 0):
            raise ValueError(f"Park 发电机 {self.name} 的端口阻抗退化；请设置正 stator_resistance_pu，或同时设置正 d/q_axis_transient_reactance_pu。")
        for prefix, initial in (("efd", "initial_efd_pu"), ("mechanical_power", "initial_mechanical_power_pu")):
            lower, upper = f"{prefix}_min_pu", f"{prefix}_max_pu"
            if getattr(self, lower) > getattr(self, upper):
                raise ValueError(f"Park 发电机 {self.name} 的限幅顺序非法；请使 {lower} <= {upper}。")
            if not getattr(self, lower) <= getattr(self, initial) <= getattr(self, upper):
                raise ValueError(f"Park 发电机 {self.name} 的 {initial} 超出限幅；请使初值位于 [{lower}, {upper}] 内。")
