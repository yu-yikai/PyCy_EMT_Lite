# PyCy_EMT_Lite Simulation Program Guide

[简体中文](simulation_program_guide.md)

## 1. Overall flow

The recommended flow is `CaseDefinition -> Circuit -> Simulator -> SimulationResult`. A case declares components and configuration; the circuit assigns nodes and branch variables; the simulator solves consistent initial values, advances positive intervals and solves event right limits; the result stores time and named signals.

## 2. Case structure and run

Keep each example focused on one physical question. Declare units, time step, stop time, integration method, plots, and output flags near the top. Call `run_case(case)` from the repository root.

`SimulationConfig` currently supports only `start_time=0.0`. Create fresh simulator, circuit, and component instances for each run; full state restoration and checkpoint continuation are not implemented, so a nonzero `start_time` cannot continue a previous simulation.

### Consistent initialization and events

No integration occurs at `t=0`; `stop_time=0` still solves and records one consistent initial row. A 1 V, 1 kΩ, 1 μF RC circuit with zero capacitor voltage starts at `vC=0 V`, `iC=1 mA`. The first positive interval uses these histories. A capacitor parallel to an ideal voltage source must have the same initial voltage. Parallel capacitors also require matching voltages and share initial current according to capacitance. A floating inductor node uses differentiated KCL to determine its voltage. Conflicts, remaining underdetermination after one differentiation, and nonunique branch currents are rejected.

`VoltageSource(..., derivative=...)` and `CurrentSource(..., derivative=...)` accept constants or time functions for analytical dv/dt (V/s) and di/dt (A/s). They are evaluated and checked for finite values only when the consistency solve needs source derivatives. Constant sources default to zero derivative; `ThreePhaseSource` uses its analytical sinusoidal derivative. Ordinary full-rank RC/RL callable sources need no derivative. For example, `VoltageSource("V", "n", "0", lambda t: 1 + 3*t, derivative=3.0)` parallel to `Capacitor("C", "n", "0", 2.0, initial_voltage=1.0)` gives 6 A initially. A callable value alone cannot guarantee an exact derivative; no finite-difference fallback is used. Example 08 demonstrates a sinusoidal source.

Pi/segmented lines, three-phase RLC and linear transformer storage branches follow the same convention; composite initial values use existing state fields. Machines support direct consistency solves with mechanical/control states held; constrained internal sources needing derivatives are rejected. Transformer initialization does not advance flux. These initialization checks do not establish physical validity of saturation, machines or average control models.

At explicit events, first integrate the old network to the left limit, then apply same-time events in declaration order and solve one right limit. Keep capacitor voltage and inductor current continuous; use right-side algebraic values as the next trapezoidal histories. Record one right-side row and keep every event log entry. Do not reinitialize ordinary steps. Callable source jumps and PWM edges still use the actual sampled grid, without automatic left/right handling. Bergeron initial launch and aligned-event right-side history are checked; short delays and nonaligned grids/interpolation remain in the improvement plan.

## 3. Circuit preparation

`Circuit` owns the component collection and node registry. `prepare()` collects non-reference nodes, allocates extra branch-current unknowns, and gives components their matrix indices. Reference nodes are excluded.

## 4. Stamping and solving

At every time step the solver creates the system matrix and right-hand side, asks each component to stamp its conductance, source, constraint, or history contribution, and solves `A x = z`. Singular matrices usually indicate isolated nodes, conflicting ideal sources, or a missing path to ground.

## 5. State updates

After a solution is obtained, `component.update_state(context, solution)` stores capacitor voltage/current and inductor current/voltage history for the next step. This ordering is essential for EMT time marching.

## 6. Results and fields

Each result row contains `time`, node voltages such as `v:out`, and component currents/voltages such as `i:R1` and `v:R1`. Three-phase fields use names such as `v:load:a` and `i:LINE:a`. Use `plot_series()` or `plot_three_phase()` for display. CSV, JSON, NPZ, and figures are written only when the corresponding save flags are enabled. JSON and NPZ also store `event_log`.

## 7. Learning order

Run examples 01–04 first, then the three-phase and fault cases 05–07, line/transformer cases 08–10, and finally PLL, PWM, average inverter, PV, storage, and HVDC candidates 11–16. The latter candidates require stronger physical validation than the core path.

Related theory: [mna.en.md](theory/mna.en.md), [basic_components.en.md](theory/basic_components.en.md), [three_phase_systems.en.md](theory/three_phase_systems.en.md), and [stamp_principles.en.md](theory/stamp_principles.en.md).

## Detailed execution contract

### Initial preparation

The case creates a `Circuit` and registers every component. `prepare()` collects non-reference nodes, assigns node indices, allocates branch-current indices, and validates names and topology. The reference node is never an unknown.

### One time step

At t=0 apply same-time events, solve consistent storage/algebraic values and record them. For each positive interval, assemble and solve the old network and update states. Apply boundary events next, solve right-side algebraic values with storage held and update histories. Record the row after these updates, once per time point.

### Errors and results

A singular system can result from an isolated node, conflicting ideal voltage sources, or a winding without a reference path. The error should preserve the time and solver context instead of replacing every failure with a generic topology message. CSV stores tabular time-step fields; JSON and NPZ also preserve the event log.

### Learning path and evidence

Examples 01–04 establish R, RC, RL, and RLC behavior. Examples 05–07 cover balanced three-phase operation and faults. Examples 08–10 cover lines, transformers, and machine candidates. Examples 11–16 cover PLL, PWM, average inverter, PV, storage, and HVDC candidates and require stronger physical checks before being treated as trusted course material.

## Component lifecycle

### Registration

Components are created with names and terminal nodes. Names must be unique within a circuit. A reference node is not assigned a voltage unknown. Components with a dynamic state must expose enough information for initialization and later state update.

### Preparation

`Circuit.prepare()` builds the node registry and the unknown ordering. Static elements need only node indices. Voltage sources, inductors, and other elements that require a branch current receive additional indices. Preparation is the boundary between declaring a topology and solving it.

### Stamping

The stamp operation receives the current context and writes into the matrix and right-hand side. A resistor contributes a conductance; a current source contributes source entries; a voltage source contributes incidence entries and a voltage constraint; dynamic elements contribute a companion element and history term. Stamps must use the same current direction as the component's reported current.

### Solve and residual

The linear solve returns node voltages and extra branch currents in the prepared order. When a case diagnoses a numerical problem, retain the time, matrix shape, solver exception, and relevant residual or input field. Do not infer that every singularity is caused by a missing ground connection.

### State update order

The first solution holds declared capacitor voltages and inductor currents and calculates consistent current/voltage histories. Each positive step solves before updating these histories and output values; recording follows the update. Event consistency solves update algebraic values without advancing storage a second time.

## Output contract

`result.series("time")` is the authoritative time axis. The nominal `time_step` is a configuration value and does not replace the actual time differences when a short final step or event policy changes the spacing. `event_log` records topology changes and is serialized in JSON and NPZ. CSV remains a plain table and does not carry all metadata.

## Plotting and persistence

`plot_series(result, columns)` plots named fields. `plot_three_phase(result, columns)` requires three explicit phase fields. Data and figures are not written unless the corresponding flags are enabled. This keeps examples repeatable and prevents an ordinary run from polluting the repository.

## Numerical interpretation

Use the actual result time column for RMS, mean, and average-power windows. Do not interpolate across a topology jump when a statistic is intended to describe one physical regime. Exclude event-boundary samples consistently and state the window, units, direction, step, and tolerance in a physical comparison.
