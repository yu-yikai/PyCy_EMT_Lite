"""
文件名称：test_events.py
文件作用：验证事件系统、故障投入清除和断路器开合。
"""

from dataclasses import dataclass

import pytest

from pycy_emt_lite import (
    Breaker,
    BreakerCloseEvent,
    BreakerOpenEvent,
    Capacitor,
    Circuit,
    CurrentSource,
    Fault,
    FaultApplyEvent,
    FaultClearEvent,
    Inductor,
    Resistor,
    SimulationConfig,
    Simulator,
    VoltageSource,
)
from pycy_emt_lite.events import SimulationEvent
from pycy_emt_lite.core.solvers import DenseLinearSolver


@dataclass(frozen=True, slots=True)
class _CustomEvent(SimulationEvent):
    """仅用于确认自定义事件不被标准状态校验限制。"""

    def apply(self, circuit: Circuit, applied_time: float) -> dict[str, float | str]:
        return {"time": applied_time, "target": self.target, "type": "custom"}


def test_fault_apply_and_clear_are_logged_and_affect_current() -> None:
    components = [
        VoltageSource("V1", "src", "0", 10.0),
        Resistor("R1", "src", "bus", 10.0),
        Resistor("LOAD", "bus", "0", 100.0),
        Fault("F1", "bus", resistance=1.0),
    ]
    circuit = Circuit.from_components("fault_event", components)
    events = [FaultApplyEvent(1e-3, "F1"), FaultClearEvent(3e-3, "F1")]

    config = SimulationConfig(time_step=1e-3, stop_time=4e-3)
    simulator = Simulator(circuit, config, events=events)
    result = simulator.run()

    assert [record["type"] for record in result.event_log] == ["fault_apply", "fault_clear"]
    assert result.rows[0]["state:F1"] == 0.0
    assert result.rows[1]["state:F1"] == 1.0
    assert result.rows[-1]["state:F1"] == 0.0
    assert result.rows[1]["i:F1"] > result.rows[0]["i:F1"]


def test_breaker_open_event_changes_state() -> None:
    components = [
        VoltageSource("V1", "src", "0", 10.0),
        Breaker("BRK", "src", "load", closed=True, closed_resistance=0.1),
        Resistor("LOAD", "load", "0", 10.0),
        Resistor("BYPASS", "src", "0", 100.0),
    ]
    circuit = Circuit.from_components("breaker_event", components)
    config = SimulationConfig(time_step=1e-3, stop_time=2e-3)
    events = [BreakerOpenEvent(1e-3, "BRK")]
    simulator = Simulator(circuit, config, events=events)
    result = simulator.run()

    assert result.event_log[0]["type"] == "breaker_open"
    assert result.rows[0]["state:BRK"] == 1.0
    assert result.rows[-1]["state:BRK"] == 0.0
    assert result.rows[-1]["i:BRK"] == 0.0


def test_t0_breaker_close_is_applied_before_topology_is_solved() -> None:
    circuit = Circuit.from_components(
        "t0_breaker_close",
        [
            CurrentSource("I1", "0", "n", 1.0),
            Breaker("BRK", "n", "0", closed=False, closed_resistance=1e-3),
        ],
    )
    result = Simulator(
        circuit,
        SimulationConfig(time_step=1e-3, stop_time=0.0),
        events=[BreakerCloseEvent(0.0, "BRK")],
    ).run()

    assert result.rows[0]["v:n"] == pytest.approx(1e-3)
    assert result.event_log[0]["type"] == "breaker_close"


@pytest.mark.parametrize("time", [float("nan"), float("inf"), float("-inf")])
def test_event_time_must_be_finite(time: float) -> None:
    with pytest.raises(ValueError, match="事件时间必须为有限数"):
        FaultApplyEvent(time, "F1")


