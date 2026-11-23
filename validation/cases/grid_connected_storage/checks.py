"""Check the single-station storage circuit in SI units."""

import math

import numpy as np

from validation.cases.two_terminal_vsc_hvdc.checks import midpoint, peak

PHASES = "abc"
VOLTAGE = ("bus_v", "pol_v", "ocv_v", "source_v", "pcc_v")
CURRENT = ("storage_a", "polar_r_a", "polar_cap_a", "bus_cap_a", "ocv_a", "feed_a", "phase_a")
DISCRETE = ("j", "gate_tick", "sample", "outer", "enabled", "saturation", "upper_on", "lower_on")
CONTROL = ("filtered_v", "ip_ref_a", "id_ref_a", "iq_ref_a", "theta_rad", "omega_rad_s")
WINDOWS = {
    "pcc_active_mean_w": "p_w", "pcc_reactive_mean_var": "q_var", "storage_absorbed_mean_w": "storage_w",
    "storage_absorbed_mean_a": "storage_a", "bus_mean_v": "bus_v", "polarization_mean_v": "pol_v",
}
CROSS = {
    "pcc_active_mean_abs_w": "pcc_active_mean_w", "pcc_reactive_mean_abs_var": "pcc_reactive_mean_var",
    "storage_power_mean_abs_w": "storage_absorbed_mean_w", "storage_current_mean_abs_a": "storage_absorbed_mean_a",
    "bus_mean_abs_v": "bus_mean_v", "polarization_mean_abs_v": "polarization_mean_v",
}


def power(trace):
    voltage, current = trace["pcc_v"], trace["phase_a"]
    cyclic = np.roll(voltage, -1, axis=1) - np.roll(voltage, 1, axis=1)
    return {"p_w": np.sum(voltage * current, axis=1), "q_var": np.sum(cyclic * current, axis=1) / math.sqrt(3),
            "storage_w": trace["bus_v"] * trace["storage_a"]}


def physics(trace, step, protocol):
    """Use the original endpoint pairs for the TR charge, voltage and energy checks."""
    dc, ac = protocol["dc_circuit"], protocol["ac_circuit"]
    r0, r1, cb, cp = (dc[k] for k in ("series_ohm", "polarization_ohm", "bus_cap_f", "polarization_cap_f"))
    rf, lf, rl, ll = (ac[k] for k in ("feeder_ohm", "feeder_h", "filter_ohm", "filter_h"))
    bus, pol, ocv = (trace[k] for k in ("bus_v", "pol_v", "ocv_v"))
    storage, polar_r, polar_c, bus_c, ocv_i, feed, phase = (trace[k] for k in CURRENT)
    source, pcc, pole, star = (trace[k] for k in ("source_v", "pcc_v", "pole_v", "star_v"))
    upper, lower = (trace[k] for k in ("upper_a", "lower_a"))

    def resistance(key):
        return np.where(trace[key], ac["bridge_closed_ohm"], ac["bridge_open_ohm"])

    high = bus[:, None] - pole
    kcl = (storage + bus_c + upper.sum(axis=1), storage - polar_r - polar_c, storage - ocv_i,
           bus_c + ocv_i + lower.sum(axis=1), feed - phase, phase + upper - lower, feed.sum(axis=1))
    ohm = (bus - pol - ocv - r0 * storage, pol - r1 * polar_r,
           high - resistance("upper_on") * upper, pole - resistance("lower_on") * lower)

    def tr_voltage(current, voltage, inductance):
        return peak(2 * (inductance * np.diff(current, axis=0) / step - midpoint(voltage)))

    charge = (cb * np.diff(bus) - step * midpoint(bus_c), cp * np.diff(pol) - step * midpoint(polar_c))

    def averaged_power(voltage, current):
        return np.sum(midpoint(voltage) * midpoint(current), axis=1)

    energy = .5 * (cb * bus**2 + cp * pol**2 + lf * np.sum(feed**2, axis=1) + ll * np.sum(phase**2, axis=1))
    # Across a switch transition use its measured endpoint voltages and currents.
    loss = (r0 * midpoint(storage)**2 + r1 * midpoint(polar_r)**2 + rf * np.sum(midpoint(feed)**2, axis=1)
            + rl * np.sum(midpoint(phase)**2, axis=1) + averaged_power(high, upper) + averaged_power(pole, lower))
    supplied = averaged_power(source, feed) - midpoint(ocv) * midpoint(ocv_i)
    residual = np.diff(energy) - step * (supplied - loss)
    values = {"clock_abs_s": peak(trace["time_s"] - np.arange(len(bus))*step), "kcl_abs_a": max(map(peak, kcl)),
              "ohm_abs_v": max(map(peak, ohm)), "cap_charge_abs_c": max(map(peak, charge)),
              "inductor_tr_abs_v": max(tr_voltage(feed, source - pcc - rf*feed, lf),
                                      tr_voltage(phase, star[:, None] + pcc - pole - rl*phase, ll)),
              "tr_energy_abs_j": peak(residual), "cumulative_energy_abs_j": peak(np.cumsum(residual))}
    return {"residuals": values, "checks": {key: value <= protocol["physics_limits"][key] for key, value in values.items()}}


