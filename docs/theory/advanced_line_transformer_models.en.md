# Advanced Line and Transformer Models

[简体中文](advanced_line_transformer_models.md)

These teaching and algorithm-validation models prioritize clear boundaries, readable stamps, and testable results.

`PiLine` and `ThreePhasePiLine` use a series R-L branch and two shunt C/2 branches per phase. They suit concentrated-parameter line transients; frequency dependence, mutual coupling, and distributed waves are excluded.

`BergeronLine` and `ThreePhaseBergeronLine` use surge impedance `Zc` and travel time `tau`. Their port currents combine the local voltage divided by `Zc` with a delayed history source from the opposite terminal. History uses integer-step lookup with optional teaching attenuation; fractional-step delays, interpolation, modal transformation and phase coupling are not modeled.

`SinglePhaseTransformer` contains a referred leakage impedance, ideal turns ratio `Vp/Vs`, and a parallel magnetizing branch. `ThreePhaseTransformer` composes three single-phase paths. Saturation magnetization remains an educational approximation.

Verify ratios, power balance, initial conditions, and transient trends before interpreting results.

## Parameter and event limits

Resistance is in ohms, inductance in henries, capacitance in farads, surge impedance in ohms, and travel time in seconds. Bergeron requires travel time to be a positive integer multiple of the step, with stop and actual event times aligned to the fixed grid under the simulator's pairwise 8 ULP rounding rule. Invalid configurations fail before the first solve; `quantize_up` can postpone off-grid scheduled events. Tests cover no pre-response, matched-load arrival and open/short reflection.

Transformer results should distinguish turns-ratio convention, leakage impedance, magnetizing current, and winding polarity. These teaching models do not include every connection group, frequency-dependent loss, mutual coupling, or a validated saturation curve.

## Pi-line parameters

For a single-phase Pi line, the topology is: sending terminal — series R-L — receiving terminal, with a shunt `C/2` from each terminal to ground. `resistance` is in ohms, `inductance` in henries, and `capacitance` is the total line-to-ground capacitance in farads. Zero inductance or capacitance reduces the corresponding part of the model.

Example 08 compares RMS phasors over two complete cycles at 0.02–0.06 s:

```text
Yrecv = 1/Rload + jωC/2
Vrecv = Vsend / (1 + (R + jωL)Yrecv)
Iseries = Yrecv Vrecv
```

Tests cover both capacitor currents, KCL, storage/port-work balance over the entire startup, and errors on common physical times: halving the step reduces trapezoidal error by approximately four and backward-Euler error by two. The trapezoidal discrete energy check computes port work from the averages of endpoint voltages/currents. Stored energy is `L Iseries²/2 + C(Vsend²+Vrecv²)/4`. Example RMS and resistor power use the existing piecewise-linear metrics.

## Bergeron history

The characteristic impedance `surge_impedance` and propagation delay `travel_time` define the teaching wave model. At each terminal, the current consists of the local voltage divided by characteristic impedance plus a history source. The history source uses the opposite terminal's delayed voltage and current. Integer-step lookup reads solved samples, with zero port history for negative times and explicit errors for missing history. Same-time events retain only the right-side terminal frame. `attenuation` is an educational propagation factor, not frequency-dependent line loss.

## Single-phase transformer details

`turns_ratio` is the primary-to-secondary voltage ratio `Vp/Vs`. The model includes primary-referred leakage impedance, an ideal ratio relation, and a parallel magnetizing branch. The sign of secondary voltage and current must be checked against the stated winding polarity. A three-phase transformer composes phase paths but does not automatically provide all vector groups or mutual-coupling effects.

The turns ratio is the ideal winding ratio; loaded terminal voltage ratio also depends on leakage impedance. `i:T1:primary` excludes parallel magnetizing and core-loss currents. Total current supplied to the transformer in example 09 is `-i:V1`. For sinusoidal primary voltage and a resistive secondary load, RMS phasors satisfy:

```text
Ileak = Vpri / (Rleak + jωLleak + n²Rload)
Vsec = n Rload Ileak
Isecondary = -n Ileak
Iinput = Ileak + Imag + Vpri/Rcore   # omit the last term when core loss is absent
```

