"""
文件名称：test_basic_components.py
文件作用：验证基础元件和 MNA 内核的基本数值行为。
"""

import math

from pycy_emt_lite import Capacitor, Circuit, Inductor, Resistor, SimulationConfig, Simulator, VoltageSource


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
