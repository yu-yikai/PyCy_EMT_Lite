"""Frozen PJM5 circuit, initialization, and waveform comparisons in SI units."""

from math import sqrt, tau

import numpy as np


def peak(values):
    return float(np.max(np.abs(values)))


def midpoint(values):
    return (values[:-1] + values[1:]) / 2


def limit_checks(values, limits):
    return {name: values[name] is limit if isinstance(limit, bool) else values[name] <= limit
            for name, limit in limits.items()}


def endpoints(model):
    buses = model["buses"]
    return tuple(np.array([buses.index(line[key]) for line in model["lines"]]) for key in ("from_bus", "to_bus"))


def source_phase(model):
    source = model["source"]
    angles = np.deg2rad([source["phase_offsets_deg"][phase] for phase in "abc"])
    return sqrt(2) * source["phase_rms_v"], angles


def resistance(model, grid):
    load = model["added_load"]
    return np.where(np.arange(grid["rows_including_zero"]) >= grid["load_step_index"],
                    load["post_resistance_ohm"], load["pre_resistance_ohm"])


def physics(model, grid, trace, limits):
    """Audit all rows using KCL and each trapezoidal component equation."""
    t, v, i = (trace[key] for key in ("time_s", "voltage_v", "series_a"))
    load_r, load_l, step_i, source_i = (trace[key] for key in ("load_resistor_a", "load_inductor_a", "step_a", "source_a"))
    h = grid["step_s"]
    buses = model["buses"]
    source = buses.index(model["source"]["bus"])
    step = buses.index(model["added_load"]["bus"])
    loads = [buses.index(load["bus"]) for load in model["baseline_loads"]]
    start, end = endpoints(model)
    line_r, line_l, shunt_c = (np.array([line[key] for line in model["lines"]])[:, None]
                              for key in ("resistance_ohm", "inductance_h", "end_capacitance_f"))
    load_resistance, load_inductance = (np.array([load[key] for load in model["baseline_loads"]])[:, None]
                                      for key in ("resistance_ohm", "inductance_h"))
    voltage_peak, angles = source_phase(model)
    expected_voltage = voltage_peak * np.minimum(t[:, None] / model["source"]["ramp_s"], 1) * np.sin(
        tau * model["frequency_hz"] * t[:, None] + angles,
    )
    kcl = np.zeros_like(v)
    for line, (left, right) in enumerate(zip(start, end, strict=True)):
        kcl[:, left] -= trace["from_a"][:, line]
        kcl[:, right] -= trace["to_a"][:, line]
    kcl[:, loads] -= load_r + load_l
    kcl[:, step] -= step_i
    kcl[:, source] += source_i

    start_v, end_v = v[:, start], v[:, end]
    load_v, step_v = v[:, loads], v[:, step]
    capacitor_error = max(peak(shunt_c * np.diff(wave, axis=0) / h - midpoint(trace[key]))
                          for wave, key in ((start_v, "from_cap_a"), (end_v, "to_cap_a")))
    inductor_error = max(peak(2 * line_l * np.diff(i, axis=0) / h - 2 * midpoint(start_v - end_v - line_r * i)),
                         peak(2 * load_inductance * np.diff(load_l, axis=0) / h - 2 * midpoint(load_v)))
    stored = (np.sum(shunt_c * (start_v**2 + end_v**2) + line_l * i**2, axis=(1, 2))
              + np.sum(load_inductance * load_l**2, axis=(1, 2))) / 2
    supply = np.sum(midpoint(v[:, source]) * midpoint(source_i), axis=1)
    loss = (np.sum(line_r * midpoint(i)**2, axis=(1, 2))
            + np.sum(midpoint(load_v) * midpoint(load_r), axis=(1, 2))
            + np.sum(midpoint(step_v) * midpoint(step_i), axis=1))
    energy_error = np.diff(stored) - h * (supply - loss)
    values = {
        "clock_max_error_s": peak(t - h * np.arange(len(t))),
        "source_peak_error_v": peak(v[:, source] - expected_voltage),
        "max_kcl_a": peak(kcl),
        "max_resistive_ohm_v": max(peak(load_v - load_resistance * load_r),
                                  peak(step_v - trace["step_r_ohm"][:, None] * step_i)),
        "max_capacitor_tr_a": capacitor_error,
        "max_inductor_tr_v": inductor_error,
        "max_interval_energy_j": peak(energy_error),
        "abs_cumulative_energy_j": abs(float(np.sum(energy_error))),
        "stored_energy_at_zero_j": float(stored[0]),
        "abs_source_current_at_zero_a": peak(source_i[0]),
        "r_step_exact": np.array_equal(trace["step_r_ohm"], resistance(model, grid)),
    }
    checks = limit_checks(values, limits)
    return {"values": values, "checks": checks, "passed": all(checks.values())}


