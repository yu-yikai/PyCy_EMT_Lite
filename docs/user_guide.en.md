# PyCy_EMT_Lite User Guide

[简体中文](user_guide.md)

This guide explains installation, examples, custom cases, and tests.

## Requirements

- Python 3.14
- [uv](https://docs.astral.sh/uv/) (recommended)

## Install and run

From the project root:

```bash
uv sync
uv run python examples/01_r_circuit.py
uv run pytest
```

The first command creates the environment and installs NumPy, SciPy, Matplotlib, and other dependencies. Examples display waveforms when possible; set `SAVE_RESULT_DATA = 1` or `SAVE_RESULT_FIGURE = 1` to save outputs. A headless backend skips the display without changing the calculation.

## Write a case

See [new_simulation_workflow.en.md](new_simulation_workflow.en.md). The public workflow is:

```python
from pycy_emt_lite import Resistor, SimulationConfig, VoltageSource
from pycy_emt_lite.cases import CaseDefinition, OutputOptions, PlotSpec, run_case

case = CaseDefinition(
    name="r_circuit",
    components=(VoltageSource("V1", "n1", "0", 10.0), Resistor("R1", "n1", "0", 5.0)),
    config=SimulationConfig(time_step=1e-4, stop_time=1e-3, method="trapezoidal"),
    plots=(PlotSpec(columns=("v:n1", "i:R1"), title="R-circuit voltage and current"),),
    output=OutputOptions(save_data=False, save_figure=False),
)
run_case(case)
```

## Results and troubleshooting

`run_case()` returns `SimulationResult`. Use `result.series("v:out")` for a NumPy column, `to_csv()`, `to_json()`, or `to_npz()` to save it, and `SimulationResult.from_json()` to load it. Analysis helpers are in `pycy_emt_lite.analysis`; plotting helpers are in `pycy_emt_lite.visualization`.

For a singular matrix, check isolated nodes and voltage-source or transformer paths to ground. For divergence, reduce the time step and check dynamic parameters.

## Complete case workflow

The recommended sequence is to construct components, create a `SimulationConfig`, define plot specifications, build a `CaseDefinition`, and call `run_case()`. Keep the case runnable from the repository root and avoid changing package-global state.

Result columns use stable names: `v:node` is a node voltage, `i:component` a component current, and `v:component` a terminal voltage. Three-phase signals add a phase suffix such as `v:load:a`.

For a fault or switching study, report pre-event, event, and post-event windows separately and preserve the event log with the result. A completed run or plausible plot is not by itself a physical validation.
