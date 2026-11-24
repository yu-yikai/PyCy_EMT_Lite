"""Read qualified PSCAD island waveforms on their original electrical grids."""

import json
from pathlib import PureWindowsPath

import numpy as np

from validation.cases.grid_connected_pv.reference import tracked_record
from validation.cases.grid_connected_vsc_closed_loop.compare import ROOT
from validation.cases.grid_connected_vsc_open_loop.metrics import require
from validation.cases.pjm5_load_step.compare import admit, record_path
from validation.cases.two_terminal_vsc_hvdc.compare import descriptors

ARCHIVE = ROOT / "local_reference/d1_gfm_single_station_20261123"
WORK = "project/vdiv.gf46"
STEM = "gfm_island"
PASS_PAIR = "PASS_NATIVE_D1_GFM_ISLAND_PAIR"
SINGLE = {
    "time_s": "Absolute_TIME_s", "peak_v": "Source_peak_kV", "phase_rad": "Source_phase_rad",
    "frequency_hz": "Frequency_Hz", "meter_w": "P_pcc_W", "filtered_w": "P_filtered_W",
    "load_resistance_ohm": "Rstep_ohm", "load_on": "Load_step_on",
}
THREE_PHASE = {
    "source_v": "V_src_{}_kV", "pcc_v": "V_pcc_{}_kV", "feeder_a": "I_feeder_{}_kA",
    "base_a": "I_base_{}_kA", "added_a": "I_step_{}_kA",
}


def same_record(first, second):
    """Compare identity without depending on the drive letter of the original archive."""
    return (first["sha256"], first["bytes"]) == (second["sha256"], second["bytes"])


