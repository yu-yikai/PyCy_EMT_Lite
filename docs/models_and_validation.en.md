# Models and Validation

[简体中文](models_and_validation.md) · [Running the project](../README.md) · [Numerical conventions](numerical_conventions.en.md)

The retained scope is small linear networks, explicit switches, control blocks and two teaching machine models. Evidence below
refers to the implemented equations. Successful execution, parameter checks and verified physical relationships are distinguished.
See [Component derivations](component_derivations.en.md) for how physical relations become discrete equations, MNA stamps and history updates. It covers basic elements, three-phase networks, lines, transformers, machines, filters and control, with source and test links; this document continues to maintain parameters and validation scope.

## 1. Validated scope

Local validation record (2026-09-14, including the integrated three-terminal VSC-HVDC example): 681 tests passed and all 14 examples ran headlessly without default output files.
The integrated example's modes, results and deviations are in its [dedicated guide](three_terminal_vsc_hvdc.en.md).
This is local evidence, not remote CI status. No full-model comparison with experimental data or commercial EMT software is claimed.

| Scope | Existing evidence | Boundary and test entry point |
|---|---|---|
| R, RC, RL, RLC | Analytic initialization/transients, AC phasors, KCL/KVL, lossless LC energy, common-time convergence | Stated linear lumped circuits; [basic tests](../tests/test_basic_components.py) |
| Time, initialization, explicit events | Integer-step stop, three event policies, consistent left/right states, same-time order and endpoint events | Callable jumps are not automatically located; [time](../tests/test_time_grid.py), [events](../tests/test_events.py) |
| Three-phase R–L and faults (05–07) | Balanced phasors, piecewise analytic RL transient, single-phase grounding resistor dividers, fixed-window RMS/P/Q | Independent phase networks; [three-phase tests](../tests/test_three_phase.py) |
| Single-phase Pi and segmented lines | Phasor/two-port references, KCL, energy, time or spatial convergence | No broadband or phase coupling; [line tests](../tests/test_line_models.py) |
| Single/three-phase Bergeron | Integer delay, no pre-arrival response, matched transmission, open/short reflection, event right-side history | Fixed grid, independent phases; same line tests |
| Linear single/three-phase transformers | Phasors, analytic startup, connection phase shifts, port work/storage, flux consistency, time convergence | Four stated connections, no shared-core coupling; [transformer tests](../tests/test_transformers.py) |
| Two machines and example 10 | Port equations, power direction, equilibrium, independent continuous ODEs, first-order mechanical convergence | Stated approximations; [classical](../tests/test_synchronous_machine.py), [Park](../tests/test_park_synchronous_generator.py) |
| L/LC/LCL filters | Parameter rejection, wiring, independent ODEs, KCL, discrete energy and step convergence | Passive linear networks; [power-electronic tests](../tests/test_power_electronics.py) |
| PWM example 12 | Gates, floating star point, fundamental RL reference, finer-grid comparison | Fine grids are not device references; no automatic edge location; same power-electronic tests |
| Three-terminal two-level VSC-HVDC example 18 | Single-station open/closed loop, two stations, three-station FAST fault recovery, PLL/dq/P/Vdc/Vac, bridge port power and discrete DC energy | Teaching reimplementation with RC snubber and control adjustments; [system tests](../tests/test_three_terminal_vsc_hvdc.py), [post-step callback and recording](../tests/test_step_callback.py) |
| `ThreePhasePiLine`, `ThreePhaseParallelRLCLoad` | Initialization/first step and output fields; nominal-power conversion for the parallel load | Local checks, no complete independent three-phase AC/fault validation; three-phase/line tests |
| Control blocks and SRF-PLL | Basic functions, sample-time consistency, preserved initial lock, independent balanced-input ODE and first-order convergence | Functional and specific balanced-condition checks, no closed-loop grid/weak-grid engineering validation; [control tests](../tests/test_controls.py) |
| Saturation approximation | Parameter and linear flux/current regressions | **No independent saturation-curve, energy or inrush validation**; linear checks cannot replace it |

Metrics, I/O, plotting and linear solves have separate [metric](../tests/test_analysis.py), [I/O](../tests/test_results_io.py),
[plot/report](../tests/test_visualization_reporting.py) and [solver](../tests/test_solvers.py) regressions. These verify utility behavior,
not unvalidated physical models. The existing [CI configuration](../.github/workflows/ci.yml) retains locked installation, tests,
examples, build and import outside the source tree; no second execution workflow is needed.

## 2. Basic circuits and single-phase AC RLC

Source and R/L/C directions and stamps are in the numerical document. DC-step analytic references are
`vC(t)=Vs+(vC0−Vs)exp(−t/RC)` and `iL(t)=Vs/R+(iL0−Vs/R)exp(−Rt/L)`.
Series RLC satisfies `L di/dt=vs−Ri−vC`, `C dvC/dt=i`; steady-state phasors cannot replace startup analysis.
Lossless LC energy is `(Li²+CvC²)/2`. Tests check declared initial values and the entire transient, so endpoint agreement cannot hide a first-step error.

[Example 17](../examples/17_single_phase_ac_rlc.py) uses a 220 V RMS, 50 Hz source in series with R=20 Ω, L=50 mH and C=100 μF.
A sinusoidal source needs peak amplitude `sqrt(2)*Vrms`; 220 is not its peak. The steady-state reference is:

