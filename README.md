# PyCy_EMT_Lite

English | [简体中文](README.zh-CN.md)

PyCy_EMT_Lite is a small, pure-Python teaching project for electromagnetic
transient (EMT) simulation of modern power systems. Its recommended public
workflow is:

```text
CaseDefinition -> Circuit -> Simulator -> SimulationResult
```

> **Teaching scope:** version 0.1 is being reduced to a small trusted model set.
> It is not a facility-grade EMT tool and must not be used for protection
> settings, grid-code compliance, equipment design, or operational decisions.

## Quick Start

Requires Python 3.14 and [uv](https://docs.astral.sh/uv/).

```bash
uv sync --locked
uv run python examples/01_r_circuit.py
uv run pytest
```

Example 01 is the trusted starting point. It exercises the complete object
workflow and checks the simulated voltage against the analytical circuit value.

Create fresh simulator, circuit and component instances for each run, including
components inside a case definition. Time parameters must be finite and only
`start_time=0` is supported. `stop_time` must be a nonnegative integer multiple
of `time_step`; invalid
configuration raises an error with repair advice before simulation. An 8 ULP
rounding tolerance accepts expressions such as `0.1 + 0.2` on a 0.1 s grid.
Results retain their original fields; the
`result_transform` callback has been removed. The first row preserves declared
capacitor voltage and inductor current, with consistent current/voltage histories.
Explicit events advance the old network to the event time, then solve right-side
algebraic values with storage states held. Impulsive state changes are rejected.
Constrained callable sources may require an analytical `derivative` (V/s or A/s);
see the [initialization contract](docs/simulation_program_guide.en.md#consistent-initialization-and-events).
Mean, RMS and average power use actual time; select separate continuous windows
for fault results instead of interpolating across events.

## Model Levels

The retained models use the following levels and approximations:

| Level | Meaning | Current use |
|---|---|---|
| Network EMT | MNA network solved at every time step | RLC, three-phase circuits, faults, pi line, transformer |
| Switching EMT | Ideal switches driven on the discrete time grid | Two-level PWM teaching example |
| Electromechanical approximation | Algebraic dq stator ports with explicit mechanical/control dynamics | Fourth-order synchronous-generator example 10 |
| Discrete control | Hand-written control/state updates without an electrical network solve | Standalone PLL example 11 |

Example 11 uses the result label `explicit_control` for its hand-written state
updates. This is descriptive metadata, not a `SimulationConfig.method` option.
Examples 13–16 and their average inverter, PV/storage and HVDC/MMC models have been
removed under the scope-reduction plan, along with the Diode/IGBT approximations.
This version has no integrated GFL/GFM example. Both synchronous-machine models
and example 10 are retained and improved: corrected power accounting, consistent
state timing and separate d/q transient reactances in the Park terminal equations.
The 13 remaining scripts retain their original numbers: 01–12 and 17.
This README is a concise entrypoint. The [English improvement plan](docs/project_improvement_plan.en.md)
describes model scope and documentation consolidation; the [Chinese README](README.zh-CN.md)
also includes a per-example decision table.

## Recommended Starting Path

| Example | Learning objective | Current evidence |
|---|---|---|
| `01_r_circuit.py` | Object workflow and static MNA | Exact voltage/current unit test |
| `02_rc_transient.py` | Capacitor companion model | Initial state/current, first interval and analytical step-halving tests |
| `03_rl_transient.py` | Inductor branch-current variable | Initial state/voltage, first interval and analytical step-halving tests |
| `04_rlc_transient.py` | Coupled second-order transient | Damped whole-curve/KCL/convergence tests and lossless LC energy test |
| `17_single_phase_ac_rlc.py` | Single-phase AC source and series RLC | Zero initial states, steady phasor/RMS and KCL/KVL checks |
| `05_three_phase_steady_state.py` | Balanced three-phase RL load | Zero-current startup, phase sequence, phasor/RMS and P/Q checks |

Run the additional AC example with `uv run python examples/17_single_phase_ac_rlc.py`.
It connects a 220 V RMS, 50 Hz source to 20 Ω, 50 mH and 100 μF in series.
Voltage and current use separate figures; data and figure saving are off by default.
Edit the parameters and output flags at the top. The default 0.08–0.12 s window
compares current RMS and phase with `Z = R + j(ωL - 1/ωC)`; after changing the
frequency or damping, choose complete steady-state cycles for that window.

Examples 08, 09 and 12 also have quantitative summaries and physical regressions:
Pi-line phasors/energy, loaded linear-transformer power including magnetizing DC,
and PWM fundamental/step sensitivity. Voltage and current use separate figures
in 08/09; PWM reports total RMS separately from its fundamental.

Example 05 uses a 20 Ω + 50 mH load per phase, with zero-current startup and a
phasor/power summary. Example 06 adds 5 mH per line phase and uses a 10 μs step to
resolve fault clearing. It reports pre/fault/post RMS and load power, and plots
continuous line currents separately from fault currents and bus voltages. The
ideal circuit produces a brief clearing overvoltage as line current transfers
to the resistive load; it contains no surge arrester or parasitic capacitance.

Run `uv run python examples/10_park_generator_avr_governor.py` for a synchronous
generator load step with AVR/governor. It starts from a balanced operating point
and uses a fourth-order dq machine with algebraic stator ports and explicit Euler
mechanical/control updates. See the [machine equations and usage](docs/theory/advanced_line_transformer_models.en.md)
for units, initialization, power balance and the limits of this near-fundamental approximation.

## Minimal Project Structure

```text
pycy_emt_lite/   # simulation kernel and model implementations
examples/        # runnable teaching cases
tests/           # numerical and physical regression checks
docs/            # documentation being consolidated
```

Import the core teaching API from `pycy_emt_lite`. Optional line/transformer
candidates remain in explicit subpackages while their scope is reviewed.
The machine classes remain in `pycy_emt_lite.machines`. The former renewable and converter-average classes are no longer available;
`pycy_emt_lite.converters` retains only the existing L/LC/LCL filter assemblies.

## Documentation

- [简体中文 README](README.zh-CN.md): complete project entry and example status
- [Improvement plan](docs/project_improvement_plan.en.md): phased reduction and
  correctness work

The existing theory documents are being consolidated into one numerical
conventions document and one model/validation document. Until that work is
complete, source docstrings and tests define implemented behavior.

## Relationship to PyCy_EMT

PyCy_EMT_Lite is a streamlined teaching edition derived from the object-oriented
PyCy_EMT v0.6 workflow. It intentionally excludes the YAML/CaseSpec pipeline and
other platform-level architecture.

## License

[MIT](LICENSE)
