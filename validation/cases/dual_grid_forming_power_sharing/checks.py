"""Check the two-source island and the original-grid comparisons in SI units."""

import math

import numpy as np

from validation.cases.grid_connected_vsc_open_loop.metrics import require
from validation.cases.two_terminal_vsc_hvdc.checks import midpoint, peak

STATIONS = "ab"
ROW_FIELDS = {
    (): ("display_s", "time_s", "peak_v", "load_r", "load_on"),
    (2,): ("phase_rad", "frequency_hz", "meter_w", "filtered_w"),
    (2, 3): ("source_v", "feeder_a"),
    (3,): ("pcc_v", "base_a", "added_a"),
}


def report(checks, **measurements):
    flags = {name: bool(value) for name, value in checks.items()}
    return {"checks": flags, "passed": all(flags.values()), **measurements}


def lattice(trace, step, protocol):
    count = round(protocol["timing"]["duration_s"] / step) + 1
    for tail, keys in ROW_FIELDS.items():
        for key in keys:
            require(trace[key].shape == (count, *tail) and np.isfinite(trace[key]).all(), f"Invalid original lattice for {key}")
    return np.arange(count)


def pcc_powers(trace):
    """Positive power flows from each source towards the common load bus."""
    return np.sum(trace["pcc_v"][:, None, :] * trace["feeder_a"], axis=2)


def phase_difference(trace):
    return trace["phase_rad"][:, 0] - trace["phase_rad"][:, 1]


def window_measures(trace, powers, step, protocol):
    windows = {}
    phase_ab = phase_difference(trace)
    for name, interval in protocol["timing"]["windows_s"].items():
        first, last = (round(time / step) for time in interval)
        take = slice(first, last)
        p_a, p_b = powers[take].T
        f_a, f_b = trace["frequency_hz"][take].T
        windows[name] = {
            "window_s": interval, "rows": last-first,
            "power_a_w": float(np.mean(p_a)), "power_b_w": float(np.mean(p_b)),
            "frequency_a_hz": float(np.mean(f_a)), "frequency_b_hz": float(np.mean(f_b)),
            "frequency_mean_hz": float(np.mean(trace["frequency_hz"][take])),
            "phase_difference_rad": float(np.mean(phase_ab[take])),
            "pcc_rms_v": float(np.sqrt(np.mean(trace["pcc_v"][take]**2))),
            "frequency_split_abs_hz": peak(f_a - f_b),
            "pointwise_sharing_abs_w": peak(p_a - 2*p_b),
            "power_ripple_abs_w": peak(np.ptp(powers[take], axis=0)),
        }
    return windows


def window_changes(windows):
    before, after = windows["before"], windows["after"]
    a, b = (after[key] - before[key] for key in ("power_a_w", "power_b_w"))
    return {"power_increase_a_w": a, "power_increase_b_w": b,
            "frequency_drop_hz": before["frequency_mean_hz"] - after["frequency_mean_hz"],
            "increment_sharing_abs_w": abs(a - 2*b)}


