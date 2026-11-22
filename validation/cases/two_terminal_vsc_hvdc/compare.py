"""Compare Example 34 with both qualified original PSCAD long runs."""

import argparse
import json
import platform
import runpy
import subprocess
from dataclasses import replace
from datetime import UTC, datetime
from operator import itemgetter
from pathlib import Path

import numpy as np

from pycy_emt_lite import OutputOptions, run_case
from validation.cases.grid_connected_vsc_closed_loop.compare import (
    ROOT,
    frozen_json,
    snapshot_inputs,
)
from validation.cases.grid_connected_vsc_open_loop.compare import save_json
from validation.cases.grid_connected_vsc_open_loop.metrics import require
from validation.cases.grid_connected_vsc_power_vac.compare import INF_LINE
from validation.cases.pjm5_load_step.compare import admit, record_path
from validation.common.runner import sha256

from . import checks

DIRECTORY = Path(__file__).resolve().parent
PROTOCOL = DIRECTORY / "candidate_protocol.json"
PROTOCOL_SHA = "208813716603912293cd0d4bc68a12aed9c6562e8feaed74904c1e1e089a1014"
CACHE = ROOT / "local_reference"
GRIDS = ("5us", "2p5us")
PHASES, RAILS, LINKS, SITES = checks.PHASES, checks.RAILS, checks.LINKS, checks.STATIONS
GATES = tuple((site, phase, side) for site in SITES for phase in "abc" for side in ("upper", "lower"))
NATIVE = {
    "rail_v": tuple(f"V_{rail}_kV" for rail in RAILS), "bus_v": tuple(f"V_{site}_dc_kV" for site in SITES),
    "pcc_v": tuple(f"V_{phase}_pcc_kV" for phase in PHASES), "line_a": tuple(f"I_link_{link}_kA" for link in LINKS),
    "phase_a": tuple(f"I_{phase}_phase_kA" for phase in PHASES), "feeder_a": tuple(f"I_{phase}_feeder_kA" for phase in PHASES),
    "applied": tuple(f"Ref_{phase}_pu" for phase in PHASES),
    "resistance": tuple(f"R_{site}_{phase}_{side}_ohm" for site, phase, side in GATES),
    "cap_a": tuple(f"I_cap_{rail}_kA" for rail in RAILS), "pole_v": tuple(f"V_{phase}_pole_kV" for phase in PHASES),
    "star_v": tuple(f"V_{site}_star_kV" for site in SITES), "upper_a": tuple(f"I_{phase}_upper_kA" for phase in PHASES),
    "lower_a": tuple(f"I_{phase}_lower_kA" for phase in PHASES), "pre_a": ("I_pre_p_kA", "I_pre_n_kA"),
    "supply_v": ("V_pre_p_kV", "V_pre_n_kV"), "load_a": ("I_load_kA",),
    "r_pre": ("R_pre_ohm",), "r_load": ("R_load_ohm",), "absolute_s": ("Absolute_TIME_s",),
}
NATIVE_STATUS = "NATIVE_D1_DUAL_VSC_LONG_RUN_CLOSED_FOR_NUMERIC_REVIEW"
GENERATED = ("Main.f", "Main.dta", "Station.f", "Station.dta")
LOG_SIGNALS = ("j", "time_s", "p_ref_w", "q_ref_var", "ip_ref_a", "iq_pcc_ref_a", "dc_integrator")


