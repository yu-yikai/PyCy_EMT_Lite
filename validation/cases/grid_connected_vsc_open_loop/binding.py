"""算例28专用输入准入与32量映射；本模块不运行仿真或读取原始波形。

check_case会执行实际接入的输入函数，但不求解电路，须在调用前封定工具身份。
plant_data返回SI数组；_kV/_kA列名仅沿用冻结表身份，不表示再次缩放。
"""

import hashlib
import inspect
import marshal
import math
from decimal import Decimal as D
from numbers import Real

import numpy as np

from pycy_emt_lite import Inductor, Resistor, VoltageSource
from pycy_emt_lite.components import IdealSwitch

PHASES = "abc"


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _function_identity(function):
    _require(inspect.isfunction(function), "Expected a Python function")
    numbers = {name: float(function.__globals__[name]) for name in function.__code__.co_names
               if isinstance(function.__globals__.get(name), Real)
               and not isinstance(function.__globals__[name], bool)}
    _require(all(math.isfinite(v) for v in numbers.values()), "Nonfinite callback global")
    return {"module": function.__module__, "qualname": function.__qualname__,
            "source_path": inspect.getsourcefile(function), "first_line": function.__code__.co_firstlineno,
            "code_sha256": hashlib.sha256(marshal.dumps(function.__code__)).hexdigest(),
            "source_sha256": hashlib.sha256(inspect.getsource(function).encode()).hexdigest(),
            "global_numbers": numbers}


def callback_identity(callback, _depth=0):
    """只记录本例的函数和实数闭包，不序列化任意对象或运行状态。"""
    _require(_depth <= 2, "Unexpected nested callback")
    identity = _function_identity(callback)
    nonlocals = {}
    for name, value in inspect.getclosurevars(callback).nonlocals.items():
        if inspect.isfunction(value):
            nonlocals[name] = callback_identity(value, _depth+1)
        else:
            _require(isinstance(value, Real) and not isinstance(value, bool) and math.isfinite(value),
                     "Unexpected callback closure value")
            nonlocals[name] = {"type": type(value).__name__, "value": float(value)}
    identity["nonlocals"] = nonlocals
    identity["global_functions"] = {name: _function_identity(value)
                                    for name, value in inspect.getclosurevars(callback).globals.items()
                                    if inspect.isfunction(value)}
    return identity


def component_binding(components):
    """仅绑定16个元件的构造参数；不含branch_index、历史量或last_state。"""
    bindings = []
    for part in components:
        _require(type(part) in {VoltageSource, Resistor, Inductor, IdealSwitch}, "Unexpected component type")
        item = {"type": type(part).__name__, "name": part.name,
                "positive": part.positive, "negative": part.negative}
        if type(part) is VoltageSource:
            item["voltage"] = callback_identity(part.voltage) if callable(part.voltage) else part.voltage
            _require(part.derivative is None, "Unexpected source derivative override")
        elif type(part) is Resistor:
            item["resistance"] = part.resistance
        elif type(part) is Inductor:
            item.update(inductance=part.inductance, initial_current=part.initial_current)
        else:
            item.update(closed=callback_identity(part.closed), closed_resistance=part.closed_resistance,
                        open_conductance=part.open_conductance)
        bindings.append(item)
    _require(len(bindings) == 16 and len({p["name"] for p in bindings}) == 16, "Expected16 unique components")
    return bindings


def _check_structure(case, parameters):
    parts = {part.name: part for part in case.components}
    component_binding(case.components)
    expected = {"Vdc"} | {prefix+p for p in PHASES for prefix in ("V", "R", "L")} | {
        f"S{p}_{side}" for p in PHASES for side in ("upper", "lower")}
    _require(set(parts) == expected, "Component names differ")
    config = case.config
    _require(config.time_step in parameters["h_s"] and config.stop_time == parameters["acquisition_stop_s"]
             and config.start_time == 0 and config.record_every == 1 and config.method == "trapezoidal"
             and config.linear_solver_mode == "reuse" and not case.events and case.on_step is None,
             "Candidate acquisition configuration differs")
    dc = parts["Vdc"]
    _require(type(dc) is VoltageSource and (dc.positive, dc.negative, dc.voltage) ==
             ("dc_p", "dc_n", parameters["dc_V"]), "Floating DC source differs")
    for p in PHASES:
        source, resistor, inductor = (parts[prefix+p] for prefix in ("V", "R", "L"))
        _require(type(source) is VoltageSource and (source.positive, source.negative) == (f"grid_{p}", "0")
                 and callable(source.voltage), "AC source ports differ")
        _require(type(resistor) is Resistor and (resistor.positive, resistor.negative, resistor.resistance) ==
                 (f"grid_{p}", f"r_{p}", parameters["R_ohm"]), "Series resistor differs")
        _require(type(inductor) is Inductor and
                 (inductor.positive, inductor.negative, inductor.inductance, inductor.initial_current) ==
                 (f"r_{p}", f"pole_{p}", parameters["L_H"], 0), "Series inductor differs")
        for side, ports in (("upper", ("dc_p", f"pole_{p}")), ("lower", (f"pole_{p}", "dc_n"))):
            switch = parts[f"S{p}_{side}"]
            _require(type(switch) is IdealSwitch and (switch.positive, switch.negative) == ports and
                     (switch.closed_resistance, switch.open_conductance) ==
                     (parameters["Ron_ohm"], parameters["Goff_S"]), "Switch ports/constants differ")
    return parts


