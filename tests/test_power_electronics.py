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

from pycy_emt_lite import (
    Circuit,
    IdealSwitch,
    SimulationConfig,
    Simulator,
    VoltageSource,
)
from pycy_emt_lite.components.switching import Breaker, Fault
from pycy_emt_lite.converters import LCLFilter


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
