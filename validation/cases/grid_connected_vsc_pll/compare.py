"""Compare fresh example 30 runs with the sealed full PSCAD reference."""

import argparse
import json
import platform
import runpy
import subprocess
from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal, localcontext
from math import asin, pi, sqrt, tau
from pathlib import Path
from time import monotonic

import matplotlib
import numpy as np

from pycy_emt_lite import OutputOptions, run_case
from validation.cases.grid_connected_vsc_closed_loop import compare as dq_case
from validation.cases.grid_connected_vsc_open_loop import binding, metrics, physics
from validation.cases.grid_connected_vsc_open_loop.compare import (
    PlantRows,
    Projection,
    save_json,
    write_plant,
)
from validation.common.runner import sha256

ROOT = dq_case.ROOT
DIRECTORY = Path(__file__).resolve().parent
CACHE = ROOT / "local_reference"
EXAMPLE = ROOT / "examples/30_grid_connected_vsc_pll.py"
PROTOCOL_SHA = "78ba092cc8099390023d3fcaa449c8479d269dcd5fa7ec315b267d968e1da767"
QUALIFICATION_SHA = "255e251c54c3146bc13a26a528c200e8af80e78cf3e1a1a62707afef66a9789d"
TIME = dq_case.TIME
PLL_FIELDS = {
    "theta": ("theta", "theta_circular_rad"),
    "omega": ("pll_omega", "omega_rad_s"),
    "xi": ("pll_xi", "xi_rad_s"),
    "normalized_error": ("pll_error", "normalized_error"),
}


def load_reference(protocol, current, qualification, plant_sha):
    """Read the qualified SI projections only after checking original archive identity."""
    metrics.require(qualification["whole_native_reference_qualified"] is True
                    and qualification["protocol"]["sha256"] == PROTOCOL_SHA, "PLL reference is not qualified")
    native, evidence = {}, {}

    def admit(path, digest, size=None):
        path = path.resolve(strict=True)
        metrics.require(path.is_relative_to(CACHE.resolve()) and (size is None or path.stat().st_size == size)
                        and sha256(path) == digest, f"Changed or invalid reference input: {path}")
        evidence[path] = digest
        return path

    def load(record):
        path = admit(ROOT/record["path"], record["sha256"], record["bytes"])
        return path, json.loads(path.read_bytes())

    _, pair = load(qualification["cross_grid"]["report"])
    metrics.require(pair["status"] == "PASS_NATIVE_PLL_FULL_CROSS_GRID"
                    and pair["protocol_sha256"] == PROTOCOL_SHA and pair["comparison"]["passed"] is True,
                    "Original native cross-grid gate did not pass")
    stem = current["native_output"]["stem"]
    expected_raw = {f"{stem}.inf", current["native_output"]["feedback"],
                    *(f"{stem}_{part:02d}.out" for part in range(1, 6))}
    samples = protocol["acquisition"]["full"]["control_samples_and_next_gate_applications_each"]
    for grid in current["electrical_grids"]:
        label, rows, step = grid["id"], grid["rows"], grid["step_s"]
        expected_updates = list(range(round(protocol["pll"]["sample_period_s"]/step), rows,
                                      round(protocol["pll"]["sample_period_s"]/step)))
        gate_ticks = round(current["controller"]["gate_period_s"]/step)
        entry = qualification["grids"][label]
        execution_path, execution = load(entry["execution_receipt"])
        numeric_path, numeric = load(entry["numerical_report"])
        run = execution_path.parent
        runtime = execution["native_runtime"]
        archive = run / "project/vdiv.gf46"
        metrics.require(execution["status"] == "NATIVE_PLL_FULL_RUN_CLOSED_FOR_NUMERIC_REVIEW"
                        and execution["protocol_sha256"] == PROTOCOL_SHA
                        and execution["rows"] == rows == entry["rows"]
                        and execution["all_out_clocks_exact_on_original_grid"] is True
                        and execution["sample_updates"] == expected_updates
                        and execution["expected_next_gate_applications"] == [j + gate_ticks for j in expected_updates]
                        and runtime["emtdc_pid_observed"] is True
                        and runtime["emtdc_process_identity"]["name"].lower() == "vdiv.exe"
                        and set(execution["raw_files"]) == expected_raw, f"Invalid execution evidence: {label}")
        terminal = json.loads(admit(run/"terminal.json", execution["terminal_sha256"]).read_bytes())
        generated = json.loads(admit(run/"pre_run_admission.json", execution["pre_run_admission_sha256"]).read_bytes())
        build_status = "PASS_PLL_FULL_5US_GENERATED" if label == "5us" else "PASS_PLL_FULL_GENERATED"
        metrics.require(terminal["worker_returncode"] == 0 and terminal["source_hash_unchanged"] is True
                        and terminal["stop_reason"] is None and not terminal["remaining_owned"]
                        and generated["status"] == build_status, f"Invalid build or closeout: {label}")
        for name, digest in (execution["raw_files"] | execution["post_run_generated_sha256"]).items():
            admit(archive/name, digest)
        for name, digest in runtime["vendor_run_artifacts_sha256"].items():
            admit(run/name, digest)
        anchor = {"path": entry["execution_receipt"]["path"], "sha256": entry["execution_receipt"]["sha256"],
                  "raw_files": execution["raw_files"]}
        metrics.require(numeric["status"] == "PASS_NATIVE_PLL_FULL_NUMERICAL"
                        and numeric["protocol_sha256"] == PROTOCOL_SHA and numeric["physical_protocol_sha256"] == plant_sha
                        and numeric["execution_receipt"] == anchor and pair["references"][label]["execution"] == anchor
                        and pair["references"][label]["sha256"] == entry["numerical_report"]["sha256"]
                        and (numeric["electrical_grid"], numeric["rows"], numeric["step_s"]) == (label, rows, step)
                        and numeric["pll_updates"] == numeric["next_gate_applications"] == samples
                        and numeric["physical"]["observed_pass"] and numeric["physical"]["failure_count"] == 0
                        and all(cycle["passed"] for cycle in numeric["tracking"]), f"Invalid numerical receipt: {label}")
        path = admit(numeric_path.parent/"plant32_si_with_pll.npz", numeric["si_npz_sha256"])
        with np.load(path, allow_pickle=False) as source:
            trace = {name: source[name] for name in (*physics.names(), "saturated", "sample_update", *PLL_FIELDS)}
        dq_case.check_clock(trace, grid)
        native[label] = trace
    return native, evidence


