"""Case-specific VSC statistics on original grids; all table values are SI.

Same-step comparison pairs original rows before integrating error samples.
Across steps, continuous signals use both PWL grids; jump PWL is diagnostic.
The formulas are reused from the qualified reference audit, without fitting.
"""
import math
from decimal import Decimal
from itertools import pairwise

import numpy as np

from .physics import names


def require(ok, message):
    if not ok:
        raise ValueError(message)


def arrays(rows):
    """Keep original Decimal TIME centers until the joint conversion gate."""
    require(len(rows) >= 2 and all(set(r) == set(rows[0]) for r in rows), 'Complete equal column inventory required')
    data = {key: np.asarray([float(r[key]) for r in rows]) for key in rows[0]}
    require(all(np.all(np.isfinite(v)) for v in data.values()), 'Finite metric samples required')
    require(np.all(np.diff(data['TIME_native_s']) > 0), 'Metric TIME must strictly increase')
    for key in data:
        if key == 'TIME_native_s' or key.startswith(('applied_g_', 'R_')):
            data[key] = [r[key] for r in rows]
    return data


def float_time_injective(tables, protocol):
    """Reject loss of any distinct original or fixed-boundary Decimal knot."""
    points = {Decimal(str(window[key])) for window in protocol['windows'] for key in ('start_s', 'end_s')}
    spec = protocol['steady_integer_cycle_features']
    points.update(Decimal(str(spec['window_s'][0] + k / 60)) for k in range(spec['grid_cycles'] + 1))
    for table in tables:
        times = table['TIME_native_s']
        require(all(isinstance(t, Decimal) and t.is_finite() for t in times), 'Original Decimal TIME required')
        points.update(times)
    require(len({float(t) for t in points}) == len(points),
            'MAIN_METRIC_UNAVAILABLE: Decimal TIME knots collide in binary64')
    return {'passed': True, 'Decimal_union_points': len(points), 'binary64_conversion_injective': True}


def _float_arrays(table):
    require(set(table) == set(names()), 'Exactly32 named metric columns required')
    data = {key: np.asarray(values, dtype=float) for key, values in table.items()}
    times = data['TIME_native_s']
    require(all(v.ndim == 1 and len(v) == len(times) and np.isfinite(v).all() for v in data.values()),
            'Equal finite metric columns required')
    require(times[0] == 0 and np.all(np.diff(times) > 0), 'Initial zero and increasing TIME required')
    return data


def _admit_pair(left, right, protocol, steps):
    """Clock/input identity uses original Decimal centers before conversion."""
    availability = float_time_injective([left, right], protocol)
    inputs = [name for name in names() if name.startswith(('applied_g_', 'R_'))]
    for table, step in zip((left, right), steps, strict=True):
        count = protocol['raw_rows']['coarse' if step == 5e-6 else 'fine']
        require(set(table) == set(names()) and all(len(v) == count for v in table.values()),
                'Exactly32 full-length named metric columns required')
        time = table['TIME_native_s']
        require(time[0] == 0 and all(b > a for a, b in pairwise(time)),
                'Initial zero and ordered original TIME required')
        h = Decimal(str(step))
        require(all(abs(t - k*h) <= Decimal('2e-12') for k, t in enumerate(time)), 'Original clock exceeds2ps')
        require(all(isinstance(v, Decimal) and v.is_finite() for key in inputs for v in table[key]),
                'Original Decimal gate/R centers required')
        for phase in 'abc':
            upper = table[f'applied_g_{phase}_u']
            lower = table[f'applied_g_{phase}_l']
            require(all(u in (0, 1) and lower_bit == 1-u for u, lower_bit in zip(upper, lower, strict=True)),
                    'Exact complementary gates required')
            for side in 'ul':
                require(all(r == (Decimal('.001') if bit else Decimal('1e9'))
                            for bit, r in zip(table[f'applied_g_{phase}_{side}'], table[f'R_{phase}_{side}_ohm'], strict=True)),
                        'Exact declared gate/R centers required')
        if step == 2.5e-6:
            require(all(table[key][k] == table[key][k-1] for key in inputs for k in range(1, count, 2)),
                    'Fine midpoint gate/R must be held')
    stride = 1 if steps[0] == steps[1] else 2
    require(len(right['TIME_native_s'][::stride]) == len(left['TIME_native_s']), 'Original partners differ')
    require(all(abs(a-b) <= Decimal('4e-12')
                for a, b in zip(left['TIME_native_s'], right['TIME_native_s'][::stride], strict=True)),
            'Paired original clocks exceed4ps')
    require(all(a == b for key in inputs for a, b in zip(left[key], right[key][::stride], strict=True)),
            'Paired original gate/R centers differ')
    return availability


