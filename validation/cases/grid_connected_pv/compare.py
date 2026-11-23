"""Compare the public photovoltaic example against both original PSCAD runs."""

import argparse
import json
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
from validation.cases.grid_connected_vsc_open_loop.compare import save_json
from validation.cases.grid_connected_vsc_open_loop.metrics import require
from validation.common.runner import sha256

from . import checks
from .reference import read_reference

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CACHE = ROOT / "local_reference"
PROTOCOL = HERE / "candidate_protocol.json"
PROTOCOL_SHA = "edbcb130ad8d2310bf65cf068fc987ddfa83e0641b29f3d1d76035374e1685c5"
EXAMPLE = ROOT / "examples/36_grid_connected_pv.py"
PHASES = "abc"

FIELDS = {
    "time_s": ("time",), "bus_v": ("v:Cdc",), "pv_a": ("pv_delivered_a",), "bus_cap_a": ("i:Cdc",),
    "load_a": ("i:Rload",), "star_v": ("v:a_star",), "negative_v": ("v:a_n",),
    "irradiance_w_m2": ("irradiance_w_m2",), "measured_export_w": ("pcc_export_w",),
    "measured_q_var": ("pcc_q_var",), "measured_pv_w": ("pv_delivered_w",),
    **{f"{name}_v": tuple(f"v:a_{node}_{phase}" for phase in PHASES)
       for name, node in (("source", "grid"), ("pcc", "pcc"), ("pole", "pole"))},
    "feed_a": tuple(f"i:a_Lg{phase}" for phase in PHASES),
    "phase_a": tuple(f"i:a_L{phase}" for phase in PHASES),
    **{f"{side}_a": tuple(f"i:a_S{phase}_{side}" for phase in PHASES) for side in ("upper", "lower")},
    **{f"{side}_on": tuple(f"state:a_S{phase}_{side}" for phase in PHASES) for side in ("upper", "lower")},
    **{key: tuple(f"a_{key}_{phase}" for phase in PHASES) for key in ("applied", "pending")},
    **{key: (f"a_{signal}",) for key, signal in {
        "j": "j", "gate_tick": "gate_tick", "sample": "sample_update", "outer": "outer_due",
        "enabled": "outer_enabled", "ip_ref_a": "ip_ref_a", "dc_integrator": "dc_integrator",
        "filtered_d_v": "filtered_pcc_d_v", "filtered_q_v": "filtered_pcc_q_v", "filtered_rms_v": "pcc_filtered_rms_v",
        "id_ref_a": "id_ref", "iq_ref_a": "iq_ref", "theta_rad": "theta", "omega_rad_s": "pll_omega",
        "carrier": "carrier_applied", "saturated": "saturated", "pll_integrator": "pll_xi",
        "d_integrator": "z_d", "q_integrator": "z_q",
    }.items()},
}


def candidate_trace(factory, grid, protocol):
    """Run the same CaseDefinition as the teaching entry and project its original rows."""
    step, count = grid["step_s"], grid["candidate_rows_including_initial"]
    stop, method = protocol["example"]["stop_s"], protocol["schedule"]["integration"]
    case = factory(time_step=step, stop_time=stop)
    require(case.name == protocol["example"]["case"], "Unexpected example name")
    result = run_case(replace(case, output=OutputOptions(show_figure=False), plots=()))
    require((len(result.rows), result.time_step, result.stop_time, result.method) == (count, step, stop, method),
            "The example did not record the frozen electrical grid")
    keys = tuple(field for fields in FIELDS.values() for field in fields)
    values = np.fromiter(map(itemgetter(*keys), result.rows), dtype=np.dtype((float, len(keys))), count=count)
    require(np.isfinite(values).all(), "The example produced nonfinite values")
    trace, start = {}, 0
    for name, fields in FIELDS.items():
        end = start + len(fields)
        trace[name] = values[:, start] if end - start == 1 else values[:, start:end]
        start = end

    trace["source_v"] -= trace["star_v"][:, None]
    trace["pcc_v"] -= trace["star_v"][:, None]
    trace["pole_v"] -= trace["negative_v"][:, None]
    trace["star_v"] -= trace.pop("negative_v")
    for key in ("upper_on", "lower_on", "sample", "outer", "enabled", "saturated"):
        require(np.isin(trace[key], (0., 1.)).all(), f"Unexpected Boolean state: {key}")
        trace[key] = trace[key].astype(bool)
    return trace


def curves(trace, step):
    """Keep raw voltage; display power as non-overlapping 5 ms averages."""
    power = checks.power(trace)
    width = round(.005 / step)
    stop = len(trace["time_s"]) // width * width
    means = [trace["time_s"], power["export_w"], power["pv_power_w"]]
    averaged = [value[:stop].reshape(-1, width).mean(axis=1) for value in means]
    return averaged, trace["time_s"], trace["bus_v"]