def admit_run(record, name, mode, protocol, protocol_sha, evidence):
    path = record_path(record, evidence)
    run = path.parent
    require(run.is_relative_to(CACHE.resolve()), "Native archive must remain below local_reference")
    receipt = json.loads(path.read_bytes())
    variant, contract = protocol["grids"][name], protocol["native_execution"]
    count = variant["seed_rows_including_zero" if mode == "seed" else "restart_rows"]
    logs_count = variant["seed_tail_rows" if mode == "seed" else "restart_rows"]
    stop = protocol["timing"]["seed_stop_s" if mode == "seed" else "restart_duration_s"]
    require(receipt["status"] == NATIVE_STATUS and receipt["protocol_sha256"] == protocol_sha
            and (receipt["variant"], receipt["mode"], receipt["rows"], receipt["step_s"], receipt["stop_s"]) ==
            (name, mode, count, variant["step_s"], stop) and receipt["stem"] == contract["raw_stem"],
            f"Original {name} {mode} receipt identity differs")
    artifacts = {key: admit(run / key, digest, evidence) for key, digest in receipt["files"].items()}
    require(all(path.is_relative_to(run) for path in artifacts.values()), "Native receipt resolves outside its run")
    terminal, admission, inputs = (json.loads(artifacts[key].read_bytes()) for key in
        ("terminal.json", "pre_run_admission.json", "sealed_inputs.json"))
    require(terminal["worker_returncode"] == 0 and terminal["stop_reason"] is None and not terminal["remaining_owned"]
            and not terminal["cleanup"] and terminal["source_hash_unchanged"] and terminal["parent_environment_unchanged"],
            "Unclosed or dirty PSCAD session")
    require(all(receipt[field] == receipt["files"][key] for field, key in (
        ("terminal_sha256", "terminal.json"), ("pre_run_admission_sha256", "pre_run_admission.json"),
        ("sealed_inputs_sha256", "sealed_inputs.json"))), "Unbound original execution/admission receipt")
    require(admission["pscx_sha256"] == receipt["files"]["project/vdiv.pscx"]
            and admission["proof"]["status"] == "PASS_NATIVE_D1_DUAL_VSC_ACTIVE_COMPILED_ADMISSION"
            and admission["proof"]["physical_branches"] == 45 and admission["native_pgb_layout"] == receipt["native_pgb_layout"],
            "Missing admitted native topology and signal layout")
    require(all(path.name == path.as_posix() for path in map(Path, inputs)), "Unexpected sealed native input path")
    for key, digest in inputs.items():
        admit(run / "input_snapshot" / key, digest, evidence)
    work = run / receipt["generated_work"]
    require(work.resolve() == run / "project/vdiv.gf46", "Native generated project location differs")
    require(all(receipt["files"][f'{receipt["generated_work"]}/{key}'] == digest
                for group in ("post_run_generated_sha256", "raw_files_sha256") for key, digest in receipt[group].items()),
            "Raw/generated file hashes differ from native execution receipt")
    require(receipt["native_log_columns"] == contract["log_columns"] and set(receipt["native_logs"]) == set(SITES),
            "Native per-station log ABI differs")
    for site, item in receipt["native_logs"].items():
        require((item["file"], item["rows"], item["columns"], item["sha256"]) ==
                (contract["log_filenames"][site], logs_count, len(contract["log_columns"]),
                 receipt["files"][f'{receipt["generated_work"]}/{item["file"]}']), "Original native controller log binding differs")
    require(receipt["snapshot_sha256"] == receipt["files"][receipt["snapshot_path"]], "Changed original native snapshot")
    return {"receipt": receipt, "work": work, "admission": admission, "inputs": inputs}


def qualified_grid(qualified, name, protocol, protocol_sha, conditioned, evidence):
    source = qualified["grids"][name]
    seed, restart = (admit_run(source["original_runs"][mode], name, mode, protocol, protocol_sha, evidence)
                     for mode in ("seed", "restart"))
    review_path = record_path(source["independent_audit"], evidence)
    review = json.loads(review_path.read_bytes())
    a, b = seed["receipt"], restart["receipt"]
    sha = source["snapshot_sha256"]
    require(a["snapshot_sha256"] == b["snapshot_sha256"] == restart["inputs"][protocol["native_execution"]["snapshot_filename"]]
            == restart["admission"]["snapshot_before_run_sha256"] == review["snapshot_sha256"] == sha
            and a["canonical_pscx_sha256"] == b["canonical_pscx_sha256"] and a["native_pgb_layout"] == b["native_pgb_layout"]
            and b["seed_receipt_sha256"] == source["original_runs"]["seed"]["sha256"]
            and all(a["post_run_generated_sha256"][key] == b["post_run_generated_sha256"][key] for key in GENERATED),
            "Original seed and continuation are not a genuine same-model native pair")
    require(review["status"] == "PASS_NATIVE_D1_DUAL_VSC_LONG" and all(review["checks"].values())
            and review["protocol_sha256"] == protocol_sha and review["grid"] == name
            and all(review["receipt_sha256"][mode] == source["original_runs"][mode]["sha256"] for mode in ("seed", "restart")),
            "Original native independent audit binding differs")
    anchor = conditioned["grids"][name]
    decode = anchor["comparison_to_long_snapshot"]
    require(decode["native_seed"]["sha256"] == source["original_runs"]["seed"]["sha256"]
            and decode["max_pole_voltage_difference_v"] == decode["max_line_current_difference_a"] == 0,
            "Decoded initial state does not bind this native snapshot")
    return restart, a["snapshot_row"], anchor


