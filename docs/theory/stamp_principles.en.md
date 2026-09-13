# Component Stamp Principles

[简体中文](stamp_principles.md)

This document explains how the components contribute to the MNA matrix, including common conventions, component equations, matrix entries, state updates, and extension requirements.

## Common convention

Reference nodes are `0`, `gnd`, and `ground`. Unknowns are ordered as non-reference node voltages followed by extra branch currents. A branch current is positive from its positive node to its negative node. Components add entries to the matrix and right-hand side; they do not solve the system themselves.

## Basic stamps

A two-terminal conductance `G` adds `+G` to both diagonal entries and `-G` to both off-diagonal entries. A current source from `p` to `n` subtracts its value at `p` and adds it at `n`. A voltage source adds one branch-current unknown, the corresponding incidence entries, and the constraint `Vp - Vn = Vsource`.

Capacitors use a conductance plus a history current source. Trapezoidal integration uses `G = 2C/dt`; backward Euler uses `G = C/dt`. Inductors use a branch-current unknown and a companion voltage relation; the equivalent resistance is `2L/dt` for trapezoidal integration and `L/dt` for backward Euler.

## Three-phase and dynamic elements

Three-phase sources, lines, and loads stamp one phase branch at a time using the same sign convention. Faults and breakers change conductance after advancing to the event left limit, before the right-side consistency solve. Pi lines combine series R-L and two shunt C/2 branches. Bergeron lines use delayed terminal history sources. Transformers add referred leakage, turns-ratio constraints, and magnetizing branches according to their simplified model.

## Switching and extension rule

Ideal switches select on/off conductance from a Boolean state or time function. A new component must document its physical equation, discrete equation, stamp entries, state-update order, code location, units, current direction, and at least one analytical or physical test. Do not call a discrete-control update a trapezoidal EMT stamp.

## Component reference

### Resistor

For a resistor between `p` and `n`, let `G = 1/R`. Add `+G` to both diagonal entries and `-G` to both off-diagonal entries. There is no state update.

### Current source

For current `I` from `p` to `n`, subtract `I` from `z[p]` and add `I` to `z[n]`. Reversing the physical direction reverses both signs.

### Voltage source

Allocate one branch-current unknown `k`. Add the incidence entries `+1` at `(p,k)`, `-1` at `(n,k)`, `+1` at `(k,p)`, and `-1` at `(k,n)`. Add the source value to `z[k]`. The constraint is `Vp - Vn = Vsource`.

### Capacitor

With trapezoidal integration use `G = 2C/dt` and `I_hist = -i_prev - G*v_prev`. With backward Euler use `G = C/dt` and `I_hist = -G*v_prev`. Stamp the equivalent two-terminal conductance and history source, then update voltage/current history only after solving.

### Inductor

Allocate a branch-current unknown. With trapezoidal integration use `R_eq = 2L/dt` and `V_hist = -R_eq*i_prev - v_prev`; with backward Euler use `R_eq = L/dt` and `V_hist = -R_eq*i_prev`. Stamp the incidence entries and companion voltage equation, then store current and voltage after the solve.

## Three-phase, fault, and switching stamps

Three-phase sources, lines, and loads expand the single-phase stamp once per phase. A fault is a state-dependent conductance between a target node and ground. A breaker or ideal switch selects an on conductance or off leakage conductance before matrix assembly. The event system must apply each state change at a deterministic step boundary.

## Pi lines, Bergeron lines, and transformers

A Pi line stamps one series R-L path plus a shunt `C/2` at each terminal. A Bergeron line combines each terminal voltage with the opposite-terminal voltage/current sampled at the travel delay; the delay must be a positive integer number of base steps, with stop and actual event times aligned to the fixed grid. Integer-step history lookup uses zero negative-time history and rejects missing samples instead of interpolation or holding the last frame. Explicit events keep one right-side frame. Any teaching attenuation must be stated. A transformer stamps referred leakage, a turns-ratio constraint, and a magnetizing branch with stated winding polarity.

## Required documentation for a new component

Record the continuous law, discrete companion equation, node and branch-current ordering, every nonzero matrix/right-hand-side entry, state initialization and update timing, units, sign convention, source location, and a test. The test should use an analytical value, KCL/KVL, residual, energy, convergence, or an independent reference. A successful exit and a plotted curve are insufficient.

