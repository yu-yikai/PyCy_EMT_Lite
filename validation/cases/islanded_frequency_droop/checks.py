"""Check the island's physical laws, sampled droop and PSCAD comparisons in SI units."""

import math

import numpy as np

from validation.cases.grid_connected_vsc_open_loop.metrics import require
from validation.cases.two_terminal_vsc_hvdc.checks import midpoint, peak

PHASE_FIELDS = ("source_v", "pcc_v", "feeder_a", "base_a", "added_a")
WINDOW_FIELDS = ("power_w", "frequency_hz", "pcc_rms_v")


def report(checks, **measurements):
    flags = {name: bool(value) for name, value in checks.items()}
    return {"checks": flags, "passed": all(flags.values()), **measurements}


def lattice(trace, step, protocol):
    count = round(protocol["timing"]["duration_s"] / step) + 1
    same = protocol["same_grid"]
    for name in (*same["absolute_limits_si"], *same["exact_words"]):
        shape = (count, 3) if name in PHASE_FIELDS else (count,)
        require(trace[name].shape == shape and np.isfinite(trace[name]).all(), f"Invalid original lattice for {name}")
    return np.arange(count)


def pcc_power(trace):
    """Positive power flows from the source feeder to the island load."""
    return np.sum(trace["pcc_v"] * trace["feeder_a"], axis=1)


def window_measures(trace, step, protocol):
    power = pcc_power(trace)
    windows = {}
    for name, interval in protocol["timing"]["windows_s"].items():
        first, last = (round(edge / step) for edge in interval)
        take = slice(first, last)
        windows[name] = {
            "window_s": interval,
            "rows": last - first,
            "power_w": float(np.mean(power[take])),
            "frequency_hz": float(np.mean(trace["frequency_hz"][take])),
            "pcc_rms_v": float(np.sqrt(np.mean(trace["pcc_v"][take] ** 2))),
        }
    return windows


def evaluate(trace, step, protocol):
    """Use solved meter values from each row and both endpoints of every interval."""
    timing, fixture, controller = (protocol[key] for key in ("timing", "fixture", "controller"))
    row = lattice(trace, step, protocol)
    time = step * row
    load_on = row >= round(timing["load_step_s"] / step)
    load_r = np.where(load_on, fixture["added_load_ohm"], fixture["open_load_ohm"])
    r, inductance = fixture["feeder_ohm"], fixture["feeder_h"]
    source, pcc, feeder, base, added = (trace[name] for name in PHASE_FIELDS)
    theta, frequency, filtered = (trace[name] for name in ("phase_rad", "frequency_hz", "filtered_w"))

    ramp = .5 * (1 - np.cos(math.pi * np.minimum(time / timing["ramp_s"], 1)))
    amplitude = math.sqrt(2) * fixture["emf_phase_rms_v"] * ramp
    expected_source = amplitude[:, None] * np.sin(theta[:, None] + np.asarray(fixture["phase_shifts_rad"]))
    inductor_voltage = source - pcc - r * feeder
    stored = .5 * inductance * np.sum(feeder**2, axis=1)
    mean_feeder = midpoint(feeder)
    supplied = np.sum(midpoint(source) * mean_feeder, axis=1)
    # Across the switching row, use midpoint voltage and current from the two solves.
    losses = np.sum(r * mean_feeder**2 + midpoint(pcc) * midpoint(base + added), axis=1)
    energy = np.diff(stored) - step * (supplied - losses)
    physical = {
        "clock_abs_s": max(peak(trace["display_s"] - time), peak(trace["time_s"] - time),
                           peak(trace["display_s"] - trace["time_s"])),
        "source_command_abs_v": peak(trace["peak_v"] - amplitude),
        "source_wave_abs_v": peak(source - expected_source),
        "kcl_abs_a": peak(feeder - base - added),
        "load_ohm_abs_v": max(peak(pcc - fixture["base_load_ohm"] * base), peak(pcc - load_r[:, None] * added)),
        "feeder_tr_abs_v": peak(2 * (inductance * np.diff(feeder, axis=0) / step - midpoint(inductor_voltage))),
        "tr_energy_abs_j": peak(energy),
        "cumulative_energy_abs_j": peak(np.cumsum(energy)),
        "open_current_abs_a": peak(added[~load_on]),
    }

    power = pcc_power(trace)
    bias = controller["initial_power_w"]
    nominal = controller["nominal_hz"]
    weight = step / (controller["filter_tau_s"] + step)
    filter_increment = weight * (power[1:] - filtered[:-1])
    frequency_command = nominal - controller["droop_hz_per_w"] * (filtered - bias)
    angle_increment = math.tau * step * frequency[:-1]
    control = {
        "power_meter_abs_w": peak(trace["meter_w"] - power),
        "filter_recurrence_abs_w": max(peak(np.diff(filtered) - filter_increment), abs(filtered[0] - bias)),
        "droop_recurrence_abs_hz": max(peak(frequency - frequency_command), abs(frequency[0] - nominal)),
        "angle_recurrence_abs_rad": max(peak(np.diff(theta) - angle_increment), abs(theta[0] - controller["initial_phase_rad"])),
    }
    thresholds = protocol["physical_limits"]
    checks = {name: value <= thresholds[name] for name, value in physical.items()}
    checks.update({name: value <= protocol["control_limits"][name] for name, value in control.items()})
    checks.update(
        zero_clock=trace["display_s"][0] == trace["time_s"][0] == 0,
        load_words=np.array_equal(trace["load_on"], load_on) and np.array_equal(trace["load_resistance_ohm"], load_r),
        cold_start=max(peak(feeder[0] - controller["initial_feeder_current_a"]), peak(base[0]), peak(added[0]))
        <= thresholds["kcl_abs_a"] and peak(pcc[0]) <= thresholds["source_wave_abs_v"],
    )

    windows = window_measures(trace, step, protocol)
    before, after = (windows[name] for name in ("before", "after"))
    changes = {"power_increase_w": after["power_w"] - before["power_w"],
               "frequency_drop_hz": before["frequency_hz"] - after["frequency_hz"]}
    limits = protocol["window_limits"]
    for window, measures in windows.items():
        for name, (low, high) in limits[window].items():
            checks[f"{window}_{name}"] = low <= measures[name] <= high
    for name, value in changes.items():
        low, high = limits[name]
        checks[name] = low <= value <= high
    return report(checks, physical=physical, control=control, windows=windows, window_changes=changes,
                  rows_including_zero=len(row))


