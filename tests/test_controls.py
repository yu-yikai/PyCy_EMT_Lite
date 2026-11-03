"""
文件名称：test_controls.py
文件作用：验证控制模块、坐标变换、PLL 和 PWM 的基础行为。
"""

import math
import runpy
from pathlib import Path

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
    carrier_compare,
    dq_to_abc,
    sine_pwm_duty,
    triangular_carrier,
)
from pycy_emt_lite.controls.vsc import VSCControlConfig, VSCController


def test_delay_rejects_huge_allocation_before_buffer_creation() -> None:
    with pytest.raises(ValueError, match="SampleDelay.steps.*上限"):
        SampleDelay(1_000_001)


@pytest.mark.parametrize("parameter", ["proportional_gain", "integral_gain", "nominal_frequency"])
def test_pll_rejects_config_mutation_without_advancing_state(parameter) -> None:
    pll = SRFPLL(1.0, 2.0)
    before = (pll.angle, pll.frequency, pll._controller.integrator)
    setattr(pll, parameter, getattr(pll, parameter) + 1.0)
    with pytest.raises(ValueError, match=rf"{parameter}.*请"):
        pll.step((1.0, -0.5, -0.5), 0.001)
    assert (pll.angle, pll.frequency, pll._controller.integrator) == before


@pytest.mark.parametrize("ki,error,expected", [(-1.0, 1.0, 1.5), (-1.0, -1.0, 2.0), (1.0, -1.0, 1.5), (1.0, 1.0, 2.0), (0.0, 1.0, 2.0)])
def test_pi_antiwindup_follows_integral_increment(ki, error, expected) -> None:
    controller = PIController(0.0, ki, lower=-1.0, upper=1.0)
    controller.reset(2.0)
    assert controller.step(error, 0.5) == 1.0
    assert controller.integrator == expected


def test_vsc_pll_trace_matches_actual_normalized_error() -> None:
    controller = VSCController("S", 50.0, 420e3, 230e3, 200e6, 1000.0)
    controller.pll.angle = math.pi / 2
    row = {"time": 0.0, "v:S:dc_p": 200e3, "v:S:dc_n": -200e3}
    for phase, voltage in zip("abc", (200.0, -100.0, -100.0), strict=True):
        row.update({f"v:S:hv:{phase}": voltage, f"v:S:lv:{phase}": 0.0, f"i:S:reactor:{phase}": 0.0})
    traces = controller.sample(row)
    assert traces["S:PLL_Vq_pu"] == pytest.approx(-1.0)


def _vsc_row(time, *, vac=1.0, voltage_dq=(30.0, 0.0), current_dq=(0.0, 0.0), vdc=400.0):
    """Balanced 50 Hz samples, with explicit phase projection independent of transforms."""
    row = {"time": time, "v:S:dc_p": vdc / 2, "v:S:dc_n": -vdc / 2}
    for phase, offset in zip("abc", (0.0, -2 * math.pi / 3, 2 * math.pi / 3), strict=True):
        angle = 2 * math.pi * 50 * time + offset
        cosine, sine = math.cos(angle), math.sin(angle)
        row[f"v:S:hv:{phase}"] = math.sqrt(2 / 3) * 100.0 * vac * cosine
        row[f"v:S:lv:{phase}"] = voltage_dq[0] * cosine - voltage_dq[1] * sine
        row[f"i:S:reactor:{phase}"] = current_dq[0] * cosine - current_dq[1] * sine
    return row


