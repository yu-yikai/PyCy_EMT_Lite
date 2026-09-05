# Standard Workflow for a New Simulation Case

[简体中文](new_simulation_workflow.md)

## 1. Template

Declare components, configuration, plots, and output options, then call `run_case(case)`. Keep saving disabled by default.

## 2. Components and nodes

Use descriptive component names and explicit nodes. Use `"0"`, `"gnd"`, or `"ground"` for reference. State units and give each example one primary learning objective.

## 3. Dynamic elements and events

Choose the step from the fastest process and check initial conditions. Put faults, breaker changes, and other topology changes in the event list. Evaluate pre-event, event, and post-event windows separately.

## 4. Split complex cases

Start with a source, load, and one dynamic element. Add lines, transformers, controls, or power electronics only after KCL/KVL, analytical values, energy, or convergence checks are available.

## 5. Control-level cases

Clearly label average-control and hand-written state updates. They are not automatically part of the `Circuit`/`Simulator` trapezoidal EMT path. Record the actual sampling interval and test saturation, power direction, and state limits.

## 6. Organization

Run examples from the repository root, use the public API, avoid hidden global state, and print only unit-bearing observations. Keep pass/fail thresholds in tests rather than relying on visual inspection.

## Recommended case template

1. State one physical question and its analytical or physical check.
2. Define nodes and components with explicit SI units.
3. Define time step, stop time, integration method, and initial values.
4. Add events in chronological order with valid target names.
5. Run the smallest circuit first, then add topology and control complexity.
6. Save data or figures only when the case explicitly requests them.

## Validation checklist

Check `t=0`, the first step, each event boundary, and the final short step if present. Compare resistive circuits with Ohm's law, dynamic circuits with analytical solutions, and passive circuits with KCL/KVL, residual, energy, or step-convergence checks.