@pytest.mark.parametrize(
    "event",
    [
        FaultApplyEvent(1e-3, "missing"),
        FaultClearEvent(1e-3, "missing"),
        BreakerOpenEvent(1e-3, "missing"),
        BreakerCloseEvent(1e-3, "missing"),
    ],
)
def test_standard_event_rejects_missing_target_before_first_solve(event: SimulationEvent) -> None:
    circuit = Circuit.from_components(
        "event_target",
        [VoltageSource("V1", "bus", "0", 1.0), Resistor("R1", "bus", "0", 1.0)],
    )
    solver = DenseLinearSolver()
    simulator = Simulator(
        circuit,
        SimulationConfig(time_step=1e-3, stop_time=1e-3),
        events=[event],
        solver=solver,
    )

    with pytest.raises(KeyError, match=rf"missing.*0\.001"):
        simulator.run()

    assert simulator.last_time is None
    assert solver.solve_count == 0


@pytest.mark.parametrize(
    ("event", "component", "expected_state"),
    [
        (FaultApplyEvent(1e-3, "R1"), Resistor("R1", "bus", "0", 1.0), "enabled"),
        (FaultClearEvent(1e-3, "R1"), Resistor("R1", "bus", "0", 1.0), "enabled"),
        (BreakerOpenEvent(1e-3, "R1"), Resistor("R1", "bus", "0", 1.0), "closed"),
        (BreakerCloseEvent(1e-3, "R1"), Resistor("R1", "bus", "0", 1.0), "closed"),
    ],
)
def test_standard_event_rejects_unsupported_target_state_before_first_solve(
    event: SimulationEvent, component: Resistor, expected_state: str
) -> None:
    circuit = Circuit.from_components(
        "event_state",
        [VoltageSource("V1", "bus", "0", 1.0), component],
    )
    solver = DenseLinearSolver()
    simulator = Simulator(
        circuit,
        SimulationConfig(time_step=1e-3, stop_time=1e-3),
        events=[event],
        solver=solver,
    )

    with pytest.raises(TypeError, match=rf"R1.*0\.001.*{expected_state}"):
        simulator.run()

    assert simulator.last_time is None
    assert solver.solve_count == 0


def test_invalid_standard_event_prevents_earlier_events_from_changing_state() -> None:
    fault = Fault("F1", "bus", resistance=1.0)
    circuit = Circuit.from_components(
        "event_validation",
        [VoltageSource("V1", "bus", "0", 1.0), Resistor("R1", "bus", "0", 1.0), fault],
    )
    solver = DenseLinearSolver()
    simulator = Simulator(
        circuit,
        SimulationConfig(time_step=1e-3, stop_time=1e-3),
        events=[FaultApplyEvent(0.0, "F1"), BreakerOpenEvent(1e-3, "missing")],
        solver=solver,
    )

    with pytest.raises(KeyError, match=rf"missing.*0\.001"):
        simulator.run()

    assert not fault.enabled
    assert simulator.event_log == []
    assert simulator.last_time is None
    assert solver.solve_count == 0


def test_custom_event_is_not_limited_to_standard_target_states() -> None:
    circuit = Circuit.from_components(
        "custom_event",
        [VoltageSource("V1", "bus", "0", 1.0), Resistor("R1", "bus", "0", 1.0)],
    )
    result = Simulator(
        circuit,
        SimulationConfig(time_step=1e-3, stop_time=0.0),
        events=[_CustomEvent(0.0, "R1")],
    ).run()

    assert result.event_log == [{"time": 0.0, "target": "R1", "type": "custom"}]


@pytest.mark.parametrize("method", ["trapezoidal", "backward_euler"])
@pytest.mark.parametrize("apply_time", [0.0, 0.1, 0.15, 0.3])
def test_capacitor_event_preserves_left_state_and_stores_right_current(method, apply_time) -> None:
    capacitor = Capacitor("C", "n", "0", 1.0)
    circuit = Circuit.from_components("capacitor_event", [
        CurrentSource("I", "0", "n", 1.0), capacitor, Fault("F", "n", 1.0),
    ])
    result = Simulator(circuit, SimulationConfig(0.1, 0.3, method=method),
                       events=[FaultApplyEvent(apply_time, "F")]).run()
    voltage = 0.0
    for index, row in enumerate(result.rows):
        if index:
            previous = result.rows[index - 1]
            h = row["time"] - previous["time"]
            if previous["state:F"] == 0.0:
                voltage += h
            else:
                decay = (1 - h / 2) / (1 + h / 2) if method == "trapezoidal" else 1 / (1 + h)
                voltage = 1 + (voltage - 1) * decay
        assert row["v:C"] == pytest.approx(voltage, abs=1e-12)
        assert row["i:F"] == pytest.approx(voltage * row["state:F"], abs=1e-12)
        assert row["i:C"] == pytest.approx(1 - row["i:F"])
    event_row = next(row for row in result.rows if row["time"] == apply_time)
    assert event_row["v:C"] == pytest.approx(apply_time, abs=1e-12)
    assert capacitor.previous_current == pytest.approx(result.rows[-1]["i:C"])
    assert len({row["time"] for row in result.rows}) == len(result.rows)


