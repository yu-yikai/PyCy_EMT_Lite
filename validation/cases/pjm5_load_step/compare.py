"""Run case 33 against the two qualified original PSCAD captures."""

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
from validation.common.runner import sha256

from . import checks
from .plots import plot_comparison

CACHE = ROOT / "local_reference"
DIRECTORY = Path(__file__).resolve().parent
PROTOCOL = DIRECTORY / "candidate_protocol.json"
PROTOCOL_SHA = "c8d6e90fa0025cd4a2775eb536a47c7bd4d99d28f104c6af416196364c733880"
EXAMPLE = ROOT / "examples/33_pjm5_load_step.py"
GRIDS = ("5us", "2p5us")
PHASES = "abc"


def admit(path, digest, evidence):
    path = path.resolve(strict=True)
    if path not in evidence:
        evidence[path] = sha256(path)
    require(evidence[path] == digest, f"Input SHA-256 differs: {path}")
    return path


def record_path(record, evidence):
    path = admit(ROOT / record["path"], record["sha256"], evidence)
    require(path.stat().st_size == record["bytes"], f"Input byte count differs: {path}")
    return path


def archive(grid_name, grid, protocol, native_record, evidence):
    """Bind a full reference to its closed native run and its original raw files."""
    index = native_record["evidence"]
    paths = {role: record_path(item, evidence) for role, item in index.items()}
    run = paths["execution"].parent
    require(run.is_relative_to(CACHE.resolve()) and all(path.parent == run for path in paths.values()),
            f"Reference evidence is outside its native archive: {grid_name}")
    receipt, terminal, admission, physics, initial = (json.loads(paths[role].read_bytes()) for role in
        ("execution", "terminal", "generated_admission", "physics", "source_initialization"))
    h, count = grid["step_s"], grid["rows_including_zero"]
    native_protocol_sha = protocol["native_protocol"]["sha256"]
    require(receipt["status"] == "NATIVE_D1_PJM5_PSCAD_RUN_CLOSED_FOR_NUMERIC_REVIEW"
            and receipt["grid"] == grid_name and receipt["scope"] == "full" and receipt["step_s"] == h
            and receipt["stop_s"] == protocol["stop_s"] and receipt["rows_including_zero"] == count
            and receipt["model_sha256"] == protocol["model"]["sha256"]
            and receipt["numerical_protocol_sha256"] == native_protocol_sha,
            f"Wrong full native run: {grid_name}")
    require(terminal["worker_returncode"] == 0 and terminal["stop_reason"] is None and not terminal["remaining_owned"]
            and not terminal["cleanup"] and terminal["source_hash_unchanged"] and terminal["parent_environment_unchanged"]
            and receipt["native_runtime"]["emtdc_pid_observed"] is True, f"Native session is unclosed: {grid_name}")
    for key, role in (("terminal", "terminal"), ("pre_run_admission", "generated_admission"),
                      ("sealed_inputs", "sealed_inputs"), ("run_output", "native_console")):
        require(receipt[f"{key}_sha256"] == index[role]["sha256"], f"Native {role} link differs: {grid_name}")
    proof = admission["proof"]
    require(proof["status"] == "PASS_NATIVE_PJM5_COMPILED_ADMISSION"
            and proof["physical_branches"] == 78 and proof["meter_only_branches"] == 6
            and set(proof["voltage_modes"].values()) == {"forced_dsout"}
            and admission["native_pgb_layout"] == receipt["native_pgb_layout"], f"Wrong native output binding: {grid_name}")
    require(physics["status"] == "PASS_NATIVE_PJM5_PHYSICS" and not physics["short"] and physics["grid"] == grid_name
            and physics["native_rows_including_zero"] == count and physics["protocol_sha256"] == native_protocol_sha
            and physics["native_run_receipt_sha256"] == index["execution"]["sha256"]
            and initial["status"] == "PASS_OBSERVED_SOURCE_INITIALIZATION" and initial["grid"] == grid_name
            and initial["native_review_sha256"] == index["physics"]["sha256"], f"Native qualification link differs: {grid_name}")

    work = (run / receipt["generated_work"]).resolve(strict=True)
    require(work == run / "project/vdiv.gf46", f"Invalid generated archive directory: {grid_name}")
    archive_files = receipt["raw_files_sha256"] | receipt["post_run_generated_sha256"]
    for name, digest in archive_files.items():
        require(Path(name).name == name, f"Expected an original native basename: {name}")
        admit(work / name, digest, evidence)
    batch = receipt["native_runtime"]
    admit(run / batch["batch_path"], batch["batch_sha256"], evidence)
    admit(run / "project/vdiv.pscx", admission["pscx_sha256"], evidence)
    return work, receipt["native_pgb_layout"], receipt["raw_files_sha256"]