@pytest.mark.parametrize("id_demand", [0.0, 8.0])
@pytest.mark.parametrize("vac_error", [-0.5, 0.5])
def test_vsc_q_current_circle_freezes_only_clipped_vac_integral_and_releases(id_demand, vac_error) -> None:
    # P/(1.5 Vd) gives Id=0 or 8 A; the independent q margin is 10 or 6 A.
    step = 1e-3
    config = VSCControlConfig(current_limit=10.0, ac_kp=16.0, ac_ki=1000.0,
                              current_kp=1.0, current_ki=10.0, dc_voltage=400.0,
                              ramp_start=0.0, ramp_duration=step / 2)
    controller = VSCController("S", 50.0, 100.0, 100.0, 1.5 * 30.0 * id_demand, 1000.0, config)
    initial = controller.sample(_vsc_row(0.0, vac=1.0 - vac_error))
    assert (initial["S:Id_ref"], initial["S:Iq_ref"], controller.ac_pi.integrator) == (0.0, 0.0, 0.0)

    traces = controller.sample(_vsc_row(step, vac=1.0 - vac_error))
    increment = 1000.0 * vac_error * step
    candidate_q = 16.0 * vac_error + increment  # ±8.5 A, below the PI's own ±10 A limits.
    q_margin = math.sqrt(10.0**2 - id_demand**2)
    expected_q = math.copysign(min(abs(candidate_q), q_margin), vac_error)
    expected_integral = 0.0 if id_demand == 8.0 else increment
    assert traces["S:Id_ref"] == pytest.approx(id_demand)
    assert traces["S:Iq_ref"] == pytest.approx(expected_q)
    assert math.hypot(traces["S:Id_ref"], traces["S:Iq_ref"]) <= 10.0 + 1e-12
    assert controller.ac_pi.integrator == pytest.approx(expected_integral)

    # Remove the active-power demand to restore all 10 A of q margin at the next sample.
    controller.active_power = 0.0
    released = controller.sample(_vsc_row(2 * step, vac=1.0 - vac_error))
    assert released["S:Id_ref"] == pytest.approx(0.0)
    assert released["S:Iq_ref"] == pytest.approx(16.0 * vac_error + expected_integral + increment)
    assert controller.ac_pi.integrator == pytest.approx(expected_integral + increment)


def test_vsc_voltage_vector_limit_freezes_both_integrals_and_preserves_direction_on_release() -> None:
    step, inductance = 1e-3, 0.01
    config = VSCControlConfig(dc_voltage=400.0, reactor_inductance=inductance,
                              current_kp=2.0, current_ki=20.0, modulation_limit=0.9,
                              ac_kp=1.0, ac_ki=1.0)
    controller = VSCController("S", 50.0, 100.0, 100.0, 0.0, 1000.0, config)
    measurements = {"voltage_dq": (90.0, 60.0), "current_dq": (3.0, -4.0)}
    controller.sample(_vsc_row(0.0, vdc=100.0, **measurements))
    held_modulation = controller.modulation
    # Constant dq measurements keep the filters settled; errors are exactly (-3, +4) A.
    errors = (-3.0, 4.0)
    increments = tuple(20.0 * error * step for error in errors)
    feedforward = (90.0 - 2 * math.pi * 50 * inductance * 4.0,
                   60.0 - 2 * math.pi * 50 * inductance * 3.0)
    for index, vdc in enumerate((100.0, 400.0, 400.0), start=1):
        traces = controller.sample(_vsc_row(index * step, vdc=vdc, **measurements))
        # At 100 V the 45 V vector allowance saturates; at 400 V, 180 V releases it.
        candidate_integrals = tuple(increment * max(index - 1, 1) for increment in increments)
        raw_voltage = tuple(v - 2.0 * error - integral
                            for v, error, integral in zip(feedforward, errors, candidate_integrals, strict=True))
        allowance = 0.9 * vdc / 2
        assert (math.hypot(*raw_voltage) > allowance) == (index == 1)
        expected_integrals = (0.0, 0.0) if index == 1 else candidate_integrals
        assert (controller.d_pi.integrator, controller.q_pi.integrator) == pytest.approx(expected_integrals, abs=1e-12)
        assert (traces["S:Id_ref"], traces["S:Iq_ref"]) == pytest.approx((0.0, 0.0), abs=1e-12)
        assert tuple(traces[f"S:m{phase}"] for phase in "abc") == held_modulation

        modulation = tuple(traces[f"S:m{phase}_next"] for phase in "abc")
        # Independent phase projections measure vector magnitude and direction, so per-phase
        # clipping cannot pass just by satisfying the individual phase bounds.
        angles = tuple(2 * math.pi * 50 * index * step + phase for phase in (0, -2 * math.pi / 3, 2 * math.pi / 3))
        projected = (2 / 3 * sum(m * math.cos(a) for m, a in zip(modulation, angles, strict=True)),
                     -2 / 3 * sum(m * math.sin(a) for m, a in zip(modulation, angles, strict=True)))
        expected_magnitude = min(2 * math.hypot(*raw_voltage) / vdc, 0.9)
        expected_vector = tuple(expected_magnitude * value / math.hypot(*raw_voltage) for value in raw_voltage)
        assert projected == pytest.approx(expected_vector, abs=1e-12)
        assert math.hypot(*projected) == pytest.approx(expected_magnitude, abs=1e-12)
        assert all(math.isfinite(value) and abs(value) <= 0.9 + 1e-12 for value in modulation)
        held_modulation = modulation


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


