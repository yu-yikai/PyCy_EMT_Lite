"""Compare Example 35 with both original, qualified PSCAD reversal runs."""

import argparse
import json
import math
import platform
import runpy
import subprocess
from dataclasses import replace
from datetime import UTC, datetime
from operator import itemgetter
from pathlib import Path

import numpy as np

from pycy_emt_lite import OutputOptions, run_case
from validation.cases.grid_connected_vsc_closed_loop.compare import (
    ROOT,
    frozen_json,
    snapshot_inputs,
)
from validation.cases.grid_connected_vsc_open_loop.compare import save_json
from validation.cases.grid_connected_vsc_open_loop.metrics import require
from validation.cases.pjm5_load_step.compare import admit, record_path
from validation.cases.two_terminal_vsc_hvdc.compare import descriptors
from validation.common.runner import sha256

from . import checks

CACHE = ROOT / "local_reference"
PROTOCOL = Path(__file__).with_name("candidate_protocol.json")
PROTOCOL_SHA = "78c0c1e8d4b68e55034d2af2439ea383e3e86fd10f5069349ae90e8635b73a7e"
GRIDS = ("5us", "2p5us")
PHASES = checks.PHASES
RECEIPT_STATUS = "NATIVE_D1_STORAGE_GRID_LONG_CLOSED_FOR_NUMERIC_REVIEW"
GENERATED = "Main.f", "Main.dta", "Station.f", "Station.dta"
NATIVE = {
    "absolute_s": ("Absolute_TIME_s",), "ocv_command_v": ("OCV_command_kV",), "bus_v": ("V_a_dc_kV",),
    "pol_v": ("V_pol_kV",), "ocv_v": ("V_ocv_kV",), "star_v": ("V_a_star_kV",),
    "storage_a": ("I_storage_kA",), "polar_r_a": ("I_R1_kA",), "polar_cap_a": ("I_C1_kA",),
    "bus_cap_a": ("I_Cdc_kA",), "ocv_a": ("I_ocv_kA",),
    **{f"{key}_v": tuple(f"V_a_{p}_{role}_kV" for p in PHASES)
       for key, role in (("source", "grid"), ("pcc", "pcc"), ("pole", "pole"))},
    **{f"{key}_a": tuple(f"I_a_{p}_{role}_kA" for p in PHASES)
       for key, role in (("feed", "feeder"), ("phase", "phase"), ("upper", "upper"), ("lower", "lower"))},
    **{f"{side}_on": tuple(f"R_a_{p}_{side}_ohm" for p in PHASES) for side in ("upper", "lower")},
    "applied": tuple(f"Ref_a_{p}_pu" for p in PHASES),
}
LOG = {"j": "j", "sample": "inner_tick", "outer": "outer_tick", "saturation": "saturated",
       "theta_rad": "theta_rad", "omega_rad_s": "omega_rad_s", "p_ref_w": "p_ref_w", "q_ref_var": "q_ref_var",
       "ip_ref_a": "ip_ref_a", "id_ref_a": "id_ref_a", "iq_ref_a": "iq_ref_a", "pll_integrator": "pll_integrator",
       "d_integrator": "id_integrator", "q_integrator": "iq_integrator"}


def read(path):
    return json.loads(path.read_bytes())


def passed(checks):
    return all(passed(value) if isinstance(value, dict) else bool(value) for value in checks.values())


