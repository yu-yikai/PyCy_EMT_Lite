# Power-Electronic Models

[简体中文](power_electronics.md)

The retained power-electronics scope consists of the explicit ideal switch, basic filter assemblies and the PWM example, for observing switched networks and load currents.

## Component behavior

`IdealSwitch` in `pycy_emt_lite.components.power_electronics` is controlled by a Boolean state or time function. In the on state it stamps a small resistance; in the off state it stamps a small leakage conductance. This explicit conductance approximation is not a complete device model. PWM checks cover gate timing, on/off conductance, current direction and the fundamental component; nonlinear semiconductor equations and switching losses are outside scope.

## Filter composition

`LFilter`, `LCFilter`, and `LCLFilter` in `pycy_emt_lite.converters.filters` are convenience assemblies. They reuse the existing resistor, inductor, and capacitor stamps and state-update logic rather than introducing a second matrix element family. This keeps the topology readable and makes the dynamic states individually testable.

## PWM example validation

`examples/12_two_level_pwm_generator.py` drives an RL load with a two-level PWM inverter using `IdealSwitch` and triangular-carrier comparison for gate signals.

Example 12 reports phase-current total RMS, fundamental RMS and phase difference over 0.1–0.2 s (six 60 Hz cycles and 100 carrier cycles). Phase is relative to each phase's unheld sinusoidal reference. The fundamental average-model reference includes the zero-order hold `sinc(f Ts) exp(-jωTs/2)` and switch on-resistance. It applies only to linear modulation and excludes switching ripple; total RMS differs from fundamental RMS.

Tests verify complementary gates, floating-star phase voltages, zero current sum and the fundamental RL impedance. Steps of 5/2.5/1.25 μs are compared over the common 0.05–0.10 s window. Relative to 1.25 μs, maximum fundamental-phasor differences are approximately 0.214% at the default 5 μs and 0.094% at 2.5 μs; waveform RMS differences are below 0.6 A and 0.3 A, respectively. The fine grid is a step-sensitivity comparison, not a device-physics reference. `event_time_policy` constrains explicit events only and does not locate callable gate edges automatically; no second-order PWM waveform convergence, dead-time or device-level behavior is claimed.
