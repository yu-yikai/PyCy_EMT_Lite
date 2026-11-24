"""Reference-loader refusal and retained-error tests; no candidate/native run.

All archives below are synthetic pytest fixtures, never commercial evidence.
"""
import json
import shutil
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from validation.cases.two_level_pwm_pscad import compare

ROOT = Path(__file__).resolve().parents[1]


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def descriptor(root, path):
    return {"path": path.relative_to(root).as_posix(), "bytes": path.stat().st_size,
            "sha256": compare.sha256(path)}


def seal(fixture, *, refresh_leaves=False):
    """Update the synthetic receipt anchor so deeper guards are actually reached."""
    if refresh_leaves:
        fixture.qualification["complete_input_bindings"] = [descriptor(fixture.root, p) for p in fixture.leaves]
    write_json(fixture.receipt, fixture.qualification)
    fixture.public["complete_receipt"] = descriptor(fixture.root, fixture.receipt)
    provenance = compare.read(fixture.paths["provenance"])
    provenance.update(complete_receipt=fixture.public["complete_receipt"],
                      normalized_reference=fixture.qualification["normalized_reference"])
    write_json(fixture.paths["provenance"], provenance)
    fixture.public["provenance"] = descriptor(fixture.root, fixture.paths["provenance"])
    fixture.public["normalized_reference"] = fixture.qualification["normalized_reference"].copy()
    write_json(fixture.case / "qualified_reference_report.json", fixture.public)


@pytest.fixture
def archive(tmp_path):
    case = tmp_path / "validation/cases/two_level_pwm_pscad"
    case.mkdir(parents=True)
    local = tmp_path / "local_reference/two_level_pwm_pscad"
    local.mkdir(parents=True)
    receipt = local / "qualification/receipt.json"
    snapshots = receipt.parent / "input_snapshot/protocol"
    snapshots.mkdir(parents=True)
    for name in ("manifest.json", "parameters.json", "acceptance_plan.md", "reference_protocol.json"):
        shutil.copy2(ROOT / "validation/cases/two_level_pwm_pscad" / name, case / name)
        shutil.copy2(case / name, snapshots / name)
    manifest = compare.read(case / "manifest.json")
    identity = {key: manifest[key] for key in ("case_id", "reference_id")}
    paths = {"raw": local / "synthetic_raw.out", "author": local / "synthetic_author.json",
             "independent": local / "synthetic_independent.json", "normalized": local / "reference.csv",
             "provenance": local / "provenance.json"}
    paths["raw"].write_bytes(b"synthetic leaf for loader tests, not native output\n")
    for name in ("author", "independent"):
        write_json(paths[name], {"synthetic_fixture_only": True})
    data = np.column_stack((np.arange(80003) * 2.5e-6, np.zeros((80003, 3))))
    np.savetxt(paths["normalized"], data, delimiter=",", header="time,i_a,i_b,i_c", comments="", fmt="%.17g")
    write_json(paths["provenance"], identity | {
        "synthetic_fixture_only": True, "solver": "EMTDC_TR", "platform": manifest["reference_platform"]})
    normalized = descriptor(tmp_path, paths["normalized"]) | {
        "rows": 80003, "columns": ["time", "i_a", "i_b", "i_c"], "time_from": "TIME_native_s",
        "units": {"time": "s", "i_a": "A", "i_b": "A", "i_c": "A"}, "source_run": "fine"}
    qualification = identity | {
        "schema": compare.SCHEMA, "status": compare.STATUS,
        "reference_self_refinement_passed": True, "independent_review_passed": True,
        "protocol_sha256": compare.sha256(case / "reference_protocol.json"),
        "scope": {"reference_only": True, "formal_stop_s": .2, "acquisition_stop_s": .200005,
                  "control_hold_s": 5e-6, "electrical_h_s": [5e-6, 2.5e-6], "rows": [40002, 80003],
                  "channels": 60, "shared_input_scope": "exact_same_shared_inputs"},
        "accepted_reports": {name: descriptor(tmp_path, paths[name]) for name in ("author", "independent")},
        "normalized_reference": normalized,
    }
    fixture = SimpleNamespace(root=tmp_path, case=case, receipt=receipt, paths=paths,
                              qualification=qualification, public=identity | {
                                  "status": compare.STATUS, "reference_qualified": True},
                              leaves=[paths[name] for name in ("raw", "author", "independent", "normalized")]
                                     + list(snapshots.iterdir()))
    seal(fixture, refresh_leaves=True)
    return fixture


