# Numerical Conventions

[简体中文](numerical_conventions.md) · [Running the project](../README.md) · [Models and validation](models_and_validation.en.md)

This document collects the implemented equation, time, initialization, event and metric conventions. Model-specific equations and evidence belong in the model document.
For equation derivations, local matrices and state updates, read [Component derivations](component_derivations.en.md): Sections 1–5 cover basic stamps and a worked RLC example; Sections 13–15 explain consistent initialization, the event loop and discrete energy.

## 1. From components to results

`CaseDefinition` holds components, simulation settings, events and output options; `run_case()` creates a `Circuit` and `Simulator`.
Small circuits may use these two objects directly. Circuit preparation registers nodes and extra branch unknowns. Each component
writes its equations into the common `A x = b`; after solving, histories are updated and a `SimulationResult` row is recorded.
This local matrix contribution is called a stamp. There is no separate compilation entry point, simulation session or checkpoint workflow.

Create fresh components, a circuit and a simulator for every run. A `Simulator` runs once, and a circuit already owned by one
simulator cannot be transferred to another; rebuild after a failed run too. This prevents old inductor, capacitor and event states
from contaminating a new calculation. `SimulationResult` contains data, not a state snapshot from which integration can resume.

| Reading order | Responsibility |
|---|---|
| [cases.py](../pycy_emt_lite/cases.py) | Shared case definition, plotting and saving |
| [circuit.py](../pycy_emt_lite/core/circuit.py) | Components, nodes, unknowns and initial constraints |
| [stamping.py](../pycy_emt_lite/core/stamping.py) | Basic matrix contributions |
| [basic.py](../pycy_emt_lite/components/basic.py) | R/L/C and independent-source equations |
| [simulation.py](../pycy_emt_lite/core/simulation.py) | Configuration checks, time grid and update order |
| [solvers.py](../pycy_emt_lite/core/solvers.py) | Linear solves, nonfinite values and residual checks |
| [results.py](../pycy_emt_lite/io/results.py) | Result access and CSV/JSON/NPZ |

## 2. Units, directions and minimal MNA

Circuits use SI units: time s, voltage V, current A, resistance Ω, inductance H and capacitance F; frequency usually uses Hz and
angles use rad. Machine per-unit quantities and PLL rad/s units are specified separately in the model document.
`0`, `gnd` and `ground` are reference-node aliases. The unknown vector contains nonreference node voltages and branch currents
required by voltage sources, inductors and similar elements. Component names and all result fields must be unique. A collision is rejected while recording the row, identifying the component, time and repair.
For example, if nodes a/b are at 10/5 V, a capacitor named a across them conflicts with node field `v:a`.
Rename the capacitor C to retain `v:a=10 V` and `v:C=5 V` separately. Expanded composite fields must also be distinct from other component outputs.

For a two-terminal element `p → n`, `v=Vp−Vn` and current flows from p to n. A voltage source delivering power usually records
a negative branch current; `v*i` is therefore not automatically outward power. Three-phase nodes usually use `bus:a/b/c`;
outputs use `v:node` and `i:component`. Composite elements may expose branch or winding fields with model-specific meanings.

A conductance G contributes `A[p,p]+=G`, `A[n,n]+=G`, `A[p,n]-=G`, `A[n,p]-=G` to the node submatrix.
An independent current I from p to n contributes `b[p]-=I`, `b[n]+=I`. Reference-node rows and columns are omitted.
An ideal voltage source adds current unknown k, contributes `+ik/−ik` to node KCL and adds `Vp−Vn=Vsource` as another row.
MNA therefore handles voltage constraints directly without replacing an ideal voltage source with a very large conductance.

For an integration interval h>0, subscript 0 denotes its left endpoint:

| Element and equation | `trapezoidal` | `backward_euler` |
|---|---|---|
| R: `i=Gv` | `G=1/R` | Same |
| C: `i=Gv+Ihist` | `G=2C/h`; `Ihist=−i0−Gv0` | `G=C/h`; `Ihist=−Gv0` |
| L: `v−Req i=Vhist` | `Req=2L/h`; `Vhist=−Req i0−v0` | `Req=L/h`; `Vhist=−Req i0` |

A series R–L branch uses `v−(R+Req)i=Vhist`. A capacitor becomes a parallel conductance and history current; an inductor retains
its branch-current unknown. Save endpoint voltage and current only after the solve, without overwriting history during stamping.
Machine mechanical/control states have their own explicit update order; their integration order cannot be inferred from global `method`.

## 3. Time grid and parameters

`SimulationConfig(time_step, stop_time, start_time=0, method="trapezoidal", event_time_policy="insert", record_every=1)`:

