"""
文件名称：test_solvers.py
文件作用：验证稠密线性求解器的 LU 分解、残差诊断与数值安全行为。
"""

from __future__ import annotations

import numpy as np
import pytest

from pycy_emt_lite.core.solvers import DenseLinearSolver, LinearSolveError


def test_dense_solver_reports_residual_diagnostics() -> None:
    """稠密求解结果应附带固定阈值下的残差诊断。"""

    matrix = np.array([[8.0, 2.0], [1.0, 5.0]])
    rhs = np.array([4.0, 7.0])
    solver = DenseLinearSolver()

    solution = solver.solve(matrix, rhs)

    assert solver.factorization_count == 1
    assert solver.solve_count == 1
    assert solver.last_diagnostics is not None
    assert solver.last_diagnostics.backend == "dense_scipy_lu"
    assert solver.last_diagnostics.absolute_residual <= 1e-12
    assert solver.last_diagnostics.relative_residual <= 1e-10
    assert solver.last_diagnostics.reused_factorization is False
    np.testing.assert_allclose(matrix @ solution, rhs)


def test_dense_solver_rejects_singular_matrix() -> None:
    """稠密 LU 后端应明确报告奇异矩阵。"""

    singular_matrix = np.array([[1.0, 2.0], [2.0, 4.0]])

    with pytest.raises(LinearSolveError, match="奇异"):
        DenseLinearSolver().solve(singular_matrix, np.ones(2))


def test_dense_solver_rejects_nonfinite_matrix_and_rhs() -> None:
    """矩阵或右端项中的非有限数应在分解或求解前失败。"""

    solver = DenseLinearSolver()

    with pytest.raises(LinearSolveError, match="NaN 或 Inf"):
        solver.solve(np.array([[np.nan, 0.0], [0.0, 1.0]]), np.ones(2))
    with pytest.raises(LinearSolveError, match="右端项包含 NaN 或 Inf"):
        solver.solve(np.eye(2), np.array([1.0, np.inf]))


def test_dense_solver_rejects_nonfinite_solution(monkeypatch: pytest.MonkeyPatch) -> None:
    """后端意外返回非有限解时必须失败，不能把污染结果传入仿真。"""

    def return_nonfinite_solution(
        factorization: tuple[np.ndarray, np.ndarray],
        rhs: np.ndarray,
        *,
        check_finite: bool,
    ) -> np.ndarray:
        del factorization, check_finite
        return np.full_like(rhs, np.inf)

    monkeypatch.setattr("pycy_emt_lite.core.solvers.lu_solve", return_nonfinite_solution)

    with pytest.raises(LinearSolveError, match="返回 NaN 或 Inf"):
        DenseLinearSolver().solve(np.eye(2), np.ones(2))