def window_values(model, trace, grid, windows):
    """Three-phase real power and bus-2 phase RMS on exact electrical ticks."""
    h = grid["step_s"]
    step = model["added_load"]["bus"]
    imports = {}
    for k, line in enumerate(model["lines"]):
        left, right = line["from_bus"], line["to_bus"]
        if step in (left, right):
            imports[f"{left}{right}"] = trace["from_a" if step == left else "to_a"][:, k]
    rows = []
    for stage, bounds in windows.items():
        for first, last in bounds:
            ticks = slice(round(first / h), round(last / h) + 1)
            bus = trace["voltage_v"][ticks, model["buses"].index(step)]

            def mean(values, duration=last - first):
                return float(np.trapezoid(values, dx=h) / duration)

            rows.append({"stage": stage, "window_s": [first, last],
                         "bus2_v_rms": sqrt(mean(np.mean(bus**2, axis=1))),
                         "path_import_w": {tag: mean(-np.sum(bus * current[ticks], axis=1)) for tag, current in imports.items()},
                         "added_load_w": mean(np.sum(bus * trace["step_a"][ticks], axis=1))})
    return rows


def compare_windows(left, right, limits):
    report = []
    for a, b in zip(left, right, strict=True):
        if a["window_s"] != b["window_s"] or a["stage"] != b["stage"]:
            raise ValueError("Window identities differ")
        paths = {tag: abs(value - b["path_import_w"][tag]) for tag, value in a["path_import_w"].items()}
        values = {"bus2_v_rms": abs(a["bus2_v_rms"] - b["bus2_v_rms"]),
                  "added_load_w": abs(a["added_load_w"] - b["added_load_w"]), "path_import_w": max(paths.values())}
        checks = limit_checks(values, limits)
        report.append({"window_s": a["window_s"], "stage": a["stage"], "absolute_errors": values,
                       "path_import_errors_w": paths, "checks": checks, "passed": all(checks.values())})
    return report


def initialization_offsets(model):
    source = model["source"]
    amplitude, angles = source_phase(model)
    slope = amplitude * np.sin(angles) / source["ramp_s"]
    ends = {
        side: np.array([line["end_capacitance_f"] if line[f"{side}_bus"] == source["bus"] else 0.
                        for line in model["lines"]])[:, None] * slope
        for side in ("from", "to")
    }
    return {"from_a": ends["from"], "to_a": ends["to"], "source_a": np.sum(ends["from"] + ends["to"], axis=0)}


def same_step(model, protocol, candidate, native):
    limits = protocol["candidate_same_grid_limits"]
    initial = protocol["source_capacitor_initialization"]
    offsets = initialization_offsets(model)
    raw = {key: candidate[key] - native[key] for key in limits}
    clock = peak(candidate["time_s"] - native["time_s"])
    waveform = {}
    for key, delta in raw.items():
        wave = {"raw_peak_abs": peak(delta), "raw_peak_by_phase": np.max(np.abs(delta), axis=0).tolist(),
                "limit": limits[key]}
        if key in offsets:
            offset = offsets[key]
            even_error, odd_error = peak(delta[::2] - offset), peak(delta[1::2] + offset)
            wave["peak_against_expected"] = max(even_error, odd_error)
            wave["predicted_initial_difference_a"] = offset.tolist()
            wave["raw_initial_difference_a"] = delta[0].tolist()
            wave["interval_average_current_error_a"] = peak(midpoint(delta))
            wave["passed"] = (wave["peak_against_expected"] <= limits[key]
                              and wave["interval_average_current_error_a"] <= initial["interval_average_current_abs_tol_a"])
        else:
            wave["passed"] = wave["raw_peak_abs"] <= limits[key]
        waveform[key] = wave

    initial_values = {"source_a": (candidate["source_a"][0], native["source_a"][0], offsets["source_a"])}
    for side in ("from", "to"):
        name = f"{side}_cap_a"
        initial_values[name] = (candidate[name][0], native[name][0], offsets[f"{side}_a"])
    zero_time = {name: {"candidate_error_a": peak(a - expected), "native_current_a": peak(b),
                        "passed": peak(a - expected) <= initial["candidate_initial_current_abs_tol_a"] and peak(b) == 0}
                 for name, (a, b, expected) in initial_values.items()}
    resistance_exact = np.array_equal(candidate["step_r_ohm"], native["step_r_ohm"])
    passed = (clock <= protocol["electrical_clock_tolerance_s"] and resistance_exact
              and all(row["passed"] for row in (*waveform.values(), *zero_time.values())))
    return {"clock_max_error_s": clock, "resistance_exact": resistance_exact, "waveforms": waveform,
            "zero_time_source_and_end_capacitors": zero_time, "passed": passed}


def cross_step(model, coarse, fine, windows, limits):
    time = coarse["time_s"]
    clock = peak(time - fine["time_s"][::2])
    away = np.abs(time - model["added_load"]["time_s"]) > limits["load_neighborhood_s"]
    waveform = {}
    for key in ("voltage_v", "series_a"):
        delta = coarse[key] - fine[key][::2]
        values = {"max_difference": peak(delta), "away_from_load_max": peak(delta[away])}
        checks = limit_checks(values, limits[key])
        waveform[key] = {"values": values, "checks": checks, "passed": all(checks.values())}
    power = compare_windows(windows["5us"], windows["2p5us"], limits["windows"])
    return {"clock_max_error_s": clock, "waveforms": waveform, "windows": power,
            "passed": clock <= limits["clock_max_error_s"] and all(row["passed"] for row in (*waveform.values(), *power))}
