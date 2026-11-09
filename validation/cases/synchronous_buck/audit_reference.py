"""Audit two complete native Buck runs; never import or run the candidate.

Run from the repository root with explicit baseline/refined directories and a
fresh output directory below local_reference/b2_protocol_research. Source means
are state/duty-derived physical reconstructions, not directly logged currents.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np

from validation.cases.synchronous_buck.normalization import (
    NativeTrace,
    normalize_reference,
)
from validation.common.comparison import SignalSpec, compare_signals

ROOT = Path(__file__).resolve().parents[3]
CASE = Path(__file__).resolve().parent
RESEARCH = ROOT / "local_reference/b2_protocol_research"
MODEL_HASH = "ea8344f62e2a691456363f0391389cd1675bfe246bd71dc8f15a3b838ca6ab42"
FEATURE_KEYS = ["vout_v", "iL_a", "duty", "source_current_a"]


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _hash(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _record(path: Path, hashes: dict[str, str], expected: str | None = None) -> None:
    actual = _hash(path)
    hashes[str(path.resolve())] = actual
    _require(expected is None or actual == expected, f"Hash mismatch: {path}")


def _read(path: Path, hashes: dict[str, str]) -> Any:
    _record(path, hashes)
    return json.loads(path.read_text(encoding="utf-8"))


def _snapshot_inputs(output: Path, hashes: dict[str, str]) -> list[dict[str, str]]:
    """Retain the actual audit sources and frozen protocol, not only hashes."""
    names = ["audit_reference.py", "normalization.py", "export_reference.m", "manifest.json", "parameters.json",
             "acceptance_plan.md", "native_logging_api_addendum.md", "reference_solver_addendum.md",
             "reference_solver_addendum.json"]
    sources = [CASE / name for name in names] + [ROOT / "validation/common/comparison.py"]
    snapshots = []
    for source in sources:
        _record(source, hashes)
        target = output / "inputs" / source.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(source.read_bytes())
        _record(target, hashes, hashes[str(source.resolve())])
        snapshots.append({"source": str(source), "snapshot": str(target.relative_to(output)),
                          "sha256": hashes[str(source.resolve())]})
    return snapshots


def _child(directory: Path, name: str) -> Path:
    path = (directory / name).resolve()
    _require(path.is_relative_to(directory.resolve()), f"Path leaves its input directory: {name}")
    return path


def _csv(path: Path, columns: int, *, header: bool = False) -> np.ndarray:
    data = np.loadtxt(path, delimiter=",", skiprows=int(header), ndmin=2)
    _require(data.shape[1] == columns and len(data) >= 2, f"Unexpected CSV shape: {path}")
    _require(bool(np.all(np.isfinite(data))), f"Nonfinite CSV data: {path}")
    _require(bool(np.all(np.diff(data[:, 0]) >= 0)), f"Time regression: {path}")
    return data


def _load_run(directory: Path, stage: str, hashes: dict[str, str]) -> tuple[NativeTrace, np.ndarray, dict]:
    """Check saved identities before using any waveform for normalization."""
    attempt = _read(directory / "attempt.json", hashes)
    after = _read(directory / "after_simulation.json", hashes)
    completion = _read(directory / "completion.json", hashes)
    _require(all(item["stage"] == stage for item in [attempt, after, completion]), "Native stage mismatch")
    _require(completion["simulation_and_extraction_complete"] is True
             and completion["closed_without_saving"] is True
             and completion["candidate_created_by_exporter"] is False
             and completion["physical_or_control_parameters_changed"] is False, "Incomplete or modified native run")
    inputs = directory / "inputs"
    input_names = [entry["file"] for entry in attempt["inputs"]]
    _require(len(input_names) == len(set(input_names))
             and {"export_reference.m", "SynchronousBuckConverter.slx"}.issubset(input_names), "Missing/duplicate input identity")
    for entry in attempt["inputs"]:
        path = _child(inputs, entry["file"])
        _record(path, hashes, entry["sha256"])
        _require(path.stat().st_size == entry["bytes"], f"Input size mismatch: {path}")
    snapshots = {item["file"]: item for item in attempt["protocol_snapshots"]}
    for name in ["acceptance_plan.md", "manifest.json", "parameters.json", "native_logging_api_addendum.md"]:
        _require(name in snapshots, f"Missing protocol snapshot: {name}")
    for name, entry in snapshots.items():
        _require(name in input_names, f"Protocol absent from input inventory: {name}")
        path = _child(inputs, name)
        _record(path, hashes, entry["sha256_raw"])
        _require(hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest() == entry["sha256_lf"],
                 f"Snapshot LF hash mismatch: {name}")
        current = _child(CASE, name)
        _record(current, hashes)
        _require(hashlib.sha256(current.read_bytes().replace(b"\r\n", b"\n")).hexdigest() == entry["sha256_lf"],
                 f"Current protocol differs from saved snapshot: {name}")
    protocol_name = Path(attempt["protocol_source"]).name
    _require(protocol_name in snapshots, "Missing explicitly selected protocol snapshot")
    _record(inputs / protocol_name, hashes, attempt["protocol_sha256"])
    parameters = _read(inputs / "parameters.json", hashes)
    _require(parameters["reference_model_sha256"] == MODEL_HASH and parameters["stop_second"] == .01,
             "Unexpected reference model or stop time")
    addendum = "reference_solver_addendum.json"
    if addendum in snapshots:
        _require("reference_solver_addendum.md" in snapshots and protocol_name == "reference_solver_addendum.md",
                 "Solver addendum must be explicitly selected and snapshotted")
        settings, settings_source = _read(inputs / addendum, hashes), addendum
    else:
        _require(not (inputs / addendum).exists() and protocol_name == "acceptance_plan.md",
                 "Unrecorded solver addendum; no silent fallback")
        settings, settings_source = parameters["reference_solver"], "parameters.json reference_solver (original protocol)"
    selected = settings[stage]
    _require(settings["solver"] == "ode23tb" and settings["auto_scale_abs_tol"] == "off",
             "Unexpected solver or AbsTol scaling")
    _require(attempt["requested_solver_settings"] == selected, "Attempt differs from selected solver protocol")
    requested = {item["Name"]: item["Value"] for item in attempt["simulation_input_model_parameters"]}
    for field, expected in {"StartTime": 0., "StopTime": .01, "MaxStep": selected["max_step_s"],
                            "RelTol": selected["relative_tolerance"], "AbsTol": selected["absolute_tolerance"]}.items():
        _require(float(requested[field]) == expected, f"SimulationInput {field} mismatch")
    _require(requested["Solver"] == "ode23tb" and requested["AutoScaleAbsTol"] == "off",
             "SimulationInput solver mismatch")
    _require(after["actual_solver"]["Solver"] == "ode23tb"
             and after["actual_solver"]["MaxStepSize"] == selected["max_step_s"], "Actual solver mismatch")
    execution = after["execution_info"]
    _require(execution["StopEvent"] == "ReachedStopTime" and not execution["ErrorDiagnostic"],
             "Native simulation did not finish successfully")
    _require(after["model_dirty_after_sim"] == "off"
             and after["stored_config_after_sim"] == attempt["original_model_config"], "Model/configuration changed")
    _require(attempt["model_sha256"] == after["source_model_sha256"] == after["copy_model_sha256"] == MODEL_HASH,
             "Model identity mismatch")
    _record(inputs / "SynchronousBuckConverter.slx", hashes, MODEL_HASH)
    _record(ROOT / "local_reference/synchronous_buck/simulink/SynchronousBuckConverter.slx", hashes, MODEL_HASH)
    _record(directory / "simulation_input.mat", hashes)
    _record(directory / "simulink_output.mat", hashes, after["raw_mat_sha256"])
    inventory_file = directory / "evidence_inventory.json"
    inventory_count = None
    if inventory_file.exists():
        inventory = _read(inventory_file, hashes)
        for entry in inventory["files"]:
            path = _child(directory, entry["path"])
            _record(path, hashes, entry["sha256"])
            _require(path.stat().st_size == entry["bytes"], f"Inventory size mismatch: {path}")
        inventory_count = len(inventory["files"])
    extracted = directory / "extracted"
    extraction = _read(extracted / "extraction_metadata.json", hashes)
    _require(Path(extraction["source_mat"]).resolve() == (directory / "simulink_output.mat").resolve()
             and extraction["source_mat_sha256"] == after["raw_mat_sha256"], "Extraction source identity mismatch")
    _require(extraction["state_groups"] == 4 and extraction["total_saved_state_width"] == 5
             and extraction["native_duplicates_preserved"] is True
             and extraction["discrete_axes_preserved_without_extension"] is True
             and extraction["resampled"] is False and extraction["sim_invoked"] is False, "Unexpected extraction")
    state_inventory = _read(extracted / "state_inventory.json", hashes)
    _require(len(state_inventory) == 4, "Need all four original state groups")
    expected_paths = ["Continuous PI/Integrator", "Continuous PI/Measurement lag", "Triangle Generator/Model/Unit Delay",
                      "powergui/EquivalentModel1/State-Space"]
    states = []
    for index, width in enumerate([1, 1, 1, 2], start=1):
        entry = state_inventory[index - 1]
        name = f"native_state_{index:02d}.csv"
        _require(entry["index"] == index and entry["width"] == width and entry["csv"] == name,
                 f"State group {index} identity mismatch")
        _require(len(entry["block_paths"]) == 1 and entry["block_paths"][0].endswith(expected_paths[index - 1]),
                 f"State group {index} physical mapping mismatch")
        _record(extracted / name, hashes, entry["sha256"])
        data = _csv(extracted / name, width + 1, header=True)
        _require(entry["rows"] == len(data) and entry["time_first"] == data[0, 0]
                 and entry["time_last"] == data[-1, 0] and entry["negative_time_increments"] == 0
                 and entry["duplicate_time_increments"] == int(np.sum(np.diff(data[:, 0]) == 0)),
                 f"State group {index} metadata mismatch")
        states.append(data)
    _require(state_inventory[2]["name"] == "DSTATE" and states[2][0, 0] >= 0
             and states[2][-1, 0] <= .01, "Invalid independent DSTATE axis")
    duty_path, source_path = extracted / "duty_native.csv", extracted / "source_current_native.csv"
    for path in [duty_path, source_path]:
        _record(path, hashes)
    duty, source = _csv(duty_path, 2), _csv(source_path, 2)
    time = states[3][:, 0]
    _require(all(np.array_equal(time, data[:, 0]) for data in [states[0], states[1], duty, source]),
             "Continuous state/Scope axes differ; never resample to hide this")
    trace = NativeTrace(time, states[3][:, 1], states[3][:, 2], states[0][:, 1], states[1][:, 1],
                        duty[:, 1], source[:, 1])
    metadata = {"directory": str(directory), "stage": stage, "matlab_version": attempt["matlab_version"],
                "solver_protocol": settings_source, "requested_solver_settings": selected,
                "selected_protocol": protocol_name, "selected_protocol_sha256": attempt["protocol_sha256"],
                "selected_protocol_lf_sha256": snapshots[protocol_name]["sha256_lf"],
                "protocol_snapshots_lf_sha256": {name: entry["sha256_lf"] for name, entry in snapshots.items()},
                "actual_solver": after["actual_solver"], "execution_info": execution,
                "controller_tolerances_recorded": attempt["original_controller_block_tolerances"],
                "controller_tolerance_note": "Unavailable block fields are unknown; requested global tolerances are not observed global error bounds",
                "inventory_files_verified": inventory_count, "identity_checks_passed": True,
                "dstate": {"samples": len(states[2]), "first": states[2][0, 0], "last": states[2][-1, 0],
                           "independent_axis_preserved": True, "resampled": False},
                "warnings_absent": not bool(execution["WarningDiagnostics"])}
    return trace, states[2], metadata


def _check_pair_metadata(baseline: dict, refined: dict) -> dict:
    """Refinements must use one protocol and native software version."""
    fields = ["solver_protocol", "selected_protocol", "selected_protocol_sha256", "selected_protocol_lf_sha256",
              "protocol_snapshots_lf_sha256", "matlab_version"]
    for field in fields:
        _require(field in baseline and field in refined, f"Native reference pair missing {field}")
        _require(baseline[field] == refined[field], f"Native reference pair differs in {field}")
    return {"passed": True, "matched_fields": fields}


def _write_json(path: Path, payload: Any) -> None:
    """Keep JSON strict; name every scalar/array nonfinite converted to null."""
    nonfinite = []

    def safe(value: Any, key: str) -> Any:
        if isinstance(value, np.ndarray):
            return safe(value.tolist(), key)
        if isinstance(value, np.generic):
            return safe(value.item(), key)
        if isinstance(value, float) and not np.isfinite(value):
            nonfinite.append(key)
            return None
        if isinstance(value, dict):
            return {name: safe(item, f"{key}/{name}") for name, item in value.items()}
        if isinstance(value, (list, tuple)):
            return [safe(item, f"{key}/{index}") for index, item in enumerate(value)]
        return value

    result = safe(payload, "")
    result["json_serialization"] = {"nonfinite_values_replaced_by_null": nonfinite,
                                  "contains_nonfinite_values": bool(nonfinite)}
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def _save_normalization(directory: Path, trace: NativeTrace, discrete: np.ndarray, normalized: dict) -> None:
    arrays = {f"raw/{name}": getattr(trace, name) for name in trace.__dataclass_fields__}
    arrays["raw/independent_dstate"] = discrete

    def array_references(value: Any, key: str) -> Any:
        if isinstance(value, np.ndarray):
            arrays[key] = value
            return {"npz_key": key, "shape": list(value.shape), "dtype": str(value.dtype),
                    "nonfinite_count": int(np.sum(~np.isfinite(value)))}
        if isinstance(value, dict):
            return {name: array_references(item, f"{key}/{name}") for name, item in value.items()}
        if isinstance(value, list):
            return [array_references(item, f"{key}/{index}") for index, item in enumerate(value)]
        return value

    diagnostics = array_references(normalized, "normalization")
    npz = directory / "raw_and_diagnostics.npz"
    np.savez_compressed(npz, **arrays)
    _write_json(directory / "diagnostics.json", {"diagnostics": diagnostics, "npz_file": npz.name,
                                                "npz_sha256": _hash(npz), "raw_duplicates_preserved": True})
    np.savetxt(directory / "cycle_means.csv", normalized["cycle_means"], delimiter=",", fmt="%.17g",
               header=",".join(normalized["cycle_mean_columns"]), comments="")


class _ContinuousStates:
    """Only UC/iL are continuous across the native load events (zero ESR)."""

    def __init__(self, trace: NativeTrace, normalized: dict):
        last = normalized["last_raw_indices"]
        self.values = {"time": normalized["time"], "vout": trace.uC[last], "iL": trace.iL[last]}

    def series(self, name: str) -> np.ndarray:
        return self.values[name]


def _compare(runs: dict, manifest: dict, output: Path) -> dict:
    fraction = manifest["reference_self_refinement"]["max_error_fraction_of_candidate_limits"]
    specs = [SignalSpec(item["reference"], item["reference"], item["unit"], item["scale"],
                        item["max_nrmse"] * fraction, item["max_abs_error"] * fraction)
             for item in manifest["signals"]]
    views = [_ContinuousStates(*runs[stage]) for stage in ["baseline", "refined"]]
    continuous = [compare_signals(views[0], views[1], specs, start=start, end=end)
                  for start, end in manifest["windows_seconds"]]
    cycle_settings = manifest["cycle_features"]
    cycles = [runs[stage][1]["cycle_means"] for stage in ["baseline", "refined"]]
    _require(all(data.shape == (cycle_settings["cycles"], 4) for data in cycles), "Missing carrier cycles")
    differences = cycles[0] - cycles[1]
    limits = np.array([cycle_settings["max_absolute_mean_errors"][name] * fraction for name in FEATURE_KEYS])
    np.savetxt(output / "cycle_mean_errors.csv", differences, delimiter=",", fmt="%.17g",
               header=",".join(runs["baseline"][1]["cycle_mean_columns"]), comments="")
    features = {"columns": runs["baseline"][1]["cycle_mean_columns"], "cycles": len(differences),
                "all_absolute_cycles_included": True, "period_seconds": cycle_settings["period_s"],
                "max_abs_errors": abs(differences).max(axis=0),
                "rms_errors": np.sqrt(np.mean(differences**2, axis=0)), "max_abs_limits": limits,
                "worst_cycle_indices_zero_based": abs(differences).argmax(axis=0),
                "passed": bool(np.all(abs(differences) <= limits))}
    return {"continuous": continuous, "period_features": features,
            "passed": all(item["passed"] for item in continuous) and features["passed"]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--refined", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--duty-error-assumption", type=float, required=True,
                        help="Explicit conditional anchor error assumption, never inferred from solver AbsTol")
    args = parser.parse_args()
    output = args.output.resolve()
    _require(output.is_relative_to(RESEARCH.resolve()) and output != RESEARCH.resolve(), "Output must be below research root")
    _require(output.parent.is_dir() and not output.exists(), "Output parent must exist; output must be new")
    _require(np.isfinite(args.duty_error_assumption) and args.duty_error_assumption >= 0, "Invalid duty error assumption")
    _require(args.baseline.resolve() != args.refined.resolve(), "Need two independent native runs")
    output.mkdir()
    hashes: dict[str, str] = {}
    report: dict[str, Any] = {"scope": "Native reference self-refinement only; no candidate imported or run",
                              "passed": False, "runs": {}, "input_sha256": hashes,
                              "explicit_duty_error_assumption": args.duty_error_assumption,
                              "accuracy_claim": "Conditional numerical evidence, not an absolute global error proof",
                              "source_current_label": "Derived from actual native storage states/duty, analytic carrier and physical KCL; raw measured samples remain in NPZ",
                              "assumptions": ["Diode-inactivity model and physical equations apply",
                                              "Explicit anchor duty error bound holds",
                                              "Native UC/filtered-error anchor errors preserve local derivative/clipping bounds; duty error alone is insufficient",
                                              "No hidden physical roots; both full native runs require checks"]}
    report["input_snapshots"] = _snapshot_inputs(output, hashes)
    manifest = _read(CASE / "manifest.json", hashes)
    runs = {}
    for stage in ["baseline", "refined"]:
        target = output / stage
        target.mkdir()
        try:
            trace, discrete, metadata = _load_run(getattr(args, stage).resolve(), stage, hashes)
            normalized = normalize_reference(trace, duty_error_assumption=args.duty_error_assumption)
            _save_normalization(target, trace, discrete, normalized)
            edge = normalized["conditional_root_certificate"]
            budget = manifest["cycle_features"]["maximum_reference_source_edge_interpolation_charge_budget_c_per_cycle"]
            edge_passed = bool(np.all(edge["charge_per_cycle"] <= budget))
            source_power = 30 * float(np.mean(normalized["cycle_means"][:, 3]))
            metadata.update(normalization_checks=normalized["checks"], summary=normalized["summary"],
                            isolated_roots=len(normalized["roots"]), conditional_edge_charge_budget_c=budget,
                            conditional_edge_charge_budget_passed=edge_passed,
                            whole_record_derived_source_power_w=source_power,
                            source_power_direction_passed=np.isfinite(source_power) and source_power > 0,
                            passed=all(normalized["checks"].values()) and edge_passed
                            and metadata["warnings_absent"] and np.isfinite(source_power) and source_power > 0)
            report["runs"][stage] = metadata
            runs[stage] = (trace, normalized)
        except (OSError, ValueError, KeyError, TypeError) as error:
            report["runs"][stage] = {"passed": False, "error_type": type(error).__name__, "error": str(error)}
    if len(runs) == 2:
        try:
            report["pair_identity"] = _check_pair_metadata(report["runs"]["baseline"], report["runs"]["refined"])
            report["comparison"] = _compare(runs, manifest, output)
            report["passed"] = report["comparison"]["passed"] and all(item["passed"] for item in report["runs"].values())
        except (OSError, ValueError, KeyError, TypeError) as error:
            report["comparison"] = {"passed": False, "error_type": type(error).__name__, "error": str(error)}
    _write_json(output / "report.json", report)
    print(f"Reference self-refinement {'PASS' if report['passed'] else 'FAIL'}: {output / 'report.json'}")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