def admit_run(item, name, mode, protocol, protocol_sha, evidence):
    path = record_path(item["receipt"], evidence)
    run, receipt = path.parent, read(path)
    require(run.is_relative_to(CACHE.resolve()), "Native archives must stay inside local_reference")
    grid, timeline = protocol["grids"][name], protocol["timeline"]
    seed = mode == "seed"
    rows = grid["seed_rows_including_zero" if seed else "positive_continuation_rows"]
    log_rows = grid["seed_tail_rows" if seed else "positive_continuation_rows"]
    stop = timeline["seed_stop_s" if seed else "continuation_duration_s"]
    require((receipt["status"], receipt["protocol_sha256"], receipt["grid"], receipt["variant"], receipt["mode"],
             receipt["step_s"], receipt["stop_s"], receipt["rows"], receipt["absolute_snapshot_s"], receipt["stem"])
            == (RECEIPT_STATUS, protocol_sha, name, name, mode, grid["step_s"], stop, rows, timeline["snapshot_s"], "storage_grid"),
            "Native execution is from a different protocol or grid")
    require(all((run / key).resolve().is_relative_to(run) for key in receipt["files"]), "Native artifact escapes the isolated run")
    files = {key: admit(run / key, value, evidence) for key, value in receipt["files"].items()}
    terminal, admission, worker = (read(files[key]) for key in ("terminal.json", "pre_run_admission.json", "worker.json"))
    proof = admission["proof"]
    require(record_path(item["metadata"], evidence) == files["terminal.json"]
            and record_path(item["compiled_admission"], evidence) == files["pre_run_admission.json"]
            and terminal["worker_returncode"] == 0 and terminal["stop_reason"] is None
            and not terminal["remaining_owned"] and not terminal["cleanup"]
            and terminal["source_hash_unchanged"] and terminal["parent_environment_unchanged"]
            and worker["causal_build_admitted"] and worker["run_calls"] == 1 and worker["run_returned"]
            and worker["build_errors"] == worker["build_warnings"] == 0, "Native build/run did not close cleanly")
    require(proof["status"] == "PASS_NATIVE_D1_STORAGE_GRID_LONG_COMPILED_ADMISSION" and proof["physical_branches"] == 20
            and proof["protocol_sha256"] == protocol_sha and proof["grid"] == name
            and admission["native_pgb_layout"] == receipt["native_pgb_layout"] and len(admission["native_pgb_layout"]) == 41,
            "Unadmitted native topology or PGB layout")
    runtime = receipt["native_runtime"]
    require((runtime["pscad_version"], runtime["emtdc_build"], runtime["compiler"], runtime["platform"], runtime["emtdc_pid_observed"])
            == ("5.0.0", "20210219", "gf46", "x86", True), "Native PSCAD toolchain differs")
    admit(run / runtime["batch_path"], runtime["batch_sha256"], evidence)
    for receipt_key, file in (("terminal_sha256", "terminal.json"), ("pre_run_admission_sha256", "pre_run_admission.json"),
                              ("sealed_inputs_sha256", "sealed_inputs.json"), ("snapshot_sha256", receipt["snapshot_path"])):
        require(receipt[receipt_key] == receipt["files"][file], f"Unbound native execution artifact: {file}")
    work = run / receipt["generated_work"]
    require(work == run / "project/vdiv.gf46" and record_path(item["snapshot"], evidence) == files[receipt["snapshot_path"]],
            "Unexpected original compiled folder or snapshot")
    for group in ("post_run_generated_sha256", "raw_files_sha256"):
        require(all(receipt["files"][f'{receipt["generated_work"]}/{key}'] == value for key, value in receipt[group].items()),
                "Generated or raw native hashes do not bind the archived files")
    for key, value in read(files["sealed_inputs.json"]).items():
        require(Path(key).name == key, "Unexpected native input file name")
        admit(run / "input_snapshot" / key, value, evidence)
    logger = receipt["native_logs"]["a"]
    require((logger["file"], logger["rows"], logger["columns"]) == ("storage_station.log", log_rows, 43)
            and logger["sha256"] == receipt["files"][f'{receipt["generated_work"]}/{logger["file"]}']
            and receipt["native_log_columns"] == proof["log_columns"] and len(receipt["native_log_columns"]) == 43,
            "Native controller log does not match the admitted ABI")
    return receipt, work, proof


def reference_grid(summary, pair, name, protocol, protocol_sha, evidence):
    trial = summary["grids"][name]
    review = read(record_path(trial["audit"], evidence))
    require(pair["grid_reports"][name]["sha256"] == trial["audit"]["sha256"], "Native pair did not bind this audit")
    require((review["status"], review["grid"], review["protocol_sha256"]) == ("PASS_NATIVE_D1_STORAGE_GRID_LONG", name, protocol_sha)
            and passed(review["checks"]) and review["snapshot"]["anchor_si"] == trial["snapshot_start_si"], "Missing decoded native audit")
    for role, source in trial["runs"].items():
        require(review["receipts"][role]["sha256"] == source["receipt"]["sha256"]
                and review["integration_review"][role]["independent_all_interval_tr_and_energy_pass"],
                "Native audit does not bind original receipt or integration evidence")
    seed, seed_work, proof = admit_run(trial["runs"]["seed"], name, "seed", protocol, protocol_sha, evidence)
    restart, work, _ = admit_run(trial["runs"]["restart"], name, "restart", protocol, protocol_sha, evidence)
    require(restart["seed_receipt_sha256"] == trial["runs"]["seed"]["receipt"]["sha256"]
            and seed["snapshot_sha256"] == restart["snapshot_sha256"] == review["snapshot_sha256"]
            and seed["native_pgb_layout"] == restart["native_pgb_layout"]
            and all(seed["post_run_generated_sha256"][file] == restart["post_run_generated_sha256"][file]
                    == review["generated_identity"][file] for file in GENERATED), "Native restart changed seed identity")
    return (work, restart), seed["snapshot_row"], decode_snapshot(seed, seed_work, proof), trial["snapshot_start_si"]