def clip(time, values, start, end):
    """Insert fixed endpoints into an actual grid, without extrapolation."""
    require(time.ndim == values.ndim == 1 and len(time) == len(values) >= 2, 'Metric shape differs')
    require(math.isfinite(start) and math.isfinite(end) and end > start, 'Invalid window')
    require(start >= time[0] and end <= time[-1], 'Metric window requires extrapolation')
    keep = (time > start) & (time < end)
    knots = np.concatenate(([start], time[keep], [end]))
    return knots, np.interp(knots, time, values)


def mean(time, values):
    d = np.diff(time)
    return math.fsum(d * (values[:-1] + values[1:]) / 2) / (time[-1] - time[0])


def square_mean(time, values):
    a, b = values[:-1], values[1:]
    return math.fsum(np.diff(time) * (a * a + a * b + b * b) / 3) / (time[-1] - time[0])


def difference(time_a, value_a, time_b, value_b, start, end):
    """Exact square integral of the difference of the two PWL interpolants."""
    require(start >= max(time_a[0], time_b[0]) and end <= min(time_a[-1], time_b[-1]), 'Pair extrapolation prohibited')
    knots = np.unique(np.concatenate(([start, end], time_a[(time_a > start) & (time_a < end)],
                                     time_b[(time_b > start) & (time_b < end)])))
    error = np.interp(knots, time_a, value_a) - np.interp(knots, time_b, value_b)
    return {'max_abs': float(np.max(np.abs(error))), 'PWL_RMSE_abs': math.sqrt(square_mean(knots, error)),
                'union_knots': len(knots), 'original_nearby_knots_retained': True}


def continuous_gate(metrics, limits):
    scale = limits['engineering_scale']
    result = dict(metrics, engineering_scale=scale,
                  max_abs_over_scale=metrics['max_abs'] / scale,
                  PWL_RMSE_over_scale=metrics['PWL_RMSE_abs'] / scale,
                  limits=limits)
    result['passed'] = (metrics['max_abs'] <= limits['max_abs']
                        and metrics['PWL_RMSE_abs'] <= limits['PWL_RMSE_abs']
                        and result['max_abs_over_scale'] <= limits['max_abs_over_scale']
                        and result['PWL_RMSE_over_scale'] <= limits['PWL_RMSE_over_scale'])
    return result


def snapshots(data):
    """Products/energy are formed on this run's original grid before PWL."""
    e = np.array([data[f'V_{p}_grid_kV'] for p in 'abc'])
    i = np.array([data[f'I_{p}_ac_to_bridge_kA'] for p in 'abc'])
    pole = np.array([data[f'V_{p}_pole_kV'] for p in 'abc'])
    vr = np.array([data[f'VR_{p}_kV'] for p in 'abc'])
    vp, vn = data['Vdc_p_kV'], data['Vdc_n_kV']
    upper = np.array([1 / data[f'R_{p}_u_ohm'] for p in 'abc'])
    lower = np.array([1 / data[f'R_{p}_l_ohm'] for p in 'abc'])
    ea, ia = (2 / 3) * (e[0] - (e[1] + e[2]) / 2), (2 / 3) * (i[0] - (i[1] + i[2]) / 2)
    eb, ib = (e[1] - e[2]) / math.sqrt(3), (i[1] - i[2]) / math.sqrt(3)
    return {'W': .005 * np.sum(i * i, axis=0), 'Pg': np.sum(e * i, axis=0),
                'Qg': 1.5 * (eb * ia - ea * ib), 'Pdc': (vp - vn) * data['I_dc_absorb_kA'],
                'PR': np.sum(vr * i, axis=0), 'Psw': np.sum(upper * (vp - pole)**2 + lower * (pole - vn)**2, axis=0)}