def plot_comparison(destination, displays, protocol):
    matplotlib.use("Agg")
    from matplotlib import pyplot as plt

    figure, axes = plt.subplots(2, len(displays), sharex=True, sharey="row", figsize=(12, 6.6), layout="constrained")
    figure.suptitle("Grid-connected PV during a 1000 to 900 W/m² irradiance step")
    for column, (grid, models) in enumerate(displays.items()):
        axes[0, column].set_title(f'{protocol["grids"][grid]["step_s"] * 1e6:g} µs')
        for platform_name, style in (("PSCAD", "-"), ("PyCy", "--")):
            (time, exported, pv), original_time, bus = models[platform_name]
            axes[0, column].plot(1000 * time, exported, style, color="#18576c", label=f"{platform_name} export")
            axes[0, column].plot(1000 * time, pv, style, color="#ad5226", label=f"{platform_name} PV")
            axes[1, column].plot(1000 * original_time, bus, style, color="#18576c", label=platform_name)
        axes[1, column].axhline(protocol["schedule"]["dc_reference_v"], color="#647984", linestyle=":", linewidth=.9)
        axes[1, column].set_xlabel("Time after precharge (ms)")
        for axis in axes[:, column]:
            axis.axvline(1000 * protocol["schedule"]["irradiance_step_s"], color="#647984", linestyle=":", linewidth=.9)
            for window in ("before", "after"):
                axis.axvspan(*(1000 * edge for edge in protocol["windows_s"][window]), color="#e4ebef", zorder=0)
            axis.set_xlim(0, 1000)
            axis.grid(alpha=.25)
    axes[0, 0].set_ylabel("Active power (W)\n5 ms averages")
    axes[1, 0].set_ylabel("DC bus voltage (V)")
    axes[0, 0].legend(loc="lower right", fontsize=8)
    axes[1, 0].legend(loc="upper right", fontsize=8)
    figure.savefig(destination, dpi=145)
    plt.close(figure)


def run_comparison(destination):
    destination = destination.resolve()
    require(destination.is_relative_to(CACHE.resolve()) and not destination.exists(),
            "Choose a fresh run directory under local_reference")
    require(sha256(PROTOCOL) == PROTOCOL_SHA, "The frozen PV protocol changed")
    protocol = json.loads(PROTOCOL.read_bytes())
    example = run_path(str(EXAMPLE))["define_case"]
    source_files = (EXAMPLE, PROTOCOL, Path(__file__), HERE / "checks.py", HERE / "reference.py",
                    ROOT / "uv.lock", ROOT / "pyproject.toml", *sorted((ROOT / "pycy_emt_lite").rglob("*.py")))
    source_hashes = {path: sha256(path) for path in source_files}
    git = ["git", "-c", f"safe.directory={ROOT.as_posix()}"]
    started = datetime.now(UTC).isoformat()
    head = subprocess.check_output([*git, "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    evidence, grids, displays = {}, {}, {}
    destination.mkdir(parents=True, exist_ok=False)
    for path, expected in source_hashes.items():
        copy = destination / "inputs" / path.relative_to(ROOT)
        copy.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, copy)
        require(sha256(copy) == expected, "A calculation input changed before snapshot")
    for name, grid in protocol["grids"].items():
        step = grid["step_s"]
        original = read_reference(protocol, name, evidence)
        if "auxiliary_a" in original:
            original["pre_a"] = original["auxiliary_a"]
        candidate = candidate_trace(example, grid, protocol)
        reports = {
            "initial": checks.initial(candidate, original, grid, protocol),
            "candidate_physics": checks.physics(candidate, step, protocol),
            "native_physics": checks.physics(original, step, protocol),
            "candidate_timing": checks.timing(candidate, step, protocol),
            "same_grid": checks.same_grid(candidate, original, step, protocol),
        }
        grids[name] = {"candidate_rows": len(candidate["time_s"]), "native_positive_rows": len(original["time_s"]) - 1,
                       "passed": all(report["passed"] for report in reports.values()), **reports}
        np.savez_compressed(destination / f"pycy_{name}.npz", **candidate)
        displays[name] = {"PyCy": curves(candidate, step), "PSCAD": curves(original, step)}
        print(f'{name}: {"PASS" if grids[name]["passed"] else "FAIL"}', flush=True)
        del candidate, original
    cross_grid = checks.cross_grid(grids["5us"]["same_grid"], grids["2p5us"]["same_grid"], protocol)
    require(all(sha256(path) == expected for path, expected in (source_hashes | evidence).items()),
            "A comparison input changed during the run")
    plot_comparison(destination / "waveform_overlay.png", displays, protocol)
    result = {
        "case": protocol["example"]["case"], "source_head": head, "started_utc": started,
        "finished_utc": datetime.now(UTC).isoformat(),
        "python": platform.python_version(), "numpy": np.__version__, "platform": platform.platform(),
        "reference_platform": "PSCAD 5.0.0 / EMTDC 20210219 (gf46)", "time_shift_s": 0,
        "passed": all(grid["passed"] for grid in grids.values()) and cross_grid["passed"],
        "grids": grids, "cross_grid": cross_grid,
        "source_sha256": {path.relative_to(ROOT).as_posix(): sha for path, sha in source_hashes.items()},
        "admitted_reference_sha256": {path.relative_to(ROOT).as_posix(): sha for path, sha in evidence.items()},
        "artifacts": {path.name: sha256(path) for path in sorted(destination.iterdir()) if path.is_file()},
    }
    save_json(destination / "report.json", result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    args = parser.parse_args()
    result = run_comparison(args.run_dir)
    print(f'{"PASS" if result["passed"] else "FAIL"} {args.run_dir / "report.json"}')
    return int(not result["passed"])


if __name__ == "__main__":
    raise SystemExit(main())
