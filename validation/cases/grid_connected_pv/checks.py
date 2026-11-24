"""Check the PV circuit, its controller, and both PSCAD comparisons in SI units."""

import math

import numpy as np

from pycy_emt_lite.controls import (
    SRFPLL,
    FirstOrderLowPass,
    PIController,
    abc_to_dq,
    dq_to_abc,
)
from validation.cases.grid_connected_vsc_open_loop.metrics import require
from validation.cases.two_terminal_vsc_hvdc.checks import midpoint, peak

PHASES = "abc"
MEANS = {
    "export_mean_w": "export_w",
    "reactive_mean_var": "reactive_var",
    "pv_mean_power_w": "pv_power_w",
    "mean_bus_v": "bus_v",
    "mean_capacitor_current_a": "bus_cap_a",
}


def report(checks, **values):
    checks = {name: bool(value) for name, value in checks.items()}
    return {**values, "checks": checks, "passed": all(checks.values())}


def power(trace):
    voltage, current = trace["pcc_v"], trace["phase_a"]
    cyclic_voltage = voltage[:, [1, 2, 0]] - voltage[:, [2, 0, 1]]
    return {
        "export_w": -np.sum(voltage * current, axis=1),
        "reactive_var": np.sum(cyclic_voltage * current, axis=1) / math.sqrt(3),
        "pv_power_w": trace["bus_v"] * trace["pv_a"],
    }


def physics(trace, step, protocol):
    """Use every endpoint pair, including the saved origin and the irradiance change."""
    dc, ac = protocol["dc_circuit"], protocol["ac_circuit"]
    cap, resistance = dc["bus_cap_f"], dc["load_ohm"]
    rf, lf, rl, ll = (ac[key] for key in ("feeder_ohm", "feeder_h", "filter_ohm", "filter_h"))
    bus, pv, load, bus_cap = (trace[key] for key in ("bus_v", "pv_a", "load_a", "bus_cap_a"))
    source, pcc, pole, star = (trace[key] for key in ("source_v", "pcc_v", "pole_v", "star_v"))
    feed, phase, upper, lower = (trace[key] for key in ("feed_a", "phase_a", "upper_a", "lower_a"))
    # Native precharge injects its measured leakage at the bus. The candidate omits this branch.
    precharge = trace.get("pre_a", np.zeros_like(bus))
    admitted_rows = round(protocol["example"]["stop_s"] / step) + 1
    require(len(bus) == admitted_rows, "PV trace does not have the complete electrical lattice")

    closed, opened = (ac[f"bridge_{state}_ohm"] for state in ("closed", "open"))
    high_v = bus[:, None] - pole
    upper_r = np.where(trace["upper_on"], closed, opened)
    lower_r = np.where(trace["lower_on"], closed, opened)
    dc_in = pv + precharge - load - bus_cap
    kcl = (dc_in - upper.sum(axis=1), lower.sum(axis=1) - dc_in,
           feed - phase, phase + upper - lower, feed.sum(axis=1))
    ohm = (bus - resistance * load, high_v - upper_r * upper, pole - lower_r * lower)

    feeder_voltage = source - pcc - rf * feed
    filter_voltage = star[:, None] + pcc - pole - rl * phase
    feeder_tr = 2 * (lf * np.diff(feed, axis=0) / step - midpoint(feeder_voltage))
    filter_tr = 2 * (ll * np.diff(phase, axis=0) / step - midpoint(filter_voltage))
    charge = cap * np.diff(bus) - step * midpoint(bus_cap)

    def interval_power(voltage, current):
        return np.sum(midpoint(voltage) * midpoint(current), axis=1)

    # Use products of midpoint V and I. Averaging instantaneous power would change the
    # energy balance across PWM transitions, where the branch resistance changes.
    stored = .5 * (cap * bus**2 + lf * np.sum(feed**2, axis=1) + ll * np.sum(phase**2, axis=1))
    supplied = interval_power(source, feed) + midpoint(bus) * midpoint(pv + precharge)
    losses = (resistance * midpoint(load)**2 + rf * np.sum(midpoint(feed)**2, axis=1)
              + rl * np.sum(midpoint(phase)**2, axis=1)
              + interval_power(high_v, upper) + interval_power(pole, lower))
    energy = np.diff(stored) - step * (supplied - losses)
    values = {
        "clock_abs_s": peak(trace["time_s"] - np.arange(admitted_rows) * step),
        "kcl_abs_a": max(map(peak, kcl)),
        "ohm_abs_v": max(map(peak, ohm)),
        "cap_charge_abs_c": peak(charge),
        "inductor_tr_abs_v": max(peak(feeder_tr), peak(filter_tr)),
        "tr_energy_abs_j": peak(energy),
        "cumulative_energy_abs_j": peak(np.cumsum(energy)),
    }
    limits = protocol["physical_limits"]
    return report({key: values[key] <= limit for key, limit in limits.items()}, values=values)