def features(time, current, start, end):
    """Fixed60Hz sine/cosine projection of each affine segment, no fitting."""
    t, y = clip(time, current, start, end)
    duration = end - start
    d = np.diff(t)
    z = (2 * math.pi * 60) * d / 2
    theta = (2 * math.pi * 60) * (t[:-1] + d / 2)
    average, change = (y[:-1] + y[1:]) / 2, y[1:] - y[:-1]
    # j(z)=(sin(z)-z*cos(z))/z**2. The series avoids cancellation.
    j = np.empty_like(z)
    small = np.abs(z) < .05
    zs = z[small]
    j[small] = zs * (1/3 + zs**2 * (-1/30 + zs**2 * (1/840 + zs**2 * (-1/45360 + zs**2/3991680))))
    j[~small] = (np.sin(z[~small]) - z[~small] * np.cos(z[~small])) / z[~small]**2
    even, odd = average * d * np.sinc(z / math.pi), change * d * j / 2
    sine = 2 * math.fsum(even * np.sin(theta) + odd * np.cos(theta)) / duration
    cosine = 2 * math.fsum(even * np.cos(theta) - odd * np.sin(theta)) / duration
    dc = mean(t, y)
    mean_square = square_mean(t, y)
    fundamental_square = (sine * sine + cosine * cosine) / 2
    residual_square = mean_square - dc * dc - fundamental_square
    require(residual_square >= -1e-12, 'Nonfundamental radicand below allowed roundoff')
    fundamental = math.sqrt(fundamental_square)
    residual = math.sqrt(max(residual_square, 0))
    return {'mean_A': dc, 'total_RMS_A': math.sqrt(mean_square), 'fundamental_RMS_A': fundamental,
                'fundamental_phase_deg': math.degrees(math.atan2(cosine, sine)),
                'fundamental_sine_coefficient_A': sine, 'fundamental_cosine_coefficient_A': cosine,
                'nonfundamental_RMS_excluding_DC_A': residual,
                'residual_ratio_to_fundamental': residual / fundamental if fundamental > 0 else None,
                'nonfundamental_is_standard_THD': False, 'fixed_frequency_Hz': 60}


