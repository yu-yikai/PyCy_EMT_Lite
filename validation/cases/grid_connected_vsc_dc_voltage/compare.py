"""Run case 32 against the two qualified PSCAD DC load-step captures."""

import argparse
import json
import platform
import runpy
import subprocess
from dataclasses import replace
from datetime import UTC, datetime
from math import sqrt
from pathlib import Path

import numpy as np

from pycy_emt_lite import OutputOptions, run_case
from validation.cases.grid_connected_vsc_closed_loop import compare as current_loop
from validation.cases.grid_connected_vsc_open_loop import metrics
from validation.cases.grid_connected_vsc_open_loop.compare import save_json
from validation.cases.grid_connected_vsc_power_vac.checks import sequence
from validation.cases.grid_connected_vsc_power_vac.compare import INF_LINE
from validation.common.runner import sha256

ROOT = current_loop.ROOT
CACHE = ROOT / "local_reference"
EXAMPLE = ROOT / "examples/32_grid_connected_vsc_dc_voltage.py"
QUALIFIED = ROOT / "docs/development_roadmap/experiments/c1_dc_live_feedback_long_20261123.json"
QUALIFIED_SHA = "43c3f53a6750cc1f55a04b3ee204b2f30aa4aa46b8778c71ad8999c59fc7ff68"
GRIDS = {"5us": 5e-6, "2p5us": 2.5e-6}
PHASES = "abc"
GRID_VOLTAGES = tuple(f"grid_{phase}_v" for phase in PHASES)
POLE_VOLTAGES = tuple(f"pole_{phase}_v" for phase in PHASES)
PHASE_CURRENTS = tuple(f"phase_{phase}_a" for phase in PHASES)
DC_CURRENTS = ("capacitor_a", "base_load_a", "added_load_a", "precharge_a")
SWITCH_CURRENTS = tuple(f"{phase}_{side}_a" for phase in PHASES for side in ("upper", "lower"))
SWITCH_STATES = tuple(f"switch_{phase}_{side}" for phase in PHASES for side in ("upper", "lower"))
GATE_RESISTANCES = tuple(f"R_{phase}_{side}_ohm" for phase in PHASES for side in "ul")
NATIVE_CHANNELS = dict(zip(GRID_VOLTAGES + POLE_VOLTAGES + PHASE_CURRENTS + SWITCH_CURRENTS, (
    *(f"V_{phase}_grid_kV" for phase in PHASES), *(f"V_{phase}_pole_kV" for phase in PHASES),
    *(f"I_{phase}_phase_kA" for phase in PHASES),
    *(f"I_{phase}_{side}_kA" for phase in PHASES for side in ("upper", "lower")),
), strict=True)) | {
    "vdc_v": "Vdc_kV", "dc_p_v": "Vdc_p_kV", "dc_n_v": "Vdc_n_kV", "precharge_source_v": "Vs_kV",
    "capacitor_a": "Icap_kA", "base_load_a": "Ibase_kA", "added_load_a": "Istep_kA", "precharge_a": "Ipre_export_kA",
    "load_R_ohm": "R_load_ohm", "precharge_R_ohm": "R_pre_ohm", "absolute_time_s": "Absolute_TIME_s",
    **{f"applied_{phase}": f"ref_{phase}" for phase in PHASES}, **{name: name for name in GATE_RESISTANCES},
}
PLOT_FIELDS = ("time_s", "vdc_v", "id_a", "iq_a", "id_ref_a", "load_power_w")


def admit(path, expected, evidence):
    path = path.resolve(strict=True)
    metrics.require(path.is_relative_to(CACHE.resolve()), f"Native evidence is outside local_reference: {path}")
    if path not in evidence:
        evidence[path] = sha256(path)
    metrics.require(evidence[path] == expected, f"Changed native evidence: {path}")
    return path


