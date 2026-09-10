"""
文件名称：transformers.py
文件作用：实现单相和三相变压器教学模型。

主要内容：
1. 单相变压器：理想变比、漏阻抗、励磁支路
2. 三相 Y/Y、Y/Δ、Δ/Y 变压器
3. 显式滞后的饱和励磁简化模型
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Iterable, Literal

import numpy as np

from pycy_emt_lite.components.base import Component
from pycy_emt_lite.components.three_phase import PHASES, PhaseName, phase_node
from pycy_emt_lite.core.context import StampContext
from pycy_emt_lite.core.nodes import NodeManager
from pycy_emt_lite.core.stamping import add_conductance, add_voltage_probe
from pycy_emt_lite.core.variables import VariableManager

TransformerConnection = Literal["Y", "D"]


@dataclass(slots=True)
class _TransformerPhaseState:
    """变压器单个绕组相的动态状态。"""

    leakage_previous_current: float = 0.0
    leakage_previous_voltage: float = 0.0
    magnetizing_previous_current: float = 0.0
    magnetizing_previous_voltage: float = 0.0
    magnetizing_flux: float = 0.0
    last_primary_current: float = 0.0
    last_secondary_current: float = 0.0
    last_magnetizing_current: float = 0.0
    last_primary_voltage: float = 0.0
    last_secondary_voltage: float = 0.0


def _validate_transformer_parameters(
    name: str,
    turns_ratio: float,
    leakage_resistance: float,
    leakage_inductance: float,
    magnetizing_inductance: float | None,
    core_loss_resistance: float | None,
    saturation_knee_flux: float | None,
    saturated_magnetizing_inductance: float | None,
) -> None:
    """检查变压器参数。"""

    if not math.isfinite(turns_ratio) or turns_ratio <= 0:
        raise ValueError(f"变压器 {name} 的变比必须为有限正数。")
    if not math.isfinite(leakage_resistance) or leakage_resistance < 0:
        raise ValueError(f"变压器 {name} 的漏电阻必须为有限非负数。")
    if not math.isfinite(leakage_inductance) or leakage_inductance < 0:
        raise ValueError(f"变压器 {name} 的漏感必须为有限非负数。")
    if magnetizing_inductance is not None and (
        not math.isfinite(magnetizing_inductance) or magnetizing_inductance <= 0
    ):
        raise ValueError(f"变压器 {name} 的励磁电感必须为有限正数。")
    if core_loss_resistance is not None and (
        not math.isfinite(core_loss_resistance) or core_loss_resistance <= 0
    ):
        raise ValueError(f"变压器 {name} 的铁耗电阻必须为有限正数。")
    has_saturation = saturation_knee_flux is not None or saturated_magnetizing_inductance is not None
    if has_saturation and (saturation_knee_flux is None or saturated_magnetizing_inductance is None):
        raise ValueError(f"变压器 {name} 的饱和参数必须同时给出 knee_flux 和 saturated_magnetizing_inductance。")
    if saturation_knee_flux is not None and (
        not math.isfinite(saturation_knee_flux) or saturation_knee_flux <= 0
    ):
        raise ValueError(f"变压器 {name} 的饱和拐点磁链必须为有限正数。")
    if saturated_magnetizing_inductance is not None and (
        not math.isfinite(saturated_magnetizing_inductance) or saturated_magnetizing_inductance <= 0
    ):
        raise ValueError(f"变压器 {name} 的饱和励磁电感必须为有限正数。")
    if has_saturation and magnetizing_inductance is None:
        raise ValueError(f"变压器 {name} 启用饱和励磁时必须给出线性励磁电感。")


def _inductor_companion(
    method: str,
    time_step: float,
    inductance: float,
    previous_current: float,
    previous_voltage: float,
) -> tuple[float, float]:
    """计算电感 companion model 的等效电阻和历史电压。"""

    if time_step == 0.0:
        return 0.0, 0.0
    if method == "trapezoidal":
        resistance = 2.0 * inductance / time_step
        history_voltage = -resistance * previous_current - previous_voltage
    elif method == "backward_euler":
        resistance = inductance / time_step
        history_voltage = -resistance * previous_current
    else:
        raise ValueError(f"不支持的积分方法：{method}")
    return resistance, history_voltage


def _stamp_branch_current(matrix: np.ndarray, positive: int | None, negative: int | None, branch: int) -> None:
    """把支路电流写入两端节点 KCL。"""

    if positive is not None:
        matrix[positive, branch] += 1.0
    if negative is not None:
        matrix[negative, branch] -= 1.0


def _stamp_voltage_coefficient(matrix: np.ndarray, row: int, positive: int | None, negative: int | None, coefficient: float) -> None:
    """把 `coefficient * (v_positive - v_negative)` 写入约束方程行。"""

    if positive is not None:
        matrix[row, positive] += coefficient
    if negative is not None:
        matrix[row, negative] -= coefficient


def _effective_magnetizing_inductance(
    magnetizing_inductance: float | None,
    saturated_magnetizing_inductance: float | None,
    saturation_knee_flux: float | None,
    state: _TransformerPhaseState,
) -> float | None:
    """根据上一时刻磁链返回本步使用的励磁电感。"""

    if magnetizing_inductance is None:
        return None
    if saturation_knee_flux is None or saturated_magnetizing_inductance is None:
        return magnetizing_inductance
    if abs(state.magnetizing_flux) >= saturation_knee_flux:
        return saturated_magnetizing_inductance
    return magnetizing_inductance


def _stamp_transformer_phase(
    context: StampContext,
    matrix: np.ndarray,
    rhs: np.ndarray,
    primary_positive: str,
    primary_negative: str,
    secondary_positive: str,
    secondary_negative: str,
    primary_branch_index: int,
    secondary_branch_index: int,
    magnetizing_branch_index: int | None,
    turns_ratio: float,
    leakage_resistance: float,
    leakage_inductance: float,
    magnetizing_inductance: float | None,
    core_loss_resistance: float | None,
    saturated_magnetizing_inductance: float | None,
    saturation_knee_flux: float | None,
    state: _TransformerPhaseState,
) -> None:
    """写入单相变压器等效方程。"""

    primary_positive_index = context.node_index(primary_positive)
    primary_negative_index = context.node_index(primary_negative)
    secondary_positive_index = context.node_index(secondary_positive)
    secondary_negative_index = context.node_index(secondary_negative)
    primary_branch = context.branch_offset + primary_branch_index
    secondary_branch = context.branch_offset + secondary_branch_index

    _stamp_branch_current(matrix, primary_positive_index, primary_negative_index, primary_branch)
    _stamp_branch_current(matrix, secondary_positive_index, secondary_negative_index, secondary_branch)

    leakage_equivalent_resistance = 0.0
    leakage_history_voltage = 0.0
    if leakage_inductance > 0:
        if context._initial is not None:
            context._initial.inductors.append((primary_branch, leakage_inductance, state.leakage_previous_current))
        leakage_equivalent_resistance, leakage_history_voltage = _inductor_companion(
            context.method,
            context.time_step,
            leakage_inductance,
            state.leakage_previous_current,
            state.leakage_previous_voltage,
        )
    _stamp_voltage_coefficient(matrix, primary_branch, primary_positive_index, primary_negative_index, 1.0)
    _stamp_voltage_coefficient(matrix, primary_branch, secondary_positive_index, secondary_negative_index, -turns_ratio)
    matrix[primary_branch, primary_branch] -= leakage_resistance + leakage_equivalent_resistance
    rhs[primary_branch] += leakage_history_voltage

    matrix[secondary_branch, primary_branch] += turns_ratio
    matrix[secondary_branch, secondary_branch] += 1.0

    if core_loss_resistance is not None:
        add_conductance(matrix, primary_positive_index, primary_negative_index, 1.0 / core_loss_resistance)

    effective_magnetizing_inductance = _effective_magnetizing_inductance(
        magnetizing_inductance,
        saturated_magnetizing_inductance,
        saturation_knee_flux,
        state,
    )
    if effective_magnetizing_inductance is not None:
        if magnetizing_branch_index is None:
            raise RuntimeError("励磁支路尚未注册支路电流变量。")
        magnetizing_branch = context.branch_offset + magnetizing_branch_index
        if context._initial is not None:
            context._initial.inductors.append((
                magnetizing_branch, effective_magnetizing_inductance, state.magnetizing_previous_current
            ))
        _stamp_branch_current(matrix, primary_positive_index, primary_negative_index, magnetizing_branch)
        equivalent_resistance, history_voltage = _inductor_companion(
            context.method,
            context.time_step,
            effective_magnetizing_inductance,
            state.magnetizing_previous_current,
            state.magnetizing_previous_voltage,
        )
        _stamp_voltage_coefficient(matrix, magnetizing_branch, primary_positive_index, primary_negative_index, 1.0)
        matrix[magnetizing_branch, magnetizing_branch] -= equivalent_resistance
        rhs[magnetizing_branch] += history_voltage


def _update_transformer_phase(
    context: StampContext,
    solution: np.ndarray,
    primary_positive: str,
    primary_negative: str,
    secondary_positive: str,
    secondary_negative: str,
    primary_branch_index: int,
    secondary_branch_index: int,
    magnetizing_branch_index: int | None,
    turns_ratio: float,
    leakage_resistance: float,
    state: _TransformerPhaseState,
) -> None:
    """更新单相变压器状态。"""

    primary_voltage = add_voltage_probe(solution, context.node_index(primary_positive), context.node_index(primary_negative))
    secondary_voltage = add_voltage_probe(solution, context.node_index(secondary_positive), context.node_index(secondary_negative))
    primary_current = float(solution[context.branch_offset + primary_branch_index])
    secondary_current = float(solution[context.branch_offset + secondary_branch_index])
    state.leakage_previous_current = primary_current
    state.leakage_previous_voltage = primary_voltage - turns_ratio * secondary_voltage - leakage_resistance * primary_current
    state.last_primary_current = primary_current
    state.last_secondary_current = secondary_current
    state.last_primary_voltage = primary_voltage
    state.last_secondary_voltage = secondary_voltage

    if magnetizing_branch_index is not None:
        magnetizing_current = float(solution[context.branch_offset + magnetizing_branch_index])
        state.magnetizing_previous_current = magnetizing_current
        state.magnetizing_previous_voltage = primary_voltage
        state.magnetizing_flux += primary_voltage * context.time_step
        state.last_magnetizing_current = magnetizing_current


@dataclass(slots=True)
class SinglePhaseTransformer(Component):
    """单相变压器教学模型。

    `turns_ratio` 定义为一次绕组电压与二次绕组电压之比，即 `Vp / Vs`。
    漏阻抗折算在一次侧；励磁支路并联在一次侧。
    """

    name: str
    primary_positive: str
    primary_negative: str
    secondary_positive: str
    secondary_negative: str
    turns_ratio: float
    leakage_resistance: float = 0.0
    leakage_inductance: float = 0.0
    magnetizing_inductance: float | None = None
    core_loss_resistance: float | None = None
    saturation_knee_flux: float | None = None
    saturated_magnetizing_inductance: float | None = None
    primary_branch_index: int | None = field(default=None, init=False)
    secondary_branch_index: int | None = field(default=None, init=False)
    magnetizing_branch_index: int | None = field(default=None, init=False)
    state: _TransformerPhaseState = field(default_factory=_TransformerPhaseState, init=False)

    def __post_init__(self) -> None:
        _validate_transformer_parameters(
            self.name,
            self.turns_ratio,
            self.leakage_resistance,
            self.leakage_inductance,
            self.magnetizing_inductance,
            self.core_loss_resistance,
            self.saturation_knee_flux,
            self.saturated_magnetizing_inductance,
        )

    def nodes(self) -> Iterable[str]:
        return (self.primary_positive, self.primary_negative, self.secondary_positive, self.secondary_negative)

    def register(self, node_manager: NodeManager, variable_manager: VariableManager) -> None:
        """注册一次、二次绕组电流和可选励磁电流。"""

        self.primary_branch_index = variable_manager.add_branch_current(f"{self.name}:primary")
        self.secondary_branch_index = variable_manager.add_branch_current(f"{self.name}:secondary")
        if self.magnetizing_inductance is not None:
            self.magnetizing_branch_index = variable_manager.add_branch_current(f"{self.name}:magnetizing")

    def stamp(self, context: StampContext, matrix: np.ndarray, rhs: np.ndarray) -> None:
        """写入单相变压器 stamp。"""

        if self.primary_branch_index is None or self.secondary_branch_index is None:
            raise RuntimeError(f"变压器 {self.name} 尚未注册支路变量。")
        _stamp_transformer_phase(
            context,
            matrix,
            rhs,
            self.primary_positive,
            self.primary_negative,
            self.secondary_positive,
            self.secondary_negative,
            self.primary_branch_index,
            self.secondary_branch_index,
            self.magnetizing_branch_index,
            self.turns_ratio,
            self.leakage_resistance,
            self.leakage_inductance,
            self.magnetizing_inductance,
            self.core_loss_resistance,
            self.saturated_magnetizing_inductance,
            self.saturation_knee_flux,
            self.state,
        )

    def update_state(self, context: StampContext, solution: np.ndarray) -> None:
        """更新单相变压器漏感和励磁状态。"""

        if self.primary_branch_index is None or self.secondary_branch_index is None:
            return
        _update_transformer_phase(
            context,
            solution,
            self.primary_positive,
            self.primary_negative,
            self.secondary_positive,
            self.secondary_negative,
            self.primary_branch_index,
            self.secondary_branch_index,
            self.magnetizing_branch_index,
            self.turns_ratio,
            self.leakage_resistance,
            self.state,
        )

    def outputs(self, context: StampContext, solution: np.ndarray) -> dict[str, float]:
        """记录一次电流、二次电流和励磁量。"""

        return {
            f"i:{self.name}:primary": self.state.last_primary_current,
            f"i:{self.name}:secondary": self.state.last_secondary_current,
            f"i:{self.name}:magnetizing": self.state.last_magnetizing_current,
            f"flux:{self.name}:magnetizing": self.state.magnetizing_flux,
        }


def _winding_port(bus: str, connection: TransformerConnection, phase: PhaseName, neutral: str) -> tuple[str, str]:
    """返回三相绕组某相的两端节点。"""

    if connection == "Y":
        return phase_node(bus, phase), neutral
    if connection == "D":
        mapping: dict[PhaseName, tuple[PhaseName, PhaseName]] = {"a": ("a", "b"), "b": ("b", "c"), "c": ("c", "a")}
        positive_phase, negative_phase = mapping[phase]
        return phase_node(bus, positive_phase), phase_node(bus, negative_phase)
    raise ValueError(f"不支持的绕组接法：{connection}")


@dataclass(slots=True)
class ThreePhaseTransformer(Component):
    """三相两绕组变压器教学模型。

    `primary_connection` 和 `secondary_connection` 支持 `"Y"` 与 `"D"`，因此可表示
    Y/Y、Y/Δ、Δ/Y。`turns_ratio` 是一次每相绕组电压与二次每相绕组电压之比。
    """

    name: str
    primary_bus: str
    secondary_bus: str
    turns_ratio: float
    primary_connection: TransformerConnection = "Y"
    secondary_connection: TransformerConnection = "Y"
    primary_neutral: str = "0"
    secondary_neutral: str = "0"
    leakage_resistance: float = 0.0
    leakage_inductance: float = 0.0
    magnetizing_inductance: float | None = None
    core_loss_resistance: float | None = None
    saturation_knee_flux: float | None = None
    saturated_magnetizing_inductance: float | None = None
    primary_branch_indices: dict[PhaseName, int] = field(default_factory=dict, init=False)
    secondary_branch_indices: dict[PhaseName, int] = field(default_factory=dict, init=False)
    magnetizing_branch_indices: dict[PhaseName, int] = field(default_factory=dict, init=False)
    states: dict[PhaseName, _TransformerPhaseState] = field(default_factory=lambda: {phase: _TransformerPhaseState() for phase in PHASES}, init=False)

    def __post_init__(self) -> None:
        _validate_transformer_parameters(
            self.name,
            self.turns_ratio,
            self.leakage_resistance,
            self.leakage_inductance,
            self.magnetizing_inductance,
            self.core_loss_resistance,
            self.saturation_knee_flux,
            self.saturated_magnetizing_inductance,
        )
        if self.primary_connection not in {"Y", "D"}:
            raise ValueError(f"变压器 {self.name} 的一次接法必须为 'Y' 或 'D'。")
        if self.secondary_connection not in {"Y", "D"}:
            raise ValueError(f"变压器 {self.name} 的二次接法必须为 'Y' 或 'D'。")
        has_delta = self.primary_connection == "D" or self.secondary_connection == "D"
        has_leakage = self.leakage_resistance > 0 or self.leakage_inductance > 0
        if has_delta and not has_leakage:
            raise ValueError(
                f"三相变压器 {self.name} 含 Δ 接法时需要设置非零漏阻抗，"
                "以避免纯理想电压约束环导致 MNA 矩阵奇异。"
            )

    def nodes(self) -> Iterable[str]:
        nodes: list[str] = []
        for phase in PHASES:
            nodes.extend(_winding_port(self.primary_bus, self.primary_connection, phase, self.primary_neutral))
            nodes.extend(_winding_port(self.secondary_bus, self.secondary_connection, phase, self.secondary_neutral))
        return nodes

    def register(self, node_manager: NodeManager, variable_manager: VariableManager) -> None:
        """为三相每个绕组相注册一次、二次和可选励磁电流。"""

        self.primary_branch_indices = {
            phase: variable_manager.add_branch_current(f"{self.name}:primary:{phase}") for phase in PHASES
        }
        self.secondary_branch_indices = {
            phase: variable_manager.add_branch_current(f"{self.name}:secondary:{phase}") for phase in PHASES
        }
        if self.magnetizing_inductance is not None:
            self.magnetizing_branch_indices = {
                phase: variable_manager.add_branch_current(f"{self.name}:magnetizing:{phase}") for phase in PHASES
            }

    def stamp(self, context: StampContext, matrix: np.ndarray, rhs: np.ndarray) -> None:
        """写入三相变压器 stamp。"""

        for phase in PHASES:
            primary_positive, primary_negative = _winding_port(
                self.primary_bus,
                self.primary_connection,
                phase,
                self.primary_neutral,
            )
            secondary_positive, secondary_negative = _winding_port(
                self.secondary_bus,
                self.secondary_connection,
                phase,
                self.secondary_neutral,
            )
            _stamp_transformer_phase(
                context,
                matrix,
                rhs,
                primary_positive,
                primary_negative,
                secondary_positive,
                secondary_negative,
                self.primary_branch_indices[phase],
                self.secondary_branch_indices[phase],
                self.magnetizing_branch_indices.get(phase),
                self.turns_ratio,
                self.leakage_resistance,
                self.leakage_inductance,
                self.magnetizing_inductance,
                self.core_loss_resistance,
                self.saturated_magnetizing_inductance,
                self.saturation_knee_flux,
                self.states[phase],
            )

    def update_state(self, context: StampContext, solution: np.ndarray) -> None:
        """更新三相变压器状态。"""

        for phase in PHASES:
            primary_positive, primary_negative = _winding_port(
                self.primary_bus,
                self.primary_connection,
                phase,
                self.primary_neutral,
            )
            secondary_positive, secondary_negative = _winding_port(
                self.secondary_bus,
                self.secondary_connection,
                phase,
                self.secondary_neutral,
            )
            _update_transformer_phase(
                context,
                solution,
                primary_positive,
                primary_negative,
                secondary_positive,
                secondary_negative,
                self.primary_branch_indices[phase],
                self.secondary_branch_indices[phase],
                self.magnetizing_branch_indices.get(phase),
                self.turns_ratio,
                self.leakage_resistance,
                self.states[phase],
            )

    def outputs(self, context: StampContext, solution: np.ndarray) -> dict[str, float]:
        """记录三相变压器各相电流和励磁磁链。"""

        outputs: dict[str, float] = {}
        for phase in PHASES:
            state = self.states[phase]
            outputs[f"i:{self.name}:primary:{phase}"] = state.last_primary_current
            outputs[f"i:{self.name}:secondary:{phase}"] = state.last_secondary_current
            outputs[f"i:{self.name}:magnetizing:{phase}"] = state.last_magnetizing_current
            outputs[f"flux:{self.name}:magnetizing:{phase}"] = state.magnetizing_flux
        return outputs