def descriptors(lines):
    layout = []
    for slot, line in enumerate(lines, 1):
        match = INF_LINE.fullmatch(line.strip())
        require(match is not None and int(match[1]) == slot, f"Invalid PSCAD slot {slot}")
        _, name, group, high, low, unit = match.groups()
        layout.append({"slot": slot, "name": name, "group": group, "min_token": low, "max_token": high, "unit": unit})
    return layout


def read_native(restart, anchor, grid, protocol):
    work, receipt = restart["work"], restart["receipt"]
    stem, count = receipt["stem"], grid["restart_rows"]
    layout = descriptors((work / f"{stem}.inf").read_text("ascii").splitlines())
    mapping = (work / "vdiv.map").read_text("ascii").splitlines()
    require(mapping.count("PGBList:") == 1, "Missing or ambiguous native PGB map")
    start = mapping.index("PGBList:") + 1
    names = [entry["name"] for entry in layout]
    wanted = {name for group in NATIVE.values() for name in group}
    require(len(layout) == len(set(names)) == 82 and set(names) == wanted
            and layout == receipt["native_pgb_layout"] == descriptors(mapping[start:start+82]) and wanted <= anchor.keys(),
            "Native raw descriptors, compiled map or measured anchor differ")
    outputs = [work / f"{stem}_{part:02}.out" for part in range(1, 10)]
    require(set(work.glob(f"{stem}_*.out")) == set(outputs)
            and set(receipt["raw_files_sha256"]) == {f"{stem}.inf", *(path.name for path in outputs)},
            "Missing or extra original native waveform files")
    columns = {}
    display = None
    for part, path in enumerate(outputs):
        shard = names[part*10:(part+1)*10]
        raw = np.loadtxt(path, skiprows=1)
        require(raw.shape == (count, len(shard)+1) and np.isfinite(raw).all(), f"Malformed native shard {path.name}")
        if display is None:
            display = raw[:, 0].copy()
        else:
            require(np.array_equal(display, raw[:, 0]), f"Original native shard clocks differ at {path.name}")
        columns.update({name: np.r_[float(anchor[name]), raw[:, col]] for col, name in enumerate(shard, 1)})
    trace = {}
    for key, group in NATIVE.items():
        values = [columns[name]*(1000 if name.endswith(("_kV", "_kA")) else 1) for name in group]
        trace[key] = np.column_stack(values) if len(values) > 1 else values[0]
    snap = protocol["timing"]["snapshot_s"]
    trace["time_s"] = np.r_[float(anchor["display_TIME_s"]) - snap, display]
    expected = grid["step_s"] * np.arange(count+1)
    limit = protocol["physical_limits"]["clock_s"]
    require(max(checks.peak(trace["time_s"] - expected), checks.peak(trace["absolute_s"] - snap - expected),
                checks.peak(trace["absolute_s"] - snap - trace["time_s"])) <= limit,
            "Original absolute/display clocks are off the frozen grid")
    names = protocol["native_execution"]["log_columns"]
    logs = {}
    for site, item in receipt["native_logs"].items():
        table = np.loadtxt(work / item["file"], delimiter=",", usecols=[names.index(key) for key in LOG_SIGNALS])
        require(table.shape == (count, len(LOG_SIGNALS)) and np.isfinite(table).all()
                and np.array_equal(table[:, 0], np.arange(1, count+1))
                and checks.peak(table[:, 1] - trace["absolute_s"][1:]) <= limit, "Original controller log clock/length differs")
        logs[site] = dict(zip(LOG_SIGNALS, table.T, strict=True))
    return trace, logs


