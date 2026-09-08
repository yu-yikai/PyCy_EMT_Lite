# PyCy_EMT_Lite Minimal Improvement Plan

[简体中文](project_improvement_plan.md)

## 1. Goal and current conclusions

Keep a small EMT teaching project around `CaseDefinition -> Circuit -> Simulator -> SimulationResult`. Correct time, state, events and physical metrics before consolidating repeated material. Basic circuits can use `Circuit/Simulator` directly, without another wrapper.

The audit baseline was **2026-09-05 at HEAD `2aa55f9`**. The worktree now implements the items below. Passing tests establishes their assertions, not advanced-model physical validity.

| Task | Current implementation |
|---|---|
| B-02 reuse | Simulator/Circuit are single-run. Component ownership is checked before registration; prepared shallow circuit copies cannot reuse shared components |
| B-03 continuation | Nonzero `start_time` is rejected; unreachable simulator continuation branches were removed |
| B-05 inputs/errors | Config/event times, basic RLC parameters/initial states and independent sources reject NaN/Inf. Names and standard-event targets are checked; custom events remain compatible. Solver errors retain cause/time/solver, and stamp errors retain component/cause. Retained switches, Pi/segmented/Bergeron lines, three-phase sources/loads and transformers now have parameter checks, preserving valid zero/None; segment counts accept positive Python/NumPy integers |
| B-05 time boundaries | Positive durations retain 0/stop. Grid and dequeueing share pairwise 8 ULP rounding; events beyond terminal tolerance are ignored, near-zero positive events survive, and canonical grid/endpoints are preserved |
| B-06 results | Result transforms are removed; example 12 uses original `i:La/i:Lb/i:Lc` fields |
| B-07/B-10 metrics | Actual-time integration of linear signals and voltage/current products, window clipping, invalid/cross-event rejection, zero-sequence active power, and stated P/Q/S/PF limits |
| C example 07 | Complete 50 Hz pre/fault/post three-phase RMS replaces signed minima; analytical resistor-divider checks pass with unchanged wiring |
| C labels | Examples 11 and 13–16 use `explicit_control` for hand-written updates; no new solver mode/algorithm |
| D engineering | Existing wheel smoke checks installed path, version and a resistor solve. CI checks no default `outputs/`; no new job/dependency |
| B-01/B-04 | Initialization remains open. Removing blocking topology prechecks fixes the resistive t=0 breaker case; dynamic left/right limits remain open |

Current code validation (2026-09-08): **198 tests passed**, all 16 examples passed headlessly without `outputs/`, wheel/sdist excluded caches, and the exact CI wheel-check code passed after installation outside the checkout. This does not establish a new remote CI run.

The historical baseline had 65 tests, 16 examples and 43 package Python files. These describe the audit starting point, not pending work. MIT, the 25-symbol root API and one CI job already exist. This pass turns time/input defects into passing regressions; initialization and delay probes still need persistent regressions. Independent review found inconsistent time comparisons, now repaired. Reviewer usage limits interrupted the final pass; the lead agent checked the final rework.

## 2. Remaining problems

Reproduced means source/execution evidence establishes a defect. Insufficient validation means accuracy is not established. P0 covers core numerical errors, P1 input/time/model boundaries, and P2 documentation.

| Priority/task | Evidence and effect | Minimum remedy |
|---|---|---|
| P0 B-01 initialization, reproduced | `Simulator.run` integrates a full dt on the first row. A 1 V/1 kΩ/1 μF RC, dt=100 μs, stop=0, v0=0 records **0.047619 V** | Separate consistent initialization from integration; preserve vC/iL, set iC/vL histories, and cover composites before switching the main loop |
| P0 B-04 dynamic events, reproduced | 1 A charges 1 F with dt=0.1 s; a 1 Ω fault at 0.15 s produces **0.195122 V**. Initialization already gives 0.15 V at 0.1 s; the old topology should advance that actual state to 0.20 V after another 0.05 s, proving backward influence from the event | Integrate to the left limit, apply events, then hold storage states while solving right-side algebraic values. After both fixes: vC=0.15 V, iC=0.85 A, iF=0.15 A |
| P1 C delay lines, reproduced | Bergeron accepts dt=1 ms, delay=0.5 ms. `_delayed_sample` substitutes the latest 0 ms frame for the required 0.5 ms state | If retained, restrict fixed-grid/aligned-delay support and reject unavailable states instead of hiding them with the last frame |
| P1 B-08 insufficient validation | RC/RL final values and RLC boundedness/final values do not cover initial/whole-curve behavior. Lines lack AC amplitude/phase/propagation assertions; transformers lack loaded power balance; the PWM bridge lacks fundamental/step-sensitivity checks | Add analytical, conservation and convergence assertions over fixed windows in existing tests; fix initialization/events before dependent acceptance |
| P1 C advanced models, equation gaps confirmed | Example 15 sets `battery_power=load_power`, cancelling DC-link mismatch. HVDC derives line current from power mismatch, giving no loss for equal-power transfer. MMC arm R/L do not affect output equations | Remove candidates outside section 4 scope with exclusive content; do not build coupling/device frameworks to preserve names |
| P2 D documentation, partial | This pass corrects checkpoint claims and old plotting imports; duplicate entrypoints/out-of-scope theory remain | Consolidate existing bilingual documents while preserving useful information, without another audit report |

