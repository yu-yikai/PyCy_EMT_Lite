"""
文件名称：stamping.py
文件作用：提供常用 MNA stamp 辅助函数。

主要内容：
1. 写入两端电导
2. 写入两端电流源
3. 从解向量读取两端电压
"""

from __future__ import annotations

import numpy as np


def add_conductance(matrix: np.ndarray, positive: int | None, negative: int | None, conductance: float) -> None:
    """向 MNA 矩阵写入连接在两个节点之间的电导。"""

    if positive is not None:
        matrix[positive, positive] += conductance
    if negative is not None:
        matrix[negative, negative] += conductance
    if positive is not None and negative is not None:
        matrix[positive, negative] -= conductance
        matrix[negative, positive] -= conductance


def add_current_source(rhs: np.ndarray, positive: int | None, negative: int | None, current: float) -> None:
    """向右端向量写入从 positive 流向 negative 的电流源。"""

    if positive is not None:
        rhs[positive] -= current
    if negative is not None:
        rhs[negative] += current


def add_voltage_probe(solution: np.ndarray, positive: int | None, negative: int | None) -> float:
    """从解向量读取两节点电压差 `V_positive - V_negative`。"""

    vp = 0.0 if positive is None else float(solution[positive])
    vn = 0.0 if negative is None else float(solution[negative])
    return vp - vn
