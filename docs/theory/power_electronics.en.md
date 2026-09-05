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

## Average-model boundary

For the average inverter, `m_phase` is clipped to `[-1, 1]` before calculating average phase voltage. The model is appropriate for dq current loops, PLL demonstrations, and grid-control studies. It cannot show carrier ripple, switching loss, dead time, diode recovery, or device thermal behavior.
