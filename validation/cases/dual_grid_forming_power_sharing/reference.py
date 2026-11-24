"""Read the qualified dual-source PSCAD runs on their original electrical grids."""

import json
from pathlib import PureWindowsPath

import numpy as np

from validation.cases.grid_connected_pv.reference import tracked_record
from validation.cases.grid_connected_vsc_closed_loop.compare import ROOT
from validation.cases.grid_connected_vsc_open_loop.metrics import require
from validation.cases.islanded_frequency_droop.reference import same_record
from validation.cases.pjm5_load_step.compare import admit, record_path
from validation.cases.two_terminal_vsc_hvdc.compare import descriptors

ARCHIVE = ROOT / "local_reference/e_dual_gfm_sharing_pscad_20261123"
WORK = "project/vdiv.gf46"
STEM = "gfm_sharing"
PASS_PAIR = "PASS_NATIVE_E_DUAL_GFM_SHARING_PAIR"
STATIONS, PHASES = "ab", "abc"


def admit_run(item, report, grid, native, protocol_record, evidence):
    path = record_path(item["original_run"], evidence)
    run, receipt = path.parent, json.loads(path.read_bytes())
    profile, protocol_sha = native["grids"][grid], protocol_record["sha256"]
    step, count, stop = profile["step_s"], profile["rows_including_zero"], native["timing"]["duration_s"]
    require(run.is_relative_to(ARCHIVE.resolve()) and path.name == "result.json"
            and (receipt["status"], receipt["grid"], receipt["step_s"], receipt["stop_s"],
                 receipt["rows_including_zero"], receipt["protocol_sha256"], receipt["raw_stem"], receipt["generated_work"])
            == ("NATIVE_E_DUAL_GFM_SHARING_CLOSED_FOR_NUMERIC_REVIEW", grid, step, stop, count, protocol_sha, STEM, WORK),
            "Wrong original PSCAD dual-source run")
    work = (run / WORK).resolve(strict=True)
    require(work == run / WORK, "Compiled directory escapes its native run")

    def bound(parent, name, digest):
        target = (parent / name).resolve(strict=True)
        require(target.is_relative_to(parent), f"PSCAD artifact escapes its archive: {name}")
        return admit(target, digest, evidence)

    files = {name: bound(run, f"{name}.json", receipt[f"{name}_sha256"]) for name in (
        "terminal", "worker", "sealed_inputs", "execution_claim", "pre_run_admission", "build_messages", "run_messages")}
    terminal, worker, inputs, claim, admission = (json.loads(files[name].read_bytes()) for name in (
        "terminal", "worker", "sealed_inputs", "execution_claim", "pre_run_admission"))
    binding = report["binding"]
    require(record_path(item["compile_admission"], evidence) == files["pre_run_admission"]
            and same_record(binding["admission"], item["compile_admission"]), "Wrong compiled admission record")
    require(terminal["worker_returncode"] == 0 and terminal["stop_reason"] is None and not terminal["remaining_owned"]
            and not terminal["cleanup"] and terminal["source_hash_unchanged"] and terminal["parent_environment_unchanged"]
            and set(terminal["final_pscad_pids"]) == set(terminal["existing_pscad_pids"])
            and worker["causal_build_admitted"] and worker["run_returned"] and worker["run_calls"] == 1
            and worker["build_errors"] == worker["build_warnings"] == 0
            and all(sum(event["stage"] == stage for event in worker["events"]) == 1 for stage in ("build", "run")),
            "Original PSCAD run did not finish one admitted build and solve")

    launch_path = record_path(item["launch"], evidence)
    launch = json.loads(launch_path.read_bytes())
    snapshot = {name: launch["input_sha256"][source] for source, name in launch["input_names"].items()}
    require(launch_path.parent == run.parent.parent and launch["grid"] == grid
            and claim["launch_sha256"] == receipt["launch_sha256"] == item["launch"]["sha256"]
            and inputs == {**snapshot, "launch.json": receipt["launch_sha256"]}
            and inputs[PureWindowsPath(protocol_record["path"]).name] == protocol_sha
            and inputs["audit_dual_gfm.py"] == report["auditor"]["sha256"]
            and inputs["native_capture.py"] == report["raw_reader"]["sha256"]
            and (claim["protocol_sha256"], claim["grid"], claim["step_s"], claim["stop_s"], claim["expected_rows"],
                 claim["builds"], claim["runs"]) == (protocol_sha, grid, step, stop, count, 1, 1),
            "Native execution and sealed launch differ")
    for name, digest in inputs.items():
        require(PureWindowsPath(name).name == name, f"Expected a sealed input basename: {name}")
        bound(run / "input_snapshot", name, digest)

    runtime, expected = receipt["native_runtime"], native["native"]["toolchain"]
    stdout = bound(run, "run_output.txt", receipt["run_output_sha256"]).read_text("utf-8")
    batch = bound(run, runtime["batch_path"], runtime["batch_sha256"])
    require(runtime == binding["native_runtime"] and all(runtime[key] == value for key, value in expected.items())
            and runtime["emtdc_pid_observed"] is True and f"Build# {expected['emtdc_build']}" in stdout
            and stdout.count("EMTDC run completed.") == 1 and batch.parent == work
            and evidence[batch] == binding["batch"]["sha256"] and batch.stat().st_size == binding["batch"]["bytes"],
            "Wrong original PSCAD toolchain or runtime")
    for key in ("installed_master", "installed_emtdc_library"):
        record = native["reference"][key]
        require(launch["installed_tool_sha256"][record["path"]] == record["sha256"], f"Wrong installed tool input: {key}")

    layout, compiled = receipt["native_pgb_layout"], receipt["post_run_generated_sha256"]
    proof = admission["proof"]
    clock, transfers = proof["compiled_clock"], proof["phase_transfers"]
    phase_slots = {transfers[site][name] for site in STATIONS for name in ("applied_phase", "next_phase")}
    require((proof["status"], proof["grid"], proof["protocol_sha256"], proof["physical_branches"], proof["generated_branches"])
            == ("PASS_NATIVE_E_DUAL_GFM_SHARING_COMPILED_ADMISSION", grid, protocol_sha, 18, 18)
            and (clock["START_TIME"], clock["FINISH_TIME"], clock["TIME_STEP"], clock["PRINT_STEP"], clock["SHORT_CIRCUIT"])
            == (0, stop, step, step, native["native"]["branch_threshold_ohm"])
            and set(transfers) == set(STATIONS) and len(phase_slots) == 4 and proof["filter_history_real_words"] == 2
            and proof["native_pgb_layout"] == admission["native_pgb_layout"] == layout
            and compiled == binding["compiled_sha256"] and set(compiled) == {"Main.f", "Main.dta", "vdiv.mak", "vdiv.map", "vdiv.exe"}
            and all(compiled[name] == admission["generated_sha256"][name] for name in ("Main.f", "Main.dta", "vdiv.mak"))
            and all(proof["hashes"][name] == admission["generated_sha256"][name] for name in ("Main.f", "Main.dta", "vdiv.map"))
            and proof["saved_project_sha256"] == admission["pscx_sha256"], "Wrong admitted dual-source plant, controller or clock")
    bound(run, "project/vdiv.pscx", admission["pscx_sha256"])
    for name, digest in compiled.items():
        bound(work, name, digest)
    for name in ("Station.f", "Station.dta"):
        record = item["compiled_wrappers"][name]
        require(record["sha256"] == proof["hashes"][name] and record_path(record, evidence) == work / name,
                f"Wrong compiled wrapper: {name}")

    outputs = [work / f"{STEM}_{part:02}.out" for part in range(1, 5)]
    raw = {PureWindowsPath(record["path"]).name: record for record in report["raw_artifacts"]}
    require(set(raw) == set(receipt["raw_files_sha256"]) == {f"{STEM}.inf", *(file.name for file in outputs)}
            and set(work.glob(f"{STEM}_*.out")) == set(outputs), "Wrong original dual-source waveform files")
    for name, record in raw.items():
        target = bound(work, name, receipt["raw_files_sha256"][name])
        require(evidence[target] == record["sha256"] and target.stat().st_size == record["bytes"], f"Wrong raw evidence: {name}")
    return work, layout, outputs


