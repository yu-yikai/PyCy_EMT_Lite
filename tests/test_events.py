"""
文件名称：test_events.py
文件作用：验证事件系统、故障投入清除和断路器开合。
"""

from pycy_emt_lite import (
    Breaker,
    BreakerOpenEvent,
    Circuit,
    Fault,
    FaultApplyEvent,
    FaultClearEvent,
    Resistor,
    SimulationConfig,
    Simulator,
    VoltageSource,
)


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