def compare_cross_h(coarse, fine, protocol):
    """Candidate5us versus qualified native2.5us under the frozen cross-step gates."""
    availability = _admit_pair(coarse, fine, protocol, (5e-6, 2.5e-6))
    coarse, fine = _float_arrays(coarse), _float_arrays(fine)
    ct, ft = coarse['TIME_native_s'], fine['TIME_native_s']
    require(len(ct) == protocol['raw_rows']['coarse'] and len(ft) == protocol['raw_rows']['fine'], 'Complete dual-step row counts required')
    require(len(ft) == 2 * len(ct) - 1, 'Every coarse acquisition point needs its fine partner')
    nominal = np.arange(len(ct)) * 5e-6
    require(float(np.max(np.abs(ct - nominal))) <= 2e-12 and float(np.max(np.abs(ft - np.arange(len(ft)) * 2.5e-6))) <= 2e-12,
            'Both original centers need their own configured clock gate')
    require(float(np.max(np.abs(ct - ft[::2]))) <= 4e-12, 'Shared recorded centers exceed4ps')
    exact_inputs = {}
    for p in 'abc':
        for side in 'ul':
            for key in [f'applied_g_{p}_{side}', f'R_{p}_{side}_ohm']:
                exact_inputs[key] = bool(np.array_equal(coarse[key], fine[key][::2]))
    windows = protocol['windows']
    continuous, jumps, mean_reports = {}, {}, {}
    cs, fs = snapshots(coarse), snapshots(fine)
    families = {'iabc_A': [f'I_{p}_ac_to_bridge_kA' for p in 'abc'],
                'VRabc_V': [f'VR_{p}_kV' for p in 'abc'],
                'grid_abc_V': [f'V_{p}_grid_kV' for p in 'abc'], 'inductor_energy_J': ['W']}
    jump_families = {'pole_and_DC_rails_V': [f'V_{p}_pole_kV' for p in 'abc'] + ['Vdc_p_kV', 'Vdc_n_kV'],
                     'VLabc_V': [f'VL_{p}_kV' for p in 'abc'], 'fresh_Jdc_A': ['I_dc_absorb_kA']}
    for window in windows:
        label, start, end = window['name'], window['start_s'], window['end_s']
        continuous[label], jumps[label], mean_reports[label] = {}, {}, {}
        for family, keys in families.items():
            limit = protocol['candidate_cross_h_continuous_all_windows'][family]
            for key in keys:
                a, b = (cs[key], fs[key]) if key == 'W' else (coarse[key], fine[key])
                continuous[label][key] = continuous_gate(difference(ct, a, ft, b, start, end), limit)
        first = int(Decimal(str(start)) / Decimal('.000005'))
        last = int(Decimal(str(end)) / Decimal('.000005'))
        for family, keys in jump_families.items():
            limit = protocol['discontinuous_quantities']['candidate_cross_h_shared_grid_hard_peak_limits'][family]
            for key in keys:
                error = coarse[key][first:last+1] - fine[key][2*first:2*last+1:2]
                peak = float(np.max(np.abs(error)))
                jumps[label][key] = {'shared_original_points': len(error), 'max_abs': peak, 'limit': limit,
                                        'passed': peak <= limit, 'PWL_diagnostic': difference(ct, coarse[key], ft, fine[key], start, end)}
        for key, family in [('Pg', 'Pgrid_Qgrid_Pdc_W'), ('Qg', 'Pgrid_Qgrid_Pdc_W'), ('Pdc', 'Pgrid_Qgrid_Pdc_W'),
                            ('PR', 'R_loss_W'), ('Psw', 'switch_loss_W')]:
            limits = protocol['mean_feature_limits_all_windows'][family]
            a, b = mean(*clip(ct, cs[key], start, end)), mean(*clip(ft, fs[key], start, end))
            delta, limit = abs(a - b), limits['candidate_cross_h_abs']
            mean_reports[label][key] = {'coarse_mean': a, 'fine_mean': b, 'absolute_difference': delta,
                'engineering_scale': limits['engineering_scale'], 'normalized_difference': delta / limits['engineering_scale'],
                'absolute_limit': limit, 'normalized_limit': limit / limits['engineering_scale'], 'passed': delta <= limit}
    acquisition = {}
    for family, keys in jump_families.items():
        limit = protocol['discontinuous_quantities']['candidate_cross_h_shared_grid_hard_peak_limits'][family]
        for key in keys:
            peak = float(np.max(np.abs(coarse[key] - fine[key][::2])))
            acquisition[key] = {'points': len(ct), 'max_abs': peak, 'limit': limit, 'passed': peak <= limit}
    steady = {}
    spec = protocol['steady_integer_cycle_features']
    start, end = spec['window_s']
    feature_fields = [('total_RMS_A', 'total_or_fundamental_I_RMS_A'), ('fundamental_RMS_A', 'total_or_fundamental_I_RMS_A'),
                      ('nonfundamental_RMS_excluding_DC_A', 'nonfundamental_residual_RMS_excluding_DC_A'),
                      ('residual_ratio_to_fundamental', 'residual_ratio_to_fundamental')]
    for p in 'abc':
        key = f'I_{p}_ac_to_bridge_kA'
        a, b = features(ct, coarse[key], start, end), features(ft, fine[key], start, end)
        prerequisite = min(a['fundamental_RMS_A'], b['fundamental_RMS_A']) >= spec['fundamental_phase_deg']['minimum_fundamental_RMS_A']
        comparisons = {}
        for field, family in feature_fields:
            limit = spec[family]['candidate_cross_h_abs']
            delta = None if a[field] is None or b[field] is None else abs(a[field] - b[field])
            passed = delta is not None and delta <= limit
            if field == 'residual_ratio_to_fundamental':
                passed = passed and prerequisite
            comparisons[field] = {'absolute_difference': delta, 'limit': limit, 'passed': passed}
        phase_delta = abs((a['fundamental_phase_deg'] - b['fundamental_phase_deg'] + 180) % 360 - 180)
        phase_limit = spec['fundamental_phase_deg']['candidate_cross_h_abs']
        comparisons['fundamental_phase_deg'] = {'wrapped_absolute_difference': phase_delta, 'limit': phase_limit,
            'passed': prerequisite and phase_delta <= phase_limit}
        cycles = []
        for n in range(spec['grid_cycles']):
            lo, hi = start + n / 60, start + (n + 1) / 60
            cycles.append({'window_s': [lo, hi], 'coarse': features(ct, coarse[key], lo, hi),
                               'fine': features(ft, fine[key], lo, hi), 'qualification': 'DIAGNOSTIC_NO_PER_CYCLE_LIMITS'})
        steady[p] = {'coarse': a, 'fine': b, 'phase_ratio_prerequisite_pass': prerequisite,
                         'hard': comparisons, 'cycles_diagnostic': cycles}
    hard = [v['passed'] for table in [continuous, jumps, mean_reports] for window in table.values() for v in window.values()]
    hard += [v['passed'] for v in acquisition.values()] + list(exact_inputs.values())
    hard += [v['passed'] for phase in steady.values() for v in phase['hard'].values()]
    return {'passed': all(hard), 'hard_results': len(hard), 'float_TIME_injective': availability,
                'exact_shared_inputs': exact_inputs,
                'continuous_PWL': continuous, 'jump_shared_peaks_and_PWL_diagnostics': jumps,
                'acquisition_jump_shared_peaks': acquisition, 'snapshot_means': mean_reports, 'steady': steady,
                'source_fixed400_pair_covered_by_each_run_source_hard_gates': True,
                'actual_TIME_centers_unchanged': True, 'candidate_accepted_by_this_module': False}


