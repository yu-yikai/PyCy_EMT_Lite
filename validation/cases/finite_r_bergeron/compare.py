"""Compare case 27 with the qualified, locally archived PSCAD outputs.

Run: uv run python -m validation.cases.finite_r_bergeron.compare
No vendor process is launched. Missing or changed reference inputs are errors.
"""

from __future__ import annotations

import json
import platform
import runpy
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from pycy_emt_lite import Circuit, Simulator
from pycy_emt_lite.io.results import SimulationResult
from validation.common.comparison import SignalSpec, aligned_signal, compare_signals
from validation.common.runner import sha256


def load_reference(root: Path, directory: Path) -> tuple[SimulationResult, dict, dict[str, str]]:
    """Check the native evidence and qualification snapshots before using CSV."""
    archive = root / "local_reference/finite_r_bergeron"
    provenance_file = archive / "provenance.json"
    provenance = json.loads(provenance_file.read_text(encoding="utf-8"))
    summary = json.loads((directory / "qualified_reference_report.json").read_text(encoding="utf-8"))
    if (provenance["case_id"] != "finite_r_bergeron"
            or provenance["reference_id"] != "pscad-installed-scalar-bergeron-v5"
            or provenance["reference_qualified"] is not True):
        raise ValueError("Reference identity/qualification differs from this case")
    bindings = dict(provenance["source_files_sha256"])
    bindings[provenance["qualification_report"]] = summary["complete_receipt"]["sha256"]
    qualification_path = root / provenance["qualification_report"]
    if not qualification_path.resolve().is_relative_to((root / "local_reference").resolve()):
        raise ValueError("Qualification receipt escapes the local reference archive")
    if sha256(qualification_path) != summary["complete_receipt"]["sha256"]:
        raise ValueError("Reference qualification receipt changed")
    qualification = json.loads(qualification_path.read_text(encoding="utf-8"))
    if (qualification["status"] != "REFERENCE_SELF_REFINEMENT_QUALIFIED"
            or qualification["all_16_signal_window_view_checks_passed"] is not True):
        raise ValueError("Native self-refinement did not qualify the reference")
    for relative, expected in qualification["audit"]["input_sha256"].items():
        path = qualification_path.parent / relative.replace("\\", "/")
        if not path.resolve().is_relative_to(qualification_path.parent.resolve()):
            raise ValueError("Qualification snapshot escapes its archive")
        bindings[path.relative_to(root).as_posix()] = expected
    for relative, expected in bindings.items():
        path = (root / relative).resolve()
        if not path.is_relative_to(root.resolve()) or sha256(path) != expected:
            raise ValueError(f"Native reference input changed: {relative}")
    for name in ("manifest.json", "parameters.json"):
        frozen = qualification_path.parent / "input_snapshot/protocol" / name
        if json.loads(frozen.read_text(encoding="utf-8")) != json.loads((directory / name).read_text(encoding="utf-8")):
            raise ValueError(f"Frozen protocol changed: {name}")
    frozen_plan = qualification_path.parent / "input_snapshot/protocol/acceptance_plan.md"
    if frozen_plan.read_text(encoding="utf-8") != (directory / "acceptance_plan.md").read_text(encoding="utf-8"):
        raise ValueError("Frozen protocol changed: acceptance_plan.md")
    reference_file = archive / "normalized_results/reference.csv"
    if sha256(reference_file) != summary["normalized_reference_sha256"]:
        raise ValueError("Normalized reference differs from the qualified native export")
    reference = SimulationResult.from_csv(reference_file, method=provenance["solver"])
    times = reference.series("time")
    if (len(reference.rows) != 12001 or times[0] != 0 or times[-1] != 0.006
            or not np.allclose(times, np.arange(12001) * 5e-7, rtol=0, atol=1e-15)):
        raise ValueError("Reference does not contain the complete native 0.5 us grid")
    bindings[provenance_file.relative_to(root).as_posix()] = sha256(provenance_file)
    return reference, provenance, bindings


