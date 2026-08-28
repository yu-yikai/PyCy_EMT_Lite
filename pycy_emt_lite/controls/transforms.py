"""
文件名称：transforms.py
文件作用：实现三相 abc、静止 alpha-beta 和同步旋转 dq 坐标变换。

主要内容：
1. 幅值不变 Clarke 变换
2. Park 和反 Park 变换
3. 角度归一化辅助函数
"""

from __future__ import annotations

import math


def abc_to_alpha_beta(a: float, b: float, c: float) -> tuple[float, float]:
    """把三相 abc 量变换到静止 alpha-beta 坐标。

    本项目第一版采用幅值不变 Clarke 变换：

    ```text
    alpha = 2/3 * (a - b/2 - c/2)
    beta  = 2/3 * sqrt(3)/2 * (b - c)
    ```
    """

    alpha = (2.0 / 3.0) * (float(a) - 0.5 * float(b) - 0.5 * float(c))
    beta = (math.sqrt(3.0) / 3.0) * (float(b) - float(c))
    return alpha, beta


def alpha_beta_to_abc(alpha: float, beta: float) -> tuple[float, float, float]:
    """把 alpha-beta 量反变换到平衡三相 abc 坐标。"""

    a = float(alpha)
    b = -0.5 * float(alpha) + (math.sqrt(3.0) / 2.0) * float(beta)
    c = -0.5 * float(alpha) - (math.sqrt(3.0) / 2.0) * float(beta)
    return a, b, c


def alpha_beta_to_dq(alpha: float, beta: float, angle: float) -> tuple[float, float]:
    """把 alpha-beta 量投影到以 `angle` 为电角度的 dq 坐标。"""

    cos_theta = math.cos(angle)
    sin_theta = math.sin(angle)
    d_axis = float(alpha) * cos_theta + float(beta) * sin_theta
    q_axis = -float(alpha) * sin_theta + float(beta) * cos_theta
    return d_axis, q_axis


def dq_to_alpha_beta(d_axis: float, q_axis: float, angle: float) -> tuple[float, float]:
    """把 dq 量反变换到 alpha-beta 坐标。"""

    cos_theta = math.cos(angle)
    sin_theta = math.sin(angle)
    alpha = float(d_axis) * cos_theta - float(q_axis) * sin_theta
    beta = float(d_axis) * sin_theta + float(q_axis) * cos_theta
    return alpha, beta


def abc_to_dq(a: float, b: float, c: float, angle: float) -> tuple[float, float]:
    """把三相 abc 量直接变换到 dq 坐标。"""

    alpha, beta = abc_to_alpha_beta(a, b, c)
    return alpha_beta_to_dq(alpha, beta, angle)


def dq_to_abc(d_axis: float, q_axis: float, angle: float) -> tuple[float, float, float]:
    """把 dq 量直接反变换到平衡三相 abc 坐标。"""

    alpha, beta = dq_to_alpha_beta(d_axis, q_axis, angle)
    return alpha_beta_to_abc(alpha, beta)


def wrap_angle(angle: float) -> float:
    """把角度归一化到 `[0, 2π)` 区间。"""

    return float(angle) % (2.0 * math.pi)
