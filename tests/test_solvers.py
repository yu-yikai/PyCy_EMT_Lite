"""
文件名称：test_solvers.py
文件作用：验证稠密线性求解器的 LU 分解、残差诊断与数值安全行为。
"""

from __future__ import annotations

import numpy as np
import pytest

from pycy_emt_lite import Circuit, CurrentSource, Resistor, SimulationConfig, Simulator, VoltageSource
from pycy_emt_lite.core.solvers import DenseLinearSolver, LinearSolveError


@pytest.mark.parametrize("mode", ["precompute", "inverse", "", None, True, 0, ["reuse"]])
def test_network_solver_mode_rejects_unsupported_values(mode) -> None:
    with pytest.raises(ValueError, match="linear_solver_mode.*rebuild.*reuse"):
        SimulationConfig(.1, .2, linear_solver_mode=mode)


@pytest.mark.parametrize("mode,expected_factors", [("rebuild", 4), ("reuse", 1)])
def test_network_solver_updates_rhs_and_reports_actual_reuse(mode, expected_factors) -> None:
    calls, diagnostics = [], []
    def current(time):
        calls.append(time)
        return 1.0 + time
    solver = DenseLinearSolver(residual_rtol=1e-12, residual_atol=1e-14)
    def observe(row):
        diagnostics.append(solver.last_diagnostics)
        return {}
    circuit = Circuit.from_components("changing_rhs", [
        CurrentSource("I", "0", "n", current), Resistor("R", "n", "0", 2.0),
    ])
    # 默认配置必须保持逐次分解。
    config = SimulationConfig(.1, .3) if mode == "rebuild" else SimulationConfig(.1, .3, linear_solver_mode=mode)
    assert config.linear_solver_mode == mode
    simulator = Simulator(circuit, config, solver=solver, on_step=observe)
    result = simulator.run()
    np.testing.assert_array_equal(result.series("v:n"), 2 * (1 + result.series("time")))
    assert calls == list(result.series("time"))  # 查缓存不额外调用源或回调。
    assert solver.factorization_count == expected_factors and solver.solve_count == 4
    assert [d.reused_factorization for d in diagnostics] == [False] + [mode == "reuse"] * 3
    assert [d.solve_count for d in diagnostics] == [1, 2, 3, 4]
    with pytest.raises(RuntimeError, match="只能运行一次"):
        simulator.run()
    with pytest.raises(RuntimeError, match="只能运行一次"):
        Simulator(circuit, config).run()


def test_network_solver_reuse_refactors_parameter_changes_and_revisited_matrix() -> None:
    resistor = Resistor("R", "n", "0", 1.0)
    solver = DenseLinearSolver()
    def change(row):
        resistor.resistance = 2.0 if row["time"] == 0.0 else 1.0
        return {}
    result = Simulator(Circuit.from_components("parameter_change", [
        resistor, CurrentSource("I", "0", "n", 1.0),
    ]), SimulationConfig(.1, .3, linear_solver_mode="reuse"), solver=solver, on_step=change).run()
    np.testing.assert_array_equal(result.series("v:n"), [1., 2., 1., 1.])
    assert solver.factorization_count == 3  # A1→A2→A1，只有上一份分解可复用。
    assert solver.solve_count == 4 and solver.last_diagnostics.reused_factorization


def test_network_solver_reuse_does_not_round_small_matrix_changes() -> None:
    resistor = Resistor("R", "n", "0", 1.0)
    changed = np.nextafter(1.0, 2.0)
    def change(row):
        resistor.resistance = changed
        return {}
    simulator = Simulator(Circuit.from_components("small_change", [
        resistor, CurrentSource("I", "0", "n", 1.0),
    ]), SimulationConfig(.1, .1, linear_solver_mode="reuse"), on_step=change)
    result = simulator.run()
    assert result.rows[1]["v:n"] == changed
    assert simulator.solver.factorization_count == 2
    assert not simulator.solver.last_diagnostics.reused_factorization


