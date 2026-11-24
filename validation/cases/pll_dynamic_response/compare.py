"""Compare unchanged example11 with the qualified local Simulink PLL reference.

Run with MPLBACKEND=Agg: uv run python -m validation.cases.pll_dynamic_response.compare
No vendor process is launched. Missing or changed evidence stops before main().
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import platform
import re
import runpy
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

from pycy_emt_lite.io.results import SimulationResult
from validation.common.comparison import SignalSpec, compare_signals

PUBLIC_REPORT_SHA256 = "ebe76a3c41bd0f5bce7680261ae56d858014f34daabffa01df240c74f5661a48"
QUALIFICATION_SHA256 = "77adfc0cfe84670cce8c2b1435ca9fed852251fa32d2808ce82e19770a7fa11e"
PROTOCOL_SHA256 = "dc6a48e221062d72816f882ae0ec70933ea887c91bf96396df8b0b436691036a"
MANIFEST_SHA256 = "9a55c97285c552b7519012ce0a2bac5f13f3a877a320b8fae6056c58d9df3e9d"
STATUS = "QUALIFIED_NATIVE_REFERENCE_ONLY"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def checked_file(root: Path, item: dict) -> Path:
    """Check a repository-relative file descriptor without accepting path aliases."""
    name = item["path"]
    if (not isinstance(name, str) or not name or "\\" in name or ":" in name
            or Path(name).is_absolute() or type(item["bytes"]) is not int or item["bytes"] < 0
            or not isinstance(item["sha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", item["sha256"])):
        raise ValueError("Invalid qualified file descriptor")
    path = (root / name).resolve()
    if (not path.is_relative_to(root.resolve()) or not path.is_file()
            or path.stat().st_size != item["bytes"] or sha256(path) != item["sha256"]):
        raise ValueError("Qualified input changed or escapes repository: " + name)
    return path


def load_reference(root: Path, directory: Path) -> tuple[SimulationResult, dict, dict[str, str]]:
    """Verify the accepted complete archive and the primary native observation."""
    for name, digest in (("qualified_reference_report.json", PUBLIC_REPORT_SHA256),
                         ("reference_protocol.json", PROTOCOL_SHA256), ("manifest.json", MANIFEST_SHA256)):
        if sha256(directory / name) != digest:
            raise ValueError("Accepted public reference identity changed: " + name)
    public = read(directory / "qualified_reference_report.json")
    protocol, manifest = read(directory / "reference_protocol.json"), read(directory / "manifest.json")
    receipt = checked_file(root, public["complete_receipt"])
    provenance_path = checked_file(root, public["provenance"])
    if (public["complete_receipt"]["sha256"] != QUALIFICATION_SHA256
            or not all(path.is_relative_to((root / "local_reference").resolve())
                       for path in (receipt, provenance_path))):
        raise ValueError("Complete qualification identity/location differs")
    q, provenance = read(receipt), read(provenance_path)
    for key in ("case_id", "reference_id"):
        if any(item[key] != manifest[key] for item in (public, q, provenance)):
            raise ValueError("Reference identity mismatch: " + key)
    scope = {"stop_s": 1.0, "control_step_s": 1e-4, "signal_rows": 10001, "signal_columns": 23,
             "solver_steps_s": [1e-4, 5e-5], "solver_rows": [10001, 20001], "signal_midpoints_observed": False}
    if (type(q["schema_version"]) is not int or q["schema_version"] != 1
            or any(item["status"] != STATUS for item in (public, q))
            or public["reference_qualified"] is not True or q["reference_only"] is not True
            or any(q[key] is not True for key in ("native_semantics_passed", "secondary_schedule_invariance_passed",
                                                "independent_review_passed"))
            or any(item["candidate_executed"] is not False for item in (public, q, provenance))
            or public["existing_11_formally_accepted"] is not False
            or q["scope"] != scope or public["scope"] != scope
            or any(item["scope"]["signal_midpoints_observed"] is not False for item in (public, q))
            or any(isinstance(item["scope"]["stop_s"], bool) for item in (public, q))):
        raise ValueError("Qualification status, reference-only flags or scope differs")
    bindings, folded = {}, {}
    for item in q["complete_input_bindings"]:
        path = checked_file(root, item)
        relative = path.relative_to(root.resolve()).as_posix()
        if relative.casefold() in folded:
            raise ValueError("Duplicate resolved qualification input: " + relative)
        bindings[relative], folded[relative.casefold()] = item["sha256"], item["sha256"]
    if type(public["complete_input_files"]) is not int or len(bindings) != public["complete_input_files"]:
        raise ValueError("Incomplete qualification inventory")

    def member(item):
        path = checked_file(root, item)
        if folded.get(path.relative_to(root.resolve()).as_posix().casefold()) != item["sha256"]:
            raise ValueError("Declared qualification evidence is outside its leaf inventory")
        return path

    contracts = {"master_protocol": "reference_protocol.json", "comparison_manifest": "manifest.json",
                 "acceptance_plan": "acceptance_plan.md"}
    if set(q["contracts"]) != set(contracts):
        raise ValueError("Three accepted contracts are required")
    for key, name in contracts.items():
        if member(q["contracts"][key]) != (directory / name).resolve():
            raise ValueError("Accepted public contract location differs")
    if (q["source_inputs"] != protocol["source_inputs"] or len(q["source_inputs"]) != 5
            or len({item["path"].casefold() for item in q["source_inputs"]}) != 5):
        raise ValueError("Original example/controller/common source inputs differ")
    for item in q["source_inputs"]:
        if folded.get(item["path"].casefold()) != item["sha256"]:
            raise ValueError("Current source is not bound by qualification")
    if (set(q["accepted_reports"]) != {"coarse", "fine", "scheduling_pair"}
            or len(q["independent_reviews"]) != 4 or set(q["native_runs"]) != {"coarse", "fine"}):
        raise ValueError("Native schedules, reports or independent reviews are incomplete")
    for item in [*q["accepted_reports"].values(), *q["independent_reviews"],
                 q["normalized_reference"], q["normalization_receipt"]]:
        member(item)
    for item in q["accepted_reports"].values():
        report = read(member(item))
        if report["passed"] is not True or report["status"] != "PLL_FULL_SEMANTIC_PASS":
            raise ValueError("Accepted native analysis did not pass")
    expected_reviews = {"CLOSED_COARSE_STRUCTURE_AND_LOGGING_AUDIT_PASS",
                        "CLOSED_FINE_STRUCTURE_AND_NATIVE_SCHEDULE_PAIR_AUDIT_PASS",
                        "INDEPENDENT_FULL_COARSE_NUMERICAL_PASS", "INDEPENDENT_FULL_FINE_AND_SAME_SEQUENCE_PAIR_PASS"}
    if {read(member(item))["status"] for item in q["independent_reviews"]} != expected_reviews:
        raise ValueError("The four independent native reviews differ")
    for native in q["native_runs"].values():
        if set(native) != {"run_directory", "terminal", "worker", "raw_reference", "solver_time",
                           "raw_mat", "saved_model", "source_manifest"}:
            raise ValueError("Native run evidence is incomplete")
        run = (root / native["run_directory"]).resolve()
        for key, item in native.items():
            if key != "run_directory" and not member(item).is_relative_to(run):
                raise ValueError("Native evidence escapes its accepted run")
        terminal, worker = read(member(native["terminal"])), read(member(native["worker"]))
        if (type(terminal["exit_code"]) is not int or terminal["exit_code"] != 0
                or terminal["termination_reason"] != "process_completed"
                or terminal["owned_all_exited"] is not True or terminal["inputs_unchanged"] is not True
                or terminal["monitor_error"] is not None or terminal["cleanup_error"] is not None
                or any(worker[key] is not True for key in ("prepared", "simulation_requested",
                                                           "simulation_finished", "completed"))):
            raise ValueError("Native run lacks successful semantic/process closure")
    normalized = public["normalized_reference"]
    core = {key: normalized[key] for key in ("path", "bytes", "sha256")}
    metadata = {"rows": 10001, "columns": ["time", "theta_rad", "theta_unwrapped", "omega_rad_s", "q_v"],
                "units": {"time": "s", "theta_rad": "rad", "theta_unwrapped": "rad", "omega_rad_s": "rad/s", "q_v": "V"},
                "source_run": "coarse", "time_from": "time_s"}
    if (core != q["normalized_reference"] or any(normalized[key] != value for key, value in metadata.items())
            or provenance["normalized_reference"] != normalized
            or provenance["complete_receipt"] != public["complete_receipt"]
            or provenance["native_runs"] != q["native_runs"]
            or provenance["normalization_receipt"] != q["normalization_receipt"]
            or provenance["qualification_reviews"] != public["qualification_reviews"]
            or len(public["qualification_reviews"]) != 2):
        raise ValueError("Public/qualification/provenance observation descriptors differ")
    normalization = read(member(q["normalization_receipt"]))
    if (normalization["candidate_executed"] is not False or normalization["rows"] != 10001
            or normalization["status"] != "EXACT_NATIVE_VALUES_WITH_DECLARED_ANCHORED_ANGLE_VIEW"
            or normalization["source"] != q["native_runs"]["coarse"]["raw_reference"]
            or normalization["protocol"] != q["contracts"]["master_protocol"]
            or normalization["normalized"] != q["normalized_reference"]):
        raise ValueError("Normalization receipt changes the accepted source observation")
    member(normalization["producer"])
    extras = [(receipt, QUALIFICATION_SHA256), (provenance_path, public["provenance"]["sha256"]),
              (directory / "qualified_reference_report.json", PUBLIC_REPORT_SHA256)]
    for item in public["qualification_reviews"]:
        path = checked_file(root, item)
        review = read(path)
        target = review["qualification"]
        target_path = Path(target["path"])
        if not target_path.is_absolute():
            target_path = root / target_path
        if (target_path.resolve() != receipt or target["sha256"] != QUALIFICATION_SHA256
                or target["bytes"] != public["complete_receipt"]["bytes"]):
            raise ValueError("Post-qualification review targets another complete receipt")
        if review["status"] == "PLL_FULL_NATIVE_Q_BINDING_AND_SCOPE_REVIEW_PASS":
            if (review["passed"] is not True or review["scope"] != scope
                    or any(review[key] != q[key] for key in ("contracts", "accepted_reports", "independent_reviews"))):
                raise ValueError("Post-qualification binding/scope review differs")
        elif review["status"] == "INDEPENDENT_ACTUAL_PLL_REFERENCE_QUALIFICATION_PASS":
            if (review["reference_only"] is not True or review["candidate_executed"] is not False
                    or review["signal_midpoints_observed"] is not False):
                raise ValueError("Post-qualification observation review scope differs")
        else:
            raise ValueError("Unknown post-qualification acceptance review")
        extras.append((path, item["sha256"]))
    for path, digest in extras:
        relative = path.resolve().relative_to(root.resolve()).as_posix()
        if relative.casefold() in folded:
            raise ValueError("Qualification inventory contains a post-qualification hash cycle")
        bindings[relative] = digest
        folded[relative.casefold()] = digest
    reference = SimulationResult.from_csv(member(q["normalized_reference"]), method=provenance["solver"])
    if reference.columns != metadata["columns"] or len(reference.rows) != 10001:
        raise ValueError("Normalized native layout changed")
    raw_path = member(q["native_runs"]["coarse"]["raw_reference"])
    with raw_path.open(encoding="utf-8", newline="") as handle:
        if next(csv.reader(handle)) != protocol["csv_columns"]:
            raise ValueError("Primary native CSV header changed")
    raw = np.loadtxt(raw_path, delimiter=",", skiprows=1, ndmin=2)
    if raw.shape != (10001, 23) or not np.all(np.isfinite(raw)):
        raise ValueError("Primary native records are incomplete/nonfinite")
    mapping = {"time": "time_s", "angle": "theta_rad", "frequency": "omega_rad_s", "q_axis_voltage": "q_v"}
    rows = [{key: float(values[protocol["csv_columns"].index(column)]) for key, column in mapping.items()}
            for values in raw]
    observed = comparison_view(SimulationResult("native", "recorded", 1e-4, 1.0, rows), protocol)
    for column, source in (("time", "time"), ("theta_rad", "angle"), ("theta_unwrapped", "angle_unwrapped"),
                           ("omega_rad_s", "frequency"), ("q_v", "q_axis_voltage")):
        if not np.array_equal(reference.series(column), observed.series(source)):
            raise ValueError("Normalized export changes the actual native observation: " + column)
    return reference, provenance, bindings


def capture_original11(example: Path, *, before_main=None) -> SimulationResult:
    """Observe all original plots without changing the original main's computation."""
    if os.environ.get("MPLBACKEND", "").lower() != "agg":
        raise ValueError("Use MPLBACKEND=Agg for the offline comparison")
    main = runpy.run_path(str(example))["main"]
    globals_used, observed = main.__globals__, []
    original_plot = globals_used["plot_series"]

    def observe(result, *args, **kwargs):
        observed.append(result)
        return original_plot(result, *args, **kwargs)

    try:
        globals_used["plot_series"] = observe
        if before_main is not None:
            before_main()
        main()
    finally:
        globals_used["plot_series"] = original_plot
    if (len(observed) != 3 or any(item is not observed[0] for item in observed)
            or not isinstance(observed[0], SimulationResult)):
        raise ValueError("Expected three original plots of the same SimulationResult")
    return observed[0]