def _check_variant(example_namespace, tested, parameters, protocol, variant, settings):
    bounds = protocol["control_numeric_hard_allowances"]
    shifts = np.asarray(parameters["source_phase_rad"])
    h, count = settings["h_s"], settings["expected_rows"]
    parts = _check_structure(tested, parameters)
    switches = [parts[f"S{p}_{s}"] for p in PHASES for s in ("upper", "lower")]
    times = np.arange(count)*h
    gate_indices = np.arange(count)//round(parameters["gate_hold_s"]/h)
    reference_indices = gate_indices//round(parameters["reference_hold_s"]/parameters["gate_hold_s"])
    held_times = np.arange(int(reference_indices[-1])+1)*parameters["reference_hold_s"]
    refs = parameters["modulation"]*np.clip(held_times/parameters["ramp_s"], 0, 1)[:, None]*np.sin(
        2*np.pi*parameters["frequency_Hz"]*held_times[:, None]+shifts+np.deg2rad(parameters["delta_deg"]))
    ticks_per_carrier = round(1/parameters["carrier_Hz"]/parameters["gate_hold_s"])
    carrier = np.abs(gate_indices % ticks_per_carrier-ticks_per_carrier//2)/(ticks_per_carrier/4)-1
    upper = refs[reference_indices] >= carrier[:, None]
    expected = np.empty((count, 6), dtype=bool)
    expected[:, ::2], expected[:, 1::2] = upper, ~upper
    globals_ = switches[0].closed.__globals__
    original = globals_["held_reference"]
    _require(original is example_namespace["held_reference"] and
             all(s.closed.__globals__ is globals_ for s in switches), "Callbacks use different globals")
    context, calls, max_ref_error = [0, 0], 0, 0.0

    def spy(reference_time, phase_shift):
        nonlocal calls, max_ref_error
        row, phase = context
        _require(abs(reference_time-held_times[reference_indices[row]]) <= bounds["held_t_ref_center_s"]
                 and phase_shift == shifts[phase], "Attached held-reference arguments differ")
        value = original(reference_time, phase_shift)
        error = abs(value-refs[reference_indices[row], phase])
        _require(math.isfinite(value) and error <= bounds["reference_formula_abs_allowance"],
                 "Attached held-reference formula differs")
        calls, max_ref_error = calls+1, max(max_ref_error, float(error))
        return value

    def probe(row, column, time):
        context[:] = [row, column//2]
        previous_calls = calls
        value = switches[column].closed(float(time))
        _require(type(value) is bool and value == bool(expected[row, column]) and calls == previous_calls+1,
                 "Actual gate/held-reference usage differs")
        return value

    try:
        globals_["held_reference"] = spy
        actual = np.empty_like(expected)
        for row, time in enumerate(times):
            for column in range(6):
                actual[row, column] = probe(row, column, time)
        for row in range(count-1, -1, -1):
            for column in range(5, -1, -1):
                probe(row, column, times[row])
        for row in np.flatnonzero(np.arange(count) % round(parameters["gate_hold_s"]/h) == 0):
            time = times[row]
            nearby = [time+1e-12, np.nextafter(time, np.inf)]
            if time > 0:
                nearby += [time-1e-12, np.nextafter(time, -np.inf)]
            for perturbed in nearby:
                for column in range(6):
                    probe(row, column, perturbed)
        for switch in switches:
            for invalid in (h/3, -1e-12, float("nan"), float("inf"), True, 1+1j):
                try:
                    switch.closed(invalid)
                except ValueError:
                    continue
                raise ValueError("Gate accepted off-grid or invalid time")
    finally:
        globals_["held_reference"] = original
    _require(np.array_equal(actual[0], [False, True]*3), "Initial gates differ")
    if variant == "fine":
        _require(np.array_equal(actual[1::2], actual[:-1:2]), "Fine midpoint gates are not held")
    source_errors = {}
    for phase, shift in zip(PHASES, shifts, strict=True):
        source = parts["V"+phase].voltage
        values = np.fromiter((source(float(t)) for t in times), dtype=float, count=count)
        target = np.sqrt(2)*parameters["grid_phase_rms_V"]*np.clip(times/parameters["ramp_s"], 0, 1)*np.sin(
            2*np.pi*parameters["frequency_Hz"]*times+shift)
        error = float(np.max(np.abs(values-target)))
        _require(np.isfinite(values).all() and error <=
                 protocol["source_allowance"]["declared_three_phase_sin_libm_absolute_V"], "Actual AC source differs")
        source_errors[phase] = error
    report = {"h_s": h, "rows": count, "held_reference_calls": calls,
                         "reference_formula_max_abs": max_ref_error, "source_max_abs_V": source_errors,
                         "component_binding": component_binding(tested.components)}
    return report, actual


def check_case(example_namespace, case, parameters, protocol):
    """两档全网格检查实际六回调与三源；临时spy必须在返回或异常前恢复。"""
    _check_structure(case, parameters)
    before = component_binding(case.components)
    variants, applied = {}, {}
    for variant, settings in parameters["variants"].items():
        tested = case if case.config.time_step == settings["h_s"] else example_namespace["define_case"](
            time_step=settings["h_s"], stop_time=parameters["acquisition_stop_s"])
        variants[variant], applied[variant] = _check_variant(
            example_namespace, tested, parameters, protocol, variant, settings)
    _require(np.array_equal(applied["coarse"], applied["fine"][::2]), "Shared-point gates differ")
    _require(before == component_binding(case.components), "Input probing changed constructor/callback identity")
    return {"passed": True, "status": "CANDIDATE_INPUT_BINDING_PASS_NOT_NUMERIC_QUALIFICATION",
            "variants": variants, "component_binding": before,
            "all_original_grid_points_and_gate_boundaries_checked": True,
            "reverse_order_and_repeat_checked": True, "nearby_time_and_off_grid_checks": True,
            "held_reference_spy_restored": True, "native_control_observers_fabricated": False}


def plant_data(result, components):
    """从实际结果映射32量SI数组；VR作节点差，VL与DC电流取直接输出。"""
    parts = {part.name: part for part in components}

    def series(name):
        values = np.fromiter((row[name] for row in result.rows), dtype=float, count=len(result.rows))
        _require(np.isfinite(values).all(), "Missing or nonfinite candidate series: "+name)
        return values

    data = {"TIME_native_s": series("time"), "Vdc_p_kV": series("v:dc_p"), "Vdc_n_kV": series("v:dc_n"),
            "I_dc_absorb_kA": series("i:Vdc")}
    data["V_dc_source_kV"] = data["Vdc_p_kV"]-data["Vdc_n_kV"]
    for phase in PHASES:
        grid, pole = series(f"v:grid_{phase}"), series(f"v:pole_{phase}")
        data.update({f"V_{phase}_grid_kV": grid, f"V_{phase}_pole_kV": pole,
                     f"VR_{phase}_kV": grid-series(f"v:r_{phase}"), f"VL_{phase}_kV": series(f"v:L{phase}"),
                     f"I_{phase}_ac_to_bridge_kA": series(f"i:L{phase}")})
        for side, short in (("upper", "u"), ("lower", "l")):
            switch = parts[f"S{phase}_{side}"]
            _require(type(switch) is IdealSwitch, "Missing actual switch")
            state = series("state:"+switch.name)
            _require(np.isin(state, (0, 1)).all(), "Nonbinary actual switch state")
            ron, goff = D(str(switch.closed_resistance)), D(str(switch.open_conductance))
            _require(ron > 0 and goff > 0, "Nonpositive switch parameter")
            roff = D(1)/goff
            _require(float(D(1)/roff) == switch.open_conductance and
                     float(D(1)/ron) == 1/switch.closed_resistance, "Declared resistance/conductance mapping differs")
            data[f"applied_g_{phase}_{short}"] = state
            data[f"R_{phase}_{short}_ohm"] = np.where(state == 1, float(ron), float(roff))
    _require(len(data) == 32, "Expected32 plant quantities")
    return data
