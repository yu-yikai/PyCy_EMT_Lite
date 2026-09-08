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
`start_time=0` is supported. Results retain their original fields; the
`result_transform` callback has been removed. Known initialization and dynamic
event limitations remain listed in the [improvement plan](docs/project_improvement_plan.en.md).
Mean, RMS and average power use actual time; select separate continuous windows
for fault results instead of interpolating across events.

## Model Levels

The repository currently contains three different levels. They are not
interchangeable:

| Level | Meaning | Current use |
|---|---|---|
| Network EMT | MNA network solved at every time step | RLC, three-phase circuits, faults, pi line, transformer |
| Switching EMT | Ideal switches driven on the discrete time grid | Two-level PWM teaching example |
| Average control | Hand-written control/state updates without switching waveforms | Inverter, PV/storage, and HVDC candidates |

Examples 11 and 13–16 use the result label `explicit_control` for their hand-written
state updates. This is descriptive metadata, not a `SimulationConfig.method` option.
Examples 06–16 remain runnable, but several still need stronger physical
checks, consolidation, or removal before they enter the default learning path.
This README is a concise entrypoint. The [English improvement plan](docs/project_improvement_plan.en.md)
describes model scope and documentation consolidation; the [Chinese README](README.zh-CN.md)
also includes a per-example decision table.

## Recommended Starting Path

| Example | Learning objective | Current evidence |
|---|---|---|
| `01_r_circuit.py` | Object workflow and static MNA | Exact voltage/current unit test |
| `02_rc_transient.py` | Capacitor companion model | Analytical end-point comparison; full-curve checks planned |
| `03_rl_transient.py` | Inductor branch-current variable | Analytical end-point comparison; full-curve checks planned |
| `04_rlc_transient.py` | Coupled second-order transient | Analytical end-point comparison; energy/convergence checks planned |
| `05_three_phase_steady_state.py` | Balanced three-phase RMS | Balanced-RMS unit test; planned merge with the fault lesson |

## Minimal Project Structure

```text
pycy_emt_lite/   # simulation kernel and model implementations
examples/        # runnable teaching cases
tests/           # numerical and physical regression checks
docs/            # documentation being consolidated
```

Import the core teaching API from `pycy_emt_lite`. Advanced candidates are
available only from their explicit subpackages while their scope is reviewed.

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
