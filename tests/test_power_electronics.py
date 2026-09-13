"""
文件名称：test_power_electronics.py
文件作用：验证阶段 3 电力电子简化元件和滤波器组合。
"""

import math
from dataclasses import replace
from pathlib import Path
import runpy

import numpy as np
import pytest
from scipy.integrate import solve_ivp

from pycy_emt_lite import (
    Circuit,
    IdealSwitch,
    Resistor,
    SimulationConfig,
    Simulator,
    VoltageSource,
)
from pycy_emt_lite.components.switching import Breaker, Fault
from pycy_emt_lite.converters import LCFilter, LCLFilter, LFilter


@pytest.mark.parametrize("assembly,parameter", [
    (LFilter("F", "in", "out", 0.01), "inductance"),
    (LFilter("F", "in", "out", 0.01), "series_resistance"),
    (LCFilter("F", "in", "out", "0", 0.01, 1e-4), "inductance"),
    (LCFilter("F", "in", "out", "0", 0.01, 1e-4), "capacitance"),
    (LCFilter("F", "in", "out", "0", 0.01, 1e-4), "series_resistance"),
    *[(LCLFilter("F", "in", "cap", "out", "0", 0.01, 0.005, 1e-4), parameter)
      for parameter in ("converter_inductance", "grid_inductance", "capacitance",
                        "converter_resistance", "grid_resistance", "damping_resistance")],
])
@pytest.mark.parametrize("value", [-1.0, math.nan, math.inf, -math.inf, True, "0.1", None])
def test_filter_rejects_invalid_parameter_at_construction(assembly, parameter, value) -> None:
    with pytest.raises(ValueError, match=rf"F.*{parameter}.*请"):
        replace(assembly, **{parameter: value})


@pytest.mark.parametrize("assembly,parameter", [
    (LFilter("F", "in", "out", 0.01), "inductance"),
    (LCFilter("F", "in", "out", "0", 0.01, 1e-4), "inductance"),
    (LCFilter("F", "in", "out", "0", 0.01, 1e-4), "capacitance"),
    (LCLFilter("F", "in", "cap", "out", "0", 0.01, 0.005, 1e-4), "converter_inductance"),
    (LCLFilter("F", "in", "cap", "out", "0", 0.01, 0.005, 1e-4), "grid_inductance"),
    (LCLFilter("F", "in", "cap", "out", "0", 0.01, 0.005, 1e-4), "capacitance"),
])
def test_filter_rejects_zero_storage_parameter(assembly, parameter) -> None:
    with pytest.raises(ValueError, match=rf"{parameter}.*大于 0.*请"):
        replace(assembly, **{parameter: 0.0})


def test_filter_accepts_numpy_values_and_zero_resistances() -> None:
    assembly = LCLFilter("F", "in", "cap", "out", "0", np.float64(0.01),
                         np.float64(0.005), np.float64(1e-4), np.int64(0), 0.0, 0.0)
    assert [component.name for component in assembly.components()] == ["F:converter:L", "F:C", "F:grid:L"]


@pytest.mark.parametrize(
    ("closed_resistance", "open_conductance"),
    ((math.nan, 1e-9), (0.1, math.inf), (0.1, -math.inf)),
)
def test_ideal_switch_rejects_nonfinite_conductance_parameters(
    closed_resistance: float, open_conductance: float
) -> None:
    with pytest.raises(ValueError):
        IdealSwitch(
            "S1",
            "source",
            "load",
            closed_resistance=closed_resistance,
            open_conductance=open_conductance,
        )


@pytest.mark.parametrize("factory", (lambda value: Fault("F", "node", value), lambda value: Breaker("B", "node", "0", closed_resistance=value)))
@pytest.mark.parametrize("value", (math.nan, math.inf, -math.inf))
def test_fault_and_breaker_reject_nonfinite_resistance(factory: object, value: float) -> None:
    with pytest.raises(ValueError, match="有限正数"):
        factory(value)  # type: ignore[operator]


