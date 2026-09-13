# Power-Electronic Models

[简体中文](power_electronics.md)

The retained power-electronics scope consists of the explicit ideal switch, basic filter assemblies and the PWM example, for observing switched networks and load currents.

## Component behavior

`IdealSwitch` in `pycy_emt_lite.components.power_electronics` is controlled by a Boolean state or time function. In the on state it stamps a small resistance; in the off state it stamps a small leakage conductance. This explicit conductance approximation is not a complete device model. PWM checks cover gate timing, on/off conductance, current direction and the fundamental component; nonlinear semiconductor equations and switching losses are outside scope.

## Filter composition

`pycy_emt_lite.converters` exports three optional single-phase assemblies for studying filter connections and damping. Calling `.components()` returns ordinary R/L/C objects for the existing `Circuit/Simulator` workflow; an assembly has no dynamic states or separate solver.

| Assembly | Connections and current directions |
|---|---|
| `LFilter` | `input_node → series_resistance → inductance → output_node`; current is positive from input to output |
| `LCFilter` | The same series R–L branch, with C from the output node to `ground`; capacitor current is positive toward ground |
| `LCLFilter` | `converter_node → R1/L1 → capacitor_node → R2/L2 → grid_node`; a series Rd–C branch connects the middle node to ground, with i1 entering the middle node and i2 flowing toward the grid |

Inductance is in H, capacitance in F and resistance in Ω. L/C must be positive. All resistance parameters may be zero, which omits the corresponding resistor. `damping_resistance` is **in series** with C. Rd=0 connects C directly to the middle node; it does not omit the capacitor. All electrical parameters must be finite real numbers. Construction rejects negative values, NaN/Inf, Booleans and nonnumeric inputs, identifying the name, parameter and required range. For example, `series_resistance=-1` used to silently omit the resistor and now raises an error; explicitly use zero for a lossless branch.

This runnable LC circuit uses a 10 V peak, 50 Hz source and a 10 Ω load:

```python
import math
from pycy_emt_lite import Circuit, Resistor, SimulationConfig, Simulator, VoltageSource
from pycy_emt_lite.converters import LCFilter

filter_ = LCFilter("F", "src", "load", "0", inductance=0.01,
                   capacitance=1e-4, series_resistance=0.5)
components = [
    VoltageSource("V", "src", "0", lambda t: 10 * math.cos(2 * math.pi * 50 * t)),
    *filter_.components(),
    Resistor("LOAD", "load", "0", 10.0),
]
result = Simulator(Circuit.from_components("lc_filter", components),
                   SimulationConfig(time_step=1e-5, stop_time=0.02)).run()
print(result.rows[-1]["v:load"])
```

Generated iL/vC initial values are zero. For nonzero states, use `dataclasses.replace` on the generated inductor's `initial_current` or capacitor's `initial_voltage` before building the circuit. Call `.components()` again to obtain fresh components for each simulation. Results retain the basic component names: for example, LC uses `i:F:L` and `i:F:C`; LCL uses `i:F:converter:L`, `i:F:grid:L` and `i:F:C`. With Rd>0, the middle-node voltage relative to `ground` is `vC + Rd·(i1-i2)` and the capacitor's upper terminal is internal node `F:damping`; with Rd=0 the two voltages coincide.

The independent reference integrates these circuit equations without calling assembly stamps or state updates:

- LC with resistive load Rload: `L·di/dt = vin-Rs·i-vC`, `C·dvC/dt = i-vC/Rload`.
- LCL between independent voltage sources: `ic=i1-i2`, `vm=vC+Rd·ic`, `L1·di1/dt=vconv-R1·i1-vm`, `L2·di2/dt=vm-R2·i2-vgrid`, `C·dvC/dt=ic`.
- LCL stored energy is `E=(L1·i1²+L2·i2²+C·vC²)/2`, with `dE/dt=vconv·i1-vgrid·i2-R1·i1²-R2·i2²-Rd·ic²`.

Regressions cover zero initial states, source-current directions, KCL, the Rd drop and whole-transient discrete energy balance, both with zero resistances and with damping. LC/LCL reuse and test the L series assembly. The reference uses SciPy DOP853 at common times over 0–0.02 s. LC uses the parameters above and an Rs=0 comparison, with 20/10 μs steps. LCL uses L1=10 mH, L2=5 mH and C=100 μF, terminal voltages `10 cos(2π50t)` V and `6 cos(2π50t-0.2)` V, resistances either all zero or `(R1,R2,Rd)=(0.4,0.3,2)` Ω, and 5/2.5 μs steps. Halving the step gives maximum-state-error ratios of about 4 for trapezoidal and 1.93–1.99 for backward Euler.

Trapezoidal energy checks use endpoint-averaged voltages/currents to balance storage, port work and physical resistor losses. Backward Euler additionally dissipates `(ΣL·Δi²+ΣC·Δv²)/2` per step. At 2.5 μs, undamped LCL still has about 0.541 V maximum vC error with backward Euler, compared with 0.000387 V for trapezoidal; backward Euler decay must not be interpreted as physical damping. These checks cover linear passive filters, not closed-loop grid-connected converters.

## PWM example validation

`examples/12_two_level_pwm_generator.py` drives an RL load with a two-level PWM inverter using `IdealSwitch` and triangular-carrier comparison for gate signals.

Example 12 reports phase-current total RMS, fundamental RMS and phase difference over 0.1–0.2 s (six 60 Hz cycles and 100 carrier cycles). Phase is relative to each phase's unheld sinusoidal reference. The fundamental average-model reference includes the zero-order hold `sinc(f Ts) exp(-jωTs/2)` and switch on-resistance. It applies only to linear modulation and excludes switching ripple; total RMS differs from fundamental RMS.

Tests verify complementary gates, floating-star phase voltages, zero current sum and the fundamental RL impedance. Steps of 5/2.5/1.25 μs are compared over the common 0.05–0.10 s window. Relative to 1.25 μs, maximum fundamental-phasor differences are approximately 0.214% at the default 5 μs and 0.094% at 2.5 μs; waveform RMS differences are below 0.6 A and 0.3 A, respectively. The fine grid is a step-sensitivity comparison, not a device-physics reference. `event_time_policy` constrains explicit events only and does not locate callable gate edges automatically; no second-order PWM waveform convergence, dead-time or device-level behavior is claimed.
