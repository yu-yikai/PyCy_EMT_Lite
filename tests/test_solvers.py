"""
文件名称：test_solvers.py
文件作用：验证稠密线性求解器的 LU 分解、残差诊断与数值安全行为。
"""

from __future__ import annotations

import numpy as np
import pytest

from pycy_emt_lite import (
    Breaker, BreakerCloseEvent, BreakerOpenEvent, Capacitor, Circuit, CurrentSource,
    Fault, FaultApplyEvent, FaultClearEvent, IdealSwitch, Inductor, Resistor,
    SimulationConfig, Simulator, VoltageSource,
)
from pycy_emt_lite.core.solvers import DenseLinearSolver, LinearSolveError


@pytest.mark.parametrize("mode", ["PRECOMPUTE", "inverse", "", None, True, 0, ["reuse"]])
def test_network_solver_mode_rejects_unsupported_values(mode) -> None:
    with pytest.raises(ValueError, match="linear_solver_mode.*rebuild.*reuse"):
        SimulationConfig(.1, .2, linear_solver_mode=mode)


@pytest.mark.parametrize("mode,expected_factors", [("rebuild", 4), ("reuse", 1), ("precompute", 1)])
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
    assert [d.reused_factorization for d in diagnostics] == [mode == "precompute"] + [mode != "rebuild"] * 3
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


@pytest.mark.parametrize("mode", ["reuse", "precompute"])
def test_network_solver_reuse_rejects_custom_backend_before_claiming_circuit(mode) -> None:
    solver = _FailingSolver(LinearSolveError("must not run"))
    circuit = Circuit.from_components("custom_backend", [Resistor("R", "n", "0", 1.0)])
    with pytest.raises(ValueError, match=f"{mode}.*DenseLinearSolver.*rebuild"):
        Simulator(circuit, SimulationConfig(.1, .1, linear_solver_mode=mode), solver=solver)
    assert not circuit.prepared
    # 拒绝新增模式后，同一电路仍可使用已有自定义求解路径，原异常链不变。
    with pytest.raises(RuntimeError) as caught:
        Simulator(circuit, SimulationConfig(.1, .1), solver=solver).run()
    assert caught.value.__cause__ is solver.error


@pytest.mark.parametrize("fault,reason", [("zero", "残差"), ("nonfinite", "NaN 或 Inf"), ("shape", "维度")])
@pytest.mark.parametrize("mode", ["reuse", "precompute"])
def test_network_solver_cache_hits_keep_backend_checks(monkeypatch, fault, reason, mode) -> None:
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
    ]), SimulationConfig(.1, .1, linear_solver_mode=mode))
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


@pytest.mark.parametrize("mode", ["reuse", "precompute"])
def test_network_solver_reuse_keeps_runtime_residual_threshold_validation(mode) -> None:
    solver = DenseLinearSolver()
    def change(row):
        solver.residual_rtol = np.nan
        return {}
    simulator = Simulator(Circuit.from_components("changed_tolerance", [
        CurrentSource("I", "0", "n", 1.0), Resistor("R", "n", "0", 1.0),
    ]), SimulationConfig(.1, .1, linear_solver_mode=mode), solver=solver, on_step=change)
    with pytest.raises(RuntimeError, match="仿真时间 0.1.*residual_rtol"):
        simulator.run()
    assert solver.factorization_count == 1


@pytest.mark.parametrize("storage", ["readonly", "shared"])
@pytest.mark.parametrize("mode", ["reuse", "precompute"])
def test_network_solver_reuse_initial_correction_preserves_ownership(monkeypatch, storage, mode) -> None:
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
    ]), SimulationConfig(1e-4, 0.0, linear_solver_mode=mode))
    result = simulator.run()
    assert simulator.solver.factorization_count == 1 and simulator.solver.solve_count == 2
    assert simulator.solver.last_diagnostics.reused_factorization
    assert result.rows[0]["v:c"] == pytest.approx(.25, abs=1e-12)
    assert result.rows[0]["i:C"] == pytest.approx(1e6 - .25, rel=1e-12)
    np.testing.assert_array_equal(lu_snapshots[0], lu_snapshots[1])
    np.testing.assert_array_equal(returned[0] if storage == "readonly" else buffer,
                                  snapshots[0] if storage == "readonly" else snapshots[-1])


