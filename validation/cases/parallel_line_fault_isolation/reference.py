"""Read both qualified PSCAD parallel-fault traces on their original grids."""

import json
from pathlib import PureWindowsPath

import numpy as np

from validation.cases.grid_connected_pv.reference import tracked_record
from validation.cases.grid_connected_vsc_closed_loop.compare import ROOT
from validation.cases.grid_connected_vsc_open_loop.metrics import require
from validation.cases.islanded_frequency_droop.reference import same_record
from validation.cases.pjm5_load_step.compare import admit, record_path
from validation.cases.two_terminal_vsc_hvdc.compare import descriptors

ARCHIVE = ROOT / "local_reference/e_parallel_fault_pscad_20261123"
WORK = "project/vdiv.gf46"
STEM = "parallel_fault"
PASS_PAIR = "PASS_NATIVE_E_PARALLEL_SURROGATE_PAIR"
RESISTANCES = ("R_sf_ohm", "R_rf_ohm", "R_fault_ohm")
VOLTAGES = ("src", "recv", "fault")
CURRENTS = ("healthy", "sf", "rf", "fault", "load", "ref")


def admit_run(item, review, grid, native, protocol_record, evidence):
    path = record_path(item["original_run"], evidence)
    run = path.parent
    receipt = json.loads(path.read_bytes())
    profile, protocol_sha = native["grids"][grid], protocol_record["sha256"]
    step, count, stop = profile["step_s"], profile["rows_including_zero"], native["timing"]["duration_s"]
    require(run.is_relative_to(ARCHIVE.resolve()) and path.name == "result.json"
            and (receipt["status"], receipt["grid"], receipt["step_s"], receipt["stop_s"],
                 receipt["rows_including_zero"], receipt["protocol_sha256"], receipt["raw_stem"], receipt["generated_work"])
            == ("NATIVE_E_PARALLEL_SURROGATE_CLOSED_FOR_NUMERIC_REVIEW", grid, step, stop, count, protocol_sha, STEM, WORK),
            "Wrong original PSCAD parallel-fault run")
    work = (run / WORK).resolve(strict=True)
    require(work == run / WORK, "Compiled work directory escapes its run")

    def bound(parent, name, digest):
        target = (parent / name).resolve(strict=True)
        require(target.is_relative_to(parent), f"Original PSCAD artifact escapes its directory: {name}")
        return admit(target, digest, evidence)

    sidecars = {name: bound(run, f"{name}.json", receipt[f"{name}_sha256"]) for name in (
        "terminal", "worker", "sealed_inputs", "execution_claim", "pre_run_admission", "build_messages", "run_messages")}
    terminal, worker, inputs, claim, admission = (json.loads(sidecars[name].read_bytes()) for name in (
        "terminal", "worker", "sealed_inputs", "execution_claim", "pre_run_admission"))
    require(terminal["worker_returncode"] == 0 and terminal["stop_reason"] is None and not terminal["remaining_owned"]
            and not terminal["cleanup"] and terminal["source_hash_unchanged"] and terminal["parent_environment_unchanged"]
            and set(terminal["final_pscad_pids"]) == set(terminal["existing_pscad_pids"])
            and worker["causal_build_admitted"] and worker["run_returned"] and worker["run_calls"] == 1
            and worker["build_errors"] == worker["build_warnings"] == 0
            and all(sum(event["stage"] == stage for event in worker["events"]) == 1 for stage in ("build", "run")),
            "Original parallel-fault run did not finish one admitted PSCAD build and solve")

    launch_path = record_path(item["launch"], evidence)
    launch = json.loads(launch_path.read_bytes())
    expected_inputs = {name: launch["input_sha256"][source] for source, name in launch["input_names"].items()}
    require(launch_path.parent == run.parent.parent and launch["grid"] == grid
            and claim["launch_sha256"] == receipt["launch_sha256"] == item["launch"]["sha256"]
            and inputs == {**expected_inputs, "launch.json": receipt["launch_sha256"]}
            and inputs[PureWindowsPath(protocol_record["path"]).name] == protocol_sha
            and inputs["audit_parallel_native.py"] == review["auditor"]["sha256"]
            and inputs["native_capture.py"] == review["raw_reader"]["sha256"]
            and (claim["protocol_sha256"], claim["grid"], claim["step_s"], claim["stop_s"], claim["expected_rows"],
                 claim["builds"], claim["runs"]) == (protocol_sha, grid, step, stop, count, 1, 1),
            "Native run and sealed launch differ")
    for name, digest in inputs.items():
        require(PureWindowsPath(name).name == name, f"Expected a sealed input basename: {name}")
        bound(run / "input_snapshot", name, digest)

    binding, runtime = review["binding"], receipt["native_runtime"]
    expected = native["native"]["toolchain"]
    stdout = bound(run, "run_output.txt", receipt["run_output_sha256"]).read_text("utf-8")
    batch = bound(run, runtime["batch_path"], runtime["batch_sha256"])
    require(runtime == binding["native_runtime"] and all(runtime[key] == value for key, value in expected.items())
            and runtime["emtdc_pid_observed"] is True and f"Build# {expected['emtdc_build']}" in stdout
            and stdout.count("EMTDC run completed.") == 1 and batch.parent == work
            and evidence[batch] == binding["batch"]["sha256"] and batch.stat().st_size == binding["batch"]["bytes"],
            "Wrong original PSCAD toolchain or runtime")
    for key in ("installed_master", "installed_emtdc_library"):
        record = native["reference"][key]
        require(launch["installed_tool_sha256"][record["path"]] == record["sha256"], f"Wrong installed native input: {key}")

    layout, compiled = receipt["native_pgb_layout"], receipt["post_run_generated_sha256"]
    proof = admission["proof"]
    clock = proof["compiled_clock"]
    require((proof["status"], proof["grid"], proof["protocol_sha256"], proof["physical_branches"], proof["generated_branches"])
            == ("PASS_NATIVE_E_PARALLEL_FAULT_COMPILED_ADMISSION", grid, protocol_sha, 21, 21)
            and (clock["START_TIME"], clock["FINISH_TIME"], clock["TIME_STEP"], clock["PRINT_STEP"]) == (0, stop, step, step)
            and proof["native_pgb_layout"] == admission["native_pgb_layout"] == layout
            and evidence[sidecars["pre_run_admission"]] == binding["admission"]["sha256"]
            and sidecars["pre_run_admission"].stat().st_size == binding["admission"]["bytes"]
            and compiled == binding["compiled_sha256"] and set(compiled) == {"Main.f", "Main.dta", "vdiv.mak", "vdiv.map", "vdiv.exe"}
            and all(compiled[name] == admission["generated_sha256"][name] for name in ("Main.f", "Main.dta", "vdiv.mak")),
            "Compiled parallel-fault circuit, clock or map differs from admission")
    bound(run, "project/vdiv.pscx", admission["pscx_sha256"])
    for name, digest in compiled.items():
        bound(work, name, digest)

    outputs = [work / f"{STEM}_{part:02}.out" for part in range(1, 5)]
    raw = {PureWindowsPath(record["path"]).name: record for record in review["raw_artifacts"]}
    require(set(raw) == set(receipt["raw_files_sha256"]) == {f"{STEM}.inf", *(path.name for path in outputs)}
            and set(work.glob(f"{STEM}_*.out")) == set(outputs), "Wrong original parallel-fault waveform files")
    for name, record in raw.items():
        target = bound(work, name, receipt["raw_files_sha256"][name])
        require(evidence[target] == record["sha256"] and target.stat().st_size == record["bytes"], f"Wrong raw evidence: {name}")
    return work, layout, outputs