def compare_same_h(candidate, reference, protocol, *, h):
    """Pair original rows, including jumps; integrate errors on nominal i*h.

    This is the declared same-step statistic. It does not call the generic
    continuous-only comparator with event guards removed.
    """
    availability = _admit_pair(candidate, reference, protocol, (h, h))
    candidate, reference = _float_arrays(candidate), _float_arrays(reference)
    require(h in (5e-6, 2.5e-6), 'Only the two declared steps are supported')
    count = protocol['raw_rows']['coarse' if h == 5e-6 else 'fine']
    ct, rt = candidate['TIME_native_s'], reference['TIME_native_s']
    require(len(ct) == len(rt) == count, 'Complete original same-step grids required')
    nominal = np.arange(count) * h
    require(ct[0] == rt[0] == 0 and np.all(np.diff(ct) > 0) and np.all(np.diff(rt) > 0), 'Initial/ordered times differ')
    require(np.max(np.abs(ct - nominal)) <= 2e-12 and np.max(np.abs(rt - nominal)) <= 2e-12,
            'Each original clock must meet its configured grid')
    require(np.max(np.abs(ct - rt)) <= 4e-12, 'Paired original clocks differ by more than4ps')
    exact = {key: bool(np.array_equal(candidate[key], reference[key])) for key in candidate
             if key.startswith(('applied_g_', 'R_'))}
    require(len(exact) == 12, 'Six actual gates and six actual resistances required')
    cs, rs = snapshots(candidate), snapshots(reference)
    analog = [key for key in candidate if key != 'TIME_native_s' and key not in exact]
    require(len(analog) == 19 and set(candidate) == set(reference), 'Exactly32 matched plant quantities required')
    families = {key: 'grid_abc_V' if '_grid_' in key else 'iabc_and_fresh_Jdc_A'
                if key.startswith('I_') else 'all_other_plant_voltages_V' for key in analog}
    families.update({'Pg': 'Pg_Qg_Pdc_W', 'Qg': 'Pg_Qg_Pdc_W', 'Pdc': 'Pg_Qg_Pdc_W', 'W': 'energy_J'})
    windows = [*protocol['windows'], {'name': 'acquisition', 'start_s': 0, 'end_s': .200005}]
    pointwise, means, power_means = {}, {}, {}
    for window in windows:
        name, start, end = window['name'], window['start_s'], window['end_s']
        first, last = round(start / h), round(end / h)
        require(0 <= first < last < count, 'Same-step window falls outside acquisition')
        time = nominal[first:last + 1]
        pointwise[name] = {}
        for key, family in families.items():
            a, b = (cs[key], rs[key]) if key in cs else (candidate[key], reference[key])
            error = a[first:last + 1] - b[first:last + 1]
            stat = {'max_abs': float(np.max(np.abs(error))), 'PWL_RMSE_abs': math.sqrt(square_mean(time, error)),
                    'original_points': len(error), 'integration': 'nominal-grid original error samples'}
            pointwise[name][key] = continuous_gate(stat, protocol['same_h_candidate_hard_all_windows'][family])
        if name != 'acquisition':
            means[name] = {}
            power_means[name] = {}
            for key in ('Pg', 'Qg', 'Pdc'):
                a = mean(*clip(ct, cs[key], start, end))
                b = mean(*clip(rt, rs[key], start, end))
                power_means[name][key] = {'candidate_mean': a, 'reference_mean': b,
                                          'absolute_difference': abs(a - b),
                                          'qualification': 'covered by same-h point-power hard gates'}
            for key, family in [('PR', 'R_loss_W'), ('Psw', 'switch_loss_W')]:
                a = mean(*clip(ct, cs[key], start, end))
                b = mean(*clip(rt, rs[key], start, end))
                limit = protocol['mean_feature_limits_all_windows'][family]['reference_self_abs']
                means[name][key] = {'candidate_mean': a, 'reference_mean': b, 'absolute_difference': abs(a - b),
                                    'limit': limit, 'passed': abs(a - b) <= limit}
    steady = _same_step_features(candidate, reference, protocol)
    hard = list(exact.values()) + [value['passed'] for rows in pointwise.values() for value in rows.values()]
    hard += [value['passed'] for rows in means.values() for value in rows.values()]
    hard += [value['passed'] for phase in steady.values() for value in phase['hard'].values()]
    return {'passed': all(hard), 'hard_results': len(hard), 'float_TIME_injective': availability, 'exact_inputs': exact,
            'same_h_original_points': pointwise, 'loss_snapshot_means': means,
            'power_snapshot_means': power_means, 'steady': steady,
            'all_acquisition_points_and_tail_retained': True}


