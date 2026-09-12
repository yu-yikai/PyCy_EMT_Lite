"""
文件名称：test_park_synchronous_generator.py
文件作用：验证带 AVR 和调速器的四阶 Park dq 同步发电机模型。
"""

import math
from dataclasses import replace
from pathlib import Path
import runpy

import numpy as np
import pytest
from scipy.integrate import solve_ivp

from pycy_emt_lite import Capacitor, Circuit, Resistor, SimulationConfig, Simulator
from pycy_emt_lite.analysis import three_phase_rms
from pycy_emt_lite.machines import ParkSynchronousGenerator
from pycy_emt_lite.controls import dq_to_abc


def _base_generator(**overrides) -> ParkSynchronousGenerator:
    """构造测试用四阶 Park dq 发电机。"""

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


STATE_COLUMNS = ("rotor_angle:GEN", "speed_pu:GEN", "eq_prime_pu:GEN", "ed_prime_pu:GEN", "efd_pu:GEN", "pm_pu:GEN")


def _reference(gen, resistance, times, initial=None):
    """消去平衡电阻网络，独立积分六个连续状态；不调用模型的 stamp/update。"""
    load = resistance / (3 * gen.base_phase_rms**2 / gen.base_power)
    a = load + gen.stator_resistance_pu
    xd, xq = gen.d_axis_transient_reactance_pu, gen.q_axis_transient_reactance_pu

    def rhs(t, y):
        delta, speed, eq, ed, efd, pm = y
        id_ = (a * ed + xq * eq) / (a*a + xd*xq)
        iq = (a * eq - xd * ed) / (a*a + xd*xq)
        vt = load * math.hypot(id_, iq)
        pe = a * (id_*id_ + iq*iq)
        de = (gen.initial_efd_pu + gen.avr_gain * (gen.voltage_reference_pu-vt) - efd) / gen.avr_time_constant
        dp = (gen.mechanical_power_reference_pu - (speed-1)/gen.governor_droop - pm) / gen.governor_time_constant
        # 参考状态限幅采用边界处阻止继续向外积分的连续方程。
        if (efd <= gen.efd_min_pu and de < 0) or (efd >= gen.efd_max_pu and de > 0):
            de = 0.0
        if (pm <= gen.mechanical_power_min_pu and dp < 0) or (pm >= gen.mechanical_power_max_pu and dp > 0):
            dp = 0.0
        return (2*math.pi*gen.frequency*(speed-1),
                (pm-pe-gen.damping*(speed-1))/(2*gen.inertia_constant*speed),
                (efd-eq-(gen.d_axis_reactance_pu-xd)*id_)/gen.d_axis_open_circuit_time_constant,
                (-ed+(gen.q_axis_reactance_pu-xq)*iq)/gen.q_axis_open_circuit_time_constant,
                de, dp)

    if initial is None:
        initial = [gen.initial_rotor_angle, gen.initial_speed_pu, gen.initial_eq_prime_pu,
                   gen.initial_ed_prime_pu, gen.initial_efd_pu, gen.initial_mechanical_power_pu]
    solved = solve_ivp(rhs, (times[0], times[-1]), initial, t_eval=times, rtol=1e-11, atol=1e-12)
    assert solved.success
    return solved.y.T


def test_dq_terminal_equations_and_air_gap_power_at_initial_time() -> None:
    """独立解两个端口方程；q 轴电抗必须直接影响初始电流。"""
    for xq in (0.3, 0.7):
        gen = _base_generator(d_axis_transient_reactance_pu=0.2, q_axis_transient_reactance_pu=xq)
        result = Simulator(Circuit.from_components("dq_port", [gen,
            *[Resistor(f"R{p}", f"bus:{p}", "0", 9.0) for p in "abc"],
        ]), SimulationConfig(1e-4, 0.0)).run()
        row = result.rows[0]
        # R_load/Zbase + Rs = 1; Ed=0, Eq=1.
        iq = 1 / (1 + 0.2 * xq)
        id_ = xq * iq
        assert row["id_pu:GEN"] == pytest.approx(id_)
        assert row["iq_pu:GEN"] == pytest.approx(iq)
        assert row["p:GEN"] == pytest.approx(3000 * 0.9 * (id_**2 + iq**2))
        assert row["p_copper:GEN"] == pytest.approx(3000 * 0.1 * (id_**2 + iq**2))
        assert row["p_em:GEN"] == pytest.approx(row["p:GEN"] + row["p_copper:GEN"])