def candidate_trace(factory, grid, duration, initial, plant):
    case = factory(time_step=grid["step_s"], stop_time=duration)
    result = run_case(replace(case, output=OutputOptions(show_figure=False), plots=(), summary=None))
    count = grid["candidate_rows_including_initial"]
    require((len(result.rows), result.time_step, result.stop_time, result.method) ==
            (count, grid["step_s"], duration, "trapezoidal"), "Candidate did not record the fixed TR grid")

    keys = {"time_s": ("time",), "rail_v": tuple(f"v:{rail}" for rail in RAILS),
            "pcc_v": tuple(f"v:{site}_pcc_{phase}" for site in SITES for phase in "abc"),
            "source_v": tuple(f"v:{site}_grid_{phase}" for site in SITES for phase in "abc"),
            "line_a": tuple(f"i:I_{link}" for link in LINKS),
            "phase_a": tuple(f"i:{site}_L{phase}" for site in SITES for phase in "abc"),
            "feeder_a": tuple(f"i:{site}_Lg{phase}" for site in SITES for phase in "abc"),
            "applied": tuple(f"{phase[0]}_applied_{phase[-1]}" for phase in PHASES),
            "pending": tuple(f"{phase[0]}_pending_{phase[-1]}" for phase in PHASES),
            "resistance": tuple(f"state:{site}_S{phase}_{side}" for site, phase, side in GATES),
            "cap_a": tuple(f"i:cap_{rail}" for rail in RAILS), "star_v": tuple(f"v:{site}_star" for site in SITES),
            "pole_v": tuple(f"v:{site}_pole_{phase}" for site in SITES for phase in "abc"),
            **{f"{side}_a": tuple(f"i:{site}_S{phase}_{side}" for site in SITES for phase in "abc") for side in ("upper", "lower")},
            "pre_a": ("i:Rpre_p", "i:Rpre_n"), "supply_v": ("v:pre_p", "v:pre_n"), "load_a": ("i:Rload",),
            **{key: tuple(f"{site}_{key}" for site in SITES) for key in
               ("j", "gate_tick", "sample_update", "outer_due", "outer_enabled", "p_ref_w", "q_ref_var", "ip_ref_a", "iq_pcc_ref_a")},
            "dc_integrator": tuple(f"{site}_dc_pi_integrator" for site in SITES),
            "filtered_rms_v": tuple(f"{site}_pcc_filtered_rms_v" for site in SITES)}
    columns = tuple(key for group in keys.values() for key in group)
    matrix = np.fromiter(map(itemgetter(*columns), result.rows), dtype=np.dtype((float, len(columns))), count=count)
    del result
    require(np.isfinite(matrix).all(), "Candidate emitted nonfinite data")
    trace, start = {}, 0
    for key, group in keys.items():
        end = start + len(group)
        trace[key] = matrix[:, start:end] if len(group) > 1 else matrix[:, start]
        start = end
    star = np.repeat(trace["star_v"], 3, axis=1)
    trace["source_v"] -= star
    trace["pcc_v"] -= star
    trace["bus_v"] = trace["rail_v"][:, [0, 2]] - trace["rail_v"][:, [3, 5]]
    switches = trace["resistance"]
    require(np.isin(switches, (0., 1.)).all(), "Invalid candidate switch state")
    r = plant["switch_resistance_ohm"]
    trace["resistance"] = np.where(switches == 1, r["closed"], r["open"])
    trace["r_load"] = np.full(count, initial["dc_load_ohm"])
    trace["r_pre"] = np.full(count, initial["precharge_branch_resistance_ohm"])
    return trace