def main() -> None:
    directory = Path(__file__).resolve().parent
    root = directory.parents[2]
    manifest_file = directory / "manifest.json"
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    if manifest["time_shift_seconds"] != 0 or manifest["event_guard_seconds"] != 0:
        raise ValueError("This case uses complete windows without shifts or exclusions")
    reference, provenance, bindings = load_reference(root, directory)
    example_file = root / manifest["example"]
    sources = [example_file, *sorted(directory.glob("*.py")),
               *[directory / name for name in ("manifest.json", "parameters.json", "acceptance_plan.md",
                                               "qualified_reference_report.json")],
               root / "validation/common/comparison.py", root / "validation/common/runner.py",
               *sorted((root / "pycy_emt_lite").rglob("*.py"))]
    source_hashes = {path.relative_to(root).as_posix(): sha256(path) for path in sources}
    case = runpy.run_path(str(example_file))["define_case"]()
    candidate = Simulator(Circuit.from_components(case.name, case.components), case.config,
                          events=case.events, on_step=case.on_step).run()
    specs = [SignalSpec(**signal) for signal in manifest["signals"]]
    windows = [compare_signals(candidate, reference, specs, start=start, end=end)
               for start, end in manifest["windows_seconds"]]
    source_spec = SignalSpec("v:src", "Vs_V", "V", 1000, 0.001,
                             manifest["reference_normalization"]["Vs_input_gate_max_abs_error_V"])
    _, actual_source, native_source = aligned_signal(candidate, reference, source_spec, 0, 0.006)
    source_error = float(np.max(np.abs(actual_source - native_source)))
    source_passed = source_error <= source_spec.max_abs_error
    run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    destination = root / "local_reference/finite_r_bergeron/comparison_results" / run_id
    destination.mkdir(parents=True, exist_ok=False)
    for relative in {**bindings, **source_hashes}:
        target = destination / "inputs" / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(root / relative, target)
    candidate.to_csv(destination / "pycy.csv")
    candidate.to_json(destination / "pycy.json")
    candidate.to_npz(destination / "pycy.npz")
    figure, axes = plt.subplots(4, 1, figsize=(10, 10), sharex=True)
    for axis, spec in zip(axes, specs, strict=True):
        axis.plot(reference.series("time") * 1000, reference.series(spec.reference), label="PSCAD", linewidth=1.8)
        axis.plot(candidate.series("time") * 1000, candidate.series(spec.candidate), "--", label="PyCy", linewidth=1)
        axis.set_ylabel(f"{spec.candidate} ({spec.unit})")
        axis.grid(alpha=0.3)
        axis.legend()
    axes[-1].set_xlabel("Absolute time (ms), no shift")
    figure.tight_layout()
    figure.savefig(destination / "comparison.png", dpi=150)
    plt.close(figure)
    for relative, expected in {**bindings, **source_hashes}.items():
        if sha256(root / relative) != expected or sha256(destination / "inputs" / relative) != expected:
            raise RuntimeError(f"Input changed during comparison or snapshot: {relative}")
    git = ["git", "-c", f"safe.directory={root.as_posix()}"]
    report = {
        "case_id": manifest["case_id"], "run_id": run_id,
        "passed": source_passed and all(window["passed"] for window in windows),
        "reference_platform": manifest["reference_platform"], "reference_provenance": provenance,
        "reference_samples": len(reference.rows), "candidate_samples": len(candidate.rows),
        "candidate_step_seconds": candidate.time_step, "candidate_method": candidate.method,
        "windows": windows, "source_input_max_abs_error_V": source_error,
        "source_input_passed": source_passed, "known_difference": manifest["known_difference"],
        "reference_initialization_evidence": provenance["initialization_evidence"],
        "native_input_sha256": bindings, "code_and_protocol_sha256": source_hashes,
        "candidate_data_sha256": {name: sha256(destination / name) for name in ("pycy.csv", "pycy.json", "pycy.npz")},
        "plot_sha256": sha256(destination / "comparison.png"), "python_version": platform.python_version(),
        "numpy_version": np.__version__,
        "git_head_at_run": subprocess.check_output([*git, "rev-parse", "HEAD"], cwd=root, text=True).strip(),
        "git_status_at_run": subprocess.check_output([*git, "status", "--porcelain"], cwd=root, text=True).splitlines(),
        "artifacts": {"directory": destination.relative_to(root).as_posix(), "plot": "comparison.png"},
    }
    (destination / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False)
                                            + "\n", encoding="utf-8")
    print(f"finite_r_bergeron: {'PASS' if report['passed'] else 'FAIL'}; {destination / 'report.json'}")
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
