"""Synthetic signal/archive tests only; never execute example11 or native tools."""

import copy
import hashlib
import json
import math
import shutil
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from pycy_emt_lite.io.results import SimulationResult
from validation.cases.pll_dynamic_response import compare

ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "validation/cases/pll_dynamic_response"


@pytest.fixture(autouse=True)
def offline_backend(monkeypatch):
    monkeypatch.setenv("MPLBACKEND", "Agg")


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def descriptor(root, path):
    return {"path": path.relative_to(root).as_posix(), "bytes": path.stat().st_size,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


@pytest.fixture
def protocol():
    return read(CASE / "reference_protocol.json")


@pytest.fixture
def smooth_signals():
    """Analytic angle/source identities, deliberately not a synthetic PI solve."""
    time = np.arange(10001) * .0001
    omega = 2 * math.pi * 50
    angle = np.remainder(omega * time, 2 * math.pi)
    q = math.sqrt(2) * 230 * np.sin(omega * time - math.pi / 3 - angle)
    rows = [{"time": float(t), "angle": float(a), "frequency": omega,
             "q_axis_voltage": float(v)} for t, a, v in zip(time, angle, q, strict=True)]
    return SimulationResult("SYNTHETIC analytic signals", "identity_fixture", .0001, 1., rows)


def test_common_anchor_unwrap_preserves_raw_and_multiple_turns(smooth_signals, protocol):
    original_rows = copy.deepcopy(smooth_signals.rows)
    view = compare.comparison_view(smooth_signals, protocol)
    assert view is not smooth_signals
    assert smooth_signals.rows == original_rows
    assert view.series("angle_unwrapped") == pytest.approx(2 * math.pi * 50 * view.series("time"), abs=1e-11)
    assert view.series("angle_unwrapped")[0] == 0
    assert view.series("angle_unwrapped")[-1] > 49 * 2 * math.pi
    assert view.series("q_axis_voltage") == pytest.approx(smooth_signals.series("q_axis_voltage"), abs=0)


@pytest.mark.parametrize("fault", ["endpoint", "duplicate", "nonfinite", "advance", "initial", "ambiguous", "q_phase", "missing", "fitted_turn"])
def test_signal_semantics_reject_invalid_observations(smooth_signals, protocol, fault):
    rows = smooth_signals.rows
    if fault == "endpoint":
        rows[-1]["time"] -= 1e-15
    elif fault == "duplicate":
        rows[1]["time"] = rows[0]["time"]
    elif fault == "nonfinite":
        rows[20]["frequency"] = math.nan
    elif fault == "advance":
        rows[20]["angle"] += .01
    elif fault == "initial":
        rows[0]["angle"] = .001
    elif fault == "ambiguous":
        rows[20]["frequency"] = math.pi / .0001
    elif fault == "q_phase":
        rows[20]["q_axis_voltage"] += 1.
    elif fault == "missing":
        rows.pop(20)
    else:
        for row in rows:
            row["angle"] += 2 * math.pi
    with pytest.raises(ValueError):
        compare.comparison_view(smooth_signals, protocol)


def test_evaluate_integrates_linear_error_in_all_declared_windows():
    manifest = read(CASE / "manifest.json")
    time = [0., .02, .4, 1.]
    slopes = {"angle_unwrapped": .0001, "frequency": .002, "q_axis_voltage": .1}
    candidate = SimulationResult("SYNTHETIC linear errors", "analytic", .02, 1.,
                                 [{"time": t} | {key: slope*t for key, slope in slopes.items()} for t in time])
    reference = SimulationResult("SYNTHETIC zero baseline", "analytic", .02, 1.,
                                 [{"time": t, "theta_unwrapped": 0., "omega_rad_s": 0., "q_v": 0.} for t in time])
    report = compare.evaluate(candidate, reference, manifest)
    assert report["passed"] is True and len(report["windows"]) == 3
    for window, (start, end) in zip(report["windows"], manifest["windows_seconds"], strict=True):
        for spec in manifest["signals"]:
            metric = window["signals"][spec["candidate"]]
            slope = slopes[spec["candidate"]]
            # Exact continuous integral of (slope*t)^2; no production metric oracle.
            expected = slope * math.sqrt((start*start + start*end + end*end) / 3)
            assert metric["rmse"] == pytest.approx(expected, rel=2e-14, abs=1e-16)
            assert metric["nrmse"] == pytest.approx(expected / spec["scale"], rel=2e-14)
            assert metric["max_abs_error"] == pytest.approx(slope * end)


@pytest.mark.parametrize("field", ["signals", "windows_seconds"])
def test_empty_comparison_contract_cannot_pass(smooth_signals, protocol, field):
    manifest = read(CASE / "manifest.json")
    manifest[field] = []
    view = compare.comparison_view(smooth_signals, protocol)
    with pytest.raises(ValueError):
        compare.evaluate(view, view, manifest)


@pytest.mark.parametrize("failure", [False, True])
def test_capture_forwards_same_object_and_restores_plot_hook(monkeypatch, tmp_path, smooth_signals, failure):
    forwarded, callback = [], []

    def original_plot(result, columns, **kwargs):
        forwarded.append((result, columns, kwargs))

    namespace = {"plot_series": original_plot, "result": smooth_signals, "failure": failure}
    exec("def main():\n"
         "    plot_series(result, ('angle',), title='angle')\n"
         "    if failure: raise RuntimeError('SYNTHETIC main failure')\n"
         "    plot_series(result, ('frequency',), title='frequency')\n"
         "    plot_series(result, ('q_axis_voltage',), title='q')\n", namespace)
    # runpy's returned dictionary need not be main.__globals__.
    monkeypatch.setattr(compare.runpy, "run_path", lambda *args, **kwargs: dict(namespace))

    def before_main():
        callback.append(namespace["plot_series"] is not original_plot)

    if failure:
        with pytest.raises(RuntimeError, match="SYNTHETIC"):
            compare.capture_original11(tmp_path / "SYNTHETIC_inert_example.py", before_main=before_main)
    else:
        assert compare.capture_original11(tmp_path / "SYNTHETIC_inert_example.py", before_main=before_main) is smooth_signals
    assert callback == [True]
    assert namespace["plot_series"] is original_plot
    assert len(forwarded) == (1 if failure else 3)
    assert all(result is smooth_signals for result, _, _ in forwarded)
    assert forwarded[0][1:] == (("angle",), {"title": "angle"})


def test_checked_file_requires_contained_exact_bytes(tmp_path):
    path = tmp_path / "SYNTHETIC.txt"
    path.write_text("synthetic input, never executable\n", encoding="utf-8")
    item = descriptor(tmp_path, path)
    assert compare.checked_file(tmp_path, item) == path
    for change in [{"path": "../outside.txt"}, {"path": str(path.resolve())},
                   {"bytes": True}, {"sha256": "0"*64}]:
        with pytest.raises((ValueError, OSError)):
            compare.checked_file(tmp_path, item | change)


@pytest.mark.parametrize("fault", ["before_main", "different_object"])
def test_capture_rejects_ambiguous_result_and_restores_after_callback_error(monkeypatch, tmp_path, smooth_signals, fault):
    def original_plot(*args, **kwargs):
        return None

    namespace = {"plot_series": original_plot, "result": smooth_signals,
                 "other": copy.deepcopy(smooth_signals)}
    exec("def main():\n"
         "    plot_series(result, ('angle',))\n"
         "    plot_series(other, ('frequency',))\n"
         "    plot_series(result, ('q_axis_voltage',))\n", namespace)
    monkeypatch.setattr(compare.runpy, "run_path", lambda *args, **kwargs: dict(namespace))

    def before_main():
        if fault == "before_main":
            raise RuntimeError("SYNTHETIC callback refusal")

    with pytest.raises(RuntimeError if fault == "before_main" else ValueError):
        compare.capture_original11(tmp_path / "SYNTHETIC_inert_example.py", before_main=before_main)
    assert namespace["plot_series"] is original_plot


def seal_archive(archive, *, refresh_leaves=False):
    """Re-anchor only this explicitly synthetic archive, reaching deeper guards."""
    q, root, paths = archive.qualification, archive.root, archive.paths
    if refresh_leaves:
        q["complete_input_bindings"] = [descriptor(root, path) for path in archive.leaves]
    write_json(paths["q"], q)
    target = descriptor(root, paths["q"])
    post = [{"status": "PLL_FULL_NATIVE_Q_BINDING_AND_SCOPE_REVIEW_PASS", "passed": True,
             "qualification": target, **{key: q[key] for key in
                                         ("scope", "contracts", "accepted_reports", "independent_reviews")}},
            {"status": "INDEPENDENT_ACTUAL_PLL_REFERENCE_QUALIFICATION_PASS", "qualification": target,
             "reference_only": True, "candidate_executed": False, "signal_midpoints_observed": False}]
    for path, value in zip(paths["post"], post, strict=True):
        write_json(path, value | {"synthetic_fixture_only": True})
    normalized = q["normalized_reference"] | {
        "rows": 10001, "columns": ["time", "theta_rad", "theta_unwrapped", "omega_rad_s", "q_v"],
        "units": {"time": "s", "theta_rad": "rad", "theta_unwrapped": "rad", "omega_rad_s": "rad/s", "q_v": "V"},
        "source_run": "coarse", "time_from": "time_s"}
    reviews = [descriptor(root, path) for path in paths["post"]]
    identity = {key: q[key] for key in ("case_id", "reference_id")}
    provenance = identity | {"synthetic_fixture_only": True, "solver": "SYNTHETIC observation fixture",
                             "candidate_executed": False, "complete_receipt": target,
                             "normalized_reference": normalized, "native_runs": q["native_runs"],
                             "normalization_receipt": q["normalization_receipt"], "qualification_reviews": reviews}
    write_json(paths["provenance"], provenance)
    public = identity | {"status": compare.STATUS, "reference_qualified": True, "candidate_executed": False,
                         "existing_11_formally_accepted": False, "scope": q["scope"], "complete_receipt": target,
                         "normalized_reference": normalized, "provenance": descriptor(root, paths["provenance"]),
                         "qualification_reviews": reviews, "complete_input_files": len(q["complete_input_bindings"]),
                         "synthetic_fixture_only": True}
    write_json(archive.case / "qualified_reference_report.json", public)
    for name, path in [("PUBLIC_REPORT_SHA256", archive.case / "qualified_reference_report.json"),
                       ("QUALIFICATION_SHA256", paths["q"]), ("PROTOCOL_SHA256", archive.case / "reference_protocol.json"),
                       ("MANIFEST_SHA256", archive.case / "manifest.json")]:
        archive.monkeypatch.setattr(compare, name, hashlib.sha256(path.read_bytes()).hexdigest())


@pytest.fixture
def archive(tmp_path, monkeypatch):
    case = tmp_path / "validation/cases/pll_dynamic_response"
    case.mkdir(parents=True)
    for name in ("reference_protocol.json", "manifest.json", "acceptance_plan.md"):
        shutil.copy2(CASE / name, case / name)
    protocol = read(case / "reference_protocol.json")
    for item in protocol["source_inputs"]:
        destination = tmp_path / item["path"]
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / item["path"], destination)
    local = tmp_path / "local_reference/SYNTHETIC_PLL"
    local.mkdir(parents=True)
    index = np.arange(10001)
    time = index * .0001
    theta = (index % 200) * (2 * math.pi / 200)
    unwrapped = theta + (index // 200) * (2 * math.pi)
    omega = np.full(10001, 2 * math.pi * 50)
    q_axis = math.sqrt(2) * 230 * np.sin(omega * time - math.pi / 3 - theta)
    observed = SimulationResult("SYNTHETIC observation only", "analytic", .0001, 1.,
                                [{"time": float(t), "angle": float(a), "frequency": float(w), "q_axis_voltage": float(q)}
                                 for t, a, w, q in zip(time, theta, omega, q_axis, strict=True)])
    normalized = local / "normalized.csv"
    np.savetxt(normalized, np.column_stack((time, theta, unwrapped, omega, q_axis)), delimiter=",",
               header="time,theta_rad,theta_unwrapped,omega_rad_s,q_v", comments="", fmt="%.17g")
    # Other raw-state columns are intentionally zero: no PI trajectory is claimed.
    raw = np.zeros((10001, 23))
    for name, values in [("time_s", time), ("theta_rad", theta), ("omega_rad_s", omega), ("q_v", q_axis)]:
        raw[:, protocol["csv_columns"].index(name)] = values
    native_runs, leaves = {}, []
    for schedule in ("coarse", "fine"):
        run = local / schedule
        run.mkdir()
        files = {"terminal": run / "terminal.json", "worker": run / "worker.json",
                 "raw_reference": run / "raw.csv", "solver_time": run / "solver.txt",
                 "raw_mat": run / "SYNTHETIC.txt", "saved_model": run / "inert_model.txt",
                 "source_manifest": run / "inputs.json"}
        write_json(files["terminal"], {"exit_code": 0, "termination_reason": "process_completed",
                                       "owned_all_exited": True, "inputs_unchanged": True,
                                       "monitor_error": None, "cleanup_error": None, "synthetic_fixture_only": True})
        write_json(files["worker"], dict.fromkeys(("prepared", "simulation_requested", "simulation_finished", "completed"), True)
                   | {"synthetic_fixture_only": True})
        np.savetxt(files["raw_reference"], raw, delimiter=",", header=",".join(protocol["csv_columns"]), comments="", fmt="%.17g")
        for name in ("solver_time", "raw_mat", "saved_model", "source_manifest"):
            files[name].write_text("SYNTHETIC metadata leaf, not a model or native output\n", encoding="utf-8")
        native_runs[schedule] = {"run_directory": run.relative_to(tmp_path).as_posix()} | {
            key: descriptor(tmp_path, path) for key, path in files.items()}
        leaves.extend(files.values())
    accepted, independent = {}, []
    for name in ("coarse", "fine", "scheduling_pair"):
        path = local / f"SYNTHETIC_{name}_report.json"
        write_json(path, {"passed": True, "status": "PLL_FULL_SEMANTIC_PASS", "synthetic_fixture_only": True})
        accepted[name] = descriptor(tmp_path, path)
        leaves.append(path)
    for number, status in enumerate(("CLOSED_COARSE_STRUCTURE_AND_LOGGING_AUDIT_PASS",
                                     "CLOSED_FINE_STRUCTURE_AND_NATIVE_SCHEDULE_PAIR_AUDIT_PASS",
                                     "INDEPENDENT_FULL_COARSE_NUMERICAL_PASS",
                                     "INDEPENDENT_FULL_FINE_AND_SAME_SEQUENCE_PAIR_PASS")):
        path = local / f"SYNTHETIC_review_{number}.json"
        write_json(path, {"status": status, "synthetic_fixture_only": True})
        independent.append(descriptor(tmp_path, path))
        leaves.append(path)
    producer = local / "inert_producer.txt"
    producer.write_text("SYNTHETIC producer descriptor only, never executable\n", encoding="utf-8")
    contracts = {key: descriptor(tmp_path, case / name) for key, name in
                 [("master_protocol", "reference_protocol.json"), ("comparison_manifest", "manifest.json"),
                  ("acceptance_plan", "acceptance_plan.md")]}
    normalization = local / "normalization.json"
    normalized_core = descriptor(tmp_path, normalized)
    write_json(normalization, {"candidate_executed": False, "rows": 10001,
                              "status": "EXACT_NATIVE_VALUES_WITH_DECLARED_ANCHORED_ANGLE_VIEW",
                              "source": native_runs["coarse"]["raw_reference"], "protocol": contracts["master_protocol"],
                              "normalized": normalized_core, "producer": descriptor(tmp_path, producer),
                              "synthetic_fixture_only": True})
    manifest = read(case / "manifest.json")
    qualification = {key: manifest[key] for key in ("case_id", "reference_id")} | {
        "schema_version": 1, "status": compare.STATUS, "reference_only": True, "candidate_executed": False,
        "native_semantics_passed": True, "secondary_schedule_invariance_passed": True, "independent_review_passed": True,
        "scope": {"stop_s": 1., "control_step_s": .0001, "signal_rows": 10001, "signal_columns": 23,
                  "solver_steps_s": [.0001, .00005], "solver_rows": [10001, 20001], "signal_midpoints_observed": False},
        "source_inputs": protocol["source_inputs"], "contracts": contracts, "native_runs": native_runs,
        "accepted_reports": accepted, "independent_reviews": independent,
        "normalized_reference": normalized_core, "normalization_receipt": descriptor(tmp_path, normalization),
        "synthetic_fixture_only": True}
    leaves.extend([normalized, producer, normalization, *[case / name for name in
                   ("reference_protocol.json", "manifest.json", "acceptance_plan.md")],
                   *[tmp_path / item["path"] for item in protocol["source_inputs"]]])
    paths = {"q": local / "qualification.json", "raw": local / "coarse/raw.csv", "normalized": normalized,
             "provenance": local / "provenance.json", "post": [local / "post0.json", local / "post1.json"],
             "master": case / "reference_protocol.json", "source": tmp_path / protocol["source_inputs"][0]["path"]}
    fixture = SimpleNamespace(root=tmp_path, case=case, qualification=qualification, paths=paths,
                              leaves=leaves, monkeypatch=monkeypatch, observed=observed)
    seal_archive(fixture, refresh_leaves=True)
    return fixture


def test_synthetic_archive_loads_without_candidate_or_native(archive, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Reference loading must not execute any candidate")
    monkeypatch.setattr(compare.runpy, "run_path", forbidden)
    result, provenance, bindings = compare.load_reference(archive.root, archive.case)
    assert len(result.rows) == 10001
    assert provenance["synthetic_fixture_only"] is True
    assert archive.paths["raw"].relative_to(archive.root).as_posix() in bindings
    assert result.series("theta_unwrapped")[-1] == pytest.approx(2 * math.pi * 50)


@pytest.mark.parametrize("name", ["q", "raw", "master", "source", "provenance"])
def test_missing_or_tampered_archive_bytes_reject(archive, name):
    path = archive.paths[name]
    if name == "provenance":
        path.unlink()
    else:
        path.write_bytes(path.read_bytes() + b"SYNTHETIC mutation\n")
    with pytest.raises((ValueError, OSError)):
        compare.load_reference(archive.root, archive.case)


@pytest.mark.parametrize("fault", ["duplicate", "escape", "scope", "status", "missing_raw_binding"])
def test_reanchored_invalid_qualification_cannot_pass(archive, fault):
    q = archive.qualification
    if fault == "duplicate":
        q["complete_input_bindings"].append(q["complete_input_bindings"][0] | {
            "path": "./" + q["complete_input_bindings"][0]["path"]})
    elif fault == "escape":
        q["complete_input_bindings"][0]["path"] = "../outside.csv"
    elif fault == "scope":
        q["scope"]["signal_midpoints_observed"] = True
    elif fault == "status":
        q["status"] = "SYNTHETIC_UNQUALIFIED"
    else:
        raw = q["native_runs"]["coarse"]["raw_reference"]["path"]
        q["complete_input_bindings"] = [item for item in q["complete_input_bindings"] if item["path"] != raw]
    seal_archive(archive)
    with pytest.raises(ValueError):
        compare.load_reference(archive.root, archive.case)


def test_normalized_angle_cannot_hide_an_added_turn_even_with_new_hashes(archive):
    path = archive.paths["normalized"]
    data = np.loadtxt(path, delimiter=",", skiprows=1)
    data[20, 2] += 2 * math.pi
    np.savetxt(path, data, delimiter=",", header="time,theta_rad,theta_unwrapped,omega_rad_s,q_v", comments="", fmt="%.17g")
    archive.qualification["normalized_reference"] = descriptor(archive.root, path)
    normal_path = archive.root / archive.qualification["normalization_receipt"]["path"]
    normal = read(normal_path)
    normal["normalized"] = archive.qualification["normalized_reference"]
    write_json(normal_path, normal)
    archive.qualification["normalization_receipt"] = descriptor(archive.root, normal_path)
    seal_archive(archive, refresh_leaves=True)
    with pytest.raises(ValueError, match="Normalized export"):
        compare.load_reference(archive.root, archive.case)


@pytest.mark.parametrize("fault", ["missing_reference", "after_load_mutation", "late_mutation"])
def test_main_preserves_fail_and_never_executes_real_example(archive, monkeypatch, fault):
    module = archive.case / "compare.py"
    shutil.copy2(Path(compare.__file__), module)
    for name in ("pyproject.toml", "uv.lock"):
        (archive.root / name).write_text("SYNTHETIC snapshot input only\n", encoding="utf-8")
    monkeypatch.setattr(compare, "__file__", str(module))
    monkeypatch.setattr(compare.subprocess, "check_output", lambda *args, **kwargs: "SYNTHETIC Git metadata\n")
    attempted = []

    def inert_capture(example, *, before_main=None):
        attempted.append(example)
        if before_main is not None:
            before_main()
        archive.paths["source"].write_bytes(archive.paths["source"].read_bytes() + b"# SYNTHETIC late mutation\n")
        return archive.observed

    monkeypatch.setattr(compare, "capture_original11", inert_capture)
    if fault == "missing_reference":
        archive.paths["q"].unlink()
    elif fault == "after_load_mutation":
        original_load = compare.load_reference

        def changed_after_load(*args):
            loaded = original_load(*args)
            path = archive.paths["source"]
            path.write_bytes(path.read_bytes() + b"# SYNTHETIC change between admission and snapshot\n")
            return loaded

        monkeypatch.setattr(compare, "load_reference", changed_after_load)
    expected_error = {"missing_reference": ValueError, "after_load_mutation": RuntimeError, "late_mutation": SystemExit}[fault]
    with pytest.raises(expected_error):
        compare.main()
    reports = list((archive.root / "local_reference/pll_dynamic_response/comparison_results").glob("*/report.json"))
    assert len(reports) == 1
    report = read(reports[0])
    assert report["passed"] is False
    assert report["candidate_executed"] is (fault == "late_mutation")
    assert bool(attempted) is (fault == "late_mutation")
    if fault == "late_mutation":
        assert report["input_integrity_errors"]
        assert len(report["windows"]) == 3
    elif fault == "after_load_mutation":
        assert "before snapshot" in report["evaluation_error"]