def native_records(trial, label, count, protocol_hash, evidence):
    entries = trial["evidence"]
    paths = {key: admit(ROOT / item["path"], item["sha256"], evidence) for key, item in entries.items()}
    records = {key: json.loads(path.read_bytes()) for key, path in paths.items()
               if key in {"seed_receipt", "restart_receipt", "seed_terminal", "restart_terminal", "physics",
                          "controller", "windows", "audit_result", "native_bindings"}}
    for mode in ("seed", "restart"):
        receipt, terminal = (records[f"{mode}_{key}"] for key in ("receipt", "terminal"))
        folder = paths[f"{mode}_receipt"].parent
        metrics.require(receipt["status"] == "NATIVE_DC_FEEDBACK_LONG_RUN_READY_FOR_INDEPENDENT_REVIEW"
                        and receipt["mode"] == mode and receipt["variant"] == label
                        and receipt["protocol_sha256"] == protocol_hash and terminal["worker_returncode"] == 0
                        and terminal["stop_reason"] is None and terminal["source_hash_unchanged"] is True
                        and not terminal["remaining_owned"], f"Unclosed PSCAD {label} {mode}")
        metrics.require(all(receipt["files"][f'{receipt["generated_work"]}/{name}'] == digest
                            for name, digest in trial["shared_seed_restart_sha256"].items()),
                        f"Changed native storage or generated model: {label} {mode}")
        for name, digest in receipt["files"].items():
            admit(folder / name, digest, evidence)
    restart, audit = records["restart_receipt"], records["controller"]
    windows, physics = records["windows"], records["physics"]
    restart_hash = entries["restart_receipt"]["sha256"]
    metrics.require(restart["rows"] == restart["feedback_positive_rows"] == count
                    and restart["feedback_field_count"] == 37 and restart["feedback_export"] == "native_complete"
                    and audit["restart_receipt_sha256"] == windows["native_receipt_sha256"] == restart_hash
                    and audit["controller_logger_sha256"] == restart["files"][f'{restart["generated_work"]}/c1_dc_feedback.csv']
                    and records["audit_result"]["passed"] and audit["passed"] and windows["passed"]
                    and physics["status"] == "PASS_LIVE_DC_BRIDGE_LONG_PHYSICS" and all(physics["checks"].values())
                    and physics["bindings_sha256"] == entries["native_bindings"]["sha256"]
                    and physics["native_inputs_sha256"] == records["native_bindings"]
                    and physics["native_positive_rows"] == windows["native_rows"] == count,
                    f"Native full-grid admissions differ: {label}")
    return paths["restart_receipt"].parent / restart["generated_work"], records["seed_receipt"]["snapshot_row"], windows


def read_native(work, seed, variant, spec):
    """Keep original positive output times and insert the independently sealed seed row."""
    stem = "bridge_restart"
    info = (work / f"{stem}.inf").read_text("ascii").splitlines()
    channels = [INF_LINE.fullmatch(line.strip()) for line in info]
    metrics.require(len(channels) == 35 and all(channels) and all(int(row[1]) == s for s, row in enumerate(channels, 1)),
                    "Original PSCAD INF slots are incomplete")
    names = [row[2] for row in channels]
    metrics.require(set(names) == set(NATIVE_CHANNELS.values()) and set(seed) == {*names, "display_TIME_s"},
                    "Original PSCAD waveform roles or seed observation differ")
    columns = {}
    time = None
    count = variant["native_positive_rows"]
    for part in range(4):
        shard = names[part*10:(part+1)*10]
        data = np.loadtxt(work / f"{stem}_{part+1:02}.out", skiprows=1)
        metrics.require(data.shape == (count, len(shard)+1) and np.isfinite(data).all(), "Invalid original waveform shard")
        if time is None:
            time = data[:, 0].copy()
        else:
            metrics.require(np.array_equal(time, data[:, 0]), "Native PSCAD shard clocks differ")
        columns.update({name: np.r_[seed[name], data[:, i]] for i, name in enumerate(shard, 1)})
    trace = {key: columns[name] * (1000 if name.endswith(("_kV", "_kA")) else 1)
             for key, name in NATIVE_CHANNELS.items()}
    trace["time_s"] = np.r_[0., time]
    log = np.loadtxt(work / "c1_dc_feedback.csv", delimiter=",", usecols=(0, 1, 25, 26, 28, 33))
    snap = variant["absolute_snapshot_tick"] * variant["step_s"]
    metrics.require(log.shape == (count, 6) and np.isfinite(log).all() and np.array_equal(log[:, 0], np.arange(1, count+1))
                    and np.max(np.abs(log[:, 1]-trace["absolute_time_s"][1:])) <= spec["physical_gates"]["clock_s"]
                    and seed["display_TIME_s"] == seed["Absolute_TIME_s"], "Native control or anchor clock differs")
    for index, name in enumerate(("id_ref_a", "iq_ref_a", "sample_update", "outer_update"), 2):
        trace[name] = np.r_[0., log[:, index]]
    plant = spec["plant"]
    on, off = plant["switch_on_ohm"], plant["switch_off_ohm"]
    for state, resistance in zip(SWITCH_STATES, GATE_RESISTANCES, strict=True):
        r = trace[resistance]
        metrics.require(np.isin(r, (on, off)).all(), f"Invalid native actual resistance {resistance}")
        trace[state] = r == on
    trace["load_closed"] = trace["load_R_ohm"] == on
    metrics.require(np.isin(trace["load_R_ohm"], (on, off)).all() and (trace["precharge_R_ohm"] == off).all(),
                    "Native load/precharge switch state differs")
    expected = np.arange(count+1)*variant["step_s"]
    metrics.require(max(np.max(np.abs(trace["time_s"]-expected)),
                        np.max(np.abs(trace["absolute_time_s"]-snap-expected))) <= spec["physical_gates"]["clock_s"],
                    "Original PSCAD time differs from its anchored electrical grid")
    return trace