def test_complete_fixture_loads_without_constructing_or_running_candidate(archive, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("A reference loader must not execute a candidate")
    monkeypatch.setattr(compare.runpy, "run_path", forbidden)
    monkeypatch.setattr(compare, "Simulator", forbidden)
    result, provenance, bindings = compare.load_reference(archive.root, archive.case)
    assert len(result.rows) == 80003 and result.series("time")[-1] > .2
    assert provenance["synthetic_fixture_only"] is True
    assert descriptor(archive.root, archive.paths["raw"])["path"] in bindings


@pytest.mark.parametrize("name", ["receipt", "raw", "normalized", "provenance"])
def test_missing_or_changed_qualified_bytes_reject_before_candidate(archive, name):
    path = archive.receipt if name == "receipt" else archive.paths[name]
    if name == "provenance":
        path.unlink()
    else:
        path.write_bytes(path.read_bytes() + b"changed\n")
    with pytest.raises((ValueError, OSError)):
        compare.load_reference(archive.root, archive.case)


@pytest.mark.parametrize("fault", ["scope", "identity", "duplicate", "escape", "boolean_bytes", "bad_sha", "no_independent"])
def test_inadmissible_receipt_contract_is_rejected(archive, fault):
    q = archive.qualification
    if fault == "scope":
        q["scope"]["shared_input_scope"] = "unreviewed_boundary_differences"
    elif fault == "identity":
        q["reference_id"] = "another_reference"
    elif fault == "duplicate":
        item = q["complete_input_bindings"][0].copy()
        item["path"] = "./" + item["path"]
        q["complete_input_bindings"].append(item)
    elif fault == "escape":
        q["complete_input_bindings"][0]["path"] = "../outside.out"
    elif fault == "boolean_bytes":
        q["complete_input_bindings"][0]["bytes"] = True
    elif fault == "bad_sha":
        q["complete_input_bindings"][0]["sha256"] = "A" * 64
    else:
        q["accepted_reports"].pop("independent")
    seal(archive)
    with pytest.raises(ValueError):
        compare.load_reference(archive.root, archive.case)


@pytest.mark.parametrize("fault", ["scope_boolean", "public_metadata", "receipt", "normalized", "solver", "platform"])
def test_qualified_identity_and_provenance_must_agree(archive, fault):
    if fault == "scope_boolean":
        archive.qualification["scope"]["reference_only"] = 1
        seal(archive)
    elif fault == "public_metadata":
        archive.public["normalized_reference"]["rows"] = 0
    else:
        provenance = compare.read(archive.paths["provenance"])
        if fault == "receipt":
            provenance["complete_receipt"]["sha256"] = "a" * 64
        elif fault == "normalized":
            provenance["normalized_reference"]["rows"] = 0
        else:
            provenance[fault] = "another source"
        write_json(archive.paths["provenance"], provenance)
        archive.public["provenance"] = descriptor(archive.root, archive.paths["provenance"])
    write_json(archive.case / "qualified_reference_report.json", archive.public)
    with pytest.raises(ValueError):
        compare.load_reference(archive.root, archive.case)


@pytest.mark.parametrize(("column", "value"), [(1, np.nan), (2, np.inf), (3, -np.inf)])
def test_all_current_columns_must_be_finite_even_with_matching_hashes(archive, column, value):
    data = np.loadtxt(archive.paths["normalized"], delimiter=",", skiprows=1)
    data[40, column] = value
    np.savetxt(archive.paths["normalized"], data, delimiter=",", header="time,i_a,i_b,i_c", comments="", fmt="%.17g")
    normalized = archive.qualification["normalized_reference"]
    normalized.update(descriptor(archive.root, archive.paths["normalized"]))
    seal(archive, refresh_leaves=True)
    with pytest.raises(ValueError, match="nonfinite current"):
        compare.load_reference(archive.root, archive.case)


@pytest.mark.parametrize("fault", ["snapshot", "run"])
def test_snapshot_or_inert_run_failure_keeps_fail_report(archive, monkeypatch, fault):
    example = archive.root / "examples/12_two_level_pwm_generator.py"
    example.parent.mkdir()
    example.write_text("# inert test input: never executed\n", encoding="utf-8")
    for relative in ("validation/common/comparison.py", "validation/cases/two_level_pwm/compare.py"):
        source = archive.root / relative
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text("# inert snapshot input: never executed\n", encoding="utf-8")
    shutil.copy2(Path(compare.__file__), archive.case / "compare.py")
    protocol = compare.read(archive.case / "reference_protocol.json")
    protocol["candidate_criteria_unchanged"]["example_sha256"] = compare.sha256(example)
    write_json(archive.case / "reference_protocol.json", protocol)
    shutil.copy2(archive.case / "reference_protocol.json", archive.receipt.parent / "input_snapshot/protocol/reference_protocol.json")
    archive.qualification["protocol_sha256"] = compare.sha256(archive.case / "reference_protocol.json")
    seal(archive, refresh_leaves=True)
    monkeypatch.setattr(compare, "__file__", str(archive.case / "compare.py"))
    monkeypatch.setattr(compare.subprocess, "check_output", lambda *args, **kwargs: "inert fixture Git metadata\n")
    case = SimpleNamespace(name="inert", components=(), config=None, events=(), on_step=None)
    monkeypatch.setattr(compare.runpy, "run_path", lambda *args: {"define_case": lambda: case})
    monkeypatch.setattr(compare.Circuit, "from_components", lambda *args: object())
    attempted = []

    class InertFailure:
        def __init__(self, *args, **kwargs):
            pass

        def run(self):
            attempted.append(True)
            raise OSError("intentional inert run refusal; no numerical simulation")

    monkeypatch.setattr(compare, "Simulator", InertFailure)
    if fault == "snapshot":
        def cannot_copy(*args, **kwargs):
            raise OSError("intentional fixture snapshot failure")
        monkeypatch.setattr(compare.shutil, "copy2", cannot_copy)
    with pytest.raises(OSError):
        compare.main()
    reports = list((archive.root / "local_reference/two_level_pwm_pscad/comparison_results").glob("*/report.json"))
    assert len(reports) == 1
    report = compare.read(reports[0])
    assert report["passed"] is False
    assert report["candidate_executed"] is (fault == "run")
    assert bool(attempted) is (fault == "run")
    assert "evaluation_error" in report
    if fault == "snapshot":
        assert report["input_integrity_errors"]
