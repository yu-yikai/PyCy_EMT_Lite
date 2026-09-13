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

from pycy_emt_lite.controls.blocks import PIController, _finite_real, _validate_time_step
from pycy_emt_lite.controls.transforms import abc_to_dq, wrap_angle


@dataclass(frozen=True, slots=True)
class PLLState:
    """当前采样时刻的角度、角频率及该角度下的 d/q 电压。"""

    angle: float
    frequency: float
    d_axis_voltage: float
    q_axis_voltage: float


@dataclass(slots=True)
class SRFPLL:
    """同步旋转坐标系锁相环。

    SRF-PLL 使用当前估计角度把三相电压变换到 dq 坐标，并通过 PI 控制器驱动
    `q` 轴电压趋近 0。`nominal_frequency` 是额定角频率，单位 rad/s。
    `minimum_frequency/maximum_frequency` 限制绝对角频率（rad/s），范围必须包含额定值。
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
        self.nominal_frequency = _finite_real(self.nominal_frequency, "SRFPLL.nominal_frequency", positive=True)
        self.initial_angle = _finite_real(self.initial_angle, "SRFPLL.initial_angle")
        for name in ("minimum_frequency", "maximum_frequency"):
            value = getattr(self, name)
            if value is not None:
                setattr(self, name, _finite_real(value, f"SRFPLL.{name}"))
        if ((self.minimum_frequency is not None and self.minimum_frequency > self.nominal_frequency)
                or (self.maximum_frequency is not None and self.maximum_frequency < self.nominal_frequency)):
            raise ValueError(
                f"SRFPLL.minimum_frequency={self.minimum_frequency!r}、maximum_frequency={self.maximum_frequency!r} "
                f"不包含 nominal_frequency={self.nominal_frequency!r}；请用 rad/s 设置包含额定值的绝对角频率范围，"
                "不要填写频率修正量。"
            )
        self._controller = PIController(
            self.proportional_gain,
            self.integral_gain,
            None if self.minimum_frequency is None else self.minimum_frequency - self.nominal_frequency,
            None if self.maximum_frequency is None else self.maximum_frequency - self.nominal_frequency,
        )
        self.angle = wrap_angle(self.initial_angle)
        self.frequency = self.nominal_frequency

    def step(self, voltages_abc: tuple[float, float, float], time_step: float) -> PLLState:
        """从上次时刻推进到当前电压采样时刻。

        先用上次角频率积分本区间角度，再用当前电压和角度更新 PI。
        新角频率用于下一积分区间；返回的 d/q 电压与返回角度一致。
        """

        _validate_time_step(time_step)
        try:
            voltages = tuple(voltages_abc)
        except TypeError as exc:
            raise ValueError("SRFPLL.voltages_abc 非法；请提供 a/b/c 三个有限实数电压采样。") from exc
        if len(voltages) != 3:
            raise ValueError("SRFPLL.voltages_abc 长度错误；请提供 a/b/c 三个有限实数电压采样。")
        voltages = tuple(_finite_real(v, f"SRFPLL.voltages_abc[{phase}]") for phase, v in zip("abc", voltages))
        angle = wrap_angle(_finite_real(self.angle + self.frequency * time_step, "SRFPLL.angle"))
        d_axis_voltage, q_axis_voltage = abc_to_dq(*voltages, angle)
        _finite_real(d_axis_voltage, "SRFPLL.d_axis_voltage")
        _finite_real(q_axis_voltage, "SRFPLL.q_axis_voltage")
        voltage_base = max(abs(d_axis_voltage), abs(q_axis_voltage), 1.0)
        previous_integrator, previous_output = self._controller.integrator, self._controller.last_output
        correction = self._controller.step(q_axis_voltage / voltage_base, time_step)
        frequency = self.nominal_frequency + correction
        if not math.isfinite(frequency):
            self._controller.integrator, self._controller.last_output = previous_integrator, previous_output
            raise ValueError("SRFPLL.frequency 计算溢出；请减小角频率或 PI 增益，并核对输入电压。")
        # 避免修正量加回额定值后的浮点舍入越过绝对边界。
        if self.minimum_frequency is not None:
            frequency = max(frequency, self.minimum_frequency)
        if self.maximum_frequency is not None:
            frequency = min(frequency, self.maximum_frequency)
        self.frequency = frequency
        self.angle = angle
        return PLLState(self.angle, self.frequency, d_axis_voltage, q_axis_voltage)

    def reset(self, angle: float | None = None) -> None:
        """重置 PLL 角度、频率和 PI 积分状态。"""

        angle = _finite_real(self.initial_angle if angle is None else angle, "SRFPLL.reset angle")
        self.angle = wrap_angle(angle)
        self.frequency = self.nominal_frequency
        self._controller.reset(0.0)