def admit_run(item, report, grid, native, protocol_record, evidence):
    path = record_path(item["original_run"], evidence)
    run = path.parent
    receipt = json.loads(path.read_bytes())
    profile, protocol_sha = native["grids"][grid], protocol_record["sha256"]
    count, step, stop = profile["rows_including_zero"], profile["step_s"], native["timing"]["duration_s"]
    require(run.is_relative_to(ARCHIVE.resolve()) and path.name == "result.json"
            and (receipt["status"], receipt["grid"], receipt["step_s"], receipt["stop_s"],
                 receipt["rows_including_zero"], receipt["protocol_sha256"], receipt["raw_stem"], receipt["generated_work"])
            == ("NATIVE_D1_GFM_ISLAND_CLOSED_FOR_NUMERIC_REVIEW", grid, step, stop, count, protocol_sha, STEM, WORK),
            "Wrong original PSCAD island run")

    work = (run / WORK).resolve(strict=True)
    require(work == run / WORK, "Native compiled directory escapes its archive")

    def bound(parent, name, digest):
        target = (parent / name).resolve(strict=True)
        require(target.is_relative_to(parent), f"Original PSCAD artifact escapes its archive: {name}")
        return admit(target, digest, evidence)

    sidecars = {name: bound(run, f"{name}.json", receipt[f"{name}_sha256"]) for name in (
        "terminal", "worker", "sealed_inputs", "execution_claim", "pre_run_admission", "build_messages", "run_messages")}
    terminal, worker, inputs, claim, admission = (json.loads(sidecars[name].read_bytes()) for name in (
        "terminal", "worker", "sealed_inputs", "execution_claim", "pre_run_admission"))
    binding = report["binding"]
    require(record_path(item["compile_admission"], evidence) == sidecars["pre_run_admission"]
            and same_record(binding["admission"], item["compile_admission"]), "Wrong native compilation admission")
    require(terminal["worker_returncode"] == 0 and terminal["stop_reason"] is None and not terminal["remaining_owned"]
            and not terminal["cleanup"] and terminal["source_hash_unchanged"] and terminal["parent_environment_unchanged"]
            and set(terminal["final_pscad_pids"]) == set(terminal["existing_pscad_pids"])
            and worker["causal_build_admitted"] and worker["run_returned"] and worker["run_calls"] == 1
            and worker["build_errors"] == worker["build_warnings"] == 0
            and all(sum(event["stage"] == stage for event in worker["events"]) == 1 for stage in ("build", "run")),
            "Original PSCAD island run did not finish one admitted solve")

    launch_path = record_path(item["launch"], evidence)
    launch = json.loads(launch_path.read_bytes())
    expected_inputs = {name: launch["input_sha256"][source] for source, name in launch["input_names"].items()}
    require(launch_path.parent == run.parent.parent and launch["grid"] == grid
            and receipt["launch_sha256"] == claim["launch_sha256"] == item["launch"]["sha256"]
            and inputs == {**expected_inputs, "launch.json": receipt["launch_sha256"]}
            and inputs[PureWindowsPath(protocol_record["path"]).name] == protocol_sha
            and inputs["audit_gfm_native.py"] == report["auditor"]["sha256"]
            and inputs["native_capture.py"] == report["raw_reader"]["sha256"]
            and (claim["protocol_sha256"], claim["grid"], claim["step_s"], claim["stop_s"], claim["expected_rows"],
                 claim["builds"], claim["runs"]) == (protocol_sha, grid, step, stop, count, 1, 1),
            "Native run and sealed launch differ")
    for name, digest in inputs.items():
        require(PureWindowsPath(name).name == name, f"Expected a sealed input basename: {name}")
        bound(run / "input_snapshot", name, digest)

    runtime = receipt["native_runtime"]
    expected = native["native"]["toolchain"]
    stdout = bound(run, "run_output.txt", receipt["run_output_sha256"]).read_text("utf-8")
    batch = bound(run, runtime["batch_path"], runtime["batch_sha256"])
    require(runtime == binding["native_runtime"] and all(runtime[key] == value for key, value in expected.items())
            and runtime["emtdc_pid_observed"] is True and f"Build# {expected['emtdc_build']}" in stdout
            and stdout.count("EMTDC run completed.") == 1 and batch.parent == work
            and runtime["batch_sha256"] == binding["batch"]["sha256"] and batch.stat().st_size == binding["batch"]["bytes"],
            "Wrong native toolchain or runtime handoff")
    for key in ("installed_master", "installed_emtdc_library"):
        record = native["reference"][key]
        require(launch["installed_tool_sha256"][record["path"]] == record["sha256"], f"Wrong native tool input: {key}")

    proof, compiled = admission["proof"], receipt["post_run_generated_sha256"]
    require((proof["status"], proof["grid"], proof["protocol_sha256"])
            == ("PASS_NATIVE_D1_GFM_ISLAND_COMPILED_ADMISSION", grid, protocol_sha)
            and proof["native_pgb_layout"] == admission["native_pgb_layout"] == receipt["native_pgb_layout"]
            and compiled == binding["compiled_sha256"] and set(compiled) == {"Main.f", "Main.dta", "vdiv.mak", "vdiv.map", "vdiv.exe"}
            and all(compiled[name] == admission["generated_sha256"][name] for name in ("Main.f", "Main.dta", "vdiv.mak")),
            "Compiled PSCAD circuit does not match its admission")
    bound(run, "project/vdiv.pscx", admission["pscx_sha256"])
    for name, digest in compiled.items():
        bound(work, name, digest)
    raw = {PureWindowsPath(record["path"]).name: record for record in report["raw_artifacts"]}
    outputs = {f"{STEM}_{part:02}.out" for part in range(1, 4)}
    require(set(raw) == set(receipt["raw_files_sha256"]) == {f"{STEM}.inf", *outputs}
            and {path.name for path in work.glob(f"{STEM}_*.out")} == outputs, "Wrong original waveform files")
    for name, record in raw.items():
        path = bound(work, name, receipt["raw_files_sha256"][name])
        require(evidence[path] == record["sha256"] and path.stat().st_size == record["bytes"], f"Wrong waveform evidence: {name}")
    return work, receipt["native_pgb_layout"]


