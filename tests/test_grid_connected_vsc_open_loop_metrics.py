"""Closed-form statistics oracles; no candidate circuit or commercial data.

Affine functions are exactly PWL on every grid. Their polynomial integrals and
six-period Fourier coefficients therefore test statistics without a time-step
approximation. Numerical slack below is a floating-point forward-error budget,
independent of the frozen engineering acceptance thresholds.
"""

import json
import math
from decimal import Decimal, localcontext
from fractions import Fraction
from pathlib import Path

import numpy as np
import pytest

from validation.cases.grid_connected_vsc_open_loop import metrics

PROTOCOL = json.loads((Path(__file__).resolve().parents[1] / "validation/cases/grid_connected_vsc_open_loop"
                       / "reference_protocol.json").read_text(encoding="utf-8"))


def roundoff_bound(segments, magnitude):
    """Conservative gamma bound: at most64 scalar roundings per segment."""
    unit_roundoff = np.finfo(float).eps / 2
    operations = 64 * (segments + 2)
    return operations * unit_roundoff / (1 - operations * unit_roundoff) * magnitude


def affine_integrals(slope, offset, start, end):
    """Exact rational antiderivatives, independent of segment quadrature."""
    integral = slope * (end**2-start**2) / 2 + offset * (end-start)
    square_integral = (slope**2 * (end**3-start**3) / 3
                       + slope*offset * (end**2-start**2) + offset**2 * (end-start))
    return float(integral), float(square_integral)


@pytest.mark.parametrize(("slope", "offset"), [
    (Fraction(7, 3), Fraction(-5, 4)), (Fraction(0), Fraction(-2)), (Fraction(-11, 5), Fraction(3, 7)),
])
def test_affine_pwl_mean_square_and_integral_on_clipped_irregular_grid(slope, offset):
    time = np.array([-.3, .02, .08, .14, .27])
    values = float(slope)*time + float(offset)
    start, end = Fraction(7, 200), Fraction(21, 100)
    clipped_time, clipped_values = metrics.clip(time, values, float(start), float(end))
    integral, square_integral = affine_integrals(slope, offset, start, end)
    duration = float(end-start)
    slack = roundoff_bound(len(time)-1, max(1., np.max(np.abs(values))**2))
    assert clipped_time[0] == float(start) and clipped_time[-1] == float(end)
    assert metrics.mean(clipped_time, clipped_values) == pytest.approx(integral/duration, rel=0, abs=slack)
    assert metrics.square_mean(clipped_time, clipped_values) == pytest.approx(square_integral/duration, rel=0, abs=slack)
    assert metrics.mean(clipped_time, clipped_values)*duration == pytest.approx(integral, rel=0, abs=slack)


def test_affine_difference_uses_both_original_grids_and_window_endpoints():
    a = np.array([0., .07, .16, .23, .3])
    b = np.array([0., .04, .12, .21, .3])
    start, end = Fraction(3, 100), Fraction(27, 100)
    result = metrics.difference(a, 4*a-2, b, -3*b+.5, float(start), float(end))
    _, square_integral = affine_integrals(Fraction(7), Fraction(-5, 2), start, end)
    slack = roundoff_bound(len(a)+len(b), 10.)
    assert result["union_knots"] == 8
    assert result["max_abs"] == pytest.approx(float(abs(7*start-Fraction(5, 2))), rel=0, abs=slack)
    assert result["PWL_RMSE_abs"] == pytest.approx(math.sqrt(square_integral/float(end-start)), rel=0, abs=slack)


def test_pwl_difference_keeps_a_peak_missing_from_the_other_grid():
    result = metrics.difference(np.array([0., .25, 1.]), np.array([0., 2., 0.]),
                                np.array([0., .6, 1.]), np.zeros(3), 0., 1.)
    # Each triangular half contributes peak**2 * width / 3.
    assert result["union_knots"] == 4
    assert result["max_abs"] == 2
    assert result["PWL_RMSE_abs"] == pytest.approx(2/math.sqrt(3), rel=0, abs=roundoff_bound(4, 4.))