@pytest.mark.parametrize("mode", ["reuse", "precompute"])
def test_network_solver_mode_reaches_simulator_through_run_case(monkeypatch, mode) -> None:
    from pycy_emt_lite.cases import CaseDefinition, run_case
    original = DenseLinearSolver.factorize
    matrices = []
    def factorize(self, matrix):
        matrices.append(matrix.copy())
        return original(self, matrix)
    monkeypatch.setattr(DenseLinearSolver, "factorize", factorize)
    result = run_case(CaseDefinition("case_reuse", (
        CurrentSource("I", "0", "n", 1.0), Resistor("R", "n", "0", 2.0),
    ), SimulationConfig(.1, .2, linear_solver_mode=mode)))
    np.testing.assert_array_equal(result.series("v:n"), [2., 2., 2.])
    assert len(matrices) == 1


def test_precompute_revisited_switch_states_are_ready_before_real_stamps(monkeypatch) -> None:
    original = DenseLinearSolver.factorize
    results, counts = [], []
    for mode in ("rebuild", "reuse", "precompute"):
        calls, seen_counts = [], []
        def gate(time):
            calls.append(time)
            return .1 <= time < .2
        solver = DenseLinearSolver()
        def factorize(self, matrix):
            if mode == "precompute":
                assert calls == []  # 只对隔离副本预分解，真实门极还没有被调用。
            return original(self, matrix)
        monkeypatch.setattr(DenseLinearSolver, "factorize", factorize)
        def observe(row):
            seen_counts.append(solver.factorization_count)
            return {}
        result = Simulator(Circuit.from_components("revisited", [
            CurrentSource("I", "0", "n", 1.0), Resistor("R", "n", "0", 2.0),
            IdealSwitch("S", "n", "0", gate, closed_resistance=1.0, open_conductance=0.0),
        ]), SimulationConfig(.1, .3, linear_solver_mode=mode), solver=solver, on_step=observe).run()
        assert calls == list(result.series("time"))
        if mode == "precompute":
            assert seen_counts == [2, 2, 2, 2]
        results.append(result.rows)
        counts.append(solver.factorization_count)
    assert results[0] == results[1] == results[2]
    assert counts == [4, 3, 2]  # A1→A2→A1，预分解两份，循环内不新增 LU。


@pytest.mark.parametrize("method", ["trapezoidal", "backward_euler"])
@pytest.mark.parametrize("policy", ["insert", "quantize_up", "require_aligned"])
def test_precompute_switched_rlc_matches_all_rows_events_and_call_counts(method, policy, monkeypatch) -> None:
    original = DenseLinearSolver.factorize
    results, traces = [], []
    for mode in ("rebuild", "reuse", "precompute"):
        calls, counts = [], []
        apply_time, clear_time = (.1, .2) if policy == "require_aligned" else (.075, .15)
        def current(time):
            calls.append(("source", time))
            return 1.0 + time
        def gate(time):
            calls.append(("gate", time))
            return apply_time <= time < clear_time
        capacitor = Capacitor("C", "n", "0", .2, initial_voltage=.3)
        inductor = Inductor("L", "n", "0", .5, initial_current=.1)
        def factorize(self, matrix):
            if mode == "precompute":
                assert calls == []
                assert (capacitor.previous_voltage, inductor.previous_current) == (.3, .1)
            return original(self, matrix)
        monkeypatch.setattr(DenseLinearSolver, "factorize", factorize)
        solver = DenseLinearSolver()
        def observe(row):
            counts.append(solver.factorization_count)
            return {}
        simulator = Simulator(Circuit.from_components("switched_rlc", [
            CurrentSource("I", "0", "n", current), Resistor("R", "n", "0", 2.0),
            capacitor, inductor, Fault("F", "n", 3.0),
            Breaker("B", "n", "0", closed_resistance=4.0),
            IdealSwitch("S", "n", "0", gate, closed_resistance=5.0, open_conductance=0.0),
        ]), SimulationConfig(.1, .3, method=method, linear_solver_mode=mode, event_time_policy=policy), events=[
            FaultApplyEvent(apply_time, "F"), BreakerOpenEvent(apply_time, "B"),
            FaultClearEvent(clear_time, "F"), BreakerCloseEvent(clear_time, "B"),
        ], solver=solver, on_step=observe)
        result = simulator.run()
        if mode == "precompute":
            assert len(set(counts)) == 1 and counts[0] > 8
            assert len(simulator._precomputed) == 8 * (1 + len({
                simulator._effective_time_step(float(h)) for h in np.diff(result.series("time"))
            }))
            assert solver.last_diagnostics.reused_factorization
        assert solver.solve_count == len(result.rows) + 2  # 两个同刻多事件各只求一次右侧。
        results.append((result.rows, result.event_log))
        traces.append(calls)
    assert results[0] == results[1] == results[2]
    assert traces[0] == traces[1] == traces[2]