def wrap_error(angle):
    return (angle + pi) % tau - pi


def replay_pll(plant, observed, protocol, grid):
    """Advance from the accepted initial state using only original solved voltages."""
    cfg = protocol["pll"]
    caps = cfg["state_replay_limits_abs"]
    dt = cfg["sample_period_s"]
    sample_rows = np.arange(round(dt/grid["step_s"]), grid["rows"], round(dt/grid["step_s"]))
    nominal = tau*cfg["nominal_Hz"]
    theta, omega, xi = 19*pi/12, nominal, 0.
    samples = [(theta, omega, xi, 0.)]
    source = np.stack([plant[key] for key in dq_case.VOLTAGES], axis=1)
    phase_angles = np.array([0., -tau/3, tau/3])
    for row in sample_rows:
        metrics.require(abs(omega*dt) < pi, f"Ambiguous PLL advance at row {row}")
        theta = (theta + omega*dt) % tau
        angles = theta + phase_angles
        ed = 2/3 * np.dot(source[row], np.cos(angles))
        eq = -2/3 * np.dot(source[row], np.sin(angles))
        error = eq/max(abs(ed), abs(eq), cfg["normalization_floor_V"])
        xi += cfg["ki"]*dt*error
        omega = nominal + (cfg["kp"]*error + xi)
        samples.append((theta, omega, xi, error))
    expected = np.array(samples)
    suppliers = np.searchsorted(sample_rows, np.arange(grid["rows"]), side="right")
    is_sample = np.zeros(grid["rows"], dtype=bool)
    is_sample[sample_rows] = True
    keep = np.r_[0, sample_rows]
    metrics.require(np.array_equal(observed["sample_update"], is_sample), "PLL update rows differ")
    metrics.require(np.all((observed["theta"] >= 0) & (observed["theta"] < tau)), "PLL angle outside [0, 2π)")
    errors = {}
    for offset, (name, (column, budget)) in enumerate(PLL_FIELDS.items()):
        actual = observed[column]
        if name == "normalized_error":
            metrics.require(np.all(actual[~is_sample] == 0), "PLL normalized error must be zero off-sample")
        else:
            metrics.require(np.array_equal(actual, actual[keep[suppliers]]), f"PLL {name} did not hold")
        difference = actual[keep] - expected[:, offset]
        if name == "theta":
            difference = wrap_error(difference)
        maximum = float(np.max(np.abs(difference)))
        metrics.require(maximum <= caps[budget], f"PLL {name} replay error {maximum:g} exceeds {caps[budget]:g}")
        errors[name] = maximum
    return errors


