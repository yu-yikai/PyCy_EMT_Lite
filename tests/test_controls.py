"""
文件名称：test_controls.py
文件作用：验证阶段 3 控制模块、坐标变换、PLL 和 PWM 的基础行为。
"""

import math
from pathlib import Path
import runpy

import numpy as np
import pytest
from scipy.integrate import solve_ivp

from pycy_emt_lite.controls import (
    SRFPLL,
    FirstOrderLowPass,
    Limiter,
    PIController,
    SampleDelay,
    abc_to_dq,
    dq_to_abc,
    sine_pwm_duty,
    triangular_carrier,
)


def test_limiter_clamps_value() -> None:
    limiter = Limiter(-1.0, 1.0)

    assert limiter.step(2.0, 1e-3) == 1.0
    assert limiter.step(-2.0, 1e-3) == -1.0
    assert limiter.step(0.25, 1e-3) == 0.25


def test_pi_controller_integrates_and_limits_output() -> None:
    controller = PIController(2.0, 10.0, lower=-1.0, upper=1.0)

    first = controller.step(0.1, 0.01)
    second = controller.step(0.1, 0.01)
    saturated = controller.step(10.0, 0.01)

    assert math.isclose(first, 0.21, rel_tol=0.0, abs_tol=1e-12)
    assert second > first
    assert saturated == 1.0


def test_low_pass_filter_matches_backward_euler_first_step() -> None:
    low_pass = FirstOrderLowPass(time_constant=0.1)

    output = low_pass.step(1.0, 0.1)

    assert math.isclose(output, 0.5, rel_tol=0.0, abs_tol=1e-12)


def test_sample_delay_returns_history_before_new_input() -> None:
    delay = SampleDelay(steps=2, initial_value=-1.0)

    assert delay.step(1.0, 1e-3) == -1.0
    assert delay.step(2.0, 1e-3) == -1.0
    assert delay.step(3.0, 1e-3) == 1.0


def test_abc_dq_round_trip_for_balanced_signal() -> None:
    angle = 0.4
    original = dq_to_abc(2.0, -0.5, angle)

    d_axis, q_axis = abc_to_dq(*original, angle)

    assert math.isclose(d_axis, 2.0, rel_tol=0.0, abs_tol=1e-12)
    assert math.isclose(q_axis, -0.5, rel_tol=0.0, abs_tol=1e-12)


def test_srf_pll_tracks_balanced_voltage_frequency() -> None:
    frequency = 2.0 * math.pi * 50.0
    pll = SRFPLL(80.0, 1000.0, nominal_frequency=frequency, initial_angle=-math.pi / 2.0)
    time_step = 1e-4
    amplitude = 325.0

    state = None
    for index in range(1, 1000):
        time = index * time_step
        angle = frequency * time
        voltages = (
            amplitude * math.sin(angle),
            amplitude * math.sin(angle - 2.0 * math.pi / 3.0),
            amplitude * math.sin(angle + 2.0 * math.pi / 3.0),
        )
        state = pll.step(voltages, time_step)

    assert state is not None
    assert abs(state.q_axis_voltage) < 5.0
    assert math.isclose(state.frequency, frequency, rel_tol=0.0, abs_tol=2.0)


def test_srf_pll_preserves_exact_lock_at_current_sample_times() -> None:
    omega = 2.0 * math.pi * 50.0
    initial_angle = 0.4
    amplitude = 325.0
    pll = SRFPLL(80.0, 1000.0, nominal_frequency=omega, initial_angle=initial_angle)
    time = 0.0
    for step in (1e-4, 2.5e-4, 1.7e-4) * 20:
        time += step
        angle = initial_angle + omega * time
        voltages = tuple(amplitude * math.cos(angle + offset) for offset in (0.0, -2*math.pi/3, 2*math.pi/3))
        state = pll.step(voltages, step)
        angle_error = math.remainder(state.angle - angle, 2 * math.pi)
        assert angle_error == pytest.approx(0.0, abs=1e-12)
        assert state.frequency == pytest.approx(omega, abs=1e-10)
        assert state.d_axis_voltage == pytest.approx(amplitude, abs=1e-10)
        assert state.q_axis_voltage == pytest.approx(0.0, abs=1e-10)


def test_srf_pll_reports_dq_at_its_returned_angle() -> None:
    omega, step, amplitude = 2 * math.pi * 50, 1e-3, 325.0
    initial_angle, grid_angle = 0.2, 0.8
    pll = SRFPLL(0.0, 0.0, nominal_frequency=omega, initial_angle=initial_angle)
    voltages = tuple(amplitude * math.cos(grid_angle + offset) for offset in (0.0, -2*math.pi/3, 2*math.pi/3))
    state = pll.step(voltages, step)
    assert state.angle == pytest.approx(initial_angle + omega * step)
    phase_error = grid_angle - state.angle
    assert state.d_axis_voltage == pytest.approx(amplitude * math.cos(phase_error), abs=1e-12)
    assert state.q_axis_voltage == pytest.approx(amplitude * math.sin(phase_error), abs=1e-12)