def decode_snapshot(seed, work, proof):
    """Read signed capacitor voltages and branch currents from the actual EMTDC saved state."""
    lines = (work / Path(seed["snapshot_path"]).name).read_text("ascii").splitlines()
    require(lines[0] == "! EMTDC SNAP-SHOT - Version, Time, Delt"
            and tuple(map(float, lines[1].split())) == (5., seed["absolute_snapshot_s"], seed["step_s"]), "Wrong native saved clock")
    branches = proof["snapshot_index"]["branches"]

    def vector(tag):
        starts = [index for index, line in enumerate(lines) if line.strip() == tag]
        require(len(starts) == 1, f"Missing or duplicate EMTDC snapshot field {tag}")
        values = []
        for line in lines[starts[0]+1:]:
            if line.lstrip().startswith("!") or len(values) == proof["generated_branches"]:
                break
            values.extend(float(word.replace("D", "E")) for word in line.split())
        require(len(values) == proof["generated_branches"] and np.isfinite(values).all(), f"Wrong EMTDC snapshot width for {tag}")
        return values

    volts, current = vector("!V20L"), vector("!CBR")

    def value(values, name, kind):
        branch = branches[name]
        require(branch["kind"] == kind and branch["orientation"] in (-1, 1), f"Unexpected saved branch {name}")
        return 1000 * branch["orientation"] * values[branch["index"] - 1]

    return {"bus_v": value(volts, "I_Cdc_kA", "C"), "pol_v": value(volts, "I_C1_kA", "C"),
            "storage_a": value(current, "I_storage_kA", "R"),
            **{f"{key}_a": [value(current, f"I_a_{p}_{role}_kA", "RL") for p in PHASES]
               for key, role in (("feed", "feeder"), ("phase", "phase"))}}


def read_native(archive, anchor, grid, protocol):
    work, receipt = archive
    stem, count = receipt["stem"], grid["native_positive_rows"]
    layout = descriptors((work / f"{stem}.inf").read_text("ascii").splitlines())
    mapping = (work / "vdiv.map").read_text("ascii").splitlines()
    require(mapping.count("PGBList:") == 1, "Missing original compiled PGB list")
    names = [row["name"] for row in layout]
    wanted = {name for group in NATIVE.values() for name in group}
    start = mapping.index("PGBList:") + 1
    require(len(names) == len(wanted) == 41 and set(names) == wanted and set(anchor) == wanted | {"display_TIME_s"}
            and layout == receipt["native_pgb_layout"] == descriptors(mapping[start:start+41]), "Changed raw native output mapping")
    shards = [work / f"{stem}_{part:02}.out" for part in range(1, 6)]
    require(set(work.glob(f"{stem}_*.out")) == set(shards)
            and set(receipt["raw_files_sha256"]) == {f"{stem}.inf", *(file.name for file in shards)}, "Incomplete raw native export")
    raw, display = {}, None
    for part, path in enumerate(shards):
        names_part = names[part*10:(part+1)*10]
        data = np.loadtxt(path, skiprows=1)
        require(data.shape == (count, len(names_part)+1) and np.isfinite(data).all(), f"Invalid raw PSCAD waveform {path}")
        if display is None:
            display = data[:, 0].copy()
        else:
            require(np.array_equal(display, data[:, 0]), "PSCAD OUT shard clocks differ")
        raw.update({name: np.r_[float(anchor[name]), data[:, i]] for i, name in enumerate(names_part, 1)})
    trace = {}
    for key, names_group in NATIVE.items():
        columns = [raw[name] * (1000 if name.endswith(("_kV", "_kA")) else 1) for name in names_group]
        trace[key] = columns[0] if len(columns) == 1 else np.column_stack(columns)
    for key in ("upper_on", "lower_on"):
        on, off = (protocol["ac_circuit"][f"bridge_{state}_ohm"] for state in ("closed", "open"))
        require(np.isin(trace[key], (on, off)).all(), "Unexpected native actual gate resistance")
        trace[key] = trace[key] == on
    snap = protocol["example"]["native_snapshot_s"]
    trace["time_s"] = np.r_[float(anchor["display_TIME_s"]) - snap, display]
    fields = receipt["native_log_columns"]
    table = np.loadtxt(work / "storage_station.log", delimiter=",")
    require(len(fields) == len(set(fields)) == 43 and table.shape == (count, 43) and np.isfinite(table).all(), "Malformed original controller log")
    log = dict(zip(fields, table.T, strict=True))
    controller = {key: log[name] for key, name in LOG.items()}
    controller.update(gate_tick=log["j"] // round(protocol["schedule"]["gate_period_s"] / grid["step_s"]),
                      enabled=log["outer_tick"] * log["pcc_ready"], absolute_s=log["time_s"],
                      filtered_v=np.hypot(log["pcc_d_v"], log["pcc_q_v"]) / math.sqrt(2),
                      pending=np.column_stack([log[f"pending_{p}"] for p in PHASES]))
    return trace, controller


