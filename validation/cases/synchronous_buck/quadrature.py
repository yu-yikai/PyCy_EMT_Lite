"""Buck-only cycle quadrature fixed before its first commercial comparison.

Storage states are PWL; recorded duty/gates hold on [t[n], t[n+1]). Source
current is integrated within each gate mode, never across a switching jump.
"""

from __future__ import annotations

import math

import numpy as np

from pycy_emt_lite.io.results import SimulationResult


def source_current(iL, uC, upper, lower, physical: dict):
    """Positive source delivery, including both snubbers and the L shunt."""
    gu = upper / physical["switch_on_resistance_ohm"] + 1 / physical["each_snubber_resistance_ohm"]
    gl = lower / physical["switch_on_resistance_ohm"] + 1 / physical["each_snubber_resistance_ohm"]
    gp = 1 / physical["inductor_parallel_resistance_ohm"]
    return gu / (gu + gl + gp) * (iL - gp * uC + physical["dc_voltage_v"] * (gl + gp))


def cycle_means(time, uC, iL, duty, upper, lower, physical: dict, settings: dict) -> np.ndarray:
    """Exact PWL/held integrals on all declared absolute carrier periods."""
    columns = [np.asarray(values, dtype=float) for values in [time, uC, iL, duty, upper, lower]]
    time, uC, iL, duty, upper, lower = columns
    if (any(values.ndim != 1 or len(values) != len(time) or not np.all(np.isfinite(values)) for values in columns)
            or len(time) < 2 or np.any(np.diff(time) <= 0)):
        raise ValueError("Buck quadrature needs finite columns and a strictly increasing native axis")
    if not all(np.all((gate == 0) | (gate == 1)) for gate in [upper, lower]):
        raise ValueError("Recorded Buck gates must be binary")
    start, end, period, count = (settings[name] for name in ["start_s", "end_s", "period_s", "cycles"])
    if (not isinstance(count, int) or count < 1 or period <= 0 or end <= start
            or not math.isclose(count * period, end - start, rel_tol=0, abs_tol=8 * math.ulp(end))
            or time[0] != start or time[-1] != end):
        raise ValueError("Buck record must cover every declared carrier cycle exactly")
    boundaries = start + np.arange(count + 1) * period
    boundaries[-1] = end
    grid = np.unique(np.r_[time, boundaries])
    index = np.searchsorted(time, grid[:-1], side="right") - 1
    voltage, current = np.interp(grid, time, uC), np.interp(grid, time, iL)
    source_left = source_current(current[:-1], voltage[:-1], upper[index], lower[index], physical)
    source_right = source_current(current[1:], voltage[1:], upper[index], lower[index], physical)
    averages = np.column_stack([.5 * (voltage[:-1] + voltage[1:]),
                                .5 * (current[:-1] + current[1:]), duty[index],
                                .5 * (source_left + source_right)])
    # Left endpoints classify even sub-ULP-close boundary intervals correctly;
    # a rounded midpoint could otherwise fall on the next period boundary.
    cycle = np.searchsorted(boundaries, grid[:-1], side="right") - 1
    if np.any((cycle < 0) | (cycle >= count)):
        raise ValueError("Quadrature interval outside the declared absolute periods")
    return np.column_stack([np.bincount(cycle, weights=np.diff(grid) * averages[:, column] / period,
                                       minlength=count) for column in range(4)])


