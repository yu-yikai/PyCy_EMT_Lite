"""
文件名称：test_time_grid.py
文件作用：验证仿真时间网格、终止时间和事件时间处理策略。
"""

import copy
import math

import pytest

from pycy_emt_lite import (
    Breaker,
    BreakerCloseEvent,
    BreakerOpenEvent,
    CaseDefinition,
    Circuit,
    Resistor,
    SimulationConfig,
    Simulator,
    VoltageSource,
    run_case,
)


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


def test_short_positive_stop_keeps_zero_and_terminal_time() -> None:
    simulator = Simulator(_resistive_circuit(), SimulationConfig(time_step=1.0, stop_time=1e-10))

    result = simulator.run()

    assert [row["time"] for row in result.rows] == [0.0, 1e-10]


@pytest.mark.parametrize("policy", ["insert", "quantize_up", "require_aligned"])
def test_event_after_stop_is_ignored_for_all_time_policies(policy) -> None:
    components = [
        VoltageSource("V1", "src", "0", 10.0),
        Breaker("BRK", "src", "load", closed=True, closed_resistance=0.1),
        Resistor("LOAD", "load", "0", 10.0),
    ]
    circuit = Circuit.from_components(f"after_stop_{policy}", components)
    config = SimulationConfig(time_step=0.1, stop_time=0.2, event_time_policy=policy)

    result = Simulator(circuit, config, events=[BreakerOpenEvent(0.20000000005, "BRK")]).run()

    assert [row["time"] for row in result.rows] == [0.0, 0.1, 0.2]
    assert result.event_log == []


@pytest.mark.parametrize("policy", ["insert", "quantize_up", "require_aligned"])
def test_float_sum_at_stop_is_normalized_for_all_time_policies(policy) -> None:
    components = [
        VoltageSource("V1", "src", "0", 10.0),
        Breaker("BRK", "src", "load", closed=True, closed_resistance=0.1),
        Resistor("LOAD", "load", "0", 10.0),
    ]
    circuit = Circuit.from_components(f"float_stop_{policy}", components)
    event_time = 0.1 + 0.2
    config = SimulationConfig(time_step=0.1, stop_time=0.3, event_time_policy=policy)

    result = Simulator(circuit, config, events=[BreakerOpenEvent(event_time, "BRK")]).run()

    assert [row["time"] for row in result.rows] == [0.0, 0.1, 0.2, 0.3]
    assert result.event_log[0]["time"] == 0.3


@pytest.mark.parametrize("policy", ["insert", "quantize_up", "require_aligned"])
def test_stop_event_across_float_power_boundary_is_due_for_all_policies(policy) -> None:
    components = [
        VoltageSource("V1", "src", "0", 10.0),
        Breaker("BRK", "src", "load", closed=True, closed_resistance=0.1),
        Resistor("LOAD", "load", "0", 10.0),
    ]
    circuit = Circuit.from_components(f"power_boundary_{policy}", components)
    stop_time = math.nextafter(0.5, 0.0)
    event_time = 0.5 + 4 * math.ulp(0.5)
    config = SimulationConfig(time_step=0.1, stop_time=stop_time, event_time_policy=policy)

    result = Simulator(circuit, config, events=[BreakerOpenEvent(event_time, "BRK")]).run()

    assert result.rows[-1]["time"] == stop_time
    assert result.event_log[0]["time"] == stop_time


def test_insert_event_near_replaced_grid_point_keeps_terminal_stop_time() -> None:
    components = [
        VoltageSource("V1", "src", "0", 10.0),
        Breaker("BRK", "src", "load", closed=True, closed_resistance=0.1),
        Resistor("LOAD", "load", "0", 10.0),
    ]
    stop_time = 0.5 + math.ulp(0.5)
    event_time = 0.5 - 16 * math.ulp(0.25)
    circuit = Circuit.from_components("replaced_grid_point", components)
    config = SimulationConfig(time_step=0.1, stop_time=stop_time, event_time_policy="insert")

    result = Simulator(circuit, config, events=[BreakerOpenEvent(event_time, "BRK")]).run()

    assert result.rows[-1]["time"] == stop_time
    assert [row["time"] for row in result.rows].count(stop_time) == 1
    assert result.rows[-2]["time"] == event_time
    assert result.event_log[0]["time"] == event_time


def test_insert_event_near_grid_uses_grid_representative() -> None:
    components = [
        VoltageSource("V1", "src", "0", 10.0),
        Breaker("BRK", "src", "load", closed=True, closed_resistance=0.1),
        Resistor("LOAD", "load", "0", 10.0),
    ]
    circuit = Circuit.from_components("near_grid_event", components)
    event_time = math.nextafter(0.2, -math.inf)
    config = SimulationConfig(time_step=0.1, stop_time=0.3, event_time_policy="insert")

    result = Simulator(circuit, config, events=[BreakerOpenEvent(event_time, "BRK")]).run()

    assert [row["time"] for row in result.rows] == [0.0, 0.1, 0.2, 0.3]
    assert result.event_log[0]["time"] == 0.2