```text
Z = R + j(ωL − 1/(ωC))
I = Vrms / Z
VL = jωL I, VC = I/(jωC), VR = R I
```

Current/voltage RMS, phase and KVL are checked over two cycles at 0.08–0.12 s. Voltage and current are plotted separately, without
saving by default. After changing amplitude, frequency or R/L/C, reconsider the steady-state window and fastest time scale.
The detailed case template and saving instructions are maintained only in the README.

## 3. Three-phase networks and faults

`ThreePhaseSource` constructs abc positive-sequence sinusoids from `phase_rms` (V), `frequency` (Hz) and phase angle,
with default offsets 0/−120/+120°. Balanced Y line-voltage RMS is √3 times phase-voltage RMS; do not interchange the ratings.
`ThreePhaseLine` comprises three independent series R–L branches; `ThreePhaseLoad` is a star load with a series R–L branch from
each phase to `neutral`. Resistance uses Ω and inductance H. Zero inductance omits the inductor; construction checks specific
zero-impedance combinations. There is no mutual inductance or automatic assignment of unbalanced loads.

`pycy_emt_lite.components.three_phase.ThreePhaseParallelRLCLoad` converts total three-phase nominal P, QL and QC into parallel
branches per phase. With `Vp=nominal_line_voltage/sqrt(3)` and `ω=2π frequency`,
`R=Vp²/(P/3)`, `L=Vp²/[ω(QL/3)]`, `C=(QC/3)/(ωVp²)`.
`active_power` uses W and `inductive_power/capacitive_power` use nonnegative var. A zero value omits that branch; all three cannot
be zero. This is a **fixed-impedance load** derived at the nominal point: power changes with terminal voltage rather than holding P/Q.
Existing checks cover conversion, outputs and initialization/first step, not full fault validation.

An enabled `Fault` connects its node to ground through a finite positive resistance; disabled, it has no branch conductance.
A closed `Breaker` uses a finite positive resistance; open, it has no branch conductance. Add them to the circuit before applying
standard events. Event order and the unsupported-impulse boundary are specified in the numerical document.

Example 05 uses 20 Ω and 50 mH in series per load phase with 0.5 Ω line resistance. At 50 Hz, reactance is about 15.7 Ω;
`I=Vsource/(Rline+Rload+jωLload)` and `Vload=I(Rload+jωLload)`.
RMS and total three-phase P/Q use two cycles at 0.06–0.10 s. Current lags its source phase voltage by about 37.46°.
All inductor currents start at zero, including phases B/C whose source voltages are nonzero at t=0.

Example 06 uses 0.8 Ω and 5 mH per line phase, 50 Ω load and 0.1 Ω fault resistance, applied at 0.04 s and cleared at 0.08 s.
Each stage satisfies `L di/dt+(Rline+Req)i=vsource`, with `Req=Rload` normally and `Req=Rload || Rfault` during the fault.
Inductor current is continuous; `vbus=Req i` and fault current may jump. Clearing transfers line current into the load, giving about
7.79 kV peak bus voltage with default parameters, decaying with the roughly 98 μs time constant `L/(Rline+Rload)`; the step is 10 μs.
This teaching circuit excludes parasitic capacitance, arresters and arcs; it does not predict equipment insulation requirements.
The three quantities are plotted separately. Tests use a piecewise sinusoidal particular solution plus exponential transient to check
initial states, switching currents, the whole waveform and fixed-window metrics.

Examples 06/07 use full 50 Hz cycles at 0.01–0.03, 0.05–0.07 and 0.09–0.11 s. The 06 fault window still includes decaying terms,
so phase RMS values can differ; mean active power per resistive load phase is `Vbus_rms²/Rload`.
Example 07 separately checks faulted/healthy-phase voltage dividers in its single-phase-grounding resistive network.
See the numerical document for restrictions on integration across events.

## 4. Pi and segmented lines

`PiLine` is a single-phase lumped line; `ThreePhasePiLine` repeats the same independent network per phase:

```text
Sending terminal -- series R-L -- Receiving terminal
Sending terminal -- C/2 -- Ground
Receiving terminal -- C/2 -- Ground
```

`resistance` is series resistance in Ω, `inductance` is series inductance in H and may be zero, and `capacitance` is total
line-to-ground capacitance in F and may be zero. These models suit lumped transients of short/medium lines; frequency-dependent
parameters, mutual coupling and distributed traveling waves are excluded. All R/L/C values must be finite and nonnegative; R/L cannot both be zero.

Example 08 compares RMS phasors over two complete cycles at 0.02–0.06 s:

```text
Yrecv = 1/Rload + jωC/2
Vrecv = Vsend / (1 + (R + jωL)Yrecv)
Iseries = Yrecv Vrecv
```

Tests cover both capacitor currents, KCL, storage/port-work balance over the entire startup, and errors on common physical times: halving the step reduces trapezoidal error by approximately four and backward-Euler error by two. The trapezoidal discrete energy check computes port work from the averages of endpoint voltages/currents. Stored energy is `L Iseries²/2 + C(Vsend²+Vrecv²)/4`. Example RMS and resistor power use the existing piecewise-linear metrics.

### Segmented lines: spatial discretization error