def test_ideal_switch_accepts_zero_open_conductance() -> None:
    switch = IdealSwitch("S1", "source", "load", open_conductance=0.0)

    assert switch.open_conductance == 0.0


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


@pytest.mark.parametrize("resistance", [0.0, 0.5])
@pytest.mark.parametrize("method,order_ratio", [("trapezoidal", 4.0), ("backward_euler", 2.0)])
def test_lc_filter_startup_matches_ode_kcl_and_energy(resistance, method, order_ratio) -> None:
    inductance, capacitance, load = 0.01, 1e-4, 10.0

    def source(time):
        return 10 * np.cos(2 * np.pi * 50 * time)

    # 独立的串联 L、并联 C/负荷方程，状态依次为 iL (A)、vC (V)。
    def derivative(time, state):
        current, voltage = state
        return [(source(time) - resistance * current - voltage) / inductance,
                (current - voltage / load) / capacitance]

    reference = solve_ivp(derivative, (0.0, 0.02), [0.0, 0.0], method="DOP853",
                          rtol=1e-11, atol=1e-12, dense_output=True)
    assert reference.success
    errors = []
    for step in [2e-5, 1e-5]:
        assembly = LCFilter("F", "in", "out", "0", inductance, capacitance, resistance)
        components = [VoltageSource("V", "in", "0", source), Resistor("LOAD", "out", "0", load),
                      *assembly.components()]
        result = Simulator(Circuit.from_components("lc_filter", components),
                           SimulationConfig(step, 0.02, method=method)).run()
        time = result.series("time")
        current, voltage = result.series("i:F:L"), result.series("v:out")
        np.testing.assert_allclose([current[0], voltage[0]], 0.0, atol=1e-12)
        np.testing.assert_allclose(-result.series("i:V"), current, atol=1e-12)
        np.testing.assert_allclose(current, result.series("i:F:C") + voltage / load, atol=1e-11)

        state = np.array([current, voltage])
        stride = round(2e-5 / step)
        errors.append(np.max(np.abs(state[:, ::stride] - reference.sol(time[::stride])), axis=1))
        energy = 0.5 * (inductance * current**2 + capacitance * voltage**2)
        if method == "trapezoidal":
            i, v = (state[:, :-1] + state[:, 1:]) / 2
            applied = (source(time[:-1]) + source(time[1:])) / 2
            numerical_loss = 0.0
        else:
            i, v = state[:, 1:]
            applied = source(time[1:])
            numerical_loss = 0.5 * (inductance * np.diff(current)**2 + capacitance * np.diff(voltage)**2)
        work = np.cumsum(np.diff(time) * (applied * i - resistance * i**2 - v**2 / load) - numerical_loss)
        np.testing.assert_allclose(work, energy[1:] - energy[0], atol=1e-11, rtol=0)

    limits = [8e-6, 7e-5] if method == "trapezoidal" else [0.005, 0.05]
    assert np.all(errors[1] < limits), errors  # A、V，整个 0–0.02 s 暂态
    np.testing.assert_allclose(errors[0] / errors[1], order_ratio, rtol=0.08)


