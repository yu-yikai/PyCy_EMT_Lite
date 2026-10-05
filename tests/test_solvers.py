"""
文件名称：test_solvers.py
文件作用：验证稠密线性求解器的 LU 分解、残差诊断与数值安全行为。
"""

from __future__ import annotations

import numpy as np
import pytest

from pycy_emt_lite import Circuit, Resistor, SimulationConfig, Simulator, VoltageSource
from pycy_emt_lite.core.solvers import DenseLinearSolver, LinearSolveError


@pytest.mark.parametrize("value", [np.nan, np.inf, -1.0, True, "1e-10"])
@pytest.mark.parametrize("parameter", ["residual_rtol", "residual_atol"])
def test_solver_rejects_invalid_residual_thresholds(parameter, value) -> None:
    with pytest.raises(ValueError, match=parameter):
        DenseLinearSolver(**{parameter: value})


@pytest.mark.parametrize("reuse", [False, True])
@pytest.mark.parametrize("fault", ["zero", "nonfinite", "overflow"])
def test_both_solver_entries_reject_invalid_backend_results(monkeypatch, reuse, fault) -> None:
    matrix = np.array([[1e308, 1e308], [1e308, -0.5e308]]) if fault == "overflow" else np.eye(2)
    bad = np.full(2, np.inf) if fault == "nonfinite" else np.ones(2) if fault == "overflow" else np.zeros(2)
    monkeypatch.setattr("pycy_emt_lite.core.solvers.lu_solve", lambda *args, **kwargs: bad.copy())
    solver = DenseLinearSolver()
    with pytest.raises(LinearSolveError):
        solver.factorize(matrix).solve(np.ones(2)) if reuse else solver.solve(matrix, np.ones(2))


@pytest.mark.parametrize("reuse", [False, True])
def test_residual_scaling_does_not_erase_small_matrix_coefficients(monkeypatch, reuse) -> None:
    from pycy_emt_lite.core import solvers

    # 非奇异矩阵；全局缩放会把 1e-100 / 1e300 变成零，掩盖第三行 1e200 的实际误差。
    matrix = np.array([[1e300, 1e300, 0.0], [1e300, 1e300, 1.0], [0.0, 1e-100, 1.0]])
    monkeypatch.setattr(solvers, "lu_solve", lambda *args, **kwargs: np.array([1e300, -1e300, 0.0]))
    solver = DenseLinearSolver()
    with pytest.raises(LinearSolveError, match="尺度|缩放|残差"):
        if reuse:
            solver.factorize(matrix).solve(np.zeros(3))
        else:
            solver.solve(matrix, np.zeros(3))


def test_factorized_entry_preserves_multiple_rhs_and_diagnostics() -> None:
    solver = DenseLinearSolver()
    matrix = np.array([[3.0, 1.0], [1.0, 2.0]])
    rhs = np.array([[1.0, 2.0], [3.0, 4.0]])
    factorization = solver.factorize(matrix)
    np.testing.assert_allclose(matrix @ factorization.solve(rhs), rhs, rtol=1e-14, atol=1e-14)
    assert solver.factorization_count == 1 and solver.solve_count == 1
    assert solver.last_diagnostics.reused_factorization
    with pytest.raises(LinearSolveError, match="维度"):
        factorization.solve(np.ones(3))


@pytest.mark.parametrize("stage", ["update_state", "outputs", "on_step"])
def test_other_simulation_failures_preserve_stage_time_and_cause(stage) -> None:
    error = LookupError("original failure")
    def fail(*args):
        raise error
    resistor = Resistor("R", "in", "0", 1.0)
    if stage != "on_step":
        class Broken(Resistor):
            pass
        setattr(Broken, stage, fail)
        resistor = Broken("R", "in", "0", 1.0)
    circuit = Circuit.from_components("context", [VoltageSource("V", "in", "0", 1.0), resistor])
    with pytest.raises(RuntimeError, match=rf"(?:R|context).*时间 0.*{stage}") as caught:
        Simulator(circuit, SimulationConfig(.1, .1), on_step=fail if stage == "on_step" else None).run()
    assert caught.value.__cause__ is error


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
