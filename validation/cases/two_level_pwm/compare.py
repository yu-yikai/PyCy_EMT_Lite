"""Compare unchanged example 12, including fixed-frequency current features."""

from __future__ import annotations

import json
import math
import runpy
from pathlib import Path

import numpy as np

from pycy_emt_lite.analysis import mean_value, rms
from pycy_emt_lite.analysis.metrics import SeriesProvider
from pycy_emt_lite.io.results import SimulationResult
from validation.common.comparison import SignalSpec, aligned_signal
from validation.common.runner import run_comparison


def current_features(
    result: SeriesProvider, column: str, *, start: float, end: float, frequency: float,
) -> dict[str, float]:
    """Project the recorded piecewise linear current onto a fixed sine/cosine.

    The phasor convention is i(t) = sqrt(2)*I_rms*sin(2*pi*f*t + phase).
    Integration is analytic on each linear sample interval, including clipped
    endpoints. No fitted frequency, delay, resampling grid or amplitude is used.
    """
    if (isinstance(frequency, bool) or not math.isfinite(frequency) or frequency <= 0
            or not math.isfinite(start) or not math.isfinite(end) or end <= start):
        raise ValueError("frequency and window must be finite and positive")
    cycles = (end - start) * frequency
    if not math.isclose(cycles, round(cycles), rel_tol=0, abs_tol=1e-10) or cycles < 1:
        raise ValueError("fundamental projection requires a whole number of cycles")
    spec = SignalSpec(column, column, "A", 1.0, 0.0, 0.0)
    time, current, _ = aligned_signal(result, result, spec, start, end)
    step = np.diff(time)
    middle = time[:-1] + step / 2
    z = math.pi * frequency * step
    # Integral of the odd linear part against exp(j*w*t). The small-z
    # expansion avoids cancellation when sin(z) and z*cos(z) nearly agree.
    odd_weight = np.empty_like(z)
    small = np.abs(z) < 1e-3
    odd_weight[small] = z[small] * (1 / 3 - z[small] ** 2 / 30 + z[small] ** 4 / 840)
    odd_weight[~small] = (np.sin(z[~small]) - z[~small] * np.cos(z[~small])) / z[~small] ** 2
    integral = np.sum(
        np.exp(2j * math.pi * frequency * middle) * step
        * ((current[:-1] + current[1:]) / 2 * np.sinc(z / math.pi)
           + 0.5j * np.diff(current) * odd_weight)
    )
    phasor = math.sqrt(2) * complex(integral.imag, integral.real) / (end - start)
    features = {
        "total_rms_ampere": rms(result, column, start_time=start, end_time=end),
        "mean_ampere": mean_value(result, column, start_time=start, end_time=end),
        "fundamental_rms_ampere": abs(phasor),
        "fundamental_phase_degrees": math.degrees(math.atan2(phasor.imag, phasor.real)),
    }
    if not all(math.isfinite(value) for value in features.values()):
        raise ValueError("current feature arithmetic must remain finite")
    return features