def read_shards(work, admitted_layout, outputs, units, group, count):
    layout = descriptors((work / f"{STEM}.inf").read_text("ascii").splitlines())
    mapping = (work / "vdiv.map").read_text("ascii").splitlines()
    require(mapping.count("PGBList:") == 1, "Missing or ambiguous compiled PGB list")
    start = mapping.index("PGBList:") + 1
    require(len(layout) == len(units) == 33 and {item["name"]: item["unit"] for item in layout} == units
            and all(item["group"] == group for item in layout)
            and layout == admitted_layout == descriptors(mapping[start:start + len(layout)]), "Wrong original dual-source channel layout")
    names = [item["name"] for item in layout]
    display, columns = None, {}
    for part, path in enumerate(outputs):
        shard = names[part * 10:(part + 1) * 10]
        data = np.loadtxt(path, skiprows=1, ndmin=2)
        require(data.shape == (count, len(shard) + 1) and np.isfinite(data).all(), f"Malformed original shard: {path.name}")
        if display is None:
            display = data[:, 0].copy()
        else:
            require(np.array_equal(display, data[:, 0]), f"Original shard clocks differ: {path.name}")
        columns.update({name: data[:, index].copy() for index, name in enumerate(shard, 1)})
    return display, columns


def read_reference(protocol, grid, evidence):
    """Return original SI arrays indexed by row, then A/B station, then abc phase."""
    sources = protocol["sources"]
    native_record = sources["native_protocol"]
    native = tracked_record(native_record, evidence)
    qualified = tracked_record(sources["qualified_native"], evidence)
    require(qualified["status"] == PASS_PAIR and qualified["protocol"] == native_record
            and qualified["pscad_toolchain"] == native["native"]["toolchain"]
            and all(protocol[name] == native[name] for name in ("fixture", "timing", "controller", "grids", "channels", "native")),
            "Frozen candidate and qualified dual-source PSCAD fixture differ")
    pair = json.loads(record_path(qualified["paired_audit"], evidence).read_bytes())
    item, profile = qualified["grids"][grid], protocol["grids"][grid]
    report = json.loads(record_path(item["audit"], evidence).read_bytes())
    step, count = profile["step_s"], profile["rows_including_zero"]
    require(pair["status"] == PASS_PAIR and same_record(pair["protocol"], native_record)
            and pair["checks"] and all(check is True for check in pair["checks"].values())
            and len({pair["receipts"][name]["sha256"] for name in protocol["grids"]}) == 2
            and same_record(pair["grid_reports"][grid], item["audit"]) and same_record(pair["receipts"][grid], item["original_run"])
            and same_record(report["binding"]["result"], item["original_run"]) and same_record(report["protocol"], native_record)
            and report["auditor"] == pair["auditor"] and report["checks"] and all(check is True for check in report["checks"].values())
            and (report["status"], report["grid"], report["step_s"], report["rows_including_zero"], item["rows_including_zero"])
            == ("PASS_NATIVE_E_DUAL_GFM_SHARING", grid, step, count, count), "Wrong native dual-source grid qualification")
    work, layout, outputs = admit_run(item, report, grid, native, native_record, evidence)
    display, columns = read_shards(work, layout, outputs, native["channels"], native["native"]["output_group"], count)
    absolute = columns["Absolute_TIME_s"]
    ticks = np.arange(count)
    time, clock = ticks * step, protocol["physical_limits"]["clock_abs_s"]
    require(display[0] == absolute[0] == 0 and np.all(np.diff(display) > 0) and np.all(np.diff(absolute) > 0)
            and max(np.max(np.abs(display - time)), np.max(np.abs(absolute - time)), np.max(np.abs(absolute - display))) <= clock,
            "Original PSCAD clocks differ from the frozen electrical grid")
    load_on = ticks >= profile["load_step_tick"]
    fixture = protocol["fixture"]
    require(np.array_equal(columns["Load_step_on"], load_on)
            and np.array_equal(columns["Rstep_ohm"], np.where(load_on, fixture["added_load_ohm"], fixture["open_load_ohm"])),
            "Original PSCAD load masks differ from the frozen event row")

    def phases(pattern):
        return 1000 * np.column_stack([columns[pattern.format(phase)] for phase in PHASES])

    def stations(pattern):
        return np.column_stack([columns[pattern.format(site)] for site in STATIONS])

    return {
        "display_s": display, "time_s": absolute, "peak_v": 1000 * columns["Source_peak_kV"],
        "load_r": columns["Rstep_ohm"], "load_on": columns["Load_step_on"],
        "phase_rad": stations("Source_{}_phase_rad"), "frequency_hz": stations("Frequency_{}_Hz"),
        "meter_w": stations("P_pcc_{}_W"), "filtered_w": stations("P_filtered_{}_W"),
        "source_v": np.stack([phases(f"V_src_{site}_{{}}_kV") for site in STATIONS], axis=1),
        "feeder_a": np.stack([phases(f"I_feeder_{site}_{{}}_kA") for site in STATIONS], axis=1),
        "pcc_v": phases("V_pcc_{}_kV"), "base_a": phases("I_base_{}_kA"), "added_a": phases("I_step_{}_kA"),
    }
