# Three-Terminal Two-Level VSC-HVDC Integrated Example

[简体中文](three_terminal_vsc_hvdc.md) · [Running the project](../README.md) · [Example source](../examples/18_three_terminal_vsc_hvdc.py)

This example reproduces the reference benchmark's core three-terminal circuit and station duties using 18 ideal switches that actually stamp MNA.
It is a teaching reimplementation with documented provenance, **not a 1:1 cross-platform reproduction accepted through waveform comparisons**.
Controller gains, measurement filtering, startup, fault-clearing snubbers and numerical methods are adjusted as described below.
For model derivations, see [Component derivations](component_derivations.en.md): Section 9 explains transformer matrices; Sections 11–12 develop filters, dq control and six-switch bridge stamps; Sections 13–15 cover initialization, events and energy checks.

First complete Examples [05 three-phase network](../examples/05_three_phase_steady_state.py), [11 PLL](../examples/11_pll_dynamic_response.py) and [12 PWM](../examples/12_two_level_pwm_generator.py).
For a first run, read [Section 10's modes](#10-simulation-modes) and use the default FAST mode. Then follow [Section 6's topology](#6-final-topology) and [Section 7's control duties](#7-station-controls) through the source, and interpret results with [Section 12's validation](#12-validation). Sections 1–3 retain the reference sources and model mapping for provenance checks.

## 1. Reference Benchmark

The sole primary electrical reference is the **MATLAB-Simulink Three-Terminal Two-Level VSC-HVDC Benchmark** published by DIgSILENT.
The [official release page](https://www.digsilent.de/index.php/en/faq-reader-powerfactory/benchmark-of-a-three-terminal-vsc-hvdc-system-in-powerfactory.html)
provides the white paper and PSCAD/Simulink models. This example takes the published Simulink model as its primary reference; other HVDC examples are not mixed in as primary references.

Obtain the reference files from the official release page above. The table lists the inspected filenames and SHA-256 hashes to identify the versions used.
Inspection covered PDF pages 1–4, SLX component masks/wiring and the parameter script. The topology/control figures on PDF pages 2/3 were also inspected visually.

| File | SHA-256 |
|---|---|
| `Three_terminal_VSC_HVDC_MATLAB_Simulink.slx` | `25c643eb66cbe97842229d046c55fe32a6f71b7a6cc7bc1b6a5617d51cd76e92` |
| `Parameterisation_Three_terminal_VSC_HVDC_MATLAB_Simulink.m` | `bfe8c4b05de6feae1dc376bc4fbee1664018c6b9bbc57ea06a6381bdc6d6133d` |
| `HVDC-VSC-2L-Benchmark.pdf` | `4f12fc424fcd96475a181a73f16f3f3baec4ab93c4fd6c876c7e771a101cba43` |

Original files remain unchanged. R2022b runs used an independent copy of the reference model, running the parameter script before `Simulink.SimulationInput`.
The original 2 μs, 1980 Hz, 2.5 s configuration completed. An additional run enabled Scope logging and exported Vdc1/2/3 at 50 μs intervals.
R2022b warned that a converter Boolean comparison parameter of 0.5 was quantized to 1, so this run is not an unconditionally certified reference dataset either.

## 2. Benchmark Analysis

- The stations connect to grids rated 420 kV/60 Hz, 420 kV/50 Hz and 500 kV/50 Hz. Rated voltages are line-to-line RMS.
- All three converter transformers are 1500 MVA, 230 kV on the low-voltage side, Yg/Yn. Each LV neutral is grounded through 1 MΩ, not a Y/Δ connection.
- Each station has 72.4 mH phase reactors, grounded high-pass filters, a two-level bridge and split DC capacitors.
- Both DC+ and DC− use T-section RLC lines with branches 1–2 and 1–3; there is no direct 2–3 branch.
- VSC1 regulates Vdc/Vac. VSC2 absorbs 200 MW from AC; VSC3 delivers 200 MW to AC. Both power stations also regulate Vac.
- The original uses three independent PLLs, dq current loops, PI voltage loops and carrier PWM. The three-phase ground fault is at the VSC3 transformer HV side, from 1.5 to 1.65 s.

1500 MVA is the transformer nameplate rating. This example validates approximately ±200 MW operation, not full rated transfer capability.
The parameter script alone is insufficient: its legacy `Filter.Lf/Rf/Cf` fields do not set the current SLX high-pass filter block, which uses Qc, tuning frequency and quality factor.

## 3. Benchmark Mapping

| Reference Benchmark | PyCy-EMT Implementation |
|---|---|
| 2-level VSC switching devices | Six `IdealSwitch` instances per station, actually stamped into MNA; no controlled-voltage-source substitution |
| AC system with internal R/L | `ThreePhaseSource` + `ThreePhaseLine` |
| Converter transformer Yg/Yn | `ThreePhaseTransformer`, leakage lumped on the primary side, plus a neutral `Resistor` |
| Phase reactor | `ThreePhaseLine`, R=0 and L=72.4 mH/phase |
| Split DC capacitor | Two `Capacitor` instances per station, each 300 μF with 200 kV initial voltage |
| Bipolar T-type DC line | Two `Resistor`/`Inductor` sections per pole and a midpoint-to-ground `Capacitor` |
| Grounded high-pass filter | C in series with (L ∥ R) per phase, assembled from existing basic elements |
| Independent SRF-PLL | Three `SRFPLL` instances measuring their respective HV PCCs |
| abc/dq and inverse | `abc_to_dq` / `dq_to_abc`, amplitude invariant |
| PI controllers | `PIController`, existing integral-freezing anti-windup plus integral freezing for downstream limits |
| SPWM | `triangular_carrier` + `carrier_compare` + complementary gate callables |
| AC fault and clearing | Three `Fault` instances, `FaultApplyEvent` / `FaultClearEvent` and the existing `EventQueue` |
| Controller/network coupling | `CaseDefinition.on_step` → `Simulator.on_step`, a post-step callback at every solution point |

## 4. Implementation and Test Entry Points

| File | Purpose |
|---|---|
| [Example 18](../examples/18_three_terminal_vsc_hvdc.py) | Parameters, station wiring, bipolar lines, three-station assembly, fault, metrics and plots |
| [controls/vsc.py](../pycy_emt_lite/controls/vsc.py) | Shared station controller and configuration, with independent state per station |
| [System tests](../tests/test_three_terminal_vsc_hvdc.py) | Single-station open/closed loop, two stations, three-station FAST, PWM, port power and discrete DC energy |
| [Callback tests](../tests/test_step_callback.py) | Initialization/event sampling order, next-step actuation, read-only input and result decimation |
| This guide and its Chinese companion | Parameter provenance, control derivation, execution and validation boundaries |

Circuit stepping uses the existing `Circuit/Simulator`; see [Numerical conventions](numerical_conventions.en.md#time-grid) for post-step callback timing.

## 5. Shared Solver and Result Interfaces

`core/simulation.py` provides an optional post-step callback and result decimation; `cases.py` passes the case's callback to the simulator.
`io/results.py` uses ordered dictionary deduplication for column names, avoiding repeated linear membership searches for hundreds of fields while preserving first-occurrence order and later new columns.
NPZ reading now loads each column from the archive once before assembling rows. Repeatedly loading entire columns for each row did not scale to this example.
A 1001-row, 21-column readback decreased from approximately 0.646 s to 0.00374 s with identical data; the complete compressed 50001-row, 377-column result took approximately 2.46 s to read.
See the [source reading table in Numerical conventions](numerical_conventions.en.md#source-route) for file responsibilities and specific function entry points.

Fault application exposed an initialization check false positive near a high-voltage zero crossing. A four-element reproducer was added to the
[basic tests](../tests/test_basic_components.py): a 1 nV source, two 1 Ω resistors and a capacitor precharged to 200 kV.
Approximately 10 pV of LU cancellation error can exceed the original absolute tolerance of the near-zero source constraint.
Only when the original consistency check fails, the solver now performs one correction `A δx=b−Ax` and rechecks against the **original thresholds**. Initialization tolerances are not relaxed and impulses are not permitted.

## 6. Final Topology

```text
Grid1 420 kV/60 Hz -- Rg,Lg -- HV1 -- Yg/Yn T1 -- LV1 -- Lphase1 -- 6 switches VSC1
Grid2 420 kV/50 Hz -- Rg,Lg -- HV2 -- Yg/Yn T2 -- LV2 -- Lphase2 -- 6 switches VSC2
Grid3 500 kV/50 Hz -- Rg,Lg -- HV3 -- Yg/Yn T3 -- LV3 -- Lphase3 -- 6 switches VSC3
                                |               |
                       S3 three-phase fault     C -- (L || R) -- ground [each station]
                       and finite RC snubber

DC+1 -- R,L -- Cmid-to-ground -- R,L -- DC+2
  |
  +---- R,L -- Cmid-to-ground -- R,L -- DC+3
DC-1 -- R,L -- Cmid-to-ground -- R,L -- DC-2
  |
  +---- R,L -- Cmid-to-ground -- R,L -- DC-3

Each station: DC+ -- 300 uF -- ground -- 300 uF -- DC-
Each transformer: LV neutral -- 1 Mohm -- ground
Each S1/S2/S3 HV phase -- 1 Mohm -- ground
```

Cmid is a shunt capacitor from the line midpoint to ground, not a series element in the DC path.
Upper/lower bridge switches connect to DC+/DC−. Independent DC voltage sources are used only in intermediate single-station validation; none exist in the final three-station network.

## 7. Station Controls

| Station | Reference duty → implementation | Positive direction |
|---|---|---|
| S1 / VSC1 | Vdc + Vac → DC voltage PI supplies Id*, AC voltage PI supplies Iq* | Covers system losses/transients; P can have either sign |
| S2 / VSC2 | P + Vac → `Id*=P*/(1.5 Vd)`, Vac PI supplies Iq* | P*=+200 MW, AC → converter |
| S3 / VSC3 | P + Vac → same structure | P*=−200 MW, converter → AC |

At every station, `Pac>0` means AC → converter, measured at the AC end of the phase reactor.
`Q>0` means inductive reactive power absorbed from AC; `Pdc>0` means converter → DC network.
Thus the steady DC balance is `ΣPdc=line resistance losses`; transients also include changes in capacitor/inductor storage.
Reactor AC-end power and bridge AC-end power differ by reactor storage power. Their difference cannot be called semiconductor loss.

## 8. Control Architecture

The implemented transform is `d=α cosθ+β sinθ`, `q=−α sinθ+β cosθ`, with positively rotating θ and d aligned with the voltage space vector.
For an a-phase sine source, the ideal initial space angle is −π/2, not 0. The inverse is exact when zero sequence is absent.

```text
P = va ia + vb ib + vc ic
P = 1.5 (vd id + vq iq)             [zero sequence absent]
Q = 1.5 (vq id - vd iq)
L did/dt = vg_d - vc_d + omega L iq
L diq/dt = vg_q - vc_q - omega L id
vc_d* = vg_d + omega L iq - PI(Id* - Id)
vc_q* = vg_q - omega L id - PI(Iq* - Iq)
```

Feedforward uses the measured LV reactor-end voltage; PLL/Vac use the station HV PCC. The current-loop model includes only the phase reactor; transformer leakage is already represented separately in the network.
P retains actual abc zero-sequence power; dq control adds no zero-sequence regulator.
After dq→abc, voltage commands are normalized by measured Vdc/2 and compared with a triangular carrier. Lower gates are logical complements of upper gates.
Rated no-load modulation is `2 sqrt(2/3)×230/400≈0.939`; the controller limits the dq voltage vector to m≤0.98.

Each independent PLL uses the existing normalized Vq input and PI. Its absolute angular-frequency limits are nominal ±10 Hz, converted to rad/s.
LV dq voltage, Vac and Vdc use 1 ms first-order low-pass filters; dq current uses 0.2 ms filters.
All three modes update PLLs and inner/outer loops at every EMT solution point, with PWM sampled on the same grid. There is no hidden multirate scheduler.

Callback order: integrate/solve → update components → apply explicit events and solve consistent right-side values → form a read-only measurement row → call control once → store selected results.
At t=0, the callback observes/initializes without a zero-interval PI/PLL call. Positive times use actual sampling intervals.
Updated modulation acts only on the next network step, without an algebraic control loop. Event left/right solves do not advance controllers twice.
`m{a,b,c}` records held values used by the completed solve; `m{a,b,c}_next` records newly generated commands.

DC station and line-midpoint capacitors are precharged to rated pole voltages. AC filter/RC capacitors use rated sinusoidal initial voltages; all inductor currents start at zero.
This is precharged startup, **not full power-flow steady-state initialization**. P commands ramp linearly from 0.02 to 0.12 s; startup transients remain in the results.
If the initial PCC magnitude is sufficient, the PLL starts from its measured space angle; otherwise it retains the rated sine-source space-angle prior. Subsequent synchronization is closed-loop from local voltage.

## 9. Main Parameters

| Parameter | Value | Source |
|---|---|---|
| Station HV voltages/frequencies | 420/420/500 kV; 60/50/50 Hz | Reference Benchmark: script, SLX and PDF |
| Transformer rating/LV voltage | 1500 MVA / 230 kV | Reference Benchmark |
| Source impedance | 4.59 Ω; L=26.04/(2πf) H/phase | Reference Benchmark |
| Transformer leakage | R=0; total X=0.10 pu; L=0.10 VHV²/(Sbase 2πf) | Reference: 0.05 pu per winding, lumped on the primary side |
| Phase reactor | 72.4 mH/phase, R=0 | Reference Benchmark |
| DC voltage/capacitance | ±200 kV; 300 μF per pole per station | Reference Benchmark; pole-to-pole equivalent is 150 μF |
| DC line half section per pole | R=7 Ω, L=0.596 H; midpoint C=26 μF to ground | Reference SLX wiring and script; full pole R=14 Ω and L=1.192 H |
| LV high-pass filter | Qc=75 Mvar, fr=450 Hz, q=0.08, grounded Y | Reference SLX, not legacy filter script values |
| Filter element conversion | `C=Qc[1−(f/fr)²]/(2πf VLL²)`, `L=1/[(2πfr)² C]`, `R=q√(L/C)` | Second-order high-pass equivalent formulas; not calibrated element by element against SPS internals |
| Switches | Ron=0.005 Ω, Goff=1 μS | Reference on/off resistance; bidirectional conductance is a simplification |
| PLL Kp/Ki | 80 / 1000 | PyCy-adjusted; not a direct conversion of script Ti |
| Current PI Kp/Ki | 60 V/A / 6000 V/(A·s) | PyCy-adjusted |
| Vdc PI Kp/Ki | 0.05 A/V / 1.1 A/(V·s) | PyCy-adjusted |
| Vac PI Kp/Ki | 10000 A/pu / 400000 A/(pu·s) | PyCy-adjusted for explicit feedback and short FAST startup |
| Reference current vector/modulation limits | 1500 A / 0.98 | PyCy-adjusted; d priority, Iq uses remaining circular headroom |
| Fault Ron/original snubber R | 5 Ω / 1 MΩ | Reference SLX |
| Additional S3 HV series RC | R=200 Ω, C=0.5 μF/phase | PyCy-adjusted finite fault-clearing snubber; not a reference parameter |

The original script uses kV, kA, MW and custom Ti expressions; its gain values were not copied mechanically.
See the [official MathWorks model description](https://www.mathworks.com/help/sps/ref/passiveharmonicfilterthreephase.html) for the high-pass filter structure.

## 10. Simulation Modes

```bash
uv run python examples/18_three_terminal_vsc_hvdc.py
```

Set `MODE` at the top of the script, or call `define_case("FULL")` in Python and pass the case to the existing `run_case()`.

<a id="network-solver-scope"></a>

The network strategy is independent of MODE. This example has 18 bridge switches and **only allows `"rebuild"` or `"reuse"`**. The top-level `LINEAR_SOLVER_MODE` defaults to `"rebuild"`; alternatively call
`define_case("FAST", linear_solver_mode="reuse")` to reuse the previous LU through the existing run_case/Simulator path.
It invalidates by exact equality of the complete actual A, preserving step sizes, source/gate/control calls and initial/event ordering.

**Networks with many switching devices do not use precomputation.** `define_case(..., linear_solver_mode="precompute")` raises before constructing controllers or the network.
This restriction applies to FAST/FULL/BENCHMARK, runs without faults and subsequent shortening of the simulation. This example no longer generates or stores a complete switching-state matrix family.
Small finite-state networks can still use precompute through the generic Simulator; see [precomputation rules](numerical_conventions.en.md#network-precompute).

The earlier N3 review covered 1024 states from nine complementary gate pairs and synchronous faults. Its 15 distinct positive h values required 16384 matrices and about 4.29 GiB for A/LU/pivots, exceeding the 1 GiB budget.
That review and the old t=0/first-two-interval evidence remain in [plan section 7.18](audit_20261005/项目问题与改进计划.md#network-solver-n3); they do not enable current HVDC precomputation.
[Section 7.19](audit_20261005/项目问题与改进计划.md#network-solver-scope-update) updates the current scope. Step-size normalization and budget expansion will no longer be pursued for HVDC precomputation.
N4 completed three interleaved measurements per rebuild/reuse strategy for both the default and three-format/image-saving workflows. Independently captured result fields and 43 control telemetry columns match R9 exactly; the order, times and states of 720054 gate calls also match between strategies.
Reuse reduces the LU count by about 31.45%, but neither complete workflow established a stable overall speedup. Median complete-workflow peak working sets were about 0.75%/0.43% lower on this machine, without a guarantee across scenarios. The default remains rebuild; see [section 7.20 for costs and scope](audit_20261005/项目问题与改进计划.md#network-solver-n4).
Small networks separately compare all three strategies, including preparation costs. No additional full-run acceptance was performed for FULL/BENCHMARK. This stage only measured costs and updated existing documents; other optimizations remain deferred.

| Mode | EMT step | PWM | Duration | Fault application/clearing | Recorded interval |
|---|---|---|---|---|---|
| FAST (default) | 20 μs | 1000 Hz | 0.8 s | 0.30 / 0.45 s | 20 μs |
| FULL | 5 μs | 1980 Hz | 2.5 s | 1.50 / 1.65 s | 50 μs |
| BENCHMARK | 2 μs | 1980 Hz | 2.5 s | 1.50 / 1.65 s | 50 μs |

All modes use existing backward-Euler MNA, without automatic location of continuous-time PWM crossings.
FULL/BENCHMARK use `record_every=10/25` to limit memory. Control and network operations still run at every step; initial, event and final points are always saved.
`result.time_step` is the EMT step. Metrics must use the actual `time` column, not mistake the stored interval for the integration step.
50 μs output supports low-frequency dynamics and coarse PWM inspection, not precise edge timing or harmonic-amplitude acceptance. Set `record_every=1` and shorten the run when such detail is needed.
Backward Euler dissipates switching-ripple energy, particularly in FAST; AC power differences cannot establish real conversion efficiency.

FAST uses a larger step for quick teaching runs and development regression: check finite operation, basic operating points, conservation, faults and gates, without requiring particularly high instantaneous waveform accuracy. FULL/BENCHMARK also change PWM and timing along with the step. Mode names do not replace accuracy validation with the same PWM/physical parameters and explicit windows and metrics.

The default displays figures without saving. The two top-level saving flags enable CSV/JSON/NPZ and figures under `outputs/three_terminal_vsc_hvdc_<mode>/`.
NPZ is preferable for large data. Enabling data saving in standard `run_case()` still writes all three formats by project convention, which can consume substantial disk space.

## 11. Fault Case

Each phase of the S3 transformer HV PCC is grounded through 5 Ω for 150 ms. FULL/BENCHMARK use the original event times.
FAST moves application to 0.30 s while retaining 150 ms duration. Timing comes from white-paper page 4 and the parameter script.
Every HV phase of every station has a 1 MΩ ground branch, including the original S3 fault-block snubbers. S1/S2 ground branches are also part of the actual topology and must not be omitted or treated as appearing only when a fault is applied.

With strictly continuous inductor currents, the original purely resistive snubber arrangement produces an approximately 14 GV algebraic spike at clearing: pre-clearing fault current must immediately transfer to the 1 MΩ path.
An independent finite series RC snubber is added to each S3 phase to provide an energy-storage path for commutation.
This changes prefault reactive power and clearing transients; the clearing waveform cannot be claimed equivalent to the original model.
FAST still produces an approximately 3.13 MV short HV-side peak. This is a result of the declared simplified circuit, not evidence for interruption overvoltage or insulation coordination.
There are no surge arresters, arcs, natural-current-zero interruption, protection settings or VSC blocking models.

## 12. Validation

Each station records Vdc, P/Q, Vac, Id/Iq and references, PLL angle/frequency/Vq, and current/next modulation. All 18 gate states and branch currents come from the actual network.
The example also records every half-section current of both bipolar DC lines, station Pdc, split-capacitor energy, and total DC storage/loss/power residual.
Default figures cover station DC voltage, P/Q, Vac, station Id/Iq tracking, PLL frequency, fault phase voltage/current, DC current and PWM over 0.2–0.203 s.

Metric windows are FAST 0.18–0.28 s / 0.70–0.80 s and FULL/BENCHMARK 1.38–1.48 s / 2.40–2.50 s.
Each 0.1 s window contains six 60 Hz cycles and five 50 Hz cycles and does not cross explicit fault events.
Pre/post windows report time-weighted means. Current error is `|mean(I)−mean(I*)|`, **not instantaneous ripple RMS tracking error**.
When pre/post boundaries fall between samples, piecewise-linear endpoint interpolation precedes integration over the full declared
window; results must cover both endpoints. `fault:S3:Vac_pu_mean` retains the arithmetic sample mean from 20 ms after application to
20 ms before clearing. With nonuniform sampling it is not a time-weighted mean; a window with no samples raises an explicit error.
Means measure bias only. The current summary also reports frequency-error/Vq/dq-error RMS of piecewise-linear signals, minimum Vd, and `control_accuracy_met`. This flag requires frequency-error RMS<0.05 Hz, Vq RMS<0.01 pu, Id/Iq-error RMS<25 A and Vd>0; cancellation in signed means cannot establish accuracy. `PLL_Vq_pu` now uses the same `Vq/max(|Vd|,|Vq|,1 V)` normalization as the internal PI.

For FAST's quick-regression purpose, the strict RMS limits above remain diagnostic references: **`control_accuracy_met=0` does not mean FAST basic regression failed**. Existing tests separately check finite values/voltage ranges, mean bias and operating points, bridge/DC conservation, faults and PWM gates; this flag is not a required FAST pass condition. Actual RMS values, existing fields and synthetic bad-waveform negative cases remain. Limits and gains are not changed to make the flag 1. See the [R12 scope update](audit_20261005/项目问题与改进计划.md#fast-regression-scope).

The current-code revalidation on 2026-10-05/06 uses default PLL gains Kp=80, Ki=1000 and the FAST 20 µs step. The table gives ranges across the three stations, combining Id/Iq. All Vd minima are positive and all six station/window strict observation flags are 0; existing FAST basic regression checks passed. **These results do not establish fine control-waveform accuracy.**

| Piecewise-linear RMS of instantaneous error | Prefault | Recovery window | Strict diagnostic reference (not a FAST gate) |
|---|---:|---:|---:|
| Frequency error / Hz | 0.336–0.445 | 0.331–0.460 | <0.05 |
| PLL Vq / pu | 0.02641–0.03495 | 0.02613–0.03613 | <0.01 |
| Id/Iq tracking / A | 148.4–170.7 | 147.9–171.6 | <25 |

The follow-up investigation explains errors and the candidate experiment without replacing default results. Detailed equations, station values and original evidence are kept in the consolidated document:

| Record (2026-10-06) | Conclusion and evidence scope |
|---|---|
| [R7 independent checks](audit_20261005/项目问题与改进计划.md#r7-control-diagnosis) | The 24 RMS values differ from existing summaries by at most 2.59e-12 in their original units. Projection, P/Q, PLL/PI, filtering, modulation and 18 gates passed checks; no new implementation defect was confirmed. Ideal balanced PCC offline frequency error is around 1e-12 Hz; offline input comparisons do not establish closed-loop current accuracy. |
| [R8 experiment design](audit_20261005/项目问题与改进计划.md#r8-accuracy-design) | Original strict RMS, low-frequency tracking, PWM ripple and external frequency estimates have separate definitions with unchanged limits. Filter and scalar current-loop derivations guide design, not proof of three-station stability with PWM/network coupling. |
| [R9 isolated experiment](audit_20261005/项目问题与改进计划.md#r9-pll-experiment) | Four Kp=80/40, 20/10 µs runs fix 1000 Hz PWM, 0–0.8 s and 0.3/0.45 s events. The 20 µs baseline arrays equal R7 exactly. Candidate high-frequency frequency-error ratios are 0.4923–0.5176 / 0.4988–0.5018, but raw frequency error remains 0.1562–0.2315 Hz and dq error 143.0–171.4 A; all 24 strict flags across four runs are 0. |
| [R10 offline review](audit_20261005/项目问题与改进计划.md#r10-rejection-review) | There are 24 cross-gain PLL replays; the 12 own-input/original-gain frequency traces match within 7.11e-15 Hz. For S3 recovery with fixed inputs, high-frequency frequency-error ratios are 0.49984–0.50018, while low-frequency frequency-error/Vq ratios are 1.940–3.181 / 1.267–1.349. The gain change alone can produce this low-frequency regression. |

Bands and smoothed signals are diagnostic measures. The R7 DFT uses 5000 samples per window, 10 Hz spacing and no taper, with ≥500 Hz as a diagnostic boundary; sampled mean square does not replace piecewise-linear RMS. Default filtered current feedback, 1 ms cycle averages and S1 low-frequency Iq still exceed some strict references; spectra and values are in R7/R8. These references are not current mandatory FAST accuracy requirements. Removing ripple or substituting smoothed signals does not establish fine waveform accuracy.

**The Kp=40 candidate was rejected; defaults remain 80/1000.** In R9, S3 recovery low-frequency frequency error increases to 2.220/2.423 times baseline. Sampled clearing-current peaks at 20 µs/S1 and 10 µs/S2 increase by 7.884%/5.765%, exceeding the planned 5% ceiling. All 24 existing integration-check invocations and independent control/integration checks passed, establishing only their respective safeguards. A 10 µs step refines both electrical integration and control sampling; two resolutions do not prove continuous physical accuracy or convergence order.

Baseline/candidate clearing peaks occur at different phases and times. R10 checked control timing, reactor voltage drops and network states at matched points; modulation vector saturation did not occur at the listed points. The records support a network-coupling explanation without uniquely identifying the link responsible for regression or ruling out earlier saturation. Offline PLL replay does not regenerate network currents, and RMS ratios cannot be added to partition causal contributions. Investigation and documentation closeout are complete; current status and separate future plans are in the [consolidated document](audit_20261005/项目问题与改进计划.md#delivery-status).

The following FAST/FULL/BENCHMARK tables, timings and cross-model comparisons preserve historical records. Their producing commits, complete Python/numerical-library environments and commands are not fully bound and remain unverified. The current correction/investigation stages reran only FAST, not FULL/BENCHMARK; R11 edits documentation only. Historical means do not establish current RMS accuracy or equivalence to the commercial model.

Historical FAST results (20 μs, 1000 Hz):

| Metric | Prefault | Recovery window |
|---|---:|---:|
| S1 Vdc / kV | 399.401 | 399.995 |
| S2 P / MW | 198.961 | 198.223 |
| S3 P / MW | −203.870 | −204.457 |
| Maximum station mean PLL frequency error / Hz | 0.00105 | 0.00478 |
| Maximum station dq mean tracking error / A | 5.28 | 3.63 |
| DC storage power / MW | 2.865 | 0.121 |

All results are finite. Whole-run Vdc spans 338.748–475.492 kV; mid-fault mean S3 Vac is approximately 0.18783 pu.
Maximum instantaneous DC power-balance residual is approximately 0.0273 W. FAST has 131 MNA unknowns and took approximately 29.9 s for simulation alone, excluding large-file saving/plotting.
These are individual local measurements, not cross-hardware performance promises.

The original historical record states that FULL and BENCHMARK completed and passed finite-value checks, Vdc/P/Vac/PLL/dq mean thresholds and DC-power thresholds.
Each stores 50001 rows and 377 columns; the network still has 131 unknowns.

| Metric | FULL prefault | FULL recovery | BENCHMARK prefault | BENCHMARK recovery |
|---|---:|---:|---:|---:|
| S1 Vdc / kV | 399.984 | 400.005 | 399.995 | 400.014 |
| S2 P / MW | 200.171 | 200.072 | 200.078 | 200.147 |
| S3 P / MW | −202.354 | −202.314 | −202.335 | −202.392 |
| Maximum station mean PLL frequency error / Hz | 0.000322 | 0.000955 | 0.000205 | 0.000357 |
| Maximum station dq mean tracking error / A | 0.753 | 0.664 | 0.152 | 0.226 |
| DC storage power / MW | 0.261 | 0.624 | 0.242 | 0.788 |

FULL/BENCHMARK simulation alone took approximately 328.9/800.9 s, with maximum DC power residuals of 0.03212/0.03250 W.
Mid-fault S3 Vac is approximately 0.188 pu in both. Whole-run Vdc spans 334.860–486.098 / 334.999–488.213 kV.
On the stored 50 μs grid, S3 HV peaks are 3.186/3.198 MV and phase-reactor current peaks are 7.366/7.434 kA.
These peaks confirm that limiting references does not limit actual fault current; peaks between recorded points may be larger.

The same-PWM, same-parameter 5/2 μs comparison uses corresponding 50 μs output points, with pointwise
`RMSE=sqrt(mean((V5us−V2us)^2))` and `NRMSE=100×RMSE/400000 V`.

| Window / s | S1 RMSE / V | S2 RMSE / V | S3 RMSE / V | Maximum station NRMSE / % |
|---|---:|---:|---:|---:|
| 1.38–1.48 | 138.712 | 263.552 | 229.147 | 0.06589 |
| 1.50–1.80 | 213.064 | 315.928 | 1083.627 | 0.27091 |
| 2.40–2.50 | 155.390 | 310.710 | 159.462 | 0.07768 |

Each window includes both endpoints, with 2001/6001/2001 samples respectively. This is a step-sensitivity check, not proof of a PWM waveform convergence order.
For example, prefault S1 Pac means are 25.684/21.092 MW in FULL/BENCHMARK and remain sensitive to switching ripple and numerical dissipation.
Similar Vdc does not establish converged physical losses from AC power differences.

BENCHMARK was also compared with original Simulink Vdc exported from the isolated copy on the same grid.
Over 1.50–1.80 s, S1/S2/S3 RMSE is 10.464/11.747/48.686 kV, or 2.616/2.937/12.171% of 400 kV.
This directly shows substantial cross-model fault differences; exact-reproduction acceptance has not been achieved.
The values above record completed validation runs. Raw simulation results are not distributed through Git; see Section 10 for execution and result-saving instructions.
The two compressed NPZ datasets used for validation follow the project schema and can be read by `SimulationResult.from_npz()`, including EMT step, method and event logs.

Power checks independently verify the bridge-port identity `Pac_bridge=Pdc+ΣGsw Vsw²` and the backward-Euler DC energy identity:

```text
E[k] - E[k-1] = h (sum(Pdc[k]) - sum(R i[k]^2))
               - 0.5 sum(C (v[k]-v[k-1])^2)
               - 0.5 sum(L (i[k]-i[k-1])^2)
```

The last two terms are numerical dissipation, not device conduction/switching losses. Intervals crossing events are excluded from this integration check because only right-side values are stored; event states and KCL are checked separately.
R2022b original-model prefault mean Vdc values were approximately 399.987/413.507/385.358 kV, useful for checking voltage levels and power-flow directions. Given the stated differences, similar means alone do not establish cross-platform acceptance.

## 13. Tests

```bash
uv run pytest tests/test_step_callback.py tests/test_three_terminal_vsc_hvdc.py
uv run pytest
```

For Windows, follow the [README test instructions](../README.md) for the locked environment, creating the .tmp parent directory and project-local basetemp before running tests for the first time.

Validation stages are: single-station open-loop switching/port power → independent PLL disturbance recovery and dq tracking → same-PWM mean-power comparison at 20/10 μs → two-station exchange/Vdc regulation → three-station FAST → fault/recovery.
Single-station validation may use a constant DC source. The final three-station test explicitly checks 18 switches, three transformers and a dynamic DC network.
A shared FAST fixture avoids repeating the full system run for each metric.

Key FAST basic-regression thresholds are mean PLL frequency error <0.05 Hz, mean Vq <0.01 pu, S1 mean Vdc error <1%, mean P2/P3 error <5%, mean Vac error <2%, mean dq error <25 A and DC power residual <1 W. They measure basic operation and mean bias; the strict RMS in Section 12 is observational and has a different meaning.
Gate/carrier agreement, bridge-node KCL, conduction loss, discrete DC energy and fault-resistor currents are checked independently.
Historical acceptance records report 681 full-regression tests, 14 headless examples and 7 I/O/plotting tests after the NPZ-reading change passed, with both 50001×377 result sets read back in the standard format. Producing-version/environment/command limitations are in Section 12; these are not current rerun results.
On 2026-10-05, the R5 main environment (CPython3.14.6) and R6 clean copy (CPython3.14.2) each completed 832 full-regression tests and 14 default examples; see the [R5 record](audit_20261005/项目问题与改进计划.md#r5-follow-up) and [R6 record](audit_20261005/项目问题与改进计划.md#r6-delivery). Existing tests and limits are retained; R11 only checks documentation without rerunning the full suite. These are the respective local records, not remote CI evidence or proof that the strict control-accuracy limits in Section 12 are met.

## 14. Deviations From Reference Benchmark

| Item | Difference and effect |
|---|---|
| Semiconductors | Bidirectional Ron/Goff switches, no independent antiparallel diodes; blocked-state rectification paths are not reproduced |
| Transformers | Yg/Yn, ratio, grounding and total leakage retained; 1e10 pu magnetizing branches and shared cores omitted |
| DC network | Bipolar lumped T-section RLC retained; midpoint capacitors precharged, unlike original zero-state startup |
| Control | Station duties/PLL/dq/SPWM retained; reselected SI gains, measurement low-pass filters and integral-freezing anti-windup rather than original back-calculation |
| Modulation/current limiting | m≤0.98 and a current-reference vector limit; original limits, initialization and device details differ |
| Fault clearing | Added S3 series 200 Ω/0.5 μF RC snubbers change reactive power and clearing transients |
| Solution | Backward Euler, explicit post-step control and grid-sampled gates; original Simulink uses ode4 plus an SPS discrete network |
| FAST | Larger step, lower PWM, shorter run and earlier fault; intended for development regression |

## 15. Remaining Limitations

The model is a **Two-level VSC modeled using ideal switching devices**, not a complete device-level IGBT model.
It omits dead time, independent diode reverse recovery, semiconductor switching loss, temperature rise, saturated magnetization, broadband/frequency-dependent DC cables, negative-sequence control and weak-grid stability validation.
Ron/Goff produce resistance losses; backward Euler produces separate numerical dissipation. These must not be combined as device losses.
The 1500 A limit applies to Id/Iq **references**; actual current is not clipped at 1500 A and can exceed it during faults.
There are no synchronous machines, AVR, governor, generator-side lines, MMC, DC faults/breakers, complex protection or grid-forming control.
Fault recovery, conservation checks and finer-step comparisons support this specific teaching example, not physical validation of every operating condition.
