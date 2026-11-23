"""Read the qualified PSCAD long PV traces and their actual saved origin."""

import json
from pathlib import Path

import numpy as np

from validation.cases.grid_connected_vsc_closed_loop.compare import ROOT, frozen_json
from validation.cases.grid_connected_vsc_open_loop.metrics import require
from validation.cases.pjm5_load_step.compare import admit, record_path
from validation.cases.two_terminal_vsc_hvdc.compare import descriptors
from validation.common.runner import sha256

CACHE = ROOT / "local_reference"
STEM = "pv_grid"
WORK = "project/vdiv.gf46"
RECEIPT_STATUS = "NATIVE_D1_PV_GRID_CLOSED_FOR_NUMERIC_REVIEW"
GENERATED = ("Main.f", "Main.dta", "Station.f", "Station.dta")
PHASES = "abc"
NATIVE_FIELDS = {
    "bus_v": ("V_a_dc_kV",), "pv_a": ("I_pv_kA",), "bus_cap_a": ("I_Cdc_kA",),
    "load_a": ("I_Rdc_kA",), "auxiliary_a": ("I_pre_kA",), "star_v": ("V_a_star_kV",),
    "irradiance_w_m2": ("G_W_m2",),
    **{f"{key}_v": tuple(f"V_a_{p}_{port}_kV" for p in PHASES)
       for key, port in (("source", "grid"), ("pcc", "pcc"), ("pole", "pole"))},
    **{f"{key}_a": tuple(f"I_a_{p}_{port}_kA" for p in PHASES)
       for key, port in (("feed", "feeder"), ("phase", "phase"), ("upper", "upper"), ("lower", "lower"))},
    **{f"{side}_on": tuple(f"R_a_{p}_{side}_ohm" for p in PHASES) for side in ("upper", "lower")},
}


def read(path):
    return json.loads(path.read_bytes())


def tracked_record(record, evidence):
    """Use the canonical LF digest for repository text and record actual bytes."""
    path = (ROOT / record["path"]).resolve(strict=True)
    summary = frozen_json(path, record["sha256"])
    require(len(path.read_bytes().replace(b"\r\n", b"\n")) == record["bytes"], f"Input byte count differs: {path}")
    evidence[path] = sha256(path)
    return summary