`pycy_emt_lite.components.lines.SegmentedLine` splits total R/L/C equally into N Pi sections. Each section has C/(2N) at each end; adjacent capacitors at an internal node sum to C/N. R/L/C use Ω/H/F, `sections` is a positive integer, and L or C may be zero, while R/L cannot both be zero. It remains an optional comparison in the lumped-line lesson, using the existing simulation workflow. More sections do not remove time-step error; phase coupling and frequency-dependent parameters are excluded.

Existing `i:LINE:sending` and `i:LINE:receiving` are the first and last **series currents**, and `i:LINE:average` is the arithmetic mean of all section series currents. All are positive from sending to receiving. Total terminal currents additionally include the end capacitors: `Iin=Ifirst+C/(2N)·dVsend/dt`, `Iout=Ilast-C/(2N)·dVrecv/dt`, where Iin enters the sending terminal and Iout leaves the receiving terminal. Do not directly use the series-current outputs to calculate terminal power. For C=40 μF, N=4, sending voltage `10 sin(2π50t)` V and zero stored states, Ifirst=0 and Iin=0.015708 A at t=0.

The independent AC reference cascades single-section two-port matrices:

```text
Z = R + jωL, Y = jωC, z = Z/N, y = Y/N
Mπ = [[1+zy/2, z], [y(1+zy/4), 1+zy/2]]
[Vsend, Iin]ᵀ = Mπᴺ [Vrecv, Iout]ᵀ
```

The continuous uniform-line reference is `exp([[0,Z],[Y,0]])`, obtained from the voltage/current spatial equations integrated from receiving to sending over normalized length 0–1. Tests use total R=8 Ω, L=60 mH, C=40 μF, a 30 Ω load and a 100 V RMS/50 Hz source. Independent phasors initialize the circuit, with a fixed 10 μs step and 0–0.02 s window. Receiving complex-phasor errors for N=1/2/4/8 are approximately 1.6680/0.40882/0.10171/0.025407 V: doubling sections reduces error by about four. Further tests cover zero initial states, zero-capacitance reduction, end-capacitor KCL and storage versus terminal work/load dissipation with zero line resistance. This evidence covers the stated linear uniform-parameter model, not broadband transients of a complete distributed line.

## 5. Bergeron lines

`BergeronLine` is a single-phase teaching distributed-line model; `ThreePhaseBergeronLine` uses independent phases.
`surge_impedance` (Ω) and `travel_time` (s) specify characteristic impedance Zc and delay τ. Both port currents enter the line:

```text
i_s(t) = v_s(t) / Zc + I_s_hist(t)
i_r(t) = v_r(t) / Zc + I_r_hist(t)
```

For unit attenuation, the histories use the opposite terminal's delayed voltage and current:

```text
I_s_hist(t) = -v_r(t - τ) / Zc - i_r(t - τ)
I_r_hist(t) = -v_s(t - τ) / Zc - i_s(t - τ)
```

Only a fixed time grid is supported. `travel_time` must be a positive integer multiple of the step; stop and actual event times
must align with the grid using the simulator's pairwise 8 ULP rounding tolerance. Invalid settings fail before the first solve;
`quantize_up` can postpone an off-grid requested event. History uses integer-step lookup, zero terminal history for negative times,
and explicit errors for missing history. Same-time events retain only the right-side terminal frame. Tests cover matched-load
arrival, no pre-arrival response and open/short reflections. `attenuation` represents teaching propagation attenuation; fractional
step delays, history interpolation, frequency-dependent attenuation, modal transforms and phase coupling are excluded.
`surge_impedance` must be finite and positive; `attenuation` must be in (0,1].

## 6. Single-phase linear transformers

`SinglePhaseTransformer` has the following structure:

```text
Primary winding port -- primary-referred leakage -- ideal turns ratio -- Secondary winding port
Parallel magnetizing branch across the primary winding port
```

- `turns_ratio`: primary/secondary ideal winding-voltage ratio `Vp/Vs`.
- `leakage_resistance`: primary-referred leakage resistance, Ω.
- `leakage_inductance`: primary-referred leakage inductance, H.
- `magnetizing_inductance`: linear magnetizing inductance, H.
- `core_loss_resistance`: core-loss resistance, Ω.

Turns ratio must be finite and positive, and leakage R/L finite and nonnegative. Magnetizing inductance and core-loss resistance
may be `None` to omit the branch; otherwise they must be finite and positive. Saturation knee and saturated inductance must both
be supplied as finite positive values, together with linear magnetizing inductance.

The winding constraints are:

```text
v_p - n v_s - Z_leak i_p = history term
i_s + n i_p = 0
```

Here `n=turns_ratio`; both currents enter the corresponding positive winding terminal.
The turns ratio is the ideal winding ratio; loaded terminal voltage ratio also depends on leakage impedance. `i:T1:primary` excludes parallel magnetizing and core-loss currents. Total current supplied to the transformer in example 09 is `-i:V1`. For sinusoidal primary voltage and a resistive secondary load, RMS phasors satisfy:

```text
Ileak = Vpri / (Rleak + jωLleak + n²Rload)
Vsec = n Rload Ileak
Isecondary = -n Ileak
Iinput = Ileak + Imag + Vpri/Rcore   # omit the last term when core loss is absent
```

With zero initial current and `sqrt(2) Vrms sin(ωt)` primary voltage, ideal magnetizing current is `im(t) = sqrt(2) Vrms (1-cos(ωt))/(ωLm)`. Its DC component does not decay and must be included in total input RMS. Example 09 compares loaded voltage/total current to analytical values over 0.02–0.06 s and checks input power minus load power and copper loss. Tests also cover optional core loss, full-startup energy balance and step convergence for both methods. These checks establish the linear model only, not saturation or hysteresis.

