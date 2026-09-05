# Three-Phase System Models

[简体中文](three_phase_systems.md)

Use `bus:phase` names such as `source:a` and `load:c`; result voltages are prefixed with `v:`. Reference nodes remain `"0"`, `"gnd"`, or `"ground"`.

`ThreePhaseSource` is a balanced positive-sequence sinusoidal source. `phase_rms` is the phase-to-neutral RMS value; default angles are A = 0°, B = -120°, C = +120°, with a 50 Hz default frequency.

`ThreePhaseLine` uses an independent series R-L branch per phase. `ThreePhaseLoad` is a wye load from each `bus:phase` to `neutral`, also using series R-L branches. Delta connections, mutual coupling, frequency-dependent parameters, and complex unbalanced loads are outside the first version.

Events can apply and clear a fault before fixed time steps, for example `FaultApplyEvent(0.04, "FA")` followed by `FaultClearEvent(0.08, "FA")`. The event log is saved with JSON and NPZ results. `pycy_emt_lite.analysis` provides `rms`, `peak_abs`, `mean_value`, and `three_phase_rms`.

For a balanced positive-sequence source, state the phase sequence and RMS convention with the result. The first version is intended for balanced teaching cases and simple faults; it does not claim a complete unbalanced-network or frequency-dependent line model. Use phase-specific columns in tests and plots.

## Signal and parameter details

The source connects one ideal voltage source from each `terminal_bus:phase` node to the neutral node. The default phase angles are A = 0°, B = -120°, and C = +120°. `phase_rms` is a phase RMS quantity; do not silently reinterpret it as line-to-line RMS.

For `ThreePhaseLine`, `resistance` and `inductance` are per-phase series parameters. With `inductance = 0`, no dynamic branch state is needed. With positive inductance, each phase registers a branch current. The load uses the same series R-L convention from each phase node to `neutral`.

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

The event log records event time, type, target, and state change. Use `three_phase_rms(result, ("v:load:a", "v:load:b", "v:load:c"), start_time=0.06)` for a window beginning after the fault is applied. Event boundaries should not be hidden inside one whole-window statistic.