def test_precompute_dependent_initial_constraints_do_not_call_real_source_or_derivative(monkeypatch) -> None:
    original = DenseLinearSolver.factorize
    outputs, traces = [], []
    for mode in ("rebuild", "precompute"):
        calls = []
        def voltage(time):
            calls.append(("source", time))
            return 1.0 + time
        def derivative(time):
            calls.append(("derivative", time))
            return 1.0
        capacitor = Capacitor("C", "n", "0", .2, initial_voltage=1.0)
        def factorize(self, matrix):
            if mode == "precompute":
                assert calls == [] and capacitor.previous_voltage == 1.0
            return original(self, matrix)
        monkeypatch.setattr(DenseLinearSolver, "factorize", factorize)
        result = Simulator(Circuit.from_components("source_derivative", [
            VoltageSource("V", "n", "0", voltage, derivative=derivative), capacitor,
            Fault("F", "n", 2.0),
        ]), SimulationConfig(.1, .2, method="backward_euler", linear_solver_mode=mode),
            [FaultApplyEvent(.1, "F"), FaultClearEvent(.2, "F")]).run()
        assert sum(call[0] == "derivative" for call in calls) == 3
        outputs.append((result.rows, result.event_log))
        traces.append(calls)
    assert outputs[0] == outputs[1] and traces[0] == traces[1]


@pytest.mark.parametrize("value", [0, -1, True, 1.5, "2", None])
def test_precompute_state_limit_is_positive_integer(value) -> None:
    with pytest.raises(ValueError, match="precompute_max_states.*正整数"):
        SimulationConfig(.1, .1, linear_solver_mode="precompute", precompute_max_states=value)


@pytest.mark.parametrize("states,reason", [
    ([], "非空"), ({"S": False}, "列表或元组"), ([False], "映射"),
    ([{}], "名称"), ([{"unknown": False}], "名称"), ([{"S": 0}], "布尔"),
    ([{"S": False}, {"S": False}], "重复"),
])
def test_precompute_rejects_invalid_declared_states(states, reason) -> None:
    simulator = None
    with pytest.raises(ValueError, match=f"precompute_states.*{reason}"):
        simulator = Simulator(Circuit.from_components("bad_states", [
            Resistor("R", "n", "0", 1.0), IdealSwitch("S", "n", "0"),
        ]), SimulationConfig(.1, .1, linear_solver_mode="precompute", precompute_states=states))
        simulator.run()
    if simulator is not None:
        assert simulator.solver.factorization_count == 0 and simulator.last_time is None


@pytest.mark.parametrize("explicit", [False, True])
def test_precompute_bounds_state_count_before_factorization(explicit) -> None:
    with pytest.raises(ValueError, match="precompute.*状态.*2.*1.*reuse"):
        simulator = Simulator(Circuit.from_components("too_many_states", [
            Resistor("R", "n", "0", 1.0), IdealSwitch("S", "n", "0"),
        ]), SimulationConfig(.1, .1, linear_solver_mode="precompute", precompute_max_states=1,
                            precompute_states=[{"S": False}, {"S": True}] if explicit else None))
        simulator.run()


def test_precompute_bounds_numeric_memory_before_allocation(monkeypatch) -> None:
    from pycy_emt_lite.core import simulation
    monkeypatch.setattr(simulation, "_PRECOMPUTE_MAX_BYTES", 1)
    simulator = Simulator(Circuit.from_components("budget", [Resistor("R", "n", "0", 1.0)]),
                          SimulationConfig(.1, .1, linear_solver_mode="precompute"))
    with pytest.raises(ValueError, match="precompute.*字节.*reuse"):
        simulator.run()
    assert simulator.last_time is None and simulator.solver.factorization_count == 0