def test_internal_voltage_and_states_belong_to_same_output_time() -> None:
    gen = _base_generator(d_axis_transient_reactance_pu=0.2, initial_ed_prime_pu=0.1)
    result = Simulator(Circuit.from_components("state_time", [gen,
        *[Resistor(f"R{p}", f"bus:{p}", "0", 9.0) for p in "abc"],
    ]), SimulationConfig(1e-4, 0.01)).run()
    for row in result.rows:
        angle = 2 * math.pi * gen.frequency * row["time"] + row["rotor_angle:GEN"]
        expected = math.sqrt(2) * gen.base_phase_rms * np.array(dq_to_abc(
            -row["ed_prime_pu:GEN"], -row["eq_prime_pu:GEN"], angle))
        assert [row[f"e:GEN:{p}"] for p in "abc"] == pytest.approx(expected, abs=1e-10)


def test_generator_initial_row_preserves_dynamic_states_and_solves_current() -> None:
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
    assert row["ed_prime_pu:GEN"] == 0.0
    # 四阶模型的定子电流为代数量，不再把暂态电抗误作零电流电感。
    assert row["id_pu:GEN"] == pytest.approx(0.3 / 1.06)
    assert row["iq_pu:GEN"] == pytest.approx(1.0 / 1.06)
    for p in "abc":
        assert row[f"v:GEN:{p}"] == pytest.approx(9.0 * row[f"i:GEN:{p}"])


def test_park_generator_terminal_voltage_with_resistive_load() -> None:
    """零电抗、固定励磁退化为纯电阻分压，排除暂态电抗的混淆。"""

    components = [
        _base_generator(d_axis_reactance_pu=0.0, q_axis_reactance_pu=0.0,
                        q_axis_transient_reactance_pu=0.0,
                        mechanical_power_reference_pu=1.0, initial_mechanical_power_pu=1.0),
        Resistor("LA", "bus:a", "0", 9.0),
        Resistor("LB", "bus:b", "0", 9.0),
        Resistor("LC", "bus:c", "0", 9.0),
    ]
    circuit = Circuit.from_components("park_generator_resistive_load", components)
    config = SimulationConfig(time_step=1e-4, stop_time=0.1)
    simulator = Simulator(circuit, config)

    result = simulator.run()

    rms_values = three_phase_rms(result, ("v:bus:a", "v:bus:b", "v:bus:c"), start_time=0.06)
    assert list(rms_values.values()) == pytest.approx([90.0]*3, rel=1e-4)
    assert result.rows[-1]["vt_pu:GEN"] == pytest.approx(0.9)
    assert result.rows[-1]["speed_pu:GEN"] == pytest.approx(1.0)


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
    reference = _reference(components[0], 20.0, result.series("time"))
    measured = np.column_stack([result.series(key) for key in STATE_COLUMNS])
    assert np.max(np.abs(measured-reference)) < 0.002  # 显式欧拉，最大误差小于 0.2% 基值。


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


def test_example_10_equilibrium_ports_and_step_convergence() -> None:
    """与消去网络后的分段连续 ODE 对照，检查实际示例与一阶收敛。"""
    module = runpy.run_path(str(Path(__file__).parents[1] / "examples/10_park_generator_avr_governor.py"))
    common = np.linspace(0.0, 0.6, 3001)
    boundary = 1000
    case = module["define_case"]()
    gen = case.components[0]
    load_after = 1 / (1/30.0 + 1/(18.0 + case.components[4].closed_resistance))
    before = _reference(gen, 30.0, common[:boundary+1])
    after = _reference(gen, load_after, common[boundary:], before[-1])
    reference = np.vstack((before[:-1], after))
    errors = []
    for stride, dt in enumerate((2e-4, 1e-4, 5e-5)):
        case = module["define_case"]()
        gen = case.components[0]
        result = Simulator(Circuit.from_components(case.name, case.components),
                           replace(case.config, time_step=dt), events=case.events).run()
        sampled = np.column_stack([result.series(key) for key in STATE_COLUMNS])[::2**stride]
        errors.append(float(np.max(np.abs(sampled-reference))))
        assert sampled[:boundary+1] == pytest.approx(np.broadcast_to(sampled[0], sampled[:boundary+1].shape), abs=2e-11)
        assert len(result.event_log) == 3
        assert np.all(np.diff(result.series("time")) > 0)
        v = np.column_stack([result.series(f"v:GEN:{p}") for p in "abc"])
        i = np.column_stack([result.series(f"i:GEN:{p}") for p in "abc"])
        load = np.where(result.series("time") < 0.2, 30.0, load_after)
        assert np.max(np.abs(v - i * load[:, None])) < 1e-8
        assert np.max(np.abs(i.sum(axis=1))) < 1e-9
        id_, iq = result.series("id_pu:GEN"), result.series("iq_pu:GEN")
        ed, eq = result.series("ed_prime_pu:GEN"), result.series("eq_prime_pu:GEN")
        assert np.max(np.abs(result.series("vd_pu:GEN") - ed + 0.04*id_ - 0.3*iq)) < 1e-11
        assert np.max(np.abs(result.series("vq_pu:GEN") - eq + 0.04*iq + 0.08*id_)) < 1e-11
        expected_pe = 3000 * (ed*id_ + eq*iq + (0.3-0.08)*id_*iq)
        assert result.series("p_em:GEN") == pytest.approx(expected_pe, abs=1e-8)
        assert result.series("p_em:GEN") == pytest.approx(result.series("p:GEN") + result.series("p_copper:GEN"), abs=1e-9)
    assert errors[-1] < 0.002
    assert 1.9 < errors[0]/errors[1] < 2.1
    assert 1.9 < errors[1]/errors[2] < 2.1


