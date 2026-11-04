"""Run a case against a locally exported vendor reference, outside teaching code."""

from __future__ import annotations

import hashlib
import json
import platform
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from pycy_emt_lite import Circuit, Simulator
from pycy_emt_lite.cases import CaseDefinition
from pycy_emt_lite.io.results import SimulationResult
from validation.common.comparison import SignalSpec, compare_signals


def sha256(path: Path) -> str:
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def run_comparison(case: CaseDefinition, manifest_file: Path, example_file: Path) -> dict:
    """Preserve PyCy data, full-waveform plot and fixed-window error report.

    A missing local reference is an error, never a synthetic fallback or a pass.
    No MATLAB license is needed to recompare previously exported CSV data.
    """
    root = Path(__file__).resolve().parents[2]
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    reference_root = root / "local_reference" / manifest["case_id"]
    reference_file = reference_root / "normalized_results/reference.csv"
    provenance_file = reference_root / "provenance.json"
    if manifest["time_shift_seconds"] != 0:
        raise ValueError("This comparator does not fit or apply time shifts")
    if not manifest["windows_seconds"]:
        raise ValueError("At least one acceptance window is required")
    provenance = json.loads(provenance_file.read_text(encoding="utf-8"))
    reference = SimulationResult.from_csv(reference_file, method=provenance["solver"])
    candidate = Simulator(Circuit.from_components(case.name, case.components), case.config,
                          events=case.events, on_step=case.on_step).run()
    run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    destination = reference_root / "comparison_results" / run_id
    destination.mkdir(parents=True, exist_ok=True)
    inputs = destination / "inputs"
    inputs.mkdir()
    for source in (reference_file, provenance_file, manifest_file, example_file,
                   manifest_file.parent / "export_reference.m", manifest_file.parent / "compare.py",
                   Path(__file__), Path(__file__).with_name("comparison.py")):
        shutil.copy2(source, inputs / source.name)
    parameter_file = manifest_file.parent / "parameters.json"
    if parameter_file.exists():
        shutil.copy2(parameter_file, inputs / parameter_file.name)
    candidate.to_csv(destination / "pycy.csv")
    candidate.to_json(destination / "pycy.json")
    candidate.to_npz(destination / "pycy.npz")
    specs = [SignalSpec(**signal) for signal in manifest["signals"]]
    windows = [compare_signals(candidate, reference, specs, start=start, end=end)
               for start, end in manifest["windows_seconds"]]
    model_file = reference_root / "simulink" / manifest["reference_model"]
    shutil.copy2(model_file, inputs / model_file.name)
    raw_hashes = {str(path.relative_to(root)).replace("\\", "/"): sha256(path)
                  for path in sorted((reference_root / "raw_results").glob("*")) if path.is_file()}
    report = {
        "case_id": manifest["case_id"], "passed": all(window["passed"] for window in windows),
        "run_id": run_id,
        "reference_platform": manifest["reference_platform"], "reference_provenance": provenance,
        "reference_sha256": sha256(reference_file), "model_sha256": sha256(model_file),
        "provenance_sha256": sha256(provenance_file), "manifest_sha256": sha256(manifest_file),
        "example_sha256": sha256(example_file),
        "export_script_sha256": sha256(manifest_file.parent / "export_reference.m"),
        "parameters_sha256": sha256(parameter_file) if parameter_file.exists() else None,
        "candidate_data_sha256": {name: sha256(destination / name) for name in ("pycy.csv", "pycy.json", "pycy.npz")},
        "raw_reference_sha256": raw_hashes,
        "git_head_at_run": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip(),
        "git_status_at_run": subprocess.check_output(["git", "status", "--porcelain"], cwd=root, text=True).splitlines(),
        "package_source_sha256": {str(path.relative_to(root)).replace("\\", "/"): sha256(path)
                                  for path in sorted((root / "pycy_emt_lite").rglob("*.py"))},
        "python_version": platform.python_version(), "numpy_version": np.__version__,
        "candidate_method": candidate.method, "candidate_step_seconds": candidate.time_step,
        "candidate_samples": len(candidate.rows), "reference_samples": len(reference.rows),
        "known_difference": manifest["known_difference"], "windows": windows,
        "artifacts": {"directory": str(destination.relative_to(root)).replace("\\", "/"),
                      "plot": "comparison.png", "candidate_data": ["pycy.csv", "pycy.json", "pycy.npz"]},
    }
    figure, axes = plt.subplots(len(specs), 1, figsize=(10, 2.4 * len(specs)), sharex=True, squeeze=False)
    for axis, spec in zip(axes[:, 0], specs, strict=True):
        axis.plot(reference.series("time"), reference.series(spec.reference), label="Simscape", linewidth=1.8)
        axis.plot(candidate.series("time"), candidate.series(spec.candidate), label="PyCy", linestyle="--", linewidth=1)
        axis.set_ylabel(f"{spec.candidate} ({spec.unit})")
        axis.grid(True, alpha=0.3)
        for start, end in manifest["windows_seconds"]:
            axis.axvspan(start, end, color="green", alpha=0.04)
        axis.legend()
    axes[-1, 0].set_xlabel("Time (s), absolute; no shift")
    figure.tight_layout()
    figure.savefig(destination / "comparison.png", dpi=150)
    plt.close(figure)
    report["comparison_plot_sha256"] = sha256(destination / "comparison.png")
    report["input_snapshot_sha256"] = {path.name: sha256(path) for path in sorted(inputs.iterdir())}
    (destination / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    print(f"{manifest['case_id']}: {'PASS' if report['passed'] else 'FAIL'}; {destination / 'report.json'}")
    return report