def initial(candidate, native, grid, protocol):
    """Separate stored-state matching from the two ports' solved algebraic currents."""
    limits = protocol["initial_state"]
    ac_keys = ("feed_a", "phase_a")
    values = {
        "bus_snapshot_abs_v": max(abs(float(trace["bus_v"][0]) - grid["initial_bus_v"])
                                   for trace in (candidate, native)),
        "native_parked_ac_max_abs_a": max(peak(native[key][0]) for key in ac_keys),
        "matched_ac_max_abs_a": max(peak(candidate[key][0] - native[key][0]) for key in ac_keys),
        "pv_current_abs_a": abs(float(candidate["pv_a"][0] - native["pv_a"][0])),
        "capacitor_current_abs_a": abs(float(candidate["bus_cap_a"][0] - native["bus_cap_a"][0])),
    }
    checks = {
        "saved_bus": values["bus_snapshot_abs_v"] <= limits["bus_snapshot_tolerance_v"],
        "native_pv_current": abs(float(native["pv_a"][0]) - grid["native_initial_pv_current_a"])
        <= limits["ac_current_snapshot_tolerance_a"],
        "native_capacitor_current": abs(float(native["bus_cap_a"][0]) - grid["native_initial_capacitor_current_a"])
        <= limits["ac_current_snapshot_tolerance_a"],
        "native_parked_ac": values["native_parked_ac_max_abs_a"] <= limits["native_parked_current_approximation_bound_a"],
        "matched_ac": values["matched_ac_max_abs_a"] <= limits["ac_current_snapshot_tolerance_a"],
        "candidate_inductors_parked": all(peak(candidate[key][0] - limits["ac_inductor_current_a"])
                                          <= limits["ac_current_snapshot_tolerance_a"] for key in ac_keys),
        "pv_current": values["pv_current_abs_a"] <= limits["pv_and_capacitor_current_tolerance_a"],
        "capacitor_current": values["capacitor_current_abs_a"] <= limits["pv_and_capacitor_current_tolerance_a"],
        "parked_bridge": all(not np.any(trace["upper_on"][0]) and np.all(trace["lower_on"][0])
                             and peak(trace["source_v"][0]) <= protocol["physical_limits"]["ohm_abs_v"]
                             for trace in (candidate, native)),
    }
    return report(checks, values=values)


