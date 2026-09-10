"""
文件名称：test_park_synchronous_generator.py
文件作用：验证带 AVR 和调速器的 Park dq0 同步发电机模型。
"""

import pytest

from pycy_emt_lite import Circuit, Resistor, SimulationConfig, Simulator
from pycy_emt_lite.analysis import three_phase_rms
from pycy_emt_lite.machines import ParkSynchronousGenerator


def _base_generator(**overrides) -> ParkSynchronousGenerator:
    """构造测试用 Park dq0 发电机。"""

    params = {
        "name": "GEN",
        "terminal_bus": "bus",
        "base_power": 3000.0,
        "base_phase_rms": 100.0,
        "stator_resistance_pu": 0.1,
        "d_axis_reactance_pu": 1.8,
        "q_axis_reactance_pu": 1.7,
        "d_axis_transient_reactance_pu": 0.0,
        "q_axis_transient_reactance_pu": 0.3,
        "d_axis_open_circuit_time_constant": 1.0,
        "q_axis_open_circuit_time_constant": 0.5,
        "inertia_constant": 3.5,
        "voltage_reference_pu": 1.0,
        "avr_gain": 0.0,
        "initial_eq_prime_pu": 1.0,
        "initial_efd_pu": 1.0,
        "mechanical_power_reference_pu": 0.9,
        "initial_mechanical_power_pu": 0.9,
        "frequency": 50.0,
    }
    params.update(overrides)
    return ParkSynchronousGenerator(**params)


def test_generator_initial_row_preserves_stator_and_control_states() -> None:
    generator = _base_generator(d_axis_transient_reactance_pu=0.2, initial_rotor_angle=0.2, initial_speed_pu=1.01)
    result = Simulator(Circuit.from_components("initial_generator", [generator,
        *[Resistor(f"R{p}", f"bus:{p}", "0", 9.0) for p in "abc"],
    ]), SimulationConfig(1e-4, 0.0)).run()
    row = result.rows[0]
    assert row["rotor_angle:GEN"] == 0.2
    assert row["speed_pu:GEN"] == 1.01
    assert row["eq_prime_pu:GEN"] == 1.0
    assert row["efd_pu:GEN"] == 1.0
    assert row["pm_pu:GEN"] == 0.9
    for p in "abc":
        assert row[f"i:GEN:{p}"] == pytest.approx(0.0, abs=1e-12)
        assert generator.state.previous_inductor_voltage[p] == pytest.approx(row[f"e:GEN:{p}"])


def test_park_generator_terminal_voltage_with_resistive_load() -> None:
    """Park 发电机经定子电阻带三相电阻负荷时，机端 RMS 应接近分压结果。"""

    components = [
        _base_generator(),
        Resistor("LA", "bus:a", "0", 9.0),
        Resistor("LB", "bus:b", "0", 9.0),
        Resistor("LC", "bus:c", "0", 9.0),
    ]
    circuit = Circuit.from_components("park_generator_resistive_load", components)
    config = SimulationConfig(time_step=1e-4, stop_time=0.1)
    simulator = Simulator(circuit, config)

    result = simulator.run()

    rms_values = three_phase_rms(result, ("v:bus:a", "v:bus:b", "v:bus:c"), start_time=0.06)
    assert all(88.0 < value < 94.0 for value in rms_values.values())
    assert 0.90 < result.rows[-1]["vt_pu:GEN"] < 0.95


def test_park_generator_avr_raises_terminal_voltage() -> None:
    """AVR 电压参考高于机端电压时，励磁和机端电压应上升。"""

    components = [
        _base_generator(
            avr_gain=10.0,
            avr_time_constant=0.05,
            d_axis_open_circuit_time_constant=0.3,
            q_axis_open_circuit_time_constant=0.3,
            initial_eq_prime_pu=0.8,
            initial_efd_pu=0.8,
            mechanical_power_reference_pu=0.5,
            initial_mechanical_power_pu=0.5,
        ),
        Resistor("LA", "bus:a", "0", 20.0),
        Resistor("LB", "bus:b", "0", 20.0),
        Resistor("LC", "bus:c", "0", 20.0),
    ]
    circuit = Circuit.from_components("park_generator_avr_response", components)
    config = SimulationConfig(time_step=1e-4, stop_time=0.2)
    simulator = Simulator(circuit, config)

    result = simulator.run()

    assert result.rows[-1]["vt_pu:GEN"] > result.rows[10]["vt_pu:GEN"] + 0.15
    assert result.rows[-1]["eq_prime_pu:GEN"] > 0.95
    assert result.rows[-1]["efd_pu:GEN"] > 0.9


def test_park_generator_governor_increases_power_when_speed_drops() -> None:
    """转速低于同步速度时，调速器应提高机械功率输出。"""

    components = [
        _base_generator(
            avr_gain=5.0,
            mechanical_power_reference_pu=0.8,
            initial_mechanical_power_pu=0.2,
            governor_time_constant=0.05,
            governor_droop=0.05,
        ),
        Resistor("LA", "bus:a", "0", 12.0),
        Resistor("LB", "bus:b", "0", 12.0),
        Resistor("LC", "bus:c", "0", 12.0),
    ]
    circuit = Circuit.from_components("park_generator_governor_response", components)
    config = SimulationConfig(time_step=1e-4, stop_time=0.15)
    simulator = Simulator(circuit, config)

    result = simulator.run()

    assert result.rows[-1]["speed_pu:GEN"] < 1.0
    assert result.rows[-1]["pm_pu:GEN"] > result.rows[0]["pm_pu:GEN"] + 0.3