With zero initial current and `sqrt(2) Vrms sin(ωt)` primary voltage, ideal magnetizing current is `im(t) = sqrt(2) Vrms (1-cos(ωt))/(ωLm)`. Its DC component does not decay and must be included in total input RMS. Example 09 compares loaded voltage/total current to analytical values over 0.02–0.06 s and checks input power minus load power and copper loss. Tests also cover optional core loss, full-startup energy balance and step convergence for both methods. These checks establish the linear model only, not saturation or hysteresis.

## Synchronous machines: two retained models with explicit limits

Import both models from `pycy_emt_lite.machines` and use the existing `Circuit/Simulator` workflow.
[Example 10](../../examples/10_park_generator_avr_governor.py) uses `CaseDefinition`.

| Model | Retained equations | Intended use |
|---|---|---|
| `SynchronousMachine` | Fixed-amplitude three-phase internal voltage, per-phase stator R–L, rotor angle and speed | Circuit transients and electromechanical power; no exciter, governor or full flux-linkage machine |
| `ParkSynchronousGenerator` | Fourth-order transient-voltage machine plus first-order AVR and governor, six states in total | Balanced, near-fundamental load and regulation responses; fast stator transients are replaced by algebraic ports |

The Park model does not cover short-circuit DC offset, subtransients, unbalanced faults, saturation or hysteresis.
Its zero-sequence port contains only stator resistance; this is not a full dq0 machine.
Restoring these models does not imply that those effects have been implemented.

### Units, directions and ports

Positive current flows from internal voltage to the terminal. `p` is total three-phase active power delivered to the network (W).
`base_power` is total three-phase capacity (VA); `base_phase_rms` is phase-to-neutral RMS voltage (V):

```text
Zbase = 3 Vbase_rms² / Sbase
Vbase_peak = sqrt(2) Vbase_rms
Ibase_peak = sqrt(2) Sbase / (3 Vbase_rms)
theta = 2 pi frequency t + rotor_angle
```

The classical model's `stator_resistance/stator_inductance` are in ohms/henries; do not enter per-unit reactance directly.
`inertia_constant` is in seconds, `frequency` in Hz, `rotor_angle` in electrical radians and `speed_pu` in per-unit speed.
`damping` is the per-unit damping-power coefficient for speed deviation from synchronism.
Classical `mechanical_power` is in watts and accepts a constant or time function; Park `mechanical_power_*_pu` uses the three-phase capacity base.

Park uses d=`-cos(theta)`, q=`sin(theta)`: negate both outputs of the general `abc_to_dq` transform and divide by their peak bases.
The inverse is `dq_to_abc(-ed, -eq, theta)`, replacing the old convention that negated only the q-axis current.
Phase angles are `theta`, `theta-2pi/3`, `theta+2pi/3`. The per-unit terminal equations are:

```text
Vd = Ed' - Rs Id + Xq' Iq
Vq = Eq' - Rs Iq - Xd' Id
```

Both transient reactances enter the port. With rows of M equal to `[-cos(theta_phase), sin(theta_phase)]`,
the SI branch equation is `Eabc - Vabc = Zabc Iabc`, where:

```text
Zabc = Rs_ohm I3 + Zbase M [[0, -Xq'], [Xd', 0]] (2/3 M^T)
```

This linear, angle-dependent coupled stamp uses the existing solver. Park stator currents are algebraic.
The old derived `stator_inductance` property and inductor histories are removed; `X'd` is no longer treated as three independent dynamic inductors.

### Power, states and initialization

The classical model uses `P_em = sum(e_phase*i_phase)`; its difference from terminal power includes copper loss and stator R–L energy exchange.
Park neglects fast stator storage and uses `P_em = P_terminal + P_copper`. Under balanced conditions:

```text
P_terminal / Sbase = Vd Id + Vq Iq
P_copper / Sbase = Rs (Id² + Iq²)
P_em / Sbase = Ed' Id + Eq' Iq + (Xq' - Xd') Id Iq
```

