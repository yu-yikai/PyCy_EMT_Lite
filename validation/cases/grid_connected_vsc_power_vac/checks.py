"""Independent sampled-control and PCC performance checks for case 31."""

from math import pi, sqrt, tau

import numpy as np

from validation.cases.grid_connected_vsc_closed_loop import compare as inner
from validation.cases.grid_connected_vsc_open_loop import metrics

PCC = tuple(f"V_{phase}_pcc_kV" for phase in "abc")
TIME = inner.TIME
OUTER_FIELDS = (
    "pcc_theta", "pcc_d_filtered", "pcc_q_filtered", "outer_update", "p_ref_w",
    "ip_ref", "iq_pcc_ref", "vac_integrator", "id_ref", "iq_ref",
)
METRIC_LIMITS = {
    "pcc_v1_v_rms": "fundamental_voltage_delta_v_rms",
    "pcc_power_w": "active_power_delta_w",
    "pcc_q1_var": "fundamental_reactive_power_delta_var",
}


def replay_outer(data, observer, protocol, scenario, grid):
    """Recompute the filtered PCC voltage and held references from measured abc."""
    step = grid["step_s"]
    rows = np.arange(grid["rows"])
    control = protocol["control"]
    limits = protocol["native_gates"]
    inner_ticks = round(100e-6/step)
    outer_ticks = round(control["outer_update_period_s"]/step)
    angle = observer["theta"] + observer["pll_omega"] * (rows % inner_ticks) * step
    angle_error = (observer["pcc_theta"] - angle + pi) % tau - pi
    projected = inner.rotating_frame(data, PCC, 60, angle=angle).T
    filtered = np.zeros_like(projected)
    weight = step/.01
    for row in rows[1:]:
        filtered[row] = (filtered[row-1] + weight*projected[row])/(1+weight)
    updates = rows[outer_ticks::outer_ticks]
    active = (rows > 0) & (rows % outer_ticks == 0)
    metrics.require(np.array_equal(observer["outer_update"], active)
                    and len(updates) == protocol["acquisition"]["outer_update_per_run"], "Outer update clock differs")
    seen = [np.zeros(6)]
    z = 0.
    for tick, row in enumerate(updates, 1):
        vd, vq = filtered[row]
        magnitude = np.hypot(vd, vq)
        pref = control["power_reference_w"] * min(max((tick-120)/20, 0), 1)
        if magnitude < sqrt(2)*control["voltage_floor_v_rms_phase"]:
            seen.append([pref, 0., 0., z, 0., 0.])
            continue
        current_limit = control["current_reference_limit_a_peak"]
        ip = np.clip(pref/(1.5*magnitude), -current_limit, current_limit)
        iq = 0.
        if scenario == "regulated" and row >= round(control["voltage_control_enable_s"]/step):
            headroom = sqrt(max(current_limit**2-ip**2, 0.))
            error = control["voltage_reference_v_rms_phase"] - magnitude/sqrt(2)
            increment = 6*error*control["outer_update_period_s"]
            trial = z + increment
            request = .15*error + trial
            iq = np.clip(request, -headroom, headroom)
            if not ((request > headroom and increment > 0) or (request < -headroom and increment < 0)):
                z = trial
        seen.append([pref, ip, iq, z, (vd*ip-vq*iq)/magnitude, (vq*ip+vd*iq)/magnitude])
    held = np.searchsorted(updates, rows, side="right")
    ref = np.array(seen)[held]
    errors = {
        "pcc_theta": float(np.max(np.abs(angle_error))),
        "pcc_d_filtered": float(np.max(np.abs(observer["pcc_d_filtered"]-filtered[:, 0]))),
        "pcc_q_filtered": float(np.max(np.abs(observer["pcc_q_filtered"]-filtered[:, 1]))),
    }
    metrics.require(errors["pcc_theta"] <= limits["source_pll_angle_abs_rad"]
                    and max(errors[key] for key in ("pcc_d_filtered", "pcc_q_filtered")) <= limits["outer_replayed_filter_abs_v"],
                    f"PCC filter or row angle differs: {errors}")
    sample_indices = np.r_[0, updates][held]
    for column, key in enumerate(OUTER_FIELDS[4:]):
        value = observer[key]
        errors[key] = float(np.max(np.abs(value-ref[:, column])))
        cap = 0. if key == "p_ref_w" else limits["outer_replayed_current_or_integrator_abs_a"]
        metrics.require(errors[key] <= cap and np.array_equal(value, value[sample_indices]),
                        f"Outer {key} replay or hold differs (maximum error {errors[key]})")
    return ref[::inner_ticks, -2:], {"updates": len(updates), "maximum_absolute_errors": errors}