## 7. Flux and the unvalidated saturation approximation

Saturation uses the preceding time's flux to choose the present step's inductance:

```text
|ψ| < ψ_knee     use magnetizing_inductance
|ψ| >= ψ_knee    use saturated_magnetizing_inductance
```

Flux integrates primary winding voltage with the same method as the magnetizing inductor:

```text
Trapezoidal:     ψ_k = ψ_{k-1} + (v_p,k-1 + v_p,k) Δt/2
Backward Euler:  ψ_k = ψ_{k-1} + v_p,k Δt
```

For linear Lm, `ψ(t)-ψ(0)=Lm·(im(t)-im(0))`. Regressions cover single/three-phase models, both methods and off-grid/endpoint events. Previously flux always used backward Euler, making it inconsistent with trapezoidal current; this is corrected. Saturation still chooses inductance from the preceding flux: `magnetizing_inductance` below `saturation_knee_flux` in absolute flux, and `saturated_magnetizing_inductance` at or above it. No nonlinear iteration is introduced. This approximation lacks independent saturation-curve or energy validation; linear regressions do not establish inrush accuracy. Full core hysteresis, remanence, loops and frequency-dependent losses are excluded.

## 8. Three-phase transformers

`ThreePhaseTransformer` supports Y/Y, Y/Δ, Δ/Y and Δ/Δ through `primary_connection` and `secondary_connection`, each taking `"Y"` or `"D"`. Y windings run from `bus:phase` to neutral. Delta winding directions are a: `bus:a → bus:b`, b: `bus:b → bus:c`, c: `bus:c → bus:a`.

`turns_ratio=n` is the ideal winding turns ratio. Leakage is referred to each primary winding in Ω/H; magnetizing inductance and core-loss resistance are also per primary winding. With a delta secondary and zero leakage impedance, winding circulating current is not uniquely determined; construction requires positive `leakage_resistance` or `leakage_inductance`. Δ/Y can use zero leakage; a delta primary alone no longer causes rejection. Y neutrals default to ground. Floating networks still need physical circuit constraints; the program does not automatically add leakage resistors.

With these winding directions, abc positive sequence and no leakage drop, the line-voltage relationships are:

| Primary/secondary | Secondary/primary line-voltage RMS | Secondary phase shift relative to primary |
|---|---|---|
| Y/Y | 1/n | 0° |
| Y/Δ | 1/(√3 n) | −30° |
| Δ/Y | √3/n | +30° |
| Δ/Δ | 1/n | 0° |

Ideal entries with a delta secondary are limits as nonzero leakage approaches zero. Loaded voltage drop and phase also depend on actual leakage. `i:T:primary:a` is winding-a leakage current, excluding magnetizing/core-loss currents; `i:T:secondary:a` enters the positive secondary winding terminal and satisfies `Is=-n Ip`. Delta line current is the difference of neighboring winding currents: `Iline,a=Iw,a-Iw,c`, with cyclic expressions for the other phases. Include magnetizing/core-loss currents in primary Iw before taking differences. Current delivered to a grounded-star load is opposite to secondary winding inflow; winding current must not be directly interpreted as load phase current.

All four connections are checked against independent analytical RL startup solutions with zero initial inductor currents. Tests use 100 V RMS/50 Hz primary phase voltage, n=2, Rleak=0.2 Ω, Lleak=20 mH, Lm=2 H, Rcore=1000 Ω and 10 Ω per grounded secondary load phase. A balanced star load is equivalent to 3Rload per delta winding; each winding uses `Vp/(Rleak+jωLleak+n²Rw)` for steady current plus the zero-initial-state exponential transient. Checks cover terminal voltages, both line/winding current sets, magnetizing DC, flux, and copper/core-loss/storage balance over the full 0–0.02 s interval. At common points for 20/10 μs steps, error ratios are approximately 4 for trapezoidal and 1.95–2.00 for backward Euler; the latter's energy balance includes numerical dissipation. Separate tests check zero-leakage Y/Y and Δ/Y voltages and power with unbalanced resistive loads. The model supports studying connection-dependent ratios and phase shifts; these checks do not establish shared-core coupling, arbitrary vector groups or saturated faults.

## 9. Synchronous machines

Import both models from `pycy_emt_lite.machines` and use the existing `Circuit/Simulator` workflow.
[Example 10](../examples/10_park_generator_avr_governor.py) uses `CaseDefinition`.

| Model | Retained equations | Intended use |
|---|---|---|
| `SynchronousMachine` | Fixed-amplitude three-phase internal voltage, per-phase stator R–L, rotor angle and speed | Circuit transients and electromechanical power; no exciter, governor or full flux-linkage machine |
| `ParkSynchronousGenerator` | Fourth-order transient-voltage machine plus first-order AVR and governor, six states in total | Balanced, near-fundamental load and regulation responses; fast stator transients are replaced by algebraic ports |

The Park model does not cover short-circuit DC offset, subtransients, unbalanced faults, saturation or hysteresis.
Its zero-sequence port contains only stator resistance; this is not a full dq0 machine.

### Units, directions and ports