The last term is the saliency/reluctance contribution. With unequal transient reactances, transient internal voltage times current alone is not air-gap power.
Both models output `p` (terminal), `p_copper` (copper loss), and `p_em` (electromagnetic/air-gap power), all in watts.
Their power-form swing equations retain the speed denominator:

```text
dspeed_pu/dt = (Pm/Sbase - P_em/Sbase - D(speed_pu-1)) / (2 H speed_pu)
drotor_angle/dt = 2 pi frequency (speed_pu-1)
```

The other Park state equations are:

```text
dEq'/dt = (Efd - Eq' - (Xd-Xd') Id) / Tdo'
dEd'/dt = (-Ed' + (Xq-Xq') Iq) / Tqo'
dEfd/dt = (Efd_initial + Kavr (Vref-Vt) - Efd) / Tavr
dPm_pu/dt = (Pm_reference - (speed_pu-1)/droop - Pm_pu) / Tgov
```

`Vt=hypot(Vd,Vq)`. The exciter bias is `initial_efd_pu`, so `avr_gain=0` holds the declared field voltage.
Time constants are in seconds; voltages, reactances, control limits and references use their respective per-unit bases.
Updated field voltage and mechanical power are clipped to `efd_min/max_pu` and `mechanical_power_min/max_pu`.

At t=0, hold declared dynamic states and solve the network. Classical stator currents start at zero; Park currents follow the algebraic port and are generally nonzero.
Electromechanical/control states advance once by forward Euler using the same left-end feedback, before solving and recording the current network.
Rotor angle, transient voltage and abc outputs in one row therefore share one time.
Electromechanical coupling is first order; `SimulationConfig.method` selects integration only for classical stator R–L and external storage components.
Explicit events hold dynamic states while solving the right-side network. Park currents may jump algebraically; classical inductor currents remain continuous.

There is no automatic load-flow initialization. Example 10 derives a balanced resistive operating point using
`I=1/Rload_pu`, `A=Rload_pu+Rs`, `Iq=I A/hypot(A,Xq)`, `Id=I Xq/hypot(A,Xq)`, then obtains `Ed'/Eq'/Efd/Pm` from the port and state equations.
Initially the terminal is at 100 V RMS and 1000 W, copper loss is 13.333333 W, and mechanical input is 1013.333333 W.
At 0.2 s, 18 ohms per phase is added in parallel through a 1 milliohm breaker. The default stop is 0.6 s, an observation endpoint with no claim of a new steady state.

Run `uv run python examples/10_park_generator_avr_governor.py`. Edit the top-level capacity, voltage, impedances, loads, times and saving flags;
exciter, governor and inertia parameters remain in `define_case()`.
The example displays separate voltage/field, speed and power figures, with saving disabled by default and fixed filenames when enabled.
Nonfinite values, negative impedances, nonpositive time constants/inertia, reversed limits and out-of-range initial states report the parameter and repair.
Reduce the step and check convergence. If an extra ideal constraint on a Park internal voltage node requires its derivative, the model rejects it:
remove that internal constraint and connect the external circuit through a terminal with finite impedance.

### Validation and remaining limits

- Classical model: resistive divider, analytical deceleration due to copper loss, independent integration of rotor and three-phase R–L currents, discrete storage balance and first-order rotor-angle convergence.
- Park: analytical initial currents with unequal transient reactances, abc/dq signs, air-gap power including saliency, and same-time state/internal-voltage consistency.
- Example 10: pre-step equilibrium, post-step KCL/port equations and an independent piecewise continuous ODE reference; 200/100/50 microsecond steps give first-order convergence on common times. Initial, off-grid and endpoint events do not advance states twice.
- These checks validate the stated approximate equations, not agreement with a vendor's complete machine or experimental data. Complex faults and engineering controller settings remain outside that evidence.

See [PowerWorld's transient-stability modeling overview](https://www.powerworld.com/files/T01ModelRelationships.pdf) for model levels and explicit update ordering,
and [PSCAD Basic Machine Theory](https://www.pscad.com/webhelp/EMTDC/Rotating_Machines/basic_machine_theory.htm) for full machine dq transforms and winding structure.
This section states this project's actual approximations and signs; the reference software's features are not implied to be implemented here.
