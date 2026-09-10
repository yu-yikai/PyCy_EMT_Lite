"""
文件名称：stamping.py
文件作用：提供常用 MNA stamp 辅助函数。

主要内容：
1. 写入两端电导
2. 写入两端电流源
3. 从解向量读取两端电压
"""

from __future__ import annotations

from collections.abc import Callable

import numpy as np
from scipy.linalg import qr, solve_triangular


class _InitialConditions:
    """仅用于线性 RLC 的瞬时一致求解；不推进时间。

    电容暂作固定电压支路，电感暂作固定电流支路。若冻结状态使方程相关，
    只对相关约束求导一次，用 iC=C*dvC/dt、vL=L*diL/dt 补足代数量。
    临时电容电流变量不进入 Circuit 的长期编号。
    """

    def __init__(self) -> None:
        self.capacitors: dict[object, tuple[int | None, int | None, float, float]] = {}
        self.inductors: list[tuple[int, float, float]] = []
        self.source_derivatives: list[tuple[dict[int, float], Callable[[], float]]] = []
        self.capacitor_currents: dict[object, float] = {}

    def assemble(self, matrix: np.ndarray, rhs: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """冻结状态，并为欠定的支路电流/节点电压补充物理导数约束。"""

        base_size = len(rhs)
        count = len(self.capacitors)
        matrix = np.pad(matrix, ((0, count), (0, count)))
        rhs = np.pad(rhs, (0, count))
        derivative = np.zeros_like(matrix)
        derivative_rhs = np.zeros_like(rhs)
        for branch, inductance, current in self.inductors:
            derivative[branch] = matrix[branch] / inductance
            derivative_rhs[branch] = -rhs[branch] / inductance
            matrix[branch] = 0.0
            matrix[branch, branch] = 1.0
            rhs[branch] = current
        for branch, (p, n, capacitance, voltage) in enumerate(self.capacitors.values(), base_size):
            if p is not None:
                matrix[p, branch] += 1.0
                matrix[branch, p] += 1.0
            if n is not None:
                matrix[n, branch] -= 1.0
                matrix[branch, n] -= 1.0
            rhs[branch] = voltage
            derivative[branch, branch] = 1.0 / capacitance

        self.matrix, self.rhs = matrix, rhs
        # 行归一化后，QR 只用于选独立方程；解仍由现有线性求解器计算。
        scale = np.max(np.abs(matrix), axis=1)
        scale[scale == 0] = 1.0
        scaled = matrix / scale[:, None]
        _, triangular, order = qr(scaled.T, pivoting=True)
        threshold = np.finfo(float).eps * len(rhs) * np.max(np.abs(triangular))
        rank = int(np.count_nonzero(np.abs(np.diag(triangular)) > threshold))
        if rank == len(rhs):
            return matrix, rhs

        weights = solve_triangular(triangular[:rank, :rank], triangular[:rank, rank:])
        dependent = np.zeros((len(rhs) - rank, len(rhs)))
        dependent[:, order[rank:]] = np.eye(len(rhs) - rank)
        dependent[:, order[:rank]] = -weights.T
        # 清除 QR 舍入噪声，再还原各物理方程的尺度。
        tiny = 8 * np.finfo(float).eps * len(rhs) * np.max(np.abs(dependent), axis=1, keepdims=True)
        dependent[np.abs(dependent) < tiny] = 0.0
        dependent /= scale[None, :]
        residual = dependent @ rhs
        tolerance = 1e-12 + 1e-10 * (np.abs(dependent) @ np.abs(rhs))
        if np.any(np.abs(residual) > tolerance):
            raise ValueError("储能初值与网络约束冲突；不支持电压/电流冲激。")

        for terms, value_at in self.source_derivatives:
            projection = sum(dependent[:, row] * coefficient for row, coefficient in terms.items())
            if np.any(projection != 0.0):
                value = value_at()
                for row, coefficient in terms.items():
                    derivative_rhs[row] += coefficient * value

        # A*xdot = derivative*x + derivative_rhs；相关行满足 dependent*A=0，
        # 因而只需补 dependent*derivative*x = -dependent*derivative_rhs。
        completed = np.vstack((scaled[order[:rank]], dependent @ derivative))
        completed_rhs = np.concatenate((rhs[order[:rank]] / scale[order[:rank]], -dependent @ derivative_rhs))
        completed_scale = np.max(np.abs(completed), axis=1)
        completed_scale[completed_scale == 0] = 1.0
        if np.linalg.matrix_rank(completed / completed_scale[:, None]) < len(rhs):
            raise ValueError("一次导数约束后仍欠定；不支持该结构或无法唯一确定支路电流。")
        return completed, completed_rhs

    def accept(self, solution: np.ndarray, base_size: int) -> None:
        """检查原始约束，保留临时电容电流供已有状态更新函数读取。"""

        residual = self.matrix @ solution - self.rhs
        tolerance = 1e-12 + 1e-10 * (np.abs(self.matrix) @ np.abs(solution) + np.abs(self.rhs))
        if np.any(np.abs(residual) > tolerance):
            raise ValueError("储能初值与网络约束冲突；一致求解未满足原始方程。")
        self.capacitor_currents = dict(zip(self.capacitors, map(float, solution[base_size:])))


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