def signal_groups(model):
    lines = [f"{line['from_bus']}{line['to_bus']}" for line in model["lines"]]
    loads = [load["bus"] for load in model["baseline_loads"]]
    return {
        "voltage_v": [[f"V_b{bus}_{p}_kV" for p in PHASES] for bus in model["buses"]],
        **{f"{role}_a": [[f"I_l{line}_{role}_{p}_kA" for p in PHASES] for line in lines]
           for role in ("series", "from", "to")},
        **{f"load_{name}_a": [[f"I_load{kind}_b{bus}_{p}_kA" for p in PHASES] for bus in loads]
           for name, kind in (("resistor", "R"), ("inductor", "L"))},
        "source_a": [f"I_source_{p}_kA" for p in PHASES], "step_a": [f"I_step_{p}_kA" for p in PHASES],
    }


def read_native(model, archive_inputs, grid, clock_limit):
    """Decode the original, admitted PGB columns into signed SI waveforms."""
    work, layout, files = archive_inputs
    out = [work / f"vdiv_{part:02}.out" for part in range(1, 11)]
    require(set(files) == {"vdiv.inf", *(path.name for path in out)} and set(work.glob("vdiv_*.out")) == set(out),
            "Missing or unexpected original OUT files")
    inf = (work / "vdiv.inf").read_text("ascii").splitlines()
    mapping = (work / "vdiv.map").read_text("ascii").splitlines()
    require(mapping.count("PGBList:") == 1, "Missing or duplicate generated PGB list")
    start = mapping.index("PGBList:") + 1
    require(len(inf) == len(layout) == 95, "Expected 95 original PGB descriptors")
    fields = ("slot", "name", "group", "max_token", "min_token", "unit")
    names = []
    for slot, (descriptor, line, compiled) in enumerate(zip(layout, inf, mapping[start:start+95], strict=True), 1):
        raw, generated = (INF_LINE.fullmatch(value.strip()) for value in (line, compiled))
        require(raw is not None and generated is not None and raw.groups() == generated.groups()
                and int(raw[1]) == slot and tuple(str(descriptor[key]) for key in fields) == raw.groups(),
                f"Native PGB slot differs: {slot}")
        require(descriptor["group"] == "PJM5" and float(descriptor["min_token"]) < float(descriptor["max_token"]),
                f"Native PGB metadata differs: {slot}")
        names.append(descriptor["name"])
    groups = signal_groups(model)
    expected = {name: name.rsplit("_", 1)[1] for group in groups.values() for name in np.asarray(group).flat}
    expected |= {"R_step_ohm": "ohm", "Absolute_TIME_s": "s"}
    require(len(set(names)) == len(expected) == 95 and {row["name"]: row["unit"] for row in layout} == expected,
            "Native channel names or units differ")

    columns = {}
    for part, path in enumerate(out):
        channels = names[part*10:(part+1)*10]
        data = np.loadtxt(path, skiprows=1)
        require(data.shape == (grid["rows_including_zero"], len(channels)+1) and np.isfinite(data).all(),
                f"Invalid native shard: {path.name}")
        if part == 0:
            display = data[:, 0]
        else:
            require(np.array_equal(display, data[:, 0]), f"Native shard clocks differ: {path.name}")
        columns.update({name: data[:, col] for col, name in enumerate(channels, 1)})
    time = columns["Absolute_TIME_s"]
    nominal = grid["step_s"] * np.arange(len(time))
    require(time[0] == display[0] == 0 and max(checks.peak(time-nominal), checks.peak(display-nominal),
            checks.peak(time-display)) <= clock_limit and np.all(np.diff(time) > 0), "Invalid original native clock")
    trace = {key: 1000 * np.column_stack([columns[name] for name in np.asarray(group).flat]).reshape((len(time), *np.shape(group)))
             for key, group in groups.items()}
    trace.update(time_s=time, display_s=display, step_r_ohm=columns["R_step_ohm"],
                 from_cap_a=trace["from_a"] - trace["series_a"], to_cap_a=trace["to_a"] + trace["series_a"])
    require(np.array_equal(trace["step_r_ohm"], checks.resistance(model, grid)), "Native load edge differs")
    return trace


