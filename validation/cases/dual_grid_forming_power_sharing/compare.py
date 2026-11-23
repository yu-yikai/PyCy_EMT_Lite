"""Compare both public dual-source island runs with their original PSCAD rows."""

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
PROTOCOL_SHA = "47c2789c151bb4209256dba5ccb8492d1c9bfcceb33110269292d8b3c3903150"
EXAMPLE = ROOT / "examples/39_dual_grid_forming_power_sharing.py"


def trace_from_result(result, fixture):
    """Read solved phases, feeder currents, control outputs and all three load poles."""
    def series(pattern, labels):
        return np.column_stack([result.series(pattern.format(label)) for label in labels])

    time = result.series("time")
    poles = series("state:Added_{}", "abc")
    require(np.isin(poles, (0, 1)).all() and np.all(poles == poles[:, :1]), "Candidate load poles disagree")
    resistance = np.where(poles[:, 0], fixture["added_load_ohm"], fixture["open_load_ohm"])
    require(np.array_equal(poles[:, 0], result.series("load_on"))
            and np.array_equal(resistance, result.series("load_r")), "Candidate load observations disagree with solved poles")
    return {
        "display_s": time, "time_s": time, "peak_v": result.series("peak_v"),
        "load_r": resistance, "load_on": poles[:, 0], "load_states": poles.astype(np.uint8),
        "phase_rad": series("phase_{}_rad", "ab"),
        "frequency_hz": series("frequency_{}_hz", "ab"),
        "meter_w": series("power_{}_w", "ab"),
        "filtered_w": series("filtered_{}_w", "ab"),
        "source_v": np.stack([series(f"v:src_{site}_{{}}", "abc") for site in "ab"], axis=1),
        "feeder_a": np.stack([series(f"i:FeederL_{site}_{{}}", "abc") for site in "ab"], axis=1),
        "pcc_v": series("v:pcc_{}", "abc"),
        "base_a": series("i:Base_{}", "abc"),
        "added_a": series("i:Added_{}", "abc"),
    }


def plot_comparison(path, curves, protocol):
    matplotlib.use("Agg")
    from matplotlib import pyplot as plt

    figure, axes = plt.subplots(3, 2, sharex=True, sharey="row", figsize=(11.4, 7.4), layout="constrained")
    figure.suptitle("Dual grid-forming sources · PSCAD and PyCy")
    timing = protocol["timing"]
    for col, (grid, traces) in enumerate(curves.items()):
        axes[0, col].set_title(f'{protocol["grids"][grid]["step_s"] * 1e6:g} µs')
        for platform_name, style in (("PSCAD", "-"), ("PyCy", "--")):
            trace = traces[platform_name]
            time = 1000 * trace["time_s"]
            power = checks.pcc_powers(trace)
            for index, (site, color) in enumerate((("A", "#17576a"), ("B", "#b4512c"))):
                axes[0, col].plot(time, power[:, index], color=color, linestyle=style, label=f"{site} · {platform_name}")
                axes[1, col].plot(time, trace["frequency_hz"][:, index], color=color, linestyle=style)
            phase = 1000 * (trace["phase_rad"][:, 0] - trace["phase_rad"][:, 1])
            axes[2, col].plot(time, phase, color="#46576d", linestyle=style)
        for axis in axes[:, col]:
            axis.axvline(1000 * timing["load_step_s"], color="#607482", linestyle=":", linewidth=.9)
            for first, last in timing["windows_s"].values():
                axis.axvspan(1000 * first, 1000 * last, color="#e6edef", zorder=0)
            axis.set_xlim(0, 1000 * timing["duration_s"])
            axis.grid(alpha=.24)
        axes[2, col].set_xlabel("Time (ms)")
    for row, label in enumerate(("PCC active power (W)", "Source frequency (Hz)", "Phase A − B (mrad)")):
        axes[row, 0].set_ylabel(label)
    axes[0, 0].legend(loc="lower right", ncols=2, frameon=False)
    figure.savefig(path, dpi=155)
    plt.close(figure)


def run_comparison(destination):
    destination = destination.resolve()
    require(destination.is_relative_to(CACHE.resolve()) and not destination.exists(),
            "Choose a fresh run directory under local_reference")
    started = datetime.now(UTC).isoformat()
    destination.mkdir(parents=True, exist_ok=False)
    inputs = destination / "inputs"
    sources, source_report = snapshot_sources(ROOT, inputs, EXAMPLE, PROTOCOL)
    protocol = frozen_json(PROTOCOL, PROTOCOL_SHA)
    example = protocol["example"]
    factory = run_path(str(EXAMPLE))["define_case"]
    evidence, grids, curves = {}, {}, {}

    for name, grid in protocol["grids"].items():
        step, stop = grid["step_s"], example["stop_s"]
        native = read_reference(protocol, name, evidence)
        case = factory(time_step=step, stop_time=stop)
        result = run_case(replace(case, plots=(), output=OutputOptions(show_figure=False)))
        require(case.name == example["case"] and result.method == "trapezoidal"
                and result.time_step == step and result.stop_time == stop
                and len(result.rows) == grid["rows_including_zero"], "Unexpected public case or grid")
        candidate = trace_from_result(result, protocol["fixture"])
        del result
        reports = {
            "native_physics": checks.evaluate(native, step, protocol),
            "candidate_physics": checks.evaluate(candidate, step, protocol),
            "same_grid": checks.same_grid(candidate, native, step, protocol),
        }
        passed = all(report["passed"] for report in reports.values())
        grids[name] = {"passed": passed, **reports}
        np.savez_compressed(destination / f"pycy_{name}.npz", **candidate)
        curves[name] = {"PSCAD": native, "PyCy": candidate}
        print(f'{name} {"PASS" if passed else "FAIL"}', flush=True)

    paired = checks.cross_grid(curves["5us"]["PyCy"], curves["2p5us"]["PyCy"], protocol)
    plot_comparison(destination / "waveform_overlay.png", curves, protocol)
    report = {
        "case": example["case"], **source_report,
        "started_utc": started, "finished_utc": datetime.now(UTC).isoformat(),
        "python": platform.python_version(), "numpy": np.__version__, "platform": platform.platform(),
        "reference_platform": "PSCAD 5.0.0 / EMTDC 20210219 (gf46)", "time_shift_s": 0,
        "passed": all(grid["passed"] for grid in grids.values()) and paired["passed"],
        "grids": grids, "cross_grid": paired,
        "admitted_reference_sha256": {path.relative_to(ROOT).as_posix(): digest for path, digest in evidence.items()},
        "artifacts": {file.name: sha256(file) for file in sorted(destination.iterdir()) if file.is_file()},
    }
    verify_inputs(ROOT, inputs, sources, evidence)
    save_json(destination / "report.json", report)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    args = parser.parse_args()
    report = run_comparison(args.run_dir)
    print(f'{"PASS" if report["passed"] else "FAIL"} {args.run_dir / "report.json"}')
    raise SystemExit(int(not report["passed"]))
