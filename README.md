# PyCy_EMT_Lite

English | [简体中文](README.zh-CN.md)

PyCy_EMT_Lite is a pure-Python teaching project for small electromagnetic-transient simulations, using
`CaseDefinition → Circuit → Simulator → SimulationResult`. Basic circuits may use `Circuit/Simulator` directly.
Equations, evidence and applicability are in [Models and validation](docs/models_and_validation.en.md).
For step-by-step derivations from physical equations to discrete models, matrix stamps and history updates, see [Component derivations](docs/component_derivations.en.md), including a runnable RLC matrix check.
The scope is teaching and algorithm checks, not plant-scale EMT, protection settings, equipment design or operational decisions.

## 1. Install and run

Use Python 3.14 and [uv](https://docs.astral.sh/uv/) from the project root:

```bash
uv sync --locked
uv run python examples/01_r_circuit.py
uv run pytest
```

Dependencies are NumPy, SciPy and Matplotlib; tests use pytest. Examples display figures by default without saving data or images.
For network cases, set `SAVE_RESULT_DATA` or `SAVE_RESULT_FIGURE` at the top of the script to `1` to save to `outputs/<case-name>/`.
The standalone PLL example 11 only displays a plot and has no saving flags.
Noninteractive backends such as `MPLBACKEND=Agg` skip window display while retaining computation and saving.

## 2. Learning order

Thirteen introductory scripts and one integrated example form nine units. Integrated average renewable/converter and HVDC/MMC candidates 13–16 were removed; retained commands keep their original numbers.

| Unit | Scripts | Topics |
|---|---|---|
| R and MNA | [01](examples/01_r_circuit.py) | Object workflow, Ohm's law and source-current direction |
| Dynamic RLC | [02 RC](examples/02_rc_transient.py), [03 RL](examples/03_rl_transient.py), [04 RLC](examples/04_rlc_transient.py), [17 AC RLC](examples/17_single_phase_ac_rlc.py) | Initial conditions, time constants, storage, phasors and step error |
| Three-phase and faults | [05](examples/05_three_phase_steady_state.py), [06](examples/06_three_phase_short_circuit.py), [07](examples/07_single_phase_ground_fault.py) | Balanced RL, three-phase short circuit, single-phase grounding and fixed-window metrics |
| Lines | [08](examples/08_pi_line_transient.py) | Pi line; segmented and Bergeron models provide optional comparisons |
| Transformers | [09](examples/09_single_phase_transformer.py) | Turns ratio, leakage and magnetization; three-phase connections are in the model document |
| Synchronous machines | [10](examples/10_park_generator_avr_governor.py) | Equilibrium initialization, load step, AVR and governor |
| Discrete control | [11](examples/11_pll_dynamic_response.py) | SRF-PLL in a standalone control loop |
| PWM | [12](examples/12_two_level_pwm_generator.py) | Ideal switches, SPWM and RL current |
| Integrated VSC-HVDC | [18](examples/18_three_terminal_vsc_hvdc.py) | Three two-level bridges, independent PLL/dq loops, bipolar DC network and AC fault |

Run `uv run python examples/18_three_terminal_vsc_hvdc.py` for the default FAST case (20 μs, 0.8 s).
Set `MODE` in that script to `FULL` (5 μs) or `BENCHMARK` (2 μs) for 2.5 s runs.
The [complete benchmark guide](docs/three_terminal_vsc_hvdc.en.md) gives source mapping, parameters, validation and model adjustments, including the fault-clearing RC snubber.

Example 17 uses a 220 V RMS, 50 Hz source in series with 20 Ω, 50 mH and 100 μF, with separate voltage/current figures.
Its default steady-state phasor window is 0.08–0.12 s; select a new window after changing frequency or damping.
Example 10 retains a fourth-order synchronous generator, starting at equilibrium and adding load at 0.2 s, with separate voltage/field, speed and power figures.
The classical synchronous machine also remains; the two models have different approximations. Example 11's `explicit_control` label describes its explicit control loop and is not an EMT integration-method option.

## 3. Write a case

Save the following as a Python script and run it. Parameters stay beside the components, and voltage/current use separate figures.

```python
from pycy_emt_lite import Resistor, SimulationConfig, VoltageSource
from pycy_emt_lite.cases import CaseDefinition, OutputOptions, PlotSpec, run_case

SAVE_RESULT_DATA = 0
SAVE_RESULT_FIGURE = 0

def define_case() -> CaseDefinition:
    components = (
        VoltageSource("V1", "n1", "0", 10.0),
        Resistor("R1", "n1", "0", 5.0),
    )
    config = SimulationConfig(time_step=1e-4, stop_time=1e-3)
    plots = (
        PlotSpec(("v:n1",), figure_name="voltage.png", title="Voltage / V"),
        PlotSpec(("i:R1",), figure_name="current.png", title="Current / A"),
    )
    output = OutputOptions(save_data=bool(SAVE_RESULT_DATA),
                           save_figure=bool(SAVE_RESULT_FIGURE), show_figure=True)
    return CaseDefinition("my_r_circuit", components, config, plots=plots, output=output)

if __name__ == "__main__":
    case = define_case()
    result = run_case(case)
```

Longer cases can put a summary in `CaseDefinition.summary`, events in `events`, and three-phase figures in `PlotSpec(kind="three_phase")` with exactly three columns.
Every plot needs `figure_name` when saving images. Extract functions only for logic that becomes long or needs reuse; examples do not import each other.
Create intermediate `case`, `circuit` and `simulator` objects before the next operation to make execution and debugging easy to follow.

Create fresh components, `Circuit` and `Simulator` for each run; calling `define_case()` again obtains new components.
Components inside a `CaseDefinition` are also single-use. Only `start_time=0` is supported; `stop_time` must be a nonnegative integer number of base steps.
A 100 μs step cannot stop at 250 μs: choose 200/300 μs or a 50 μs step.
Initial conditions, source derivatives and event rules are in [Numerical conventions](docs/numerical_conventions.en.md).

## 4. Read, plot and save results

`result.columns` lists fields; `result.series("v:n1")` returns a NumPy array. Node voltage is `v:<node>` and ordinary branch current is `i:<component>`; see model descriptions for three-phase/composite fields.
Node voltages are relative to reference ground; current delivered by a voltage source is opposite to its branch-current direction.

This code continues with `result` from the preceding example, explicitly saves JSON and reads it back for comparison:

```python
from pycy_emt_lite import SimulationResult
from pycy_emt_lite.analysis import rms
from pycy_emt_lite.visualization import plot_result_comparison, plot_zoom_window, write_markdown_report

voltage_rms = rms(result, "v:n1", start_time=0.0, end_time=1e-3)
result.to_json("outputs/my_r_circuit/result.json")
loaded = SimulationResult.from_json("outputs/my_r_circuit/result.json")
plot_result_comparison([result, loaded], "v:n1", labels=["original", "loaded"], show=False)
plot_zoom_window(result, ["v:n1"], 0.0, 5e-4,
                 output_path="outputs/my_r_circuit/zoom.png", show=False)
write_markdown_report(result, "outputs/my_r_circuit/report.md",
                      summary={"Voltage RMS / V": voltage_rms}, figure_paths=["zoom.png"])
```

`to_csv/from_csv` and `to_npz/from_npz` are also available. JSON/NPZ retain metadata and `event_log`; CSV contains only tabular data.
Supply the case name/method when reading CSV; its inferred first interval need not equal the original base step. Reading a file does not restore resumable simulation state.
Other plotting functions are `plot_series` and `plot_three_phase`; `output_path` supports extensions such as PNG/SVG/PDF.
Reports organize existing results and user-provided summaries; they do not establish model correctness.
Window and direction rules for RMS, mean, three-phase power, sampled peaks and sag statistics are in [Numerical conventions](docs/numerical_conventions.en.md).

## 5. Documents and source

| Document | Contents |
|---|---|
| This README | Installation, learning order, case creation and result operations |
| [Numerical conventions](docs/numerical_conventions.en.md) | MNA/stamps, units, initialization, time, events, metrics and diagnostics |
| [Component derivations](docs/component_derivations.en.md) | Physical equations, TR/BE discretization, local MNA matrices, history updates and the complete EMT loop |
| [Models and validation](docs/models_and_validation.en.md) | Retained equations, example parameters, evidence and unvalidated scope |
| [Three-terminal VSC-HVDC](docs/three_terminal_vsc_hvdc.en.md) | Reference mapping, switching network, closed-loop control, modes, fault and validation |

The root exposes `CaseDefinition`, `Circuit`, `Simulator`, `SimulationResult`, basic RLC/independent sources, switches/faults/events,
three-phase sources/lines/loads, Pi lines and single-phase transformers. See the [root interface](pycy_emt_lite/__init__.py) for exact exports.
Import machines from `pycy_emt_lite.machines`, L/LC/LCL from `pycy_emt_lite.converters`, and segmented/Bergeron/three-phase Pi lines and three-phase transformers from their `components` modules.
Use the respective subpackages for control, analysis and plotting; importability does not imply complete physical validation.

`pycy_emt_lite/` contains implementations, `examples/` cases, `tests/` regressions, and `docs/` full bilingual versions of the four topics above.
New components need physical/discrete equations, units/directions, initialization/event behavior, and an analytical, conservation or independent-reference check.
Update the learning table for new cases; avoid wrappers, dependencies or entrypoints added only for organization.
Documentation links to repository files use relative paths; execution and output paths are relative to the project root. Identify external references by public source links and filenames, without personal absolute paths or temporary validation directories.

PyCy_EMT_Lite derives from the object workflow in PyCy_EMT v0.6, retaining material suitable for small teaching models. [MIT license](LICENSE).