def comparison_view(raw: SimulationResult, protocol: dict) -> SimulationResult:
    """Check only recorded identities and add raw theta plus integer turn counts."""
    names = ["time", "angle", "frequency", "q_axis_voltage"]
    if raw.columns != names or len(raw.rows) != 10001:
        raise ValueError("Unexpected original observation layout")
    columns = [raw.series(name) for name in names]
    if any(values.shape != (10001,) or not np.all(np.isfinite(values)) for values in columns):
        raise ValueError("All original observation columns must be finite")
    time, theta, omega, q_axis = columns
    dt, h = np.diff(time), protocol["control_step_s"]
    parameters, budgets = protocol["parameters"], protocol["absolute_budgets"]
    if (time[0] != 0 or time[-1] != 1 or np.any(dt <= 0)
            or np.max(np.abs(time - np.arange(10001) * h)) > budgets["time_s"]
            or raw.time_step != h or raw.stop_time != 1):
        raise ValueError("Raw time/update contract changed")
    if (theta[0] != parameters["theta0_rad"] or np.any(theta < 0) or np.any(theta >= 2 * np.pi)
            or np.any(np.abs(omega[:-1] * dt) >= np.pi)
            or abs(omega[0] - parameters["omega0_rad_s"]) > budgets["omega_rad_s"]):
        raise ValueError("Initial state or unique old-omega advance differs")
    difference = np.diff(theta)
    changes = np.where(difference < -np.pi, 1, np.where(difference > np.pi, -1, 0))
    principal = difference + (2 * np.pi) * changes
    if (np.any(np.abs(principal) >= np.pi)
            or np.any(np.abs(principal - omega[:-1] * dt) > budgets["angle_rad"])):
        raise ValueError("Angle did not advance with the observed old omega")
    expected_q = np.sqrt(2) * parameters["phase_rms_v"] * np.sin(parameters["omega0_rad_s"] * time - np.pi / 3 - theta)
    if np.any(np.abs(q_axis - expected_q) > budgets["voltage_v"]):
        raise ValueError("Observed q violates the independent balanced-vector identity")
    turns = np.r_[np.int64(0), np.cumsum(changes, dtype=np.int64)]
    rows = [dict(row, angle_unwrapped=float(angle))
            for row, angle in zip(raw.rows, theta + (2 * np.pi) * turns, strict=True)]
    return SimulationResult(raw.circuit_name, raw.method, raw.time_step, raw.stop_time, rows,
                            event_log=list(raw.event_log))


