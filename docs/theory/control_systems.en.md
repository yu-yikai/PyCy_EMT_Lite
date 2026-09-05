# Control-System Models

[简体中文](control_systems.md)

Discrete modules in `pycy_emt_lite.controls` produce references, modulation values, or equivalent voltage commands; they do not stamp the MNA matrix.

The interface is `output = block.step(input_value, time_step)` followed by `block.reset()`. The step is the actual sampling interval. Modules include `Limiter`, a discrete `PIController` with frozen anti-windup, a backward-Euler `FirstOrderLowPass`, and a queue-based `SampleDelay`.

The amplitude-invariant Clarke/Park transform uses alpha = 2/3(a - b/2 - c/2), beta = sqrt(3)/3(b - c), d = alpha cos(theta) + beta sin(theta), and q = -alpha sin(theta) + beta cos(theta). `SRFPLL` corrects angular frequency from q-axis voltage and integrates the angle. Negative-sequence decoupling, notch filters, and weak-grid enhancements are not included.

PWM helpers provide triangular carriers, sine-PWM duty generation, and carrier comparison. Controls are called explicitly by examples and do not directly enter MNA assembly. See [renewable_grid_models.en.md](renewable_grid_models.en.md).

The control sampling interval must be passed explicitly, especially when a case contains event boundaries, a short final step, or multiple rates. Controller saturation and state limits belong to the controller contract and should be tested independently from the electrical network. Average-control examples must be labelled as control-level simulations rather than as the same trapezoidal EMT method used by the network solver.

## Controller details

`Limiter` has no dynamic state and clamps its input. `PIController` integrates the error with an explicit rectangular rule; when output limits are configured, the integral is frozen in the direction that would increase saturation. `FirstOrderLowPass` represents `dy/dt = (u-y)/tau` and uses backward Euler. `SampleDelay` stores a fixed number of historical samples and returns a whole-sample delayed value.

## Transform conventions

The first implementation assumes balanced three-phase signals and no zero-sequence component. `dq_to_abc()` provides the inverse mapping. If a future implementation adds zero-sequence or power-invariant transforms, it should use an explicit function name so that amplitude scaling is not confused.

## PLL and PWM boundaries

`SRFPLL` is suitable for a teaching grid-following average model. It does not include negative-sequence decoupling, notch filtering, special weak-grid logic, or a complete limiter-recovery strategy. `triangular_carrier()` returns a carrier in `[-1, 1]`; `sine_pwm_duty()` computes a single-phase duty from modulation and electrical angle; `carrier_compare()` returns a 0/1 switching state.
