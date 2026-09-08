"""
文件名称：test_basic_components.py
文件作用：验证基础元件和 MNA 内核的基本数值行为。
"""

import math

import pytest

import pycy_emt_lite
from pycy_emt_lite import Capacitor, Circuit, CurrentSource, Inductor, Resistor, SimulationConfig, Simulator, VoltageSource


@pytest.mark.parametrize("invalid", ["", "  ", None, 1])
def test_preparation_rejects_invalid_node_names(invalid) -> None:
    circuit = Circuit.from_components("invalid_node", [Resistor("R", invalid, "0", 1.0)])
    with pytest.raises(ValueError, match="节点名称"):
        circuit.prepare()


@pytest.mark.parametrize("invalid", ["", "  ", None, 1])
def test_preparation_rejects_invalid_component_names(invalid) -> None:
    circuit = Circuit.from_components("invalid_name", [Resistor(invalid, "n", "0", 1.0)])
    with pytest.raises(ValueError, match="元件名称"):
        circuit.prepare()


@pytest.mark.parametrize(
    "factory",
    [
        lambda value: Resistor("Rbad", "n", "0", value),
        lambda value: Capacitor("Cbad", "n", "0", value),
        lambda value: Inductor("Lbad", "n", "0", value),
    ],
)
@pytest.mark.parametrize("invalid", [math.nan, math.inf, -math.inf])
def test_basic_component_parameters_reject_nonfinite_values(factory, invalid) -> None:
    with pytest.raises(ValueError, match="有限"):
        factory(invalid)


@pytest.mark.parametrize(
    "factory",
    [
        lambda value: Capacitor("Cbad", "n", "0", 1.0, initial_voltage=value),
        lambda value: Inductor("Lbad", "n", "0", 1.0, initial_current=value),
    ],
)
@pytest.mark.parametrize("invalid", [math.nan, math.inf, -math.inf])
def test_dynamic_initial_conditions_reject_nonfinite_values(factory, invalid) -> None:
    with pytest.raises(ValueError, match="有限"):
        factory(invalid)


def test_zero_initial_conditions_are_valid() -> None:
    capacitor = Capacitor("C0", "n", "0", 1.0, initial_voltage=0.0)
    inductor = Inductor("L0", "n", "0", 1.0, initial_current=0.0)

    assert capacitor.previous_voltage == 0.0
    assert inductor.previous_current == 0.0


@pytest.mark.parametrize(
    ("name", "factory"),
    [
        ("Ibad", lambda value: CurrentSource("Ibad", "0", "n", value)),
        ("Vbad", lambda value: VoltageSource("Vbad", "n", "0", value)),
    ],
)
@pytest.mark.parametrize("invalid", [math.nan, math.inf, -math.inf])
def test_source_constants_reject_nonfinite_values(name, factory, invalid) -> None:
    with pytest.raises(ValueError, match="有限") as exc_info:
        factory(invalid)
    assert name in str(exc_info.value)


@pytest.mark.parametrize(
    ("name", "factory"),
    [
        ("Ibad", lambda function: CurrentSource("Ibad", "0", "n", function)),
        ("Vbad", lambda function: VoltageSource("Vbad", "n", "0", function)),
    ],
)
def test_callable_source_values_are_checked_at_runtime(name, factory) -> None:
    calls: list[float] = []

    def value_at(time: float) -> float:
        calls.append(time)
        return 1.0 if time < 1e-4 else math.nan

    source = factory(value_at)
    assert calls == []
    circuit = Circuit.from_components(name, [source, Resistor("R1", "n", "0", 1.0)])

    with pytest.raises(RuntimeError) as exc_info:
        Simulator(circuit, SimulationConfig(time_step=1e-4, stop_time=1e-4)).run()

    message = str(exc_info.value)
    assert name in message
    assert "0.0001" in message
    assert len(calls) == 2