def _same_step_features(candidate, reference, protocol):
    """Six-cycle features use frozen candidate limits, with no fitting."""
    spec = protocol['steady_integer_cycle_features']
    start, end = spec['window_s']
    result = {}
    fields = {'total_RMS_A': 'total_or_fundamental_I_RMS_A',
              'fundamental_RMS_A': 'total_or_fundamental_I_RMS_A',
              'nonfundamental_RMS_excluding_DC_A': 'nonfundamental_residual_RMS_excluding_DC_A',
              'residual_ratio_to_fundamental': 'residual_ratio_to_fundamental'}
    for phase in 'abc':
        key = f'I_{phase}_ac_to_bridge_kA'
        a = features(candidate['TIME_native_s'], candidate[key], start, end)
        b = features(reference['TIME_native_s'], reference[key], start, end)
        prerequisite = min(a['fundamental_RMS_A'], b['fundamental_RMS_A']) >= spec['fundamental_phase_deg']['minimum_fundamental_RMS_A']
        hard = {}
        for field, family in fields.items():
            delta = None if a[field] is None or b[field] is None else abs(a[field] - b[field])
            limit = spec[family]['candidate_cross_h_abs']
            hard[field] = {'absolute_difference': delta, 'limit': limit,
                           'passed': delta is not None and delta <= limit
                           and (prerequisite or field != 'residual_ratio_to_fundamental')}
        delta = abs((a['fundamental_phase_deg'] - b['fundamental_phase_deg'] + 180) % 360 - 180)
        limit = spec['fundamental_phase_deg']['candidate_cross_h_abs']
        hard['fundamental_phase_deg'] = {'wrapped_absolute_difference': delta, 'limit': limit,
                                         'passed': prerequisite and delta <= limit}
        cycles = [{'window_s': [start + k / 60, start + (k + 1) / 60],
                   'candidate': features(candidate['TIME_native_s'], candidate[key], start + k / 60, start + (k + 1) / 60),
                   'reference': features(reference['TIME_native_s'], reference[key], start + k / 60, start + (k + 1) / 60),
                   'qualification': 'DIAGNOSTIC_NO_PER_CYCLE_LIMITS'} for k in range(spec['grid_cycles'])]
        result[phase] = {'candidate': a, 'reference': b, 'phase_ratio_prerequisite_pass': prerequisite,
                         'hard': hard, 'cycles_diagnostic': cycles}
    return result