def candidate_trace(factory, grid, protocol):
    example = protocol["example"]
    step, stop, count = grid["step_s"], example["stop_s"], grid["candidate_rows_including_initial"]
    case = factory(time_step=step, stop_time=stop)
    require(case.name == example["case"], "Unexpected candidate case identity")
    result = run_case(replace(case, output=OutputOptions(show_figure=False), plots=(), summary=None))
    require((len(result.rows), result.time_step, result.stop_time, result.method) == (count, step, stop, "trapezoidal"),
            "Candidate does not use the fixed TR recording grid")
    fields = {
        "time_s": ("time",), "bus_v": ("v:Cdc",), "pol_v": ("v:C1",), "ocv_v": ("v:ocv",), "negative_v": ("v:a_n",),
        "star_v": ("v:a_star",), "storage_a": ("i:R0",), "polar_r_a": ("i:R1",), "polar_cap_a": ("i:C1",),
        "bus_cap_a": ("i:Cdc",), "ocv_a": ("i:Vocv",),
        **{f"{key}_v": tuple(f"v:a_{role}_{p}" for p in PHASES)
           for key, role in (("source", "grid"), ("pcc", "pcc"), ("pole", "pole"))},
        "feed_a": tuple(f"i:a_Lg{p}" for p in PHASES), "phase_a": tuple(f"i:a_L{p}" for p in PHASES),
        **{f"{side}_a": tuple(f"i:a_S{p}_{side}" for p in PHASES) for side in ("upper", "lower")},
        **{f"{side}_on": tuple(f"state:a_S{p}_{side}" for p in PHASES) for side in ("upper", "lower")},
        **{key: tuple(f"a_{key}_{p}" for p in PHASES) for key in ("applied", "pending")},
        **{key: (f"a_{signal}",) for key, signal in
           {"j": "j", "gate_tick": "gate_tick", "sample": "sample_update", "outer": "outer_due", "enabled": "outer_enabled",
            "saturation": "saturated", "filtered_v": "pcc_filtered_rms_v", "ip_ref_a": "ip_ref_a", "id_ref_a": "id_ref",
            "iq_ref_a": "iq_ref", "p_ref_w": "p_ref_w", "q_ref_var": "q_ref_var", "theta_rad": "theta", "omega_rad_s": "pll_omega",
            "pll_integrator": "pll_xi", "d_integrator": "z_d", "q_integrator": "z_q"}.items()},
        "measured_p_w": ("pcc_p_w",), "measured_q_var": ("pcc_q_var",), "measured_storage_w": ("storage_p_w",),
    }
    columns = tuple(key for group in fields.values() for key in group)
    matrix = np.fromiter(map(itemgetter(*columns), result.rows), dtype=np.dtype((float, len(columns))), count=count)
    require(np.isfinite(matrix).all(), "Nonfinite candidate waveform")
    trace, start = {}, 0
    for key, group in fields.items():
        stop = start + len(group)
        trace[key] = matrix[:, start] if len(group) == 1 else matrix[:, start:stop]
        start = stop
    for key in ("source_v", "pcc_v"):
        trace[key] -= trace["star_v"][:, None]
    trace["pole_v"] -= trace["negative_v"][:, None]
    trace["ocv_v"] -= trace["negative_v"]
    trace["star_v"] -= trace["negative_v"]
    for key in ("upper_on", "lower_on"):
        require(np.isin(trace[key], (0., 1.)).all(), "Invalid candidate switch values")
        trace[key] = trace[key].astype(bool)
    return trace