def candidate_trace(factory, variant, duration):
    case = factory(time_step=variant["step_s"], stop_time=duration)
    result = run_case(replace(case, output=OutputOptions(show_figure=False), plots=(), summary=None))
    mapping = dict(zip(GRID_VOLTAGES + POLE_VOLTAGES + PHASE_CURRENTS + DC_CURRENTS, (
        *(f"v:grid_{phase}" for phase in PHASES), *(f"v:pole_{phase}" for phase in PHASES),
        *(f"i:L{phase}" for phase in PHASES), "i:Cdc", "i:Rload", "i:Rstep", "i:Rpre",
    ), strict=True)) | {
        "time_s": "time", "vdc_v": "v:Cdc", "dc_p_v": "v:dc_p", "dc_n_v": "v:dc_n",
        "load_closed": "state:Sload", "id_ref_a": "id_ref", "iq_ref_a": "iq_ref",
        **{name: name for name in ("j", "sample_update", "outer_update", "dc_pi_integrator", "theta", "pll_omega",
                                  "pll_xi", "pll_error", "saturated", "carrier_applied", "z_d", "z_q",
                                  *(f"{state}_{p}" for state in ("applied", "pending") for p in PHASES))},
    }
    for phase_index, phase in enumerate(PHASES):
        for side_index, side in enumerate(("upper", "lower")):
            index = 2*phase_index+side_index
            name = f"S{phase}_{side}"
            mapping[SWITCH_STATES[index]] = f"state:{name}"
            mapping[SWITCH_CURRENTS[index]] = f"i:{name}"
    trace = {name: result.series(signal) for name, signal in mapping.items()}
    current_loop.check_clock({current_loop.TIME: trace["time_s"], **trace},
                             {"rows": variant["native_positive_rows"]+1, "step_s": variant["step_s"]})
    return trace


def add_metrics(trace):
    frequency = 60
    trace["id_a"], trace["iq_a"] = current_loop.rotating_frame(
        {current_loop.TIME: trace["time_s"], **trace}, PHASE_CURRENTS, frequency,
    )
    trace["grid_power_w"] = sum(trace[v]*trace[i] for v, i in zip(GRID_VOLTAGES, PHASE_CURRENTS, strict=True))
    trace["load_power_w"] = trace["vdc_v"]*(trace["base_load_a"] + trace["added_load_a"])
    for first, second in zip(PHASES, "bca", strict=True):
        trace[f"bridge_{first}{second}_v"] = trace[f"pole_{first}_v"] - trace[f"pole_{second}_v"]


def performance(trace, protocol):
    time = trace["time_s"]
    criteria = protocol["native_performance"]
    rows = {"pre": [], "post": []}
    sources, currents = (tuple(trace[name] for name in columns) for columns in (GRID_VOLTAGES, PHASE_CURRENTS))
    for stage, windows in rows.items():
        id_target, id_limit = criteria[f"mean_id_{stage}_target_and_tolerance_peak_a"]
        load_target, load_limit = criteria[f"mean_load_{stage}_target_and_tolerance_w"]
        for interval in protocol["windows"][stage]:
            keys = ("vdc_v", "id_a", "iq_a", "grid_power_w", "load_power_w")
            means = dict(zip(keys, current_loop.cycle_means(time, (trace[key] for key in keys), interval), strict=True))
            voltage, current = (sequence(time, phases, *interval) for phases in (sources, currents))
            means["grid_q1_var"] = float(1.5*(voltage*current.conjugate()).imag)
            gates = {
                "dc_voltage": abs(means["vdc_v"]-400) <= criteria["mean_dc_voltage_error_v"],
                "d_axis": abs(means["id_a"]-id_target) <= id_limit,
                "q_axis": abs(means["iq_a"]) <= criteria["mean_iq_max_abs_peak_a"],
                "load_power": abs(means["load_power_w"]-load_target) <= load_limit,
            }
            windows.append({"window_s": interval, "means": means, "checks": gates, "passed": all(gates.values())})
    time, voltage = metrics.clip(time, trace["vdc_v"], *protocol["windows"]["sag"])
    row = int(np.argmin(voltage))
    sag = {"time_s": float(time[row]), "vdc_v": float(voltage[row]),
           "passed": bool(voltage[row] >= criteria["post_load_minimum_v"])}
    return {"windows": rows, "sag_minimum": sag,
            "passed": sag["passed"] and all(report["passed"] for windows in rows.values() for report in windows)}