def test_network_solver_cache_belongs_to_one_simulator() -> None:
    solver = DenseLinearSolver()
    for name in ("first", "second"):
        result = Simulator(Circuit.from_components(name, [
            CurrentSource("I", "0", "n", 1.0), Resistor("R", "n", "0", 2.0),
        ]), SimulationConfig(.1, .1, linear_solver_mode="reuse"), solver=solver).run()
        np.testing.assert_array_equal(result.series("v:n"), [2., 2.])
    assert solver.factorization_count == 2 and solver.solve_count == 4


def test_network_solver_reuse_rejects_custom_backend_before_claiming_circuit() -> None:
    solver = _FailingSolver(LinearSolveError("must not run"))
    circuit = Circuit.from_components("custom_backend", [Resistor("R", "n", "0", 1.0)])
    with pytest.raises(ValueError, match="reuse.*DenseLinearSolver.*rebuild"):
        Simulator(circuit, SimulationConfig(.1, .1, linear_solver_mode="reuse"), solver=solver)
    assert not circuit.prepared
    # 拒绝新增模式后，同一电路仍可使用已有自定义求解路径，原异常链不变。
    with pytest.raises(RuntimeError) as caught:
        Simulator(circuit, SimulationConfig(.1, .1), solver=solver).run()
    assert caught.value.__cause__ is solver.error


