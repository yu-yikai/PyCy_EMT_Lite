# PyCy_EMT_Lite

English | [简体中文](README.zh-CN.md)

PyCy_EMT_Lite is an **educational Python project for electromagnetic transient
(EMT) simulation of modern power systems**. It is a streamlined, approachable
edition of PyCy_EMT built around one clear workflow:

```text
Define components -> Build a circuit -> Configure the simulation -> Run -> Plot
```

There is no YAML configuration, no collection of parallel APIs, and no
architecture-specific documentation. The project keeps the focus on the
principles of EMT simulation and how they are implemented in code.

## Quick Start

```bash
uv sync                                      # Install dependencies (first run)
uv run python examples/01_r_circuit.py       # Run the first example
uv run pytest                                # Run the full test suite
```

You can also sample the complete learning path by running examples of increasing
complexity:

```bash
uv run python examples/04_rlc_transient.py               # Second-order RLC transient
uv run python examples/06_three_phase_short_circuit.py    # Three-phase short circuit
uv run python examples/10_park_generator_avr_governor.py  # Synchronous generator
uv run python examples/16_vsc_hvdc_average.py             # Average VSC-HVDC model
```

## What an Example Looks Like

Using `examples/01_r_circuit.py` as a reference, an example has three parts:
component objects, a case definition, and execution.

```python
from pycy_emt_lite import Resistor, SimulationConfig, VoltageSource
from pycy_emt_lite.cases import CaseDefinition, OutputOptions, PlotSpec, run_case

SAVE_RESULT_DATA = 0    # Set to 1 to save result data
SAVE_RESULT_FIGURE = 0  # Set to 1 to save figures
SHOW_FIGURE = True


def define_case() -> CaseDefinition:
    components = (
        VoltageSource("V1", "n1", "0", 10.0),  # 10 V DC source
        Resistor("R1", "n1", "0", 5.0),        # 5 ohm resistor
    )
    config = SimulationConfig(
        time_step=1e-4,
        stop_time=1e-3,
        method="trapezoidal",
    )
    plots = (
        PlotSpec(columns=("v:n1", "i:R1"), title="R-Circuit Voltage and Current"),
    )
    output = OutputOptions(show_figure=SHOW_FIGURE)
    return CaseDefinition(
        name="r_circuit",
        components=components,
        config=config,
        plots=plots,
        output=output,
    )


def main() -> None:
    case = define_case()
    run_case(case)  # Simulate, summarize, and plot automatically


if __name__ == "__main__":
    main()
```

`run_case()` runs the simulation, prints completion information and a result
summary (including analytical or theoretical comparisons), and plots the
waveforms. The foundational examples (01-05) compare simulation results with
analytical solutions in their summaries, making the results directly
verifiable.

## Learning Path: 16 Examples

| No. | Example | Topic |
|---:|---|---|
| 01 | `r_circuit` | DC resistive circuit and the basic modeling workflow |
| 02 | `rc_transient` | First-order RC charging transient |
| 03 | `rl_transient` | First-order RL current buildup |
| 04 | `rlc_transient` | Second-order RLC oscillation |
| 05 | `three_phase_steady_state` | Three-phase steady-state waveforms and RMS analysis |
| 06 | `three_phase_short_circuit` | Three-phase short-circuit fault and the event system |
| 07 | `single_phase_ground_fault` | Asymmetrical single-line-to-ground fault |
| 08 | `pi_line_transient` | Lumped-parameter pi transmission-line model |
| 09 | `single_phase_transformer` | Single-phase transformer (ratio, leakage reactance, and magnetization) |
| 10 | `park_generator_avr_governor` | Park dq0 synchronous generator with AVR and governor |
| 11 | `pll_dynamic_response` | SRF-PLL synchronization dynamics |
| 12 | `two_level_pwm_generator` | Two-level PWM inverter (switching model) |
| 13 | `three_phase_grid_inverter_average` | Three-phase average inverter with dq current control |
| 14 | `pv_grid_following` | Grid-following PV system with an irradiance step |
| 15 | `storage_grid_forming` | Islanded grid-forming battery system with VSG control |
| 16 | `vsc_hvdc_average` | Average VSC-HVDC model with a power step |

## Project Structure

```text
pycy_emt_lite/     # Core package with a single object-oriented Circuit/Simulator API
  core/            # Simulation kernel: circuits, configuration, dense solver, main loop
  components/      # RLC, sources, three-phase, lines, transformers, switches, power electronics
  controls/        # PI, limiting, filtering, transforms, PLL, and PWM
  converters/      # Average inverters, MMC, VSC-HVDC, and filter assemblies
  machines/        # Classical second-order and Park dq0 synchronous-machine models
  renewables/      # PV, battery, DC link, grid-following/grid-forming, and LVRT control
  events/          # Fault application/clearing and breaker opening/closing
  io/              # SimulationResult and CSV/JSON/NPZ output
  visualization/   # Plotting and Markdown reports
  analysis/        # RMS, peak, power, and voltage-sag analysis
  cases.py         # Unified CaseDefinition / run_case interface
examples/          # 16 examples ordered as a learning path
tests/             # Unit tests
docs/              # Theory, user guide, and example workflow documentation
```

## Requirements

- Python 3.14, managed with `uv`
- Runtime dependencies: NumPy, SciPy, and Matplotlib

## Recommended Theory Reading Order

Run the examples first, then read the theory documents in the order below to
connect the program behavior with the underlying mathematical models:

1. [Modified Nodal Analysis (MNA)](docs/theory/mna.md): motivation, equation form, and variable conventions
2. [Basic component modeling](docs/theory/basic_components.md): discretization of R, L, C, and sources
3. [Component stamping principles](docs/theory/stamp_principles.md): how each component contributes to the system matrix
4. [Three-phase systems](docs/theory/three_phase_systems.md): sources, lines, and loads
5. [Control systems](docs/theory/control_systems.md): PI control, PLLs, and coordinate transforms
6. [Power electronics](docs/theory/power_electronics.md): switching and average inverter models
7. [Line and transformer models](docs/theory/advanced_line_transformer_models.md): pi-section/Bergeron lines and transformers
8. [Renewable-energy models](docs/theory/renewable_grid_models.md): PV, batteries, and grid-following/grid-forming control

> The detailed documentation is currently written in Chinese. The numbered
> examples and Python APIs can still be followed directly from the source code.

## Documentation

- [User guide](docs/user_guide.md): detailed installation, execution, result-object, and troubleshooting information
- [Simulation program guide](docs/simulation_program_guide.md): how MNA assembly, solving, and state updates are implemented
- [Adding a new simulation example](docs/new_simulation_workflow.md): the workflow for creating a new case

## Relationship to PyCy_EMT

PyCy_EMT_Lite is a streamlined edition derived from the object-oriented API in
PyCy_EMT v0.6. It retains the object-oriented models and simulation kernel while
removing the YAML/CaseSpec compilation pipeline, architecture-specific code, and
related documentation. The package is named `pycy_emt_lite`, and the examples
have been renumbered into a progressive learning path.