@pytest.mark.parametrize("event_time", [0.0, 0.20005, 0.6])
def test_example_10_event_holds_dynamic_states_and_resolves_current(event_time) -> None:
    module = runpy.run_path(str(Path(__file__).parents[1] / "examples/10_park_generator_avr_governor.py"))
    case = module["define_case"]()
    gen = case.components[0]
    initial = [gen.initial_rotor_angle, gen.initial_speed_pu, gen.initial_eq_prime_pu,
               gen.initial_ed_prime_pu, gen.initial_efd_pu, gen.initial_mechanical_power_pu]
    result = Simulator(Circuit.from_components(case.name, case.components),
                       replace(case.config, stop_time=0.6),
                       events=[replace(event, time=event_time) for event in case.events]).run()
    event_row = next(row for row in result.rows if row["time"] == event_time)
    assert [event_row[key] for key in STATE_COLUMNS] == pytest.approx(initial, abs=2e-11)
    assert event_row["p:GEN"] > 2000.0
    assert len(result.event_log) == 3
    assert np.all(np.diff(result.series("time")) > 0)


@pytest.mark.parametrize("parameters, match", [
    ({"q_axis_transient_reactance_pu": -0.1}, "q_axis_transient_reactance_pu"),
    ({"q_axis_transient_reactance_pu": 2.0}, "q_axis_reactance_pu"),
    ({"d_axis_transient_reactance_pu": 2.0}, "d_axis_reactance_pu"),
    ({"inertia_constant": 0}, "inertia_constant"),
    ({"avr_time_constant": 0}, "avr_time_constant"),
    ({"governor_droop": 0}, "governor_droop"),
    ({"governor_time_constant": -1}, "governor_time_constant"),
    ({"d_axis_open_circuit_time_constant": 0}, "d_axis_open_circuit_time_constant"),
    ({"q_axis_open_circuit_time_constant": 0}, "q_axis_open_circuit_time_constant"),
    ({"damping": -1}, "damping"),
    ({"efd_min_pu": 2, "efd_max_pu": 1}, "efd_min_pu"),
    ({"initial_efd_pu": 6}, "initial_efd_pu"),
    ({"initial_mechanical_power_pu": -1}, "initial_mechanical_power_pu"),
    ({"mechanical_power_min_pu": 3}, "mechanical_power_min_pu"),
    ({"stator_resistance_pu": 0}, "端口阻抗"),
])
def test_generator_rejects_invalid_parameters_with_repair(parameters, match) -> None:
    with pytest.raises(ValueError, match=match) as error:
        _base_generator(**parameters)
    assert "请" in str(error.value)


@pytest.mark.parametrize("field", ["base_power", "base_phase_rms", "initial_rotor_angle", "initial_speed_pu",
                                  "q_axis_reactance_pu", "avr_gain", "mechanical_power_reference_pu", "efd_max_pu"])
@pytest.mark.parametrize("value", [float("nan"), float("inf"), True, "1"])
def test_generator_rejects_nonfinite_or_nonreal_parameters(field, value) -> None:
    with pytest.raises(ValueError, match=field):
        _base_generator(**{field: value})


def test_internal_source_constraint_reports_supported_connection() -> None:
    generator = _base_generator(d_axis_transient_reactance_pu=0.2)
    circuit = Circuit.from_components("internal_constraint", [generator,
        Capacitor("C", "GEN_internal:a", "0", 1.0),
        *[Resistor(f"R{p}", f"bus:{p}", "0", 9.0) for p in "abc"],
    ])
    with pytest.raises(RuntimeError, match="GEN.+请解除内部电势节点"):
        Simulator(circuit, SimulationConfig(1e-4, 0.0)).run()