@pytest.mark.parametrize("resistances", [(0.0, 0.0, 0.0), (0.4, 0.3, 2.0)])
@pytest.mark.parametrize("method,order_ratio", [("trapezoidal", 4.0), ("backward_euler", 2.0)])
def test_lcl_filter_two_port_startup_matches_ode_kcl_and_energy(resistances, method, order_ratio) -> None:
    l1, l2, capacitance = 0.01, 0.005, 1e-4
    r1, r2, damping = resistances

    def converter_voltage(time):
        return 10 * np.cos(2 * np.pi * 50 * time)

    def grid_voltage(time):
        return 6 * np.cos(2 * np.pi * 50 * time - 0.2)

    # 两端都接电压源；i1 流入滤波器，i2 流向电网，Rd 与 C 串联。
    def derivative(time, state):
        i1, i2, vc = state
        ic = i1 - i2
        junction = vc + damping * ic
        return [(converter_voltage(time) - r1 * i1 - junction) / l1,
                (junction - r2 * i2 - grid_voltage(time)) / l2, ic / capacitance]

    reference = solve_ivp(derivative, (0.0, 0.02), [0.0, 0.0, 0.0], method="DOP853",
                          rtol=1e-11, atol=1e-12, dense_output=True)
    assert reference.success
    errors = []
    # 无阻尼模态的后向欧拉衰减会在多周期内累积，使用 5/2.5 μs 检查收敛。
    for step in [5e-6, 2.5e-6]:
        assembly = LCLFilter("F", "in", "cap", "grid", "0", l1, l2, capacitance, r1, r2, damping)
        components = [VoltageSource("V1", "in", "0", converter_voltage),
                      VoltageSource("V2", "grid", "0", grid_voltage), *assembly.components()]
        result = Simulator(Circuit.from_components("lcl_filter", components),
                           SimulationConfig(step, 0.02, method=method)).run()
        time = result.series("time")
        i1, i2, ic = [result.series(f"i:F:{suffix}") for suffix in ("converter:L", "grid:L", "C")]
        vc = result.series("v:F:damping" if damping else "v:cap")
        state = np.array([i1, i2, vc])
        np.testing.assert_allclose(state[:, 0], 0.0, atol=1e-12)
        np.testing.assert_allclose(-result.series("i:V1"), i1, atol=1e-12)
        np.testing.assert_allclose(result.series("i:V2"), i2, atol=1e-12)
        np.testing.assert_allclose(i1 - i2, ic, atol=1e-11)
        np.testing.assert_allclose(result.series("v:cap"), vc + damping * ic, atol=1e-11)
        stride = round(5e-6 / step)
        errors.append(np.max(np.abs(state[:, ::stride] - reference.sol(time[::stride])), axis=1))

        energy = 0.5 * (l1 * i1**2 + l2 * i2**2 + capacitance * vc**2)
        if method == "trapezoidal":
            first, second, _ = (state[:, :-1] + state[:, 1:]) / 2
            v1 = (converter_voltage(time[:-1]) + converter_voltage(time[1:])) / 2
            v2 = (grid_voltage(time[:-1]) + grid_voltage(time[1:])) / 2
            numerical_loss = 0.0
        else:
            first, second, _ = state[:, 1:]
            v1, v2 = converter_voltage(time[1:]), grid_voltage(time[1:])
            numerical_loss = 0.5 * (l1 * np.diff(i1)**2 + l2 * np.diff(i2)**2 + capacitance * np.diff(vc)**2)
        power = v1 * first - v2 * second - r1 * first**2 - r2 * second**2 - damping * (first - second)**2
        work = np.cumsum(np.diff(time) * power - numerical_loss)
        np.testing.assert_allclose(work, energy[1:] - energy[0], atol=1e-11, rtol=0)

    limits = [3e-5, 5e-5, 5e-4] if method == "trapezoidal" else [0.04, 0.08, 0.6]
    assert np.all(errors[1] < limits), errors  # A、A、V，包含无阻尼振荡
    np.testing.assert_allclose(errors[0] / errors[1], order_ratio, rtol=0.08)


