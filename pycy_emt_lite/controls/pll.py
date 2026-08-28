"""
文件名称：pll.py
文件作用：实现同步旋转坐标系锁相环 SRF-PLL。

主要内容：
1. PLL 状态对象
2. 基于 q 轴电压误差的 PI 锁相逻辑
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from pycy_emt_lite.controls.blocks import PIController
from pycy_emt_lite.controls.transforms import abc_to_dq, wrap_angle


@dataclass(frozen=True, slots=True)
class PLLState:
    """SRF-PLL 单步输出状态。"""

    angle: float
    frequency: float
    d_axis_voltage: float
    q_axis_voltage: float


@dataclass(slots=True)
class SRFPLL:
    """同步旋转坐标系锁相环。

    SRF-PLL 使用当前估计角度把三相电压变换到 dq 坐标，并通过 PI 控制器驱动
    `q` 轴电压趋近 0。`nominal_frequency` 是额定角频率，单位 rad/s。
    """

    proportional_gain: float
    integral_gain: float
    nominal_frequency: float = 2.0 * math.pi * 50.0
    initial_angle: float = 0.0
    minimum_frequency: float | None = None
    maximum_frequency: float | None = None
    _controller: PIController = field(init=False, repr=False)
    angle: float = field(init=False)
    frequency: float = field(init=False)

    def __post_init__(self) -> None:
        self._controller = PIController(
            self.proportional_gain,
            self.integral_gain,
            self.minimum_frequency,
            self.maximum_frequency,
        )
        self.angle = wrap_angle(self.initial_angle)
        self.frequency = self.nominal_frequency

    def step(self, voltages_abc: tuple[float, float, float], time_step: float) -> PLLState:
        """用一组三相电压采样推进 PLL。"""

        if time_step <= 0.0:
            raise ValueError("PLL 采样周期必须大于 0。")
        d_axis_voltage, q_axis_voltage = abc_to_dq(*voltages_abc, self.angle)
        voltage_base = max(abs(d_axis_voltage), abs(q_axis_voltage), 1.0)
        correction = self._controller.step(q_axis_voltage / voltage_base, time_step)
        self.frequency = self.nominal_frequency + correction
        self.angle = wrap_angle(self.angle + self.frequency * time_step)
        return PLLState(self.angle, self.frequency, d_axis_voltage, q_axis_voltage)

    def reset(self, angle: float | None = None) -> None:
        """重置 PLL 角度、频率和 PI 积分状态。"""

        self.angle = wrap_angle(self.initial_angle if angle is None else angle)
        self.frequency = self.nominal_frequency
        self._controller.reset(0.0)
