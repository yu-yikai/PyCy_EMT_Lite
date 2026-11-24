"""Compare continuous waveforms on a declared window without fitting a time shift.

Linear interpolation is used only inside the two recorded time ranges. Metrics
integrate the piecewise linear signals on their combined knots, so nonuniform
reference sampling does not give dense regions disproportionate weight.
Switching discontinuities must be excluded or handled by case-specific code.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from pycy_emt_lite.analysis.metrics import SeriesProvider


@dataclass(frozen=True)
class SignalSpec:
    """Physical mapping and limits fixed before running a candidate example.

    `scale` is an explicit engineering base in the same units as the signal,
    never a fitted amplitude or a peak-to-peak range measured after simulation.
    """

    candidate: str
    reference: str
    unit: str
    scale: float
    max_nrmse: float
    max_abs_error: float

    def __post_init__(self) -> None:
        for name in ("candidate", "reference", "unit"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be a nonempty string")
        for name in ("scale", "max_nrmse", "max_abs_error"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError(f"{name} must be finite")
            if value < 0 or (name == "scale" and value == 0):
                raise ValueError(f"{name} must be positive (limits may be zero)")


def _series(result: SeriesProvider, column: str) -> tuple[np.ndarray, np.ndarray]:
    time = np.asarray(result.series("time"), dtype=float)
    values = np.asarray(result.series(column), dtype=float)
    if time.ndim != 1 or values.ndim != 1 or time.size != values.size or time.size < 2:
        raise ValueError(f"{column}: need at least two equally sized 1-D time/signal samples")
    if not np.all(np.isfinite(time)) or not np.all(np.isfinite(values)):
        raise ValueError(f"{column}: time and values must be finite")
    if np.any(np.diff(time) <= 0):
        raise ValueError(f"{column}: time must be strictly increasing")
    return time, values


def aligned_signal(
    candidate: SeriesProvider, reference: SeriesProvider, spec: SignalSpec,
    start: float, end: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return combined knots; no extrapolation, rescaling or time shifting."""
    if not math.isfinite(start) or not math.isfinite(end) or end <= start:
        raise ValueError("window must have finite boundaries and positive duration")
    ct, cv = _series(candidate, spec.candidate)
    rt, rv = _series(reference, spec.reference)
    if start < max(ct[0], rt[0]) or end > min(ct[-1], rt[-1]):
        raise ValueError("window requires extrapolation outside recorded data")
    for result in (candidate, reference):
        # The sample interval ending at an event contains a discontinuity even
        # when its earlier sample lies before the requested window.
        times = np.asarray(result.series("time"), dtype=float)
        for record in getattr(result, "event_log", ()):
            event = float(record["time"])
            intervals = (times[:-1] < event) & (event <= times[1:])
            overlaps = (times[:-1] < end) & (times[1:] > start)
            if np.any(intervals & overlaps):
                raise ValueError("continuous comparison window crosses an event interval")
    knots = np.unique(np.concatenate(([start, end], ct[(ct > start) & (ct < end)], rt[(rt > start) & (rt < end)])))
    return knots, np.interp(knots, ct, cv), np.interp(knots, rt, rv)


def _mean(time: np.ndarray, values: np.ndarray) -> float:
    weights = np.diff(time) / (time[-1] - time[0])
    return float(np.sum(weights * (values[:-1] + values[1:]) / 2))


def _rms(time: np.ndarray, values: np.ndarray) -> float:
    scale = float(np.max(np.abs(values))) or 1.0
    a, b = values[:-1] / scale, values[1:] / scale
    weights = np.diff(time) / (time[-1] - time[0])
    return float(np.sqrt(np.sum(weights * (a * a + a * b + b * b) / 3))) * scale


def compare_signals(
    candidate: SeriesProvider, reference: SeriesProvider, specs: list[SignalSpec],
    *, start: float, end: float,
) -> dict:
    """Calculate a JSON-ready report. Both absolute and normalized limits apply."""
    if not specs or len({spec.candidate for spec in specs}) != len(specs):
        raise ValueError("signal specifications must be nonempty and candidate names unique")
    signals = {}
    for spec in specs:
        time, actual, expected = aligned_signal(candidate, reference, spec, start, end)
        error = actual - expected
        rmse = _rms(time, error)
        maximum = float(np.max(np.abs(error)))
        nrmse = rmse / spec.scale
        metrics = {"rmse": rmse, "nrmse": nrmse, "max_abs_error": maximum,
                   "candidate_mean": _mean(time, actual), "reference_mean": _mean(time, expected),
                   "candidate_rms": _rms(time, actual), "reference_rms": _rms(time, expected)}
        if not all(math.isfinite(value) for value in metrics.values()):
            raise ValueError("comparison arithmetic overflowed; check physical scales")
        signals[spec.candidate] = {"reference": spec.reference, "unit": spec.unit,
                                  "scale": spec.scale, **metrics,
                                  "limits": {"max_nrmse": spec.max_nrmse, "max_abs_error": spec.max_abs_error},
                                  "passed": nrmse <= spec.max_nrmse and maximum <= spec.max_abs_error}
    return {"window_seconds": [start, end], "alignment": "absolute_time_linear_interpolation",
            "passed": all(item["passed"] for item in signals.values()), "signals": signals}
