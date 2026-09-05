# Component Stamp Principles

[简体中文](stamp_principles.md)

This document explains how the components contribute to the MNA matrix, including common conventions, component equations, matrix entries, state updates, and extension requirements.

## Common convention

Reference nodes are `0`, `gnd`, and `ground`. Unknowns are ordered as non-reference node voltages followed by extra branch currents. A branch current is positive from its positive node to its negative node. Components add entries to the matrix and right-hand side; they do not solve the system themselves.

## Basic stamps

A two-terminal conductance `G` adds `+G` to both diagonal entries and `-G` to both off-diagonal entries. A current source from `p` to `n` subtracts its value at `p` and adds it at `n`. A voltage source adds one branch-current unknown, the corresponding incidence entries, and the constraint `Vp - Vn = Vsource`.

Capacitors use a conductance plus a history current source. Trapezoidal integration uses `G = 2C/dt`; backward Euler uses `G = C/dt`. Inductors use a branch-current unknown and a companion voltage relation; the equivalent resistance is `2L/dt` for trapezoidal integration and `L/dt` for backward Euler.

## Three-phase and dynamic elements

Three-phase sources, lines, and loads stamp one phase branch at a time using the same sign convention. Faults and breakers change the effective conductance before the affected time step. Pi lines combine series R-L and two shunt C/2 branches. Bergeron lines use delayed terminal history sources. Transformers add referred leakage, turns-ratio constraints, and magnetizing branches according to their simplified model.

## Switching and extension rule

Ideal switches use on/off conductance, while diode and IGBT approximations select an explicit state from the previous step or gate signal. A new component must document its physical equation, discrete equation, stamp entries, state-update order, code location, units, current direction, and at least one analytical or physical test. Do not call an average-control update a trapezoidal EMT stamp.

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

A Pi line stamps one series R-L path plus a shunt `C/2` at each terminal. A Bergeron line combines each terminal voltage with the opposite-terminal voltage/current sampled at the travel delay; interpolation and attenuation must be documented. A transformer stamps referred leakage, a turns-ratio constraint, and a magnetizing branch with stated winding polarity.

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

The inactive state contributes leakage or no effective short; the active state contributes the configured conductance. State transitions occur before the matrix for the affected step is assembled and must follow the event-boundary convention.

### PiLine and BergeronLine

Stamp the Pi line's series branch and two terminal shunt capacitors, each with independent history. For a Bergeron line use characteristic impedance and delayed terminal history; check that the first response cannot arrive before the configured travel time.

### Transformers

Stamp leakage, ideal turns ratio, and magnetizing branch using stated primary/secondary polarity. Verify open-circuit ratio and loaded power direction. State which connection groups and mutual effects are unsupported.

### Saturation and machines

Document the flux or magnetizing-current approximation and valid range. For `SynchronousMachine`, identify rotor-angle and speed states, initial values, and electrical torque/power sign. For `ParkSynchronousGenerator`, document dq0 scaling, angle convention, port mapping, and parameter use.

### Diode and IGBTSwitch

The first implementation selects an explicit state from previous terminal voltage or gate signal. It must not be described as a same-step nonlinear semiconductor solve.

### Average renewable models

PV, battery, DC-link, grid-following, grid-forming, VSG, and LVRT updates must state their sampling interval and energy/power conventions. They are not MNA stamps unless explicitly connected to the network solver.

## Review questions

1. Which unknowns does the component add?
2. Which matrix and right-hand-side entries does it write?
3. What is the positive current or voltage direction?
4. What is initialized at `t=0` and when is it updated?
5. Which analytical, conservation, convergence, or independent-reference test proves the stamp?
6. Which parameters are intentionally unsupported?
