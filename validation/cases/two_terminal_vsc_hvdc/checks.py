"""Measure the frozen two-station physical, timing and power checks in SI units."""

import numpy as np

from pycy_emt_lite.controls import PIController
from validation.cases.grid_connected_vsc_open_loop.metrics import require

STATIONS = "ab"
PHASES = tuple(f"{site}_{phase}" for site in STATIONS for phase in "abc")
RAILS = tuple(f"{site}_{pole}" for pole in "pn" for site in "amb")
LINKS = tuple(f"{pole}_{half}" for pole in "pn" for half in ("am", "mb"))
MEANS = ("a_p_mean_w", "a_q_mean_var", "b_p_mean_w", "b_q_mean_var", "b_dc_mean_v",
         "dc_sent_w", "dc_received_w", "dc_series_loss_w")
PEAK = "b_dc_peak_after_ramp_start_v"
RECOVERY = "b_dc_recovered_abs_error_v"
FAMILIES = {"voltage_abs_v": ("rail_v", "bus_v", "pcc_v"),
            "current_abs_a": ("line_a", "phase_a", "feeder_a"), "modulation_abs_pu": ("applied",)}


def peak(values):
    return float(np.max(np.abs(values)))


def midpoint(data):
    return (data[1:] + data[:-1]) * .5


def physics(trace, step, plant, limits):
    """Check actual branch currents, TR charge and source-to-load energy."""
    rails, cap, line = (trace[key] for key in ("rail_v", "cap_a", "line_a"))
    feed, phase, upper, lower = (trace[key] for key in ("feeder_a", "phase_a", "upper_a", "lower_a"))
    source, pcc, pole = (trace[key] for key in ("source_v", "pcc_v", "pole_v"))
    supply, pre, load = (trace[key] for key in ("supply_v", "pre_a", "load_a"))
    star = np.repeat(trace["star_v"], 3, axis=1)
    sending = [0, 3]
    receiving = [2, 5]
    left, right = [0, 1, 3, 4], [1, 2, 4, 5]
    line_r, line_l = (plant["dc_line_half"][key] for key in ("r_ohm", "l_h"))
    feeder_r, feeder_l = (plant["feeder_per_phase"][key] for key in ("r_ohm", "l_h"))
    filter_r, filter_l = (plant["filter_per_phase"][key] for key in ("r_ohm", "l_h"))
    capacitance = np.array([plant["pole_capacitance_f"]["midpoint" if key.startswith("m") else "terminal"] for key in RAILS])

    kcl = -cap.copy()
    for branch, (a, b) in enumerate(zip(left, right, strict=True)):
        kcl[:, a] -= line[:, branch]
        kcl[:, b] += line[:, branch]
    kcl[:, sending] += pre
    kcl[:, [0, 2]] -= upper.reshape(-1, 2, 3).sum(axis=2)
    kcl[:, [3, 5]] += lower.reshape(-1, 2, 3).sum(axis=2)
    kcl[:, receiving] += np.column_stack((-load, load))

    def tr(inductance, current, voltage):
        return peak(2 * (inductance * np.diff(current, axis=0) / step - midpoint(voltage)))

    line_tr = tr(line_l, line, rails[:, left] - rails[:, right] - line_r * line)
    feeder_tr = tr(feeder_l, feed, source - pcc - feeder_r * feed)
    filter_tr = tr(filter_l, phase, star + pcc - pole - filter_r * phase)
    charge = capacitance * np.diff(rails, axis=0) - step * midpoint(cap)

    def power(voltage, current):
        return np.sum(midpoint(voltage) * midpoint(current), axis=1)

    positive, negative = (np.repeat(rails[:, cols], 3, axis=1) for cols in ([0, 2], [3, 5]))
    load_v = rails[:, 2] - rails[:, 5]
    stored = .5 * (np.sum(capacitance * rails**2, axis=1) + line_l * np.sum(line**2, axis=1)
                   + filter_l * np.sum(phase**2, axis=1) + feeder_l * np.sum(feed**2, axis=1))
    supplied = power(supply, pre) + power(source, feed)
    loss = (power(supply - rails[:, sending], pre) + midpoint(load_v) * midpoint(load)
            + power(positive - pole, upper) + power(pole - negative, lower)
            + line_r * np.sum(midpoint(line)**2, axis=1) + feeder_r * np.sum(midpoint(feed)**2, axis=1)
            + filter_r * np.sum(midpoint(phase)**2, axis=1))
    energy = np.diff(stored) - step * (supplied - loss)
    values = {"kcl_a": max(peak(kcl), peak(feed - phase), peak(phase + upper - lower), peak(feed.reshape(-1, 2, 3).sum(axis=2))),
              "tr_line_voltage_v": line_tr, "tr_ac_voltage_v": max(feeder_tr, filter_tr),
              "tr_cap_charge_c": peak(charge), "tr_energy_j": max(peak(energy), peak(charge * midpoint(rails))),
              "abs_cumulative_energy_j": abs(float(np.sum(energy)))}
    gates = {name: value <= limits[name] for name, value in values.items()}
    return {"values": values, "checks": gates, "passed": all(gates.values())}