def read_shards(work, admitted_layout, units, count):
    layout = descriptors((work / f"{STEM}.inf").read_text("ascii").splitlines())
    mapping = (work / "vdiv.map").read_text("ascii").splitlines()
    require(mapping.count("PGBList:") == 1, "Missing or ambiguous compiled PGB list")
    start = mapping.index("PGBList:") + 1
    require(len(layout) == len(units) == 23 and {item["name"]: item["unit"] for item in layout} == units
            and all(item["group"] == "GFMIsland" for item in layout)
            and layout == admitted_layout == descriptors(mapping[start:start + len(layout)]), "Wrong native island signal layout")
    names = [item["name"] for item in layout]
    display, columns = None, {}
    for part in range(3):
        path = work / f"{STEM}_{part + 1:02}.out"
        shard = names[part * 10:(part + 1) * 10]
        data = np.loadtxt(path, skiprows=1, ndmin=2)
        require(data.shape == (count, len(shard) + 1) and np.isfinite(data).all(), f"Malformed native shard: {path.name}")
        if display is None:
            display = data[:, 0].copy()
        else:
            require(np.array_equal(display, data[:, 0]), f"Native shard clocks differ: {path.name}")
        columns.update({name: data[:, col].copy() for col, name in enumerate(shard, 1)})
    return display, columns


def read_reference(protocol, grid, evidence):
    """Return the original PSCAD rows in SI and record their input hashes."""
    sources = protocol["sources"]
    native_record = sources["native_protocol"]
    native = tracked_record(native_record, evidence)
    qualified = tracked_record(sources["qualified_native"], evidence)
    require(qualified["status"] == PASS_PAIR and qualified["protocol"] == native_record
            and qualified["pscad_toolchain"] == native["native"]["toolchain"]
            and all(protocol[name] == native[name] for name in ("fixture", "timing", "controller", "grids")),
            "Frozen candidate and qualified PSCAD fixture differ")
    pair = json.loads(record_path(qualified["paired_audit"], evidence).read_bytes())
    item, profile = qualified["grids"][grid], protocol["grids"][grid]
    report = json.loads(record_path(item["audit"], evidence).read_bytes())
    count = profile["rows_including_zero"]
    require(pair["status"] == PASS_PAIR and same_record(pair["protocol"], native_record)
            and pair["checks"] and all(check is True for check in pair["checks"].values())
            and same_record(pair["grid_reports"][grid], item["audit"]) and same_record(pair["receipts"][grid], item["original_run"])
            and same_record(report["binding"]["result"], item["original_run"]) and same_record(report["protocol"], native_record)
            and report["auditor"] == pair["auditor"] and report["checks"] and all(check is True for check in report["checks"].values())
            and (report["status"], report["grid"], report["step_s"], report["rows_including_zero"], item["rows_including_zero"])
            == ("PASS_NATIVE_D1_GFM_ISLAND", grid, profile["step_s"], count, count), "Wrong native grid qualification")
    work, layout = admit_run(item, report, grid, native, native_record, evidence)
    display, columns = read_shards(work, layout, native["channels"], count)
    absolute = columns["Absolute_TIME_s"]
    ticks = np.arange(count)
    time = ticks * profile["step_s"]
    clock = protocol["physical_limits"]["clock_abs_s"]
    require(display[0] == absolute[0] == 0 and np.all(np.diff(display) > 0) and np.all(np.diff(absolute) > 0)
            and max(np.max(np.abs(display - time)), np.max(np.abs(absolute - time)), np.max(np.abs(absolute - display))) <= clock,
            "Original PSCAD clocks differ from the frozen electrical grid")
    load_on = ticks >= profile["load_step_tick"]
    fixture = protocol["fixture"]
    require(np.array_equal(columns["Load_step_on"], load_on)
            and np.array_equal(columns["Rstep_ohm"], np.where(load_on, fixture["added_load_ohm"], fixture["open_load_ohm"])),
            "Original switched loads do not match the frozen tick and resistance")

    trace = {"display_s": display, **{key: columns[name] for key, name in SINGLE.items()}}
    trace["peak_v"] = 1000 * trace["peak_v"]
    for key, pattern in THREE_PHASE.items():
        trace[key] = 1000 * np.column_stack([columns[pattern.format(phase)] for phase in "abc"])
    return trace