def same_grid(candidate, native, anchor, grid, protocol, candidate_protocol):
    limits = candidate_protocol["same_grid_gate"]
    step, snap = grid["step_s"], protocol["timing"]["snapshot_s"]
    clock = max(checks.peak(candidate["time_s"] - np.arange(len(candidate["time_s"]))*step),
                checks.peak(candidate["time_s"]-native["time_s"]), checks.peak(candidate["time_s"]+snap-native["absolute_s"]))
    conditions = {"original_clocks": clock <= limits["clock_abs_s"], "initial_row": bool(candidate["time_s"][0] == 0)}
    analog = {}
    for limit_name, groups in checks.FAMILIES.items():
        for key in groups:
            delta = candidate[key][1:] - native[key][1:]
            maximum = checks.peak(delta)
            analog[key] = {"maximum": maximum, "by_channel": np.max(np.abs(delta), axis=0).tolist(), "limit": limits[limit_name]}
            conditions[key] = maximum <= limits[limit_name]
    initial_v = checks.peak(candidate["rail_v"][0] - np.asarray([anchor["capacitor_voltage_v"][key] for key in RAILS]))
    initial_line = checks.peak(candidate["line_a"][0] - np.asarray([anchor["line_inductor_current_a"][key] for key in LINKS]))
    initial_ac = max(checks.peak(candidate[key][0] - candidate_protocol["initial_state"]["ac_inductor_current_a"])
                     for key in ("phase_a", "feeder_a"))
    mismatch = int(np.count_nonzero(candidate["resistance"] != native["resistance"]))
    conditions.update(initial_voltage=initial_v <= limits["initial_voltage_abs_v"],
                      initial_current=max(initial_line, initial_ac) <= limits["initial_current_abs_a"],
                      gate_words=mismatch == limits["switch_word_mismatches"],
                      passive_resistances=all(np.array_equal(candidate[key], native[key]) for key in ("r_pre", "r_load")))
    return {"clock_max_error_s": clock, "initial_voltage_error_v": initial_v, "initial_line_current_error_a": initial_line,
            "initial_ac_current_error_a": initial_ac, "switch_word_mismatches": mismatch,
            "waveforms": analog, "checks": conditions, "passed": all(conditions.values())}