def lock_metrics(trace, protocol, plant_protocol, grid):
    pll = protocol["pll"]
    full = protocol["acquisition"]["full"]
    start, end = (round(time/grid["step_s"]) for time in full["tracking_window_s"])
    rows = np.arange(start, end + 1, round(pll["sample_period_s"]/grid["step_s"]))
    metrics.require(np.all(trace["sample_update"][rows] == 1), "Missing lock-window sample")
    nominal = tau * pll["nominal_Hz"]
    theta = trace["theta"][rows]
    target = nominal*trace[TIME][rows] - pi/2
    source = np.stack([trace[key][rows] for key in dq_case.VOLTAGES])
    a, b, c = source
    phase = np.arctan2((b-c)/sqrt(3), (2*a-b-c)/3)
    ed, _ = dq_case.rotating_frame({key: trace[key][rows] for key in dq_case.VOLTAGES}, dq_case.VOLTAGES,
                                   pll["nominal_Hz"], angle=theta)
    physical_budget = plant_protocol["physical_residual_budgets"]["source_configured_grid_with_tokens_V"]
    phase_consistency_limit = asin(2*physical_budget/(120*sqrt(2)))
    result = {
        "sample_rows": len(rows),
        "angle_wraps": int(np.count_nonzero(np.diff(trace["theta"]) < -pi)),
        "minimum_grid_d_V": float(np.min(ed)),
        "maximum_phase_error_rad": float(np.max(np.abs(wrap_error(theta-target)))),
        "maximum_frequency_error_Hz": float(np.max(np.abs(trace["omega"][rows]/tau - pll["nominal_Hz"]))),
        "maximum_measured_phase_disagreement_rad": float(np.max(np.abs(wrap_error(phase-target)))),
        "measured_phase_consistency_limit_rad": phase_consistency_limit,
    }
    result["passed"] = (result["angle_wraps"] > 0 and result["minimum_grid_d_V"] > 0
                        and result["maximum_phase_error_rad"] <= pi/180 and result["maximum_frequency_error_Hz"] <= .05
                        and result["maximum_measured_phase_disagreement_rad"] <= phase_consistency_limit)
    return result


def compare_states(candidate, native, protocol, intervals, step):
    caps = protocol["pll"]["state_replay_limits_abs"]
    metrics.require(np.array_equal(candidate["sample_update"], native["sample_update"]), "Different PLL sample clocks")
    reports = []
    for start, stop in intervals:
        lo, hi = round(start/step), round(stop/step)
        rows = slice(lo, hi+1)
        active = candidate["sample_update"][rows].astype(bool)
        if lo == 0:
            active[0] = True
        checks = {}
        for name, (_, budget) in PLL_FIELDS.items():
            error = candidate[name][rows][active] - native[name][rows][active]
            if name == "theta":
                error = wrap_error(error)
            maximum = float(np.max(np.abs(error)))
            checks[name] = {"max_abs": maximum, "limit": caps[budget], "passed": maximum <= caps[budget]}
        reports.append({"interval_s": [start, stop], "samples": int(np.count_nonzero(active)), "metrics": checks,
                        "passed": all(item["passed"] for item in checks.values())})
    return reports


