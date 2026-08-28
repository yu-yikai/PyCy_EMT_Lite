"""
文件名称：solvers.py
文件作用：定义 MNA 线性方程求解器接口和基于 SciPy LU 的稠密求解器。

主要内容：
1. 统一线性求解器协议
2. 基于 SciPy LU 分解的稠密求解器
3. 残差、奇异矩阵和非有限数值诊断
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass
from typing import Protocol, TypeAlias

import numpy as np
from scipy.linalg import LinAlgWarning, lu_factor, lu_solve

DEFAULT_RESIDUAL_RTOL = 1e-10
DEFAULT_RESIDUAL_ATOL = 1e-12


class LinearSolveError(RuntimeError):
    """线性方程求解失败。"""


@dataclass(frozen=True, slots=True)
class LinearSolveDiagnostics:
    """记录最近一次线性求解的残差和分解信息。"""

    backend: str
    absolute_residual: float
    relative_residual: float
    matrix_size: int
    nnz: int
    reused_factorization: bool
    factorization_count: int
    solve_count: int


MatrixInput: TypeAlias = np.ndarray


class Factorization(Protocol):
    """已经完成分解、可对多个右端项重复求解的最小协议。"""

    backend_name: str
    matrix: np.ndarray

    def solve(self, rhs: np.ndarray) -> np.ndarray:
        """使用已保存的分解求解一个或多个右端项。"""


class LinearSolver(Protocol):
    """MNA 线性方程求解器协议。"""

    name: str

    def solve(self, matrix: MatrixInput, rhs: np.ndarray) -> np.ndarray:
        """求解 `matrix * x = rhs` 并返回解向量。"""


@dataclass(slots=True)
class _DenseLUFactorization:
    """保存稠密矩阵及其 LU 分解。"""

    matrix: np.ndarray
    lu: np.ndarray
    pivots: np.ndarray
    backend_name: str = "dense_scipy_lu"

    def solve(self, rhs: np.ndarray) -> np.ndarray:
        """使用已缓存的稠密 LU 分解求解右端项。"""

        return np.asarray(lu_solve((self.lu, self.pivots), rhs, check_finite=True), dtype=float)


def _validate_square_finite_matrix(matrix: np.ndarray) -> None:
    """检查矩阵形状和有限性。"""

    if len(matrix.shape) != 2 or matrix.shape[0] != matrix.shape[1]:
        raise LinearSolveError("MNA 系数矩阵必须是方阵。")
    if not np.all(np.isfinite(matrix)):
        raise LinearSolveError("MNA 系数矩阵包含 NaN 或 Inf，无法进行 LU 分解。")


def _validate_rhs(rhs: np.ndarray, matrix_size: int) -> np.ndarray:
    """检查右端项维度和有限性。"""

    rhs_array = np.asarray(rhs, dtype=float)
    if rhs_array.ndim != 1 or rhs_array.shape[0] != matrix_size:
        raise LinearSolveError("线性方程右端项维度与 MNA 系数矩阵不匹配。")
    if not np.all(np.isfinite(rhs_array)):
        raise LinearSolveError("线性方程右端项包含 NaN 或 Inf。")
    return rhs_array


def _solve_factorization(
    factorization: Factorization,
    rhs: np.ndarray,
    *,
    residual_rtol: float,
    residual_atol: float,
    reused_factorization: bool,
    factorization_count: int,
    solve_count: int,
) -> tuple[np.ndarray, LinearSolveDiagnostics]:
    """求解并验证残差，返回数值解和诊断。"""

    rhs_array = _validate_rhs(rhs, factorization.matrix.shape[0])
    try:
        solution = factorization.solve(rhs_array)
    except (ValueError, RuntimeError) as exc:
        raise LinearSolveError(f"{factorization.backend_name} 求解失败。") from exc
    if not np.all(np.isfinite(solution)):
        raise LinearSolveError(f"{factorization.backend_name} 返回 NaN 或 Inf。")

    residual = factorization.matrix @ solution - rhs_array
    absolute_residual = float(np.linalg.norm(residual, ord=np.inf))
    matrix_scale = float(np.linalg.norm(factorization.matrix, ord=np.inf))
    solution_scale = float(np.linalg.norm(solution, ord=np.inf))
    rhs_scale = float(np.linalg.norm(rhs_array, ord=np.inf))
    denominator = max(matrix_scale * solution_scale + rhs_scale, np.finfo(float).tiny)
    relative_residual = absolute_residual / denominator
    diagnostics = LinearSolveDiagnostics(
        backend=factorization.backend_name,
        absolute_residual=absolute_residual,
        relative_residual=relative_residual,
        matrix_size=factorization.matrix.shape[0],
        nnz=int(np.count_nonzero(factorization.matrix)),
        reused_factorization=reused_factorization,
        factorization_count=factorization_count,
        solve_count=solve_count,
    )
    if absolute_residual > residual_atol and relative_residual > residual_rtol:
        raise LinearSolveError(
            f"{factorization.backend_name} 残差超限："
            f"absolute={absolute_residual:.3e}，relative={relative_residual:.3e}。"
        )
    return solution, diagnostics


class DenseLinearSolver:
    """基于 SciPy 稠密 LU 分解的线性求解器。

    每个时间步对当前 MNA 矩阵执行一次 LU 分解并求解右端项，同时检查残差、
    奇异矩阵和非有限数，保证仿真结果的数值可靠性。
    """

    name = "dense_numpy"

    def __init__(
        self,
        *,
        residual_rtol: float = DEFAULT_RESIDUAL_RTOL,
        residual_atol: float = DEFAULT_RESIDUAL_ATOL,
    ) -> None:
        self.residual_rtol = residual_rtol
        self.residual_atol = residual_atol
        self.factorization_count = 0
        self.solve_count = 0
        self.last_diagnostics: LinearSolveDiagnostics | None = None

    def factorize(self, matrix: MatrixInput) -> Factorization:
        """计算并返回一个可复用的稠密 LU 分解。"""

        matrix_array = np.asarray(matrix, dtype=float)
        _validate_square_finite_matrix(matrix_array)
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", LinAlgWarning)
                lu, pivots = lu_factor(matrix_array, check_finite=True)
        except (LinAlgWarning, ValueError) as exc:
            raise LinearSolveError("稠密 LU 分解失败，MNA 系数矩阵可能奇异。") from exc
        self.factorization_count += 1
        return _DenseLUFactorization(matrix=matrix_array.copy(), lu=lu, pivots=pivots)

    def solve(self, matrix: MatrixInput, rhs: np.ndarray) -> np.ndarray:
        """分解稠密矩阵、求解右端项并检查残差。"""

        factorization = self.factorize(matrix)
        self.solve_count += 1
        solution, diagnostics = _solve_factorization(
            factorization,
            rhs,
            residual_rtol=self.residual_rtol,
            residual_atol=self.residual_atol,
            reused_factorization=False,
            factorization_count=self.factorization_count,
            solve_count=self.solve_count,
        )
        self.last_diagnostics = diagnostics
        return solution