@pytest.mark.parametrize("fault,reason", [("zero", "残差"), ("nonfinite", "NaN 或 Inf"), ("shape", "维度")])
def test_network_solver_cache_hits_keep_backend_checks(monkeypatch, fault, reason) -> None:
    from pycy_emt_lite.core import solvers
    original = solvers.lu_solve
    calls = 0
    def solve(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            return original(*args, **kwargs)
        return np.full(1, np.inf) if fault == "nonfinite" else np.zeros((1, 1)) if fault == "shape" else np.zeros(1)
    monkeypatch.setattr(solvers, "lu_solve", solve)
    simulator = Simulator(Circuit.from_components("backend_check", [
        Resistor("R", "n", "0", 1.0), CurrentSource("I", "0", "n", 1.0),
    ]), SimulationConfig(.1, .1, linear_solver_mode="reuse"))
    with pytest.raises(RuntimeError, match=rf"仿真时间 0.1.*{reason}") as caught:
        simulator.run()
    assert isinstance(caught.value.__cause__, LinearSolveError)
    assert calls == 2 and simulator.solver.factorization_count == 1


@pytest.mark.parametrize("fault,reason", [("matrix", "NaN 或 Inf"), ("singular", "奇异"),
                                         ("rhs", "右端项.*NaN 或 Inf"), ("rhs_shape", "右端项维度")])
def test_network_solver_reuse_rejects_invalid_next_equation(fault, reason) -> None:
    class BadEquation(Resistor):
        def stamp(self, context, matrix, rhs):
            super().stamp(context, matrix, rhs)
            if context.time > 0:
                if fault in {"matrix", "singular"}:
                    matrix[:] = np.nan if fault == "matrix" else 0.0
                elif fault == "rhs":
                    rhs[:] = np.nan
                else:
                    rhs.resize((1, 1), refcheck=False)
    simulator = Simulator(Circuit.from_components("bad_equation", [
        CurrentSource("I", "0", "n", 1.0), BadEquation("R", "n", "0", 1.0),
    ]), SimulationConfig(.1, .1, linear_solver_mode="reuse"))
    with pytest.raises(RuntimeError, match=rf"仿真时间 0.1.*{reason}"):
        simulator.run()


def test_network_solver_reuse_keeps_runtime_residual_threshold_validation() -> None:
    solver = DenseLinearSolver()
    def change(row):
        solver.residual_rtol = np.nan
        return {}
    simulator = Simulator(Circuit.from_components("changed_tolerance", [
        CurrentSource("I", "0", "n", 1.0), Resistor("R", "n", "0", 1.0),
    ]), SimulationConfig(.1, .1, linear_solver_mode="reuse"), solver=solver, on_step=change)
    with pytest.raises(RuntimeError, match="仿真时间 0.1.*residual_rtol"):
        simulator.run()
    assert solver.factorization_count == 1


@pytest.mark.parametrize("storage", ["readonly", "shared"])
def test_network_solver_reuse_initial_correction_preserves_ownership(monkeypatch, storage) -> None:
    from pycy_emt_lite import Capacitor
    from pycy_emt_lite.core import solvers
    original = solvers.lu_solve
    returned, snapshots, lu_snapshots = [], [], []
    buffer = None
    def solve(factors, rhs, **kwargs):
        nonlocal buffer
        lu_snapshots.append(factors[0].copy())
        values = original(factors, rhs, **kwargs)
        if not returned:
            values[1] += 1e-5  # 原全局残差允许，但电容初值约束要求一次修正。
        if storage == "readonly":
            values.setflags(write=False)
        else:
            if buffer is None:
                buffer = np.empty_like(values)
            buffer[:] = values
            values = buffer
        returned.append(values)
        snapshots.append(values.copy())
        return values
    monkeypatch.setattr(solvers, "lu_solve", solve)
    simulator = Simulator(Circuit.from_components("reuse_correction", [
        VoltageSource("V", "s", "0", 1e6), Resistor("R", "s", "c", 1.0),
        Capacitor("C", "c", "0", 1.0, initial_voltage=.25),
    ]), SimulationConfig(1e-4, 0.0, linear_solver_mode="reuse"))
    result = simulator.run()
    assert simulator.solver.factorization_count == 1 and simulator.solver.solve_count == 2
    assert simulator.solver.last_diagnostics.reused_factorization
    assert result.rows[0]["v:c"] == pytest.approx(.25, abs=1e-12)
    assert result.rows[0]["i:C"] == pytest.approx(1e6 - .25, rel=1e-12)
    np.testing.assert_array_equal(lu_snapshots[0], lu_snapshots[1])
    np.testing.assert_array_equal(returned[0] if storage == "readonly" else buffer,
                                  snapshots[0] if storage == "readonly" else snapshots[-1])


def test_network_solver_mode_reaches_simulator_through_run_case(monkeypatch) -> None:
    from pycy_emt_lite.cases import CaseDefinition, run_case
    original = DenseLinearSolver.factorize
    matrices = []
    def factorize(self, matrix):
        matrices.append(matrix.copy())
        return original(self, matrix)
    monkeypatch.setattr(DenseLinearSolver, "factorize", factorize)
    result = run_case(CaseDefinition("case_reuse", (
        CurrentSource("I", "0", "n", 1.0), Resistor("R", "n", "0", 2.0),
    ), SimulationConfig(.1, .2, linear_solver_mode="reuse")))
    np.testing.assert_array_equal(result.series("v:n"), [2., 2., 2.])
    assert len(matrices) == 1


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


@pytest.mark.parametrize("storage", ["owned", "readonly", "shared"])
def test_initial_correction_preserves_solver_array_ownership(storage) -> None:
    from pycy_emt_lite import Capacitor

    class BufferedSolver:
        name = "buffered_solver"

        def __init__(self):
            self.backend = DenseLinearSolver()
            self.returned, self.snapshots = [], []
            self.buffer = None

        def solve(self, matrix, rhs):
            values = self.backend.solve(matrix, rhs)
            if not self.returned:
                values[1] += 1e-5  # 全局残差很小，但破坏0.25V电容的逐行初值约束。
            if storage == "shared":
                if self.buffer is None:
                    self.buffer = np.empty_like(values)
                self.buffer[:] = values
                values = self.buffer
            elif storage == "readonly":
                values.setflags(write=False)
            self.returned.append(values)
            self.snapshots.append(values.copy())
            return values

    solver = BufferedSolver()
    circuit = Circuit.from_components("initial_ownership", [
        VoltageSource("V", "s", "0", 1e6), Resistor("R", "s", "c", 1.0),
        Capacitor("C", "c", "0", 1.0, initial_voltage=0.25),
    ])
    result = Simulator(circuit, SimulationConfig(1e-4, 0.0), solver=solver).run()
    assert len(solver.returned) == 2  # 确实触发修正，而非仅验证普通求解。
    assert result.rows[0]["v:c"] == pytest.approx(0.25, abs=1e-12)
    assert result.rows[0]["i:C"] == pytest.approx(1e6 - 0.25, rel=1e-12)
    if storage == "shared":
        np.testing.assert_array_equal(solver.buffer, solver.snapshots[-1])
    else:
        np.testing.assert_array_equal(solver.returned[0], solver.snapshots[0])


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