def test_near_zero_inserted_events_are_not_merged_by_step_tolerance() -> None:
    components = [
        VoltageSource("V1", "src", "0", 10.0),
        Breaker("BRK", "src", "load", closed=True, closed_resistance=0.1),
        Resistor("LOAD", "load", "0", 10.0),
    ]
    circuit = Circuit.from_components("near_zero_events", components)
    events = [BreakerOpenEvent(5e-11, "BRK"), BreakerCloseEvent(1.5e-10, "BRK")]
    config = SimulationConfig(time_step=0.1, stop_time=0.1, event_time_policy="insert")

    result = Simulator(circuit, config, events=events).run()

    assert [row["time"] for row in result.rows] == [0.0, 5e-11, 1.5e-10, 0.1]
    assert [record["time"] for record in result.event_log] == [5e-11, 1.5e-10]


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


def test_simulator_and_circuit_are_single_run() -> None:
    circuit = _resistive_circuit()
    config = SimulationConfig(time_step=1e-4, stop_time=1e-4)
    simulator = Simulator(circuit, config)

    simulator.run()

    with pytest.raises(RuntimeError, match="只能运行一次"):
        simulator.run()
    with pytest.raises(RuntimeError, match="只能运行一次"):
        Simulator(circuit, config).run()


def test_simulator_cannot_run_again_after_its_circuit_is_replaced() -> None:
    simulator = Simulator(_resistive_circuit(), SimulationConfig(time_step=1e-4, stop_time=0.0))
    simulator.run()
    simulator.circuit = _resistive_circuit()

    with pytest.raises(RuntimeError, match="Simulator 实例只能运行一次"):
        simulator.run()


def test_shared_component_is_claimed_before_prepare_changes_branch_number() -> None:
    shared_source = VoltageSource("SHARED", "src", "0", 10.0)
    first = Circuit.from_components(
        "first",
        [
            VoltageSource("OFFSET", "offset", "0", 1.0),
            shared_source,
            Resistor("R1", "src", "0", 10.0),
        ],
    )
    second = Circuit.from_components(
        "second",
        [shared_source, Resistor("R2", "src", "0", 20.0)],
    )

    first.prepare()
    original_branch_index = shared_source.branch_index

    with pytest.raises(RuntimeError, match="已属于电路 'first'"):
        second.prepare()

    assert shared_source.branch_index == original_branch_index
    Simulator(first, SimulationConfig(time_step=1e-4, stop_time=0.0)).run()


def test_failed_shared_prepare_does_not_claim_unique_components() -> None:
    shared_source = VoltageSource("SHARED", "src", "0", 10.0)
    unique_source = VoltageSource("UNIQUE", "unique", "0", 5.0)
    first = Circuit.from_components(
        "first",
        [shared_source, Resistor("R1", "src", "0", 10.0)],
    )
    second = Circuit.from_components("second", [unique_source, shared_source])

    first.prepare()

    with pytest.raises(RuntimeError, match="已属于电路 'first'"):
        second.prepare()

    third = Circuit.from_components(
        "third",
        [unique_source, Resistor("R3", "unique", "0", 5.0)],
    )
    third.prepare()
    Simulator(third, SimulationConfig(time_step=1e-4, stop_time=0.0)).run()


def test_shallow_copied_prepared_circuit_cannot_bypass_component_ownership() -> None:
    circuit = _resistive_circuit()
    circuit.prepare()
    cloned = copy.copy(circuit)

    with pytest.raises(RuntimeError, match="已属于电路 'time_grid'"):
        Simulator(cloned, SimulationConfig(time_step=1e-4, stop_time=0.0)).run()

    Simulator(circuit, SimulationConfig(time_step=1e-4, stop_time=0.0)).run()


def test_run_case_rejects_reusing_its_component_instances() -> None:
    case = CaseDefinition(
        name="single_run_case",
        components=(
            VoltageSource("V1", "src", "0", 10.0),
            Resistor("R1", "src", "0", 10.0),
        ),
        config=SimulationConfig(time_step=1e-4, stop_time=0.0),
    )

    run_case(case)

    with pytest.raises(RuntimeError, match="已属于电路 'single_run_case'"):
        run_case(case)


def test_failed_run_cannot_be_retried() -> None:
    simulator = Simulator(Circuit("empty"), SimulationConfig(time_step=1e-4, stop_time=0.0))

    with pytest.raises(ValueError, match="电路没有"):
        simulator.run()
    with pytest.raises(RuntimeError, match="只能运行一次"):
        simulator.run()


@pytest.mark.parametrize("field", ["time_step", "stop_time", "start_time"])
@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
def test_simulation_times_must_be_finite(field: str, value: float) -> None:
    values = {"time_step": 1e-4, "stop_time": 1e-3, "start_time": 0.0}
    values[field] = value

    with pytest.raises(ValueError, match=field):
        SimulationConfig(**values)


def test_nonzero_start_time_is_rejected_without_state_restore() -> None:
    with pytest.raises(ValueError, match="起始时间目前只支持 0"):
        SimulationConfig(time_step=1e-4, start_time=1e-4, stop_time=2e-4)
