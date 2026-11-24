"""Analytic quadrature and safety checks; no candidate or native simulation."""

import hashlib
import json
from fractions import Fraction

import numpy as np
import pytest

from pycy_emt_lite.io.results import SimulationResult
from validation.cases.synchronous_buck import compare
from validation.cases.synchronous_buck.quadrature import cycle_means
from validation.common.comparison import SignalSpec, compare_signals

PHYSICAL = {"switch_on_resistance_ohm": .1, "each_snubber_resistance_ohm": 100000.,
            "inductor_parallel_resistance_ohm": 10000., "dc_voltage_v": 30.}
SETTINGS = {"start_s": 0., "end_s": 2., "period_s": 1., "cycles": 2}


def exact_source_primitive(time, upper, lower):
    """Independent Fraction integral for iL=1+3t and UC=5+2t."""
    gu, gl = 10 * upper + Fraction(1, 100000), 10 * lower + Fraction(1, 100000)
    gp = Fraction(1, 10000)
    slope = gu / (gu + gl + gp) * (3 - 2 * gp)
    intercept = gu / (gu + gl + gp) * (1 - 5 * gp + 30 * (gl + gp))
    return slope * time**2 / 2 + intercept * time


def test_nonuniform_knots_and_mode_sided_source_have_exact_cycle_integrals():
    time = np.array([0., .25, 1.25, 2.])
    actual = cycle_means(time, 5 + 2 * time, 1 + 3 * time,
                         np.array([.1, .3, .6, .9]), np.array([0., 1., 0., 1.]),
                         np.array([0., 0., 1., 0.]), PHYSICAL, SETTINGS)
    quarter = Fraction(1, 4)
    first = (exact_source_primitive(quarter, 0, 0) - exact_source_primitive(0, 0, 0)
             + exact_source_primitive(1, 1, 0) - exact_source_primitive(quarter, 1, 0))
    second = (exact_source_primitive(5 * quarter, 1, 0) - exact_source_primitive(1, 1, 0)
              + exact_source_primitive(2, 0, 1) - exact_source_primitive(5 * quarter, 0, 1))
    expected = np.array([[6., 2.5, .25, float(first)], [8., 5.5, .525, float(second)]])
    assert actual == pytest.approx(expected, abs=2e-14)


def test_final_duty_and_gate_row_have_no_extension_and_jump_is_not_a_ramp():
    time = np.array([0., 1., 2.])
    upper, lower = np.array([0., 1., 0.]), np.array([0., 0., 1.])
    actual = cycle_means(time, np.full(3, 15.), np.full(3, 4.), np.array([.1, .2, .95]),
                         upper, lower, PHYSICAL, SETTINGS)
    off = float(Fraction(1, 100000) / Fraction(12, 100000) *
                (4 - Fraction(15, 10000) + 30 * Fraction(11, 100000)))
    high = float(Fraction(1000001, 100000) / Fraction(1000012, 100000) *
                 (4 - Fraction(15, 10000) + 30 * Fraction(11, 100000)))
    assert actual[:, 2] == pytest.approx([.1, .2])
    assert actual[:, 3] == pytest.approx([off, high], abs=2e-14)
    assert abs((off + high) / 2 - actual[0, 3]) > 1


def test_period_boundary_neighbors_keep_their_own_held_interval():
    time = np.array([0., np.nextafter(1., 0.), 1., np.nextafter(1., 2.), 2.])
    actual = cycle_means(time, np.ones(5), np.ones(5), np.array([.1, .2, .3, .4, .9]),
                         np.ones(5), np.zeros(5), PHYSICAL, SETTINGS)
    assert actual[:, 2] == pytest.approx([.1, .4], abs=1e-15)


@pytest.mark.parametrize("time", [[0., 1., 1.], [0., float("nan"), 2.], [0., 1., 1.9]])
def test_incomplete_or_invalid_axes_are_rejected(time):
    with pytest.raises(ValueError):
        cycle_means(time, np.ones(3), np.ones(3), np.ones(3), np.ones(3), np.zeros(3), PHYSICAL, SETTINGS)


def test_nonbinary_gate_is_rejected():
    with pytest.raises(ValueError, match="binary"):
        cycle_means([0., 1., 2.], np.ones(3), np.ones(3), np.ones(3), [0., .5, 1.], np.zeros(3), PHYSICAL, SETTINGS)


def test_only_storage_view_can_cross_events_and_original_log_remains_intact():
    rows = [{"time": float(index), "v:out": float(index), "i:L": 2. * index, "i:Vdc": float(index > 0)}
            for index in range(3)]
    events = [{"time": 1., "type": "load_current_step", "target": "Ipulse", "before": 0., "after": 2.}]
    original = SimulationResult("synthetic", "test", 1., 2., rows, events)
    reference = compare.ContinuousStorage(np.arange(3.), np.arange(3.), 2 * np.arange(3.), candidate=False)
    spec = [SignalSpec("v:out", "vout", "V", 15., .005, .3)]
    with pytest.raises(ValueError, match="event interval"):
        compare_signals(original, reference, spec, start=0., end=2.)
    view = compare.ContinuousStorage(original.series("time"), original.series("v:out"), original.series("i:L"), candidate=True)
    assert compare_signals(view, reference, spec, start=0., end=2.)["passed"]
    with pytest.raises(KeyError):
        view.series("i:Vdc")
    assert original.event_log is events and original.rows is rows and len(events) == 1