def sequence(time, signals, start, stop):
    complex_peaks = []
    rotation = np.exp(2j*pi/3)
    for signal in signals:
        sine, cosine = metrics.fundamental_coefficients(*metrics.clip(time, signal, start, stop))
        complex_peaks.append(complex(cosine, -sine))
    return (complex_peaks[0] + rotation*complex_peaks[1] + rotation**2*complex_peaks[2])/3


def performance(data, protocol, trial, scenario):
    """Keep original single cycles and qualify with the frozen common-period windows."""
    t = data[TIME]
    e, v, i = (np.stack([data[key] for key in names]) for names in (inner.VOLTAGES, PCC, inner.CURRENTS))
    power = np.sum(v*i, axis=0)
    omega = tau*60
    feeder = protocol["plant"]
    resistance, inductance = (feeder[key] for key in ("per_phase_feeder_r_ohm", "per_phase_feeder_l_h"))
    rules = trial["trial_rules"]
    original_limits = protocol["performance_gates"]
    limits = rules["each_coherent_window"]
    target = protocol["control"]["voltage_reference_v_rms_phase"]

    def endpoint(time):
        a, b, c = [np.interp(time, t, phase) for phase in i]
        return complex((2*a-b-c)/3, (b-c)/sqrt(3))*np.exp(-1j*omega*time)

    def evaluate(start, stop, held, coherent):
        v1, i1 = (sequence(t, signals, start, stop) for signals in (v, i))
        p = float(metrics.mean(*metrics.clip(t, power, start, stop)))
        rms, q = float(abs(v1)/sqrt(2)), float(1.5*(v1*i1.conjugate()).imag)
        fraction = float(np.dot(np.maximum(np.minimum(t[1:], stop)-np.maximum(t[:-1], start), 0),
                                data["saturated"][:-1])/(stop-start))
        values = {"window_s": [start, stop], "pcc_v1_v_rms": rms, "pcc_power_w": p, "pcc_q1_var": q,
                  "radial_limit_fraction": fraction}
        if coherent:
            boundary = inductance*(endpoint(stop)-endpoint(start))/(stop-start)
            residual = abs(v1-(sequence(t, e, start, stop)-complex(resistance, omega*inductance)*i1-boundary))
            values.update(feeder_endpoint_v_peak=float(abs(boundary)), complex_kvl_error_v_peak=float(residual))
            checks = {
                "power": abs(p-original_limits["pcc_power_target_w"]) <= limits["active_power_abs_error_w"],
                "voltage": (target-rms >= limits["held_sag_min_v_rms"] if held
                            else abs(rms-target) <= limits["regulated_v_abs_error_v_rms"]),
                "reactive": abs(q) <= limits["held_q_abs_max_var"] if held else q <= limits["regulated_q_max_var"],
                "endpoint": abs(boundary) <= limits["feeder_endpoint_term_max_v_peak"],
                "complex_kvl": residual <= limits["complex_reconstruction_error_max_v_peak"],
            }
        else:
            checks = {
                "power": abs(p-original_limits["pcc_power_target_w"]) <= original_limits["pcc_power_abs_error_w_each_cycle"],
                "voltage_direction": rms < target if held else True,
                "reactive": (abs(q) <= original_limits["held_q_abs_max_var_each_cycle"] if held
                             else q <= original_limits["regulated_q_max_var_each_settled_cycle"]),
                "radial_limit": fraction <= original_limits["radial_voltage_limit_max_fraction_each_cycle"],
            }
            values["original_voltage_gate_passed"] = (
                target-rms >= original_limits["held_sag_min_v_rms_each_cycle"] if held
                else abs(rms-target) <= original_limits["regulated_v_abs_error_v_rms_each_settled_cycle"]
            )
        return {**values, "checks": checks, "passed": all(checks.values())}

    cycles, coherent = {}, {}
    for stage, (start, stop) in original_limits["windows_s"].items():
        held = stage == "mid" or scenario == "held"
        cycles[stage] = [evaluate(start+k/60, stop if k == 2 else start+(k+1)/60, held, False) for k in range(3)]
        coherent[stage] = [evaluate(a, b, held, True) for a, b in rules["phase_windows_s"][stage]]
    return {"single_cycles": cycles, "coherent_windows": coherent,
            "passed": all(row["passed"] for table in (cycles, coherent) for group in table.values() for row in group)}


def compare_performance(left, right, limit):
    """Report absolute physical-measure differences in corresponding windows."""
    rows = []
    for a, b in zip(left, right, strict=True):
        metrics.require(a["window_s"] == b["window_s"], "Different physical measurement windows")
        peak = {key: abs(a[key]-b[key]) for key in limit}
        rows.append({"window_s": a["window_s"], "absolute_differences": peak,
                     "passed": all(value <= limit[key] for key, value in peak.items())})
    return rows
