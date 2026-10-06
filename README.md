# PyCy_EMT_Lite

English | [简体中文](README.zh-CN.md)

PyCy_EMT_Lite is a pure-Python teaching project for small electromagnetic-transient (EMT) simulations: it calculates circuit voltages and currents at short time intervals.
The workflow is
`CaseDefinition → Circuit → Simulator → SimulationResult`. Basic circuits may use `Circuit/Simulator` directly.
Equations, evidence and applicability are in [Models and validation](docs/models_and_validation.en.md).
For step-by-step derivations from physical equations to discrete models, matrix stamps and history updates, see [Component derivations](docs/component_derivations.en.md), including a runnable RLC matrix check.
The scope is teaching and algorithm checks, not plant-scale EMT, protection settings, equipment design or operational decisions.

## 1. Install and run

### First run on Windows

1. On the [project page](https://github.com/yu-yikai/PyCy_EMT_Lite), choose **Code → Download ZIP**, extract it, and open the folder containing `pyproject.toml`, `README.md` and `examples`. This is the "project root"; if you already have a local copy, open that folder directly.
2. Type `powershell` in the File Explorer address bar and press Enter to open a terminal in that folder. Run the following commands there, waiting for each command to finish before starting the next.
3. If [uv](https://docs.astral.sh/uv/getting-started/installation/) is not installed, run its official installation command in PowerShell:

   ```powershell
   powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
   ```

   Close the terminal after installation, reopen it as in step 2, and run `uv --version`. Continue once it prints a version number.
4. Run these commands one at a time:

```powershell
uv sync --locked
uv run python --version
uv run python examples/01_r_circuit.py
```

`uv sync --locked` installs dependencies from `uv.lock` and creates the project's `.venv` environment.
The project requires Python 3.14; uv downloads a compatible version automatically if one is missing, so the first run needs internet access. The version check should print `Python 3.14.x`.
Keep using `uv run python ...` for later runs; manual environment activation is unnecessary. On macOS/Linux, install uv using its installation page, then use the same three commands from the project root.

### Read the result and change one parameter

Example 01 connects a 10 V source across a 5 Ω resistor. The terminal should print the following summary, and both voltage and current plots should be horizontal lines:

```text
节点 n1 电压：10.000000 V（解析值 10.000000 V）
电阻 R1 电流：2.000000 A（解析值 2.000000 A）
电源 V1 支路电流：-2.000000 A（负号表示电源向外供电）
```

The script prints Chinese labels: these lines report node voltage, resistor current and source branch current, respectively.
Close the voltage window to see the current window; the terminal prompt returns after all figure windows close.
Ohm's law gives `I = V/R = 10/5 = 2 A`. Source current is positive into its positive terminal, so it is negative when the source delivers power.

Open `examples/01_r_circuit.py` in a text editor, change `RESISTANCE = 5.0` to `RESISTANCE = 10.0`, save it, and rerun the same command.
The voltage should remain 10 V, the resistor current should become 1 A, and the source current should become −1 A. Restore 5.0 before moving to the next example.

Dependencies are NumPy, SciPy and Matplotlib; tests use pytest. Run `uv run pytest` when you want to check installation or changed behavior.

If the default temporary directory raises `PermissionError` on Windows, rerun from the project root with a project-local temporary directory:

```powershell
New-Item -ItemType Directory -Force -Path .tmp | Out-Null
$env:UV_CACHE_DIR = "$PWD/.tmp/uv-cache"
$env:MPLBACKEND = "Agg"
uv run --locked pytest -o addopts= -q -p no:cacheprovider --basetemp=.tmp/pytest-local
```

Create `.tmp` explicitly so a fresh download has the parent directory required by `--basetemp`. Ensure no other test run uses the same `--basetemp`; pytest clears that directory. This distinguishes directory-permission failures from code failures. Existing automatic CI remains Linux-only; Windows CI is a future task.

Examples display figures by default without saving data or images.
For network cases, set `SAVE_RESULT_DATA` or `SAVE_RESULT_FIGURE` at the top of the script to `1` to save to `outputs/<case-name>/`.
The standalone PLL example 11 only displays figures and has no saving flags.
Noninteractive backends such as `MPLBACKEND=Agg` skip window display while retaining computation and saving.

If something goes wrong, check these points first:

| Symptom | Check and action |
|---|---|
| `uv` is not found | Reopen the terminal after installation and first confirm that `uv --version` works. |
| `pyproject.toml` or the example file is not found | Return to the folder containing both `pyproject.toml` and `examples`; do not run from inside the ZIP or the `examples` subfolder. |
| `ModuleNotFoundError: pycy_emt_lite` | Run `uv sync --locked` from the project root, then use `uv run python ...`. |
| The summary has printed but the terminal is still busy | Check for a figure window waiting to be closed; multiple figures appear in sequence. |
| No figure window appears | `MPLBACKEND=Agg` intentionally skips display. Set `SAVE_RESULT_FIGURE` to `1` in the relevant example if you need saved images. |

## 2. Learning order

Thirteen introductory scripts and one integrated example form nine units. Integrated average renewable/converter and HVDC/MMC candidates 13–16 were removed; retained commands keep their original numbers.
Complete 01 first, then study storage in 02 and 03 before moving to 04 and 17. Once you can explain these waveforms, use sections 1–5 of [Component derivations](docs/component_derivations.en.md) to check a complete RLC matrix. Leave machines, control and HVDC for later as needed.

| Unit | Scripts | What you can check after studying it |
|---|---|---|
| R and MNA | [01](examples/01_r_circuit.py) | Run the object workflow, predict current with Ohm's law and explain source-current direction; read about matrix assembly afterward. |
| Dynamic RLC | [02 RC](examples/02_rc_transient.py), [03 RL](examples/03_rl_transient.py), [04 RLC](examples/04_rlc_transient.py), [17 AC RLC](examples/17_single_phase_ac_rlc.py) | Check storage initial conditions and time constants, distinguish transients from steady-state phasors, and compare whole-waveform errors after reducing the time step. |
| Three-phase and faults | [05](examples/05_three_phase_steady_state.py), [06](examples/06_three_phase_short_circuit.py), [07](examples/07_single_phase_ground_fault.py) | Observe balanced RL, three-phase short circuits and single-phase grounding; compare faulted and healthy phases over fixed time windows. |
| Lines | [08](examples/08_pi_line_transient.py) | Distinguish Pi-line series current from terminal capacitor currents; optionally study segmented and Bergeron models next. |
| Transformers | [09](examples/09_single_phase_transformer.py) | Check the turns ratio and observe leakage and magnetization effects; see the model document for three-phase connections. |
| Synchronous machines | [10](examples/10_park_generator_avr_governor.py) | Start at equilibrium, observe voltage and speed after a load step, and distinguish the roles of the AVR and governor. |
| Discrete control | [11](examples/11_pll_dynamic_response.py) | Observe q-axis voltage and angular frequency in the standalone SRF-PLL loop and explain when it approaches lock. |
| PWM | [12](examples/12_two_level_pwm_generator.py) | Compare ideal-switch SPWM gates with RL current and distinguish switching ripple from the fundamental. |
| Integrated VSC-HVDC | [18](examples/18_three_terminal_vsc_hvdc.py) | Follow voltage and power after an AC fault through three two-level bridges, independent PLL/dq loops and a bipolar DC network. |

Try these exercises in the first four examples. Change one item at a time, save and rerun, then restore the original value. Each script also starts with connections, expected behavior and source locations.

| Example | Check with default parameters | Change and expected behavior |
|---|---|---|
| 01 resistor | 10 V and 5 Ω give 2 A | Change `RESISTANCE` from `5.0` to `10.0`: current becomes 1 A. |
| 02 RC | `R*C = 1 ms`; capacitor voltage starts at 0 V, reaches about 0.6321 V at 1 ms and 0.9933 V at 5 ms | Change `CAPACITANCE` from `1e-6` to `2e-6`: the time constant becomes 2 ms and charging is slower; the long-time limit remains 1 V. |
| 03 RL | `L/R = 1 ms`; inductor current starts at 0 A, reaches about 0.06321 A at 1 ms and 0.09933 A at 5 ms | Change `INDUCTANCE` from `10e-3` to `20e-3`: the time constant becomes 2 ms and current builds more slowly; the long-time limit remains 0.1 A. |
| 04 RLC | Capacitor voltage first exceeds 1 V, then oscillations decay toward 1 V | Change `RESISTANCE` from `20.0` to `40.0`: the first voltage peak is lower. At `100.0`, plots still appear and the summary says it skips the underdamped analytical comparison. |

The "long-time limit" is not necessarily reached when the script stops. After changing parameters, the existing simulation duration may cover only part of the transient.

Start with these code conventions:

| Notation | Meaning in this project |
|---|---|
| `import` / `from ... import ...` | Make a component or function available to the script. |
| `Resistor("R1", "n1", "0", 5.0)` | Create a resistor object named R1, connected between n1 and 0, with resistance 5 Ω. Identical node names mean a wire connection; `"0"` is reference ground. |
| `1e-6`, `10e-3` | Respectively 0.000001 and 0.01; component parameters use F, H and Ω, and time uses s. |
| `def define_case()` / `define_case()` | The first defines a function; the second calls it to create a fresh case. |
| `result: SimulationResult` / `-> None` | Type hints describe a parameter or return type; `-> None` means the function does not return a computed result. |
| `CaseDefinition` / `run_case(case)` | The first holds components and settings; the second creates the circuit, runs it and handles output. On a first reading, focus on component parameters and simulation settings. |
| `result.series("i:R1")[-1]` | Read all R1 current samples and select the last value; `result.series("time")` supplies the corresponding times. |
| MNA / `stamp()` | MNA is modified nodal analysis; `stamp()` writes each component's equations into a shared matrix. See Component derivations for details. |

Run `uv run python examples/18_three_terminal_vsc_hvdc.py` for the default FAST case (20 μs, 0.8 s).
Set `MODE` in that script to `FULL` (5 μs) or `BENCHMARK` (2 μs) for 2.5 s runs.
The [complete benchmark guide](docs/three_terminal_vsc_hvdc.en.md) gives source mapping, parameters, validation and model adjustments, including the fault-clearing RC snubber.

Example 17 uses a 220 V RMS, 50 Hz source in series with 20 Ω, 50 mH and 100 μF, with separate voltage/current figures.
Its default steady-state phasor window is 0.08–0.12 s; select a new window after changing frequency or damping.
Example 10 retains a fourth-order synchronous generator, starting at equilibrium and adding load at 0.2 s, with separate voltage/field, speed and power figures.
The classical synchronous machine also remains; the two models have different approximations. Example 11's `explicit_control` label describes its explicit control loop and is not an EMT integration-method option.

## 3. Write a case

Save the following as `my_r_circuit.py` in the project root (with the `.py` extension), then run `uv run python my_r_circuit.py`.
Parameters stay beside the components, and voltage/current use separate figures.

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
    config = SimulationConfig(time_step=1e-4, stop_time=1e-3, linear_solver_mode="rebuild")
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

Choose the network solve strategy before running through `linear_solver_mode`: the default `"rebuild"` performs a fresh LU factorization for every solve.
Change the configuration above to `"reuse"` to refactor only when the actual coefficient matrix changes; other solves reuse the previous LU.
Each step still assembles the matrix/right-hand side, updates states and performs numerical checks; changes in step size, parameters or machine states can also invalidate the LU.
The third option, `"precompute"`, factors matrices for a finite state family and every actual step size before the time loop, then solves by table lookup.
It currently supports fixed-parameter Resistor/Capacitor/Inductor, CurrentSource/VoltageSource, Fault/Breaker/IdealSwitch,
plus ThreePhaseSource, ThreePhaseLine and ThreePhaseTransformer without saturation; other composite models and machines are not admitted yet.
Binary states are enumerated automatically, up to 1024 states; `precompute_states` can instead declare the complete valid family.
Undeclared states, coefficient-matrix changes, singular matrices or exceeded limits raise errors; see [precomputation rules and example](docs/numerical_conventions.en.md#network-precompute).
The network strategy is independent of the BE/trapezoidal integration `method`. Precomputation adds startup cost and memory, and does not guarantee a speedup for every case.
The existing HVDC entry accepts a strategy, but full FAST precomputation raises because its actual h family exceeds the 1 GiB budget. Rebuild/reuse remain available; see [HVDC strategy scope](docs/three_terminal_vsc_hvdc.en.md#network-solver-scope).

## 4. Read, plot and save results

`result.columns` lists fields; `result.series("v:n1")` returns a NumPy array. Node voltage is `v:<node>` and ordinary branch current is `i:<component>`; see model descriptions for three-phase/composite fields.
Node voltages are relative to reference ground; current delivered by a voltage source is opposite to its branch-current direction.

Append the following code to the end of the same `my_r_circuit.py` file, then rerun the script. It uses `result` from the preceding code, explicitly saves JSON and reads it back for comparison:

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
                      summary={"Voltage RMS / V": voltage_rms}, figure_paths=["outputs/my_r_circuit/zoom.png"])
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