def test_precompute_singular_state_rejected_before_events_sources_or_gates() -> None:
    calls = []
    def gate(time):
        calls.append(time)
        return True
    simulator = Simulator(Circuit.from_components("singular_family", [
        CurrentSource("I", "0", "n", lambda time: calls.append(time) or 1.0),
        IdealSwitch("S", "n", "0", gate, open_conductance=0.0), Fault("F", "n", 1.0),
    ]), SimulationConfig(.1, .1, linear_solver_mode="precompute"), [FaultApplyEvent(0.0, "F")])
    with pytest.raises(ValueError, match="precompute.*S.*F.*奇异|precompute.*S.*F.*欠定"):
        simulator.run()
    assert calls == [] and simulator.event_log == [] and simulator.last_time is None
    assert simulator.solver.solve_count == 0


def test_precompute_explicit_state_family_is_snapshotted_and_has_no_lazy_fallback() -> None:
    declared = [{"S": False}]
    switch = IdealSwitch("S", "n", "0", False, closed_resistance=1.0, open_conductance=0.0)
    def change(row):
        switch.closed = True
        return {}
    simulator = Simulator(Circuit.from_components("snapshot", [
        Resistor("R", "n", "0", 1.0), switch, CurrentSource("I", "0", "n", 1.0),
    ]), SimulationConfig(.1, .1, linear_solver_mode="precompute", precompute_states=declared), on_step=change)
    declared[0]["S"] = True
    declared.append({"S": False})
    with pytest.raises(RuntimeError, match="仿真时间 0.1.*precompute.*未声明.*S"):
        simulator.run()
    assert simulator.last_time == 0.0 and simulator.solver.factorization_count == 1
    assert simulator.solver.solve_count == 1


def test_precompute_explicit_family_can_exclude_unreachable_singular_states() -> None:
    result = Simulator(Circuit.from_components("closed_only", [
        CurrentSource("I", "0", "n", 1.0), Breaker("B", "n", "0", closed_resistance=2.0),
    ]), SimulationConfig(.1, .1, linear_solver_mode="precompute", precompute_states=[{"B": True}]),
        [BreakerCloseEvent(0.0, "B")]).run()
    np.testing.assert_array_equal(result.series("v:n"), [2., 2.])


def test_precompute_rejects_new_coefficients_before_stale_solve() -> None:
    resistor = Resistor("R", "n", "0", 1.0)
    def change(row):
        resistor.resistance = np.nextafter(1.0, 2.0)
        return {}
    simulator = Simulator(Circuit.from_components("new_coefficient", [
        resistor, CurrentSource("I", "0", "n", 1.0),
    ]), SimulationConfig(.1, .1, linear_solver_mode="precompute"), on_step=change)
    with pytest.raises(RuntimeError, match="仿真时间 0.1.*precompute.*矩阵.*改变.*reuse"):
        simulator.run()
    assert simulator.solver.factorization_count == 1 and simulator.solver.solve_count == 1


def test_precompute_rejects_undeclared_step_without_factorizing(monkeypatch) -> None:
    calls = []
    simulator = Simulator(Circuit.from_components("new_step", [
        Resistor("R", "n", "0", 1.0),
        CurrentSource("I", "0", "n", lambda time: calls.append(time) or 1.0),
    ]), SimulationConfig(.1, .1, linear_solver_mode="precompute"))
    original = simulator._effective_time_step
    # 模拟运行时出现一个未在准备网格中的 h；即使纯电阻的 A 相同也必须拒绝。
    monkeypatch.setattr(simulator, "_effective_time_step", lambda h: .05 if calls else original(h))
    with pytest.raises(RuntimeError, match="仿真时间 0.1.*precompute.*未声明.*h=0.05"):
        simulator.run()
    assert simulator.solver.factorization_count == 1 and simulator.solver.solve_count == 1


def test_precompute_rejects_custom_component_before_claiming_or_stamping() -> None:
    class Custom(Resistor):
        def stamp(self, *args):
            pytest.fail("unsupported stamp must not be called")
    circuit = Circuit.from_components("unsupported", [Custom("R", "n", "0", 1.0)])
    simulator = Simulator(circuit, SimulationConfig(.1, .1, linear_solver_mode="precompute"))
    with pytest.raises(ValueError, match="precompute.*R.*Custom.*reuse"):
        simulator.run()
    assert not circuit.prepared and not circuit._run_claimed and simulator.last_time is None


@pytest.mark.parametrize("fault,reason", [("conflict", "初值.*冲突"), ("derivative", "需要 derivative"),
                                         ("nonfinite", "有限实数")])