def compare_features(
    candidate: SeriesProvider, reference: SeriesProvider, manifest: dict, load_resistance: float,
) -> dict:
    """Apply every frozen per-phase criterion and total load dissipation limit.

    Mean resistor dissipation is R*sum(I_rms**2), using the same exact
    piecewise linear square integral as analysis.rms. This excludes converter
    losses and the inductor's instantaneous storage power. Current polarity
    is checked by the signed fundamental phase, since i**2 alone cannot do so.
    """
    if (isinstance(load_resistance, bool) or not math.isfinite(load_resistance)
            or load_resistance <= 0):
        raise ValueError("load resistance must be finite and positive")
    criteria = manifest["feature_criteria"]
    start, end = criteria["window_seconds"]
    frequency = criteria["fundamental_hz"]
    phases = {}
    for mapping in manifest["signals"]:
        name, ref_name = mapping["candidate"], mapping["reference"]
        if name in phases:
            raise ValueError("feature phase mappings must be unique")
        actual = current_features(candidate, name, start=start, end=end, frequency=frequency)
        expected = current_features(reference, ref_name, start=start, end=end, frequency=frequency)
        if expected["total_rms_ampere"] <= 0 or expected["fundamental_rms_ampere"] <= 0:
            raise ValueError("reference current must have positive RMS and fundamental amplitude")
        errors = {
            "relative_rms_error": abs(actual["total_rms_ampere"] / expected["total_rms_ampere"] - 1),
            "relative_fundamental_rms_error": abs(
                actual["fundamental_rms_ampere"] / expected["fundamental_rms_ampere"] - 1
            ),
            "fundamental_phase_error_degrees": abs(
                (actual["fundamental_phase_degrees"] - expected["fundamental_phase_degrees"] + 180) % 360 - 180
            ),
        }
        limits = {
            "relative_rms_error": criteria["max_relative_rms_error"],
            "relative_fundamental_rms_error": criteria["max_relative_fundamental_rms_error"],
            "fundamental_phase_error_degrees": criteria["max_fundamental_phase_error_degrees"],
        }
        for limit in limits.values():
            if isinstance(limit, bool) or not math.isfinite(limit) or limit < 0:
                raise ValueError("feature limits must be finite and nonnegative")
        phases[name] = {
            "reference": ref_name, "candidate_features": actual, "reference_features": expected,
            **errors, "limits": limits, "passed": all(errors[key] <= limits[key] for key in limits),
        }
    if not phases:
        raise ValueError("at least one current phase is required")
    actual_power = load_resistance * sum(x["candidate_features"]["total_rms_ampere"] ** 2 for x in phases.values())
    expected_power = load_resistance * sum(x["reference_features"]["total_rms_ampere"] ** 2 for x in phases.values())
    power_error = abs(actual_power / expected_power - 1)
    power_limit = criteria["max_relative_load_mean_power_error"]
    if isinstance(power_limit, bool) or not math.isfinite(power_limit) or power_limit < 0:
        raise ValueError("power limit must be finite and nonnegative")
    if not all(math.isfinite(value) for value in (actual_power, expected_power, power_error)):
        raise ValueError("load power arithmetic must remain finite")
    power = {
        "candidate_watt": actual_power, "reference_watt": expected_power,
        "resistance_per_phase_ohm": load_resistance,
        "definition": "R * sum(time-weighted phase-current RMS squared); resistor absorption only",
        "relative_error": power_error, "max_relative_error": power_limit,
        "positive_absorption": actual_power > 0 and expected_power > 0,
        "passed": actual_power > 0 and expected_power > 0 and power_error <= power_limit,
    }
    return {
        "window_seconds": [start, end], "fundamental_hz": frequency,
        "fundamental_cycles": (end - start) * frequency,
        "projection": "exact piecewise-linear integral against fixed-frequency sin/cos at absolute time",
        "phase_convention": "i(t) = sqrt(2)*I_rms*sin(2*pi*f*t + phase); wrapped phase difference",
        "time_shift_seconds": 0, "amplitude_fitting": False,
        "phases": phases, "load_mean_power": power,
        "passed": all(phase["passed"] for phase in phases.values()) and power["passed"],
    }


def add_feature_report(
    report: dict, candidate: SeriesProvider, reference: SeriesProvider, manifest: dict, load_resistance: float,
) -> dict:
    """Make overall acceptance require both waveform and feature results."""
    report["waveform_passed"] = report["passed"]
    report["passed"] = False  # A failed feature calculation must never leave a waveform-only pass.
    try:
        report["features"] = compare_features(candidate, reference, manifest, load_resistance)
    except Exception as exc:
        report["feature_evaluation_error"] = f"{type(exc).__name__}: {exc}"
        raise
    report["passed"] = report["waveform_passed"] and report["features"]["passed"]
    return report


def main() -> None:
    directory = Path(__file__).resolve().parent
    root = directory.parents[2]
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    parameters = json.loads((directory / "parameters.json").read_text(encoding="utf-8"))
    example = root / manifest["example"]
    case = runpy.run_path(str(example))["define_case"]()
    report = run_comparison(case, directory / "manifest.json", example)
    destination = root / report["artifacts"]["directory"]
    try:
        candidate = SimulationResult.from_csv(destination / "pycy.csv", method=report["candidate_method"])
        reference = SimulationResult.from_csv(destination / "inputs/reference.csv", method=report["reference_provenance"]["solver"])
        add_feature_report(report, candidate, reference, manifest, parameters["load_resistance_ohm"])
    except Exception as exc:
        report.setdefault("waveform_passed", report["passed"])
        report["passed"] = False
        report["feature_evaluation_error"] = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        (destination / "report.json").write_text(
            json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8",
        )
    print(f"two_level_pwm: waveform={report['waveform_passed']}; features={report['features']['passed']}; "
          f"overall={'PASS' if report['passed'] else 'FAIL'}; {destination / 'report.json'}")
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
