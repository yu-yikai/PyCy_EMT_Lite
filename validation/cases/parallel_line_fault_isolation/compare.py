"""Compare the public three-bus example against both original PSCAD runs."""

import argparse
import platform
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from runpy import run_path

import matplotlib
import numpy as np

from pycy_emt_lite import OutputOptions, run_case
from validation.cases.grid_connected_vsc_closed_loop.compare import frozen_json
from validation.cases.grid_connected_vsc_open_loop.compare import save_json
from validation.cases.grid_connected_vsc_open_loop.metrics import require
from validation.common.runner import sha256
from validation.common.snapshot import snapshot_sources, verify_inputs

from . import checks
from .reference import read_reference

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CACHE = ROOT / "local_reference"
PROTOCOL = HERE / "candidate_protocol.json"
PROTOCOL_SHA = "e1644873c2b23c367af0cbd109c4e62b6dbb6c3114358851016987b0facf20fb"
EXAMPLE = ROOT / "examples/38_parallel_line_fault_isolation.py"
FIELDS = {
    "v_src": "v:src_{}", "v_recv": "v:recv_{}", "v_fault": "v:fault_{}",
    "i_healthy": "i:Healthy:{}", "i_load": "i:Load:{}", "i_ref": "i:Reference:{}",
    "i_sf": "i:SF_{}", "i_rf": "i:RF_{}", "i_fault": "i:Fault_{}",
}


def trace_from_result(result, fixture):
    """Read actual three-pole states before reducing them to common resistance words."""
    time = result.series("time")
    trace = {"display_s": time, "time_s": time}
    trace.update({name: np.column_stack([result.series(field.format(phase)) for phase in "abc"])
                  for name, field in FIELDS.items()})
    for label, component, resistance in (
        ("sf", "SF", "path_on_ohm"), ("rf", "RF", "path_on_ohm"), ("fault", "Fault", "fault_on_ohm"),
    ):
        poles = np.column_stack([result.series(f"state:{component}_{phase}") for phase in "abc"])
        require(np.isin(poles, (0, 1)).all() and np.all(poles == poles[:, :1]), f"Invalid {label} pole states")
        trace[f"R_{label}_ohm"] = np.where(poles[:, 0], fixture[resistance], fixture["open_ohm"])
    return trace


def candidate_trace(factory, grid, protocol):
    example = protocol["example"]
    step, stop = grid["step_s"], example["stop_s"]
    case = factory(time_step=step, stop_time=stop)
    result = run_case(replace(case, plots=(), output=OutputOptions(show_figure=False)))
    require(case.name == example["case"] and result.method == "trapezoidal"
            and result.time_step == step and result.stop_time == stop
            and len(result.rows) == grid["rows_including_zero"], "Unexpected public candidate or electrical grid")
    return trace_from_result(result, protocol["fixture"])


def plot_comparison(path, curves, protocol):
    matplotlib.use("Agg")
    from matplotlib import pyplot as plt

    timing = protocol["timing"]
    figure, axes = plt.subplots(2, 2, sharex=True, sharey="row", figsize=(11.8, 6.6), layout="constrained")
    figure.suptitle("Three-bus parallel line fault and restoration")
    for column, (grid, traces) in enumerate(curves.items()):
        axes[0, column].set_title(f'{protocol["grids"][grid]["step_s"] * 1e6:g} µs')
        for platform_name, color, style in (("PSCAD", "#17576a", "-"), ("PyCy", "#bb581e", "--")):
            trace = traces[platform_name]
            t, voltage = 1000 * trace["time_s"], trace["v_src"]
            signed_rf = np.mean(trace["i_rf"] * voltage, axis=1) / np.sqrt(np.mean(voltage**2, axis=1))
            axes[0, column].step(t, checks.load_power(trace) / 1000, where="post", color=color, linestyle=style,
                                 label=platform_name, linewidth=1.3)
            axes[1, column].step(t, signed_rf, where="post", color=color, linestyle=style, linewidth=1.3)
        for axis in axes[:, column]:
            for event in ("fault_on_s", "open_sf_s", "open_rf_s", "fault_off_s", "reclose_s"):
                axis.axvline(1000 * timing[event], color="#647984", linestyle=":", linewidth=.9)
            axis.axvspan(1000 * timing["open_rf_s"], 1000 * timing["reclose_s"], color="#e4edeb", zorder=0)
            axis.set_xlim(0, 1000 * timing["duration_s"])
            axis.grid(alpha=.25)
        axes[1, column].axhline(0, color="#647984", linewidth=.7)
        axes[1, column].set_xlabel("Time (ms)")
    axes[0, 0].set_ylabel("Receiving load power (kW)")
    axes[1, 0].set_ylabel("Receiver → fault (A RMS, signed)")
    axes[0, 0].legend(loc="lower right")
    figure.savefig(path, dpi=145)
    plt.close(figure)


def run_comparison(destination):
    destination = destination.resolve()
    require(destination.is_relative_to(CACHE.resolve()) and not destination.exists(),
            "Choose a fresh run directory under local_reference")
    started = datetime.now(UTC).isoformat()
    destination.mkdir(parents=True, exist_ok=False)
    inputs = destination / "inputs"
    source_hashes, source_report = snapshot_sources(ROOT, inputs, EXAMPLE, PROTOCOL)
    protocol = frozen_json(PROTOCOL, PROTOCOL_SHA)
    factory = run_path(str(EXAMPLE))["define_case"]
    evidence, grids, curves = {}, {}, {}

    for name, grid in protocol["grids"].items():
        step = grid["step_s"]
        native = read_reference(protocol, name, evidence)
        candidate = candidate_trace(factory, grid, protocol)
        reports = {
            "native_physics": checks.evaluate(native, step, protocol),
            "candidate_physics": checks.evaluate(candidate, step, protocol),
            "same_grid": checks.same_grid(candidate, native, step, protocol),
        }
        grids[name] = {"passed": all(report["passed"] for report in reports.values()), **reports}
        np.savez_compressed(destination / f"pycy_{name}.npz", **candidate)
        curves[name] = {"PSCAD": native, "PyCy": candidate}
        print(f'{name} {"PASS" if grids[name]["passed"] else "FAIL"}', flush=True)
    paired = checks.cross_grid(curves["50us"]["PyCy"], curves["25us"]["PyCy"], protocol)
    plot_comparison(destination / "waveform_overlay.png", curves, protocol)
    result = {
        "case": protocol["example"]["case"], **source_report,
        "started_utc": started, "finished_utc": datetime.now(UTC).isoformat(),
        "python": platform.python_version(), "numpy": np.__version__, "platform": platform.platform(),
        "reference_platform": "PSCAD 5.0.0 / EMTDC 20210219 (gf46)", "time_shift_s": 0,
        "passed": all(grid["passed"] for grid in grids.values()) and paired["passed"],
        "grids": grids, "cross_grid": paired,
        "admitted_reference_sha256": {path.relative_to(ROOT).as_posix(): digest for path, digest in evidence.items()},
        "artifacts": {file.name: sha256(file) for file in sorted(destination.iterdir()) if file.is_file()},
    }
    verify_inputs(ROOT, inputs, source_hashes, evidence)
    save_json(destination / "report.json", result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    args = parser.parse_args()
    report = run_comparison(args.run_dir)
    print(f'{"PASS" if report["passed"] else "FAIL"} {args.run_dir / "report.json"}')
    return int(not report["passed"])


if __name__ == "__main__":
    raise SystemExit(main())