def test_precompute_keeps_real_source_and_initial_constraint_checks(fault, reason) -> None:
    simulator = Simulator(Circuit.from_components("real_constraints", [
        VoltageSource("V", "n", "0", lambda time: np.nan if fault == "nonfinite" else 1.0),
        Capacitor("C", "n", "0", 1.0, initial_voltage=0.0 if fault == "conflict" else 1.0),
    ]), SimulationConfig(.1, 0.0, linear_solver_mode="precompute"))
    with pytest.raises(RuntimeError, match=reason):
        simulator.run()
    assert simulator.solver.factorization_count == 1 and simulator.solver.solve_count == 0


@pytest.mark.parametrize("method", ["trapezoidal", "backward_euler"])
@pytest.mark.parametrize("connections", [("Y", "Y"), ("Y", "D"), ("D", "Y"), ("D", "D")])
def test_precompute_three_phase_composites_match_events_and_preserve_original_history(method, connections, monkeypatch):
    from pycy_emt_lite.components.three_phase import ThreePhaseLine, ThreePhaseSource
    from pycy_emt_lite.components.transformers import ThreePhaseTransformer
    original = DenseLinearSolver.factorize
    results = []
    for mode in ("rebuild", "reuse", "precompute"):
        source = ThreePhaseSource("V", "src", 10.0, frequency=5.0)
        line = ThreePhaseLine("Z", "src", "pri", 1.0, .01)
        transformer = ThreePhaseTransformer("T", "pri", "sec", 2.0,
            primary_connection=connections[0], secondary_connection=connections[1],
            leakage_resistance=.5, leakage_inductance=.02,
            magnetizing_inductance=.1, core_loss_resistance=100.0)
        counts = []
        def factorize(self, matrix):
            if mode == "precompute":
                assert counts == []
                assert source.phase_rms == 10.0
                assert all(value == 0.0 for value in line.state.previous_current.values())
                assert all(state.magnetizing_flux == 0.0 for state in transformer.states.values())
            return original(self, matrix)
        monkeypatch.setattr(DenseLinearSolver, "factorize", factorize)
        solver = DenseLinearSolver()
        def observe(row):
            counts.append(solver.factorization_count)
            return {}
        components = [source, line, transformer, Fault("F", "sec:a", 2.0),
                      *(Resistor(f"R:{p}", f"sec:{p}", "0", 10.0) for p in "abc")]
        result = Simulator(Circuit.from_components("three_phase_precompute", components),
            SimulationConfig(.01, .03, method=method, linear_solver_mode=mode),
            [FaultApplyEvent(.015, "F"), FaultClearEvent(.02, "F")], solver=solver, on_step=observe).run()
        if mode == "precompute":
            assert len(set(counts)) == 1
        results.append((result.rows, result.event_log))
    assert results[0] == results[1] == results[2]


def test_precompute_three_phase_source_keeps_real_dependent_derivative():
    from pycy_emt_lite.components.three_phase import ThreePhaseSource
    amplitude = 10.0 * np.sqrt(2.0)
    results = []
    for mode in ("rebuild", "precompute"):
        components = [ThreePhaseSource("V", "n", 10.0, 5.0),
            *(Capacitor(f"C:{p}", f"n:{p}", "0", .01,
                       initial_voltage=amplitude * np.sin(-k * 2 * np.pi / 3)) for k, p in enumerate("abc"))]
        results.append(Simulator(Circuit.from_components("three_phase_derivative", components),
            SimulationConfig(.01, 0.0, linear_solver_mode=mode)).run().rows)
    assert results[0] == results[1]
    assert results[0][0]["i:C:a"] == pytest.approx(.01 * amplitude * 2 * np.pi * 5)


def test_precompute_rejects_saturating_three_phase_transformer_before_claiming():
    from pycy_emt_lite.components.transformers import ThreePhaseTransformer
    circuit = Circuit.from_components("saturating_precompute", [ThreePhaseTransformer("T", "p", "s", 1.0,
        magnetizing_inductance=.1, saturation_knee_flux=.01, saturated_magnetizing_inductance=.02)])
    simulator = Simulator(circuit, SimulationConfig(.01, .01, linear_solver_mode="precompute"))
    with pytest.raises(ValueError, match="precompute.*T.*饱和.*reuse"):
        simulator.run()
    assert not circuit.prepared and not circuit._run_claimed and simulator.solver.factorization_count == 0


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
