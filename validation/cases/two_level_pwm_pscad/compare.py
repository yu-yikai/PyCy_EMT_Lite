"""Compare unchanged example12 with the qualified local PSCAD reference.

Run: uv run python -m validation.cases.two_level_pwm_pscad.compare
No vendor process is launched. Missing or changed evidence stops before a candidate.
"""
from __future__ import annotations

import hashlib
import json
import platform
import re
import runpy
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

from pycy_emt_lite import Circuit, Simulator
from pycy_emt_lite.io.results import SimulationResult
from validation.cases.two_level_pwm.compare import compare_features
from validation.common.comparison import SignalSpec, compare_signals

SCHEMA = "two_level_pwm_pscad_full_reference_v1"
STATUS = "QUALIFIED_FULL_CONDITIONAL_NATIVE_REFERENCE"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def checked_file(root: Path, item: dict) -> Path:
    """Verify one explicit repository-relative path, size and SHA descriptor."""
    name = item["path"]
    if (not isinstance(name, str) or not name or Path(name).is_absolute()
            or type(item["bytes"]) is not int or item["bytes"] < 0
            or not isinstance(item["sha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", item["sha256"])):
        raise ValueError("Invalid reference file descriptor")
    path = (root / name).resolve()
    if (not path.is_relative_to(root.resolve()) or not path.is_file()
            or path.stat().st_size != item["bytes"] or sha256(path) != item["sha256"]):
        raise ValueError("Qualified reference input changed or escapes repository: " + name)
    return path


def load_reference(root: Path, directory: Path) -> tuple[SimulationResult, dict, dict[str, str]]:
    """Require the accepted complete receipt and every native/snapshot leaf file."""
    manifest = read(directory / "manifest.json")
    protocol = read(directory / "reference_protocol.json")
    public = read(directory / "qualified_reference_report.json")
    receipt = checked_file(root, public["complete_receipt"])
    provenance_path = checked_file(root, public["provenance"])
    if not all(path.is_relative_to((root / "local_reference").resolve()) for path in (receipt, provenance_path)):
        raise ValueError("Qualification/provenance must be in the local reference archive")
    qualification, provenance = read(receipt), read(provenance_path)
    for field in ("case_id", "reference_id"):
        if any(item[field] != manifest[field] for item in (public, qualification, provenance)):
            raise ValueError("Reference identity mismatch: " + field)
    scope = {"reference_only": True, "formal_stop_s": .2, "acquisition_stop_s": .200005,
             "control_hold_s": 5e-6, "electrical_h_s": [5e-6, 2.5e-6], "rows": [40002, 80003],
             "channels": 60, "shared_input_scope": "exact_same_shared_inputs"}
    if (public["status"] != STATUS or public["reference_qualified"] is not True
            or qualification["schema"] != SCHEMA or qualification["status"] != STATUS
            or qualification["reference_self_refinement_passed"] is not True
            or qualification["independent_review_passed"] is not True
            or qualification["scope"].get("reference_only") is not True
            or qualification["protocol_sha256"] != sha256(directory / "reference_protocol.json")
            or any(qualification["scope"].get(key) != value for key, value in scope.items())):
        raise ValueError("Full native reference qualification/scope/protocol differs")
    bindings = {}
    for item in qualification["complete_input_bindings"]:
        path = checked_file(root, item)
        relative = path.relative_to(root.resolve()).as_posix()
        if relative in bindings:
            raise ValueError("Duplicate resolved qualification input: " + relative)
        bindings[relative] = item["sha256"]
    normalized = qualification["normalized_reference"]
    for item in [*qualification["accepted_reports"].values(), normalized]:
        path = checked_file(root, item)
        if bindings.get(path.relative_to(root.resolve()).as_posix()) != item["sha256"]:
            raise ValueError("Accepted report/normalized export is not in the complete input inventory")
    if set(qualification["accepted_reports"]) != {"author", "independent"}:
        raise ValueError("Both accepted author and independent reports are required")
    for name in ("manifest.json", "parameters.json", "acceptance_plan.md", "reference_protocol.json"):
        if (receipt.parent / "input_snapshot/protocol" / name).read_bytes() != (directory / name).read_bytes():
            raise ValueError("Frozen protocol changed: " + name)
    if (public["normalized_reference"] != normalized
            or provenance["complete_receipt"] != public["complete_receipt"]
            or provenance["normalized_reference"] != normalized
            or provenance["solver"] != "EMTDC_TR" or provenance["platform"] != manifest["reference_platform"]):
        raise ValueError("Public/complete/provenance reference descriptors or solver differ")
    if (normalized["rows"] != 80003 or normalized["rows"] != protocol["fine_rows"]
            or normalized["columns"] != ["time", "i_a", "i_b", "i_c"] or normalized["time_from"] != "TIME_native_s"):
        raise ValueError("Normalized export rows/columns/native time mapping differs")
    reference = SimulationResult.from_csv(checked_file(root, normalized), method=provenance["solver"])
    times = reference.series("time")
    if (len(reference.rows) != 80003 or reference.columns != normalized["columns"]
            or times[0] != 0 or times[-1] <= .2 or np.any(np.diff(times) <= 0)
            or any(not np.all(np.isfinite(reference.series(name))) for name in normalized["columns"])):
        raise ValueError("Reference has incomplete native TIME/tail or nonfinite current data")
    for path in (receipt, provenance_path, directory / "qualified_reference_report.json"):
        bindings[path.relative_to(root.resolve()).as_posix()] = sha256(path)
    return reference, provenance, bindings


def main() -> None:
    directory = Path(__file__).resolve().parent
    root = directory.parents[2]
    manifest, parameters = read(directory / "manifest.json"), read(directory / "parameters.json")
    protocol = read(directory / "reference_protocol.json")
    if manifest["time_shift_seconds"] != 0 or manifest["event_guard_seconds"] != 0:
        raise ValueError("This case uses complete fixed windows without shifts or exclusions")
    reference, provenance, bindings = load_reference(root, directory)
    example = root / manifest["example"]
    if sha256(example) != protocol["candidate_criteria_unchanged"]["example_sha256"]:
        raise ValueError("Existing default12 source changed")
    sources = [example, *sorted(directory.glob("*.py")), *sorted((root / "pycy_emt_lite").rglob("*.py")),
               root / "validation/common/comparison.py", root / "validation/cases/two_level_pwm/compare.py",
               *[directory / name for name in ("manifest.json", "parameters.json", "acceptance_plan.md",
                                              "reference_protocol.json", "qualified_reference_report.json")]]
    code = {path.relative_to(root).as_posix(): sha256(path) for path in sources}
    run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    out = root / "local_reference/two_level_pwm_pscad/comparison_results" / run_id
    out.mkdir(parents=True, exist_ok=False)
    git = ["git", "-c", f"safe.directory={root.as_posix()}"]
    report = {"case_id": manifest["case_id"], "reference_id": manifest["reference_id"], "run_id": run_id,
              "passed": False, "candidate_executed": False, "reference_provenance": provenance,
              "native_input_sha256": bindings, "code_and_protocol_sha256": code,
              "python_version": platform.python_version(), "numpy_version": np.__version__}
    try:
        report["git_head_at_run"] = subprocess.check_output([*git, "rev-parse", "HEAD"], cwd=root, text=True).strip()
        report["git_status_at_run"] = subprocess.check_output([*git, "status", "--porcelain"], cwd=root, text=True).splitlines()
        for relative, expected in {**bindings, **code}.items():
            target = out / "inputs" / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(root / relative, target)
            if sha256(target) != expected:
                raise RuntimeError("Snapshot changed: " + relative)
        case = runpy.run_path(str(example))["define_case"]()
        simulator = Simulator(Circuit.from_components(case.name, case.components), case.config,
                              events=case.events, on_step=case.on_step)
        report["candidate_executed"] = True
        candidate = simulator.run()
        candidate.to_csv(out / "pycy.csv")
        candidate.to_json(out / "pycy.json")
        candidate.to_npz(out / "pycy.npz")
        specs = [SignalSpec(**signal) for signal in manifest["signals"]]
        windows = [compare_signals(candidate, reference, specs, start=start, end=end)
                   for start, end in manifest["windows_seconds"]]
        features = compare_features(candidate, reference, manifest, parameters["load_resistance_ohm"])
        import matplotlib.pyplot as plt
        figure, axes = plt.subplots(3, 1, figsize=(10, 8), sharex=True)
        for axis, spec in zip(axes, specs, strict=True):
            axis.plot(reference.series("time"), reference.series(spec.reference), label="PSCAD")
            axis.plot(candidate.series("time"), candidate.series(spec.candidate), "--", label="Existing12")
            axis.set_ylabel(spec.candidate + " [A]")
            axis.grid(alpha=.3)
            axis.legend()
        axes[-1].set_xlabel("Absolute time [s], no shift")
        figure.tight_layout()
        figure.savefig(out / "comparison.png", dpi=150)
        plt.close(figure)
        report.update(passed=all(window["passed"] for window in windows) and features["passed"],
                      windows=windows, features=features, reference_samples=len(reference.rows),
                      candidate_samples=len(candidate.rows), candidate_method=candidate.method,
                      candidate_step_s=candidate.time_step,
                      candidate_data_sha256={name: sha256(out / name) for name in ("pycy.csv", "pycy.json", "pycy.npz")},
                      plot_sha256=sha256(out / "comparison.png"))
    except Exception as exc:
        report.update(passed=False, evaluation_error=f"{type(exc).__name__}: {exc}")
        raise
    finally:
        errors = []
        for relative, expected in {**bindings, **code}.items():
            try:
                if sha256(root / relative) != expected or sha256(out / "inputs" / relative) != expected:
                    errors.append("changed: " + relative)
            except OSError as exc:
                errors.append(f"missing/unreadable {relative}: {exc}")
        if errors:
            report.update(passed=False, input_integrity_errors=errors)
        (out / "report.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print("two_level_pwm_pscad", report["passed"], out / "report.json")
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
