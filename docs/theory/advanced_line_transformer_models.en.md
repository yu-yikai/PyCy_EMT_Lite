# Advanced Line and Transformer Models

[简体中文](advanced_line_transformer_models.md)

These teaching and algorithm-validation models prioritize clear boundaries, readable stamps, and testable results.

`PiLine` and `ThreePhasePiLine` use a series R-L branch and two shunt C/2 branches per phase. They suit concentrated-parameter line transients; frequency dependence, mutual coupling, and distributed waves are excluded.

`BergeronLine` and `ThreePhaseBergeronLine` use surge impedance `Zc` and travel time `tau`. Their port currents combine the local voltage divided by `Zc` with a delayed history source from the opposite terminal. History uses integer-step lookup with optional teaching attenuation; fractional-step delays, interpolation, modal transformation and phase coupling are not modeled.

`SinglePhaseTransformer` contains a referred leakage impedance, ideal turns ratio `Vp/Vs`, and a parallel magnetizing branch. `ThreePhaseTransformer` composes three single-phase paths. Saturation magnetization and `SynchronousMachine` are educational approximations. `ParkSynchronousGenerator` is a candidate dq0 model and is not validated high-fidelity machinery without parameter and port-equation evidence.

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

## Machine limits

The classical synchronous-machine model is a teaching second-order model. The Park dq0 generator candidate must be checked for parameter use, dq port meaning, initial state, and power direction before being described as a detailed generator model. Example output and a successful simulation are not substitutes for those checks.