def controller_replay(trace, step, protocol, sample, outer):
    """Recompute PI and PLL states from the candidate's own solved feedback."""
    dc, ac = protocol["schedule"], protocol["ac_circuit"]
    limit = dc["current_request_abs_a"]
    nominal = math.tau * ac["frequency_hz"]
    pll = SRFPLL(100.0, 1000.0, nominal, protocol["initial_state"]["parked_pll_angle_rad"])
    d_filter, q_filter = (FirstOrderLowPass(dc["pcc_dq_filter_tau_s"]) for _ in range(2))
    dc_pi = PIController(dc["voltage_pi_kp"], dc["voltage_pi_ki"], -limit, limit)
    resistance = ac["feeder_ohm"] + ac["filter_ohm"]
    inductance = ac["feeder_h"] + ac["filter_h"]
    bandwidth = math.tau * 100.0
    d_pi, q_pi = (PIController(inductance * bandwidth, resistance * bandwidth) for _ in range(2))
    inner_period = dc["inner_period_s"]
    inner_ticks = round(inner_period / step)
    floor = dc["pcc_min_filtered_rms_v"] * math.sqrt(2)
    ip = 0.0
    id_ref = iq_ref = 0.0
    pending = (0.0, 0.0, 0.0)
    saturated = False
    names = ("filtered_d_v", "filtered_q_v", "filtered_rms_v", "ip_ref_a", "dc_integrator",
             "id_ref_a", "iq_ref_a", "pll_integrator", "d_integrator", "q_integrator", "theta_rad", "omega_rad_s")
    expected = np.zeros((len(sample), len(names)))
    expected[0, -2:] = pll.angle, pll.frequency
    expected_pending = np.zeros_like(trace["pending"], dtype=float)
    expected_saturation = np.zeros_like(sample)
    enabled = np.zeros_like(outer)
    feedback = (trace[key] for key in ("source_v", "pcc_v", "phase_a", "bus_v"))
    for j, (source, pcc, current, bus) in enumerate(zip(*feedback, strict=True)):
        if j == 0:
            continue
        if sample[j]:
            state = pll.step(tuple(source), inner_period)
        theta_row = pll.angle + pll.frequency * (j % inner_ticks) * step
        pd, pq = abc_to_dq(*pcc, theta_row)
        vd, vq = d_filter.step(pd, step), q_filter.step(pq, step)
        magnitude = math.hypot(vd, vq)
        if outer[j]:
            enabled[j] = magnitude >= floor
            ip = dc_pi.step(dc["dc_reference_v"] - bus, dc["outer_period_s"]) if enabled[j] else 0.0
            id_ref, iq_ref = (vd * ip / magnitude, vq * ip / magnitude) if enabled[j] else (0.0, 0.0)
        if sample[j]:
            measured_d, measured_q = abc_to_dq(*current, pll.angle)
            old_d, old_q = d_pi.integrator, q_pi.integrator
            ud = d_pi.step(id_ref - measured_d, inner_period)
            uq = q_pi.step(iq_ref - measured_q, inner_period)
            raw_d = state.d_axis_voltage + nominal * inductance * measured_q - ud
            raw_q = state.q_axis_voltage - nominal * inductance * measured_d - uq
            radius = .95 * bus / 2
            vector = math.hypot(raw_d, raw_q)
            saturated = vector > radius
            if saturated:
                raw_d, raw_q = raw_d * radius / vector, raw_q * radius / vector
                d_pi.integrator, q_pi.integrator = old_d, old_q
            pending = tuple(component / (bus / 2) for component in dq_to_abc(raw_d, raw_q, pll.angle))
        expected[j] = (vd, vq, magnitude / math.sqrt(2), ip, dc_pi.integrator, id_ref, iq_ref,
                       pll.integrator, d_pi.integrator, q_pi.integrator, pll.angle, pll.frequency)
        expected_pending[j] = pending
        expected_saturation[j] = saturated

    errors = {}
    for name, wanted in zip(names, expected.T, strict=True):
        difference = trace[name] - wanted
        if name == "theta_rad":
            difference = (difference + math.pi) % math.tau - math.pi
        errors[name] = peak(difference)
    errors["pending"] = peak(trace["pending"] - expected_pending)
    return enabled, expected_saturation, errors