## Component-by-component checklist

For every implementation, verify the physical equation, terminal polarity, matrix contribution, history initialization, post-solve update, and source path.

### ThreePhaseSource

Stamp one ideal voltage-source branch for phases A, B, and C. Use the declared RMS magnitude, frequency, and 0/-120/+120 degree sequence. Record phase voltage fields with their phase suffixes.

### ThreePhaseLine

Create one R-L path per phase. A zero-inductance path has no inductor history; a positive-inductance path has one branch current per phase. The from/to node order defines current sign.

### ThreePhaseLoad

Connect each phase to the declared neutral through its own R-L path. Do not silently replace the wye topology with delta or introduce mutual coupling that is not in the contract.

### Fault, Breaker, and IdealSwitch

The inactive state contributes leakage or no effective short; the active state contributes the configured conductance. Explicit state transitions follow integration to the event left limit; the right-side consistency solve holds storage and supplies the next histories.

### PiLine and BergeronLine

Stamp the Pi line's series branch and two terminal shunt capacitors, each with independent history. For a Bergeron line use characteristic impedance and delayed terminal history; check that the first response cannot arrive before the configured travel time.

### Transformers

Stamp leakage, ideal turns ratio, and magnetizing branch using stated primary/secondary polarity. Verify open-circuit ratio and loaded power direction. State which connection groups and mutual effects are unsupported.

`ThreePhaseTransformer` supports Y/Y, Y/Δ, Δ/Y and Δ/Δ. A delta secondary with zero leakage has undetermined circulating winding current and requires positive leakage resistance or inductance. Δ/Y permits zero leakage. Delta line current is the difference between adjacent winding currents, for example `Ia=Iab-Ica`; primary winding totals also include magnetizing and core-loss currents. See [line and transformer models](advanced_line_transformer_models.en.md) for winding ratios, line-voltage phase shifts and validation limits.

### SegmentedLine

Assemble equal Pi sections sequentially in one component using the shared solver, with separate series and capacitor histories. The `sending/receiving` outputs are the first/last series currents, and `average` is their arithmetic mean, all positive from sending to receiving. They exclude end-capacitor currents: total input is `Ifirst+C/(2N)·dVsend/dt` and total output is `Ilast-C/(2N)·dVrecv/dt`. Use total currents for terminal power.

### Saturation

Flux integrates primary winding voltage using the magnetizing inductor's method: `ψ_k=ψ_{k-1}+(v_p,k-1+v_p,k)Δt/2` for trapezoidal and `ψ_k=ψ_{k-1}+v_p,k Δt` for backward Euler. Read the old voltage before replacing it with the current value. Linear Lm satisfies `Δψ=Lm·Δim`; initialization and event right-side consistency solves do not advance flux. Saturation still selects inductance from previous flux and lacks independent saturation-curve and energy validation; hysteresis, remanence and frequency-dependent core losses are excluded.

### Synchronous machines

The classical model in `machines/synchronous.py` uses three internal ideal voltage sources and stator R–L branches with the existing companion stamps. Electromagnetic power uses internal voltage times branch current, separately from terminal active power.

The fourth-order model in `machines/park_generator.py` uses `Vd=Ed'-Rs*Id+Xq'*Iq`, `Vq=Eq'-Rs*Iq-Xd'*Id`. Transforming to abc gives an angle-dependent coupled impedance: all three branch rows include cross-phase coefficients, instead of a single d-axis inductor. Stator currents are algebraic and may jump at events. Air-gap power is terminal power plus stator copper loss.

Both models advance mechanical states once with left-end feedback before a positive-interval stamp, then solve the current network. `update_state()` records network feedback and classical stator histories; event-right solves do not advance states again. Rotor angle, internal voltage, terminal voltage and current share one output time. See [machine equations and validation](advanced_line_transformer_models.en.md) for full equations, units, initialization and limits, without duplicating the control equations here.

## Review questions

1. Which unknowns does the component add?
2. Which matrix and right-hand-side entries does it write?
3. What is the positive current or voltage direction?
4. What is initialized at `t=0` and when is it updated?
5. Which analytical, conservation, convergence, or independent-reference test proves the stamp?
6. Which parameters are intentionally unsupported?
