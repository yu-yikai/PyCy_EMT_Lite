"""Validate the teaching example against the two original PSCAD island runs."""

import argparse
import platform
import shutil
import subprocess
from dataclasses import replace
from datetime import UTC, datetime
from operator import itemgetter
from pathlib import Path
from runpy import run_path

import matplotlib
import numpy as np

from pycy_emt_lite import OutputOptions, run_case
from validation.cases.grid_connected_vsc_closed_loop.compare import frozen_json
from validation.cases.grid_connected_vsc_open_loop.compare import save_json
from validation.cases.grid_connected_vsc_open_loop.metrics import require
from validation.common.runner import sha256

from . import checks
from .reference import read_reference

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CACHE = ROOT / "local_reference"
PROTOCOL = HERE / "candidate_protocol.json"
PROTOCOL_SHA = "e98afbabbeb2e3dd3dfd3841d607563a1a8d31371bf49ea71b5f13b9b32ab1f4"
EXAMPLE = ROOT / "examples/37_islanded_frequency_droop.py"

FIELDS = {
    "time_s": ("time",),
    "peak_v": ("source_peak_v",),
    "phase_rad": ("source_phase_rad",),
    "frequency_hz": ("frequency_hz",),
    "meter_w": ("pcc_power_w",),
    "filtered_w": ("filtered_power_w",),
    "load_resistance_ohm": ("added_resistance_ohm",),
    "load_on": ("added_load_on",),
    **{key: tuple(f"{prefix}{phase}" for phase in "abc") for key, prefix in (
        ("source_v", "v:src_"), ("pcc_v", "v:pcc_"), ("feeder_a", "i:FeederL_"),
        ("base_a", "i:Base_"), ("added_a", "i:Added_"),
    )},
}


def trace_from_result(result, count):
    """Project solved rows without aligning, downsampling or replaying control."""
    fields = tuple(field for group in FIELDS.values() for field in group)
    data = np.fromiter(map(itemgetter(*fields), result.rows), dtype=np.dtype((float, len(fields))), count=count)
    require(np.isfinite(data).all(), "Nonfinite island result")
    trace, first = {}, 0
    for key, group in FIELDS.items():
        last = first + len(group)
        trace[key] = data[:, first] if last - first == 1 else data[:, first:last]
        first = last
    trace["display_s"] = trace["time_s"]
    return trace


def candidate_trace(factory, profile, protocol):
    example = protocol["example"]
    step, stop, count = profile["step_s"], example["stop_s"], profile["rows_including_zero"]
    case = factory(time_step=step, stop_time=stop)
    require(case.name == example["case"], "Unexpected island candidate")
    result = run_case(replace(case, output=OutputOptions(show_figure=False), plots=()))
    require((len(result.rows), result.time_step, result.stop_time, result.method) == (count, step, stop, "trapezoidal"),
            "Candidate did not use the frozen electrical grid")
    return trace_from_result(result, count)


def plot_comparison(path, curves, protocol):
    matplotlib.use("Agg")
    from matplotlib import pyplot as plt

    figure, axes = plt.subplots(2, 2, sharex=True, sharey="row", figsize=(11.8, 6.6), layout="constrained")
    figure.suptitle("Island frequency droop after adding a balanced load")
    for column, (grid, results) in enumerate(curves.items()):
        axes[0, column].set_title(f'{protocol["grids"][grid]["step_s"] * 1e6:g} µs')
        for platform_name, color, style in (("PSCAD", "#17576a", "-"), ("PyCy", "#ad5226", "--")):
            time, power, frequency = results[platform_name]
            axes[0, column].plot(1000 * time, power, style, color=color, linewidth=1.3, label=platform_name)
            axes[1, column].plot(1000 * time, frequency, style, color=color, linewidth=1.3)
        axes[1, column].set_xlabel("Time (ms)")
        for axis in axes[:, column]:
            timing = protocol["timing"]
            axis.axvline(1000 * timing["load_step_s"], color="#647984", linestyle=":", linewidth=.9)
            for window in timing["windows_s"].values():
                axis.axvspan(*(1000 * edge for edge in window), color="#e4ebef", zorder=0)
            axis.grid(alpha=.25)
            axis.set_xlim(0, 1000 * timing["duration_s"])
    axes[0, 0].set_ylabel("PCC active power (W)")
    axes[1, 0].set_ylabel("Source frequency (Hz)")
    axes[0, 0].legend(loc="lower right")
    figure.savefig(path, dpi=145)
    plt.close(figure)


