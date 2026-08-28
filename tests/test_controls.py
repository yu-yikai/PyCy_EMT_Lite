"""
文件名称：test_controls.py
文件作用：验证阶段 3 控制模块、坐标变换、PLL 和 PWM 的基础行为。
"""

import math

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


def test_pwm_helpers_generate_expected_values() -> None:
    assert math.isclose(triangular_carrier(0.0, 1000.0), -1.0, rel_tol=0.0, abs_tol=1e-12)
    assert math.isclose(triangular_carrier(0.00025, 1000.0), 0.0, rel_tol=0.0, abs_tol=1e-12)
    assert math.isclose(sine_pwm_duty(0.8, math.pi / 2.0), 0.9, rel_tol=0.0, abs_tol=1e-12)
