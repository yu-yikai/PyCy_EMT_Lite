"""
文件名称：test_synchronous_machine.py
文件作用：验证同步机经典二阶教学模型。
"""

import math

import pytest
from pycy_emt_lite import Circuit, Resistor, SimulationConfig, Simulator
from pycy_emt_lite.analysis import three_phase_rms
from pycy_emt_lite.machines import SynchronousMachine


def test_machine_initial_row_does_not_advance_stator_or_rotor() -> None:
    machine = SynchronousMachine("SM", "bus", 100.0, 1.0, 0.1, 3000.0, 3.5,
                                 mechanical_power=2700.0, initial_rotor_angle=0.2, initial_speed_pu=1.01)
    result = Simulator(Circuit.from_components("initial_machine", [machine,
        *[Resistor(f"R{p}", f"bus:{p}", "0", 9.0) for p in "abc"],
    ]), SimulationConfig(1e-4, 0.0)).run()
    row = result.rows[0]
    assert row["rotor_angle:SM"] == 0.2
    assert row["speed_pu:SM"] == 1.01
    for p in "abc":
        assert row[f"i:SM:{p}"] == pytest.approx(0.0, abs=1e-12)
        assert machine.state.previous_inductor_voltage[p] == pytest.approx(row[f"e:SM:{p}"])


def test_synchronous_machine_terminal_voltage_with_resistive_load() -> None:
    """同步机内电势经定子电阻带三相电阻负荷时，机端 RMS 应符合分压关系。"""

    components = [
        SynchronousMachine(
            "SM",
            "bus",
            internal_phase_rms=100.0,
            stator_resistance=1.0,
            stator_inductance=0.0,
            base_power=2700.0,
            inertia_constant=3.5,
            mechanical_power=2700.0,
            frequency=50.0,
        ),
        Resistor("LA", "bus:a", "0", 9.0),
        Resistor("LB", "bus:b", "0", 9.0),
        Resistor("LC", "bus:c", "0", 9.0),
    ]
    circuit = Circuit.from_components("synchronous_machine_resistive_load", components)
    config = SimulationConfig(time_step=1e-4, stop_time=0.1)
    simulator = Simulator(circuit, config)

    result = simulator.run()

    rms_values = three_phase_rms(result, ("v:bus:a", "v:bus:b", "v:bus:c"), start_time=0.06)
    assert all(89.8 < value < 90.2 for value in rms_values.values())
    assert math.isclose(result.rows[-1]["speed_pu:SM"], 1.0, rel_tol=0.0, abs_tol=1e-4)


def test_synchronous_machine_accelerates_when_mechanical_power_exceeds_electrical_power() -> None:
    """机械输入大于电磁输出时，摆动方程应使转速上升。"""

    components = [
        SynchronousMachine(
            "SM",
            "bus",
            internal_phase_rms=1.0,
            stator_resistance=1e-3,
            stator_inductance=0.0,
            base_power=1e6,
            inertia_constant=2.0,
            mechanical_power=1e6,
            frequency=50.0,
        )
    ]
    circuit = Circuit.from_components("synchronous_machine_acceleration", components)
    config = SimulationConfig(time_step=1e-4, stop_time=0.02)
    simulator = Simulator(circuit, config)

    result = simulator.run()

    assert result.rows[-1]["speed_pu:SM"] > 1.004
    assert result.rows[-1]["rotor_angle:SM"] > 0.0