def physical(trace, variant, spec):
    """Verify fresh capacitor/line histories and native-style switching clocks."""
    plant, limits = spec["plant"], spec["physical_gates"]
    h = variant["step_s"]
    bus, capacitor = trace["vdc_v"], trace["capacitor_a"]
    phase = np.stack([trace[key] for key in PHASE_CURRENTS])
    upper, lower = (np.stack([trace[f"{p}_{side}_a"] for p in PHASES]) for side in ("upper", "lower"))
    phase_v = (np.stack([trace[key] for key in GRID_VOLTAGES]) - plant["phase_r_ohm"]*phase
               - np.stack([trace[key] for key in POLE_VOLTAGES]))
    capacitor_branch = sum(trace[key] for key in DC_CURRENTS)
    half_sum = (capacitor[1:]+capacitor[:-1])/2
    charge_error = plant["capacitance_f"]*np.diff(bus) - h*half_sum
    maxima = {
        "snapshot_vdc_v": abs(bus[0]-plant["target_dc_v"]), "snapshot_reactor_a": np.max(np.abs(phase[:, 0])),
        "differential_measurement_v": np.max(np.abs(bus-trace["dc_p_v"]+trace["dc_n_v"])),
        "kcl_a": max(np.max(np.abs(phase+upper-lower)), np.max(np.abs(capacitor_branch+np.sum(upper, axis=0))),
                     np.max(np.abs(capacitor_branch+np.sum(lower, axis=0)))),
        "phase_companion_v": np.max(np.abs(2*plant["phase_l_h"]/h*np.diff(phase)-phase_v[:, 1:]-phase_v[:, :-1])),
        "dc_tr_charge_c": np.max(np.abs(charge_error)),
        "dc_tr_energy_j": np.max(np.abs(charge_error*(bus[1:]+bus[:-1])/2)),
        "precharge_leakage_a": np.max(np.abs(trace["precharge_a"])),
    }
    checks = {key: float(value) <= limits[key] for key, value in maxima.items()}
    j = np.arange(len(bus))
    pairs = tuple((trace[f"switch_{p}_upper"], trace[f"switch_{p}_lower"]) for p in PHASES)
    checks.update(
        logical_rows=np.array_equal(trace["j"], j), load_event=np.array_equal(trace["load_closed"], j >= variant["relative_load_tick"]),
        complementary_gates=all(np.isin(upper, (0, 1)).all() and np.array_equal(upper+lower, np.ones_like(upper))
                                and upper[0] == 0 for upper, lower in pairs),
        inner_clock=np.array_equal(trace["sample_update"], (j>0) & (j % round(100e-6/h) == 0)),
        outer_clock=np.array_equal(trace["outer_update"], (j>0) & (j % round(.001/h) == 0)),
        load_current_limit=bool(np.all((trace["id_ref_a"] >= 0) & (trace["id_ref_a"] <= 5)) and np.all(trace["iq_ref_a"] == 0)),
    )
    return {"maxima": {key: float(value) for key, value in maxima.items()}, "checks": checks, "passed": all(checks.values())}