@pytest.mark.parametrize("step", [0.0, -1.0, True, None, "0.1", math.nan, math.inf, -math.inf])
def test_srf_pll_rejects_invalid_interval_without_advancing(step) -> None:
    pll = SRFPLL(80.0, 1000.0, initial_angle=0.4)
    voltages = (325.0, -162.5, -162.5)
    with pytest.raises(ValueError, match="time_step.*请.*有限正实数"):
        pll.step(voltages, step)
    fresh = SRFPLL(80.0, 1000.0, initial_angle=0.4)
    assert pll.step(voltages, 1e-4) == fresh.step(voltages, 1e-4)


def test_srf_pll_phase_and_frequency_converge_to_independent_continuous_ode() -> None:
    kp, ki, amplitude = 80.0, 1000.0, 325.0
    nominal, grid_omega = 2 * math.pi * 50, 2 * math.pi * 52
    initial_angle, offset = 0.4, 0.7
    times = np.linspace(0.0, 0.2, 2001)

    def reference_rhs(time, state):
        phase_error = grid_omega * time + offset - state[0]
        cosine, sine = math.cos(phase_error), math.sin(phase_error)
        error = sine / max(abs(cosine), abs(sine), 1 / amplitude)
        return nominal + kp * error + state[1], ki * error

    reference = solve_ivp(reference_rhs, (0.0, 0.2), (initial_angle, 0.0),
                          t_eval=times, method="DOP853", rtol=1e-11, atol=1e-12)
    assert reference.success
    # The declared initial frequency is nominal; compare feedback frequencies after t=0.
    reference_frequency = [reference_rhs(t, state)[0] for t, state in zip(times[1:], reference.y.T[1:])]
    errors = []
    for stride in (1, 2, 4):
        step = 1e-4 / stride
        pll = SRFPLL(kp, ki, nominal_frequency=nominal, initial_angle=initial_angle)
        angles, frequencies = [], []
        for index in range(1, 2000 * stride + 1):
            angle = grid_omega * (index * step) + offset
            voltages = tuple(amplitude * math.cos(angle + phase) for phase in (0.0, -2*math.pi/3, 2*math.pi/3))
            state = pll.step(voltages, step)
            if index % stride == 0:
                angles.append(state.angle)
                frequencies.append(state.frequency)
        angle_error = [abs(math.remainder(a - b, 2 * math.pi)) for a, b in zip(angles, reference.y[0, 1:])]
        errors.append((max(angle_error), np.max(np.abs(np.array(frequencies) - reference_frequency))))
    errors = np.array(errors)
    assert np.all(errors[-1] < [6.2e-4, 0.055])  # rad, rad/s over 0 < t <= 0.2 s
    assert np.all((errors[:-1] / errors[1:] > 1.95) & (errors[:-1] / errors[1:] < 2.05))


@pytest.mark.parametrize("stop", [0.0, 3e-4])
def test_pll_example_records_initial_state_before_advancing(monkeypatch, stop) -> None:
    example = runpy.run_path(str(Path(__file__).resolve().parents[1] / "examples/11_pll_dynamic_response.py"))
    namespace = example["main"].__globals__
    captured = []
    monkeypatch.setitem(namespace, "STOP_TIME", stop)
    monkeypatch.setitem(namespace, "plot_series", lambda result, *args, **kwargs: captured.append(result))
    example["main"]()
    result = captured[0]
    assert len(result.rows) == round(stop / namespace["TIME_STEP"]) + 1
    assert result.rows[-1]["time"] == pytest.approx(stop)
    first = result.rows[0]
    assert first["time"] == 0.0
    assert first["angle"] == 0.0
    assert first["frequency"] == 2 * math.pi * namespace["FREQUENCY"]
    # cos-based voltage-vector angle is the sinusoidal source phase minus pi/2.
    amplitude = math.sqrt(2) * namespace["PHASE_RMS"]
    offset = math.radians(namespace["ANGLE_OFFSET_DEG"]) - math.pi / 2
    for row in result.rows:
        phase_error = 2 * math.pi * namespace["FREQUENCY"] * row["time"] + offset - row["angle"]
        assert row["q_axis_voltage"] == pytest.approx(amplitude * math.sin(phase_error), abs=1e-10)


def test_pll_example_rejects_non_integer_stop_before_plotting(monkeypatch) -> None:
    example = runpy.run_path(str(Path(__file__).resolve().parents[1] / "examples/11_pll_dynamic_response.py"))
    namespace = example["main"].__globals__
    monkeypatch.setitem(namespace, "STOP_TIME", 2.5e-4)
    monkeypatch.setitem(namespace, "plot_series", lambda *args, **kwargs: pytest.fail("invalid configuration reached plotting"))
    with pytest.raises(ValueError, match="stop_time.*time_step.*整数倍.*请"):
        example["main"]()


def test_pwm_helpers_generate_expected_values() -> None:
    assert math.isclose(triangular_carrier(0.0, 1000.0), -1.0, rel_tol=0.0, abs_tol=1e-12)
    assert math.isclose(triangular_carrier(0.00025, 1000.0), 0.0, rel_tol=0.0, abs_tol=1e-12)
    assert math.isclose(sine_pwm_duty(0.8, math.pi / 2.0), 0.9, rel_tol=0.0, abs_tol=1e-12)
