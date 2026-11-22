"""并网VSC开环的32量纯Decimal物理检查；不执行仿真或读取文件。

输入rows与radii是可重复迭代且支持len的两条投影流，每行必须恰含names()
列出的32个量。evaluate中的数值与完整末位q均为SI（V、A、ohm、s）；
列名中的_kV/_kA仅沿用冻结表的身份，不能再次缩放。token仅供原生单位ASCII
入口使用，在解析时一次转换到SI；Python候选入口直接提供SI值与相应q。

本模块保留冻结参考核的19项物理预算、相族检查和条件离散预测。它不检查13个
原生内部控制观察量，也不冒充45量参考资格；实际接入的六个门极回调、保持函数
和端口身份须先由独立的全网格准入检查绑定。这里仍逐点核实际施加g/R与规范输入。
"""

import math
import re
from decimal import Decimal as D

# 局部noqa保留已验收核的原AST，避免为zip/dict/list风格改写物理表达式。
PHASES = 'abc'


def require(ok, message):
    if not ok:
        raise ValueError(message)


def names():
    return (['TIME_native_s'] + [f'V_{p}_grid_kV' for p in PHASES]
            + [f'V_{p}_pole_kV' for p in PHASES] + ['Vdc_p_kV', 'Vdc_n_kV']
            + [f'VR_{p}_kV' for p in PHASES] + [f'VL_{p}_kV' for p in PHASES]
            + [f'I_{p}_ac_to_bridge_kA' for p in PHASES] + ['I_dc_absorb_kA']
            + [f'applied_g_{p}_{s}' for p in PHASES for s in 'ul']
            + [f'R_{p}_{s}_ohm' for p in PHASES for s in 'ul'] + ['V_dc_source_kV'])


def unit(name):
    return ('s' if name == 'TIME_native_s' else 'kV' if name.startswith('V')
            else 'kA' if name.startswith('I') else 'ohm' if name.startswith('R') else '1')


def token(word, name):
    require(re.fullmatch(r'[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[EeDd][+-]?[0-9]+)?', word), 'Malformed token')
    value = D(word.replace('D', 'E').replace('d', 'E'))
    require(value.is_finite(), 'Nonfinite token')
    factor = D(1000) if unit(name) in {'kV', 'kA'} else D(1)
    return value * factor, D(1).scaleb(value.as_tuple().exponent) * factor


def references(time):
    amplitude = .85 * min(max(float(time) / .02, 0), 1)
    return [D(str(amplitude * math.sin(2*math.pi*60*float(time) + shift - math.pi/36)))
            for shift in [0, -2*math.pi/3, 2*math.pi/3]]


