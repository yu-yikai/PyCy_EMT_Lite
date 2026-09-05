# Advanced Line and Transformer Models

[简体中文](advanced_line_transformer_models.md)

These teaching and algorithm-validation models prioritize clear boundaries, readable stamps, and testable results.

`PiLine` and `ThreePhasePiLine` use a series R-L branch and two shunt C/2 branches per phase. They suit concentrated-parameter line transients; frequency dependence, mutual coupling, and distributed waves are excluded.

`BergeronLine` and `ThreePhaseBergeronLine` use surge impedance `Zc` and travel time `tau`. Their port currents combine the local voltage divided by `Zc` with a delayed history source from the opposite terminal. History samples use linear interpolation and optional teaching attenuation; modal transformation and phase coupling are not modeled.

`SinglePhaseTransformer` contains a referred leakage impedance, ideal turns ratio `Vp/Vs`, and a parallel magnetizing branch. `ThreePhaseTransformer` composes three single-phase paths. Saturation magnetization and `SynchronousMachine` are educational approximations. `ParkSynchronousGenerator` is a candidate dq0 model and is not validated high-fidelity machinery without parameter and port-equation evidence.

Verify ratios, power balance, initial conditions, and transient trends before interpreting results.

## Parameter and event limits

Resistance is in ohms, inductance in henries, capacitance in farads, surge impedance in ohms, and travel time in seconds. For a Bergeron case, travel time, stop time, and event times must be compatible with the time grid when a fixed-step interpretation is required. Check pre-response, wave arrival, reflection, and post-event windows separately.

Transformer results should distinguish turns-ratio convention, leakage impedance, magnetizing current, and winding polarity. These teaching models do not include every connection group, frequency-dependent loss, mutual coupling, or a validated saturation curve.

## Pi-line parameters

For a single-phase Pi line, the topology is: sending terminal — series R-L — receiving terminal, with a shunt `C/2` from each terminal to ground. `resistance` is in ohms, `inductance` in henries, and `capacitance` is the total line-to-ground capacitance in farads. Zero inductance or capacitance reduces the corresponding part of the model.

## Bergeron history

The characteristic impedance `surge_impedance` and propagation delay `travel_time` define the teaching wave model. At each terminal, the current consists of the local voltage divided by characteristic impedance plus a history source. The history source uses the opposite terminal's delayed voltage and current. Linear interpolation is used when a delayed sample falls between stored samples; `attenuation` is an educational propagation factor, not frequency-dependent line loss.

## Single-phase transformer details

`turns_ratio` is the primary-to-secondary voltage ratio `Vp/Vs`. The model includes primary-referred leakage impedance, an ideal ratio relation, and a parallel magnetizing branch. The sign of secondary voltage and current must be checked against the stated winding polarity. A three-phase transformer composes phase paths but does not automatically provide all vector groups or mutual-coupling effects.

## Machine limits

The classical synchronous-machine model is a teaching second-order model. The Park dq0 generator candidate must be checked for parameter use, dq port meaning, initial state, and power direction before being described as a detailed generator model. Example output and a successful simulation are not substitutes for those checks.
