"""
文件名称：lines.py
文件作用：实现高级 EMT 阶段的线路教学模型。

主要内容：
1. 单相 π 型集中参数线路
2. 三相 π 型集中参数线路
3. 单相 Bergeron 分布参数线路教学版
4. 三相 Bergeron 分布参数线路教学版
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

import numpy as np

from pycy_emt_lite.components.base import Component
from pycy_emt_lite.components.three_phase import PHASES, PhaseName, phase_node
from pycy_emt_lite.core.context import StampContext
from pycy_emt_lite.core.nodes import NodeManager
from pycy_emt_lite.core.stamping import add_conductance, add_current_source, add_voltage_probe
from pycy_emt_lite.core.variables import VariableManager

@dataclass(slots=True)
class _CapacitorState:
    """电容 companion model 所需的历史状态。"""

    previous_voltage: float = 0.0
    previous_current: float = 0.0
    last_current: float = 0.0

@dataclass(slots=True)
class _SeriesState:
    """串联 R-L 支路的历史状态。"""

    previous_current: float = 0.0
    previous_inductor_voltage: float = 0.0
    last_current: float = 0.0
    last_voltage: float = 0.0

def _validate_pi_parameters(name: str, resistance: float, inductance: float, capacitance: float) -> None:
    """检查 π 型线路参数。"""

    if resistance < 0:
        raise ValueError(f"{name} 的串联电阻不能小于 0。")
    if inductance < 0:
        raise ValueError(f"{name} 的串联电感不能小于 0。")
    if capacitance < 0:
        raise ValueError(f"{name} 的并联电容不能小于 0。")
    if resistance == 0 and inductance == 0:
        raise ValueError(f"{name} 的串联电阻和串联电感不能同时为 0。")

def _series_companion(
    method: str,
    time_step: float,
    inductance: float,
    previous_current: float,
    previous_inductor_voltage: float,
) -> tuple[float, float]:
    """计算串联电感的等效电阻和历史电压。"""

    if method == "trapezoidal":
        resistance = 2.0 * inductance / time_step
        history_voltage = -resistance * previous_current - previous_inductor_voltage
    elif method == "backward_euler":
        resistance = inductance / time_step
        history_voltage = -resistance * previous_current
    else:
        raise ValueError(f"不支持的积分方法：{method}")
    return resistance, history_voltage

def _capacitor_companion(method: str, time_step: float, capacitance: float, state: _CapacitorState) -> tuple[float, float]:
    """计算并联电容的等效电导和历史电流。"""

    if method == "trapezoidal":
        conductance = 2.0 * capacitance / time_step
        history_current = -state.previous_current - conductance * state.previous_voltage
    elif method == "backward_euler":
        conductance = capacitance / time_step
        history_current = -conductance * state.previous_voltage
    else:
        raise ValueError(f"不支持的积分方法：{method}")
    return conductance, history_current

def _stamp_series_rl(
    matrix: np.ndarray,
    rhs: np.ndarray,
    context: StampContext,
    positive: str,
    negative: str,
    branch_index: int | None,
    resistance: float,
    inductance: float,
    state: _SeriesState,
) -> None:
    """写入串联 R-L 支路。"""

    p = context.node_index(positive)
    n = context.node_index(negative)
    if inductance == 0:
        add_conductance(matrix, p, n, 1.0 / resistance)
        return
    if branch_index is None:
        raise RuntimeError("含电感线路支路尚未注册电流变量。")
    branch = context.branch_offset + branch_index
    equivalent_resistance, history_voltage = _series_companion(
        context.method,
        context.time_step,
        inductance,
        state.previous_current,
        state.previous_inductor_voltage,
    )
    if p is not None:
        matrix[p, branch] += 1.0
        matrix[branch, p] += 1.0
    if n is not None:
        matrix[n, branch] -= 1.0
        matrix[branch, n] -= 1.0
    matrix[branch, branch] -= resistance + equivalent_resistance
    rhs[branch] += history_voltage

def _stamp_shunt_capacitor(
    matrix: np.ndarray,
    rhs: np.ndarray,
    context: StampContext,
    node: str,
    ground: str,
    capacitance: float,
    state: _CapacitorState,
) -> None:
    """写入并联电容 companion model。"""

    if capacitance == 0:
        return
    conductance, history_current = _capacitor_companion(context.method, context.time_step, capacitance, state)
    add_conductance(matrix, context.node_index(node), context.node_index(ground), conductance)
    add_current_source(rhs, context.node_index(node), context.node_index(ground), history_current)

def _update_series_state(
    context: StampContext,
    solution: np.ndarray,
    positive: str,
    negative: str,
    branch_index: int | None,
    resistance: float,
    inductance: float,
    state: _SeriesState,
) -> None:
    """更新串联支路历史状态。"""

    voltage = add_voltage_probe(solution, context.node_index(positive), context.node_index(negative))
    if inductance > 0:
        if branch_index is None:
            return
        current = float(solution[context.branch_offset + branch_index])
        state.previous_current = current
        state.previous_inductor_voltage = voltage - resistance * current
        state.last_current = current
    else:
        state.last_current = voltage / resistance
    state.last_voltage = voltage

def _update_shunt_capacitor_state(
    context: StampContext,
    solution: np.ndarray,
    node: str,
    ground: str,
    capacitance: float,
    state: _CapacitorState,
) -> None:
    """更新并联电容历史状态。"""

    if capacitance == 0:
        state.last_current = 0.0
        return
    voltage = add_voltage_probe(solution, context.node_index(node), context.node_index(ground))
    conductance, history_current = _capacitor_companion(context.method, context.time_step, capacitance, state)
    current = conductance * voltage + history_current
    state.previous_voltage = voltage
    state.previous_current = current
    state.last_current = current

@dataclass(slots=True)
class PiLine(Component):
    """单相 π 型集中参数线路。

    线路由一条串联 `R-L` 支路和两端各 `C/2` 的并联电容组成。该模型适合中短线路
    的教学和集中参数暂态示例，不代表完整频率相关线路模型。
    """

    name: str
    sending: str
    receiving: str
    resistance: float
    inductance: float
    capacitance: float
    ground: str = "0"
    branch_index: int | None = field(default=None, init=False)
    series_state: _SeriesState = field(default_factory=_SeriesState, init=False)
    sending_cap_state: _CapacitorState = field(default_factory=_CapacitorState, init=False)
    receiving_cap_state: _CapacitorState = field(default_factory=_CapacitorState, init=False)

    def __post_init__(self) -> None:
        _validate_pi_parameters(f"π 型线路 {self.name}", self.resistance, self.inductance, self.capacitance)

    def nodes(self) -> Iterable[str]:
        return (self.sending, self.receiving, self.ground)

    def register(self, node_manager: NodeManager, variable_manager: VariableManager) -> None:
        """含串联电感时注册线路串联支路电流。"""

        if self.inductance > 0:
            self.branch_index = variable_manager.add_branch_current(self.name)

    def stamp(self, context: StampContext, matrix: np.ndarray, rhs: np.ndarray) -> None:
        """写入 π 型线路 stamp。"""

        _stamp_series_rl(
            matrix,
            rhs,
            context,
            self.sending,
            self.receiving,
            self.branch_index,
            self.resistance,
            self.inductance,
            self.series_state,
        )
        half_capacitance = 0.5 * self.capacitance
        _stamp_shunt_capacitor(matrix, rhs, context, self.sending, self.ground, half_capacitance, self.sending_cap_state)
        _stamp_shunt_capacitor(
            matrix,
            rhs,
            context,
            self.receiving,
            self.ground,
            half_capacitance,
            self.receiving_cap_state,
        )

    def update_state(self, context: StampContext, solution: np.ndarray) -> None:
        """更新串联支路和两端并联电容状态。"""

        _update_series_state(
            context,
            solution,
            self.sending,
            self.receiving,
            self.branch_index,
            self.resistance,
            self.inductance,
            self.series_state,
        )
        half_capacitance = 0.5 * self.capacitance
        _update_shunt_capacitor_state(context, solution, self.sending, self.ground, half_capacitance, self.sending_cap_state)
        _update_shunt_capacitor_state(
            context,
            solution,
            self.receiving,
            self.ground,
            half_capacitance,
            self.receiving_cap_state,
        )

    def outputs(self, context: StampContext, solution: np.ndarray) -> dict[str, float]:
        """记录线路串联电流、两端电压和并联电容电流。"""

        return {
            f"i:{self.name}:series": self.series_state.last_current,
            f"v:{self.name}:series": self.series_state.last_voltage,
            f"i:{self.name}:send_cap": self.sending_cap_state.last_current,
            f"i:{self.name}:recv_cap": self.receiving_cap_state.last_current,
        }

@dataclass(slots=True)
class ThreePhasePiLine(Component):
    """三相 π 型集中参数线路。

    每相都是一条独立的 `PiLine` 等效支路，暂不考虑相间互感和零序耦合。
    """

    name: str
    from_bus: str
    to_bus: str
    resistance: float
    inductance: float
    capacitance: float
    ground: str = "0"
    branch_indices: dict[PhaseName, int] = field(default_factory=dict, init=False)
    series_states: dict[PhaseName, _SeriesState] = field(default_factory=lambda: {phase: _SeriesState() for phase in PHASES}, init=False)
    from_cap_states: dict[PhaseName, _CapacitorState] = field(default_factory=lambda: {phase: _CapacitorState() for phase in PHASES}, init=False)
    to_cap_states: dict[PhaseName, _CapacitorState] = field(default_factory=lambda: {phase: _CapacitorState() for phase in PHASES}, init=False)

    def __post_init__(self) -> None:
        _validate_pi_parameters(f"三相 π 型线路 {self.name}", self.resistance, self.inductance, self.capacitance)

    def nodes(self) -> Iterable[str]:
        nodes = [self.ground]
        for phase in PHASES:
            nodes.append(phase_node(self.from_bus, phase))
            nodes.append(phase_node(self.to_bus, phase))
        return nodes

    def register(self, node_manager: NodeManager, variable_manager: VariableManager) -> None:
        """含串联电感时为每相注册支路电流。"""

        if self.inductance > 0:
            self.branch_indices = {phase: variable_manager.add_branch_current(f"{self.name}:{phase}") for phase in PHASES}

    def stamp(self, context: StampContext, matrix: np.ndarray, rhs: np.ndarray) -> None:
        """写入三相 π 型线路 stamp。"""

        half_capacitance = 0.5 * self.capacitance
        for phase in PHASES:
            from_node = phase_node(self.from_bus, phase)
            to_node = phase_node(self.to_bus, phase)
            branch_index = self.branch_indices.get(phase)
            _stamp_series_rl(
                matrix,
                rhs,
                context,
                from_node,
                to_node,
                branch_index,
                self.resistance,
                self.inductance,
                self.series_states[phase],
            )
            _stamp_shunt_capacitor(matrix, rhs, context, from_node, self.ground, half_capacitance, self.from_cap_states[phase])
            _stamp_shunt_capacitor(matrix, rhs, context, to_node, self.ground, half_capacitance, self.to_cap_states[phase])

    def update_state(self, context: StampContext, solution: np.ndarray) -> None:
        """更新三相 π 型线路状态。"""

        half_capacitance = 0.5 * self.capacitance
        for phase in PHASES:
            from_node = phase_node(self.from_bus, phase)
            to_node = phase_node(self.to_bus, phase)
            _update_series_state(
                context,
                solution,
                from_node,
                to_node,
                self.branch_indices.get(phase),
                self.resistance,
                self.inductance,
                self.series_states[phase],
            )
            _update_shunt_capacitor_state(context, solution, from_node, self.ground, half_capacitance, self.from_cap_states[phase])
            _update_shunt_capacitor_state(context, solution, to_node, self.ground, half_capacitance, self.to_cap_states[phase])

    def outputs(self, context: StampContext, solution: np.ndarray) -> dict[str, float]:
        """记录三相线路每相串联电流和并联电容电流。"""

        outputs: dict[str, float] = {}
        for phase in PHASES:
            outputs[f"i:{self.name}:series:{phase}"] = self.series_states[phase].last_current
            outputs[f"v:{self.name}:series:{phase}"] = self.series_states[phase].last_voltage
            outputs[f"i:{self.name}:from_cap:{phase}"] = self.from_cap_states[phase].last_current
            outputs[f"i:{self.name}:to_cap:{phase}"] = self.to_cap_states[phase].last_current
        return outputs

@dataclass(slots=True)
class SegmentedLine(Component):
    """单相分段线路模型。

    该模型把一条线路拆成多个等长 π 型集中参数小段。总电阻、电感、电容按段数
    均分，段间自动生成内部节点。它适合教学中演示“集中参数逐步逼近分布参数”
    的思想，不包含频率相关参数和相间耦合。
    """

    name: str
    sending: str
    receiving: str
    resistance: float
    inductance: float
    capacitance: float
    sections: int
    ground: str = "0"
    branch_indices: list[int] = field(default_factory=list, init=False)
    series_states: list[_SeriesState] = field(default_factory=list, init=False)
    sending_cap_states: list[_CapacitorState] = field(default_factory=list, init=False)
    receiving_cap_states: list[_CapacitorState] = field(default_factory=list, init=False)

    def __post_init__(self) -> None:
        if self.sections <= 0:
            raise ValueError(f"分段线路 {self.name} 的段数必须大于 0。")
        _validate_pi_parameters(f"分段线路 {self.name}", self.resistance, self.inductance, self.capacitance)
        self.series_states = [_SeriesState() for _ in range(self.sections)]
        self.sending_cap_states = [_CapacitorState() for _ in range(self.sections)]
        self.receiving_cap_states = [_CapacitorState() for _ in range(self.sections)]

    def nodes(self) -> Iterable[str]:
        nodes = [self.sending, self.receiving, self.ground]
        nodes.extend(self._internal_node(index) for index in range(1, self.sections))
        return nodes

    def register(self, node_manager: NodeManager, variable_manager: VariableManager) -> None:
        """含串联电感时为每个线路小段注册支路电流。"""

        if self.inductance > 0:
            self.branch_indices = [variable_manager.add_branch_current(f"{self.name}:section:{index}") for index in range(self.sections)]

    def stamp(self, context: StampContext, matrix: np.ndarray, rhs: np.ndarray) -> None:
        """逐段写入 π 型线路 stamp。"""

        resistance = self.resistance / self.sections
        inductance = self.inductance / self.sections
        capacitance = self.capacitance / self.sections
        half_capacitance = 0.5 * capacitance
        for index in range(self.sections):
            positive, negative = self._section_nodes(index)
            branch_index = self.branch_indices[index] if self.branch_indices else None
            _stamp_series_rl(
                matrix,
                rhs,
                context,
                positive,
                negative,
                branch_index,
                resistance,
                inductance,
                self.series_states[index],
            )
            _stamp_shunt_capacitor(matrix, rhs, context, positive, self.ground, half_capacitance, self.sending_cap_states[index])
            _stamp_shunt_capacitor(matrix, rhs, context, negative, self.ground, half_capacitance, self.receiving_cap_states[index])

    def update_state(self, context: StampContext, solution: np.ndarray) -> None:
        """更新各分段串联支路和并联电容状态。"""

        resistance = self.resistance / self.sections
        inductance = self.inductance / self.sections
        capacitance = self.capacitance / self.sections
        half_capacitance = 0.5 * capacitance
        for index in range(self.sections):
            positive, negative = self._section_nodes(index)
            branch_index = self.branch_indices[index] if self.branch_indices else None
            _update_series_state(
                context,
                solution,
                positive,
                negative,
                branch_index,
                resistance,
                inductance,
                self.series_states[index],
            )
            _update_shunt_capacitor_state(context, solution, positive, self.ground, half_capacitance, self.sending_cap_states[index])
            _update_shunt_capacitor_state(context, solution, negative, self.ground, half_capacitance, self.receiving_cap_states[index])

    def outputs(self, context: StampContext, solution: np.ndarray) -> dict[str, float]:
        """记录首段、末段和平均线路电流。"""

        currents = [state.last_current for state in self.series_states]
        return {
            f"i:{self.name}:sending": currents[0],
            f"i:{self.name}:receiving": currents[-1],
            f"i:{self.name}:average": float(np.mean(currents)),
        }

    def _section_nodes(self, index: int) -> tuple[str, str]:
        """返回指定分段的首末节点。"""

        positive = self.sending if index == 0 else self._internal_node(index)
        negative = self.receiving if index == self.sections - 1 else self._internal_node(index + 1)
        return positive, negative

    def _internal_node(self, index: int) -> str:
        """生成分段线路内部节点名。"""

        return f"{self.name}:internal:{index}"

@dataclass(slots=True)
class _BergeronHistorySample:
    """Bergeron 线路端口历史样本。"""

    time: float
    sending_voltage: float
    sending_current: float
    receiving_voltage: float
    receiving_current: float

@dataclass(slots=True)
class BergeronLine(Component):
    """单相 Bergeron 分布参数线路教学版。

    该模型使用特性阻抗 `surge_impedance` 和传播时延 `travel_time` 表示无损线路的
    行波关系，并用历史源把对端延时电压、电流反映到本端。`attenuation` 可用于
    教学中演示传播衰减，默认 1 表示无衰减。
    """

    name: str
    sending: str
    receiving: str
    surge_impedance: float
    travel_time: float
    ground: str = "0"
    attenuation: float = 1.0
    history: list[_BergeronHistorySample] = field(default_factory=list, init=False)
    last_sending_current: float = 0.0
    last_receiving_current: float = 0.0

    def __post_init__(self) -> None:
        if self.surge_impedance <= 0:
            raise ValueError(f"Bergeron 线路 {self.name} 的特性阻抗必须大于 0。")
        if self.travel_time <= 0:
            raise ValueError(f"Bergeron 线路 {self.name} 的传播时延必须大于 0。")
        if not 0 < self.attenuation <= 1:
            raise ValueError(f"Bergeron 线路 {self.name} 的衰减系数必须位于 (0, 1]。")

    def nodes(self) -> Iterable[str]:
        return (self.sending, self.receiving, self.ground)

    def stamp(self, context: StampContext, matrix: np.ndarray, rhs: np.ndarray) -> None:
        """写入 Bergeron 线路等效 Norton stamp。"""

        conductance = 1.0 / self.surge_impedance
        sending = context.node_index(self.sending)
        receiving = context.node_index(self.receiving)
        ground = context.node_index(self.ground)
        delayed = self._delayed_sample(context.time - self.travel_time)
        sending_history = self.attenuation * (-delayed.receiving_voltage / self.surge_impedance - delayed.receiving_current)
        receiving_history = self.attenuation * (-delayed.sending_voltage / self.surge_impedance - delayed.sending_current)

        add_conductance(matrix, sending, ground, conductance)
        add_conductance(matrix, receiving, ground, conductance)
        add_current_source(rhs, sending, ground, sending_history)
        add_current_source(rhs, receiving, ground, receiving_history)

    def update_state(self, context: StampContext, solution: np.ndarray) -> None:
        """更新线路两端历史电压和注入线路的端口电流。"""

        sending_voltage = add_voltage_probe(solution, context.node_index(self.sending), context.node_index(self.ground))
        receiving_voltage = add_voltage_probe(solution, context.node_index(self.receiving), context.node_index(self.ground))
        delayed = self._delayed_sample(context.time - self.travel_time)
        sending_history = self.attenuation * (-delayed.receiving_voltage / self.surge_impedance - delayed.receiving_current)
        receiving_history = self.attenuation * (-delayed.sending_voltage / self.surge_impedance - delayed.sending_current)
        self.last_sending_current = sending_voltage / self.surge_impedance + sending_history
        self.last_receiving_current = receiving_voltage / self.surge_impedance + receiving_history
        self.history.append(
            _BergeronHistorySample(
                time=context.time,
                sending_voltage=sending_voltage,
                sending_current=self.last_sending_current,
                receiving_voltage=receiving_voltage,
                receiving_current=self.last_receiving_current,
            )
        )

    def outputs(self, context: StampContext, solution: np.ndarray) -> dict[str, float]:
        """记录线路两端电流。"""

        return {
            f"i:{self.name}:sending": self.last_sending_current,
            f"i:{self.name}:receiving": self.last_receiving_current,
        }

    def _delayed_sample(self, target_time: float) -> _BergeronHistorySample:
        """按时间线性插值读取延时历史样本。"""

        if not self.history:
            return _BergeronHistorySample(target_time, 0.0, 0.0, 0.0, 0.0)
        if target_time < self.history[0].time:
            return _BergeronHistorySample(target_time, 0.0, 0.0, 0.0, 0.0)
        if target_time <= self.history[0].time:
            return self.history[0]
        if target_time >= self.history[-1].time:
            return self.history[-1]
        for lower, upper in zip(self.history, self.history[1:], strict=False):
            if lower.time <= target_time <= upper.time:
                weight = (target_time - lower.time) / (upper.time - lower.time)
                return _BergeronHistorySample(
                    time=target_time,
                    sending_voltage=lower.sending_voltage + weight * (upper.sending_voltage - lower.sending_voltage),
                    sending_current=lower.sending_current + weight * (upper.sending_current - lower.sending_current),
                    receiving_voltage=lower.receiving_voltage + weight * (upper.receiving_voltage - lower.receiving_voltage),
                    receiving_current=lower.receiving_current + weight * (upper.receiving_current - lower.receiving_current),
                )
        return self.history[-1]

@dataclass(slots=True)
class ThreePhaseBergeronLine(Component):
    """三相 Bergeron 分布参数线路教学版。

    每相独立使用单相 Bergeron 行波关系，暂不考虑相间耦合和模量变换。
    """

    name: str
    from_bus: str
    to_bus: str
    surge_impedance: float
    travel_time: float
    ground: str = "0"
    attenuation: float = 1.0
    lines: dict[PhaseName, BergeronLine] = field(init=False)

    def __post_init__(self) -> None:
        self.lines = {
            phase: BergeronLine(
                f"{self.name}:{phase}",
                phase_node(self.from_bus, phase),
                phase_node(self.to_bus, phase),
                self.surge_impedance,
                self.travel_time,
                self.ground,
                self.attenuation,
            )
            for phase in PHASES
        }

    def nodes(self) -> Iterable[str]:
        nodes = [self.ground]
        for line in self.lines.values():
            nodes.extend(line.nodes())
        return nodes

    def stamp(self, context: StampContext, matrix: np.ndarray, rhs: np.ndarray) -> None:
        """写入三相 Bergeron 线路 stamp。"""

        for line in self.lines.values():
            line.stamp(context, matrix, rhs)

    def update_state(self, context: StampContext, solution: np.ndarray) -> None:
        """更新三相 Bergeron 线路历史。"""

        for line in self.lines.values():
            line.update_state(context, solution)

    def outputs(self, context: StampContext, solution: np.ndarray) -> dict[str, float]:
        """记录三相 Bergeron 线路端口电流。"""

        outputs: dict[str, float] = {}
        for phase, line in self.lines.items():
            outputs[f"i:{self.name}:sending:{phase}"] = line.last_sending_current
            outputs[f"i:{self.name}:receiving:{phase}"] = line.last_receiving_current
        return outputs