- `time_step` must be a finite positive real number; `stop_time` must be finite and nonnegative. Booleans are not accepted as numbers.
- Only `start_time=0` is supported. `stop_time=0` is valid and records one consistent initial row.
- **Stop time must be an integer multiple of the base step.** A 100 μs step and 250 μs stop raise an error before calculation;
  use 200/300 μs, or choose a step that divides 250 μs. The program does not shorten the final step to fit the endpoint.
- Only small floating-point representation differences are absorbed: positive times use a pairwise 8 ULP tolerance and are
  canonicalized to grid values; zero matches only zero. This is not arbitrary approximate alignment.
- `method` accepts only the two methods above. Basic R/L/C values must be finite positive real numbers; composite-model rules determine whether zero impedance is allowed.

`insert` permits explicit events between base grid points, so actual interval lengths h can differ. Storage histories and metrics
must use actual times. Integer-step stop time and inserted events are separate conventions. Bergeron history additionally requires
a fixed grid and an integer-step propagation delay.

`record_every` must be a positive integer and defaults to saving every solution point. N saves every Nth point by index,
always retaining the initial point, explicit-event points and endpoint. Inserted events count toward the index, so output need not be uniform.
It only reduces stored rows; network solves, state updates and control callbacks still run at every solution point.
`result.time_step` remains the base EMT step; plots and metrics use the actual `time` column.

### Optional post-step control callback

Use `CaseDefinition(..., on_step=callback)` or `Simulator(..., on_step=callback)` to connect explicit control.
The callback receives the current read-only measurement row and returns a mapping of additional fields (`{}` when none are needed).
Keys must be nonempty strings without collisions; values must be finite real numbers, excluding booleans.
The order is solve/update, consistent event right-side solve, one callback, then selective recording. Same-time events do not advance controllers twice.
The callback also runs at t=0 for observation/initialization; do not pass a zero interval to PI/PLL blocks requiring positive intervals.
Held controller commands reach the next network step through component callables; there is no same-step algebraic control loop.
Use consecutive `row["time"]` values for the actual interval and create fresh controller state with each case.
See [three-terminal VSC-HVDC](three_terminal_vsc_hvdc.en.md). The default `on_step=None` preserves the original workflow.

## 4. Consistent initialization

With high-voltage storage beside near-zero voltage constraints, LU cancellation may cause a consistent solution to fail per-row checks.
In that case, solve the residual equation `A δx=b−Ax` once and recheck against the original initialization thresholds; constraints are not relaxed and impulses are not allowed.

At `t=0`, apply zero-time events, solve the initial network and record it. No positive step is integrated first, and h=0 is not
substituted into the companion formulas above. Capacitors preserve `initial_voltage`, inductors preserve `initial_current`, and both
default to zero. Network constraints determine the accompanying capacitor currents, inductor voltages and source currents, providing
consistent histories for the first step. Composite models follow the same conventions for their internal storage branches.

Existing regressions include these checkable initial values:

| Circuit | Consistent state and outputs at t=0 |
|---|---|
| Series 1 V source, 1 Ω, 1 F; `vC(0)=0.25 V` | `iC(0)=0.75 A` |
| Series 1 V source, 1 Ω, 1 H; `iL(0)=0.2 A` | `vL(0)=0.8 V` |
| 3 A injected into parallel 1 F and 2 F capacitors with equal initial voltage | Currents of 1 A and 2 A |
| Equal inductors connected to a floating star point, external voltages 400/0/0 V and zero initial currents | Initial neutral voltage `400/3 V` |
| Ideal `1+3t V` source parallel to 2 F; `vC(0)=1 V` | `iC(0)=6 A` |

The last case needs the source derivative to determine capacitor current. It runs directly:

```python
from pycy_emt_lite import Capacitor, Circuit, SimulationConfig, Simulator, VoltageSource

components = [
    VoltageSource("V", "n", "0", lambda t: 1 + 3 * t, derivative=lambda t: 3.0),
    Capacitor("C", "n", "0", 2.0, initial_voltage=1.0),
]
result = Simulator(Circuit.from_components("consistent_initial_state", components),
                   SimulationConfig(time_step=0.01, stop_time=0.02)).run()
assert abs(result.rows[0]["i:C"] - 6.0) < 1e-12
```

Constant sources have zero derivative, and three-phase sinusoidal sources supply analytic derivatives. A callable independent source
needs `derivative` only when network constraints require it; derivatives are not universally estimated by differencing or assumed zero.
Conflicting ideal-voltage/capacitor initial constraints, conflicting current/inductor initial constraints, or redundant ideal sources
with nonunique currents require corrected initial values or wiring. The program does not add small leakage resistors automatically
and does not support every higher-order algebraic-constraint topology.