Keep completed ownership, single-run, event-prevalidation, metric and zero-sequence checks. A resistive t=0 breaker test does not establish dynamic event correctness.

## 3. Execution order and acceptance

Initialization has the highest priority but must not block independent input/time fixes. Work in existing files: failing assertions first, then implementation, then another agent's review. Use Luna/Terra for implementation/routine execution and Sol for numerical design/independent review, without more agent layers.

| Order | Scope and locations | Completion condition |
|---|---|---|
| 1, completed | `_time_points`, `EventQueue.pop_due`, retained-component validators; existing time-grid/event/component tests | Positive short duration retains 0/stop; stop=0 has one row; outside-stop events stay out; 0.1+0.2 rounding works; valid zero/None meanings remain and invalid inputs fail before solving |
| 2, B-01 validation | Existing basic/time-grid/line/three-phase/transformer tests and temporary equation experiments | Each structure below has an analytical result or explicit rejection reason; no permanently unused initializer or mode switch |
| 3, B-01 implementation | Existing basic/composite states and one internal consistency solve used by `Simulator.run` | No t=0 integration; zero/nonzero initial states and zero duration correct; supported retained line/PWM examples do not regress; conflicts/unsupported structures fail clearly |
| 4, B-04 implementation | Event order/history writes in `Simulator.run`; stable EventQueue order | RC/RL apply/clear/same-time/t=0/off-grid/stop events pass; continuous storage, right-side KCL/KVL, no duplicate time/advance |
| 5, B-08 and C/D | Physical assertions and section 4 consolidation; independently removable candidates may go earlier | Analytical/energy/convergence acceptance passes; removal includes exports, exclusive tests/examples/bilingual documents; full tests and retained examples pass |

### Initialization: minimum support

Initialize both storage **vC/iL** and consistent algebraic **iC/vL**. Merely displaying initial values while retaining wrong histories is insufficient. At t=0 apply same-time events, then initialize the right side. Only positive intervals use integration companions; `time_step=0` cannot enter existing 1/dt stamps.

| Required structure | Constraints | Minimum treatment |
|---|---|---|
| Ordinary RC/RL/RLC | Preserve C voltage/L current; solve resistor/source KCL/KVL | RC: 1 V/1 Ω/1 F, v0=0.25 V gives iC0=0.75 A. RL: 1 V/1 Ω/1 H, i0=0.2 A gives vL0=0.8 V. Temporary C-current unknowns are internal only |
| Ideal voltage source parallel to C | vC(0)=Vs(0), iC=C·dVs/dt when consistent | Reject conflicts. Request derivatives only when required; constant derivative is zero and existing sinusoidal sources have analytical derivatives |
| Parallel C | Consistent initial voltages, currents proportional to C | 3 A into 1 F/2 F gives dv/dt=1 V/s and 1 A/2 A. Not every underdetermined structure requires a source callback |
| Floating inductor star | Initial KCL and its derivative hold | Equal inductors, phase terminals 400/0/0 V and zero currents give neutral voltage 400/3 V; no added leakage or rewiring |
| Pi line, three-phase RLC, linear transformer | Every internal storage branch obeys the same relations | Read/write existing local nodes/parameters/states; compare initial/first-step results with independently decomposed equivalents, without a model registry/reflection interface |

An arbitrary `value(t)` cannot guarantee exact derivatives. Ordinary full-rank networks retain the current callable interface. Only necessary degenerate constraints may justify optional VoltageSource/CurrentSource derivative callbacks, checked for finite values. This interface is **not implemented**; first establish necessity and sufficiency with these cases. Do not add waveform class hierarchies or finite-difference fallback.

Underdetermination differs from inconsistent initial values. Explicit derivative constraints can complete the former; missing inputs mean unsupported, violated ideal constraints mean conflict. Keep the existing linear solver, without arbitrary regularization, epsilon steps, unconstrained least squares or a generic DAE framework. Redundant independent ideal sources whose branch currents are not unique must not receive fabricated outputs.

Limit support to linear RLC solvable directly or by differentiating constraints once. Reject remaining underdetermination/higher-order constraints. Check initial consistency separately: solving derivative equations does not prove the original ideal constraints hold.