def timing(trace, step, protocol):
    schedule, limits = protocol["schedule"], protocol["control_limits"]
    ac, dc = protocol["ac_circuit"], protocol["dc_circuit"]
    j = np.arange(len(trace["time_s"]))
    g, n_inner, n_outer = (round(schedule[key] / step) for key in ("gate_period_s", "inner_period_s", "outer_period_s"))
    gate = j // g
    sample, outer = (j > 0) & (j % n_inner == 0), (j > 0) & (j % n_outer == 0)
    midpoint_rows = j[j % g != 0]
    carrier = (np.abs(gate % 200 - 100) - 50) / 50
    applied, pending = trace["applied"], trace["pending"]
    upper = applied >= carrier[:, None]
    upper_on, lower_on = trace["upper_on"], trace["lower_on"]
    enabled, saturation, errors = controller_replay(trace, step, protocol, sample, outer)
    first_gate = np.flatnonzero(np.any(applied != 0, axis=1))
    first_enable = np.flatnonzero(enabled)
    held = all(np.array_equal(trace[key][midpoint_rows], trace[key][midpoint_rows-1])
               for key in ("applied", "upper_on", "lower_on"))
    switch_errors = int(np.count_nonzero(upper_on != upper) + np.count_nonzero(lower_on != ~upper))

    times = j * step
    rise_start, rise_end = schedule["source_ramp_s"]
    source_ramp = np.clip((times-rise_start) / (rise_end-rise_start), 0, 1)
    angles = math.tau * ac["frequency_hz"] * times[:, None] + np.array([0, -math.tau/3, math.tau/3])
    source = math.sqrt(2) * ac["phase_rms_v"] * source_ramp[:, None] * np.sin(angles)
    sunny, shaded = schedule["irradiance_w_m2"]
    irradiance = np.where(j >= round(schedule["irradiance_step_s"] / step), shaded, sunny)
    current = dc["norton_source_by_irradiance_a"]
    pv = np.where(irradiance == sunny, current[str(sunny)], current[str(shaded)]) - trace["bus_v"] / dc["string_shunt_ohm"]
    observed = power(trace)
    meter_error = max(peak(trace[key] - observed[name]) for key, name in (
        ("measured_export_w", "export_w"), ("measured_q_var", "reactive_var"), ("measured_pv_w", "pv_power_w")))
    bus = trace["bus_v"]
    source_error = peak(trace["source_v"] - source)
    port_error = peak(trace["pv_a"] - pv)
    applied_error = peak(applied - pending[np.maximum(gate*g-1, 0)])
    current_peak = max(peak(trace["ip_ref_a"]), peak(np.hypot(trace["id_ref_a"], trace["iq_ref_a"])))
    values = {
        "inner_samples": int(np.count_nonzero(sample)), "outer_samples": int(np.count_nonzero(outer)),
        "fine_midpoint_holds": len(midpoint_rows), "switch_mismatches": switch_errors,
        "applied_reference_abs_pu": applied_error, "controller_replay_abs": errors,
        "source_abs_v": source_error, "affine_port_abs_a": port_error, "power_meter_abs": meter_error,
        "current_request_peak_a": current_peak, "bus_min_v": float(bus.min()), "bus_max_v": float(bus.max()),
    }
    checks = {
        "indices": np.array_equal(trace["j"], j) and np.array_equal(trace["gate_tick"], gate),
        "inner_samples": np.array_equal(trace["sample"], sample) and values["inner_samples"] == schedule["inner_samples"],
        "outer_samples": np.array_equal(trace["outer"], outer) and values["outer_samples"] == schedule["outer_samples"],
        "enabled": np.array_equal(trace["enabled"], enabled) and len(first_enable) > 0
        and first_enable[0] == round(schedule["first_enabled_outer_s"] / step),
        "recurrence": max(errors.values()) <= limits["recurrence_abs"],
        "saturation": np.array_equal(trace["saturated"], saturation),
        "first_gate": len(first_gate) > 0 and first_gate[0] == round(schedule["first_nonzero_gate_s"] / step),
        "applied": applied_error <= limits["applied_reference_abs_pu"],
        "carrier": np.array_equal(trace["carrier"], carrier),
        "gate_words": switch_errors == limits["switch_mismatches_on_own_trajectory"],
        "fine_holds": held and len(midpoint_rows) == (schedule["fine_midpoint_holds"] if g == 2 else 0),
        "current_reference": current_peak <= schedule["current_request_abs_a"] + limits["recurrence_abs"],
        "source": source_error <= protocol["physical_limits"]["ohm_abs_v"],
        "irradiance": np.array_equal(trace["irradiance_w_m2"], irradiance),
        "affine_port": port_error <= protocol["physical_limits"]["kcl_abs_a"] and np.all(trace["pv_a"] > 0),
        "affine_domain": dc["affine_valid_bus_v"][0] <= bus.min() and bus.max() <= dc["affine_valid_bus_v"][1],
        "power_meters": meter_error <= limits["recurrence_abs"],
    }
    return report(checks, values=values)


def within(value, bounds):
    return bounds[0] <= value <= bounds[1]