Positive current flows from internal voltage to the terminal. `p` is total three-phase active power delivered to the network (W).
`base_power` is total three-phase capacity (VA); `base_phase_rms` is phase-to-neutral RMS voltage (V):

```text
Zbase = 3 Vbase_rms² / Sbase
Vbase_peak = sqrt(2) Vbase_rms
Ibase_peak = sqrt(2) Sbase / (3 Vbase_rms)
theta = 2 pi frequency t + rotor_angle
```

The classical model's `stator_resistance/stator_inductance` are in ohms/henries; do not enter per-unit reactance directly.
`inertia_constant` is in seconds, `frequency` in Hz, `rotor_angle` in electrical radians and `speed_pu` in per-unit speed.
`damping` is the per-unit damping-power coefficient for speed deviation from synchronism.
Classical `mechanical_power` is in watts and accepts a constant or time function; Park `mechanical_power_*_pu` uses the three-phase capacity base.

Park uses d=`-cos(theta)`, q=`sin(theta)`: negate both outputs of the general `abc_to_dq` transform and divide by their peak bases.
The inverse is `dq_to_abc(-ed, -eq, theta)`, replacing the old convention that negated only the q-axis current.
Phase angles are `theta`, `theta-2pi/3`, `theta+2pi/3`. The per-unit terminal equations are:

```text
Vd = Ed' - Rs Id + Xq' Iq
Vq = Eq' - Rs Iq - Xd' Id
```

Both transient reactances enter the port. With rows of M equal to `[-cos(theta_phase), sin(theta_phase)]`,
the SI branch equation is `Eabc - Vabc = Zabc Iabc`, where:

```text
Zabc = Rs_ohm I3 + Zbase M [[0, -Xq'], [Xd', 0]] (2/3 M^T)
```

This linear, angle-dependent coupled stamp uses the existing solver. Park stator currents are algebraic.
The old derived `stator_inductance` property and inductor histories are removed; `X'd` is no longer treated as three independent dynamic inductors.

### Power, states and initialization

The classical model uses `P_em = sum(e_phase*i_phase)`; its difference from terminal power includes copper loss and stator R–L energy exchange.
Park neglects fast stator storage and uses `P_em = P_terminal + P_copper`. Under balanced conditions:

```text
P_terminal / Sbase = Vd Id + Vq Iq
P_copper / Sbase = Rs (Id² + Iq²)
P_em / Sbase = Ed' Id + Eq' Iq + (Xq' - Xd') Id Iq
```

The last term is the saliency/reluctance contribution. With unequal transient reactances, transient internal voltage times current alone is not air-gap power.
Both models output `p` (terminal), `p_copper` (copper loss), and `p_em` (electromagnetic/air-gap power), all in watts.
Their power-form swing equations retain the speed denominator:

```text
dspeed_pu/dt = (Pm/Sbase - P_em/Sbase - D(speed_pu-1)) / (2 H speed_pu)
drotor_angle/dt = 2 pi frequency (speed_pu-1)
```

The other Park state equations are:

```text
dEq'/dt = (Efd - Eq' - (Xd-Xd') Id) / Tdo'
dEd'/dt = (-Ed' + (Xq-Xq') Iq) / Tqo'
dEfd/dt = (Efd_initial + Kavr (Vref-Vt) - Efd) / Tavr
dPm_pu/dt = (Pm_reference - (speed_pu-1)/droop - Pm_pu) / Tgov
```

`Vt=hypot(Vd,Vq)`. The exciter bias is `initial_efd_pu`, so `avr_gain=0` holds the declared field voltage.
Time constants are in seconds; voltages, reactances, control limits and references use their respective per-unit bases.
Updated field voltage and mechanical power are clipped to `efd_min/max_pu` and `mechanical_power_min/max_pu`.

At t=0, hold declared dynamic states and solve the network. Classical stator currents start at zero; Park currents follow the algebraic port and are generally nonzero.
Electromechanical/control states advance once by forward Euler using the same left-end feedback, before solving and recording the current network.
Rotor angle, transient voltage and abc outputs in one row therefore share one time.
Electromechanical coupling is first order; `SimulationConfig.method` selects integration only for classical stator R–L and external storage components.
Explicit events hold dynamic states while solving the right-side network. Park currents may jump algebraically; classical inductor currents remain continuous.

There is no automatic load-flow initialization. Example 10 derives a balanced resistive operating point using
`I=1/Rload_pu`, `A=Rload_pu+Rs`, `Iq=I A/hypot(A,Xq)`, `Id=I Xq/hypot(A,Xq)`, then obtains `Ed'/Eq'/Efd/Pm` from the port and state equations.
Initially the terminal is at 100 V RMS and 1000 W, copper loss is 13.333333 W, and mechanical input is 1013.333333 W.
At 0.2 s, 18 ohms per phase is added in parallel through a 1 milliohm breaker. The default stop is 0.6 s, an observation endpoint with no claim of a new steady state.

Run `uv run python examples/10_park_generator_avr_governor.py`. Edit the top-level capacity, voltage, impedances, loads, times and saving flags;
exciter, governor and inertia parameters remain in `define_case()`.
The example displays separate voltage/field, speed and power figures, with saving disabled by default and fixed filenames when enabled.
Nonfinite values, negative impedances, nonpositive time constants/inertia, reversed limits and out-of-range initial states report the parameter and repair.
Reduce the step and check convergence. If an extra ideal constraint on a Park internal voltage node requires its derivative, the model rejects it:
remove that internal constraint and connect the external circuit through a terminal with finite impedance.