def same_step(candidate, native, protocol, candidate_metrics, native_metrics):
    """Compare matching original rows while keeping absolute-node voltages diagnostic."""
    limits = protocol["candidate_same_step"]
    time = candidate["time_s"]
    clock_error = np.abs(time-native["time_s"])
    worst = int(np.argmax(clock_error))
    clock = {"error_max_s": float(clock_error[worst]), "limit_s": 2e-12, "worst_row": worst,
             "candidate_time_s": float(time[worst]), "native_time_s": float(native["time_s"][worst]),
             "passed": bool(clock_error[worst] <= 2e-12)}
    exact = {}
    for key in (*SWITCH_STATES, "load_closed", "sample_update", "outer_update"):
        differing = np.flatnonzero(candidate[key] != native[key])
        exact[key] = {"passed": len(differing) == 0, "different_rows": len(differing),
                      "first_different_row": int(differing[0]) if len(differing) else None}

    def errors(key):
        delta = candidate[key]-native[key]
        peak = int(np.argmax(np.abs(delta)))
        return {"peak_abs": float(abs(delta[peak])), "rms_abs": sqrt(metrics.square_mean(time, delta)), "worst_row": peak}

    waveform = {}
    for keys, prefix in ((('vdc_v', 'bridge_ab_v', 'bridge_bc_v', 'bridge_ca_v'), "differential_vdc_and_line_to_line"),
                         (PHASE_CURRENTS + DC_CURRENTS + SWITCH_CURRENTS, "phase_and_branch_current")):
        units = "v" if prefix.startswith("differential") else "a"
        bound = {metric: limits[f"{prefix}_{metric}_{units}"] for metric in ("peak", "rms")}
        for key in keys:
            residual = errors(key)
            waveform[key] = {**residual, "limits": bound,
                             "passed": all(residual[f"{metric}_abs"] <= value for metric, value in bound.items())}
    windows = []
    bounds = {"grid_power_w": limits["window_power_w"], "load_power_w": limits["window_power_w"],
              "grid_q1_var": limits["window_fundamental_q_var"]}
    for stage in ("pre", "post"):
        for left, right in zip(candidate_metrics["windows"][stage], native_metrics["windows"][stage], strict=True):
            metrics.require(left["window_s"] == right["window_s"], "Mismatched frozen power window")
            residual = {key: abs(left["means"][key]-right["means"][key]) for key in bounds}
            windows.append({"window_s": left["window_s"], "absolute_errors": residual, "limits": bounds,
                            "passed": all(residual[key] <= cap for key, cap in bounds.items())})
    return {"passed": clock["passed"] and all(row["passed"] for row in (*exact.values(), *waveform.values(), *windows)),
            "clock": clock, "exact_states": exact, "waveforms": waveform, "power_windows": windows,
            "absolute_voltage_diagnostic": {name: errors(name) for name in ("dc_p_v", "dc_n_v", *POLE_VOLTAGES)}}


def frozen_inputs():
    qualified = current_loop.frozen_json(QUALIFIED, QUALIFIED_SHA)
    metrics.require(qualified["status"] == "BOTH_NATIVE_LONG_FEEDBACK_GRIDS_PASS", "Native DC reference is not qualified")
    protocol_record = qualified["protocol"]
    protocol_path = ROOT / protocol_record["path"]
    protocol = current_loop.frozen_json(protocol_path, protocol_record["sha256"])
    metrics.require(protocol["candidate_same_step"] == protocol_record["candidate_same_step"], "Frozen candidate criteria differ")
    record = protocol["short_reference"]
    short_path = ROOT / record["path"]
    short = current_loop.frozen_json(short_path, record["sha256"])
    record = short["protocol"]
    short_protocol_path = ROOT / record["path"]
    base = current_loop.frozen_json(short_protocol_path, record["sha256"])
    record = base["plant_protocol"]
    plant_path = ROOT / record["path"]
    plant = current_loop.frozen_json(plant_path, record["sha256"])
    return qualified, protocol, {**base, **plant}, (QUALIFIED, protocol_path, short_path, short_protocol_path, plant_path)