Validate ordinary RLC in temporary experiments/existing tests, cover retained composites and constraints, then replace the loop. Line/PWM complexity must not postpone basic repair forever or cause silent fallback to old t=0 integration. Before switching, decide how to handle saturation, machines and delay history outside this linear initializer: removal, explicit rejection or independently validated dedicated treatment. They are not already covered by this proposal.

### Dynamic events: fixed order

1. Integrate `(t_prev, t_event)` with the old network to the left limit, advancing storage once.
2. Apply same-time events in declaration order. Keep each log, but solve the right limit only once for the final topology.
3. Hold vC/iL and reuse the consistency solve for right-side iC/vL; do not integrate a second positive interval.
4. Store right-side algebraic values for the next trapezoidal interval: capacitor `previous_current/last_current`, inductor `previous_voltage/last_voltage`, and equivalent composite histories. Do not change storage again.
5. Output one row per time, using event right-side values, and continue from that state. Events exactly at stop also execute and output right-side values.

Finite-resistance switching without impulses preserves storage. Reject ideal connections that conflict with states, force capacitor-voltage jumps or interrupt inductor current; impulses are outside scope. Do not reinitialize ordinary continuous steps.

This first covers explicit events. Callable source jumps/PWM edges lack automatic change-time and left/right information; inserting event times does not solve them. PWM stays sampled on the actual grid with separate step-sensitivity checks. Any necessary retained-example edge extension needs a concrete failure first, not a general crossing detector. Existing backward_euler is a switching reference; automatic method switching is neither implemented nor the default remedy.

### Time boundaries and delay lines

Result times must be finite, strictly increasing, start at 0 and end at stop. Positive duration cannot collapse to one point. Treat times within eight times the larger ULP of the compared pair around canonical grid/endpoints as the same instant; ULP is adjacent floating-point spacing. Floats cannot distinguish intentional nextafter from arithmetic rounding, so outside-stop means beyond that threshold. Near zero, only exact zero counts as zero. Do not impose a seconds-scale absolute floor on all small times.

Canonicalize the grid first and use the same rule for event dequeueing; do not loosen terminal filtering, alignment and pop_due independently. Cover inside/outside threshold, before/at/after stop, near zero, close consecutive events and all three policies.

Bergeron is optional. If retained, initially require `travel_time>=dt` and delay/stop/actual-event times aligned with fixed dt. Reject short final steps or inserted points before solving, without rewriting history interpolation. Require no response before arrival, matched-load arrival amplitude and open/short reflection. Finite fields do not prove propagation. Wavefront interpolation across history intervals needs separate validation from ordinary RLC variable-step support.

### Metrics and physical tests

Use piecewise-linear reconstruction for continuous windows. Duration h and endpoints a/b give integral `h*(a+b)/2` and square integral `h*(a*a+a*b+b*b)/3`. Divide by duration, then take the root for RMS. Points inserted on the same line leave metrics unchanged; interpolate window boundaries on that line.

For mean power, reconstruct voltage/current before integrating their product. Linear interpolation of sampled power would violate resistor `P=Vrms²/R`. P/Q share product integration without a signal-processing framework.

`trapezoid(x*x,time)` is an approximation: choosing it would require convergence rather than exact insertion invariance. Reject nonfinite/non-increasing axes and empty/single-point/zero-duration/out-of-range windows. Use pre/fault/post windows excluding jumps and adjoining intervals; cross-event integration is out of scope. Total instantaneous active power sums phase products. Alpha-beta q and S/PF from `sqrt(P²+Q²)` apply only under stated conditions, not general unbalanced/distorted power-quality claims.

B-08 uses existing tests for analytical R/RC/RL/RLC, KCL/KVL, passive energy and step-halving error. Compare fixed physical windows/common points, excluding events for smooth-region convergence order. Do not demand second order for every event algorithm. Model-specific checks follow below. B-09 reuses plotting/export tests without repeating display/save/no-save combinations for every example.

## 4. Models, examples and document reduction

These are subsequent scope decisions, not files already removed in this pass. With each deletion check imports, subpackage exports, tests, examples, READMEs and exclusive documents. Use Git history, not an archive directory.

