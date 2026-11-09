"""解析合成数据测试参考数学；不把本地商业 CSV 用作 oracle。"""

from dataclasses import replace

import numpy as np
import pytest

from validation.cases.synchronous_buck.audit_reference import _check_pair_metadata
from validation.cases.synchronous_buck.normalization import (
    NativeTrace,
    normalize_reference,
)


def analytic_source(iL, uC, high):
    # 独立节点 KCL：先解 mid 电压，再从30V端电阻计算源流。
    upper = 1 / (.1 if high else 1e100) + 1 / 100000
    lower = 1 / (1e100 if high else .1) + 1 / 100000
    mid = (30 * upper + uC / 10000 - iL) / (upper + lower + 1 / 10000)
    return (30 - mid) * upper


def constant_trace(duty=.25, *, time=None, slope=0.0):
    if time is None:
        time = np.linspace(0, .01, 2001)
    iL = 4 + slope * time
    uC = np.full(len(time), 15.0)
    phase = np.remainder(time + 5e-6, 20e-6) / 20e-6
    high = (phase <= duty / 2) | (phase >= 1 - duty / 2)
    current = np.where(high, analytic_source(iL, uC, True), analytic_source(iL, uC, False))
    # t0单独保留四器件阻断，不用互补假设覆盖初始化。
    current[time == 0] = 1e-5 * (30 - (30e-5 + 15e-4 - iL[time == 0]) / 12e-5)
    return NativeTrace(time, iL, uC, np.full(len(time), duty / 200), np.zeros(len(time)),
                       np.full(len(time), duty), current)


def test_constant_state_and_duty_have_exact_500_cycle_averages():
    trace = constant_trace()
    result = normalize_reference(trace, duty_error_assumption=0)
    means = result["cycle_means"]
    expected_source = .25 * analytic_source(4, 15, True) + .75 * analytic_source(4, 15, False)
    assert means.shape == (500, 4)
    assert means[:, :3] == pytest.approx(np.tile([15, 4, .25], (500, 1)), abs=2e-11)
    assert means[:, 3] == pytest.approx(np.full(500, expected_source), abs=2e-11)
    assert result["checks"]["pi_mapping"]
    assert result["summary"]["strict_unsaturated_samples"] == len(trace.time)
    # 稀疏常值fixture没有root锚点，不能凭精确积分伪造误差证书。
    assert not result["checks"]["root_local_conditions"]


def test_affine_state_integral_covers_first_and_last_period_without_phase_shift():
    trace = constant_trace(slope=100)
    actual = normalize_reference(trace, duty_error_assumption=0)["cycle_means"]
    # 每个绝对周期high区间是[T*.625,T*.875]；解析积分仿射源流。
    ah = analytic_source(1, 15, True) - analytic_source(0, 15, True)
    al = analytic_source(1, 15, False) - analytic_source(0, 15, False)
    bh, bl = analytic_source(0, 15, True), analytic_source(0, 15, False)
    period = 20e-6
    for p in [0, 499]:
        start = p * period
        full_i = 4 * period + 100 * (start * period + period**2 / 2)
        on_i = 4 * period * .25 + 100 * (start * period * .25 + period**2 * (.875**2 - .625**2) / 2)
        expected = (al * full_i + bl * period + (ah - al) * on_i + (bh - bl) * .25 * period) / period
        assert actual[p, 1] == pytest.approx(4 + 100 * (start + period / 2), abs=2e-11)
        assert actual[p, 3] == pytest.approx(expected, abs=2e-11)


def test_duplicate_root_sides_remain_in_raw_diagnostics_and_only_last_is_derived():
    root = 12.5e-6
    time = np.sort(np.r_[np.linspace(0, .01, 2001), root, root])
    trace = constant_trace(time=time)
    positions = np.flatnonzero(time == root)
    current = trace.source_current.copy()
    current[positions[0]] = analytic_source(4, 15, False)
    current[positions[-1]] = analytic_source(4, 15, True)
    trace = replace(trace, source_current=current)
    original = trace.source_current.copy()
    result = normalize_reference(trace, duty_error_assumption=0)
    assert len(result["raw_diagnostics"]["time"]) == len(time)
    assert result["raw_diagnostics"]["mode"][positions].tolist() == [2, 1]
    assert result["raw_diagnostics"]["root_near"][positions].all()
    assert positions[0] not in result["last_raw_indices"]
    assert positions[-1] in result["last_raw_indices"]
    assert np.array_equal(trace.source_current, original)
    assert not trace.time.flags.writeable
    row = min(result["roots"], key=lambda r: abs(r["time"] - root))
    assert row["source_before"] == pytest.approx(analytic_source(4, 15, False))
    assert row["source_after"] == pytest.approx(analytic_source(4, 15, True))


def test_bad_pi_coordinate_and_unmatched_source_are_reported_without_dropping_points():
    trace = constant_trace()
    lag, current = trace.xlag.copy(), trace.source_current.copy()
    lag[12], current[13] = 1e-6, -500
    result = normalize_reference(replace(trace, xlag=lag, source_current=current), duty_error_assumption=1e-9)
    assert not result["checks"]["pi_mapping"]
    assert result["summary"]["unclipped_max_abs_residual"] == pytest.approx(.5)
    assert not result["checks"]["all_post_initial_modes_unique"]
    assert result["raw_diagnostics"]["mode"][13] == -1
    assert len(result["raw_diagnostics"]["pi_residual"]) == len(trace.time)
    assert result["conditional_root_certificate"]["assumed_abs_duty_error_at_anchor"] == 1e-9