def candidate_trace(factory, model, grid, stop):
    case = factory(time_step=grid["step_s"], stop_time=stop)
    result = run_case(replace(case, output=OutputOptions(show_figure=False), plots=(), summary=None))
    count = grid["rows_including_zero"]
    require(len(result.rows) == count and result.time_step == grid["step_s"] and result.stop_time == stop,
            "Candidate did not record the full original electrical grid")
    buses = model["buses"]
    loads = [load["bus"] for load in model["baseline_loads"]]
    lines = [f"line_{line['from_bus']}{line['to_bus']}" for line in model["lines"]]
    signals = {
        "voltage_v": [[f"v:b{bus}:{p}" for p in PHASES] for bus in buses],
        **{f"{role}_a": [[f"i:{line}:{role}:{p}" for p in PHASES] for line in lines]
           for role in ("series", "from_cap", "to_cap")},
        **{f"load_{name}_a": [[f"i:{kind}load_{bus}_{p}" for p in PHASES] for bus in loads]
           for name, kind in (("resistor", "R"), ("inductor", "L"))},
        "source_a": [f"i:Vsource_{p}" for p in PHASES], "step_a": [f"i:Rstep_{p}" for p in PHASES],
        "time_s": "time", "step_r_ohm": "step_resistance_ohm",
    }
    arrays = {key: np.asarray(names) for key, names in signals.items()}
    signal_names = tuple(name for group in arrays.values() for name in group.flat)
    data = np.fromiter(map(itemgetter(*signal_names), result.rows), dtype=np.dtype((float, len(signal_names))), count=count)
    del result
    require(np.isfinite(data).all() and data[0, -2] == 0, "Candidate requires finite, original initial electrical row")
    trace = {}
    index = 0
    for key, group in arrays.items():
        stop_col = index + group.size
        trace[key] = data[:, index:stop_col].reshape((count, *group.shape))
        index = stop_col
    trace["source_a"] *= -1  # PyCy's branch positive direction enters the source.
    trace["from_a"] = trace["from_cap_a"] + trace["series_a"]
    trace["to_a"] = trace["to_cap_a"] - trace["series_a"]
    require(np.all(np.diff(trace["time_s"]) > 0), "Candidate time does not strictly increase")
    return trace


