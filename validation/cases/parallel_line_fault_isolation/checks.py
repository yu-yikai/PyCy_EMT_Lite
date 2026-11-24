"""Check the resistive three-bus circuit and its PSCAD comparisons in SI units."""

import math

import numpy as np

from validation.cases.grid_connected_vsc_open_loop.metrics import require
from validation.cases.two_terminal_vsc_hvdc.checks import peak

VOLTAGES = ("v_src", "v_recv", "v_fault")
CURRENTS = ("i_healthy", "i_sf", "i_rf", "i_fault", "i_load", "i_ref")
RESISTANCES = ("R_sf_ohm", "R_rf_ohm", "R_fault_ohm")
EDGES = ("fault_on_s", "open_sf_s", "open_rf_s", "fault_off_s", "reclose_s")


def report(checks, **measurements):
    flags = {name: bool(value) for name, value in checks.items()}
    return {"checks": flags, "passed": all(flags.values()), **measurements}


def lattice(trace, step, protocol):
    count = round(protocol["timing"]["duration_s"] / step) + 1
    for name in ("display_s", "time_s", *RESISTANCES, *VOLTAGES, *CURRENTS):
        shape = (count, 3) if name in (*VOLTAGES, *CURRENTS) else (count,)
        require(trace[name].shape == shape and np.isfinite(trace[name]).all(), f"Invalid original lattice for {name}")
    return np.arange(count)


def resistance_schedule(rows, step, timing, fixture):
    fault_on, open_sf, open_rf, fault_off, reclose = (round(timing[key] / step) for key in EDGES)
    opened, closed = fixture["open_ohm"], fixture["path_on_ohm"]
    sf = np.where((rows >= open_sf) & (rows < reclose), opened, closed)
    rf = np.where((rows >= open_rf) & (rows < reclose), opened, closed)
    fault = np.where((rows >= fault_on) & (rows < fault_off), fixture["fault_on_ohm"], opened)
    return sf, rf, fault


def analytic_nodes(source, fixture, sf_r, rf_r, fault_r):
    """Eliminate the two unknown nodes R and F independently for each phase."""
    healthy, load, reference = (1 / fixture[key] for key in ("healthy_ohm", "load_ohm", "reference_ohm"))
    sf, rf, fault = (1 / value for value in (sf_r, rf_r, fault_r))
    rr, ff = healthy + rf + load, sf + rf + fault + reference
    determinant = rr * ff - rf**2
    # [rr, -rf; -rf, ff] [V_R, V_F] = V_S [healthy, sf]
    recv = (healthy * ff + rf * sf) / determinant * source
    midpoint = (sf * rr + rf * healthy) / determinant * source
    currents = (healthy * (source - recv), sf * (source - midpoint), rf * (recv - midpoint),
                fault * midpoint, load * recv, reference * midpoint)
    return recv, midpoint, currents


def load_power(trace):
    return np.sum(trace["v_recv"] * trace["i_load"], axis=1)


def window_measures(trace, step, protocol):
    power = load_power(trace)
    windows = {}
    for name, interval in protocol["timing"]["windows_s"].items():
        first, last = (round(edge / step) for edge in interval)
        take = slice(first, last)
        source = trace["v_src"][take]
        source_rms = math.sqrt(np.mean(source**2))
        require(source_rms > 0, "Signed current projection needs a nonzero source in each window")
        signed = {f"{key}_signed_rms_a": float(np.mean(trace[f"i_{key}"][take] * source) / source_rms)
                  for key in ("healthy", "sf", "rf")}
        windows[name] = {"window_s": interval, "rows": last - first, **signed,
                         "recv_rms_v": float(np.sqrt(np.mean(trace["v_recv"][take]**2))),
                         "fault_rms_v": float(np.sqrt(np.mean(trace["v_fault"][take]**2))),
                         "fault_rms_a": float(np.sqrt(np.mean(trace["i_fault"][take]**2))),
                         "load_mean_w": float(np.mean(power[take]))}
    return windows