### Validation and remaining limits

- Classical model: resistive divider, analytical deceleration due to copper loss, independent integration of rotor and three-phase R–L currents, discrete storage balance and first-order rotor-angle convergence.
- Park: analytical initial currents with unequal transient reactances, abc/dq signs, air-gap power including saliency, and same-time state/internal-voltage consistency.
- Example 10: pre-step equilibrium, post-step KCL/port equations and an independent piecewise continuous ODE reference; 200/100/50 microsecond steps give first-order convergence on common times. Initial, off-grid and endpoint events do not advance states twice.
- These checks validate the stated approximate equations, not agreement with a vendor's complete machine or experimental data. Complex faults and engineering controller settings remain outside that evidence.

See [PowerWorld's transient-stability modeling overview](https://www.powerworld.com/files/T01ModelRelationships.pdf) for model levels and explicit update ordering,
and [PSCAD Basic Machine Theory](https://www.pscad.com/webhelp/EMTDC/Rotating_Machines/basic_machine_theory.htm) for full machine dq transforms and winding structure.
This section states this project's actual approximations and signs; the reference software's features are not implied to be implemented here.

## 10. Switches, filters and PWM

### Explicit switches

`IdealSwitch` in `pycy_emt_lite.components.power_electronics` accepts a Boolean, numeric 0/1, or a time function returning those values. It stamps `1/closed_resistance` when on and `open_conductance` when off. The resistance must be finite and positive (Ω); off conductance must be finite and nonnegative (S), and may be zero. Constant gates are checked at construction and callable results at each stamp. NaN/Inf, strings, arrays and other numeric values raise an error before Boolean conversion, with the switch name, time and `closed` value. A rejected sample does not change switch state. This explicit conductance approximation is not a complete device model. PWM checks cover gate timing, on/off conductance, current direction and the fundamental component; nonlinear semiconductor equations and switching losses are outside scope.

### Filter composition

`pycy_emt_lite.converters` exports three optional single-phase assemblies for studying filter connections and damping. Calling `.components()` returns ordinary R/L/C objects for the existing `Circuit/Simulator` workflow; an assembly has no dynamic states or separate solver.

| Assembly | Connections and current directions |
|---|---|
| `LFilter` | `input_node → series_resistance → inductance → output_node`; current is positive from input to output |
| `LCFilter` | The same series R–L branch, with C from the output node to `ground`; capacitor current is positive toward ground |
| `LCLFilter` | `converter_node → R1/L1 → capacitor_node → R2/L2 → grid_node`; a series Rd–C branch connects the middle node to ground, with i1 entering the middle node and i2 flowing toward the grid |

Inductance is in H, capacitance in F and resistance in Ω. L/C must be positive. All resistance parameters may be zero, which omits the corresponding resistor. `damping_resistance` is **in series** with C. Rd=0 connects C directly to the middle node; it does not omit the capacitor. All electrical parameters must be finite real numbers. Construction rejects negative values, NaN/Inf, Booleans and nonnumeric inputs, identifying the name, parameter and required range. For example, `series_resistance=-1` used to silently omit the resistor and now raises an error; explicitly use zero for a lossless branch.

This runnable LC circuit uses a 10 V peak, 50 Hz source and a 10 Ω load:

```python
import math
from pycy_emt_lite import Circuit, Resistor, SimulationConfig, Simulator, VoltageSource
from pycy_emt_lite.converters import LCFilter

filter_ = LCFilter("F", "src", "load", "0", inductance=0.01,
                   capacitance=1e-4, series_resistance=0.5)
components = [
    VoltageSource("V", "src", "0", lambda t: 10 * math.cos(2 * math.pi * 50 * t)),
    *filter_.components(),
    Resistor("LOAD", "load", "0", 10.0),
]
result = Simulator(Circuit.from_components("lc_filter", components),
                   SimulationConfig(time_step=1e-5, stop_time=0.02)).run()
print(result.rows[-1]["v:load"])
```

Generated iL/vC initial values are zero. For nonzero states, use `dataclasses.replace` on the generated inductor's `initial_current` or capacitor's `initial_voltage` before building the circuit. Call `.components()` again to obtain fresh components for each simulation. Results retain the basic component names: for example, LC uses `i:F:L` and `i:F:C`; LCL uses `i:F:converter:L`, `i:F:grid:L` and `i:F:C`. With Rd>0, the middle-node voltage relative to `ground` is `vC + Rd·(i1-i2)` and the capacitor's upper terminal is internal node `F:damping`; with Rd=0 the two voltages coincide.

The independent reference integrates these circuit equations without calling assembly stamps or state updates:

- LC with resistive load Rload: `L·di/dt = vin-Rs·i-vC`, `C·dvC/dt = i-vC/Rload`.
- LCL between independent voltage sources: `ic=i1-i2`, `vm=vC+Rd·ic`, `L1·di1/dt=vconv-R1·i1-vm`, `L2·di2/dt=vm-R2·i2-vgrid`, `C·dvC/dt=ic`.
- LCL stored energy is `E=(L1·i1²+L2·i2²+C·vC²)/2`, with `dE/dt=vconv·i1-vgrid·i2-R1·i1²-R2·i2²-Rd·ic²`.

Regressions cover zero initial states, source-current directions, KCL, the Rd drop and whole-transient discrete energy balance, both with zero resistances and with damping. LC/LCL reuse and test the L series assembly. The reference uses SciPy DOP853 at common times over 0–0.02 s. LC uses the parameters above and an Rs=0 comparison, with 20/10 μs steps. LCL uses L1=10 mH, L2=5 mH and C=100 μF, terminal voltages `10 cos(2π50t)` V and `6 cos(2π50t-0.2)` V, resistances either all zero or `(R1,R2,Rd)=(0.4,0.3,2)` Ω, and 5/2.5 μs steps. Halving the step gives maximum-state-error ratios of about 4 for trapezoidal and 1.93–1.99 for backward Euler.

Trapezoidal energy checks use endpoint-averaged voltages/currents to balance storage, port work and physical resistor losses. Backward Euler additionally dissipates `(ΣL·Δi²+ΣC·Δv²)/2` per step. At 2.5 μs, undamped LCL still has about 0.541 V maximum vC error with backward Euler, compared with 0.000387 V for trapezoidal; backward Euler decay must not be interpreted as physical damping. These checks cover linear passive filters, not closed-loop grid-connected converters.

### PWM example validation

`examples/12_two_level_pwm_generator.py` drives an RL load with a two-level PWM inverter using `IdealSwitch` and triangular-carrier comparison for gate signals.

Example 12 reports phase-current total RMS, fundamental RMS and phase difference over 0.1–0.2 s (six 60 Hz cycles and 100 carrier cycles). Phase is relative to each phase's unheld sinusoidal reference. The fundamental average-model reference includes the zero-order hold `sinc(f Ts) exp(-jωTs/2)` and switch on-resistance. It applies only to linear modulation and excludes switching ripple; total RMS differs from fundamental RMS.

Tests verify complementary gates, floating-star phase voltages, zero current sum and the fundamental RL impedance. Steps of 5/2.5/1.25 μs are compared over the common 0.05–0.10 s window. Relative to 1.25 μs, maximum fundamental-phasor differences are approximately 0.214% at the default 5 μs and 0.094% at 2.5 μs; waveform RMS differences are below 0.6 A and 0.3 A, respectively. The fine grid is a step-sensitivity comparison, not a device-physics reference. `event_time_policy` constrains explicit events only and does not locate callable gate edges automatically; no second-order PWM waveform convergence, dead-time or device-level behavior is claimed.

## 11. Control blocks and SRF-PLL

`pycy_emt_lite.controls` supplies discrete blocks called explicitly by the example; they do not stamp MNA.
`block.step(input_value, time_step)` uses the actual control sampling interval. `block.reset()` resets only the control block,
not a `Simulator`. Calling code connects sampling, measurements and control outputs; there is no hidden closed-loop scheduler.
Example 18 explicitly updates three independent controllers through optional `on_step` at each EMT solution point; commands act at the next network step. See the [control and reference mapping](three_terminal_vsc_hvdc.en.md).
Numeric block parameters, inputs, sampling intervals and reset values are checked for type and finiteness, rejecting NaN/Inf,
Boolean numeric inputs and strings. Sampling intervals and low-pass time constants must be positive; `SampleDelay.steps` must be
a nonnegative integer. Validation precedes updates, so invalid inputs and reset values do not contaminate history.

| Block | Implemented discrete relation |
|---|---|
| `Limiter` | Clamps to lower/upper bounds, without dynamic state |
| `PIController` | Candidate integral `xi_new=xi+Ki*e*h`; output is clipped `Kp*e+xi_new`. The candidate integral is not stored when saturated and the error pushes farther in that direction |
| `FirstOrderLowPass` | Backward Euler for `dy/dt=(u−y)/tau`: `y_new=(y+h*u/tau)/(1+h/tau)` |
| `SampleDelay` | Integer-sample queue delay, initialized with `initial_value`; zero delay passes input through |

Amplitude-invariant Clarke/Park transforms are:

```text
alpha = 2/3 * (a - b/2 - c/2)
beta  = sqrt(3)/3 * (b - c)
d = alpha cos(theta) + beta sin(theta)
q = -alpha sin(theta) + beta cos(theta)
```

`dq_to_abc()` reconstructs with zero sequence set to zero. Round trips are tested for balanced signals without zero sequence;
do not assume arbitrary input zero sequence is retained. Machine d/q axes use the section 9 convention and cannot be substituted directly.

`SRFPLL.step(voltages_abc, time_step)` takes voltage samples at the **current time**; `time_step` is the interval since the previous
sample. First integrate angle using the previous angular frequency, then update PI using the current voltage and that angle.
The new angular frequency applies to the next integration interval:

```text
θ_new = wrap_0_to_2pi(θ_old + ω_old h)
(vd, vq) = abc_to_dq(vabc_current, θ_new)
Vbase = max(abs(vd), abs(vq), 1.0)
Δω = PI(vq / Vbase)
ω_new = nominal_frequency + Δω
```

Both `nominal_frequency` and output `frequency` use **rad/s**, not Hz: pass `2π50` for 50 Hz.
`nominal_frequency` must be finite and positive. `minimum_frequency/maximum_frequency` bound **absolute angular frequency**;
provided bounds must be finite and contain nominal frequency, while `None` leaves that side unbounded. Internally, PI correction
limits are `[ωmin−ωnom, ωmax−ωnom]`, preserving integral freezing during saturation. For nominal 50 Hz with 45–55 Hz limits,
pass `2π50`, `2π45`, `2π55` respectively; nominal locked output remains 50 Hz. Invalid ranges, including those excluding nominal
frequency, fail at construction. This corrects the earlier correction-limit interpretation: add `nominal_frequency` to each old Δω
bound when migrating an existing script.
Returned `PLLState` d/q voltages use the returned angle; angle, angular frequency and voltages belong to the current sample row.
`time_step` must be a finite positive real number. Invalid intervals fail before state changes and report how to repair the input;
do not call `step` merely to observe initial values at zero time.

[Example 11](../examples/11_pll_dynamic_response.py) is a pure control loop marked `explicit_control`, without an MNA network.
It records the declared t=0 angle, nominal angular frequency and their d/q projection before advancing from the first positive time;
`stop_time=0` produces only the initial row. Time parameters reuse `SimulationConfig` validation, rejecting noninteger-step stops
before the loop; this does not change the control discretization above. Defaults are 230 V RMS, 50 Hz, a 30° source-phase offset,
100 μs sampling and a 1 s duration. PLL aligns with the voltage space vector: for this sinusoidal source the target angle is `2πft+offset−π/2`.

Regressions cover nominal initial lock with varying positive intervals, same-time returned angle/dq, example initialization/endpoints
and invalid intervals without state advancement. PLL voltage samples must contain exactly three finite real numbers; invalid
parameters, samples or reset angles raise explicit errors, and rejected samples preserve usable prior state. Further checks cover
45–55 Hz limits, one-sided limits, persistent saturation and release, reset, and no partial PI update on frequency overflow. The balanced 325 V peak, 50 Hz test with 100 μs sampling and PI gains 80/1000
still checks `|vq|<5 V` and angular-frequency error `<2 rad/s` after about 0.1 s.
An independent continuous reference additionally checks positive-time transients with `dθ/dt=ωnom+Kp e+xi`, `dxi/dt=Ki e`,
where `e=sin(θgrid−θ)/max(|cos(θgrid−θ)|,|sin(θgrid−θ)|,1/Vpeak)`, without calling PLL transforms or state updates.

That comparison uses nominal 50 Hz, actual 52 Hz, 325 V peak, initial angle 0.4 rad, initial grid space-vector angle 0.7 rad,
PI gains 80/1000 and zero initial integral, with a DOP853 reference over 0–0.2 s.
For 100/50/25 μs steps, maximum angle errors at common positive times are approximately 0.002471/0.001230/0.000614 rad,
and angular-frequency errors are 0.2168/0.1079/0.0538 rad/s, showing first-order convergence.
Declared initial frequency remains nominal and is held over the first interval; the continuous equation's instantaneous proportional
feedback frequency is not used to check the declared t=0 output. Evidence is limited to these balanced inputs, discrete relations
and the listed input boundaries, not frequency/phase-step performance, weak-grid stability, negative-sequence decoupling,
notch filters, specialized limit recovery or closed-loop grid control.

PWM helpers `triangular_carrier()` generate a [-1,1] triangle, `sine_pwm_duty()` gives duty from modulation index and electrical angle,
and `carrier_compare()` returns a 0/1 comparison. PWM functions reject nonfinite values and incorrect types before comparison;
carrier frequency must be positive and modulation index must lie in [0,1]. Space-vector modulation, three-level modulation and dead time are not currently promised features.

## 12. Optional connection examples

Segmented line with zero initial stored states and a 10 V peak/50 Hz source:

```python
import math
from pycy_emt_lite import Circuit, Resistor, SimulationConfig, Simulator, VoltageSource
from pycy_emt_lite.components.lines import SegmentedLine

components = [
    VoltageSource("V1", "source", "0", lambda t: 10 * math.sin(2 * math.pi * 50 * t),
                  derivative=lambda t: 10 * 2 * math.pi * 50 * math.cos(2 * math.pi * 50 * t)),
    SegmentedLine("LINE", "source", "load", resistance=1.0, inductance=1e-3, capacitance=1e-6, sections=4),
    Resistor("LOAD", "load", "0", 9.0),
]

circuit = Circuit.from_components("segmented_line_demo", components)
config = SimulationConfig(time_step=1e-5, stop_time=0.02)
simulator = Simulator(circuit, config)
result = simulator.run()
```

Delta/Y transformer with zero leakage and approximately 86.6025 V RMS secondary phase voltage:

```python
from pycy_emt_lite import Circuit, Resistor, SimulationConfig, Simulator, ThreePhaseSource
from pycy_emt_lite.components.transformers import ThreePhaseTransformer

components = [
    ThreePhaseSource("VS", "primary", phase_rms=100.0),
    ThreePhaseTransformer(
        "T1",
        "primary",
        "secondary",
        turns_ratio=2.0,
        primary_connection="D",
        secondary_connection="Y",
        magnetizing_inductance=10.0,
    ),
    Resistor("LA", "secondary:a", "0", 50.0),
    Resistor("LB", "secondary:b", "0", 50.0),
    Resistor("LC", "secondary:c", "0", 50.0),
]

circuit = Circuit.from_components("transformer_demo", components)
config = SimulationConfig(time_step=1e-4, stop_time=0.1)
simulator = Simulator(circuit, config)
result = simulator.run()
```