@pytest.mark.parametrize("voltage", [16.0, 41.0])
def test_duplicate_storage_jump_cannot_disappear_in_last_value_view(voltage):
    root = 12.5e-6
    time = np.sort(np.r_[np.linspace(0, .01, 2001), root, root])
    trace = constant_trace(time=time)
    index = np.flatnonzero(time == root)[0]
    uc, source = trace.uC.copy(), trace.source_current.copy()
    uc[index] = voltage
    source[index] = analytic_source(4, voltage, True)
    result = normalize_reference(replace(trace, uC=uc, source_current=source), duty_error_assumption=0)
    assert result["checks"]["pi_mapping"] and result["checks"]["all_post_initial_modes_unique"]
    assert not result["checks"]["duplicate_storage_continuity"]
    assert result["checks"]["domain_bridge_arithmetic"] == (voltage < 40)
    assert index not in result["last_raw_indices"]
    assert len(result["raw_diagnostics"]["time"]) == len(time)


def test_root_charge_certificate_requires_explicit_error_and_close_transverse_anchors():
    roots = np.r_[12.5e-6 + np.arange(500) * 20e-6, 17.5e-6 + np.arange(500) * 20e-6]
    time = np.unique(np.r_[np.linspace(0, .01, 2001), roots])
    trace = constant_trace(time=time)
    result = normalize_reference(trace, duty_error_assumption=1e-9)
    certificate = result["conditional_root_certificate"]
    assert result["checks"]["root_local_conditions"]
    assert certificate["charge_budget_passed"]
    assert max(certificate["charge_per_cycle"]) < 2e-8
    assert certificate["assumed_abs_duty_error_at_anchor"] == 1e-9
    assert "AbsTol" in " ".join(certificate["assumptions"])
    assert all(r["minimum_local_speed"] > 0 for r in result["roots"])
    # 放大假设会超出局部证书半径；积分结果不变，证书必须拒绝。
    failed = normalize_reference(trace, duty_error_assumption=.001)
    assert not failed["checks"]["root_local_conditions"]
    assert not failed["conditional_root_certificate"]["charge_budget_passed"]
    assert failed["cycle_means"] == pytest.approx(result["cycle_means"])
    with pytest.raises(TypeError, match="duty_error_assumption"):
        normalize_reference(trace)


def test_samples_inside_domain_do_not_certify_a_large_unobserved_interval():
    trace = constant_trace(time=np.array([0, .01]))
    result = normalize_reference(trace, duty_error_assumption=0)
    assert np.max(abs(trace.iL)) < 7.99 and np.max(abs(trace.uC)) < 40
    assert not result["checks"]["domain_bridge_arithmetic"]
    assert min(result["domain_certificate"]["current_margins"]) < 0


@pytest.mark.parametrize("bad", [np.nan, np.inf, -np.inf])
def test_nonfinite_trace_is_rejected(bad):
    trace = constant_trace()
    values = trace.uC.copy()
    values[3] = bad
    with pytest.raises(ValueError, match="finite"):
        replace(trace, uC=values)


def test_backwards_mismatched_and_missing_window_inputs_are_rejected():
    trace = constant_trace()
    with pytest.raises(ValueError, match="same length"):
        replace(trace, duty=trace.duty[:-1])
    time = trace.time.copy()
    time[3] = time[1]
    with pytest.raises(ValueError, match="nondecreasing"):
        replace(trace, time=time)
    for time in [np.linspace(1e-8, .01, 2001), np.linspace(0, .00999, 2001)]:
        with pytest.raises(ValueError, match="cover exactly"):
            normalize_reference(constant_trace(time=time), duty_error_assumption=0)


@pytest.mark.parametrize("epsilon", [-1, np.inf, np.nan])
def test_invalid_error_assumption_is_rejected(epsilon):
    with pytest.raises(ValueError, match="duty_error_assumption"):
        normalize_reference(constant_trace(), duty_error_assumption=epsilon)


def pair_metadata():
    # Only provenance fields: no simulated or commercial waveform fixture.
    return {"solver_protocol": "parameters.json reference_solver (original protocol)",
            "selected_protocol": "acceptance_plan.md", "selected_protocol_sha256": "a" * 64,
            "selected_protocol_lf_sha256": "a" * 64,
            "protocol_snapshots_lf_sha256": {"acceptance_plan.md": "a" * 64, "parameters.json": "c" * 64},
            "matlab_version": "25.1.0.2973910 (R2025a) Update 1"}


@pytest.mark.parametrize("addendum", [False, True])
def test_same_protocol_and_native_version_allow_two_refinement_stages(addendum):
    baseline = pair_metadata()
    if addendum:
        baseline.update(solver_protocol="reference_solver_addendum.json", selected_protocol="reference_solver_addendum.md")
        baseline["protocol_snapshots_lf_sha256"]["reference_solver_addendum.md"] = "a" * 64
    refined = {**baseline, "requested_solver_settings": {"max_step_s": 12.5e-9}}
    baseline["requested_solver_settings"] = {"max_step_s": 25e-9}
    assert _check_pair_metadata(baseline, refined)["passed"]


@pytest.mark.parametrize(("field", "different"), [
    ("solver_protocol", "reference_solver_addendum.json"),
    ("selected_protocol_lf_sha256", "b" * 64),
    ("protocol_snapshots_lf_sha256", {"acceptance_plan.md": "b" * 64, "parameters.json": "c" * 64}),
    ("matlab_version", "25.1.0 (R2025a) Update 2"),
])
def test_mixed_protocol_snapshot_or_native_version_cannot_form_a_refinement_pair(field, different):
    baseline = pair_metadata()
    refined = {**baseline, field: different}
    with pytest.raises(ValueError, match=field):
        _check_pair_metadata(baseline, refined)