@pytest.mark.parametrize("method", ["trapezoidal", "backward_euler"])
@pytest.mark.parametrize("open_time,close_time,stop", [(0.0, 0.2, 0.3), (0.1, 0.3, 0.3), (0.15, 0.25, 0.35)])
def test_rl_open_and_close_events_recompute_voltage_without_advancing_twice(method, open_time, close_time, stop) -> None:
    circuit = Circuit.from_components("rl_events", [
        VoltageSource("V", "src", "0", 1.0), Inductor("L", "src", "n", 1.0, initial_current=0.2),
        Resistor("R", "n", "0", 2.0), Breaker("B", "n", "0", closed_resistance=2.0),
    ])
    result = Simulator(circuit, SimulationConfig(0.1, stop, method=method), events=[
        BreakerOpenEvent(open_time, "B"), BreakerCloseEvent(close_time, "B"),
    ]).run()
    current = 0.2
    for index, row in enumerate(result.rows):
        if index:
            previous = result.rows[index - 1]
            resistance = 1.0 if previous["state:B"] else 2.0
            h = row["time"] - previous["time"]
            decay = (1 - resistance * h / 2) / (1 + resistance * h / 2) if method == "trapezoidal" else 1 / (1 + resistance * h)
            current = 1 / resistance + (current - 1 / resistance) * decay
        resistance = 1.0 if row["state:B"] else 2.0
        assert row["i:L"] == pytest.approx(current)
        assert row["v:L"] == pytest.approx(1 - resistance * current)
        assert row["i:R"] + row["i:B"] == pytest.approx(current)


def test_same_time_events_use_declaration_order_and_one_right_solve() -> None:
    circuit = Circuit.from_components("same_time", [
        CurrentSource("I", "0", "n", 1.0), Capacitor("C", "n", "0", 1.0), Fault("F", "n", 1.0),
    ])
    solver = DenseLinearSolver()
    result = Simulator(circuit, SimulationConfig(0.1, 0.3), solver=solver, events=[
        FaultApplyEvent(0.15, "F"), FaultClearEvent(0.15, "F"),
    ]).run()
    assert [record["type"] for record in result.event_log] == ["fault_apply", "fault_clear"]
    assert result.series("v:C") == pytest.approx(result.series("time"))
    assert result.series("i:C") == pytest.approx([1.0] * len(result.rows))
    assert solver.solve_count == len(result.rows) + 1


def test_opening_only_inductor_path_reports_state_conflict() -> None:
    circuit = Circuit.from_components("interrupted_current", [
        Inductor("L", "n", "0", 1.0, initial_current=1.0),
        Breaker("B", "n", "0", closed_resistance=1.0),
    ])
    with pytest.raises(RuntimeError, match="仿真时间 0.15.*冲突"):
        Simulator(circuit, SimulationConfig(0.1, 0.2), events=[BreakerOpenEvent(0.15, "B")]).run()


def test_capacitor_clear_event_restores_charging_current_and_history() -> None:
    result = Simulator(Circuit.from_components("clear_capacitor", [
        CurrentSource("I", "0", "n", 1.0), Capacitor("C", "n", "0", 1.0), Fault("F", "n", 1.0),
    ]), SimulationConfig(0.1, 0.3), events=[FaultApplyEvent(0.0, "F"), FaultClearEvent(0.15, "F")]).run()
    voltage_at_clear = 1 - (0.95 / 1.05) * (0.975 / 1.025)
    assert result.rows[2]["v:C"] == pytest.approx(voltage_at_clear)
    assert result.rows[2]["i:C"] == pytest.approx(1.0)
    assert result.rows[-1]["v:C"] == pytest.approx(voltage_at_clear + 0.15)
