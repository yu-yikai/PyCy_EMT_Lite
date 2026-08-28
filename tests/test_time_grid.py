"""
文件名称：test_time_grid.py
文件作用：验证仿真时间网格、终止时间和事件时间处理策略。
"""

import math

import pytest

from pycy_emt_lite import Breaker, BreakerOpenEvent, Circuit, Resistor, SimulationConfig, Simulator, VoltageSource


def _resistive_circuit() -> Circuit:
    circuit = Circuit("time_grid")
    circuit.add(VoltageSource("V1", "src", "0", 10.0))
    circuit.add(Resistor("R1", "src", "0", 10.0))
    return circuit


def test_non_integer_stop_time_is_included_exactly() -> None:
    circuit = _resistive_circuit()
    config = SimulationConfig(time_step=1e-4, stop_time=1.5e-4)
    simulator = Simulator(circuit, config)
    result = simulator.run()

    assert math.isclose(result.rows[-1]["time"], 1.5e-4, rel_tol=0.0, abs_tol=1e-12)
    assert math.isclose(result.stop_time, 1.5e-4, rel_tol=0.0, abs_tol=1e-12)


def test_off_grid_event_time_is_inserted_by_default() -> None:
    components = [
        VoltageSource("V1", "src", "0", 10.0),
        Breaker("BRK", "src", "load", closed=True, closed_resistance=0.1),
        Resistor("LOAD", "load", "0", 10.0),
    ]
    circuit = Circuit.from_components("insert_event_time", components)
    event = BreakerOpenEvent(1.5e-3, "BRK")

    config = SimulationConfig(time_step=1e-3, stop_time=2e-3)
    events = [event]
    simulator = Simulator(circuit, config, events=events)
    result = simulator.run()

    assert [row["time"] for row in result.rows] == [0.0, 1e-3, 1.5e-3, 2e-3]
    assert math.isclose(result.event_log[0]["time"], 1.5e-3, rel_tol=0.0, abs_tol=1e-12)
    assert result.rows[2]["state:BRK"] == 0.0


def test_event_time_can_be_required_to_align_with_step() -> None:
    circuit = _resistive_circuit()
    config = SimulationConfig(time_step=1e-3, stop_time=2e-3, event_time_policy="require_aligned")
    events = [BreakerOpenEvent(1.5e-3, "missing_breaker")]
    simulator = Simulator(circuit, config, events=events)

    with pytest.raises(ValueError, match="未与仿真步长"):
        simulator.run()


def test_event_time_can_still_be_quantized_up() -> None:
    components = [
        VoltageSource("V1", "src", "0", 10.0),
        Breaker("BRK", "src", "load", closed=True, closed_resistance=0.1),
        Resistor("LOAD", "load", "0", 10.0),
    ]
    circuit = Circuit.from_components("quantized_event_time", components)
    event = BreakerOpenEvent(1.5e-3, "BRK")
    config = SimulationConfig(time_step=1e-3, stop_time=2e-3, event_time_policy="quantize_up")

    events = [event]
    simulator = Simulator(circuit, config, events=events)
    result = simulator.run()

    assert [row["time"] for row in result.rows] == [0.0, 1e-3, 2e-3]
    assert math.isclose(result.event_log[0]["time"], 2e-3, rel_tol=0.0, abs_tol=1e-12)