def run_comparison(destination):
    candidate_protocol = frozen_json(PROTOCOL, PROTOCOL_SHA)
    records = candidate_protocol["sources"]
    evidence = {}
    paths = {name: record_path(record, evidence) for name, record in records.items()}
    qualified, protocol, conditioned = (json.loads(paths[key].read_bytes()) for key in
        ("native_both_grids", "native_controls_timing_and_power_windows", "conditioned_state_audit"))
    protocol_sha = records["native_controls_timing_and_power_windows"]["sha256"]
    require(qualified["status"] == "PASS_NATIVE_LONG_AND_CROSS_GRID"
            and qualified["protocol"] == records["native_controls_timing_and_power_windows"], "Native long report is not qualified")
    paired = json.loads(record_path(qualified["cross_grid"], evidence).read_bytes())
    require(paired["status"] == "PASS_NATIVE_D1_DUAL_VSC_LONG_CROSS_GRID" and paired["protocol_sha256"] == protocol_sha
            and paired["audit_sha256"] == {name: qualified["grids"][name]["independent_audit"]["sha256"] for name in GRIDS},
            "Native paired long report does not bind the original audits")
    original = {name: qualified_grid(qualified, name, protocol, protocol_sha, conditioned, evidence) for name in GRIDS}
    example = ROOT / candidate_protocol["example"]["path"]
    sources = {PROTOCOL, example, *paths.values(), ROOT / "pyproject.toml", ROOT / "uv.lock",
               *(ROOT / "pycy_emt_lite").rglob("*.py"), *(ROOT / "validation").rglob("*.py")}
    frozen = snapshot_inputs(destination, sources)
    manifest = destination / "inputs.json"
    revision = subprocess.check_output(["git", "-c", f"safe.directory={ROOT.as_posix()}", "rev-parse", "HEAD"],
                                       cwd=ROOT, text=True).strip()
    save_json(manifest, {"git_head_before_run": revision, "platform": platform.platform(),
              "python_version": platform.python_version(), "numpy_version": np.__version__, "sources": frozen,
              "reference_inputs": {path.relative_to(ROOT).as_posix(): digest for path, digest in evidence.items()}})
    factory = runpy.run_path(str(example))["define_case"]
    plant, timing = protocol["plant"], protocol["timing"]
    same_limits = candidate_protocol["same_grid_gate"]
    windows = tuple(timing["power_windows_s"])
    power_limits = dict.fromkeys(checks.MEANS, same_limits["window_mean_power_abs_w_or_var"])
    power_limits.update(b_dc_mean_v=same_limits["window_mean_b_dc_voltage_abs_v"])
    power_limits[checks.PEAK] = same_limits["post_ramp_b_dc_peak_abs_v"]
    grids, plots, candidates = {}, {}, {}
    for name in GRIDS:
        print(f"Comparing {name}", flush=True)
        target = destination / name
        target.mkdir()
        running = protocol["grids"][name]
        grid = candidate_protocol["grids"][name]
        require(grid["step_s"] == running["step_s"] and grid["original_positive_rows"] == running["restart_rows"],
                "Candidate and qualified native grids differ")
        candidate = candidate_trace(factory, grid, candidate_protocol["example"]["duration_s"], candidate_protocol["initial_state"], plant)
        archive, seed_row, anchor = original[name]
        native, logs = read_native(archive, seed_row, running, protocol)
        candidate_file, native_file = target / "candidate_waveforms.npz", target / "native_waveforms.npz"
        for path, trace in ((candidate_file, candidate), (native_file, native)):
            np.savez(path, **trace)
        clock_wave = same_grid(candidate, native, anchor, running, protocol, candidate_protocol)
        control = checks.timing(candidate, native, logs, running, protocol, same_limits)
        physical = checks.physics(candidate, grid["step_s"], plant, protocol["physical_limits"])
        cp, npower = (checks.power_series(trace, plant["dc_line_half"]["r_ohm"]) for trace in (candidate, native))
        cw, pc = checks.power_windows(cp, grid["step_s"], protocol)
        nw, nc = checks.power_windows(npower, grid["step_s"], protocol)
        candidates[name] = cw
        agreement = checks.compare_windows(cw, nw, windows, power_limits)
        passed = all(result["passed"] for result in (clock_wave, control, physical, agreement)) and all((*pc.values(), *nc.values()))
        report = target / "report.json"
        save_json(report, {"passed": passed, "grid": grid, "same_grid": clock_wave, "control": control, "physics": physical,
                           "power_windows": agreement, "candidate_windows": cw, "native_windows": nw,
                           "candidate_window_checks": pc, "native_window_checks": nc,
                           "native_initial_row": "Read from the seed's original snapshot row witness",
                           "waveforms_sha256": {path.name: sha256(path) for path in (candidate_file, native_file)}})
        grids[name] = {"passed": passed, "report_sha256": sha256(report), "rows_with_initial": len(candidate["time_s"])}
        plots[name] = (candidate["time_s"].copy(), cp, npower)
        del candidate, native, trace, logs

    cross_limits = protocol["long_window_acceptance"]["cross_grid_max_abs"]
    cross = checks.compare_windows(candidates["5us"], candidates["2p5us"], windows,
                                   {key: cross_limits[key] for key in checks.MEANS} | {checks.PEAK: cross_limits["b_dc_peak_v"]})
    require(all(sha256(ROOT / name) == digest for name, digest in frozen.items())
            and all(sha256(path) == digest for path, digest in evidence.items()), "Comparison inputs changed during the run")
    passed = cross["passed"] and all(grid["passed"] for grid in grids.values())
    summary = {"passed": passed, "reference_platform": "PSCAD 5.0.0 / EMTDC 5", "grids": grids,
               "candidate_cross_grid": cross, "inputs_sha256": sha256(manifest)}
    if passed:
        from .plots import plot_comparison

        figure = destination / "waveform_overlay.png"
        plot_comparison(figure, plots, timing)
        summary["figure_sha256"] = sha256(figure)
    report = destination / "report.json"
    save_json(report, summary)
    return report, passed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, help="Fresh directory below local_reference")
    args = parser.parse_args()
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    destination = (args.run_dir or CACHE / f"case34_comparison_{stamp}").resolve()
    require(destination != CACHE.resolve() and destination.is_relative_to(CACHE.resolve()), "Output must be below local_reference")
    destination.mkdir(parents=True, exist_ok=False)
    try:
        report, passed = run_comparison(destination)
    except Exception as error:
        save_json(destination / "failure.json", {"passed": False, "exception": type(error).__name__, "message": str(error)})
        raise
    print(report, "PASS" if passed else "FAIL")
    return int(not passed)


if __name__ == "__main__":
    raise SystemExit(main())