@pytest.mark.parametrize("amplitude", [0.1, 1.0, 325.0])
def test_srf_pll_phase_and_frequency_converge_to_independent_continuous_ode(amplitude) -> None:
    kp, ki = 80.0, 1000.0
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
    reference_frequency = [reference_rhs(t, state)[0] for t, state in zip(times[1:], reference.y.T[1:], strict=True)]
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
        angle_error = [abs(math.remainder(a - b, 2 * math.pi)) for a, b in zip(angles, reference.y[0, 1:], strict=True)]
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


@pytest.mark.parametrize("factory", [lambda: Limiter(-1, 1), lambda: PIController(2, 10),
                                      lambda: FirstOrderLowPass(0.1), lambda: SampleDelay(2)])
@pytest.mark.parametrize("invalid", [math.nan, math.inf, -math.inf, True, "1", None])
def test_control_blocks_reject_invalid_input_and_interval_without_state_change(factory, invalid) -> None:
    block, reference = factory(), factory()
    block.step(0.2, 0.01)
    reference.step(0.2, 0.01)
    for value, step in ((invalid, 0.01), (0.3, invalid)):
        with pytest.raises(ValueError, match="请"):
            block.step(value, step)
    with pytest.raises(ValueError, match="请"):
        block.reset(invalid)
    for value in (0.3, 0.4, 0.5):
        assert block.step(value, 0.01) == reference.step(value, 0.01)


@pytest.mark.parametrize("factory", [
    lambda v: Limiter(v, 1), lambda v: Limiter(-1, v),
    lambda v: PIController(v, 1), lambda v: PIController(1, v),
    lambda v: PIController(1, 1, lower=v), lambda v: PIController(1, 1, upper=v),
    lambda v: FirstOrderLowPass(v), lambda v: SampleDelay(1, initial_value=v),
    lambda v: SRFPLL(v, 1), lambda v: SRFPLL(1, v),
    lambda v: SRFPLL(1, 1, nominal_frequency=v), lambda v: SRFPLL(1, 1, initial_angle=v),
])
@pytest.mark.parametrize("invalid", [math.nan, math.inf, True])
def test_control_construction_rejects_invalid_numeric_parameters(factory, invalid) -> None:
    with pytest.raises(ValueError, match="请"):
        factory(invalid)


@pytest.mark.parametrize("invalid", [-1, 1.5, True, math.nan])
def test_sample_delay_requires_nonnegative_integer_steps(invalid) -> None:
    with pytest.raises(ValueError, match="steps.*请"):
        SampleDelay(invalid)


@pytest.mark.parametrize("voltages", [(math.nan, 0, 0), (0, math.inf, 0), (0, 0, -math.inf),
                                      (True, 0, 0), ("1", 0, 0), (None, 0, 0), (1, 2), None])
def test_pll_rejects_invalid_voltage_sample_without_state_change(voltages) -> None:
    pll, reference = SRFPLL(80, 1000), SRFPLL(80, 1000)
    valid = (325.0, -162.5, -162.5)
    pll.step(valid, 1e-4)
    reference.step(valid, 1e-4)
    with pytest.raises(ValueError, match="voltages_abc.*请"):
        pll.step(voltages, 1e-4)
    assert pll.step(valid, 1e-4) == reference.step(valid, 1e-4)


@pytest.mark.parametrize("invalid", [math.nan, math.inf, True, "1"])
def test_pll_rejects_invalid_reset_angle_without_state_change(invalid) -> None:
    pll, reference = SRFPLL(80, 1000), SRFPLL(80, 1000)
    valid = (325.0, -162.5, -162.5)
    pll.step(valid, 1e-4)
    reference.step(valid, 1e-4)
    with pytest.raises(ValueError, match="angle.*请"):
        pll.reset(invalid)
    assert pll.step(valid, 1e-4) == reference.step(valid, 1e-4)


@pytest.mark.parametrize("call", [
    lambda v: triangular_carrier(v, 1000), lambda v: triangular_carrier(0, v),
    lambda v: sine_pwm_duty(v, 0), lambda v: sine_pwm_duty(0.8, v),
    lambda v: carrier_compare(v, 0), lambda v: carrier_compare(0, v),
])
@pytest.mark.parametrize("invalid", [math.nan, math.inf, True, "0"])
def test_pwm_helpers_reject_invalid_values_before_gate_comparison(call, invalid) -> None:
    with pytest.raises(ValueError, match="请"):
        call(invalid)


