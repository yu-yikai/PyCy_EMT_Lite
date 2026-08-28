"""
文件名称：test_power_electronics.py
文件作用：验证阶段 3 电力电子简化元件和滤波器组合。
"""

import math

from pycy_emt_lite import (
    Circuit,
    Diode,
    IdealSwitch,
    IGBTSwitch,
    LCLFilter,
    SimulationConfig,
    Simulator,
    ThreePhaseAverageInverter,
    VoltageSource,
)


def test_ideal_switch_conducts_when_closed() -> None:
    components = [
        VoltageSource("V1", "src", "0", 10.0),
        IdealSwitch("S1", "src", "out", closed=True, closed_resistance=0.1),
        IdealSwitch("Sload", "out", "0", closed=True, closed_resistance=9.9),
    ]
    circuit = Circuit.from_components("ideal_switch", components)

    config = SimulationConfig(time_step=1e-4, stop_time=1e-4)
    simulator = Simulator(circuit, config)
    result = simulator.run()

    assert math.isclose(result.rows[-1]["i:S1"], 1.0, rel_tol=0.0, abs_tol=1e-9)
    assert result.rows[-1]["state:S1"] == 1.0


def test_diode_uses_previous_voltage_for_explicit_state() -> None:
    diode = Diode("D1", "src", "out", previous_voltage=1.0, on_resistance=1.0)
    components = [
        VoltageSource("V1", "src", "0", 10.0),
        diode,
        IdealSwitch("Sload", "out", "0", closed=True, closed_resistance=9.0),
    ]
    circuit = Circuit.from_components("diode_explicit", components)

    config = SimulationConfig(time_step=1e-4, stop_time=1e-4)
    simulator = Simulator(circuit, config)
    result = simulator.run()

    assert result.rows[-1]["state:D1"] == 1.0
    assert result.rows[-1]["i:D1"] > 0.0


def test_igbt_gate_controls_conductance() -> None:
    components = [
        VoltageSource("V1", "src", "0", 5.0),
        IGBTSwitch("Q1", "src", "out", gate=lambda time: time >= 1e-4, on_resistance=0.1),
        IdealSwitch("Sload", "out", "0", closed=True, closed_resistance=4.9),
    ]
    circuit = Circuit.from_components("igbt_gate", components)

    config = SimulationConfig(time_step=1e-4, stop_time=2e-4)
    simulator = Simulator(circuit, config)
    result = simulator.run()

    assert result.rows[0]["state:Q1"] == 0.0
    assert result.rows[-1]["state:Q1"] == 1.0
    assert result.rows[-1]["i:Q1"] > 0.9


def test_lcl_filter_creates_expected_component_list() -> None:
    lcl_filter = LCLFilter(
        "F1",
        "conv",
        "cap",
        "grid",
        "0",
        converter_inductance=1e-3,
        grid_inductance=0.5e-3,
        capacitance=10e-6,
        converter_resistance=0.1,
        grid_resistance=0.05,
        damping_resistance=2.0,
    )

    components = lcl_filter.components()

    assert [component.name for component in components] == [
        "F1:converter:R",
        "F1:converter:L",
        "F1:Rd",
        "F1:C",
        "F1:grid:R",
        "F1:grid:L",
    ]


def test_three_phase_average_inverter_limits_modulation() -> None:
    inverter = ThreePhaseAverageInverter(dc_voltage=800.0)

    voltages = inverter.phase_voltages_from_modulation((1.2, 0.0, -1.2))

    assert voltages == (400.0, 0.0, -400.0)
