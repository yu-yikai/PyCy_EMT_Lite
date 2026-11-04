"""Run a case against a locally exported vendor reference, outside teaching code."""

from __future__ import annotations

import hashlib
import json
import platform
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
    provenance = json.loads(provenance_file.read_text(encoding="utf-8"))
    reference = SimulationResult.from_csv(reference_file, method=provenance["solver"])
    candidate = Simulator(Circuit.from_components(case.name, case.components), case.config,
                          events=case.events, on_step=case.on_step).run()
    run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    destination = reference_root / "comparison_results" / run_id
    destination.mkdir(parents=True, exist_ok=True)
    candidate.to_csv(destination / "pycy.csv")
    candidate.to_json(destination / "pycy.json")
    candidate.to_npz(destination / "pycy.npz")
    specs = [SignalSpec(**signal) for signal in manifest["signals"]]
    windows = [compare_signals(candidate, reference, specs, start=start, end=end)
               for start, end in manifest["windows_seconds"]]
    model_file = reference_root / "simulink" / manifest["reference_model"]
    report = {
        "case_id": manifest["case_id"], "passed": all(window["passed"] for window in windows),
        "run_id": run_id,
        "reference_platform": manifest["reference_platform"], "reference_provenance": provenance,
        "reference_sha256": sha256(reference_file), "model_sha256": sha256(model_file),
        "provenance_sha256": sha256(provenance_file), "manifest_sha256": sha256(manifest_file),
        "example_sha256": sha256(example_file),
        "export_script_sha256": sha256(manifest_file.parent / "export_reference.m"),
        "python_version": platform.python_version(), "numpy_version": np.__version__,
        "candidate_method": candidate.method, "candidate_step_seconds": candidate.time_step,
        "candidate_samples": len(candidate.rows), "reference_samples": len(reference.rows),
        "known_difference": manifest["known_difference"], "windows": windows,
        "artifacts": {"directory": str(destination.relative_to(root)).replace("\\", "/"),
                      "plot": "comparison.png", "candidate_data": ["pycy.csv", "pycy.json", "pycy.npz"]},
    }
    (destination / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    figure, axes = plt.subplots(len(specs), 1, figsize=(10, 2.4 * len(specs)), sharex=True, squeeze=False)
    for axis, spec in zip(axes[:, 0], specs, strict=True):
        axis.plot(reference.series("time"), reference.series(spec.reference), label="Simscape", linewidth=1.8)
        axis.plot(candidate.series("time"), candidate.series(spec.candidate), label="PyCy", linestyle="--", linewidth=1)
        axis.set_ylabel(f"{spec.candidate} ({spec.unit})")
        axis.grid(True, alpha=0.3)
        axis.legend()
    axes[-1, 0].set_xlabel("Time (s), absolute; no shift")
    figure.tight_layout()
    figure.savefig(destination / "comparison.png", dpi=150)
    plt.close(figure)
    print(f"{manifest['case_id']}: {'PASS' if report['passed'] else 'FAIL'}; {destination / 'report.json'}")
    return report