def run_comparison(destination):
    protocol = frozen_json(PROTOCOL, PROTOCOL_SHA)
    evidence = {}
    contracts = [record_path(protocol[key], evidence) for key in ("native_reference", "native_protocol", "model")]
    qualification, _, model = [json.loads(path.read_bytes()) for path in contracts]
    require(qualification["status"] == "BOTH_PJM5_NATIVE_FULL_GRIDS_PASS" and qualification["native_reference_qualified"]
            and qualification["model"] == protocol["model"] and qualification["prospective_protocol"] == protocol["native_protocol"],
            "Native reference is not qualified for this frozen model")
    cross_path = record_path(qualification["cross_grid_receipt"], evidence)
    paired = json.loads(cross_path.read_bytes())
    originals = qualification["full"]
    require(paired == qualification["cross_grid"] and paired["status"] == "PASS_NATIVE_PJM5_CROSS_GRID"
            and paired["reports_sha256"] == {name: originals[name]["evidence"]["physics"]["sha256"] for name in GRIDS},
            "Original cross-grid release differs")
    grids = protocol["grids"]
    native_inputs = {name: archive(name, grids[name], protocol, originals[name], evidence) for name in GRIDS}
    sources = {EXAMPLE, PROTOCOL, *contracts, ROOT / "pyproject.toml", ROOT / "uv.lock",
               *(ROOT / "pycy_emt_lite").rglob("*.py"), *(ROOT / "validation").rglob("*.py")}
    source_hashes = snapshot_inputs(destination, sources)
    manifest = destination / "inputs.json"
    git_head = subprocess.check_output(["git", "-c", f"safe.directory={ROOT.as_posix()}", "rev-parse", "HEAD"],
                                       cwd=ROOT, text=True).strip()
    save_json(manifest, {"git_head_before_run": git_head, "platform": platform.platform(),
              "python_version": platform.python_version(), "numpy_version": np.__version__, "sources": source_hashes,
              "reference_inputs": {path.relative_to(ROOT).as_posix(): digest for path, digest in evidence.items()}})
    factory = runpy.run_path(str(EXAMPLE))["define_case"]
    results, candidate_plots, native_plots, windows = {}, {}, {}, {}
    for name in GRIDS:
        print(f"Comparing {name}", flush=True)
        target = destination / name
        target.mkdir()
        grid = grids[name]
        candidate = candidate_trace(factory, model, grid, protocol["stop_s"])
        native = read_native(model, native_inputs[name], grid, protocol["electrical_clock_tolerance_s"])
        windows[name] = checks.window_values(model, candidate, grid, protocol["windows_s"])
        native_windows = checks.window_values(model, native, grid, protocol["windows_s"])
        power = checks.compare_windows(windows[name], native_windows, protocol["candidate_window_limits"])
        waveform = checks.same_step(model, protocol, candidate, native)
        physics = checks.physics(model, grid, candidate, protocol["candidate_physical_limits"])
        passed = waveform["passed"] and physics["passed"] and all(row["passed"] for row in power)
        names = ("candidate_waveforms.npz", "reference_waveforms.npz", "raw_differences.npz")
        for path, trace in zip(names, (candidate, native, {key: value - native[key] for key, value in candidate.items()}), strict=True):
            np.savez(target / path, **trace)
        report = target / "report.json"
        save_json(report, {"passed": passed, "grid": grid, "same_step": waveform, "candidate_physics": physics,
                           "candidate_windows": windows[name], "native_windows": native_windows, "power_windows": power,
                           "waveforms_sha256": {path: sha256(target / path) for path in names}})
        results[name] = {"passed": passed, "report_sha256": sha256(report), "rows_with_initial": grid["rows_including_zero"]}
        plotted = ("time_s", "voltage_v", "from_a", "to_a", "series_a")
        candidate_plots[name], native_plots[name] = ({key: data[key] for key in plotted} for data in (candidate, native))
        del candidate, native, trace

    cross = checks.cross_step(model, *[candidate_plots[name] for name in GRIDS], windows, protocol["candidate_cross_grid_limits"])
    figure = destination / "waveform_overlay.png"
    plot_comparison(figure, candidate_plots, native_plots)
    require(all(sha256(ROOT / path) == digest for path, digest in source_hashes.items())
            and all(sha256(path) == digest for path, digest in evidence.items()), "Comparison inputs changed during the run")
    report = destination / "report.json"
    passed = cross["passed"] and all(row["passed"] for row in results.values())
    save_json(report, {"passed": passed, "reference_platform": "PSCAD 5.0.0 / EMTDC 5", "grids": results,
                      "candidate_cross_grid": cross, "inputs_sha256": sha256(manifest), "figure_sha256": sha256(figure)})
    return report, passed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, help="Fresh directory under local_reference")
    args = parser.parse_args()
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    destination = (args.run_dir or CACHE / f"case33_comparison_{stamp}").resolve()
    require(destination.is_relative_to(CACHE.resolve()) and destination != CACHE.resolve(), "Output must be below local_reference")
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
