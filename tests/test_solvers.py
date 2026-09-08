"""
文件名称：test_solvers.py
文件作用：验证稠密线性求解器的 LU 分解、残差诊断与数值安全行为。
"""

from __future__ import annotations

import numpy as np
import pytest

from pycy_emt_lite import Circuit, Resistor, SimulationConfig, Simulator, VoltageSource
from pycy_emt_lite.core.solvers import DenseLinearSolver, LinearSolveError


class _FailingSolver:
    name = "test_solver"

    def __init__(self, error: LinearSolveError) -> None:
        self.error = error

    def solve(self, matrix: np.ndarray, rhs: np.ndarray) -> np.ndarray:
        del matrix, rhs
        raise self.error


class _BrokenResistor(Resistor):
    def stamp(self, *args: object) -> None:
        del args
        raise ValueError("custom stamp failure")


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


@pytest.mark.parametrize(
    "reason",
    [
        "MNA 系数矩阵包含 NaN 或 Inf，无法进行 LU 分解。",
        "稠密 LU 分解失败，MNA 系数矩阵可能奇异。",
        "dense_scipy_lu 残差超限：absolute=1.000e+00，relative=1.000e+00。",
    ],
)
def test_simulator_preserves_linear_solve_reason_with_time_and_solver(reason: str) -> None:
    circuit = Circuit.from_components(
        "solver_context",
        [VoltageSource("V1", "n", "0", 1.0), Resistor("R1", "n", "0", 1.0)],
    )
    solver = _FailingSolver(LinearSolveError(reason))

    with pytest.raises(RuntimeError, match=r"仿真时间 0.*test_solver") as error:
        Simulator(circuit, SimulationConfig(time_step=1e-3, stop_time=0.0), solver=solver).run()

    assert reason in str(error.value)
    assert error.value.__cause__ is solver.error


def test_simulator_reports_component_name_and_time_when_stamp_fails() -> None:
    circuit = Circuit.from_components(
        "stamp_context",
        [VoltageSource("V1", "n", "0", 1.0), _BrokenResistor("R1", "n", "0", 1.0)],
    )

    with pytest.raises(RuntimeError, match=r"元件 'R1'.*仿真时间 0.*stamp") as error:
        Simulator(circuit, SimulationConfig(time_step=1e-3, stop_time=0.0)).run()

    assert isinstance(error.value.__cause__, ValueError)
    assert "custom stamp failure" in str(error.value.__cause__)
