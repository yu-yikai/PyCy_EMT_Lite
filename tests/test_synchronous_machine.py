"""
文件名称：test_synchronous_machine.py
文件作用：验证同步机经典二阶教学模型。
"""

import math

import numpy as np
import pytest
from scipy.integrate import solve_ivp
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
            mechanical_power=3000.0,
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
    # 电磁功率包含 300 W 定子铜损，机械输入不能只与端口功率相等。
    assert result.rows[-1]["p_em:SM"] == pytest.approx(3000.0)
    assert result.rows[-1]["p_copper:SM"] == pytest.approx(300.0)


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


def test_copper_loss_causes_deceleration_when_only_terminal_power_is_supplied() -> None:
    machine = SynchronousMachine("SM", "bus", 100.0, 1.0, 0.0, 3000.0, 3.5, mechanical_power=2700.0)
    result = Simulator(Circuit.from_components("copper_loss", [machine,
        *[Resistor(f"R{p}", f"bus:{p}", "0", 9.0) for p in "abc"],
    ]), SimulationConfig(1e-4, 0.1)).run()
    # 无电感时 Pe=3000 W 恒定；H*Sbase*(speed²-1) = -300 W*t。
    expected_speed = np.sqrt(1 - 300 * result.series("time") / (3.5 * 3000))
    assert result.series("speed_pu:SM") == pytest.approx(expected_speed, abs=2e-9)


def test_classical_rl_energy_and_coupled_state_convergence() -> None:
    """独立积分转子与三相电流，核对机电耦合和 R-L 离散能量。"""
    time = np.linspace(0, 0.04, 401)
    phase = np.array([0, -2*math.pi/3, 2*math.pi/3])
    def rhs(t, state):
        delta, speed = state[:2]
        current = state[2:]
        voltage = math.sqrt(2)*100*np.sin(2*math.pi*50*t+delta+phase)
        pe = voltage @ current
        return [2*math.pi*50*(speed-1),
                ((2700-pe)/3000-0.2*(speed-1))/(2*3.5*speed),
                *((voltage-10*current)/0.05)]
    reference = solve_ivp(rhs, (0, 0.04), [0.2, 1.01, 0, 0, 0], t_eval=time, rtol=1e-11, atol=1e-12)
    assert reference.success
    errors = []
    for stride, dt in enumerate((1e-4, 5e-5, 2.5e-5)):
        machine = SynchronousMachine("SM", "bus", 100, 1, 0.05, 3000, 3.5, mechanical_power=2700,
                                     damping=0.2, initial_rotor_angle=0.2, initial_speed_pu=1.01)
        result = Simulator(Circuit.from_components("rl_machine", [machine,
            *[Resistor(f"R{p}", f"bus:{p}", "0", 9.0) for p in "abc"],
        ]), SimulationConfig(dt, 0.04)).run()
        columns = ["rotor_angle:SM", "speed_pu:SM", *[f"i:SM:{p}" for p in "abc"]]
        observed = np.column_stack([result.series(key) for key in columns])[::2**stride]
        # 电流按 10 A、角度按 1 rad、转速按 1 pu 归一化后比较。
        assert np.max(np.abs(observed-reference.y.T) / [1, 1, 10, 10, 10]) < 2e-4
        # 机电显式更新为一阶；较粗步长下电流误差由梯形离散主导，单独考察转角。
        errors.append(np.max(np.abs(observed[:, 0]-reference.y[0])))
        current = np.column_stack([result.series(f"i:SM:{p}") for p in "abc"])
        voltage = np.column_stack([result.series(f"e:SM:{p}") for p in "abc"])
        angle = 2*math.pi*50*result.series("time") + result.series("rotor_angle:SM")
        assert voltage == pytest.approx(math.sqrt(2)*100*np.sin(angle[:, None]+phase), abs=1e-10)
        assert result.series("p_em:SM") == pytest.approx(np.sum(voltage*current, axis=1), abs=1e-9)
        avg_v, avg_i = (voltage[:-1]+voltage[1:])/2, (current[:-1]+current[1:])/2
        work = np.diff(result.series("time")) * np.sum(avg_v*avg_i-10*avg_i**2, axis=1)
        energy = 0.5*0.05*np.sum(current**2, axis=1)
        assert np.max(np.abs(np.diff(energy)-work)) < 1e-11
    assert errors[-1] < 5e-4
    assert 1.7 < errors[0]/errors[1] < 2.3
    assert 1.7 < errors[1]/errors[2] < 2.3


@pytest.mark.parametrize("overrides, match", [
    ({"base_power": float("nan")}, "base_power"),
    ({"initial_speed_pu": float("inf")}, "initial_speed_pu"),
    ({"mechanical_power": float("nan")}, "mechanical_power"),
    ({"inertia_constant": 0}, "inertia_constant"),
    ({"stator_inductance": -1}, "stator_inductance"),
    ({"stator_resistance": 0, "stator_inductance": 0}, "stator_resistance"),
    ({"damping": -1}, "damping"),
    ({"frequency": True}, "frequency"),
])
def test_classical_machine_reports_invalid_parameter_and_repair(overrides, match) -> None:
    parameters = dict(name="SM", terminal_bus="bus", internal_phase_rms=100, stator_resistance=1,
                      stator_inductance=0, base_power=3000, inertia_constant=3.5)
    parameters.update(overrides)
    with pytest.raises(ValueError, match=match) as error:
        SynchronousMachine(**parameters)
    assert "请" in str(error.value)


def test_classical_machine_rejects_nonfinite_callable_power_at_its_time() -> None:
    machine = SynchronousMachine("SM", "bus", 100, 1, 0, 3000, 3.5,
                                 mechanical_power=lambda t: 2700 if t == 0 else float("nan"))
    with pytest.raises(ValueError, match=r"mechanical_power\(time=0.0001\).+请"):
        Simulator(Circuit.from_components("bad_power", [machine,
            *[Resistor(f"R{p}", f"bus:{p}", "0", 9.0) for p in "abc"],
        ]), SimulationConfig(1e-4, 1e-4)).run()