def timing(trace, step, protocol):
    """Verify lattice, signed current request schedule, next-gate application and half-step holds."""
    schedule, limits = protocol["schedule"], protocol["continuation_limits"]
    j = np.arange(len(trace["time_s"]))
    g, inner, outer = (round(schedule[key] / step) for key in ("gate_period_s", "inner_period_s", "outer_period_s"))
    sample, due = (j > 0) & (j % inner == 0), (j > 0) & (j % outer == 0)
    gate, outer_index = j // g, j // outer

    def ramp(name):
        lo, hi = (round(edge / schedule["outer_period_s"]) for edge in schedule[name])
        return np.clip((outer_index - lo) / (hi - lo), 0, 1)

    start_p, end_p = (schedule[k] for k in ("charge_p_ref_w", "discharge_p_ref_w"))
    command = start_p * ramp("charge_ramp_s") + (end_p - start_p) * ramp("reversal_ramp_s")
    active = trace["p_ref_w"]
    negative = np.flatnonzero(active < 0)
    first_sample, first_apply = (round(schedule[key] / step) for key in ("first_sample_s", "first_gate_effect_s"))
    first_nonzero = np.flatnonzero(np.any(trace["applied"] != 0, axis=1))
    carrier_index = gate % 200
    carrier = (np.abs(carrier_index - 100) - 50) / 50
    upper = trace["applied"] >= carrier[:, None]
    midpoint_rows = j[j % g != 0]
    hold = all(np.array_equal(trace[key][midpoint_rows], trace[key][midpoint_rows-1]) for key in ("applied", "upper_on", "lower_on"))
    bus = trace["bus_v"][1:]
    metrics = {"inner_updates": int(np.count_nonzero(trace["sample"])), "outer_updates": int(np.count_nonzero(trace["outer"])),
               "fine_midpoint_holds": len(midpoint_rows), "command_max_abs_w": peak(active - command),
               "phase_peak_a": peak(trace["phase_a"][1:]), "bus_range_v": [float(bus.min()), float(bus.max())]}
    modulation_limit = protocol["same_grid_limits"]["modulation_abs_pu"]
    projected = trace["pending"][np.maximum(gate*g-1, 0)]
    gates = {
        "indices": np.array_equal(trace["j"], j) and np.array_equal(trace["gate_tick"], gate),
        "sample_ticks": np.array_equal(trace["sample"], sample) and metrics["inner_updates"] == schedule["inner_updates"],
        "outer_ticks": np.array_equal(trace["outer"], due) and metrics["outer_updates"] == schedule["outer_updates"],
        "outer_enable": np.array_equal(trace["enabled"], due & (trace["filtered_v"] >= schedule["pcc_min_filtered_rms_v"])),
        "signed_power_schedule": metrics["command_max_abs_w"] <= limits["p_command_abs_w"]
        and peak(trace["q_ref_var"] - schedule["q_ref_var"]) == 0
        and active[round(schedule["zero_crossing_tick_s"] / step)] == 0
        and bool(len(negative) and negative[0] == round(schedule["first_negative_tick_s"] / step)),
        "reference_radius": peak(np.hypot(trace["id_ref_a"], trace["iq_ref_a"])) <= schedule["max_current_request_peak_a"],
        "first_publication": bool(trace["sample"][first_sample] == 1 and len(first_nonzero) and first_nonzero[0] == first_apply),
        "gate_reference_delay": peak(trace["applied"] - projected) <= modulation_limit,
        "carrier_and_switches": np.array_equal(trace["upper_on"], upper) and np.array_equal(trace["lower_on"], ~upper),
        "midpoint_hold": hold and len(midpoint_rows) == (schedule["fine_midpoint_holds"] if g == 2 else 0),
        "phase_current": metrics["phase_peak_a"] <= limits["phase_current_abs_a_max"],
        "bus_voltage": limits["bus_voltage_v"][0] <= float(bus.min()) <= float(bus.max()) <= limits["bus_voltage_v"][1],
    }
    return {**metrics, "checks": {key: bool(value) for key, value in gates.items()}}


def signed_windows(trace, series, step, protocol):
    windows, checks = {}, {}
    observed = trace | series
    for name, bounds in protocol["windows_s"].items():
        lo, hi = (round(time / step) for time in bounds)
        values = {key: float(np.mean(observed[signal][lo:hi])) for key, signal in WINDOWS.items()}
        rules = protocol["signed_window_limits"][name]
        gates = {key: bounds[0] <= values[key] <= bounds[1] for key, bounds in rules.items() if isinstance(bounds, list)}
        gates["pcc_reactive_mean_abs_var_max"] = abs(values["pcc_reactive_mean_var"]) <= rules["pcc_reactive_mean_abs_var_max"]
        windows[name], checks[name] = values, gates
    return windows, checks


def cross_grid(coarse, fine, limits):
    deltas = {name: {key: abs(coarse[name][metric] - fine[name][metric]) for key, metric in CROSS.items()} for name in coarse}
    tests = {name: {key: value <= limits[key] for key, value in entries.items()} for name, entries in deltas.items()}
    return {"deltas": deltas, "checks": tests}