def same_grid(candidate, native, step, protocol):
    """Compare every original positive and zero row at the same electrical tick."""
    lattice(candidate, step, protocol)
    lattice(native, step, protocol)
    rules = protocol["same_grid"]
    limits = rules["absolute_limits_si"]
    maxima = {name: peak(candidate[name] - native[name]) for name in limits}
    checks = {name: value <= limits[name] for name, value in maxima.items()}
    checks.update({name: np.array_equal(candidate[name], native[name]) for name in rules["exact_words"]})

    actual = window_measures(candidate, step, protocol)
    reference = window_measures(native, step, protocol)
    windows = {}
    for window, measures in actual.items():
        differences = {name: measures[name] - reference[window][name] for name in WINDOW_FIELDS}
        windows[window] = {"candidate": measures, "native": reference[window], "differences": differences}
        for name, limit in rules["window_abs_limits"].items():
            checks[f"{window}_{name}"] = abs(differences[name]) <= limit
    return report(checks, maxima_si=maxima, windows=windows, rows_including_zero=len(candidate["time_s"]))


def cross_grid(coarse, fine, protocol):
    """Compare coincident rows and the two complete windows on their own grids."""
    h = protocol["grids"]["5us"]["step_s"]
    h_fine = protocol["grids"]["2p5us"]["step_s"]
    require(h == 2 * h_fine, "The fine lattice must contain all coarse ticks")
    row = lattice(coarse, h, protocol)
    lattice(fine, h_fine, protocol)
    limits = protocol["cross_grid_limits"]
    margin = round(limits["away_from_edge_margin_s"] / h)
    away = np.abs(row - round(protocol["timing"]["load_step_s"] / h)) > margin
    maxima = {"clock_abs_s": max(peak(coarse[key] - fine[key][::2]) for key in ("display_s", "time_s"))}
    checks = {"common_clock": maxima["clock_abs_s"] <= protocol["physical_limits"]["clock_abs_s"]}
    checks.update({name: np.array_equal(coarse[name], fine[name][::2]) for name in protocol["same_grid"]["exact_words"]})
    for name, field, take in (
        ("source_abs_v", "source_v", slice(None)), ("phase_abs_rad", "phase_rad", slice(None)),
        ("frequency_abs_hz", "frequency_hz", slice(None)), ("filtered_power_abs_w", "filtered_w", slice(None)),
        ("pcc_abs_v", "pcc_v", slice(None)), ("feeder_abs_a", "feeder_a", slice(None)),
        ("pcc_away_abs_v", "pcc_v", away), ("feeder_away_abs_a", "feeder_a", away),
    ):
        maxima[name] = peak(coarse[field][take] - fine[field][::2][take])
        checks[name] = maxima[name] <= limits[name]

    coarse_windows = window_measures(coarse, h, protocol)
    fine_windows = window_measures(fine, h_fine, protocol)
    differences = {}
    for window in coarse_windows:
        differences[window] = {}
        for name, field in (("window_power_abs_w", "power_w"), ("window_frequency_abs_hz", "frequency_hz"),
                            ("window_rms_abs_v", "pcc_rms_v")):
            value = abs(coarse_windows[window][field] - fine_windows[window][field])
            differences[window][name] = value
            checks[f"{window}_{name}"] = value <= limits[name]
    return report(checks, maxima_si=maxima, window_differences=differences, common_rows_including_zero=len(row),
                  away_rows=int(np.count_nonzero(away)), away_from_edge_margin_s=limits["away_from_edge_margin_s"])