def admit_run(record, grid, mode, native, protocol_sha, evidence):
    path = record_path(record, evidence)
    run, receipt = path.parent, read(path)
    profile, timing = native["grids"][grid], native["timeline"]
    seed = mode == "seed"
    count = profile["seed_rows_including_zero" if seed else "full_positive_rows"]
    log_count = profile["short_positive_rows" if seed else "full_positive_rows"]
    stop = timing["seed_stop_absolute_s" if seed else "full_restore_duration_s"]
    require(run.is_relative_to(CACHE.resolve()) and path.name == "snapshot_result.json"
            and (receipt["status"], receipt["grid"], receipt["variant"], receipt["mode"], receipt["stem"],
                 receipt["rows"], receipt["step_s"], receipt["stop_s"], receipt["absolute_snapshot_s"],
                 receipt["protocol_sha256"], receipt["generated_work"])
            == (RECEIPT_STATUS, grid, grid, mode, STEM, count, profile["step_s"], stop,
                timing["snapshot_absolute_s"], protocol_sha, WORK), "Wrong original native PV identity")
    files = receipt["files"]

    def bound(key):
        target = (run / key).resolve()
        require(target.is_relative_to(run), f"Original PV artifact escapes its run: {key}")
        return admit(target, files[key], evidence)

    terminal, worker, admission, inputs, claim = (read(bound(f"{name}.json")) for name in (
        "terminal", "worker", "pre_run_admission", "sealed_inputs", "execution_claim"))
    for name in ("terminal", "pre_run_admission", "sealed_inputs"):
        require(receipt[f"{name}_sha256"] == files[f"{name}.json"], f"Unbound native sidecar: {name}")
    require(terminal["worker_returncode"] == 0 and terminal["stop_reason"] is None
            and not terminal["remaining_owned"] and not terminal["cleanup"]
            and terminal["source_hash_unchanged"] and terminal["parent_environment_unchanged"]
            and set(terminal["final_pscad_pids"]) == set(terminal["existing_pscad_pids"])
            and worker["causal_build_admitted"] and worker["run_returned"] and worker["run_calls"] == 1
            and worker["build_errors"] == worker["build_warnings"] == 0
            and all(sum(event["stage"] == stage for event in worker["events"]) == 1 for stage in ("build", "run")),
            "Original PSCAD PV run did not finish one admitted solve")
    runtime = receipt["native_runtime"]
    stdout = bound("run_output.txt").read_text("utf-8")
    expected = native["native"]["toolchain"]
    require(all(runtime[key] == value for key, value in expected.items()) and runtime["emtdc_pid_observed"]
            and "Build# 20210219" in stdout and stdout.count("EMTDC run completed.") == 1
            and claim["protocol_sha256"] == protocol_sha and protocol_sha in inputs.values()
            and claim["launch_sha256"] == receipt["launch_sha256"], "Wrong original PSCAD toolchain or unsealed run")
    batch = (run / runtime["batch_path"]).resolve()
    require(receipt["snapshot_path"] == f"{WORK}/{STEM}.snp"
            and files[receipt["snapshot_path"]] == receipt["snapshot_sha256"]
            and batch.parent == run / WORK, "Unbound original snapshot or native launch batch")
    snapshot = bound(receipt["snapshot_path"])
    admit(batch, runtime["batch_sha256"], evidence)
    bound("project/vdiv.pscx")
    compiled = receipt["post_run_generated_sha256"]
    require(set(GENERATED) | {"vdiv.map", "vdiv.exe", "vdiv.mak"} <= compiled.keys(), "Incomplete native compilation")
    for name, digest in compiled.items():
        require(Path(name).name == name and files[f"{WORK}/{name}"] == digest,
                f"Unbound generated PV file: {name}")
        if name not in ("vdiv.map", "vdiv.exe"):
            require(admission["generated_sha256"][name] == digest, f"Native generated content changed: {name}")
        bound(f"{WORK}/{name}")
    raw = receipt["raw_files_sha256"]
    require(set(raw) == {f"{STEM}.inf", *(f"{STEM}_{shard:02}.out" for shard in range(1, 6))},
            "Incomplete original PV raw files")
    for name, digest in raw.items():
        require(files[f"{WORK}/{name}"] == digest, f"Unbound native raw file: {name}")
        bound(f"{WORK}/{name}")
    log, columns = receipt["native_logs"]["a"], receipt["native_log_columns"]
    require(set(receipt["native_logs"]) == {"a"} and (log["file"], log["rows"], log["columns"], len(set(columns)))
            == ("pv_grid_station.log", log_count, 43, 43)
            and log["sha256"] == files[f'{WORK}/{log["file"]}'], "Wrong native PV controller log ABI")
    bound(f'{WORK}/{log["file"]}')
    proof = admission["proof"]
    require((proof["status"], proof["grid"], proof["stage"], proof["physical_branches"])
            == ("PASS_NATIVE_D1_PV_GRID_COMPILED_ADMISSION", grid, mode, 20)
            and proof["controller_state_totals"] == {"real": 25, "integer": 1}
            and proof["log_columns"] == columns
            and admission["native_pgb_layout"] == receipt["native_pgb_layout"], "Wrong admitted PV electrical model")
    if not seed:
        require(inputs[f"{STEM}.snp"] == admission["snapshot_before_run_sha256"] == receipt["snapshot_sha256"]
                and inputs["seed_snapshot_result.json"] == admission["seed_receipt_sha256"] == receipt["seed_receipt_sha256"],
                "Restore did not retain its admitting snapshot and seed")
        for key in (f"{STEM}.snp", "seed_snapshot_result.json"):
            admit(run / "input_snapshot" / key, inputs[key], evidence)
    return run / WORK, receipt, proof, snapshot


def read_shards(work, receipt, units, *, snapshot_tick=None):
    names = [entry["name"] for entry in receipt["native_pgb_layout"]]
    layout = descriptors((work / f"{STEM}.inf").read_text("ascii").splitlines())
    mapping = (work / "vdiv.map").read_text("ascii").splitlines()
    require(mapping.count("PGBList:") == 1, "Missing unambiguous native PGB list")
    start = mapping.index("PGBList:") + 1
    require(len(names) == len(set(names)) == len(units) == 43
            and {item["name"]: item["unit"] for item in layout} == units
            and all(item["group"] == "PVGrid" for item in layout)
            and layout == receipt["native_pgb_layout"] == descriptors(mapping[start:start+43]), "Wrong native PV signal layout")
    shards = [work / f"{STEM}_{part:02}.out" for part in range(1, 6)]
    require(set(work.glob(f"{STEM}_*.out")) == set(shards), "Missing or additional native PV output shards")
    values, display = {}, None
    count = receipt["rows"] if snapshot_tick is None else 1
    for part, path in enumerate(shards):
        group = names[part*10:(part+1)*10]
        data = np.loadtxt(path, ndmin=2, skiprows=1 + (snapshot_tick or 0),
                          max_rows=None if snapshot_tick is None else 1)
        require(data.shape == (count, len(group)+1) and np.isfinite(data).all(), f"Malformed native PV shard: {path.name}")
        if display is None:
            display = data[:, 0].copy()
        else:
            require(np.array_equal(display, data[:, 0]), f"Native PV shard clocks differ: {path.name}")
        values.update({name: data[:, i].copy() for i, name in enumerate(group, 1)})
    return display, values


