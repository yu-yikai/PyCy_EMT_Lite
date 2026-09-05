# PyCy_EMT_Lite Simplification and Improvement Plan

[简体中文](project_improvement_plan.md)

## Goals and principles

The project should reduce its public API, models, examples, and documents; fix time, state, event, error, and metric semantics; retain a small set of physically checked EMT lessons; and maintain one minimal CI workflow. The only public workflow is `CaseDefinition -> Circuit -> Simulator -> SimulationResult`.

Before adding a file, class, script, document, or dependency, answer why existing content cannot be changed or merged, which confirmed teaching goal needs it, how it will be tested, and what it replaces. If there is no clear answer, do not add it.

## Scope and minimum structure

The project teaches MNA, discretization, time marching, events, and basic control in small EMT circuits. It does not claim facility-grade accuracy, real-time/HIL capability, complete device nonlinearities, engineering MMC/HVDC, or production research capability. The minimum product should contain the package, a small set of validated examples and tests, bilingual README entrypoints, and two compact target documents for numerical conventions and models/validation.

## Phases

### Phase A: reduce and baseline

Audit exports, give every example one objective and one verification method, map existing documents to the target documents, state model boundaries in both READMEs, choose a compatible license, and establish a single CI job.

### Phase B: repair the trusted core

Define `t=0`, first-step, event-boundary, and short-final-step semantics. Reject instance reuse, invalid inputs, duplicate names, and invalid event targets. Preserve raw results, use the actual time column for metrics, and add analytical, KCL/KVL, residual, energy, and step-convergence checks.

### Phase C: keep the smallest trusted course

Retain R/L/C, sources, ideal switching, faults, the minimal three-phase set, Pi lines, and single-phase transformers when physical tests pass. Keep controls, PWM, PLL, and at most one renewable-system average case only when they have a clear course role and independent checks. Remove or defer unsupported advanced models rather than creating general frameworks for them.

### Phase D: consolidate documentation and CI

The product documentation should have one complete Chinese entry, a short English entry, a numerical-conventions document, and a models-and-validation document. Update only the nearest necessary document when behavior changes. CI should run locked installation, tests, the README quick start, retained examples headlessly, a wheel build, an installed-wheel smoke test, and a clean-tree check.

## Out of scope and completion definition

Do not add YAML/CaseSpec, a second API, a teaching CLI, a general nonlinear framework, checkpoints, a documentation website, broad platform matrices, or release/security infrastructure without new evidence. A task is complete only when the defect or documentation change is checkable, the scope is surgical, numerical assumptions are explicit, physical checks pass, required documentation is updated, and no unused files, symbols, or dependencies were introduced.

External references define questions to verify; they do not replace analytical, conservation, convergence, or independent-reference checks in this project.

## Phase A exit gate

- No top-level physical model lacks a course purpose.
- Every retained example has one objective and a checkable observation.
- New models, examples, and documents are frozen until existing correctness issues are addressed.
- Audit conclusions are reflected directly in code, README, tests, or target documents.

## Phase B acceptance gates

Each defect must first be reproduced by a failing test. Time, event, and statistical windows must be testable without manually inspecting a wide plot. Halving the step should move results toward an analytical solution or independent reference. Solver failures must retain their root cause and context. Do not introduce session, checkpoint, callback-security, manifest, or general-validation frameworks.

## Phase C model decisions

Retain R/L/C and independent sources as the trusted core with analytical, KCL/KVL, residual, and convergence checks. Retain ideal switches, faults, and breakers only with deterministic event and gate-boundary tests. Retain three-phase sources, loads, and faults with balanced and unbalanced checks. Retain Pi lines and single-phase transformers with ratio, conservation, and transient checks. Keep Bergeron only if propagation, arrival, reflection, and event timing can be verified.

Controls, coordinate transforms, PLL, and PWM should remain only when used by final examples and covered by independent tests. Retain at most one renewable-system average case after checking power direction, limiting, DC/storage energy balance, disturbance response, and an independent reference. Do not preserve advanced names merely to avoid deletion.

## Phase D maintenance rules

When public API, result fields, or commands change, update the relevant README and example. When equations, units, directions, time, or event semantics change, update the nearest target document and its test. When a model changes status, update the learning order and validation record. When Python or dependencies change, update `pyproject.toml`, `uv.lock`, README, and CI.

The minimum CI should run locked installation, tests, the README quick start, retained examples with `MPLBACKEND=Agg`, a wheel build, an installed-wheel import/version smoke test, and a clean-tree check. Do not add release infrastructure until the corresponding product decision is real.

## Detailed minimum structure

The intended repository contains a short English README, a complete Chinese README, the package implementation used by the course, approximately six to eight single-objective examples, numerical and physical tests, and two consolidated documents. It should not pre-create empty directories or maintain archive copies of obsolete plans.

## Phase A work items

The public API audit separates supported physical model families, internal helpers, and deletion candidates. The example audit records one learning objective and one validation method for each current script. The documentation audit maps each old document to a consolidated target or deletion. The boundary audit distinguishes network EMT, switching EMT, and average-control models. The CI baseline runs tests, retained examples, package build, wheel smoke, and a clean-tree check.

## Phase B technical requirements

Time semantics must define `t=0`, the first interval, event application, event clearing, and a final short interval. A `Simulator`, `Circuit`, or stateful component should not silently participate in multiple runs. Unsupported nonzero start times should be rejected rather than implying checkpoint continuation.

Events at one time are processed in declaration order. Inputs must reject NaN and Inf before the first solve, invalid nodes, duplicate component names, and unknown event targets. Results should remain raw; a callback must not mutate the stored simulation result.

Metrics must use actual time spacing. Redundant samples should not change a time-weighted statistic. Statistics should not cross a topology jump by implicit interpolation, and event-window boundaries must be explicit. Add physical tests for R, RC, RL, RLC, events, three-phase basics, and transformer basics.

## Phase C evidence rules

Analytical solutions and physical invariants are preferred. Add only one or two independent references when no analytical solution exists. If reference data is introduced, record its source, software version, parameters, units, signal mapping, and associated test in one model-validation document. Do not create generic manifests, reports, or validation frameworks.

The first example decisions are: correct the single-phase fault metric to use pre/fault/post windows; do not call hand-written control stepping trapezoidal EMT; remove a VSC-HVDC candidate until DC-link, line-loss, and power-balance contracts are credible; and do not call a simplified machine a full Park dq0 EMT generator.

## Phase D documentation rules

The Chinese README is the complete navigation entry. The English README synchronizes only boundary, installation, quick start, and supported versions. Numerical conventions contain MNA, initial values, time, events, units, directions, and a few basic stamps. Models and validation contain model level, limitations, equations, evidence, and unresolved items.

Do not copy long legacy documents unchanged into the consolidated targets. Do not create `docs/index.md`, archive directories, per-model report folders, metadata owners, SLA fields, bilingual parity YAML, version selectors, or quality dashboards. Update documentation when behavior changes, not on a fixed calendar.
