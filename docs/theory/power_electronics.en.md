# Power-Electronic Models

[简体中文](power_electronics.md)

The first power-electronics models prioritize verifiability, explainability, and teaching. They are explicit approximations, not device-level models.

`IdealSwitch` uses on/off conductances controlled by a Boolean or time function. `Diode` determines conduction from the previous-step voltage, avoiding nonlinear iteration. `IGBTSwitch` has a gate-controlled main path and an optional antiparallel-diode approximation.

`LFilter`, `LCFilter`, and `LCLFilter` in `pycy_emt_lite.converters.filters` compose existing resistor, inductor, and capacitor objects. They are combinations, not new MNA elements.

`ThreePhaseAverageInverter` maps modulation or dq commands to average phase voltage using `v_phase = 0.5 * Vdc * m_phase`, with `m_phase` limited to `[-1, 1]`. It does not produce switching ripple. See examples 12 and 13 for PWM and average grid-inverter teaching cases.

The switch models are explicit conductance approximations. They do not solve a nonlinear diode equation, model semiconductor losses, or reproduce a vendor device. A PWM lesson should verify gate timing, on/off conductance behavior, current direction, and a meaningful fundamental component rather than claim device-level accuracy.

## Component behavior

`IdealSwitch` is controlled by a Boolean state or time function. In the on state it stamps a small resistance; in the off state it stamps a small leakage conductance. `Diode` uses the previous-step terminal voltage to choose its explicit state, so a same-step nonlinear operating-point iteration is intentionally absent. `IGBTSwitch` uses the gate state for its main path and can add a simplified antiparallel diode.

## Filter composition

The L, LC, and LCL classes are convenience assemblies. They reuse the existing resistor, inductor, and capacitor stamps and state-update logic rather than introducing a second matrix element family. This keeps the topology readable and makes the dynamic states individually testable.

## PWM example validation

Example 12 reports phase-current total RMS, fundamental RMS and phase difference over 0.1–0.2 s (six 60 Hz cycles and 100 carrier cycles). Phase is relative to each phase's unheld sinusoidal reference. The fundamental average-model reference includes the zero-order hold `sinc(f Ts) exp(-jωTs/2)` and switch on-resistance. It applies only to linear modulation and excludes switching ripple; total RMS differs from fundamental RMS.

Tests verify complementary gates, floating-star phase voltages, zero current sum and the fundamental RL impedance. Steps of 5/2.5/1.25 μs are compared over the common 0.05–0.10 s window. Relative to 1.25 μs, maximum fundamental-phasor differences are approximately 0.214% at the default 5 μs and 0.094% at 2.5 μs; waveform RMS differences are below 0.6 A and 0.3 A, respectively. The fine grid is a step-sensitivity comparison, not a device-physics reference. `event_time_policy` constrains explicit events only and does not locate callable gate edges automatically; no second-order PWM waveform convergence, dead-time or device-level behavior is claimed.

## Average-model boundary

For the average inverter, `m_phase` is clipped to `[-1, 1]` before calculating average phase voltage. The model is appropriate for dq current loops, PLL demonstrations, and grid-control studies. It cannot show carrier ripple, switching loss, dead time, diode recovery, or device thermal behavior.