def canonical(index, h):
    per_gate = int(D('.000005') / h)
    require(per_gate*h == D('.000005') and per_gate in {1, 2}, 'Electrical step differs')
    k = index // per_gate
    held = D(k//20) * D('.0001')
    refs = references(held)
    carrier = D(abs(k % 200 - 100))/50-1
    bits = [int(r >= carrier) for r in refs]
    return held, refs, carrier, bits


def sources(time, sign=1):
    t = float(time)
    return [D(str(120*math.sqrt(2)*min(t/.02, 1)*math.sin(2*math.pi*60*t+sign*shift)))
            for shift in [0, -2*math.pi/3, 2*math.pi/3]]


def conductances(bits):
    return ([D(1000) if b else D('1e-9') for b in bits],
            [D('1e-9') if b else D(1000) for b in bits])


def solve(matrix, rhs):
    a = [list(row)+[b] for row, b in zip(matrix, rhs)]  # noqa: B905, RUF005
    for col in range(4):
        pivot = max(range(col, 4), key=lambda row: abs(a[row][col]))
        require(a[pivot][col] != 0, 'Singular four-variable independent network')
        a[col], a[pivot] = a[pivot], a[col]
        divisor = a[col][col]
        a[col] = [v/divisor for v in a[col]]
        for row in range(4):
            if row != col:
                multiple = a[row][col]
                a[row] = [x-multiple*y for x, y in zip(a[row], a[col])]  # noqa: B905
    return [row[-1] for row in a]


def advance(old_i, old_n, e, old_e, gu, gl, old_gu, old_gl, h):
    a = [[D(0)]*4 for _ in range(4)]
    rhs = []
    coefficient = D('.02') / h
    for j in range(3):
        z, old_z = 1/(gu[j]+gl[j]), 1/(old_gu[j]+old_gl[j])
        emf, old_emf = 400*gu[j]*z, 400*old_gu[j]*old_z
        a[j][j], a[j][3] = coefficient+1+z, D(1)
        rhs.append((coefficient-1-old_z)*old_i[j]-old_n+e[j]+old_e[j]-emf-old_emf)
    a[3], rhs = [D(1), D(1), D(1), D(0)], rhs+[D(0)]  # noqa: RUF005
    answer = solve(a, rhs)
    return answer[:3], answer[3]


def evaluate(rows, radii, *, h, expected_rows, limits, precision_caps, upper_states=None):
    """Check every supplied acquisition row/prefix against prospective budgets.

    No output file is opened, no reference qualification is granted here, and no
    original timestamp is changed. All input numbers and full-place radii are SI.
    A feedback case may supply its independently checked upper states by row.
    """
    require(h in {D('.000005'), D('.0000025')}, 'Unsupported electrical step')
    require(len(rows) == len(radii) == expected_rows and expected_rows >= 2, 'Incomplete acquisition')
    if upper_states is not None:
        require(len(upper_states) == expected_rows, 'Incomplete upper gate schedule')
        require(all(len(row) == 3 and all(bit in (0, 1) for bit in row) for row in upper_states),
                'Each row requires three binary upper gate states')
    expected = set(names())
    require(all(set(r) == expected and all(v.is_finite() for v in r.values()) for r in rows), '32 finite values required')
    require(all(set(q) == expected and all(v.is_finite() and v >= 0 for v in q.values()) for q in radii), '32 nonnegative finite radii required')
    maxima, raw_maxima, worst_rows = {}, {}, {}
    failures, failure_count, failed_gates = [], 0, set()

    def check(key, value, radius=D(0), bound=None):
        nonlocal failure_count
        limit = D(str(limits[key])) if bound is None else bound
        observed = abs(value)+radius
        if observed > maxima.get(key, D(-1)):
            maxima[key], worst_rows[key] = observed, k
        raw_maxima[key] = max(raw_maxima.get(key, D(0)), abs(value))
        if observed > limit:
            failure_count += 1
            failed_gates.add(key)
            if len(failures) < 40:
                failures.append(dict(gate=key, row=k, residual=str(value), radius=str(radius), limit=str(limit)))  # noqa: C408

    def exact(key, value, expected_value):
        check(key, value-D(expected_value), bound=D(0))

    def product_radius(a, qa, b, qb):
        return abs(a)*qb+abs(b)*qa+qa*qb

    pred_i, pred_n = [D(0)]*3, -D(400)*D('1e-9')/(D(1000)+D('1e-9'))
    old_e, old_gu, old_gl = [D(0)]*3, *conductances([0, 0, 0])
    previous = None
    work = work_q = D(0)
    phase_errors = {'plus': D(0), 'minus': D(0)}
    initial_energy = initial_energy_q = D(0)
    for k, (row, q) in enumerate(zip(rows, radii)):  # noqa: B905
        time = k*h
        check('TIME_configured_center_s', row['TIME_native_s']-time)
        if k == 0:
            exact('initial_TIME', row['TIME_native_s'], 0)
        require(q['TIME_native_s'] <= D(str(precision_caps.get('TIME_native_full_last_place_s', 1e-12))), 'TIME token cap')
        for name in names():
            if unit(name) == 'kV':
                require(q[name] <= D(str(precision_caps['every_plant_voltage_full_last_place_V'])), 'Voltage token cap')
                require(abs(row[name])+q[name] <= 900, 'Universal voltage guard')
            elif unit(name) == 'kA':
                require(q[name] <= D(str(precision_caps['phase_current_full_last_place_A'])), 'Current token cap')
                require(abs(row[name])+q[name] <= 440, 'Universal current guard')
        bits = canonical(k, h)[3] if upper_states is None else [int(bit) for bit in upper_states[k]]
        gu, gl = conductances(bits)
        for j, p in enumerate(PHASES):
            for s, b, g in [('u', bits[j], gu[j]), ('l', 1-bits[j], gl[j])]:
                exact('applied_g', row[f'applied_g_{p}_{s}'], b)
                exact('actual_R', row[f'R_{p}_{s}_ohm'], 1/g)

        e = [row[f'V_{p}_grid_kV'] for p in PHASES]
        pole = [row[f'V_{p}_pole_kV'] for p in PHASES]
        current = [row[f'I_{p}_ac_to_bridge_kA'] for p in PHASES]
        n, vp, jdc = row['Vdc_n_kV'], row['Vdc_p_kV'], row['I_dc_absorb_kA']
        qn, qvp, qj = q['Vdc_n_kV'], q['Vdc_p_kV'], q['I_dc_absorb_kA']
        for label, sign in [('plus', 1), ('minus', -1)]:
            for j, target in enumerate(sources(time, sign)):
                phase_errors[label] = max(phase_errors[label], abs(e[j]-target)+q[f'V_{PHASES[j]}_grid_kV']+D('1e-9'))
        for j, target in enumerate(sources(time)):
            check('source_configured_grid_with_tokens_V', e[j]-target, q[f'V_{PHASES[j]}_grid_kV']+D('1e-9'))
        check('source_terminal_400V_with_tokens_V', row['V_dc_source_kV']-400, q['V_dc_source_kV']+D('1e-10'))
        check('bridge_400V_with_tokens_V', vp-n-400, qvp+qn+D('1e-10'))
        if k:
            pred_i, pred_n = advance(pred_i, pred_n, e, old_e, gu, gl, old_gu, old_gl, h)
        power = (vp-n)*jdc
        power_q = product_radius(vp-n, qvp+qn, jdc, qj)
        for j, p in enumerate(PHASES):
            i, qi, v, qv = current[j], q[f'I_{p}_ac_to_bridge_kA'], pole[j], q[f'V_{p}_pole_kV']
            vr, vl, qr, ql = row[f'VR_{p}_kV'], row[f'VL_{p}_kV'], q[f'VR_{p}_kV'], q[f'VL_{p}_kV']
            z, emf = 1/(gu[j]+gl[j]), 400*gu[j]/(gu[j]+gl[j])
            if k == 0:
                check('initial_phase_current_with_tokens_A', i, qi)
                check('initial_pole_with_tokens_V', v, qv)
            check('resistor_with_tokens_V', vr-i, qr+qi)
            check('phase_KVL_with_tokens_V', e[j]-vr-vl-v, q[f'V_{p}_grid_kV']+qr+ql+qv)
            check('pole_KCL_with_tokens_A', i+gu[j]*(vp-v)-gl[j]*(v-n), qi+gu[j]*(qvp+qv)+gl[j]*(qv+qn))
            check('pole_Thevenin_with_tokens_V', v-n-emf-z*i, qv+qn+z*qi)
            check('conditional_reduced_TR_current_A', i-pred_i[j], qi+D('1e-8')+time/D('.01')*D(4)/3*D('2.02e-7'))
            if previous:
                old, oq = previous
                oi, oiq = old[f'I_{p}_ac_to_bridge_kA'], oq[f'I_{p}_ac_to_bridge_kA']
                ovl, ovq = old[f'VL_{p}_kV'], oq[f'VL_{p}_kV']
                check('full_TR_with_tokens_V', D('.02')/h*(i-oi)-vl-ovl, D('.02')/h*(qi+oiq)+ql+ovq)
                work += h/4*(vl+ovl)*(i+oi)
                work_q += h/4*product_radius(vl+ovl, ql+ovq, i+oi, qi+oiq)
            upper, lower = vp-v, v-n
            power += vr*i+vl*i+gu[j]*upper**2+gl[j]*lower**2-e[j]*i
            power_q += (product_radius(vr, qr, i, qi)+product_radius(vl, ql, i, qi)
                        +gu[j]*(2*abs(upper)*(qvp+qv)+(qvp+qv)**2)
                        +gl[j]*(2*abs(lower)*(qv+qn)+(qv+qn)**2)
                        +product_radius(e[j], q[f'V_{p}_grid_kV'], i, qi))
        check('three_line_KCL_with_tokens_A', sum(current), sum(q[f'I_{p}_ac_to_bridge_kA'] for p in PHASES))
        check('DC_rail_KCL_with_tokens_A', jdc+sum(g*(vp-v) for g, v in zip(gu, pole)),  # noqa: B905
              qj+sum(g*(qvp+q[f'V_{p}_pole_kV']) for g, p in zip(gu, PHASES)))  # noqa: B905
        check('DC_rail_KCL_with_tokens_A', jdc+sum(g*(v-n) for g, v in zip(gl, pole)),  # noqa: B905
              qj+sum(g*(qn+q[f'V_{p}_pole_kV']) for g, p in zip(gl, PHASES)))  # noqa: B905
        check('commonmode_with_tokens_V', n-sum(e[j]-400*gu[j]/(gu[j]+gl[j])-(1+1/(gu[j]+gl[j]))*current[j] for j in range(3))/3,
              qn+sum(q[f'V_{p}_grid_kV']+(1+1/(gu[j]+gl[j]))*q[f'I_{p}_ac_to_bridge_kA'] for j, p in enumerate(PHASES))/3)
        check('conditional_reduced_TR_rail_V', n-pred_n, qn+D('2.2e-6'))
        if k == 0:
            check('initial_DC_leakage_with_tokens_A', jdc+1200/(D('1e9')+D('.001')), qj)
        check('instantaneous_power_with_tokens_W', power, power_q)
        energy = D('.005')*sum(i*i for i in current)
        energy_q = D('.005')*sum(2*abs(current[j])*q[f'I_{p}_ac_to_bridge_kA']+q[f'I_{p}_ac_to_bridge_kA']**2 for j, p in enumerate(PHASES))
        if k == 0:
            initial_energy, initial_energy_q = energy, energy_q
        else:
            check('prefix_TR_energy_with_tokens_J', energy-initial_energy-work, energy_q+initial_energy_q+work_q)
        previous, old_e, old_gu, old_gl = (row, q), e, gu, gl
    phase_ok = (phase_errors['plus'] <= D(str(limits['source_configured_grid_with_tokens_V']))
                and phase_errors['minus'] > D(str(limits['source_configured_grid_with_tokens_V'])))
    prerequisites = {'source_configured_grid_with_tokens_V', 'source_terminal_400V_with_tokens_V',
                     'bridge_400V_with_tokens_V', 'initial_phase_current_with_tokens_A',
                     'initial_pole_with_tokens_V', 'initial_DC_leakage_with_tokens_A', 'commonmode_with_tokens_V',
                     'applied_g', 'actual_R'}
    pre_ok = phase_ok and not failed_gates.intersection(prerequisites)
    physical_input_ok = not failed_gates.intersection({'applied_g', 'actual_R'})
    return dict(observed_pass=failure_count == 0 and phase_ok, rows=len(rows), intervals=len(rows)-1,  # noqa: C408
                failure_count=failure_count, failed_gates=sorted(failed_gates), first_failures=failures, phase_family_plus_only=phase_ok,
                phase_errors_V={k: str(v) for k, v in phase_errors.items()},
                maxima_with_full_token={k: str(v) for k, v in maxima.items()},
                raw_maxima={k: str(v) for k, v in raw_maxima.items()}, worst_rows=worst_rows,
                conditional_prediction_prerequisites_pass=pre_ok,
                physical_input_prerequisites_pass=physical_input_ok,
                physical_residuals_status=('observed checks with admitted discrete inputs' if physical_input_ok
                                           else 'DIAGNOSTIC_ONLY_CANONICAL_INPUTS_NOT_ACTUAL_INPUT_QUALIFICATION'),
                conditional_predictions='conditional observed checks' if pre_ok else 'diagnostic only',
                all_acquisition_rows_and_energy_prefixes_retained=True,
                actual_mapping_proven_by_this_kernel=False, overall_reference_accepted=False)
