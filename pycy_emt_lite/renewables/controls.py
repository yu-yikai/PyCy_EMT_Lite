"""
文件名称：controls.py
文件作用：提供新能源并网阶段的跟网、构网、LVRT 简化控制器。
主要内容：
1. 跟网型变流器功率外环与 dq 电流内环
2. 下垂控制与 VSG 教学模型
3. 电压跌落穿越 LVRT 简化逻辑
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from pycy_emt_lite.controls.blocks import PIController
from pycy_emt_lite.controls.transforms import wrap_angle


def _validate_time_step(time_step: float) -> None:
    """检查控制采样周期。"""

    if time_step <= 0.0:
        raise ValueError("控制采样周期必须大于 0。")


@dataclass(slots=True)
class GridFollowingControlState:
    """跟网型控制器单步输出状态。"""

    d_axis_current_reference: float
    q_axis_current_reference: float
    d_axis_voltage_command: float
    q_axis_voltage_command: float


@dataclass(slots=True)
class GridFollowingPowerController:
    """跟网型变流器功率外环和电流内环。

    外环按瞬时功率关系计算 dq 电流参考：
    `P = 1.5(vd id + vq iq)`，`Q = 1.5(vq id - vd iq)`。
    内环使用 PI 控制，并加入 L 滤波器 dq 交叉耦合前馈。
    """

    d_current_controller: PIController
    q_current_controller: PIController
    filter_inductance: float
    filter_resistance: float
    current_limit: float
    min_voltage_magnitude: float = 1.0

    def __post_init__(self) -> None:
        if self.filter_inductance <= 0.0:
            raise ValueError("滤波电感必须大于 0。")
        if self.filter_resistance < 0.0:
            raise ValueError("滤波电阻不能小于 0。")
        if self.current_limit <= 0.0:
            raise ValueError("电流限值必须大于 0。")
        if self.min_voltage_magnitude <= 0.0:
            raise ValueError("最小电压幅值必须大于 0。")

    def current_references(self, active_power: float, reactive_power: float, grid_d_voltage: float, grid_q_voltage: float) -> tuple[float, float]:
        """由有功/无功功率参考计算 dq 电流参考。"""

        denominator = 1.5 * (grid_d_voltage * grid_d_voltage + grid_q_voltage * grid_q_voltage)
        denominator = max(denominator, 1.5 * self.min_voltage_magnitude * self.min_voltage_magnitude)
        d_reference = (active_power * grid_d_voltage + reactive_power * grid_q_voltage) / denominator
        q_reference = (active_power * grid_q_voltage - reactive_power * grid_d_voltage) / denominator
        magnitude = math.hypot(d_reference, q_reference)
        if magnitude > self.current_limit:
            scale = self.current_limit / magnitude
            d_reference *= scale
            q_reference *= scale
        return d_reference, q_reference

    def step(
        self,
        *,
        active_power_reference: float,
        reactive_power_reference: float,
        d_axis_current: float,
        q_axis_current: float,
        grid_d_voltage: float,
        grid_q_voltage: float,
        angular_frequency: float,
        time_step: float,
    ) -> GridFollowingControlState:
        """推进功率外环和电流内环，返回 dq 电压指令。"""

        _validate_time_step(time_step)
        d_reference, q_reference = self.current_references(
            active_power_reference,
            reactive_power_reference,
            grid_d_voltage,
            grid_q_voltage,
        )
        d_error = d_reference - d_axis_current
        q_error = q_reference - q_axis_current
        d_control = self.d_current_controller.step(d_error, time_step)
        q_control = self.q_current_controller.step(q_error, time_step)
        d_voltage = grid_d_voltage - angular_frequency * self.filter_inductance * q_axis_current
        d_voltage += self.filter_resistance * d_axis_current + d_control
        q_voltage = grid_q_voltage + angular_frequency * self.filter_inductance * d_axis_current
        q_voltage += self.filter_resistance * q_axis_current + q_control
        return GridFollowingControlState(d_reference, q_reference, d_voltage, q_voltage)

    def reset(self) -> None:
        """重置两个电流环 PI 控制器。"""

        self.d_current_controller.reset()
        self.q_current_controller.reset()


@dataclass(slots=True)
class DroopControlState:
    """下垂控制器单步输出状态。"""

    angle: float
    angular_frequency: float
    voltage_reference: float


@dataclass(slots=True)
class DroopController:
    """构网型变流器 P-f/Q-V 下垂控制器。"""

    nominal_frequency: float
    nominal_voltage: float
    active_power_reference: float
    reactive_power_reference: float
    frequency_droop: float
    voltage_droop: float
    angle: float = 0.0

    def __post_init__(self) -> None:
        if self.nominal_frequency <= 0.0:
            raise ValueError("额定频率必须大于 0。")
        if self.nominal_voltage <= 0.0:
            raise ValueError("额定电压必须大于 0。")
        if self.frequency_droop < 0.0 or self.voltage_droop < 0.0:
            raise ValueError("下垂系数不能小于 0。")

    def step(self, active_power: float, reactive_power: float, time_step: float) -> DroopControlState:
        """根据输出功率推进构网相角和电压参考。"""

        _validate_time_step(time_step)
        omega_nominal = 2.0 * math.pi * self.nominal_frequency
        omega = omega_nominal + self.frequency_droop * (self.active_power_reference - active_power)
        voltage = self.nominal_voltage + self.voltage_droop * (self.reactive_power_reference - reactive_power)
        self.angle = wrap_angle(self.angle + omega * time_step)
        return DroopControlState(self.angle, omega, max(voltage, 0.0))

    def reset(self, angle: float = 0.0) -> None:
        """重置构网相角。"""

        self.angle = wrap_angle(angle)


@dataclass(slots=True)
class VSGControlState:
    """VSG 控制器单步输出状态。"""

    angle: float
    angular_frequency: float
    speed_pu: float
    voltage_reference: float


@dataclass(slots=True)
class VSGController:
    """虚拟同步机 VSG 简化控制器。

    本模型采用经典二阶摆动方程的显式离散形式，功率使用三相基准容量归一化。
    """

    nominal_frequency: float
    nominal_voltage: float
    base_power: float
    inertia_constant: float
    damping: float
    active_power_reference: float
    reactive_power_reference: float = 0.0
    voltage_droop: float = 0.0
    angle: float = 0.0
    speed_pu: float = 1.0

    def __post_init__(self) -> None:
        if self.nominal_frequency <= 0.0:
            raise ValueError("额定频率必须大于 0。")
        if self.nominal_voltage <= 0.0:
            raise ValueError("额定电压必须大于 0。")
        if self.base_power <= 0.0:
            raise ValueError("VSG 基准功率必须大于 0。")
        if self.inertia_constant <= 0.0:
            raise ValueError("VSG 惯量常数必须大于 0。")
        if self.damping < 0.0:
            raise ValueError("VSG 阻尼不能小于 0。")

    def step(self, active_power: float, reactive_power: float, time_step: float) -> VSGControlState:
        """推进虚拟转速、相角和电压参考。"""

        _validate_time_step(time_step)
        power_error_pu = (self.active_power_reference - active_power) / self.base_power
        acceleration = (power_error_pu - self.damping * (self.speed_pu - 1.0)) / (2.0 * self.inertia_constant)
        self.speed_pu += acceleration * time_step
        omega_nominal = 2.0 * math.pi * self.nominal_frequency
        omega = omega_nominal * self.speed_pu
        self.angle = wrap_angle(self.angle + omega * time_step)
        voltage = self.nominal_voltage + self.voltage_droop * (self.reactive_power_reference - reactive_power)
        return VSGControlState(self.angle, omega, self.speed_pu, max(voltage, 0.0))

    def reset(self, *, angle: float = 0.0, speed_pu: float = 1.0) -> None:
        """重置 VSG 相角和虚拟转速。"""

        self.angle = wrap_angle(angle)
        self.speed_pu = float(speed_pu)


@dataclass(slots=True)
class LVRTState:
    """LVRT 单步输出状态。"""

    active_power_reference: float
    reactive_power_reference: float
    active_current_scale: float
    voltage_pu: float
    in_lvrt: float


@dataclass(slots=True)
class LVRTController:
    """低电压穿越 LVRT 简化逻辑。

    当电压低于触发阈值时，按 `reactive_current_gain` 增加无功功率参考，
    并按电压标幺值缩减有功参考，保留电流容量用于电压支撑。
    """

    nominal_voltage_rms: float
    trigger_voltage_pu: float = 0.9
    clear_voltage_pu: float = 0.95
    reactive_current_gain: float = 2.0
    min_active_current_scale: float = 0.2
    _latched: bool = field(default=False, init=False, repr=False)

    def __post_init__(self) -> None:
        if self.nominal_voltage_rms <= 0.0:
            raise ValueError("LVRT 额定电压必须大于 0。")
        if not 0.0 < self.trigger_voltage_pu <= self.clear_voltage_pu:
            raise ValueError("LVRT 阈值必须满足 0 < trigger <= clear。")
        if self.min_active_current_scale < 0.0 or self.min_active_current_scale > 1.0:
            raise ValueError("LVRT 最小有功电流比例必须在 [0, 1]。")

    def step(self, voltage_rms: float, active_power_reference: float, reactive_power_reference: float) -> LVRTState:
        """根据当前电压修正有功和无功参考。"""

        voltage_pu = max(float(voltage_rms), 0.0) / self.nominal_voltage_rms
        if voltage_pu < self.trigger_voltage_pu:
            self._latched = True
        elif voltage_pu >= self.clear_voltage_pu:
            self._latched = False

        if not self._latched:
            return LVRTState(active_power_reference, reactive_power_reference, 1.0, voltage_pu, 0.0)

        active_scale = max(self.min_active_current_scale, min(voltage_pu / self.trigger_voltage_pu, 1.0))
        reactive_boost = self.reactive_current_gain * max(self.trigger_voltage_pu - voltage_pu, 0.0)
        return LVRTState(
            active_power_reference * active_scale,
            reactive_power_reference + abs(active_power_reference) * reactive_boost,
            active_scale,
            voltage_pu,
            1.0,
        )

    def reset(self) -> None:
        """清除 LVRT 锁存状态。"""

        self._latched = False