def run_candidate(factory, destination, protocol, current, plant_protocol, grid):
    start = monotonic()
    case = factory(time_step=grid["step_s"], stop_time=protocol["acquisition"]["full"]["stop_s"])
    case = replace(case, output=OutputOptions(show_figure=False), summary=None, plots=())
    result = run_case(case)
    plant = binding.plant_data(result, case.components)
    columns = (
        "j", "sample_update", "gate_tick", "ed", "eq", "id", "iq", "id_ref", "iq_ref",
        "carrier_applied", "saturated", "z_d", "z_q",
        *(column for column, _ in PLL_FIELDS.values()),
        *(f"{state}_{phase}" for state in ("applied", "pending") for phase in "abc"),
    )
    observer = {name: result.series(name) for name in columns}
    del result
    dq_case.check_clock({**plant, **observer}, grid)
    path = destination / "waveforms.npz"
    np.savez(path, **plant, **observer)
    replay = replay_pll(plant, observer, protocol, grid)
    upper, feedback = dq_case.check_feedback(plant, observer, current, "main", grid, angle=observer["theta"])
    updates = protocol["acquisition"]["full"]["control_samples_and_next_gate_applications_each"]
    metrics.require(feedback["updates"] == feedback["next_gate_applications"] == updates, "Incomplete PLL acquisition")
    plant_path = destination / "plant32.csv"
    write_plant(plant_path, plant)
    rows = PlantRows(plant_path, grid["rows"], physics.names())
    with localcontext() as context:
        context.prec = 70
        physical = physics.evaluate(
            Projection(rows, 0), Projection(rows, 1), h=Decimal(str(grid["step_s"])), expected_rows=grid["rows"],
            limits=plant_protocol["physical_residual_budgets"],
            precision_caps=plant_protocol["printed_precision_caps_SI"], upper_states=upper,
        )
    trace = {**plant, "saturated": observer["saturated"], "sample_update": observer["sample_update"],
             **{name: observer[column] for name, (column, _) in PLL_FIELDS.items()}}
    lock = lock_metrics(trace, protocol, plant_protocol, grid)
    tracking = dq_case.tracking(trace, current, current["scenarios"]["main"])
    report = {"grid": grid, "pll_replay_maximum_absolute_errors": replay, "feedback": feedback, "physical": physical,
              "lock": lock, "tracking": tracking, "elapsed_s": monotonic()-start,
              "artifacts": {file.name: sha256(file) for file in (path, plant_path)},
              "passed": physical["observed_pass"] and lock["passed"] and all(cycle["passed"] for cycle in tracking)}
    save_json(destination / "report.json", report)
    return trace, report


def plot_comparison(path, candidate, native, frequency):
    matplotlib.use("Agg")
    from matplotlib import pyplot as plt

    figure, axes = plt.subplots(2, 2, sharex=True, layout="constrained", figsize=(11, 7))
    for column, grid in enumerate(candidate):
        phase, currents = axes[:, column]
        for traces, engine, style in ((candidate, "PyCy", "-"), (native, "PSCAD", "--")):
            trace = traces[grid]
            time = trace[TIME]
            samples = trace["sample_update"].astype(bool)
            error = wrap_error(trace["theta"][samples] - (tau*frequency*time[samples] - pi/2))
            phase.plot(1000*time[samples], np.degrees(error), style, label=engine, linewidth=1.15)
            for axis, signal, color in zip("dq", dq_case.native_dq(trace, frequency), ("#176581", "#aa4b2b"), strict=True):
                currents.plot(1000*time, signal, color=color, linestyle=style, linewidth=.8, label=f"{engine} i{axis}")
        phase.set_title(f"{grid} electrical step")
        for axis in (phase, currents):
            axis.axvspan(110, 160, color="#bbbbbb", alpha=.15)
            axis.grid(alpha=.25)
    axes[0, 0].set_ylabel("PLL phase error (deg)")
    axes[1, 0].set_ylabel("Grid-frame current (A)")
    axes[0, 0].legend()
    axes[1, 0].legend(ncols=2, loc="lower right")
    figure.supxlabel("Time (ms)")
    figure.savefig(path, dpi=145)
    plt.close(figure)