def evaluate(trace, step, protocol):
    """Check the solved circuit and each controller using all original electrical rows."""
    timing, fixture, controller = (protocol[key] for key in ("timing", "fixture", "controller"))
    rows = lattice(trace, step, protocol)
    t = step * rows
    load_on = rows >= round(timing["load_step_s"] / step)
    load_r = np.where(load_on, fixture["added_load_ohm"], fixture["open_load_ohm"])
    source, pcc, feeder, base, added = (trace[key] for key in ("source_v", "pcc_v", "feeder_a", "base_a", "added_a"))
    r, inductance = fixture["feeder_ohm"], fixture["feeder_h"]
    ramp = .5 * (1 - np.cos(math.pi * np.minimum(t / timing["ramp_s"], 1)))
    amplitude = math.sqrt(2) * fixture["emf_phase_rms_v"] * ramp
    angles = trace["phase_rad"][:, :, None] + np.asarray(fixture["phase_shifts_rad"])
    expected_source = amplitude[:, None, None] * np.sin(angles)

    power = pcc_powers(trace)
    load_power = np.sum(pcc * (base + added), axis=1)
    inductor_voltage = source - pcc[:, None, :] - r*feeder
    stored = .5 * inductance * np.sum(feeder**2, axis=(1, 2))
    mean_i = midpoint(feeder)
    supplied = np.sum(midpoint(source) * mean_i, axis=(1, 2))
    # Midpoint voltage and current come from the two solved endpoints of each interval.
    dissipated = r*np.sum(mean_i**2, axis=(1, 2)) + np.sum(midpoint(pcc) * midpoint(base + added), axis=1)
    energy = np.diff(stored) - step*(supplied - dissipated)
    physical = {
        "clock_abs_s": max(peak(trace["display_s"] - t), peak(trace["time_s"] - t), peak(trace["time_s"] - trace["display_s"])),
        "source_command_abs_v": peak(trace["peak_v"] - amplitude),
        "source_wave_abs_v": peak(source - expected_source),
        "kcl_abs_a": peak(feeder.sum(axis=1) - base - added),
        "load_ohm_abs_v": max(peak(pcc - fixture["base_load_ohm"]*base), peak(pcc - load_r[:, None]*added)),
        "feeder_tr_abs_v": peak(2 * (inductance*np.diff(feeder, axis=0)/step - midpoint(inductor_voltage))),
        "tr_energy_abs_j": peak(energy), "cumulative_energy_abs_j": peak(np.cumsum(energy)),
        "open_current_abs_a": peak(added[~load_on]), "pcc_power_abs_w": peak(power.sum(axis=1) - load_power),
    }
    checks = {key: value <= protocol["physical_limits"][key] for key, value in physical.items()}
    control = {}
    weight = step / (controller["filter_tau_s"] + step)
    nominal = controller["nominal_hz"]
    for i, site in enumerate(STATIONS):
        settings = controller["stations"][site]
        filtered, frequency, angle = (trace[key][:, i] for key in ("filtered_w", "frequency_hz", "phase_rad"))
        frequency_command = nominal - settings["droop_hz_per_w"] * (filtered - settings["reference_power_w"])
        control[site] = {
            "power_meter_abs_w": peak(trace["meter_w"][:, i] - power[:, i]),
            "filter_recurrence_abs_w": max(peak(np.diff(filtered) - weight*(power[1:, i] - filtered[:-1])),
                                           abs(filtered[0] - settings["initial_power_w"])),
            "droop_recurrence_abs_hz": max(peak(frequency - frequency_command), abs(frequency[0] - nominal)),
            "angle_recurrence_abs_rad": max(peak(np.diff(angle) - math.tau*step*frequency[:-1]),
                                            abs(angle[0] - controller["initial_phase_rad"])),
        }
        checks.update({f"{site}_{key}": value <= protocol["control_limits"][key] for key, value in control[site].items()})
    checks.update(zero_clock=trace["time_s"][0] == trace["display_s"][0] == 0,
                  exact_branch_schedule=np.array_equal(trace["load_on"], load_on) and np.array_equal(trace["load_r"], load_r),
                  cold_start=max(peak(feeder[0]-controller["initial_feeder_current_a"]), peak(base[0]), peak(added[0]))
                  <= protocol["physical_limits"]["kcl_abs_a"] and peak(pcc[0]) <= protocol["physical_limits"]["source_wave_abs_v"])

    windows = window_measures(trace, power, step, protocol)
    changes = window_changes(windows)
    limits = protocol["window_limits"]
    for name, values in windows.items():
        checks.update({f"{name}_{key}": low <= values[key] <= high for key, (low, high) in limits[name].items()})
        for key in ("frequency_split_abs_hz", "pointwise_sharing_abs_w", "power_ripple_abs_w"):
            checks[f"{name}_{key}"] = values[key] <= limits[key]
    for key in ("power_increase_a_w", "power_increase_b_w", "frequency_drop_hz"):
        low, high = limits[key]
        checks[key] = low <= changes[key] <= high
    checks["increment_sharing_abs_w"] = changes["increment_sharing_abs_w"] <= limits["increment_sharing_abs_w"]
    return report(checks, physical=physical, control=control, windows=windows, window_changes=changes, rows_including_zero=len(rows))