def same_grid(candidate, native, step, protocol):
    """Compare the complete native positive lattice, then the frozen half-open windows."""
    limits = protocol["same_grid_limits"]
    behavior = protocol["export_behavior"]
    signals = dict(zip(("candidate", "native"), (trace | power(trace) for trace in (candidate, native)), strict=True))
    delta = {name: signals["candidate"][name][1:] - signals["native"][name][1:]
             for name in ("bus_v", "pv_a", "pv_power_w", "export_w", "reactive_var")}
    pointwise = {name: peak(values) for name, values in delta.items()}
    phase_peak = {name: peak(trace["phase_a"][1:]) for name, trace in signals.items()}
    peak_difference = abs(phase_peak["candidate"] - phase_peak["native"])
    clock = peak(candidate["time_s"] - native["time_s"])
    checks = {
        "clock": clock <= protocol["physical_limits"]["clock_abs_s"],
        "pointwise_bus": pointwise["bus_v"] <= limits["pointwise_bus_abs_v"],
        "pointwise_pv_current": pointwise["pv_a"] <= limits["pointwise_pv_current_abs_a"],
        "pointwise_pv_power": pointwise["pv_power_w"] <= limits["pointwise_pv_power_abs_w"],
        "phase_current_peak": peak_difference <= limits["phase_current_peak_abs_a"],
    }
    windows = {}
    for name, bounds in protocol["windows_s"].items():
        first, last = (round(t / step) for t in bounds)
        take = slice(first, last)
        quantities = {site: {key: float(np.mean(trace[signal][take])) for key, signal in MEANS.items()}
                      for site, trace in signals.items()}
        actual, reference = quantities["candidate"], quantities["native"]
        differences = {key: actual[key] - reference[key] for key in MEANS}
        activation = name == "activation"
        bus_tol = limits["activation_bus_mean_abs_v" if activation else "late_bus_mean_abs_v"]
        rules = behavior["activation"] if activation else behavior["late_windows"]
        power_ranges = rules if activation else rules[name]
        checks[f"{name}_behavior"] = (within(actual["export_mean_w"], power_ranges["export_mean_w"])
                                      and within(actual["pv_mean_power_w"], power_ranges["pv_mean_power_w"])
                                      and within(actual["mean_bus_v"], rules["mean_bus_v"])
                                      and abs(actual["reactive_mean_var"]) <= rules["reactive_mean_abs_var"])
        checks[f"{name}_export"] = abs(differences["export_mean_w"]) <= limits["anchor_window_export_abs_w"]
        checks[f"{name}_q"] = abs(differences["reactive_mean_var"]) <= limits["anchor_window_reactive_abs_var"]
        checks[f"{name}_bus"] = abs(differences["mean_bus_v"]) <= bus_tol
        window = {**quantities, "differences": differences, "window_s": bounds, "rows": last-first}
        if not activation:
            checks[f"{name}_cap_current"] = abs(actual["mean_capacitor_current_a"]) <= rules["mean_capacitor_current_abs_a"]
            phase = candidate["phase_a"][take]
            reference_phase = native["phase_a"][take]
            rms_difference = np.sqrt(np.mean(phase**2, axis=0)) - np.sqrt(np.mean(reference_phase**2, axis=0))
            angles = np.exp(-1j * math.tau * protocol["ac_circuit"]["frequency_hz"] * np.arange(first, last) * step)
            fundamental = angles @ phase
            reference_fundamental = angles @ reference_phase
            angle_difference = np.angle(fundamental * reference_fundamental.conj(), deg=True)
            checks[f"{name}_phase_rms"] = peak(rms_difference) <= limits["late_phase_current_rms_abs_a"]
            checks[f"{name}_fundamental_angle"] = (np.all(np.abs(fundamental) > 0) and np.all(np.abs(reference_fundamental) > 0)
                                                   and peak(angle_difference) <= limits["late_fundamental_angle_abs_deg"])
            window.update(phase_rms_difference_a=rms_difference.tolist(), fundamental_angle_difference_deg=angle_difference.tolist())
        windows[name] = window

    drops = {site: windows["before"][site]["export_mean_w"] - windows["after"][site]["export_mean_w"] for site in signals}
    checks["export_drop_behavior"] = within(drops["candidate"], behavior["late_windows"]["export_drop_w"])
    checks["export_drop_difference"] = abs(drops["candidate"] - drops["native"]) <= limits["export_drop_abs_w"]

    blocks = limits["three_cycle_windows"]
    start, stop, width = (round(blocks[name] / step) for name in ("start_s", "stop_s", "width_s"))
    three_cycle = {}
    for key, limit in (("export_w", "export_mean_abs_w"), ("reactive_var", "reactive_mean_abs_var")):
        differences = delta[key][start-1:stop-1].reshape(-1, width).mean(axis=1)
        three_cycle[key] = {"signed_means": differences.tolist(), "max_abs": peak(differences)}
        checks[f"three_cycle_{key}"] = three_cycle[key]["max_abs"] <= blocks[limit]
    switches = {name: [int(x) for x in np.count_nonzero(candidate[name][1:] != native[name][1:], axis=0)]
                for name in ("upper_on", "lower_on")}
    return report(checks, windows=windows, clock_abs_s=clock, positive_rows=len(delta["bus_v"]),
                  pointwise_max_abs=pointwise, pointwise_rms={key: float(np.sqrt(np.mean(x**2))) for key, x in delta.items()},
                  phase_current_peak_a=phase_peak, phase_current_peak_difference_a=peak_difference,
                  export_drop_w=drops, three_cycle_differences=three_cycle, cross_platform_switch_differences=switches)


def cross_grid(coarse, fine, protocol):
    """Check numerical resolution from the two candidate three-cycle plateaus."""
    limits = protocol["candidate_cross_grid_late_limits"]
    fields = {"export_mean_abs_w": "export_mean_w", "reactive_mean_abs_var": "reactive_mean_var",
              "pv_power_mean_abs_w": "pv_mean_power_w", "bus_mean_abs_v": "mean_bus_v"}
    differences = {}
    for window in ("before", "after"):
        left, right = (item["windows"][window]["candidate"] for item in (coarse, fine))
        differences[window] = {name: abs(left[key] - right[key]) for name, key in fields.items()}
    return report({f"{window}_{name}": value <= limits[name] for window, values in differences.items()
                   for name, value in values.items()}, differences=differences)