def saved_state(path, proof, profile, anchor, origin, ac, tolerance):
    """Read the capacitor, current history and gate words from the admitted snapshot."""
    lines = path.read_text("ascii").splitlines()

    def number(text):
        return float(text.replace("D", "E"))

    require(lines[0] == "! EMTDC SNAP-SHOT - Version, Time, Delt"
            and tuple(map(number, lines[1].split())) == (5., origin, profile["step_s"]), "Wrong saved native clock")
    count = proof["generated_branches"]
    branches = proof["snapshot_index"]["branches"]

    def vector(tag):
        starts = [i for i, row in enumerate(lines) if row.strip() == tag]
        require(len(starts) == 1, f"Missing or duplicate native snapshot vector {tag}")
        values = []
        for row in lines[starts[0]+1:]:
            if row.lstrip().startswith("!") or len(values) == count:
                break
            values.extend(map(number, row.split()))
        require(len(values) == count and np.isfinite(values).all(), f"Wrong native snapshot width for {tag}")
        return values

    def state(values, name, *, oriented=True):
        branch = branches[name]
        index, direction = branch["index"], branch["orientation"]
        require(branch["subsystem"] == 1 and 0 < index <= count and direction in (-1, 1),
                f"Invalid native saved index for {name}")
        return values[index-1] * (direction if oriented else 1)

    volt, current, resistance = (vector(tag) for tag in ("!V20L", "!CBR", "!BRANCH_R"))
    voltage = 1000 * state(volt, "I_Cdc_kA")
    require(abs(voltage - profile["initial_bus_v"]) <= tolerance["bus_snapshot_tolerance_v"]
            and abs(voltage - 1000*anchor["V_a_dc_kV"]) <= tolerance["bus_snapshot_tolerance_v"],
            "Stored native bus voltage differs from origin")
    for name, expected in (("I_pv_kA", profile["native_initial_pv_current_a"]),
                           ("I_Cdc_kA", profile["native_initial_capacitor_current_a"])):
        observed = 1000 * state(current, name)
        require(max(abs(observed - expected), abs(observed - 1000*anchor[name])) <= tolerance[
                    "ac_current_snapshot_tolerance_a"], f"Stored native current differs for {name}")
    reactors = [f"I_a_{p}_{port}_kA" for p in PHASES for port in ("phase", "feeder")]
    require(max(abs(1000*state(current, name)) for name in reactors) <= tolerance["native_parked_current_approximation_bound_a"]
            and all(abs(1000*(state(current, name)-anchor[name])) <= tolerance["ac_current_snapshot_tolerance_a"]
                    for name in reactors), "Wrong parked native inductive state")
    for p in PHASES:
        for side, opened in (("upper", True), ("lower", False)):
            name = f"I_a_{p}_{side}_kA"
            expected = ac["bridge_open_ohm" if opened else "bridge_closed_ohm"]
            require(state(resistance, name, oriented=False) == anchor[f"R_a_{p}_{side}_ohm"] == expected,
                    "Wrong parked native gate word")
    require(state(resistance, "I_pre_kA", oriented=False) == anchor["Rpre_command_ohm"] == 1e9,
            "Saved native auxiliary branch should be open")