def run_comparison(destination):
    protocol_path = DIRECTORY / "reference_protocol.json"
    qualification_path = DIRECTORY / "full_reference_report.json"
    protocol = dq_case.frozen_json(protocol_path, PROTOCOL_SHA)
    qualification = dq_case.frozen_json(qualification_path, QUALIFICATION_SHA)
    current_input = protocol["basis"]["plant_and_current_loop"]
    current_path = ROOT / current_input["path"]
    current = dq_case.frozen_json(current_path, current_input["sha256"])
    plant_input = current["basis"]["plant_validation"]
    plant_path = ROOT / plant_input["path"]
    plant = dq_case.frozen_json(plant_path, plant_input["sha256"])
    native, native_inputs = load_reference(protocol, current, qualification, plant_input["sha256"])
    case = current["scenarios"]["main"]
    limits = plant[current["same_step"]["numeric_budget_key_in_case_28"]]
    destination.mkdir(parents=True, exist_ok=False)
    sources = [
        EXAMPLE, Path(__file__).resolve(), Path(dq_case.__file__), protocol_path, qualification_path, current_path, plant_path,
        *(ROOT/name for name in ("pyproject.toml", "uv.lock")),
        *(ROOT/"pycy_emt_lite").rglob("*.py"),
        *(ROOT/"validation/common").rglob("*.py"),
        *(ROOT/"validation/cases/grid_connected_vsc_open_loop").rglob("*.py"),
    ]
    bindings = dq_case.snapshot_inputs(destination, sources)
    manifest = destination/"inputs.json"
    save_json(manifest, {
        "git_head_before_run": subprocess.check_output(
            ["git", "-c", f"safe.directory={ROOT.as_posix()}", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "platform": platform.platform(),
        "python_version": platform.python_version(),
        "numpy_version": np.__version__,
        "matplotlib_version": matplotlib.__version__,
        "source_sha256": bindings,
        "native_sha256": {path.relative_to(ROOT).as_posix(): digest for path, digest in native_inputs.items()},
    })
    factory = runpy.run_path(str(EXAMPLE))["define_case"]
    candidate, reports, numerical, state, native_checks = {}, {}, {}, {}, {}
    intervals = [*dq_case.windows(case), (0., protocol["acquisition"]["full"]["stop_s"])]
    for grid in current["electrical_grids"]:
        label, step = grid["id"], grid["step_s"]
        print(f"Running {label}", flush=True)
        folder = destination/label
        folder.mkdir()
        trace, result = run_candidate(factory, folder, protocol, current, plant, grid)
        candidate[label] = trace
        reports[label] = {"passed": result["passed"], "report_sha256": sha256(folder/"report.json")}
        native_checks[label] = {"lock": lock_metrics(native[label], protocol, plant, grid),
                                "tracking": dq_case.tracking(native[label], current, case)}
        numerical[label] = dq_case.same_step(trace, native[label], step, intervals, limits)
        state[label] = compare_states(trace, native[label], protocol, intervals, step)
    cross = {engine: dq_case.cross_step(traces["5us"], traces["2p5us"], current, case)
             for engine, traces in (("PyCy", candidate), ("PSCAD", native))}
    passed = (
        all(item["passed"] for item in reports.values())
        and all(check["lock"]["passed"] and all(item["passed"] for item in check["tracking"])
                for check in native_checks.values())
        and all(item["passed"] for table in (numerical, state) for group in table.values() for item in group)
        and all(item["passed"] for item in cross.values())
    )
    figure = destination/"pll_and_current_comparison.png"
    plot_comparison(figure, candidate, native, protocol["pll"]["nominal_Hz"])
    metrics.require(all(sha256(ROOT/name) == digest for name, digest in bindings.items())
                    and all(sha256(path) == digest for path, digest in native_inputs.items()),
                    "Candidate or reference inputs changed during comparison")
    report = destination/"report.json"
    save_json(report, {"passed": passed, "native_engine": qualification["engine"], "inputs_sha256": sha256(manifest),
                       "candidate_runs": reports, "native_checks": native_checks, "same_step": numerical,
                       "pll_state_same_step": state, "cross_step": cross, "figure_sha256": sha256(figure)})
    return report, passed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="New output directory below local_reference")
    args = parser.parse_args()
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    destination = (args.output or dq_case.RESEARCH/f"c1_example30_comparison_{stamp}").resolve()
    metrics.require(destination.is_relative_to(CACHE.resolve()) and destination != CACHE.resolve(),
                    "Output must be below local_reference")
    report, passed = run_comparison(destination)
    print(report, "PASS" if passed else "FAIL")
    return int(not passed)


if __name__ == "__main__":
    raise SystemExit(main())