def power_series(trace, line_r):
    data = {"b_dc_mean_v": trace["bus_v"][:, 1]}
    for index, site in enumerate(STATIONS):
        phases = slice(3 * index, 3 * index + 3)
        voltage, current = (trace[key][:, phases] for key in ("pcc_v", "phase_a"))
        data[f"{site}_p_mean_w"] = np.sum(voltage * current, axis=1)
        # The cyclic voltage differences give positive Q for balanced lagging current.
        data[f"{site}_q_mean_var"] = np.sum((np.roll(voltage, -1, axis=1) - np.roll(voltage, 1, axis=1)) * current,
                                           axis=1) / np.sqrt(3.)
    rails, current = (trace[key] for key in ("rail_v", "line_a"))
    data["dc_sent_w"] = np.sum(rails[:, [0, 3]] * current[:, [0, 2]], axis=1)
    data["dc_received_w"] = np.sum(rails[:, [2, 5]] * current[:, [1, 3]], axis=1)
    data["dc_series_loss_w"] = line_r * np.sum(current**2, axis=1)
    return data


def power_windows(series, step, protocol):
    """Use half-open windows of original integer ticks, including their first sample."""
    criteria = protocol["long_window_acceptance"]
    result, checks = {}, {}
    for name, bounds in protocol["timing"]["power_windows_s"].items():
        lo, hi = (round(edge /  step) for edge in bounds)
        means = {key: float(np.mean(series[key][lo:hi])) for key in MEANS}
        result[name] = means
        checks.update({f"{name}.{key}": criteria[name][key][0] <= value <= criteria[name][key][1]
                       for key, value in means.items()})
        checks[f"{name}.b_active_direction"] = means["b_p_mean_w"] > 0 if name == "baseline" else means["b_p_mean_w"] < 0
        checks[f"{name}.positive_bipolar_power"] = means["dc_sent_w"] > 0 and means["dc_received_w"] > 0
    outer = protocol["control"]["outer"]
    start = round(outer["high_power_ramp_start_s"] / step)
    result[PEAK] = float(np.max(series["b_dc_mean_v"][start:]))
    result[RECOVERY] = abs(result["recovered"]["b_dc_mean_v"] - outer["station_b"]["dc_target_v"])
    checks[PEAK] = criteria[PEAK][0] <= result[PEAK] <= criteria[PEAK][1]
    checks[RECOVERY] = result[RECOVERY] <= criteria[RECOVERY]
    return result, checks


def compare_windows(candidate, reference, names, limits):
    differences = {name: {key: abs(candidate[name][key] - reference[name][key]) for key in MEANS} for name in names}
    differences[PEAK] = abs(candidate[PEAK] - reference[PEAK])
    passed = differences[PEAK] <= limits[PEAK] and all(
        error <= limits[key] for name in names for key, error in differences[name].items())
    return {"values": differences, "limits": limits, "passed": passed}


