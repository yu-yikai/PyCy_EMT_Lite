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
import math
from numbers import Real
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
        """求解 `matrix * x = rhs`；返回数组可只读或由求解器复用，调用者修改前须复制。"""


@dataclass(slots=True)
class _DenseLUFactorization:
    """保存稠密矩阵及其 LU 分解。"""

    matrix: np.ndarray
    lu: np.ndarray
    pivots: np.ndarray
    _solver: DenseLinearSolver
    backend_name: str = "dense_scipy_lu"

    def solve(self, rhs: np.ndarray) -> np.ndarray:
        """使用已缓存的稠密 LU 分解求解右端项。"""

        return self._solver._solve(self, rhs, reused=True, allow_multiple=True)

    def _solve_raw(self, rhs: np.ndarray) -> np.ndarray:
        return np.asarray(lu_solve((self.lu, self.pivots), rhs, check_finite=True), dtype=float)


def _validate_square_finite_matrix(matrix: np.ndarray) -> None:
    """检查矩阵形状和有限性。"""

    if len(matrix.shape) != 2 or matrix.shape[0] != matrix.shape[1] or matrix.shape[0] == 0:
        raise LinearSolveError("MNA 系数矩阵必须是方阵。")
    if not np.all(np.isfinite(matrix)):
        raise LinearSolveError("MNA 系数矩阵包含 NaN 或 Inf，无法进行 LU 分解。")


def _validate_rhs(rhs: np.ndarray, matrix_size: int, *, allow_multiple: bool = False) -> np.ndarray:
    """检查右端项维度和有限性。"""

    rhs_array = np.asarray(rhs, dtype=float)
    if (rhs_array.ndim not in ((1, 2) if allow_multiple else (1,))
            or rhs_array.shape[0] != matrix_size or rhs_array.size == 0):
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
    allow_multiple: bool = False,
) -> tuple[np.ndarray, LinearSolveDiagnostics]:
    """求解并验证残差，返回数值解和诊断。"""

    rhs_array = _validate_rhs(rhs, factorization.matrix.shape[0], allow_multiple=allow_multiple)
    try:
        solution = factorization._solve_raw(rhs_array) if isinstance(factorization, _DenseLUFactorization) else factorization.solve(rhs_array)
    except (ValueError, RuntimeError) as exc:
        raise LinearSolveError(f"{factorization.backend_name} 求解失败。") from exc
    if not np.all(np.isfinite(solution)):
        raise LinearSolveError(f"{factorization.backend_name} 返回 NaN 或 Inf。")
    if solution.shape != rhs_array.shape:
        raise LinearSolveError(f"{factorization.backend_name} 返回解的维度错误。")

    # 先缩放再乘/求和，避免有限输入在诊断中变为 Inf/Inf。
    a_scale = float(np.max(np.abs(factorization.matrix))) or 1.0
    x_scale = float(np.max(np.abs(solution))) or 1.0
    a = factorization.matrix / a_scale
    x = solution / x_scale
    with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
        b = rhs_array / a_scale / x_scale
        for original, scaled in ((factorization.matrix, a), (solution, x), (rhs_array, b)):
            if np.any((original != 0) & (scaled == 0)):
                raise LinearSolveError("残差诊断缩放下溢，非零量无法保留；请检查方程和数值尺度。")
        residual = a @ x - b
        residual_scale = float(np.linalg.norm(residual, ord=np.inf))
        denominator = float(np.linalg.norm(a, ord=np.inf) * np.linalg.norm(x, ord=np.inf) + np.linalg.norm(b, ord=np.inf))
    if not math.isfinite(residual_scale) or not math.isfinite(denominator):
        raise LinearSolveError("残差诊断缩放仍溢出；请检查方程和数值尺度。")
    relative_residual = residual_scale / denominator if denominator > 0 else 0.0
    try:
        mantissas, exponents = zip(*(math.frexp(v) for v in (residual_scale, a_scale, x_scale)))
        absolute_residual = math.ldexp(math.prod(mantissas), sum(exponents))
    except OverflowError as exc:
        raise LinearSolveError("绝对残差超出有限数范围，拒绝溢出的求解诊断。") from exc
    if not math.isfinite(absolute_residual) or not math.isfinite(relative_residual):
        raise LinearSolveError("残差诊断包含 NaN 或 Inf。")
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
    奇异矩阵和非有限数。这些检查衡量后向误差，不能保证病态系统的前向误差或
    由相近电压相减得到的电流精度；物理量还需要独立验收。
    """

    name = "dense_numpy"

    def __init__(
        self,
        *,
        residual_rtol: float = DEFAULT_RESIDUAL_RTOL,
        residual_atol: float = DEFAULT_RESIDUAL_ATOL,
    ) -> None:
        for parameter, value in (("residual_rtol", residual_rtol), ("residual_atol", residual_atol)):
            if isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(value) or value < 0:
                raise ValueError(f"{parameter} 必须为有限非负实数。")
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
        return _DenseLUFactorization(matrix=matrix_array.copy(), lu=lu, pivots=pivots, _solver=self)

    def solve(self, matrix: MatrixInput, rhs: np.ndarray) -> np.ndarray:
        """分解稠密矩阵、求解右端项并检查残差。"""

        factorization = self.factorize(matrix)
        return self._solve(factorization, rhs, reused=False)

    def _solve(self, factorization: Factorization, rhs: np.ndarray, *, reused: bool, allow_multiple: bool = False) -> np.ndarray:
        for parameter in ("residual_rtol", "residual_atol"):
            value = getattr(self, parameter)
            if isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(value) or value < 0:
                raise ValueError(f"{parameter} 必须为有限非负实数。")
        self.solve_count += 1
        solution, diagnostics = _solve_factorization(
            factorization,
            rhs,
            residual_rtol=self.residual_rtol,
            residual_atol=self.residual_atol,
            reused_factorization=reused,
            factorization_count=self.factorization_count,
            solve_count=self.solve_count,
            allow_multiple=allow_multiple,
        )
        self.last_diagnostics = diagnostics
        return solution
