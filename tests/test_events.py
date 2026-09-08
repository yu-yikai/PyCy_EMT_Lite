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
    Circuit,
    CurrentSource,
    Fault,
    FaultApplyEvent,
    FaultClearEvent,
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
