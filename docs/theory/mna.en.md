# Modified Nodal Analysis (MNA)

[简体中文](mna.md)

## Why MNA

Ordinary nodal analysis is convenient for resistors and current sources. Ideal voltage sources, inductors, controlled sources, and power-electronic models require additional branch-current unknowns. MNA handles these elements in one system.

## Equation form

```text
A x = z
```

`A` is the system matrix, `x` contains node voltages and required branch currents, and `z` contains source values and history terms.

## Project conventions

`"0"`, `"gnd"`, and `"ground"` are reference nodes and are excluded from the unknown vector. The usual ordering is:

```text
[all non-reference node voltages, all extra branch currents]
```

For `n1`, `n2`, and voltage source `V1`, one possible vector is `x = [v:n1, v:n2, i:V1]`.

## Basic stamps

A resistor between `p` and `n` contributes `G = 1/R`. A current source is positive from `p` to `n`: it leaves `p` and enters `n`. An ideal voltage source adds a branch current and the constraint `V_p - V_n = V_source`.

Capacitors and inductors are discretized into equivalent conductances/resistances and history sources. See [basic_components.en.md](basic_components.en.md) and [stamp_principles.en.md](stamp_principles.en.md).

## Assembly order

Before the first solve, the circuit registers non-reference nodes and allocates indices for extra branch currents. At each step the solver creates `A` and `z`, asks every component to stamp its contribution, solves the system, records fields, and then updates dynamic history. State must be updated after the solution, not before it.

The same sign convention must be used in the physical equation, matrix entries, right-hand side, recorded current, and state update. A sign mismatch can produce a plausible waveform while violating KCL or energy balance.
