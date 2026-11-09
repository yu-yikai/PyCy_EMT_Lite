"""Compare the unchanged 50 ns Buck candidate with an audited native reference.

Run: python -m validation.cases.synchronous_buck.compare
Canonical provenance must bind a passing full native reference pair first.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import runpy
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

from pycy_emt_lite import Circuit, Simulator
from validation.cases.synchronous_buck.audit_reference import _load_run
from validation.cases.synchronous_buck.quadrature import candidate_features
from validation.common.comparison import SignalSpec, compare_signals

ROOT = Path(__file__).resolve().parents[3]
CASE = Path(__file__).resolve().parent
REFERENCE = ROOT / "local_reference/synchronous_buck"
FEATURE_KEYS = ["vout_v", "iL_a", "duty", "source_current_a"]
FEATURE_COLUMNS = ["uC", "iL", "duty", "reconstructed_source_current"]


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _hash(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _lf_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")).hexdigest()


def _local_path(value: str) -> Path:
    path = (ROOT / value).resolve()
    _require(path.is_relative_to((ROOT / "local_reference").resolve()), "Reference path must stay below local_reference")
    return path


class ContinuousStorage:
    """Only UC/iL are continuous across this Buck's declared load events.

    This view never changes or copies away the original result's event_log.
    It deliberately cannot expose a jumping source current or gate signal.
    """

    def __init__(self, time: np.ndarray, voltage: np.ndarray, current: np.ndarray, *, candidate: bool):
        self.values = {"time": time, "v:out" if candidate else "vout": voltage,
                       "i:L" if candidate else "iL": current}

    def series(self, name: str) -> np.ndarray:
        return self.values[name]


def load_reference(provenance_file: Path) -> dict:
    """Verify provenance and actual native bytes before candidate execution."""
    provenance = json.loads(provenance_file.read_text(encoding="utf-8-sig"))
    _require(provenance["reference_stage"] == "refined", "Only the audited refined stage may be canonical")
    manifest = json.loads((CASE / "manifest.json").read_text(encoding="utf-8"))
    _require(all(provenance[key] == manifest[key] for key in ["case_id", "reference_id"]),
             "Canonical case/reference identity differs from the manifest")
    _require(provenance["solver"] == "ode23tb" and provenance["platform"] == manifest["reference_platform"],
             "Reference platform/solver differs from the frozen case")
    _require(_lf_hash(CASE / "candidate_quadrature_addendum.md")
             == provenance["candidate_quadrature_addendum_lf_sha256"], "Candidate quadrature clarification changed")
    files = {key: _local_path(provenance[key])
             for key in ["reference_audit_report", "reference_npz", "reference_cycle_means"]}
    hash_keys = {"reference_audit_report": "reference_audit_sha256", "reference_npz": "reference_npz_sha256",
                 "reference_cycle_means": "reference_cycle_means_sha256"}
    for key, path in files.items():
        _require(_hash(path) == provenance[hash_keys[key]], f"Canonical reference hash mismatch: {key}")
    audit_path = files["reference_audit_report"]
    _require(files["reference_npz"] == audit_path.parent / "refined/raw_and_diagnostics.npz"
             and files["reference_cycle_means"] == audit_path.parent / "refined/cycle_means.csv",
             "Reference arrays must be the selected audit's actual refined artifacts")
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    _require(audit["passed"] is True and audit["comparison"]["passed"] is True
             and audit["pair_identity"]["passed"] is True
             and all(audit["runs"][stage]["passed"] is True for stage in ["baseline", "refined"]),
             "Reference self-refinement has not passed")
    hashes: dict[str, str] = {}
    for name, expected in audit["input_sha256"].items():
        path = (ROOT / name).resolve()
        _require(path.is_relative_to(ROOT.resolve()), f"Audited input leaves repository: {name}")
        actual = _hash(path)
        _require(actual == expected, f"Audited input changed: {path}")
        hashes[str(path)] = actual
    for stage in ["baseline", "refined"]:
        saved = provenance["runs"][stage]
        directory = _local_path(saved["directory"])
        _require(directory == _local_path(audit["runs"][stage]["directory"]), "Canonical native run differs from passing pair")
        for name, key in [("simulink_output.mat", "raw_mat_sha256"), ("completion.json", "completion_sha256"),
                          ("resource_summary.json", "resource_summary_sha256")]:
            file = directory / name
            digest = _hash(file)
            _require(digest == saved[key], f"Canonical native artifact changed: {stage}/{name}")
            hashes[str(file)] = digest
        terminal = json.loads((directory / "resource_summary.json").read_text(encoding="utf-8-sig"))
        _require(terminal["termination_reason"] == "process_completed" and terminal["exit_code"] == 0
                 and terminal["owned_all_exited"] is True and terminal["monitor_error"] is None
                 and terminal["cleanup_error"] is None, "Native reference monitor is not successfully terminated")
    _require(provenance["requested_solver_settings"] == audit["runs"]["refined"]["requested_solver_settings"]
             and provenance["matlab_version"] == audit["runs"]["refined"]["matlab_version"], "Canonical native settings/version mismatch")
    for name in ["manifest.json", "parameters.json", "acceptance_plan.md", "reference_solver_addendum.md",
                 "reference_solver_addendum.json", "native_logging_api_addendum.md"]:
        _require(_hash(CASE / name) == audit["input_sha256"][str((CASE / name).resolve())],
                 f"Frozen reference protocol changed: {name}")
        _require(_lf_hash(CASE / name) == provenance["frozen_protocol_lf_sha256"][name],
                 f"Canonical frozen protocol differs: {name}")
    raw_directory = _local_path(audit["runs"]["refined"]["directory"])
    trace, discrete, native_metadata = _load_run(raw_directory, "refined", hashes)
    _require(_hash(raw_directory / "simulink_output.mat") == provenance["reference_raw_mat_sha256"], "Canonical raw MAT mismatch")
    parameters = json.loads((CASE / "parameters.json").read_text(encoding="utf-8"))
    _require(provenance["model_sha256"] == parameters["reference_model_sha256"], "Canonical source model mismatch")
    with np.load(files["reference_npz"], allow_pickle=False) as arrays:
        for name in trace.__dataclass_fields__:
            _require(np.array_equal(arrays[f"raw/{name}"], getattr(trace, name)), f"Audited NPZ raw {name} differs from native CSV")
        _require(np.array_equal(arrays["raw/independent_dstate"], discrete), "Audited discrete axis differs from native")
        last = arrays["normalization/last_raw_indices"]
        expected_last = np.r_[np.flatnonzero(np.diff(trace.time) > 0), len(trace.time) - 1]
        _require(np.array_equal(last, expected_last), "Unexpected continuous derived-axis mapping")
        time = arrays["normalization/time"]
        _require(np.array_equal(time, trace.time[last]), "Unexpected normalized continuous axis")
        cycles = np.loadtxt(files["reference_cycle_means"], delimiter=",", skiprows=1, ndmin=2)
        _require(np.array_equal(cycles, arrays["normalization/cycle_means"])
                 and cycles.shape == (manifest["cycle_features"]["cycles"], 4), "Reference cycle means differ from audited data")
        charges = arrays["normalization/conditional_root_certificate/charge_per_cycle"]
        _require(bool(np.all(charges <= manifest["cycle_features"]["maximum_reference_source_edge_interpolation_charge_budget_c_per_cycle"])),
                 "Audited conditional edge-charge budget failed")
    hashes.update({str(path): _hash(path) for path in [provenance_file, *files.values()]})
    return {"provenance": provenance, "audit": audit, "native_metadata": native_metadata,
            "view": ContinuousStorage(time, trace.uC[last], trace.iL[last], candidate=False),
            "cycles": cycles, "input_hashes": hashes,
            "files": [provenance_file, *files.values(), audit_path.parent / "refined/diagnostics.json"]}


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def _plots(directory: Path, candidate: ContinuousStorage, reference: ContinuousStorage,
           candidate_cycles: np.ndarray, reference_cycles: np.ndarray, limits: np.ndarray, period: float) -> None:
    import matplotlib.pyplot as plt

    figure, axes = plt.subplots(2, 1, figsize=(11, 6), sharex=True)
    for axis, actual, expected, unit in zip(axes, ["v:out", "i:L"], ["vout", "iL"], ["V", "A"], strict=True):
        axis.plot(reference.series("time"), reference.series(expected), label="Native Simulink", linewidth=1.4)
        axis.plot(candidate.series("time"), candidate.series(actual), label="PyCy 50 ns", linewidth=.8, linestyle="--")
        axis.set_ylabel(f"{expected} ({unit})")
        axis.grid(True, alpha=.3)
        axis.legend()
    axes[-1].set_xlabel("Absolute time (s), no shift")
    figure.tight_layout()
    figure.savefig(directory / "continuous_comparison.png", dpi=150)
    plt.close(figure)
    figure, axes = plt.subplots(4, 2, figsize=(13, 10), sharex=True)
    time = (np.arange(len(candidate_cycles)) + .5) * period
    for column, label in enumerate(FEATURE_COLUMNS):
        axes[column, 0].plot(time, reference_cycles[:, column], label="Native derived means")
        axes[column, 0].plot(time, candidate_cycles[:, column], label="PyCy mode/hold means", linestyle="--", linewidth=.8)
        axes[column, 0].set_ylabel(label)
        axes[column, 0].legend()
        axes[column, 1].plot(time, abs(candidate_cycles[:, column] - reference_cycles[:, column]))
        axes[column, 1].axhline(limits[column], color="red", linestyle="--", label="Frozen limit")
        axes[column, 1].set_ylabel("Absolute mean error")
        axes[column, 1].legend()
        for axis in axes[column]:
            axis.grid(True, alpha=.3)
    for axis in axes[-1]:
        axis.set_xlabel("Absolute cycle midpoint (s), all 500 cycles")
    figure.tight_layout()
    figure.savefig(directory / "cycle_comparison.png", dpi=150)
    plt.close(figure)


def run_comparison(provenance_file: Path, destination: Path) -> dict:
    """Save a fresh full comparison; failure never updates canonical data."""
    _require(destination.resolve().is_relative_to((ROOT / "local_reference").resolve()) and not destination.exists(),
             "Comparison output must be a new child below local_reference")
    destination.mkdir(parents=True)
    inputs = destination / "inputs"
    inputs.mkdir()
    report = {"case_id": "synchronous_buck", "passed": False, "output": str(destination),
              "scope": "Candidate commercial comparison; separate from native reference self-refinement",
              "git_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
              "git_status": subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).splitlines(),
              "python_version": platform.python_version(), "numpy_version": np.__version__,
              "package_source_sha256": {str(path.relative_to(ROOT)): _hash(path) for path in sorted((ROOT / "pycy_emt_lite").rglob("*.py"))}}
    try:
        reference = load_reference(provenance_file)
        manifest = json.loads((CASE / "manifest.json").read_text(encoding="utf-8"))
        parameters = json.loads((CASE / "parameters.json").read_text(encoding="utf-8"))
        _require(manifest["time_shift_seconds"] == 0, "Buck comparison never fits or applies a time shift")
        example = ROOT / "examples/26_synchronous_buck.py"
        sources = [*CASE.glob("*.py"), *CASE.glob("*.json"), *CASE.glob("*.md"), example,
                   ROOT / "validation/common/comparison.py", *reference["files"]]
        snapshots = []
        for index, source in enumerate(dict.fromkeys(sources)):
            target = inputs / f"{index:02d}_{source.name}"
            # Large audited NPZ stays in place, bound by provenance/hash; never duplicate the raw MAT.
            if source.suffix == ".npz":
                snapshots.append({"source": str(source), "sha256": _hash(source), "snapshot": None})
            else:
                shutil.copy2(source, target)
                snapshots.append({"source": str(source), "sha256": _hash(source), "snapshot": target.name})
        report.update(input_snapshots=snapshots, reference_provenance=reference["provenance"],
                      reference_input_sha256=reference["input_hashes"],
                      reference_self_refinement=reference["audit"]["comparison"],
                      known_difference=manifest["known_difference"])
        _write_json(destination / "input_snapshot.json", report)
        case = runpy.run_path(str(example))["define_case"]()
        _require(case.config.time_step == parameters["time_step_second"] and case.config.stop_time == parameters["stop_second"]
                 and case.config.method == parameters["integration_method"], "Candidate numerical configuration changed")
        candidate = Simulator(Circuit.from_components(case.name, case.components), case.config,
                              events=case.events, on_step=case.on_step).run()
        candidate.to_csv(destination / "pycy.csv")
        candidate.to_json(destination / "pycy.json")
        candidate.to_npz(destination / "pycy.npz")
        _write_json(destination / "event_log.json", {"events": candidate.event_log})
        features = candidate_features(candidate, parameters, manifest["cycle_features"])
        view = ContinuousStorage(candidate.series("time"), candidate.series("v:out"), candidate.series("i:L"), candidate=True)
        specs = [SignalSpec(**signal) for signal in manifest["signals"]]
        windows = [compare_signals(view, reference["view"], specs, start=start, end=end)
                   for start, end in manifest["windows_seconds"]]
        cycles = features.pop("cycle_means")
        residual = features.pop("source_kcl_residual")
        reconstructed = features.pop("reconstructed_source_rows")
        np.savez_compressed(destination / "candidate_physical_diagnostics.npz", time=candidate.series("time"),
                            rowwise_source_kcl_residual=residual, reconstructed_source_rows=reconstructed)
        differences = cycles - reference["cycles"]
        limits = np.array([manifest["cycle_features"]["max_absolute_mean_errors"][name] for name in FEATURE_KEYS])
        period_features = {"columns": FEATURE_COLUMNS, "cycles": len(cycles), "all_absolute_cycles_included": True,
                           "max_abs_errors": abs(differences).max(axis=0).tolist(), "max_abs_limits": limits.tolist(),
                           "rms_errors": np.sqrt(np.mean(differences**2, axis=0)).tolist(),
                           "worst_cycle_indices_zero_based": abs(differences).argmax(axis=0).tolist(),
                           "passed": bool(np.all(abs(differences) <= limits))}
        for name, values in [("candidate_cycle_means.csv", cycles), ("cycle_mean_errors.csv", differences)]:
            np.savetxt(destination / name, values, delimiter=",", fmt="%.17g", header=",".join(FEATURE_COLUMNS), comments="")
        _plots(destination, view, reference["view"], cycles, reference["cycles"], limits, manifest["cycle_features"]["period_s"])
        hashes_stable = all(_hash(Path(source)) == digest for source, digest in reference["input_hashes"].items())
        hashes_stable = hashes_stable and all(_hash(Path(item["source"])) == item["sha256"] for item in snapshots)
        report.update(windows=windows, period_features=period_features, candidate_physical_checks=features,
                      reference_inputs_unchanged=hashes_stable, candidate_samples=len(candidate.rows),
                      candidate_step_seconds=candidate.time_step, candidate_method=candidate.method,
                      candidate_event_log=candidate.event_log,
                      source_current_note="Both cycle-source quantities are explicitly mode/state-derived; raw measured source columns remain in full saved artifacts.",
                      reference_accuracy_note=reference["audit"]["accuracy_claim"],
                      reference_accuracy_assumptions=reference["audit"]["assumptions"],
                      passed=hashes_stable and features["passed"] and period_features["passed"] and all(window["passed"] for window in windows))
    except (OSError, ValueError, KeyError, TypeError, RuntimeError) as error:
        report.update(error_type=type(error).__name__, error=str(error), passed=False)
    report["artifact_sha256"] = {str(path.relative_to(destination)): _hash(path)
                                  for path in sorted(destination.rglob("*")) if path.is_file() and path.name != "report.json"}
    _write_json(destination / "report.json", report)
    print(f"synchronous_buck: {'PASS' if report['passed'] else 'FAIL'}; {destination / 'report.json'}")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--provenance", type=Path, default=REFERENCE / "provenance.json")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    destination = args.output or REFERENCE / "comparison_results" / datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    if not run_comparison(args.provenance.resolve(), destination.resolve())["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