@pytest.mark.parametrize("parameter", ["proportional_gain", "integral_gain"])
def test_pll_rejects_gain_sign_opposed_to_its_phase_detector(parameter) -> None:
    gains = {"proportional_gain": 80.0, "integral_gain": 1000.0, parameter: -1.0}
    with pytest.raises(ValueError, match=parameter + ".*非负"):
        SRFPLL(**gains)


@pytest.mark.parametrize("kp,ki", [(0.0, 0.0), (80.0, 0.0), (0.0, 1000.0)])
def test_pll_zero_gains_preserve_exact_nominal_lock(kp, ki) -> None:
    nominal, step = 2 * math.pi * 50, 1e-4
    pll = SRFPLL(kp, ki, nominal_frequency=nominal)
    for index in range(1, 21):
        angle = nominal * index * step
        voltages = tuple(325 * math.cos(angle + phase) for phase in (0.0, -2*math.pi/3, 2*math.pi/3))
        state = pll.step(voltages, step)
        assert state.frequency == pytest.approx(nominal, abs=1e-10)
        assert state.q_axis_voltage == pytest.approx(0.0, abs=1e-10)


def test_pll_absolute_frequency_limits_preserve_50hz_lock() -> None:
    omega, step, angle = 2 * math.pi * 50, 1e-4, 0.4
    pll = SRFPLL(80, 1000, nominal_frequency=omega, initial_angle=angle,
                 minimum_frequency=2 * math.pi * 45, maximum_frequency=2 * math.pi * 55)
    voltages = tuple(325 * math.cos(angle + omega * step + phase) for phase in (0, -2*math.pi/3, 2*math.pi/3))
    state = pll.step(voltages, step)
    assert state.frequency / (2 * math.pi) == pytest.approx(50.0, abs=1e-10)


@pytest.mark.parametrize("bounds,errors", [((45, 55), [0.8, -0.8]), ((45, None), [-0.8]), ((None, 55), [0.8])])
def test_pll_absolute_limits_saturate_and_release_without_windup(bounds, errors) -> None:
    lower, upper = (None if value is None else 2 * math.pi * value for value in bounds)
    pll = SRFPLL(1000, 10000, minimum_frequency=lower, maximum_frequency=upper)
    step = 1e-4
    for error in [*errors, 0.0]:
        for _ in range(20):
            predicted = pll.angle + pll.frequency * step
            voltages = tuple(325 * math.cos(predicted + error + phase) for phase in (0, -2*math.pi/3, 2*math.pi/3))
            state = pll.step(voltages, step)
            expected = upper if error > 0 else lower if error < 0 else pll.nominal_frequency
            assert state.frequency == pytest.approx(expected, abs=1e-9)
            if lower is not None:
                assert state.frequency >= lower
            if upper is not None:
                assert state.frequency <= upper
    pll.reset()
    assert pll.frequency == pll.nominal_frequency


@pytest.mark.parametrize("parameters", [
    {"minimum_frequency": 2 * math.pi * 60}, {"maximum_frequency": 2 * math.pi * 40},
    {"minimum_frequency": 400, "maximum_frequency": 300},
    {"minimum_frequency": -2 * math.pi * 5, "maximum_frequency": 2 * math.pi * 5},
    {"minimum_frequency": math.nan}, {"maximum_frequency": math.inf}, {"maximum_frequency": True},
    {"nominal_frequency": 0}, {"nominal_frequency": -1},
])
def test_pll_rejects_invalid_absolute_frequency_range(parameters) -> None:
    with pytest.raises(ValueError, match="frequency.*请"):
        SRFPLL(80, 1000, **parameters)


def test_pll_frequency_overflow_does_not_commit_partial_controller_state() -> None:
    pll, reference = SRFPLL(1e308, 0, nominal_frequency=1e308), SRFPLL(1e308, 0, nominal_frequency=1e308)
    step = 1e-308
    angle = pll.frequency * step
    invalid = tuple(math.cos(angle + 1.2 + phase) for phase in (0, -2*math.pi/3, 2*math.pi/3))
    with pytest.raises(ValueError, match="frequency.*请"):
        pll.step(invalid, step)
    valid = tuple(math.cos(angle + phase) for phase in (0, -2*math.pi/3, 2*math.pi/3))
    assert pll.step(valid, step) == reference.step(valid, step)