def evaluate(trace, step, protocol):
    """Verify solved resistances and conservation at each row including every edge."""
    fixture, timing = protocol["fixture"], protocol["timing"]
    rows = lattice(trace, step, protocol)
    time = step * rows
    controlled = resistance_schedule(rows, step, timing, fixture)
    sf_r, rf_r, fault_r = (value[:, None] for value in controlled)
    source, recv, midpoint = (trace[name] for name in VOLTAGES)
    currents = tuple(trace[name] for name in CURRENTS)
    i_healthy, i_sf, i_rf, i_fault, i_load, i_ref = currents
    phase = math.tau * fixture["frequency_hz"] * time[:, None] + np.asarray(fixture["phase_shifts_rad"])
    expected_source = math.sqrt(2) * fixture["emf_phase_rms_v"] * np.sin(phase)
    expected_recv, expected_midpoint, expected_currents = analytic_nodes(source, fixture, sf_r, rf_r, fault_r)

    resistances = (fixture["healthy_ohm"], sf_r, rf_r, fault_r, fixture["load_ohm"], fixture["reference_ohm"])
    drops = (source - recv, source - midpoint, recv - midpoint, midpoint, recv, midpoint)
    branches = tuple(zip(drops, resistances, currents, strict=True))
    ohm = max(peak(voltage - resistance * current) for voltage, resistance, current in branches)
    loss = sum(resistance * current**2 for _, resistance, current in branches)
    power = source * (i_healthy + i_sf) - loss
    physical = {
        "clock_abs_s": max(peak(trace["display_s"] - time), peak(trace["time_s"] - time),
                           peak(trace["display_s"] - trace["time_s"])),
        "source_abs_v": peak(source - expected_source),
        "kcl_abs_a": max(peak(i_healthy - i_rf - i_load), peak(i_sf + i_rf - i_fault - i_ref)),
        "ohm_abs_v": ohm,
        "power_abs_w": max(peak(power), peak(np.sum(power, axis=1))),
        "analytic_voltage_abs_v": max(peak(recv - expected_recv), peak(midpoint - expected_midpoint)),
        "analytic_current_abs_a": max(peak(value - expected) for value, expected in zip(currents, expected_currents, strict=True)),
    }
    checks = {name: value <= protocol["physical_limits"][name] for name, value in physical.items()}
    checks.update(zero_clock=trace["display_s"][0] == trace["time_s"][0] == 0,
                  resistance_words=all(np.array_equal(trace[name], value) for name, value in zip(RESISTANCES, controlled, strict=True)))

    windows = window_measures(trace, step, protocol)
    for window, measures in windows.items():
        for name, (lower, upper) in protocol["window_limits"][window].items():
            checks[f"{window}_{name}"] = lower <= measures[name] <= upper
    restored = {name: abs(windows["restored"][name] - windows["pre"][name]) for name in protocol["restored_abs_limits"]}
    checks.update({f"restored_vs_pre_{name}": value <= protocol["restored_abs_limits"][name] for name, value in restored.items()})
    edges = {}
    for name in EDGES:
        row = round(timing[name] / step)
        edges[name] = [{"row": index, "time_s": float(trace["time_s"][index]),
                        **{key: float(trace[key][index]) for key in RESISTANCES}} for index in (row - 1, row, row + 1)]
    return report(checks, physical=physical, windows=windows, restored_vs_pre_abs=restored, edge_rows=edges,
                  rows_including_zero=len(rows))


def same_grid(candidate, native, step, protocol):
    """Compare all same-tick native samples and the full frozen windows."""
    rows = lattice(candidate, step, protocol)
    lattice(native, step, protocol)
    rules = protocol["same_grid"]
    limits = {**rules["absolute_limits_si"], "instantaneous_load_power_abs_w": rules["instantaneous_load_power_abs_w"]}
    maxima = {name: peak(candidate[name] - native[name]) for name in rules["absolute_limits_si"]}
    maxima["instantaneous_load_power_abs_w"] = peak(load_power(candidate) - load_power(native))
    checks = {name: value <= limits[name] for name, value in maxima.items()}
    checks.update({name: np.array_equal(candidate[name], native[name]) for name in rules["exact_resistance_words"]})

    actual, reference = (window_measures(trace, step, protocol) for trace in (candidate, native))
    windows = {}
    for window, measures in actual.items():
        differences = {name: measures[name] - reference[window][name] for name in rules["window_abs_limits"]}
        windows[window] = {"candidate": measures, "native": reference[window], "differences": differences}
        checks.update({f"{window}_{name}": abs(value) <= rules["window_abs_limits"][name] for name, value in differences.items()})
    return report(checks, maxima_si=maxima, windows=windows, rows_including_zero=len(rows))


def cross_grid(coarse, fine, protocol):
    """Compare coincident times, retaining each full grid's window measurements."""
    h, h_fine = (protocol["grids"][key]["step_s"] for key in ("50us", "25us"))
    require(h == 2 * h_fine, "The fine lattice must contain the coarse ticks")
    rows = lattice(coarse, h, protocol)
    lattice(fine, h_fine, protocol)
    common = {name: values[::2] for name, values in fine.items()}
    clock = max(peak(coarse[key] - common[key]) for key in ("display_s", "time_s"))
    maxima = {"voltage_abs_v": max(peak(coarse[name] - common[name]) for name in VOLTAGES),
              "current_abs_a": max(peak(coarse[name] - common[name]) for name in CURRENTS),
              "power_abs_w": peak(load_power(coarse) - load_power(common))}
    checks = {name: value <= protocol["cross_grid_limits"][name] for name, value in maxima.items()}
    checks.update(common_clock=clock <= protocol["physical_limits"]["clock_abs_s"],
                  resistance_words=all(np.array_equal(coarse[name], common[name]) for name in RESISTANCES))
    coarse_windows, fine_windows = window_measures(coarse, h, protocol), window_measures(fine, h_fine, protocol)
    differences = {window: {name: abs(measures[name] - fine_windows[window][name])
                            for name in protocol["same_grid"]["window_abs_limits"]} for window, measures in coarse_windows.items()}
    return report(checks, common_row_maxima_si=maxima, clock_abs_s=clock, common_rows_including_zero=len(rows),
                  window_differences=differences)
