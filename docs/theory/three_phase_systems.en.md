# Three-Phase System Models

[简体中文](three_phase_systems.md)

Use `bus:phase` names such as `source:a` and `load:c`; result voltages are prefixed with `v:`. Reference nodes remain `"0"`, `"gnd"`, or `"ground"`.

`ThreePhaseSource` is a balanced positive-sequence sinusoidal source. `phase_rms` is the phase-to-neutral RMS value; default angles are A = 0°, B = -120°, C = +120°, with a 50 Hz default frequency.

`ThreePhaseLine` uses an independent series R-L branch per phase. `ThreePhaseLoad` is a wye load from each `bus:phase` to `neutral`, also using series R-L branches. Delta connections, mutual coupling, frequency-dependent parameters, and complex unbalanced loads are outside the first version.

Explicit events first advance the old network to the left limit, then change component states and solve/record right-side algebraic values with storage held. For example, use `FaultApplyEvent(0.04, "FA")` followed by `FaultClearEvent(0.08, "FA")`. The event log is saved with JSON and NPZ results. `pycy_emt_lite.analysis` provides `rms`, `peak_abs`, `mean_value`, and `three_phase_rms`.

For a balanced positive-sequence source, state the phase sequence and RMS convention with the result. The first version is intended for balanced teaching cases and simple faults; it does not claim a complete unbalanced-network or frequency-dependent line model. Use phase-specific columns in tests and plots.

## Signal and parameter details

The source connects one ideal voltage source from each `terminal_bus:phase` node to the neutral node. The default phase angles are A = 0°, B = -120°, and C = +120°. `phase_rms` is a phase RMS quantity; do not silently reinterpret it as line-to-line RMS.

For `ThreePhaseLine`, `resistance` and `inductance` are per-phase series parameters. With `inductance = 0`, no dynamic branch state is needed. With positive inductance, each phase registers a branch current. The load uses the same series R-L convention from each phase node to `neutral`.

Example 05 uses a 20 Ω + 50 mH load and 0.5 Ω line resistance per phase. At 50 Hz,
the load reactance is about 15.7 Ω. Steady current is
`I = Vsource / (Rline + Rload + jωLload)` and load voltage is
`Vload = I(Rload + jωLload)`. RMS and three-phase P/Q use two cycles at 0.06–0.10 s;
current lags its phase source voltage by about 37.46°. All three inductor currents
start at zero, including phases B/C whose source voltages are nonzero at t=0.

## Event example and analysis window

```python
from pycy_emt_lite import Simulator
from pycy_emt_lite.events import FaultApplyEvent, FaultClearEvent

events = [
    FaultApplyEvent(0.04, "FA"),
    FaultClearEvent(0.08, "FA"),
]
result = Simulator(circuit, config, events=events).run()
```

The event log records event time, type, target, and state change. Use `three_phase_rms(result, ("v:load:a", "v:load:b", "v:load:c"), start_time=0.05, end_time=0.07)` for a full 50 Hz period during the fault in example 07. Examples 06/07 compare 0.01–0.03, 0.05–0.07 and 0.09–0.11 s windows. Example 06 retains decaying components in its fault window, so phase RMS values can differ and are not pure steady-state phasors. Mean power in each resistive load is `Vbus_rms²/Rload`.

Example 06 uses 0.8 Ω + 5 mH per line phase, a 50 Ω load and a 0.1 Ω fault resistor.
The fault applies at 0.04 s and clears at 0.08 s. Each stage obeys
`L di/dt + (Rline + Req)i = vsource`, with `Req = Rload` normally and
`Req = Rload || Rfault` during the fault. Inductor current is continuous;
bus voltage `vbus = Req i` and fault-branch current can jump at events.

At clearing, line current transfers to the resistive load. Default parameters
produce a bus-voltage absolute peak of about 7.79 kV, decaying with the approximately
98 μs time constant `L/(Rline+Rload)`. The step is therefore 10 μs. This ideal
teaching circuit contains no parasitic capacitance, surge arrester or arc model.
Separate line-current, fault-current and bus-voltage plots distinguish continuous
inductor current from discontinuous fault current. Tests use sinusoidal particular
solutions plus exponential transients to check zero states, application/clearing
currents, complete waveforms and fixed-window metrics.

Mean and RMS integrate piecewise-linear signals over actual time, interpolating window endpoints when needed. Time must be finite and strictly increasing; integration windows need positive duration inside the data range. Do not integrate across events or interpolate within a raw sample interval containing a jump. `peak_abs` still returns the sampled peak and accepts a single-point window.

Instantaneous total active power is `va*ia + vb*ib + vc*ic`, including zero sequence. Average active power integrates products of the linearly reconstructed voltage and current. Reactive power uses the alpha-beta definition; S/PF derived from mean P/Q apply to balanced sinusoidal conditions, not general distorted or unbalanced power quality.