def candidate_features(result: SimulationResult, parameters: dict, settings: dict) -> dict:
    """Audit actual saved rows and integrate without changing result/event_log."""
    names = ["time", "v:out", "i:L", "duty", "state:Supper", "state:Slower", "i:Vdc", "v:mid"]
    values = {name: result.series(name) for name in names}
    if any(not np.all(np.isfinite(column)) for column in values.values()):
        raise ValueError("Candidate Buck signals must be finite")
    time, uC, iL, duty, upper, lower, source, mid = (values[name] for name in names)
    physical = parameters["physical_parameters"]
    means = cycle_means(time, uC, iL, duty, upper, lower, physical, settings)
    rebuilt = source_current(iL, uC, upper, lower, physical)
    residual = rebuilt + source  # measured i:Vdc is opposite to delivered source current
    gu = upper / physical["switch_on_resistance_ohm"] + 1 / physical["each_snubber_resistance_ohm"]
    gl = lower / physical["switch_on_resistance_ohm"] + 1 / physical["each_snubber_resistance_ohm"]
    gp = 1 / physical["inductor_parallel_resistance_ohm"]
    rebuilt_mid = (physical["dc_voltage_v"] * gu + gp * uC - iL) / (gu + gl + gp)
    held_right_mid = (physical["dc_voltage_v"] * gu[:-1] + gp * uC[1:] - iL[1:]) / (gu[:-1] + gl[:-1] + gp)
    domain = parameters["diode_inactivity_domain"]
    events = result.event_log
    expected_events = parameters["pulse_events"]
    event_mapping = (len(events) == len(expected_events) and all(
        record["time"] == expected[0] and record["target"] == "Ipulse" and record["after"] == expected[1]
        and record["before"] == (0. if index == 0 else expected_events[index - 1][1])
        and record["type"] == "load_current_step"
        for index, (record, expected) in enumerate(zip(events, expected_events, strict=True))))
    power = physical["dc_voltage_v"] * float(np.mean(means[:, 3]))
    expected_grid = np.arange(round(parameters["stop_second"] / parameters["time_step_second"]) + 1) * parameters["time_step_second"]
    expected_grid[-1] = parameters["stop_second"]
    checks = {
        "frozen_step_and_stop": result.time_step == parameters["time_step_second"] and result.stop_time == parameters["stop_second"],
        "all_frozen_grid_rows_retained": len(time) == len(expected_grid) and bool(np.all(abs(time - expected_grid) <= 8 * math.ulp(parameters["stop_second"]))),
        "initial_both_off": bool(upper[0] == lower[0] == 0),
        "post_initial_complementary": bool(np.all(upper[1:] + lower[1:] == 1)),
        "duty_limits": bool(np.all((duty >= parameters["controller"]["duty_limits"][0])
                                    & (duty <= parameters["controller"]["duty_limits"][1]))),
        "rowwise_source_kcl": bool(np.max(abs(residual)) <= 1e-8),
        "rowwise_midpoint_kcl": bool(np.max(abs(mid - rebuilt_mid)) <= 1e-9),
        "current_voltage_domain": bool(np.max(abs(iL)) < domain["abs_iL_a"] and np.max(abs(uC)) < domain["abs_UC_v"]),
        "diode_voltage_domain": bool(np.min(mid) > -physical["diode_forward_voltage_v"]
                                     and np.max(mid) < physical["dc_voltage_v"] + physical["diode_forward_voltage_v"]
                                     and np.min(held_right_mid) > -physical["diode_forward_voltage_v"]
                                     and np.max(held_right_mid) < physical["dc_voltage_v"] + physical["diode_forward_voltage_v"]),
        "all_declared_load_events": event_mapping,
        "positive_source_power": math.isfinite(power) and power > 0,
    }
    return {"cycle_means": means, "checks": checks, "passed": all(checks.values()),
            "source_kcl_residual": residual, "reconstructed_source_rows": rebuilt,
            "max_rowwise_source_kcl_residual_a": float(np.max(abs(residual))),
            "max_rowwise_midpoint_kcl_residual_v": float(np.max(abs(mid - rebuilt_mid))),
            "whole_record_source_power_w": power,
            "source_label": "Held recorded gate modes with PWL storage states and KCL; measured -i:Vdc retained separately",
            "quadrature": "PWL UC/iL; left-held duty and observed gates on [t[n],t[n+1]); no terminal extension"}
