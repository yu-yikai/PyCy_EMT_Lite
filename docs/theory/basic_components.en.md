# Basic Component Models

[简体中文](basic_components.md)

## Resistor

```text
i = (v_p - v_n) / R
G = 1 / R
```

The conductance is stamped between the two nodes.

## Capacitor

Current is positive from the positive to the negative terminal: `i = C dv/dt`.

```text
trapezoidal: i_k = G v_k + I_hist
             G = 2C/dt
             I_hist = -i_(k-1) - G v_(k-1)
backward Euler: G = C/dt
                I_hist = -G v_(k-1)
```

The discrete capacitor is a parallel conductance and history current source.

## Inductor

Voltage is positive from the positive to the negative terminal: `v = L di/dt`. Branch current is an MNA unknown.

```text
trapezoidal: v_k - R_eq i_k = V_hist
             R_eq = 2L/dt
             V_hist = -R_eq i_(k-1) - v_(k-1)
backward Euler: R_eq = L/dt
                V_hist = -R_eq i_(k-1)
```

## Ideal sources

An ideal voltage source adds a branch-current unknown and `V_positive - V_negative = V_source`. An ideal current source is positive from positive to negative and changes only the right-hand side.

## Initial values and state update

Capacitor voltage and inductor current are storage states. Their declared initial values must remain the state at `t=0`; the first network solution must not silently overwrite them before the first discrete update. After solving a step, store the current voltage/current and use those values to form the next history source.

For a passive RLC circuit, decreasing the time step should move the result toward the analytical solution. A test should check the waveform, not only its final sample.
