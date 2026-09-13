"""
文件名称：pwm.py
文件作用：提供 PWM 生成相关的基础函数。

主要内容：
1. 三角载波生成
2. 正弦调制占空比
3. 载波比较开关逻辑
"""

from __future__ import annotations

import math

from pycy_emt_lite.controls.blocks import _finite_real

def triangular_carrier(time: float, switching_frequency: float) -> float:
    """生成范围为 `[-1, 1]` 的对称三角载波。"""

    time = _finite_real(time, "triangular_carrier.time")
    switching_frequency = _finite_real(switching_frequency, "triangular_carrier.switching_frequency", positive=True)
    phase = _finite_real(time * switching_frequency, "triangular_carrier.time*switching_frequency") % 1.0
    if phase < 0.5:
        return 4.0 * phase - 1.0
    return 3.0 - 4.0 * phase


def sine_pwm_duty(modulation_index: float, angle: float) -> float:
    """计算单相正弦 PWM 占空比。

    `modulation_index` 第一版限制在 `[0, 1]`，输出占空比位于 `[0, 1]`。
    """

    modulation_index = _finite_real(modulation_index, "sine_pwm_duty.modulation_index")
    angle = _finite_real(angle, "sine_pwm_duty.angle")
    if not 0.0 <= modulation_index <= 1.0:
        raise ValueError("sine_pwm_duty.modulation_index 越界；请使用 [0, 1] 内的调制比。")
    duty = 0.5 + 0.5 * modulation_index * math.sin(angle)
    return min(max(duty, 0.0), 1.0)


def carrier_compare(reference: float, carrier: float) -> int:
    """执行载波比较，返回 1 表示上桥臂导通，0 表示关断。"""

    reference = _finite_real(reference, "carrier_compare.reference")
    carrier = _finite_real(carrier, "carrier_compare.carrier")
    return 1 if reference >= carrier else 0