def test_modified_reference_audit_hash_is_rejected_before_array_or_candidate_use(tmp_path, monkeypatch):
    case = tmp_path / "case"
    case.mkdir()
    local = tmp_path / "local_reference"
    local.mkdir()
    (case / "manifest.json").write_text(json.dumps({"case_id": "synthetic_buck", "reference_id": "synthetic_native",
                                                   "reference_platform": "synthetic"}), encoding="utf-8")
    clarification = b"pre-run quadrature\n"
    (case / "candidate_quadrature_addendum.md").write_bytes(clarification)
    for name in ["report.json", "arrays.npz", "means.csv"]:
        (local / name).write_bytes(b"unchanged synthetic bytes")
    provenance = {"case_id": "synthetic_buck", "reference_id": "synthetic_native",
                  "reference_stage": "refined", "solver": "ode23tb", "platform": "synthetic",
                  "candidate_quadrature_addendum_lf_sha256": hashlib.sha256(clarification).hexdigest(),
                  "reference_audit_report": "local_reference/report.json", "reference_audit_sha256": "0" * 64,
                  "reference_npz": "local_reference/arrays.npz", "reference_npz_sha256": "0" * 64,
                  "reference_cycle_means": "local_reference/means.csv", "reference_cycle_means_sha256": "0" * 64}
    file = local / "provenance.json"
    file.write_text(json.dumps(provenance), encoding="utf-8")
    monkeypatch.setattr(compare, "ROOT", tmp_path)
    monkeypatch.setattr(compare, "CASE", case)
    with pytest.raises(ValueError, match="Canonical reference hash mismatch: reference_audit_report"):
        compare.load_reference(file)


@pytest.mark.parametrize("key", ["case_id", "reference_id"])
def test_reference_identity_must_match_manifest(tmp_path, monkeypatch, key):
    manifest = {"case_id": "synthetic_buck", "reference_id": "synthetic_native"}
    (tmp_path / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    provenance = manifest | {"reference_stage": "refined", key: "different_identity"}
    file = tmp_path / "provenance.json"
    file.write_text(json.dumps(provenance), encoding="utf-8")
    monkeypatch.setattr(compare, "CASE", tmp_path)
    with pytest.raises(ValueError, match="case/reference identity differs"):
        compare.load_reference(file)


@pytest.mark.parametrize("outside", [False, True])
def test_every_audit_input_is_rechecked_before_native_array_use(tmp_path, monkeypatch, outside):
    repository = tmp_path / "repository"
    case = repository / "case"
    case.mkdir(parents=True)
    local = repository / "local_reference"
    refined = local / "audit/refined"
    refined.mkdir(parents=True)
    identity = {"case_id": "synthetic_buck", "reference_id": "synthetic_native"}
    (case / "manifest.json").write_text(json.dumps(identity | {"reference_platform": "synthetic"}), encoding="utf-8")
    clarification = b"pre-run quadrature\n"
    (case / "candidate_quadrature_addendum.md").write_bytes(clarification)
    native_input = tmp_path / "outside.csv" if outside else repository / "baseline_state.csv"
    frozen_bytes = b"complete original baseline state CSV\n"
    native_input.write_bytes(frozen_bytes if outside else b"changed baseline state CSV\n")
    audit = {"passed": True, "comparison": {"passed": True}, "pair_identity": {"passed": True},
             "runs": {"baseline": {"passed": True}, "refined": {"passed": True}},
             "input_sha256": {str(native_input): hashlib.sha256(frozen_bytes).hexdigest()}}
    audit_file = refined.parent / "report.json"
    audit_file.write_text(json.dumps(audit), encoding="utf-8")
    arrays, means = refined / "raw_and_diagnostics.npz", refined / "cycle_means.csv"
    arrays.write_bytes(b"arrays must not be opened on stale input")
    means.write_bytes(b"means must not be opened on stale input")
    provenance = identity | {"reference_stage": "refined", "solver": "ode23tb", "platform": "synthetic",
                            "candidate_quadrature_addendum_lf_sha256": hashlib.sha256(clarification).hexdigest()}
    for key, path, hash_key in [("reference_audit_report", audit_file, "reference_audit_sha256"),
                                ("reference_npz", arrays, "reference_npz_sha256"),
                                ("reference_cycle_means", means, "reference_cycle_means_sha256")]:
        provenance[key] = str(path.relative_to(repository))
        provenance[hash_key] = hashlib.sha256(path.read_bytes()).hexdigest()
    file = local / "provenance.json"
    file.write_text(json.dumps(provenance), encoding="utf-8")
    monkeypatch.setattr(compare, "ROOT", repository)
    monkeypatch.setattr(compare, "CASE", case)
    original_hash = compare._hash

    def checked_hash(path):
        if outside and path == native_input:
            pytest.fail("Outside-repository audited input must be rejected before reading its bytes")
        return original_hash(path)

    monkeypatch.setattr(compare, "_hash", checked_hash)
    message = "Audited input leaves repository" if outside else "Audited input changed"
    with pytest.raises(ValueError, match=message):
        compare.load_reference(file)