def run_comparison(destination, grids):
    qualified, protocol, spec, contracts = frozen_inputs()
    variants = {name: next(row for row in protocol["variants"] if row["step_s"] == GRIDS[name]) for name in grids}
    evidence = {}
    proof = qualified["cross_step"]["evidence"]
    paired = json.loads(admit(ROOT / proof["path"], proof["sha256"], evidence).read_bytes())
    metrics.require(paired["passed"] and paired["protocol_sha256"] == qualified["protocol"]["sha256"]
                    and paired["native_window_report_sha256"] == [qualified["trials"][key]["evidence"]["windows"]["sha256"]
                                                                  for key in GRIDS], "Original native cross-step verdict differs")
    native_inputs = {name: native_records(qualified["trials"][name], name, variant["native_positive_rows"],
                                          qualified["protocol"]["sha256"], evidence) for name, variant in variants.items()}
    snapshot = (EXAMPLE, Path(__file__), *contracts, ROOT / "pyproject.toml", ROOT / "uv.lock",
                *(ROOT / "pycy_emt_lite").rglob("*.py"), *(ROOT / "validation/common").rglob("*.py"),
                *(ROOT / "validation/cases/grid_connected_vsc_open_loop").rglob("*.py"),
                *(ROOT / "validation/cases/grid_connected_vsc_closed_loop").rglob("*.py"),
                *(ROOT / "validation/cases/grid_connected_vsc_power_vac").rglob("*.py"),
                *((Path(__file__).with_name("plots.py"),) if len(grids) == 2 else ()))
    hashes = current_loop.snapshot_inputs(destination, snapshot)
    manifest = destination / "inputs.json"
    save_json(manifest, {
        "git_head_before_run": subprocess.check_output(
            ["git", "-c", f"safe.directory={ROOT.as_posix()}", "rev-parse", "HEAD"], cwd=ROOT, text=True,
        ).strip(),
        "platform": platform.platform(), "python_version": platform.python_version(), "numpy_version": np.__version__,
        "sources": hashes, "reference_inputs": {path.relative_to(ROOT).as_posix(): digest for path, digest in evidence.items()},
    })
    factory = runpy.run_path(str(EXAMPLE))["define_case"]
    summaries, plots_candidate, plots_native = {}, {}, {}
    for label, variant in variants.items():
        print(f"Comparing {label}", flush=True)
        target = destination / label
        target.mkdir()
        work, seed, archived_windows = native_inputs[label]
        native = read_native(work, seed, variant, spec)
        add_metrics(native)
        native_metrics = performance(native, protocol)
        metrics.require(native_metrics["passed"] and archived_windows["passed"], f"Native windows failed readback: {label}")
        candidate = candidate_trace(factory, variant, protocol["relative_stop_s"])
        add_metrics(candidate)
        first, second = target / "candidate_waveforms.npz", target / "reference_waveforms.npz"
        np.savez(first, **candidate)
        np.savez(second, **native)
        candidate_metrics = performance(candidate, protocol)
        comparison = same_step(candidate, native, protocol, candidate_metrics, native_metrics)
        checks = physical(candidate, variant, spec)
        passed = comparison["passed"] and checks["passed"] and candidate_metrics["passed"]
        report = target / "report.json"
        save_json(report, {"passed": passed, "grid": variant, "same_step": comparison, "candidate_physics": checks,
                           "candidate_performance": candidate_metrics, "native_performance": native_metrics,
                           "waveforms_sha256": {artifact.name: sha256(artifact) for artifact in (first, second)}})
        summaries[label] = {"passed": passed, "report_sha256": sha256(report), "rows_with_initial": len(candidate["time_s"])}
        plots_candidate[label] = {name: candidate[name] for name in PLOT_FIELDS}
        plots_native[label] = {name: native[name] for name in PLOT_FIELDS}
        del candidate, native

    results = {"passed": all(row["passed"] for row in summaries.values()), "grids": summaries,
               "paired_run": len(grids) == 2, "reference_platform": qualified["native_platform"],
               "inputs_sha256": sha256(manifest)}
    if len(grids) == 2:
        from .plots import plot_comparison

        figure = destination / "waveform_overlay.png"
        plot_comparison(figure, plots_candidate, plots_native)
        results["figure_sha256"] = sha256(figure)
    metrics.require(all(sha256(ROOT / name) == digest for name, digest in hashes.items())
                    and all(sha256(path) == digest for path, digest in evidence.items()), "Comparison inputs changed during the run")
    report = destination / "report.json"
    save_json(report, results)
    return report, results["passed"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--grid", choices=GRIDS, help="Run one step for diagnosis. Omit for both steps.")
    parser.add_argument("--output", type=Path, help="Fresh directory under local_reference")
    args = parser.parse_args()
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    destination = (args.output or CACHE / f"case32_comparison_{stamp}").resolve()
    metrics.require(destination.is_relative_to(CACHE.resolve()) and destination != CACHE.resolve(), "Output must be below local_reference")
    destination.mkdir(parents=True, exist_ok=False)
    try:
        report, passed = run_comparison(destination, (args.grid,) if args.grid else tuple(GRIDS))
    except Exception as error:
        save_json(destination / "failure.json", {"passed": False, "exception": type(error).__name__, "message": str(error)})
        raise
    print(report, "PASS" if passed else "FAIL")
    return int(not passed)


if __name__ == "__main__":
    raise SystemExit(main())