def evaluate(candidate: SimulationResult, reference: SimulationResult, manifest: dict) -> dict:
    if not manifest["windows_seconds"] or not manifest["signals"] or manifest["time_shift_seconds"] != 0:
        raise ValueError("Fixed nonempty windows/signals with zero time shift are required")
    specs = [SignalSpec(**item) for item in manifest["signals"]]
    windows = [compare_signals(candidate, reference, specs, start=start, end=end)
               for start, end in manifest["windows_seconds"]]
    return {"passed": all(window["passed"] for window in windows), "windows": windows}


def main() -> None:
    directory = Path(__file__).resolve().parent
    root = directory.parents[2]
    out = root / "local_reference/pll_dynamic_response/comparison_results" / datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    out.mkdir(parents=True, exist_ok=False)
    report = {"case_id": "pll_dynamic_response", "passed": False, "candidate_executed": False, "run_id": out.name,
              "python_version": platform.python_version(), "numpy_version": np.__version__}
    bindings, code = {}, {}
    try:
        git = ["git", "-c", f"safe.directory={root.as_posix()}"]
        report["git_head_at_run"] = subprocess.check_output([*git, "rev-parse", "HEAD"], cwd=root, text=True).strip()
        report["git_status_at_run"] = subprocess.check_output([*git, "status", "--porcelain"], cwd=root, text=True).splitlines()
        reference, provenance, bindings = load_reference(root, directory)
        manifest, protocol = read(directory / "manifest.json"), read(directory / "reference_protocol.json")
        report.update(case_id=manifest["case_id"], reference_id=manifest["reference_id"], reference_provenance=provenance,
                      native_input_sha256=bindings)
        sources = [root / manifest["example"], *sorted((root / "pycy_emt_lite").rglob("*.py")),
                   *sorted(directory.glob("*.py")), root / "validation/common/comparison.py",
                   *[directory / name for name in ("manifest.json", "reference_protocol.json", "acceptance_plan.md",
                                                  "qualified_reference_report.json")], root / "pyproject.toml", root / "uv.lock"]
        test = root / "tests/test_pll_reference_comparison.py"
        if test.is_file():
            sources.append(test)
        code = {path.relative_to(root).as_posix(): sha256(path) for path in sources}
        accepted = {relative.casefold(): digest for relative, digest in bindings.items()}
        for relative, digest in code.items():
            if relative.casefold() in accepted and accepted[relative.casefold()] != digest:
                raise RuntimeError("Qualified input changed before snapshot: " + relative)
        report["code_and_protocol_sha256"] = code
        for relative, digest in {**code, **bindings}.items():
            target = out / "input_snapshot" / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(root / relative, target)
            if sha256(target) != digest:
                raise RuntimeError("Input snapshot changed: " + relative)
        os.environ["MPLBACKEND"] = "Agg"
        raw = capture_original11(root / manifest["example"], before_main=lambda: report.update(candidate_executed=True))
        raw.to_csv(out / "pycy.csv")
        raw.to_json(out / "pycy.json")
        raw.to_npz(out / "pycy.npz")
        candidate = comparison_view(raw, protocol)
        candidate.to_csv(out / "comparison_view.csv")
        metrics = evaluate(candidate, reference, manifest)
        import matplotlib.pyplot as plt
        figure, axes = plt.subplots(3, 1, figsize=(10, 8), sharex=True)
        for axis, item in zip(axes, manifest["signals"], strict=True):
            axis.plot(reference.series("time"), reference.series(item["reference"]), label="Simulink")
            axis.plot(candidate.series("time"), candidate.series(item["candidate"]), "--", label="Existing11")
            axis.set_ylabel(item["candidate"] + " [" + item["unit"] + "]")
            axis.grid(alpha=.3)
            axis.legend()
        axes[-1].set_xlabel("Actual time [s]; common initial angle; no shift")
        figure.tight_layout()
        figure.savefig(out / "comparison.png", dpi=150)
        plt.close(figure)
        report.update(**metrics, candidate_samples=len(raw.rows), reference_samples=len(reference.rows),
                      candidate_method=raw.method, candidate_step_s=raw.time_step,
                      artifact_sha256={name: sha256(out / name) for name in
                                       ("pycy.csv", "pycy.json", "pycy.npz", "comparison_view.csv", "comparison.png")})
    except Exception as error:
        report.update(passed=False, evaluation_error=f"{type(error).__name__}: {error}")
        raise
    finally:
        errors = []
        for relative, digest in {**code, **bindings}.items():
            try:
                if sha256(root / relative) != digest or sha256(out / "input_snapshot" / relative) != digest:
                    errors.append("changed: " + relative)
            except OSError as error:
                errors.append(f"missing/unreadable {relative}: {error}")
        if errors:
            report.update(passed=False, input_integrity_errors=errors)
        (out / "report.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print("pll_dynamic_response", report["passed"], out / "report.json")
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
