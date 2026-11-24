"""同步 Buck 的原生参考规范化；不运行电路或构造候选。

原始重复时刻和每个采样的诊断都保留。只有积分派生视图取同刻最后值。
源流由原生状态、duty 和已核拓扑分段重建，不冒充直接 gate/Isrc 日志。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

PERIOD = 20e-6
STOP = .01
CYCLES = 500
GP = 1e-4  # 电感并联 10kΩ；两管各自另有 100kΩ snubber。
CURRENT_BOUND, VOLTAGE_BOUND = 7.99, 40.0
DI_BOUND, DU_BOUND = 70800.0, 939261.2121212123


@dataclass(frozen=True, slots=True)
class NativeTrace:
    """同一原生轴上的实际状态和 Scope 输出；xlag 尚未乘 1e6。

    接受非递减原始轴，包括事件左右侧的重复时刻；拒绝回退、非有限值和缺列。
    数组复制并设为只读，调用者的原始数据不会被规范化修改。
    """

    time: np.ndarray
    iL: np.ndarray
    uC: np.ndarray
    xint: np.ndarray
    xlag: np.ndarray
    duty: np.ndarray
    source_current: np.ndarray

    def __post_init__(self) -> None:
        for name in self.__dataclass_fields__:
            original = getattr(self, name)
            if np.iscomplexobj(original):
                raise ValueError(f"{name} must be real and finite")
            values = np.array(original, dtype=float, copy=True)
            if values.ndim != 1 or not np.all(np.isfinite(values)):
                raise ValueError(f"{name} must be a finite one-dimensional array")
            values.setflags(write=False)
            object.__setattr__(self, name, values)
        if len(self.time) < 2 or any(len(getattr(self, name)) != len(self.time) for name in self.__dataclass_fields__):
            raise ValueError("native columns must have the same length, at least two")
        if np.any(np.diff(self.time) < 0):
            raise ValueError("native time must be nondecreasing; never sort a failed trace")


def carrier01(time: np.ndarray | float) -> np.ndarray:
    """已核的 +5us/50kHz 三角载波，范围 [0,1]。"""
    phase = np.remainder(np.asarray(time) + 5e-6, PERIOD) / PERIOD
    return np.where(phase < .5, 2 * phase, 2 * (1 - phase))


def _source(iL: np.ndarray | float, uC: np.ndarray | float, high: bool | None) -> np.ndarray:
    if high is None:  # powergui 初始四器件阻断，不能套 t>0 互补电导之和。
        upper = lower = 1e-5
    else:
        upper, lower = (10.00001, 1e-5) if high else (1e-5, 10.00001)
    total = upper + lower + GP
    return upper / total * (np.asarray(iL) - GP * np.asarray(uC) + 30 * (lower + GP))


def _root_diagnostics(roots: np.ndarray, time: np.ndarray, trace: NativeTrace, last: np.ndarray,
                      grid: np.ndarray, high: np.ndarray, epsilon: float) -> tuple[list[dict[str, Any]], np.ndarray]:
    """条件根预算；锚点状态/导数相容性另作假设，epsilon 不由 AbsTol 推导。"""
    radius = 1e-10
    curvature = .5 * (DU_BOUND + 80e6) / 1e-6 + 200 * 80e6
    rows: list[dict[str, Any]] = []
    charges = np.zeros(CYCLES)
    il_values, uc_values = trace.iL[last], trace.uC[last]
    for root in roots:
        k = min(int(np.searchsorted(time, root)), len(time) - 1)
        if k and abs(time[k - 1] - root) < abs(time[k] - root):
            k -= 1
        raw_index = int(last[k])
        ef = 1e6 * trace.xlag[raw_index]
        raw_duty = .5 * ef + 200 * trace.xint[raw_index]
        raw_slope = .5 * (15 - trace.uC[raw_index] - ef) / 1e-6 + 200 * ef
        duty_slope = raw_slope if .01 < raw_duty < .95 else 0.0
        phase = float(np.remainder(time[k] + 5e-6, PERIOD) / PERIOD)
        carrier_slope = 1e5 if phase < .5 else -1e5
        speed = abs(duty_slope - carrier_slope) - curvature * radius
        clip_safety = min(abs(raw_duty - .01), abs(raw_duty - .95)) - abs(raw_slope) * radius - .5 * curvature * radius**2
        gap = float(trace.duty[raw_index] - carrier01(time[k]))
        distance = abs(float(root - time[k]))
        anchor_to_true = (abs(gap) + epsilon) / speed if speed > 0 else float("inf")
        passed = speed > 0 and clip_safety > 0 and distance < radius and anchor_to_true < radius
        error = distance + anchor_to_true
        period = min(int(root / PERIOD), CYCLES - 1)
        if passed:
            charges[period] += 8 * error
        else:
            charges[period] = float("inf")
        p = int(np.searchsorted(grid, root))
        il, uc = np.interp(root, time, il_values), np.interp(root, time, uc_values)
        rows.append({"time": float(root), "anchor_raw_index": raw_index, "anchor_time": float(time[k]),
                     "anchor_gap": gap, "distance_to_anchor": distance, "minimum_local_speed": float(speed),
                     "clipping_branch_safety": float(clip_safety),
                     "conditional_time_error": float(error) if passed else None,
                     "bound_available": bool(passed), "local_conditions_passed": bool(passed), "period_index": period,
                     "source_before": float(_source(il, uc, bool(high[p - 1]))) if p else None,
                     "source_after": float(_source(il, uc, bool(high[p]))) if p < len(high) else None})
    return rows, charges


def normalize_reference(trace: NativeTrace, *, duty_error_assumption: float) -> dict[str, Any]:
    """核对整窗原生参考，返回数组、全点诊断及条件证书，不宣称商业验证通过。

    必须显式提供锚点 duty 误差假设；还须假设状态误差不破坏局部导数界。
    两者不是 solver 全局精度证明。结构输入无效时
    拒绝；物理/坐标核验失败则保留诊断及 false，不删坏点或强行挑选模式。
    cycle_means 的列依次是 UC、iL、duty、重建 Isrc，覆盖全部500周期。
    """
    if not np.isfinite(duty_error_assumption) or duty_error_assumption < 0:
        raise ValueError("duty_error_assumption must be explicit, finite and nonnegative")
    last = np.r_[np.flatnonzero(np.diff(trace.time) > 0), len(trace.time) - 1]
    time = trace.time[last]
    if len(time) < 2 or time[0] != 0 or time[-1] != STOP or np.any(np.diff(time) <= 0):
        raise ValueError("reference must cover exactly 0..0.01s on a strictly increasing derived axis")
    if np.any((trace.duty < .01) | (trace.duty > .95)):
        raise ValueError("native duty must remain in the declared [.01,.95] limits")

    # 每个原始点独立核对，包括重复时间和开关根两侧。
    raw_control = .5e6 * trace.xlag + 200 * trace.xint
    pi_error = np.clip(raw_control, .01, .95) - trace.duty
    unsaturated = (trace.duty > .01) & (trace.duty < .95)
    unclipped_error = raw_control[unsaturated] - trace.duty[unsaturated]
    residuals = np.column_stack([abs(_source(trace.iL, trace.uC, mode) - trace.source_current)
                                for mode in [None, True, False]])
    matches = residuals[:, 1:] <= 1e-8
    unique = matches.sum(axis=1) == 1
    mode = np.where(unique, np.where(matches[:, 0], 1, 2), -1)
    mode[trace.time == 0] = 0
    gap = trace.duty - carrier01(trace.time)
    near = abs(gap) <= 1e-9
    post = trace.time > 0
    mismatch = post & unique & ((gap >= 0) != matches[:, 0])
    derived_mode = mode[last]
    switches = np.flatnonzero((derived_mode[1:-1] != derived_mode[2:])
                             & (derived_mode[1:-1] > 0) & (derived_mode[2:] > 0)) + 1

    base = np.unique(np.r_[time, np.arange(5e-6, STOP, 10e-6), np.arange(CYCLES + 1) * PERIOD])
    base = base[(base >= 0) & (base <= STOP)]
    base_gap = np.interp(base, time, trace.duty[last]) - carrier01(base)
    if np.any((base_gap[:-1] == 0) & (base_gap[1:] == 0)):
        raise ValueError("finite carrier-equality interval has no isolated-root certificate")
    crossing = base_gap[:-1] * base_gap[1:] < 0
    left = np.flatnonzero(crossing)
    roots = np.unique(np.r_[base[base_gap == 0], base[left] + np.diff(base)[left]
                           * (-base_gap[left]) / (base_gap[left + 1] - base_gap[left])])
    grid = np.unique(np.r_[base, roots])
    midpoint = .5 * (grid[:-1] + grid[1:])
    high = np.interp(midpoint, time, trace.duty[last]) >= carrier01(midpoint)
    il, uc, duty = [np.interp(grid, time, values[last]) for values in [trace.iL, trace.uC, trace.duty]]
    source_left = np.where(high, _source(il[:-1], uc[:-1], True), _source(il[:-1], uc[:-1], False))
    source_right = np.where(high, _source(il[1:], uc[1:], True), _source(il[1:], uc[1:], False))
    averages = np.column_stack([.5 * (uc[:-1] + uc[1:]), .5 * (il[:-1] + il[1:]),
                               .5 * (duty[:-1] + duty[1:]), .5 * (source_left + source_right)])
    period_index = np.minimum((midpoint / PERIOD).astype(int), CYCLES - 1)
    means = np.column_stack([np.bincount(period_index, weights=np.diff(grid) * averages[:, j] / PERIOD,
                                        minlength=CYCLES) for j in range(4)])
    root_rows, charges = _root_diagnostics(roots, time, trace, last, grid, high, duty_error_assumption)

    current_margin = CURRENT_BOUND - (abs(trace.iL[last][:-1]) + np.diff(time) * DI_BOUND)
    voltage_margin = VOLTAGE_BOUND - (abs(trace.uC[last][:-1]) + np.diff(time) * DU_BOUND)
    initial_down = 1 / (1e-5 + 1 / 3.75)
    initial_uc = 30 * initial_down / (1e5 + initial_down)
    initial_error = np.array([trace.iL[0] - initial_uc / 3.75, trace.uC[0] - initial_uc,
                              trace.xint[0], trace.xlag[0]])
    duplicates = np.diff(trace.time) == 0
    storage_continuous = (np.all(abs(np.diff(trace.iL)[duplicates]) <= 1e-12)
                          and np.all(abs(np.diff(trace.uC)[duplicates]) <= 1e-12))
    pi_max = float(max(abs(pi_error)))
    unsaturated_max = float(max(abs(unclipped_error))) if len(unclipped_error) else 0.0
    checks = {"pi_mapping": pi_max <= 1e-10 and unsaturated_max <= 1e-10,
              "all_post_initial_modes_unique": bool(np.all(unique[post])),
              "initial_source_blocked_mode": bool(np.all(residuals[~post, 0] <= 1e-8)),
              "initial_states": bool(np.all(abs(initial_error) <= 1e-12)),
              "clear_carrier_modes": not bool(np.any(mismatch & ~near)),
              "duplicate_storage_continuity": bool(storage_continuous),
              "domain_bridge_arithmetic": bool(min(current_margin) > 0 and min(voltage_margin) > 0
                                                and max(abs(trace.iL)) < CURRENT_BOUND
                                                and max(abs(trace.uC)) < VOLTAGE_BOUND),
              "root_local_conditions": all(row["local_conditions_passed"] for row in root_rows)}
    return {"time": time, "last_raw_indices": last, "cycle_means": means,
            "cycle_mean_columns": ["uC", "iL", "duty", "reconstructed_source_current"],
            "raw_diagnostics": {"time": trace.time, "mode": mode, "source_mode_residuals": residuals,
                                "source_residual_columns": ["both_off_initial", "high_on", "low_on"],
                                "post_initial_mode_match_count": matches.sum(axis=1),
                                "pi_residual": pi_error, "carrier_gap": gap, "root_near": near,
                                "carrier_mode_mismatch": mismatch},
            "mode_switch_brackets": np.column_stack([time[switches], time[switches + 1]]),
            "roots": root_rows, "checks": checks,
            "summary": {"raw_samples": len(trace.time), "derived_samples": len(time),
                        "duplicates_preserved": len(trace.time) - len(time), "cycles": CYCLES,
                        "pi_max_abs_residual": pi_max, "strict_unsaturated_samples": int(unsaturated.sum()),
                        "unclipped_max_abs_residual": unsaturated_max,
                        "high_on_samples": int(np.sum((mode == 1) & post)),
                        "low_on_samples": int(np.sum((mode == 2) & post)),
                        "unmatched_samples": int(np.sum((matches.sum(axis=1) == 0) & post)),
                        "ambiguous_samples": int(np.sum((matches.sum(axis=1) == 2) & post)),
                        "root_near_samples": int(np.sum(near & post)),
                        "carrier_mismatches_near": int(np.sum(mismatch & near)),
                        "carrier_mismatches_clear": int(np.sum(mismatch & ~near))},
            "domain_certificate": {"current_margins": current_margin, "voltage_margins": voltage_margin,
                                   "assumption": "True native storage-state errors must be below these positive margins; arithmetic is not a global solver error proof"},
            "conditional_root_certificate": {"assumed_abs_duty_error_at_anchor": duty_error_assumption,
                                             "local_radius": 1e-10, "charge_per_cycle": charges,
                                             "bound_available_per_cycle": np.isfinite(charges),
                                             "edge_charge_budget": 2e-8,
                                             "charge_budget_passed": bool(np.all(charges <= 2e-8)),
                                             "assumptions": ["Physical equations and diode-inactivity domain apply",
                                                             "Explicit anchor duty error assumption holds; never inferred from AbsTol",
                                                             "Native uC and filtered-error anchor errors preserve the stated local derivative and clipping bounds; duty error alone does not imply this",
                                                             "No unresolved extra physical roots; both native refinements must be checked"],
                                             "label": "State/duty-derived physical reconstruction; not direct gate/current logging or an unconditional accuracy certificate"}}
