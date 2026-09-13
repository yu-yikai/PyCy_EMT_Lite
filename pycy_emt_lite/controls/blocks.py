"""
文件名称：blocks.py
文件作用：实现离散控制系统基础模块。

主要内容：
1. 控制模块统一接口
2. 限幅器、PI 控制器、一阶低通滤波器
3. 整步采样延迟模块
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
import math
from numbers import Integral, Real
from typing import Protocol, runtime_checkable


@runtime_checkable
class ControlBlock(Protocol):
    """离散控制模块统一接口。

    控制模块在每个采样时刻调用 `step(input_value, time_step)` 推进一步。
    `reset()` 用于把内部状态恢复到指定初值，便于重复仿真和测试。
    """

    def step(self, input_value: float, time_step: float) -> float:
        """推进一个采样周期并返回输出。"""

    def reset(self, value: float = 0.0) -> None:
        """重置控制模块内部状态。"""


def _finite_real(value: float, name: str, *, positive: bool = False) -> float:
    """在转换为 float 前拒绝非数值、布尔值和非有限量。"""

    try:
        valid = not isinstance(value, bool) and isinstance(value, Real) and math.isfinite(value)
    except OverflowError:
        valid = False
    if not valid or (positive and value <= 0.0):
        required = "有限正实数" if positive else "有限实数"
        raise ValueError(f"{name}={value!r} 非法；请使用{required}，不要使用布尔值、字符串、NaN 或 Inf。")
    return float(value)


def _validate_time_step(time_step: float) -> None:
    """控制采样间隔以秒为单位，且必须为有限正数。"""

    _finite_real(time_step, "time_step", positive=True)


@dataclass(slots=True)
class Limiter:
    """限幅器。

    `lower` 和 `upper` 分别表示输出下限和上限。该模块无动态状态。
    """

    lower: float
    upper: float

    def __post_init__(self) -> None:
        self.lower = _finite_real(self.lower, "Limiter.lower")
        self.upper = _finite_real(self.upper, "Limiter.upper")
        if self.lower > self.upper:
            raise ValueError("Limiter.lower 大于 upper；请将下限设为不大于上限的值。")

    def step(self, input_value: float, time_step: float) -> float:
        """返回限幅后的输入值。"""

        _validate_time_step(time_step)
        return min(max(_finite_real(input_value, "Limiter.input_value"), self.lower), self.upper)

    def reset(self, value: float = 0.0) -> None:
        """限幅器没有内部状态，重置时不执行操作。"""

        _finite_real(value, "Limiter.reset value")

@dataclass(slots=True)
class PIController:
    """离散 PI 控制器。

    控制律为：

    ```text
    u = Kp * e + xi
    xi_k = xi_{k-1} + Ki * e * dt
    ```

    如果配置了 `lower` 和 `upper`，输出会被限幅；当输出已饱和且误差继续推动
    积分项进入饱和方向时，本实现冻结该步积分，作为第一版抗积分饱和策略。
    """

    proportional_gain: float
    integral_gain: float
    lower: float | None = None
    upper: float | None = None
    integrator: float = 0.0
    last_output: float = 0.0

    def __post_init__(self) -> None:
        for name in ("proportional_gain", "integral_gain", "integrator", "last_output"):
            setattr(self, name, _finite_real(getattr(self, name), f"PIController.{name}"))
        for name in ("lower", "upper"):
            value = getattr(self, name)
            if value is not None:
                setattr(self, name, _finite_real(value, f"PIController.{name}"))
        if self.lower is not None and self.upper is not None and self.lower > self.upper:
            raise ValueError("PIController.lower 大于 upper；请将下限设为不大于上限的值。")

    def step(self, input_value: float, time_step: float) -> float:
        """根据误差输入推进 PI 控制器。"""

        _validate_time_step(time_step)
        error = _finite_real(input_value, "PIController.input_value")
        candidate_integrator = _finite_real(self.integrator + self.integral_gain * error * time_step,
                                            "PIController.integrator")
        raw_output = _finite_real(self.proportional_gain * error + candidate_integrator, "PIController.output")
        limited_output = self._limit(raw_output)

        saturated_high = self.upper is not None and raw_output > self.upper and error > 0.0
        saturated_low = self.lower is not None and raw_output < self.lower and error < 0.0
        if not (saturated_high or saturated_low):
            self.integrator = candidate_integrator

        self.last_output = limited_output
        return limited_output

    def reset(self, value: float = 0.0) -> None:
        """把积分状态和输出状态重置为指定值。"""

        value = _finite_real(value, "PIController.reset value")
        self.integrator = value
        self.last_output = self._limit(value)

    def _limit(self, value: float) -> float:
        """按可选上下限约束输出。"""

        output = float(value)
        if self.lower is not None:
            output = max(output, self.lower)
        if self.upper is not None:
            output = min(output, self.upper)
        return output


@dataclass(slots=True)
class FirstOrderLowPass:
    """一阶低通滤波器。

    连续模型为 `dy/dt = (u - y) / tau`，离散化采用后退欧拉形式：

    ```text
    y_k = (y_{k-1} + alpha * u_k) / (1 + alpha)
    alpha = dt / tau
    ```
    """

    time_constant: float
    state: float = 0.0

    def __post_init__(self) -> None:
        self.time_constant = _finite_real(self.time_constant, "FirstOrderLowPass.time_constant", positive=True)
        self.state = _finite_real(self.state, "FirstOrderLowPass.state")

    def step(self, input_value: float, time_step: float) -> float:
        """推进一阶低通滤波器。"""

        _validate_time_step(time_step)
        value = _finite_real(input_value, "FirstOrderLowPass.input_value")
        alpha = _finite_real(time_step / self.time_constant, "FirstOrderLowPass.time_step/time_constant")
        state = _finite_real((self.state + alpha * value) / (1.0 + alpha), "FirstOrderLowPass.state")
        self.state = state
        return self.state

    def reset(self, value: float = 0.0) -> None:
        """重置滤波器状态。"""

        self.state = _finite_real(value, "FirstOrderLowPass.reset value")


@dataclass(slots=True)
class SampleDelay:
    """整采样周期延迟模块。

    `steps` 表示延迟的采样步数。`initial_value` 用于填充仿真开始前的历史队列。
    """

    steps: int
    initial_value: float = 0.0
    _buffer: deque[float] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if isinstance(self.steps, bool) or not isinstance(self.steps, Integral) or self.steps < 0:
            raise ValueError(f"SampleDelay.steps={self.steps!r} 非法；请使用非负整数步数，不使用布尔值。")
        self.steps = int(self.steps)
        self.initial_value = _finite_real(self.initial_value, "SampleDelay.initial_value")
        self._buffer = deque([self.initial_value] * self.steps, maxlen=self.steps)

    def step(self, input_value: float, time_step: float) -> float:
        """返回延迟后的输入值。"""

        _validate_time_step(time_step)
        value = _finite_real(input_value, "SampleDelay.input_value")
        if self.steps == 0:
            return value
        output = self._buffer[0]
        self._buffer.append(value)
        return output

    def reset(self, value: float = 0.0) -> None:
        """用指定值重新填充延迟队列。"""

        self.initial_value = _finite_real(value, "SampleDelay.reset value")
        self._buffer = deque([self.initial_value] * self.steps, maxlen=self.steps)