def timing(candidate, native, logs, grid, protocol, limits):
    """Check sample and application ticks, reference ramps and signed B-side feedback."""
    count = len(candidate["time_s"])
    j = np.arange(count)
    h = grid["step_s"]
    g, inner, outer = (grid[name] for name in ("gate_ticks", "inner_ticks", "outer_ticks"))
    sample = (j > 0) & (j % inner == 0)
    due = (j > 0) & (j % outer == 0)
    enabled = due[:, None] & (candidate["filtered_rms_v"] >= protocol["control"]["outer"]["minimum_pcc_rms_v"])
    pending_source = np.maximum(j // g * g - 1, 0)
    caps = protocol["control_acceptance"]
    ctrl = protocol["control"]["outer"]
    cap = protocol["physical_limits"]["control_recurrence"]
    upper_limit = protocol["control"]["current"]["phase_peak_reference_limit_a"]
    b_ctrl = ctrl["station_b"]
    pi = PIController(b_ctrl["voltage_pi_proportional"], b_ctrl["voltage_pi_integral"], -upper_limit, upper_limit)
    b_updates = np.flatnonzero(due)
    commands, integrators = [0.], [0.]
    for index in b_updates:
        command = pi.step(b_ctrl["dc_target_v"] - candidate["bus_v"][index, 1], ctrl["update_period_s"]) if enabled[index, 1] else 0.
        commands.append(command)
        integrators.append(pi.integrator)
    hold = np.searchsorted(b_updates, j, side="right")
    values = {"b_dc_request_a": peak(candidate["ip_ref_a"][:, 1] - np.asarray(commands)[hold]),
              "b_dc_integrator_a": peak(candidate["dc_integrator"][:, 1] - np.asarray(integrators)[hold]),
              "apply_next_gate_pu": peak(candidate["applied"] - candidate["pending"][pending_source])}
    checks = {"b_dc_request": values["b_dc_request_a"] <= cap, "b_dc_integrator": values["b_dc_integrator_a"] <= cap,
              "next_gate": values["apply_next_gate_pu"] <= limits["modulation_abs_pu"],
              "first_sample_tick": int(np.flatnonzero(sample)[0]) == inner,
              "first_applied_tick": inner + g == grid["first_gate_apply_tick"],
              "native_switch_shape": native["resistance"].shape == candidate["resistance"].shape}
    counts = {}
    for idx, site in enumerate(STATIONS):
        words = {"j": j, "gate_tick": j // g, "sample_update": sample, "outer_due": due, "outer_enabled": enabled[:, idx]}
        checks.update({f"{site}.{name}": bool(np.array_equal(candidate[name][:, idx], expected)) for name, expected in words.items()})
        first = peak(candidate["pending"][inner, idx * 3:idx * 3 + 3])
        low, high = caps["first_sample_pending_abs_peak_pu"]
        checks[f"{site}.first_pending"] = low <= first <= high
        checks[f"{site}.first_outer_enable"] = bool(np.flatnonzero(enabled[:, idx]).size and
                                                   abs(np.flatnonzero(enabled[:, idx])[0]*h - caps["first_enabled_outer_s"]) <= limits["clock_abs_s"])
        counts[site] = {"first_pending_peak_pu": first, "inner_updates": int(np.count_nonzero(candidate["sample_update"][:, idx])),
                        "outer_due": int(np.count_nonzero(candidate["outer_due"][:, idx]))}
        log = logs[site]
        for key in ("p_ref_w", "q_ref_var", "ip_ref_a", "iq_pcc_ref_a", "dc_integrator"):
            error = peak(candidate[key][1:, idx] - log[key])
            values[f"{site}.{key}"] = error
            checks[f"{site}.{key}_same_grid"] = error <= cap

    if g == 2:
        holds = np.arange(1, count, 2)
        checks["fine_midpoints"] = (len(holds) == limits["fine_midpoint_holds"]
            and np.array_equal(candidate["resistance"][holds], candidate["resistance"][holds-1])
            and np.array_equal(candidate["applied"][holds], candidate["applied"][holds-1]))
    a_outer = ctrl["station_a"]
    outer_time = (j // outer) * ctrl["update_period_s"]
    lo, hi = (ctrl[key] for key in ("setpoint_ramp_start_s", "setpoint_ramp_end_s"))
    high_lo, high_hi = (ctrl[key] for key in ("high_power_ramp_start_s", "high_power_ramp_end_s"))
    requested = (a_outer["p_end_w"] * np.clip((outer_time-lo) / (hi-lo), 0, 1)
                 + (a_outer["p_high_w"] - a_outer["p_end_w"]) * np.clip((outer_time-high_lo) / (high_hi-high_lo), 0, 1))
    values["a_p_ramp_w"] = peak(candidate["p_ref_w"][:, 0] - requested)
    checks["a_p_ramp"] = values["a_p_ramp_w"] <= cap
    current = candidate["line_a"][-1]
    intervals = [caps["final_positive_half_link_current_a"]] * 2 + [caps["final_negative_half_link_current_a"]] * 2
    checks["both_dc_rails"] = all(lo <= value <= hi for value, (lo, hi) in zip(current, intervals, strict=True))
    require(all(counts[site]["inner_updates"] == caps["inner_updates_per_station"]
                and counts[site]["outer_due"] == caps["outer_due_per_station"] for site in STATIONS), "Incomplete candidate sampling")
    return {"values": values, "checks": checks, "stations": counts, "final_line_currents_a": current.tolist(), "passed": all(checks.values())}