| Model/examples | Minimum retained scope and acceptance |
|---|---|
| R/L/C/independent sources; 01–04 | Retain. 01 is Quick Start; 02–04 can form one unit. Keep small separate scripts when clearer than a multi-mode script |
| Three-phase/faults; 05–07 | Retain balanced behavior, three-phase short circuit and one asymmetric fault. Check fixed pre/fault/post RMS, sequence and phase power. Example 07 RMS/divider checks are complete |
| Pi line; 08 | Retain one lumped-line lesson; add AC steady-state amplitude/phase and current/energy checks |
| Single-phase transformer; 09 | Retain; add loaded ratio, leakage and power balance. Segmented lines/three-phase transformers need a clear course use |
| Bergeron | No current example, so optional. If retained, first require `travel_time>=dt` and fixed-grid delay/stop/events; check no-preresponse, arrival and reflection without a history-interpolation framework upgrade |
| IdealSwitch/PWM; 12 | Retain sampled switching; check phase currents, fundamental and step sensitivity. Alias-only `result_transform` is removed |
| Transforms/PI/PLL; 11 | Keep parts used in the final course and directly tested. Labels are corrected; pure control demonstrations need not be forced into MNA |
| Average GFL/GFM; 13–15 | At most one integrated case; assess 13 first. Merge/remove 14. 15 may replace 13 only after energy/independent-reference checks. If integration needs a new coupling framework, keep no integrated case this version |
| Park machine; 10 | dq ports/parameter effects lack evidence. Clearly rename/downgrade the proxy or remove it with exclusive content; do not build a full Park machine to justify its name |
| Diode/antiparallel IGBT, detailed PV, VSC-HVDC/MMC; 16 | Exclude from final scope; remove implementations/examples/exclusive documents after tracing dependencies. No generic Newton, active-set or full device library |
| Topology heuristics | Blocking use and unused code/imports are removed. Existing solver handles singularity; no topology-edge protocol |

Aim for 6–8 learning units, **not a file quota**. Two short RC/RL scripts may be simpler than extra branches/configuration. Advanced models without independent references leave the core scope without delaying basic fixes.

Consolidate documents into README entrypoints, numerical conventions and models/validation. Merge both languages together, preserving useful information and entrypoints. Do not shorten full translations into summaries or expand translation infrastructure.

| Existing content | Destination |
|---|---|
| `user_guide`, `new_simulation_workflow` | Necessary README operations; remove duplicate long code |
| `simulation_program_guide`, `theory/mna`, `basic_components`, `stamp_principles` | Numerical conventions: initial states, time, events, units, directions and a few basic stamps |
| Other theory | Models/validation: retained equations, limits, evidence and unverified items |
| `visualization_reporting` | Necessary plotting use in README/docstrings; remove old API content |
| This plan and its English version | Keep during improvement, remove when complete; no separate audit report |

Create `numerical_conventions.md`/`models_and_validation.md` only when actually merging content; remove replaced documents and update links in the same change. Keep joint bilingual edits equivalent without a full-text parity gate. Synchronize this plan and corrected passages in English. Start with a one-off link check; add a small test only for recurring regressions, not a documentation parser/site.

## 5. Minimum engineering gate and stopping conditions

Keep one Ubuntu/Python 3.14 CI job: locked installation, pytest, Quick Start, retained headless examples, build and source-external wheel import/version checks. The wheel command already includes a resistor assertion; do not add another script. Verify the installed import path so source files cannot conceal packaging omissions.

`git status --porcelain` misses ignored `outputs/`. Default examples disable saving and CI already checks no `outputs/`. Local caches need not be deleted. Identify the commit for remote CI evidence; equivalent local checks do not replace remote status.

Before adding a file/class/dependency ask: which confirmed problem needs it, why existing code cannot contain it, and how to verify it minimally. **A needed regression need not delete an old file.** Do not merge clear modules to meet a count. Keep NumPy/SciPy/Matplotlib/pytest instead of rewriting solvers/plots/tests for zero dependencies.

Numerical completion requires the original failure to pass; physical assertions with explicit windows/units/directions/tolerances; relevant regressions and retained examples; nearby necessary documentation; no new unused content. Documentation needs valid links, clear destinations and clean diffs, not unrelated numerical reruns. Never mark unverified work complete.

Do not build a second API, YAML/CaseSpec, course CLI, generic nonlinear/control coupling, reset/checkpoint, speculative sparse/streaming/LU caching, model cards/manifests/report generators, documentation site, complex CI matrix, coverage gate or recurring maintenance. Optimize only from default-course profiler evidence. Add platform checks for changed support or reproduced platform issues, and release facilities only after a publishing decision.

## 6. Necessary references

- [NumPy trapezoid](https://numpy.org/doc/stable/reference/generated/numpy.trapezoid.html): accepts actual coordinates without sorting them; it does not automatically give an insertion-invariant square integral.
- [PSCAD Interpolation and Switching](https://www.pscad.com/webhelp-v5-ol/EMTDC/Advanced_Features/interpolation_and_switching.htm): event-time/step effects on switching error; defines validation boundaries here, without copying a full interpolation mechanism.

References check definitions; project credibility still requires its own analytical, conservation, convergence and independent-reference evidence.