def same_grid(candidate, native, step, protocol):
    """Compare all original rows, including the load edge and the signed phase difference."""
    rows = lattice(candidate, step, protocol)
    lattice(native, step, protocol)
    limits = protocol["same_grid"]
    a = {**candidate, "phase_difference_rad": phase_difference(candidate)}
    b = {**native, "phase_difference_rad": phase_difference(native)}
    maxima = {key: peak(a[key].astype(float, copy=False) - b[key]) for key in limits["pointwise_max_abs"]}
    checks = {key: value <= limits["pointwise_max_abs"][key] for key, value in maxima.items()}
    a_windows, b_windows = (window_measures(trace, pcc_powers(trace), step, protocol) for trace in (a, b))
    differences = {}
    for name, values in a_windows.items():
        differences[name] = {key: abs(values[key] - b_windows[name][key]) for key in limits["window_max_abs"]}
        checks.update({f"{name}_{key}": value <= limits["window_max_abs"][key] for key, value in differences[name].items()})
    a_change, b_change = (window_changes(windows) for windows in (a_windows, b_windows))
    change_differences = {key: abs(a_change[key] - b_change[key]) for key in limits["window_change_max_abs"]}
    checks.update({key: value <= limits["window_change_max_abs"][key] for key, value in change_differences.items()})
    return report(checks, maxima_si=maxima, window_differences=differences, window_change_differences=change_differences,
                  rows_including_zero=len(rows))


def cross_grid(coarse, fine, protocol):
    """Compare coincident samples and use both complete grids for their window means."""
    h, h_fine = (protocol["grids"][name]["step_s"] for name in ("5us", "2p5us"))
    require(h == 2 * h_fine, "The fine lattice must contain all coarse ticks")
    rows = lattice(coarse, h, protocol)
    lattice(fine, h_fine, protocol)
    limits = protocol["cross_grid_limits"]
    common = {key: value[::2] for key, value in fine.items()}
    edge = round(protocol["timing"]["load_step_s"] / h)
    margin = round(limits["away_from_edge_margin_s"] / h)
    away = np.abs(rows - edge) > margin
    clock = max(peak(coarse[key] - common[key]) for key in ("time_s", "display_s"))
    checks = {"common_clock": clock <= protocol["physical_limits"]["clock_abs_s"],
              "command_words": all(np.array_equal(coarse[key], common[key]) for key in ("load_on", "load_r"))}
    peaks = {"phase_difference_abs_rad": peak(phase_difference(coarse) - phase_difference(common))}
    for name, key, take in (
        ("source_abs_v", "source_v", slice(None)), ("phase_abs_rad", "phase_rad", slice(None)),
        ("frequency_abs_hz", "frequency_hz", slice(None)), ("filtered_power_abs_w", "filtered_w", slice(None)),
        ("pcc_abs_v", "pcc_v", slice(None)), ("feeder_abs_a", "feeder_a", slice(None)),
        ("pcc_away_abs_v", "pcc_v", away), ("feeder_away_abs_a", "feeder_a", away),
    ):
        peaks[name] = peak(coarse[key][take] - common[key][take])
    checks.update({key: value <= limits[key] for key, value in peaks.items()})

    left, right = (window_measures(trace, pcc_powers(trace), step, protocol)
                   for trace, step in ((coarse, h), (fine, h_fine)))
    differences = {}
    for window, values in left.items():
        differences[window] = {}
        for name, fields in (("window_power_abs_w", ("power_a_w", "power_b_w")),
                             ("window_frequency_abs_hz", ("frequency_a_hz", "frequency_b_hz")),
                             ("window_rms_abs_v", ("pcc_rms_v",)), ("window_phase_difference_abs_rad", ("phase_difference_rad",))):
            value = max(abs(values[key] - right[window][key]) for key in fields)
            differences[window][name] = value
            checks[f"{window}_{name}"] = value <= limits[name]
    return report(checks, common_rows_including_zero=len(rows), clock_abs_s=clock, full_and_away_peaks=peaks,
                  window_differences=differences, away_from_edge_margin_s=limits["away_from_edge_margin_s"],
                  away_rows=int(np.count_nonzero(away)))