def run_comparison(destination):
    destination = destination.resolve()
    require(destination.is_relative_to(CACHE.resolve()) and not destination.exists(),
            "Choose a fresh run directory under local_reference")
    protocol = frozen_json(PROTOCOL, PROTOCOL_SHA)
    factory = run_path(str(EXAMPLE))["define_case"]
    source_files = (
        EXAMPLE, PROTOCOL, Path(__file__), HERE / "checks.py", HERE / "reference.py",
        ROOT / "pyproject.toml", ROOT / "uv.lock", *sorted((ROOT / "pycy_emt_lite").rglob("*.py")),
    )
    sources = {path: sha256(path) for path in source_files}
    git = ["git", "-c", f"safe.directory={ROOT.as_posix()}"]
    head = subprocess.check_output([*git, "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    started = datetime.now(UTC).isoformat()
    evidence, grids, curves, candidates = {}, {}, {}, {}
    destination.mkdir(parents=True, exist_ok=False)
    for path, digest in sources.items():
        copy = destination / "inputs" / path.relative_to(ROOT)
        copy.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, copy)
        require(sha256(copy) == digest, f"Comparison input changed: {path.name}")

    for grid, profile in protocol["grids"].items():
        step = profile["step_s"]
        native = read_reference(protocol, grid, evidence)
        candidate = candidate_trace(factory, profile, protocol)
        reports = {
            "native_physics_and_control": checks.evaluate(native, step, protocol),
            "candidate_physics_and_control": checks.evaluate(candidate, step, protocol),
            "same_grid": checks.same_grid(candidate, native, step, protocol),
        }
        grids[grid] = {"passed": all(report["passed"] for report in reports.values()), **reports}
        traces = {"PSCAD": native, "PyCy": candidate}
        curves[grid] = {
            name: (trace["time_s"], np.sum(trace["pcc_v"] * trace["feeder_a"], axis=1), trace["frequency_hz"])
            for name, trace in traces.items()
        }
        np.savez_compressed(destination / f"pycy_{grid}.npz", **candidate)
        candidates[grid] = candidate
        print(f'{grid} {"PASS" if grids[grid]["passed"] else "FAIL"}', flush=True)
    paired = checks.cross_grid(candidates["5us"], candidates["2p5us"], protocol)
    require(all(sha256(path) == digest for path, digest in (sources | evidence).items()),
            "An input changed during comparison")

    plot_comparison(destination / "waveform_overlay.png", curves, protocol)
    report = {
        "case": protocol["example"]["case"], "source_head": head,
        "started_utc": started, "finished_utc": datetime.now(UTC).isoformat(),
        "python": platform.python_version(), "numpy": np.__version__, "platform": platform.platform(),
        "reference_platform": "PSCAD 5.0.0 / EMTDC 20210219 (gf46)", "time_shift_s": 0,
        "passed": all(result["passed"] for result in grids.values()) and paired["passed"],
        "grids": grids, "cross_grid": paired,
        "source_sha256": {path.relative_to(ROOT).as_posix(): digest for path, digest in sources.items()},
        "admitted_reference_sha256": {path.relative_to(ROOT).as_posix(): digest for path, digest in evidence.items()},
        "artifacts": {path.name: sha256(path) for path in sorted(destination.iterdir()) if path.is_file()},
    }
    save_json(destination / "report.json", report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    args = parser.parse_args()
    report = run_comparison(args.run_dir)
    print(f'{"PASS" if report["passed"] else "FAIL"} {args.run_dir / "report.json"}')
    return int(not report["passed"])


if __name__ == "__main__":
    raise SystemExit(main())