def read_shards(work, admitted_layout, outputs, units, count):
    layout = descriptors((work / f"{STEM}.inf").read_text("ascii").splitlines())
    mapping = (work / "vdiv.map").read_text("ascii").splitlines()
    require(mapping.count("PGBList:") == 1, "Missing or ambiguous compiled PGB list")
    start = mapping.index("PGBList:") + 1
    require(len(layout) == len(units) == 31 and {item["name"]: item["unit"] for item in layout} == units
            and all(item["group"] == "ParallelFault" for item in layout)
            and layout == admitted_layout == descriptors(mapping[start:start + len(layout)]), "Wrong original parallel-fault channel layout")
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
        columns.update({name: data[:, col].copy() for col, name in enumerate(shard, 1)})
    return display, columns


def read_reference(protocol, grid, evidence):
    """Return qualified original PSCAD time, resistance and three-phase SI arrays."""
    sources = protocol["sources"]
    native_record = sources["native_protocol"]
    native = tracked_record(native_record, evidence)
    qualified = tracked_record(sources["qualified_native"], evidence)
    require(qualified["status"] == PASS_PAIR and qualified["protocol"] == native_record
            and all(protocol[name] == native[name] for name in ("fixture", "timing", "grids")),
            "Frozen candidate and qualified parallel-fault fixture differ")
    pair = json.loads(record_path(qualified["paired_audit"], evidence).read_bytes())
    item, profile = qualified["grids"][grid], protocol["grids"][grid]
    review = json.loads(record_path(item["audit"], evidence).read_bytes())
    step, count = profile["step_s"], profile["rows_including_zero"]
    require(pair["status"] == PASS_PAIR and same_record(pair["protocol"], native_record)
            and pair["checks"] and all(check is True for check in pair["checks"].values())
            and same_record(pair["grid_reports"][grid], item["audit"]) and same_record(pair["receipts"][grid], item["original_run"])
            and same_record(review["binding"]["result"], item["original_run"]) and same_record(review["protocol"], native_record)
            and review["auditor"] == pair["auditor"] and review["checks"] and all(check is True for check in review["checks"].values())
            and (review["status"], review["grid"], review["step_s"], review["rows_including_zero"], item["rows_including_zero"])
            == ("PASS_NATIVE_E_PARALLEL_SURROGATE", grid, step, count, count), "Wrong parallel-fault grid qualification")
    work, layout, outputs = admit_run(item, review, grid, native, native_record, evidence)
    display, columns = read_shards(work, layout, outputs, native["channels"], count)
    absolute = columns["Absolute_TIME_s"]
    ticks = np.arange(count)
    time, clock = ticks * step, protocol["physical_limits"]["clock_abs_s"]
    require(display[0] == absolute[0] == 0 and np.all(np.diff(display) > 0) and np.all(np.diff(absolute) > 0)
            and max(np.max(np.abs(display - time)), np.max(np.abs(absolute - time)), np.max(np.abs(absolute - display))) <= clock,
            "Original PSCAD clocks differ from the frozen electrical grid")

    timing, fixture = protocol["timing"], protocol["fixture"]
    fault_on, open_sf, open_rf, fault_off, reclose = (round(timing[key] / step) for key in (
        "fault_on_s", "open_sf_s", "open_rf_s", "fault_off_s", "reclose_s"))
    opened, closed = fixture["open_ohm"], fixture["path_on_ohm"]
    expected = (np.where((open_sf <= ticks) & (ticks < reclose), opened, closed),
                np.where((open_rf <= ticks) & (ticks < reclose), opened, closed),
                np.where((fault_on <= ticks) & (ticks < fault_off), fixture["fault_on_ohm"], opened))
    require(all(np.array_equal(columns[name], values) for name, values in zip(RESISTANCES, expected, strict=True)),
            "Original PSCAD resistance words differ from the frozen event rows")

    trace = {"display_s": display, "time_s": absolute, **{name: columns[name] for name in RESISTANCES}}
    for letter, unit, names in (("V", "kV", VOLTAGES), ("I", "kA", CURRENTS)):
        for name in names:
            trace[f"{letter.lower()}_{name}"] = 1000 * np.column_stack([columns[f"{letter}_{name}_{p}_{unit}"] for p in "abc"])
    return trace