def test_six_cycle_ramp_plus_dc_has_closed_form_fixed_60hz_features():
    start, duration, dc, slope = .0137, 6/60, 1.25, 17.
    end = start + duration
    time = start + np.array([-.002, .00001, .004, .011, .029, .06, .087, duration+.007])
    values = dc + slope*(time-start)
    result = metrics.features(time, values, start, end)
    omega, phase = 2*math.pi*60, 2*math.pi*60*start
    sine, cosine = -2*slope*math.cos(phase)/omega, 2*slope*math.sin(phase)/omega
    fundamental = math.sqrt(2)*abs(slope)/omega
    residual = abs(slope)*math.sqrt(duration**2/12-2/omega**2)
    expected = {"mean_A": dc+slope*duration/2,
                "total_RMS_A": math.sqrt(dc**2+dc*slope*duration+slope**2*duration**2/3),
                "fundamental_sine_coefficient_A": sine, "fundamental_cosine_coefficient_A": cosine,
                "fundamental_RMS_A": fundamental, "nonfundamental_RMS_excluding_DC_A": residual}
    # Include phase-argument rounding in the scale; all chosen radicands are positive.
    slack = roundoff_bound(len(time)-1, np.max(np.abs(values)) * (1+omega*np.max(np.abs(time))))
    for key, value in expected.items():
        assert result[key] == pytest.approx(value, rel=0, abs=slack)
    ratio_slack = slack/fundamental + residual*slack/fundamental**2
    assert result["residual_ratio_to_fundamental"] == pytest.approx(residual/fundamental, rel=0, abs=ratio_slack)
    phase_error = (result["fundamental_phase_deg"]-math.degrees(math.atan2(cosine, sine))+180) % 360-180
    assert abs(phase_error) <= 2*slack/fundamental * 180/math.pi
    assert result["fixed_frequency_Hz"] == 60 and result["nonfundamental_is_standard_THD"] is False


def test_zero_fundamental_cannot_qualify_phase_or_residual_ratio():
    time = np.linspace(.1, .2, 13)
    table = {"TIME_native_s": time, **{f"I_{p}_ac_to_bridge_kA": np.zeros_like(time) for p in "abc"}}
    result = metrics._same_step_features(table, table, PROTOCOL)
    for phase in result.values():
        assert phase["candidate"]["fundamental_RMS_A"] == 0
        assert phase["candidate"]["residual_ratio_to_fundamental"] is None
        assert phase["phase_ratio_prerequisite_pass"] is False
        assert phase["hard"]["fundamental_phase_deg"]["passed"] is False
        assert phase["hard"]["residual_ratio_to_fundamental"]["passed"] is False


@pytest.mark.parametrize("collision", ["cross_stream", "window_endpoint", "cycle_endpoint"])
def test_distinct_decimal_time_collisions_make_float_metrics_unavailable(collision):
    if collision == "cross_stream":
        point = Decimal(".125")
    elif collision == "window_endpoint":
        point = Decimal(str(PROTOCOL["windows"][1]["end_s"]))
    else:
        point = Decimal(str(PROTOCOL["steady_integer_cycle_features"]["window_s"][0] + 1/60))
    with localcontext() as context:
        context.prec = 60
        nearby = point + Decimal("1e-40")
    assert point != nearby and float(point) == float(nearby)
    tables = [{"TIME_native_s": [Decimal(0), nearby, Decimal(".2")]}]
    if collision == "cross_stream":
        tables.append({"TIME_native_s": [Decimal(0), point, Decimal(".2")]})
    with pytest.raises(ValueError, match="MAIN_METRIC_UNAVAILABLE"):
        metrics.float_time_injective(tables, PROTOCOL)


def test_metric_arrays_keep_decimal_centers_until_joint_injectivity_check():
    times = [Decimal(0), Decimal(".0125"), Decimal(".2")]
    table = metrics.arrays([{"TIME_native_s": time, "sample": Decimal(1)} for time in times])
    assert table["TIME_native_s"] == times
    assert all(isinstance(time, Decimal) for time in table["TIME_native_s"])
    assert metrics.float_time_injective([table], PROTOCOL)["passed"] is True


def test_comparison_report_preserves_numpy_verdicts_and_rejects_nonfinite_before_write(tmp_path):
    from validation.cases.grid_connected_vsc_open_loop.compare import save_json
    path = tmp_path / "report.json"
    save_json(path, {"passed": np.bool_(False), "rows": np.int64(3), "maximum": np.float64(.25)})
    assert json.loads(path.read_text()) == {"passed": False, "rows": 3, "maximum": .25}
    rejected = tmp_path / "rejected.json"
    with pytest.raises(ValueError):
        save_json(rejected, {"maximum": np.float64(np.inf)})
    assert not rejected.exists()


@pytest.mark.parametrize(("name", "value", "factor"), [
    ("TIME_native_s", .100005, 1), ("TIME_native_s", 0., 1),
    ("V_a_grid_kV", -169.7056274847714, 1000), ("V_a_grid_kV", 0., 1000),
    ("I_dc_absorb_kA", -1.1999999999988e-6, 1000),
])
def test_candidate_ascii_full_place_encloses_actual_binary_value_with_one_si_scaling(name, value, factor):
    from validation.cases.grid_connected_vsc_open_loop.compare import token_word
    word = token_word(value, name)
    with localcontext() as context:
        context.prec = 70
        printed = Decimal(word)
        q = Decimal(1).scaleb(printed.as_tuple().exponent)*factor
        assert q > 0
        assert abs(printed*factor-Decimal.from_float(value)) <= q
    if value == 0:
        assert word == "0.000000000000000e+00"