def read_reference(protocol, grid, evidence):
    """Return a same-grid SI trace and add its admitted original input digests."""
    sources = protocol["sources"]
    native, activation, qualified = (tracked_record(sources[name], evidence) for name in (
        "native_protocol", "native_activation", "qualified_native"))
    protocol_sha = sources["native_protocol"]["sha256"]
    require(qualified["status"] == "PASS_NATIVE_D1_PV_GRID_LONG_PAIR"
            and activation["status"] == "PASS_NATIVE_D1_PV_GRID_SHORT_PAIR"
            and qualified["protocol"] == activation["protocol"] == sources["native_protocol"]
            and qualified["qualified_activation"] == sources["native_activation"], "Unqualified PV reference")
    pair = read(record_path(qualified["paired_audit"], evidence))
    item, active = qualified["grids"][grid], activation["grids"][grid]
    review = read(record_path(item["audit"], evidence))
    original_seed = active["native_runs"]["seed"]["receipt"]
    original_long = item["original_long_run"]["receipt"]
    require(pair["status"] == qualified["status"] and pair["protocol_sha256"] == protocol_sha
            and pair["grid_reports"][grid]["sha256"] == item["audit"]["sha256"]
            and (review["status"], review["grid"], review["protocol_sha256"])
            == ("PASS_NATIVE_D1_PV_GRID_LONG", grid, protocol_sha)
            and review["seed"]["native_receipt"]["sha256"] == original_seed["sha256"]
            and review["long"]["native_receipt"]["sha256"] == original_long["sha256"], "Native PV audit and archives differ")
    seed_work, seed, proof, snapshot = admit_run(original_seed, grid, "seed", native, protocol_sha, evidence)
    work, restored, _, _ = admit_run(original_long, grid, "long", native, protocol_sha, evidence)
    require(seed["snapshot_sha256"] == restored["snapshot_sha256"] == item["original_long_run"]["snapshot_sha256"]
            == review["seed"]["snapshot"]["native_snapshot"]["sha256"]
            and restored["seed_receipt_sha256"] == original_seed["sha256"]
            and seed["native_pgb_layout"] == restored["native_pgb_layout"]
            and all(seed["post_run_generated_sha256"][file] == restored["post_run_generated_sha256"][file]
                    == review["compiled_identity"][file] for file in GENERATED), "Restored PSCAD PV differs from its seed")
    units = {name: name.rsplit("_", 1)[-1] for names in NATIVE_FIELDS.values() for name in names}
    units |= native["outputs"]["dc_solved"] | native["outputs"]["control_commands"] | {
        "Absolute_TIME_s": "s", **{f"Ref_a_{p}_pu": "pu" for p in PHASES}}
    seed_time, seed_row = read_shards(seed_work, seed, units, snapshot_tick=native["grids"][grid]["snapshot_tick"])
    anchor = {name: row[0] for name, row in seed_row.items()}
    require({**anchor, "display_TIME_s": seed_time[0]} == {name: float(value) for name, value in seed["snapshot_row"].items()},
            "Original native zero row differs from admitted seed sample")
    profile, origin = protocol["grids"][grid], protocol["example"]["native_snapshot_s"]
    limits, ac = protocol["initial_state"], protocol["ac_circuit"]
    saved_state(snapshot, proof, profile, anchor, origin, ac, limits)
    display, data = read_shards(work, restored, units)
    count, h = profile["native_positive_rows"], profile["step_s"]
    ticks = np.arange(1, count+1)
    clock = protocol["physical_limits"]["clock_abs_s"]
    require(len(display) == count and max(abs(seed_time[0]-origin), abs(anchor["Absolute_TIME_s"]-origin),
                np.max(np.abs(display - ticks*h)), np.max(np.abs(data["Absolute_TIME_s"] - origin - display))) <= clock,
            "Native PSCAD absolute and display clocks differ from frozen integer ticks")
    schedule = protocol["schedule"]
    edge = round(schedule["irradiance_step_s"]/h)
    require(anchor["G_W_m2"] == schedule["irradiance_w_m2"][0] and np.array_equal(
        data["G_W_m2"], np.where(ticks < edge, *schedule["irradiance_w_m2"])), "Wrong original native illumination edge")
    table = np.loadtxt(work / "pv_grid_station.log", delimiter=",")
    require(table.shape == (count, 43) and np.isfinite(table).all(), "Malformed native PV controller table")
    columns = dict(zip(restored["native_log_columns"], table.T, strict=True))
    require(np.array_equal(columns["j"], ticks) and np.max(np.abs(columns["time_s"]-data["Absolute_TIME_s"])) <= clock
            and np.array_equal(columns["inner_tick"], ticks % round(schedule["inner_period_s"]/h) == 0)
            and np.array_equal(columns["outer_tick"], ticks % round(schedule["outer_period_s"]/h) == 0),
            "Original native controller clock or integer sample events differ")

    # The native source and PCC PGBs are differential voltmeters against the floating star.
    trace = {"time_s": np.r_[float(seed_time[0]) - origin, display]}
    for key, names in NATIVE_FIELDS.items():
        values = [np.r_[anchor[name], data[name]] * (1000 if name.endswith(("_kV", "_kA")) else 1) for name in names]
        trace[key] = values[0] if len(values) == 1 else np.column_stack(values)
    for key in ("upper_on", "lower_on"):
        on, off = ac["bridge_closed_ohm"], ac["bridge_open_ohm"]
        require(np.isin(trace[key], (on, off)).all(), "Unknown native PV switch word")
        trace[key] = trace[key] == on
    require(np.array_equal(trace["upper_on"], ~trace["lower_on"]) and np.max(np.abs(trace["auxiliary_a"])) <= 1e-8,
            "Native gates or parked auxiliary leakage differ")
    return trace