def difference(candidate, native, limit, *, angle=False):
    delta = candidate - native
    if angle:
        delta = (delta + math.pi) % math.tau - math.pi
    maximum = checks.peak(delta)
    return {"maximum": maximum, "rms": float(np.sqrt(np.mean(delta**2))), "limit": limit, "passed": maximum <= limit}


def same_grid(candidate, native, controller, decoded, anchor, grid, protocol, power):
    limits = protocol["same_grid_limits"]
    snap, step = protocol["example"]["native_snapshot_s"], grid["step_s"]
    ticks = np.arange(len(candidate["time_s"]))
    clock = max(checks.peak(candidate["time_s"] - ticks*step), checks.peak(native["time_s"] - ticks*step),
                checks.peak(candidate["time_s"] - native["time_s"]), checks.peak(candidate["time_s"] + snap - native["absolute_s"]),
                checks.peak(controller["absolute_s"] - native["absolute_s"][1:]))
    initial = protocol["initial_state"]
    require((grid["initial_bus_v"], grid["initial_polarization_v"], grid["reference_initial_storage_current_a"])
            == (anchor["vdc_v"], anchor["polarization_v"], anchor["storage_current_a"]), "Frozen initial values differ from native audit")
    voltage_error = max(abs(candidate[key][0]-decoded[key]) for key in ("bus_v", "pol_v"))
    current_error = max(checks.peak(candidate[key][0]-decoded[key]) for key in ("storage_a", "feed_a", "phase_a"))
    saved_row_error_v = max(abs(native[key][0]-decoded[key]) for key in ("bus_v", "pol_v"))
    saved_row_error_a = max(checks.peak(native[key][0]-decoded[key]) for key in ("storage_a", "feed_a", "phase_a"))
    measurements = {}
    for keys, limit in ((checks.VOLTAGE, "voltage_abs_v"), (checks.CURRENT, "current_abs_a"), (("applied",), "modulation_abs_pu")):
        measurements.update({key: difference(candidate[key][1:], native[key][1:], limits[limit]) for key in keys})
    for keys, limit in ((checks.CONTROL, "controller_abs_in_reported_units"), (("pending",), "modulation_abs_pu"),
                        (("p_ref_w", "q_ref_var"), "power_command_abs_w_or_var")):
        measurements.update({key: difference(candidate[key][1:], controller[key], limits[limit], angle=key=="theta_rad") for key in keys})
    for signal in power[0]:
        measurements[signal] = difference(power[0][signal][1:], power[1][signal][1:], limits["point_power_abs_w_or_var"])
    for key in ("p_w", "q_var", "storage_w"):
        measurements[f"candidate_meter_{key}"] = difference(candidate[f"measured_{key}"], power[0][key], limits["point_power_abs_w_or_var"])
    disagree = {key: int(np.count_nonzero(candidate[key][1:] != (native[key][1:] if key.endswith("_on") else controller[key])))
                for key in checks.DISCRETE}
    zero_keys = ("pll_integrator", "d_integrator", "q_integrator", "filtered_v", "ip_ref_a", "id_ref_a", "iq_ref_a", "applied", "pending")
    gates = {"clock": clock <= limits["clock_abs_s"], "initial_clock": candidate["time_s"][0] == native["time_s"][0] == 0,
             "initial_voltage": max(voltage_error, saved_row_error_v) <= limits["initial_voltage_abs_v"],
             "initial_current": max(current_error, saved_row_error_a) <= limits["initial_current_abs_a"],
             "initial_ac_zero_approximation": all(checks.peak(decoded[key]) <= initial["ac_inductor_snapshot_max_abs_a_for_zero_approximation"]
                 and np.all(candidate[key][0] == initial["ac_inductor_current_a"]) for key in ("feed_a", "phase_a")),
             "initial_source": np.all(candidate["source_v"][0] == initial["ac_source_v"]),
             "initial_controller": all(np.all(candidate[key][0] == initial["pll_integrator_current_pi_and_voltage_filters"]) for key in zero_keys)
                 and abs(candidate["theta_rad"][0]-initial["pll_angle_rad"]) <= limits["controller_abs_in_reported_units"]
                 and abs(candidate["omega_rad_s"][0]-initial["pll_omega_rad_per_s"]) <= limits["controller_abs_in_reported_units"],
             "initial_gates": all(not np.any(trace["upper_on"][0]) and np.all(trace["lower_on"][0]) for trace in (candidate, native)),
             "ocv_source": checks.peak(native["ocv_command_v"] - protocol["dc_circuit"]["ocv_v"]) <= limits["voltage_abs_v"],
             "discrete": all(value == limits["discrete_mismatches"] for value in disagree.values()),
             "continuous": all(record["passed"] for record in measurements.values())}
    return {"checks": {key: bool(value) for key, value in gates.items()}, "clock_maximum_s": clock,
            "initial": {"decoded_native": decoded, "candidate_voltage_error_v": voltage_error, "candidate_current_error_a": current_error,
                         "seed_row_voltage_error_v": saved_row_error_v, "seed_row_current_error_a": saved_row_error_a},
            "discrete_mismatches": disagree, "waveforms": measurements}