def test_pwm_bridge_phasors_current_balance_and_step_sensitivity() -> None:
    example = runpy.run_path(str(Path(__file__).parents[1] / "examples/12_two_level_pwm_generator.py"))
    omega = 2 * math.pi * example["FUNDAMENTAL_FREQUENCY"]
    phase_shifts = np.array([math.pi / 2, math.pi / 2 - 2 * math.pi / 3, math.pi / 2 + 2 * math.pi / 3])
    snapshots = []
    # 0.05–0.10 s 是同一个物理窗口，含三个基波周期及 50 个载波周期。
    for step in [5e-6, 2.5e-6, 1.25e-6]:
        case = example["define_case"]()
        switch = next(component for component in case.components if isinstance(component, IdealSwitch))
        conductance_on = 1 / switch.closed_resistance
        conductance_off = switch.open_conductance
        switch_resistance = 1 / (conductance_on + conductance_off)
        result = Simulator(Circuit.from_components(case.name, case.components), replace(case.config, time_step=step, stop_time=0.1)).run()
        time = result.series("time")
        window = time >= 0.05
        time = time[window]
        current = np.array([result.series(f"i:L{phase}")[window] for phase in "abc"])
        voltage = np.array([(result.series(f"v:phase_{phase}") - result.series("v:load_n"))[window] for phase in "abc"])
        upper = np.array([result.series(f"state:S{phase}_upper")[window] for phase in "abc"])
        lower = np.array([result.series(f"state:S{phase}_lower")[window] for phase in "abc"])
        np.testing.assert_array_equal(upper + lower, 1.0)
        np.testing.assert_allclose(current.sum(axis=0), 0.0, atol=1e-9)
        for phase in "abc":
            assert result.rows[0][f"i:L{phase}"] == pytest.approx(0.0, abs=1e-12)

        # 互补桥臂的戴维南电压减去浮置星点电位和导通压降。
        pole = example["DC_VOLTAGE"] * (upper * conductance_on + lower * conductance_off) * switch_resistance
        np.testing.assert_allclose(voltage, pole - pole.mean(axis=0) - switch_resistance * current, atol=1e-8)

        def fundamental(values):
            sine = np.trapezoid(values * np.sin(omega * time), time, axis=1)
            cosine = np.trapezoid(values * np.cos(omega * time), time, axis=1)
            return math.sqrt(2) * (sine + 1j * cosine) / (time[-1] - time[0])

        voltage_phasor, current_phasor = fundamental(voltage), fundamental(current)
        impedance = complex(example["LOAD_RESISTANCE"], omega * example["LOAD_INDUCTANCE"])
        np.testing.assert_allclose(voltage_phasor / current_phasor, impedance, atol=2e-6, rtol=0)
        # 平均模型只作基波参考，包含零阶保持及开关导通电阻，不代表开关纹波。
        hold = np.sinc(example["FUNDAMENTAL_FREQUENCY"] * example["CONTROL_SAMPLE_TIME"]) * np.exp(-1j * omega * example["CONTROL_SAMPLE_TIME"] / 2)
        reference = example["MODULATION_INDEX"] * example["DC_VOLTAGE"] / (2 * math.sqrt(2)) * hold * np.exp(1j * phase_shifts) / (impedance + switch_resistance)
        assert np.max(np.abs(current_phasor - reference) / np.abs(reference)) < 0.003
        stride = round(5e-6 / step)
        snapshots.append((time[::stride], current[:, ::stride], current_phasor))

    fine_time, fine_current, fine_phasor = snapshots[-1]
    waveform_errors = []
    for time, current, phasor in snapshots[:2]:
        np.testing.assert_allclose(time, fine_time, atol=1e-14, rtol=0)
        waveform_errors.append(np.sqrt(np.trapezoid((current - fine_current)**2, time, axis=1) / (time[-1] - time[0])))
    assert np.max(waveform_errors[0]) < 0.6  # A，默认 5 μs 相对细网格的三相最大 RMS 差
    assert np.max(waveform_errors[1]) < 0.3
    assert np.all(waveform_errors[1] < 0.6 * waveform_errors[0])
    assert np.max(np.abs(snapshots[0][2] - fine_phasor) / np.abs(fine_phasor)) < 0.0025
    assert np.max(np.abs(snapshots[1][2] - fine_phasor) / np.abs(fine_phasor)) < 0.0012