def test_root_public_api_is_limited_to_the_teaching_workflow() -> None:
    expected = {
        "Breaker",
        "BreakerCloseEvent",
        "BreakerOpenEvent",
        "Capacitor",
        "CaseDefinition",
        "Circuit",
        "CurrentSource",
        "Fault",
        "FaultApplyEvent",
        "FaultClearEvent",
        "IdealSwitch",
        "Inductor",
        "OutputOptions",
        "PiLine",
        "PlotSpec",
        "Resistor",
        "SimulationConfig",
        "SimulationResult",
        "Simulator",
        "SinglePhaseTransformer",
        "ThreePhaseLine",
        "ThreePhaseLoad",
        "ThreePhaseSource",
        "VoltageSource",
        "run_case",
    }

    assert len(pycy_emt_lite.__all__) == len(expected)
    assert set(pycy_emt_lite.__all__) == expected


def test_resistor_voltage_source_solution() -> None:
    circuit = Circuit("resistor_solution")
    circuit.add(VoltageSource("V1", "n1", "0", 10.0))
    circuit.add(Resistor("R1", "n1", "0", 5.0))

    config = SimulationConfig(time_step=1e-4, stop_time=1e-4)
    simulator = Simulator(circuit, config)
    result = simulator.run()

    assert math.isclose(result.rows[-1]["v:n1"], 10.0, rel_tol=0.0, abs_tol=1e-12)
    assert math.isclose(result.rows[-1]["i:R1"], 2.0, rel_tol=0.0, abs_tol=1e-12)


def test_circuit_can_be_created_from_user_component_objects() -> None:
    components = [
        VoltageSource("V1", "n1", "0", 10.0),
        Resistor("R1", "n1", "0", 5.0),
    ]
    circuit = Circuit.from_components("from_components", components)

    config = SimulationConfig(time_step=1e-4, stop_time=1e-4)
    simulator = Simulator(circuit, config)
    result = simulator.run()

    assert math.isclose(result.rows[-1]["v:n1"], 10.0, rel_tol=0.0, abs_tol=1e-12)
    assert math.isclose(result.rows[-1]["i:R1"], 2.0, rel_tol=0.0, abs_tol=1e-12)


def test_current_source_direction_satisfies_kcl() -> None:
    circuit = Circuit("current_source_direction")
    circuit.add(CurrentSource("I1", "0", "n1", 2.0))
    circuit.add(Resistor("R1", "n1", "0", 5.0))

    config = SimulationConfig(time_step=1e-4, stop_time=1e-4)
    result = Simulator(circuit, config).run()

    assert math.isclose(result.rows[-1]["v:n1"], 10.0, rel_tol=0.0, abs_tol=1e-12)
    assert math.isclose(result.rows[-1]["i:R1"], 2.0, rel_tol=0.0, abs_tol=1e-12)


def test_rc_step_response_reaches_expected_value() -> None:
    circuit = Circuit("rc_step")
    circuit.add(VoltageSource("V1", "src", "0", 1.0))
    circuit.add(Resistor("R1", "src", "out", 1_000.0))
    circuit.add(Capacitor("C1", "out", "0", 1e-6))

    config = SimulationConfig(time_step=1e-5, stop_time=5e-3)
    simulator = Simulator(circuit, config)
    result = simulator.run()

    final_voltage = result.rows[-1]["v:out"]
    assert 0.99 < final_voltage < 1.01


def test_rl_step_response_reaches_expected_current() -> None:
    circuit = Circuit("rl_step")
    circuit.add(VoltageSource("V1", "src", "0", 1.0))
    circuit.add(Resistor("R1", "src", "mid", 10.0))
    circuit.add(Inductor("L1", "mid", "0", 10e-3))

    config = SimulationConfig(time_step=1e-5, stop_time=5e-3)
    simulator = Simulator(circuit, config)
    result = simulator.run()

    final_current = result.rows[-1]["i:L1"]
    assert 0.099 < final_current < 0.101


def test_rlc_response_is_bounded_and_settles_near_source_voltage() -> None:
    circuit = Circuit("rlc_step")
    circuit.add(VoltageSource("V1", "src", "0", 1.0))
    circuit.add(Resistor("R1", "src", "n1", 20.0))
    circuit.add(Inductor("L1", "n1", "out", 10e-3))
    circuit.add(Capacitor("C1", "out", "0", 10e-6))

    config = SimulationConfig(time_step=2e-6, stop_time=10e-3)
    simulator = Simulator(circuit, config)
    result = simulator.run()
    out = result.series("v:out")

    assert out.max() < 1.4
    assert out.min() > -0.1
    assert 0.95 < out[-1] < 1.05