def plot_comparison(destination, curves):
    from matplotlib import pyplot as plt

    figure, axes = plt.subplots(3, 2, sharex=True, figsize=(11, 7), layout="constrained")
    for column, (grid, (time, candidate, native)) in enumerate(curves.items()):
        axes[0, column].set_title("5 µs" if grid == "5us" else "2.5 µs")
        stride = round(.001 / (time[1]-time[0]))
        ends = np.arange(stride, len(time), stride)
        for row, (key, label) in enumerate((("p_w", "PCC active power (W)"), ("bus_v", "DC bus (V)"), ("pol_v", "Polarization (V)"))):
            axis = axes[row, column]
            for series, name, style in ((native, "PSCAD", "-"), (candidate, "PyCy", "--")):
                values = series[key]
                if row == 0:
                    axis.plot(time[ends]*1000, np.mean(values[1:ends[-1]+1].reshape(-1, stride), axis=1), style, label=name)
                else:
                    axis.plot(time*1000, values, style, label=name, linewidth=.9)
            axis.set_ylabel(label)
            axis.grid(alpha=.25)
        axes[2, column].set_xlabel("Time since restart (ms)")
    axes[0, 0].legend()
    figure.savefig(destination, dpi=150)
    plt.close(figure)


def run_comparison(destination):
    protocol = frozen_json(PROTOCOL, PROTOCOL_SHA)
    records, evidence = protocol["sources"], {}
    native_record, contract_record = records["qualified_native"], records["native_protocol"]
    native_path, contract_path = ROOT / native_record["path"], ROOT / contract_record["path"]
    summary = frozen_json(native_path, native_record["sha256"])
    contract_sha = contract_record["sha256"]
    contract = frozen_json(contract_path, contract_sha)
    require(summary["status"] == "PASS_BOTH_NATIVE_STORAGE_GRID_LONG_GRIDS" and summary["protocol"] == records["native_protocol"],
            "The frozen PSCAD reference is not qualified")
    pair = read(record_path(summary["paired_audit"], evidence))
    require(pair["status"] == "PASS_NATIVE_D1_STORAGE_GRID_LONG_PAIR" and pair["protocol_sha256"] == contract_sha and passed(pair["checks"]),
            "The original native paired audit is not qualified")
    example = ROOT / protocol["example"]["path"]
    source = {PROTOCOL, example, native_path, contract_path, ROOT / "pyproject.toml", ROOT / "uv.lock",
              *(ROOT / "pycy_emt_lite").rglob("*.py"), *(ROOT / "validation").rglob("*.py")}
    frozen = snapshot_inputs(destination, source)
    head = subprocess.check_output(["git", "-c", f"safe.directory={ROOT.as_posix()}", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    archived = {name: reference_grid(summary, pair, name, contract, contract_sha, evidence) for name in GRIDS}
    manifest = destination / "inputs.json"
    save_json(manifest, {"git_head": head, "platform": platform.platform(), "python": platform.python_version(), "numpy": np.__version__,
                         "sources": frozen, "native_files": {path.relative_to(ROOT).as_posix(): sha for path, sha in evidence.items()}})
    factory = runpy.run_path(str(example))["define_case"]
    reports, windows, curves = {}, {}, {}
    for name in GRIDS:
        print(f"Comparing {name}", flush=True)
        grid = protocol["grids"][name]
        require(grid["step_s"] == contract["grids"][name]["step_s"]
                and grid["native_positive_rows"] == contract["grids"][name]["positive_continuation_rows"], "Native grid does not match candidate")
        archive, original_anchor, decoded, audited_anchor = archived[name]
        native, log = read_native(archive, original_anchor, grid, protocol)
        candidate = candidate_trace(factory, grid, protocol)
        powers = [checks.power(trace) for trace in (candidate, native)]
        validation = same_grid(candidate, native, log, decoded, audited_anchor, grid, protocol, powers)
        candidate_physics = checks.physics(candidate, grid["step_s"], protocol)
        native_physics = checks.physics(native, grid["step_s"], protocol)
        timing = checks.timing(candidate, grid["step_s"], protocol)
        (cw, candidate_signed), (nw, native_signed) = [checks.signed_windows(trace, series, grid["step_s"], protocol)
                                                      for trace, series in zip((candidate, native), powers, strict=True)]
        compare_window = {window: {key: difference(np.array([cw[window][key]]), np.array([nw[window][key]]),
                                     protocol["same_grid_limits"]["window_mean_power_abs_w_or_var"])
                                   for key in ("pcc_active_mean_w", "pcc_reactive_mean_var", "storage_absorbed_mean_w")}
                          for window in protocol["windows_s"]}
        ok = all(passed(value["checks"]) for value in (validation, candidate_physics, native_physics, timing)) and all(
            passed(value) for value in (candidate_signed, native_signed)) and all(
            metric["passed"] for values in compare_window.values() for metric in values.values())
        run = destination / name
        run.mkdir()
        outputs = {f"{role}_waveforms.npz": trace for role, trace in (("candidate", candidate), ("native", native))}
        for filename, trace in outputs.items():
            np.savez(run / filename, **trace)
        details = run / "report.json"
        save_json(details, {"passed": ok, "rows_including_initial": len(candidate["time_s"]), "native_positive_rows": grid["native_positive_rows"],
                            "same_grid": validation, "timing": timing, "candidate_physics": candidate_physics, "native_physics": native_physics,
                            "candidate_windows": cw, "native_windows": nw, "candidate_window_checks": candidate_signed,
                            "native_window_checks": native_signed, "same_grid_window_deltas": compare_window,
                            "waveforms_sha256": {filename: sha256(run / filename) for filename in outputs}})
        reports[name] = {"passed": ok, "report_sha256": sha256(details), "candidate_rows": len(candidate["time_s"]), "native_positive_rows": grid["native_positive_rows"]}
        windows[name] = cw, nw
        curves[name] = (candidate["time_s"], *({key: trace[key] for key in ("bus_v", "pol_v")} | power
                                              for trace, power in zip((candidate, native), powers, strict=True)))
    cross = {role: checks.cross_grid(windows["5us"][index], windows["2p5us"][index], protocol["cross_grid_window_limits"])
             for index, role in enumerate(("candidate", "native"))}
    require(all(sha256(ROOT / path) == sha for path, sha in frozen.items())
            and all(sha256(path) == sha for path, sha in evidence.items()), "Comparison inputs changed during execution")
    ok = all(entry["passed"] for entry in reports.values()) and all(passed(value["checks"]) for value in cross.values())
    report = {"passed": ok, "git_head": head, "protocol_sha256": PROTOCOL_SHA, "inputs_sha256": sha256(manifest),
              "reference_platform": "PSCAD 5.0.0 / EMTDC 5 / gf46 x86", "grids": reports, "cross_grid": cross}
    if ok:
        figure = destination / "waveform_overlay.png"
        plot_comparison(figure, curves)
        report["figure_sha256"] = sha256(figure)
    result = destination / "report.json"
    save_json(result, report)
    return result, ok


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, help="fresh directory under local_reference")
    args = parser.parse_args()
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    destination = (args.run_dir or CACHE / f"case35_comparison_{stamp}").resolve()
    require(destination != CACHE.resolve() and destination.is_relative_to(CACHE.resolve()), "Output must stay below local_reference")
    destination.mkdir(parents=True, exist_ok=False)
    try:
        report, ok = run_comparison(destination)
    except Exception as error:
        save_json(destination / "failure.json", {"passed": False, "exception": type(error).__name__, "message": str(error)})
        raise
    print(report, "PASS" if ok else "FAIL")
    return int(not ok)


if __name__ == "__main__":
    raise SystemExit(main())