## 5. Explicit-event left and right sides

`FaultApplyEvent/FaultClearEvent` change `Fault.enabled`; `BreakerOpenEvent/BreakerCloseEvent` change `Breaker.closed`.
`time` is the requested execution time and `target` is a component's `name`. Event times and standard-event targets are checked
before the first solve. Events beyond stop time are not executed and do not extend the simulation.

| `event_time_policy` | Treatment of off-grid events |
|---|---|
| `insert` (default) | Insert a result time point at the requested time |
| `quantize_up` | Delay to the next base grid point; log both requested and actual times |
| `require_aligned` | Raise before calculation, with guidance to align the time or choose another policy |

At each positive-time event point:

1. Integrate with the old topology to the left side of that time.
2. Apply events sorted by requested time; equal requested times preserve insertion order.
3. Hold dynamic states fixed and solve the right-side network with the new topology.
4. Update accompanying histories without advancing time or dynamic states again.
5. Save one right-side result row; retain each operation in the event log.

Capacitor voltage and inductor current remain continuous for supported finite switching; algebraic quantities such as resistor current
and node voltage may jump. If the new topology requires an instantaneous storage-state change or impulse, an error is required:
correct wiring or initial conditions, or use physically justified finite impedance. Zero-time and stop-time events also produce one
right-side row. Ordinary callable sources and PWM gate edges are not automatically converted to explicit events, so this mechanism
does not guarantee automatic detection of those discontinuities.

## 6. Metrics use actual times

[analysis/metrics.py](../pycy_emt_lite/analysis/metrics.py) treats signals as linear between adjacent result points.
Window boundaries inside an interval are clipped by linear interpolation. Sample-count averages are unsuitable for nonuniform grids
after event insertion. For interval h with endpoint values a/b, `∫x dt=h(a+b)/2` and `∫x² dt=h(a²+ab+b²)/3`.
For a product, `∫vi dt=h(2v0i0+v0i1+v1i0+2v1i1)/6`. Thus RMS is `sqrt(∫x²dt/T)` and average active power is `∫vidt/T`;
these are not trapezoidal integrals of sampled squares.

Integral windows need positive duration, with finite, increasing times. Integral metrics reject windows involving an interval with
an explicit-event jump: right-side-only records cannot reconstruct the left limit. Choose windows that do not cross switching.
This check relies on `event_log`; for CSV and other data without a log, the caller must ensure the window does not cross an event.
`peak_abs` is a sampled peak and permits one point; it does not locate the true continuous-waveform extremum.
`voltage_sag_summary` compares window RMS with nominal voltage and does not track sag duration.

Three-phase instantaneous active power is `va ia+vb ib+vc ic`, including zero-sequence contributions. Reactive power uses the
amplitude-invariant Clarke convention `q=1.5(vβ iα−vα iβ)`. Conventional interpretations of `sqrt(P²+Q²)` and the corresponding
power factor are limited to balanced sinusoids, not general unbalanced-system capacity definitions. Waveform comparisons should
state common physical times, window, directions, units and reference; a finer-step run is only a numerical comparison.

## 7. Repairing errors

| Problem | Repair |
|---|---|
| Noninteger-step stop, invalid step or start | Correct configuration using section 3; do not tolerate an incorrect endpoint |
| Output field collision | Rename the identified node or component; existing voltage, time or branch fields cannot be overwritten |
| Invalid control/PWM input or gate | Use finite real numeric parameters, samples and reset values; gates accept only Booleans or numeric 0/1 |
| Duplicate component names, missing or incompatible event target | Use unique names and target the appropriate Fault/Breaker |
| Repeated run or reused owned circuit | Create fresh components, Circuit and Simulator |
| Invalid R/L/C, turns ratio, time constant or control limits | Use the named parameter and allowed range in the error; check SI/per-unit units |
| Conflicting initial values or required source derivative | Check storage states against ideal constraints; supply analytic `derivative` when needed |
| Singular matrix | Check floating nodes, redundant ideal constraints and undetermined circulating currents; missing ground is not the only cause |
| Nonfinite source/matrix/solution or abnormal residual | Locate the reported time, component or solve context, then check parameter scales and step size |
| Invalid event-window metric | Select physical windows separately before and after switching |

Error checks do not establish physical correctness. Numerical validation still needs initial values, analytic/independent references,
KCL, energy and step convergence. Trapezoidal energy accounting uses interval-average voltages/currents; backward Euler additionally
has numerical dissipation. Model-specific evidence and unvalidated items are maintained only in the model document.
