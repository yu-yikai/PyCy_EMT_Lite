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


def _validate_time_step(time_step: float) -> None:
    """检查控制采样周期是否合法。"""

    if time_step <= 0.0:
        raise ValueError("控制采样周期必须大于 0。")


@dataclass(slots=True)
class Limiter:
    """限幅器。

    `lower` 和 `upper` 分别表示输出下限和上限。该模块无动态状态。
    """

    lower: float
    upper: float

    def __post_init__(self) -> None:
        if self.lower > self.upper:
            raise ValueError("限幅器下限不能大于上限。")

    def step(self, input_value: float, time_step: float) -> float:
        """返回限幅后的输入值。"""

        _validate_time_step(time_step)
        return min(max(float(input_value), self.lower), self.upper)

    def reset(self, value: float = 0.0) -> None:
        """限幅器没有内部状态，重置时不执行操作。"""


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
        if self.lower is not None and self.upper is not None and self.lower > self.upper:
            raise ValueError("PI 控制器输出下限不能大于上限。")

    def step(self, input_value: float, time_step: float) -> float:
        """根据误差输入推进 PI 控制器。"""

        _validate_time_step(time_step)
        error = float(input_value)
        candidate_integrator = self.integrator + self.integral_gain * error * time_step
        raw_output = self.proportional_gain * error + candidate_integrator
        limited_output = self._limit(raw_output)

        saturated_high = self.upper is not None and raw_output > self.upper and error > 0.0
        saturated_low = self.lower is not None and raw_output < self.lower and error < 0.0
        if not (saturated_high or saturated_low):
            self.integrator = candidate_integrator

        self.last_output = limited_output
        return limited_output

    def reset(self, value: float = 0.0) -> None:
        """把积分状态和输出状态重置为指定值。"""

        self.integrator = float(value)
        self.last_output = self._limit(float(value))

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
        if self.time_constant <= 0.0:
            raise ValueError("低通滤波器时间常数必须大于 0。")

    def step(self, input_value: float, time_step: float) -> float:
        """推进一阶低通滤波器。"""

        _validate_time_step(time_step)
        alpha = time_step / self.time_constant
        self.state = (self.state + alpha * float(input_value)) / (1.0 + alpha)
        return self.state

    def reset(self, value: float = 0.0) -> None:
        """重置滤波器状态。"""

        self.state = float(value)


@dataclass(slots=True)
class SampleDelay:
    """整采样周期延迟模块。

    `steps` 表示延迟的采样步数。`initial_value` 用于填充仿真开始前的历史队列。
    """

    steps: int
    initial_value: float = 0.0
    _buffer: deque[float] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if self.steps < 0:
            raise ValueError("采样延迟步数不能小于 0。")
        self._buffer = deque([float(self.initial_value)] * self.steps, maxlen=self.steps)

    def step(self, input_value: float, time_step: float) -> float:
        """返回延迟后的输入值。"""

        _validate_time_step(time_step)
        if self.steps == 0:
            return float(input_value)
        output = self._buffer[0]
        self._buffer.append(float(input_value))
        return output

    def reset(self, value: float = 0.0) -> None:
        """用指定值重新填充延迟队列。"""

        self.initial_value = float(value)
        self._buffer = deque([self.initial_value] * self.steps, maxlen=self.steps)
