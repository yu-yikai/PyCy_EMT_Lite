"""Run example 29 and compare with four qualified PSCAD archives.

Use `python -m validation.cases.grid_connected_vsc_closed_loop.compare`.
The comparison reads archived native results and starts no vendor process.
"""

import argparse
import itertools
import json
import platform
import runpy
import shutil
import subprocess
from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal, localcontext
from hashlib import sha256 as hash_bytes
from math import pi, sqrt
from pathlib import Path
from time import monotonic

import matplotlib
import numpy as np

from pycy_emt_lite import OutputOptions, run_case
from validation.cases.grid_connected_vsc_open_loop import binding, metrics, physics
from validation.cases.grid_connected_vsc_open_loop.compare import (
    PlantRows,
    Projection,
    save_json,
    write_plant,
)
from validation.common.runner import sha256

ROOT = Path(__file__).resolve().parents[3]
DIRECTORY = Path(__file__).resolve().parent
RESEARCH = ROOT / "local_reference/native_static_reviews"
EXAMPLE = ROOT / "examples/29_grid_connected_vsc_closed_loop.py"
PROTOCOL_SHA = "53c1eb1c237fc4bd78ff83feb614023fc7d06b4b1700e7df09e1cd4de8236f06"
QUALIFICATION_SHA = "ef609369fe275a96af667023c44a9b418a31d750b041d88109eb41851c0550cd"
TIME = "TIME_native_s"
CURRENTS = tuple(f"I_{phase}_ac_to_bridge_kA" for phase in "abc")
VOLTAGES = tuple(f"V_{phase}_grid_kV" for phase in "abc")
DISCRETE = tuple(name for name in physics.names() if name.startswith(("applied_g_", "R_")))
ANALOG = tuple(name for name in physics.names() if name not in (*DISCRETE, TIME))
FAMILIES = {
    **{name: ("grid_abc_V" if "_grid_" in name else "iabc_and_fresh_Jdc_A" if name.startswith("I_")
              else "all_other_plant_voltages_V") for name in ANALOG},
    **dict.fromkeys(("Pg", "Qg", "Pdc"), "Pg_Qg_Pdc_W"),
    "W": "energy_J",
}


def windows(case):
    boundaries = case["window_boundaries_s"]
    return [(boundaries[0], boundaries[-1]), *itertools.pairwise(boundaries)]


def cycles(start, count, frequency):
    return [(start + k / frequency, start + (k + 1) / frequency) for k in range(count)]


def cycle_means(time, values, interval):
    return [float(metrics.mean(*metrics.clip(time, signal, *interval))) for signal in values]


def rotating_frame(data, names, frequency):
    time = data[TIME]
    angles = (2 * pi * frequency * time - pi / 2) + np.array([0., -2*pi/3, 2*pi/3])[:, None]
    phase_values = np.stack([data[key] for key in names])
    return (2 / 3) * np.stack([np.sum(phase_values * np.cos(angles), axis=0),
                                -np.sum(phase_values * np.sin(angles), axis=0)])


def native_dq(data, frequency):
    return rotating_frame(data, CURRENTS, frequency)


def tracking(data, protocol, case):
    frequency = protocol["grid_frequency_Hz"]
    dq = native_dq(data, frequency)
    power = metrics.snapshots(data)
    result = []
    for interval in cycles(case["tracking_start_s"], protocol["tracking_cycles"], frequency):
        mean = cycle_means(data[TIME], dq, interval)
        errors = [abs(actual - target) for actual, target in zip(mean, case["tracking_target_A"], strict=True)]
        means = {key: cycle_means(data[TIME], [power[key]], interval)[0] for key in ("Pg", "Qg", "Pdc")}
        passed = max(errors) <= protocol["tracking_error_limit_A"]
        passed &= all(means[key] * sign > 0 for key, sign in case["tracking_power_signs"].items())
        result.append({"interval_s": interval, "mean_dq_A": mean, "tracking_error_A": errors, "mean_power_W": means, "passed": passed})
    return result


def same_step(left, right, step, intervals, limits, *, compare_saturation=True):
    metrics.require(left[TIME].shape == right[TIME].shape and np.max(np.abs(left[TIME] - right[TIME])) <= 4e-12,
                    "Same-step original clocks differ")
    first, second = ({**data, **metrics.snapshots(data)} for data in (left, right))
    result = []
    for start, end in intervals:
        lo, hi = round(start / step), round(end / step)
        metrics.require(0 <= lo < hi < len(left[TIME]), "Same-step indices outside acquisition")
        time = np.arange(lo, hi+1) * step
        sample = slice(lo, hi+1)
        checks = {}
        for key, family in FAMILIES.items():
            error = first[key][sample] - second[key][sample]
            stats = {"max_abs": float(np.max(np.abs(error))), "PWL_RMSE_abs": sqrt(metrics.square_mean(time, error))}
            checks[key] = metrics.continuous_gate(stats, limits[family])
        exact = {key: bool(np.array_equal(left[key][sample], right[key][sample])) for key in DISCRETE}
        if compare_saturation:
            exact["saturated"] = bool(np.array_equal(left["saturated"][sample], right["saturated"][sample]))
        result.append({"interval_s": [start, end], "rows": len(time), "metrics": checks, "exact": exact,
                           "passed": all(v["passed"] for v in checks.values()) and all(exact.values())})
    return result


def cross_step(coarse, fine, protocol, case):
    clock_coarse, clock_fine = coarse[TIME], fine[TIME]
    metrics.require(clock_fine[::2].shape == clock_coarse.shape
                    and np.max(np.abs(clock_fine[::2] - clock_coarse)) <= 4e-12, "Cross-step shared clocks differ")
    frequency = protocol["grid_frequency_Hz"]
    dc, df = native_dq(coarse, frequency), native_dq(fine, frequency)
    pc, pf = metrics.snapshots(coarse), metrics.snapshots(fine)
    limits = protocol["cross_step"]
    waveforms, means = [], []
    for start, end in windows(case):
        dq = [metrics.difference(clock_coarse, a, clock_fine, b, start, end) for a, b in zip(dc, df, strict=True)]
        phase = [{name: metrics.features(data[TIME], data[name], start, end) for name in CURRENTS}
                 for data in (coarse, fine)]
        power = [{key: float(metrics.mean(*metrics.clip(data[TIME], p[key], start, end))) for key in ("Pg", "Qg", "Pdc")}
                 for data, p in ((coarse, pc), (fine, pf))]
        waveforms.append({"interval_s": [start, end], "dq": dq, "phase_current": phase, "power_means_W": power,
                              "passed": all(s["PWL_RMSE_abs"] <= limits["dq_pwl_RMS_difference_limit_A"] for s in dq)})
    cycle_windows = cycles(0, round(protocol["formal_stop_s"] * frequency), frequency)
    cycle_windows += cycles(case["tracking_start_s"], protocol["tracking_cycles"], frequency)
    for interval in cycle_windows:
        a, b = cycle_means(clock_coarse, dc, interval), cycle_means(clock_fine, df, interval)
        change = [abs(x - y) for x, y in zip(a, b, strict=True)]
        means.append({"interval_s": interval, "mean_difference_A": change,
                          "passed": max(change) <= limits["cycle_mean_dq_difference_limit_A"]})
    unequal = np.stack([coarse[f"applied_g_{p}_u"] != fine[f"applied_g_{p}_u"][::2] for p in "abc"])
    return {"waveforms": waveforms, "means": means, "shared_gate_difference_rows": int(np.count_nonzero(np.any(unequal, axis=0))),
                "passed": all(check["passed"] for check in (*waveforms, *means))}


def paired_scenarios(main, d_only, protocol, step, limits):
    scenario = protocol["scenarios"]["main"]
    previous_index = round(protocol["paired_scenarios"]["q_application_s"] / step) - 1
    prefix = same_step(main, d_only, step, [(0., previous_index * step)], limits, compare_saturation=False)
    frequency = protocol["grid_frequency_Hz"]
    first, second = (native_dq(data, frequency) for data in (main, d_only))
    effect = []
    for interval in cycles(scenario["tracking_start_s"], protocol["tracking_cycles"], frequency):
        a, b = cycle_means(main[TIME], first, interval), cycle_means(d_only[TIME], second, interval)
        change = [x - y for x, y in zip(a, b, strict=True)]
        expected_q = scenario["tracking_target_A"][1]
        passed = max(abs(change[0]), abs(change[1] - expected_q)) <= protocol["tracking_error_limit_A"]
        effect.append({"interval_s": interval, "main_minus_d_only_A": change, "passed": passed})
    return {"prefix": prefix, "effect": effect, "passed": all(check["passed"] for check in (*prefix, *effect))}


def frozen_json(path, expected):
    """Allow checkout line endings in tracked JSON, retaining its LF digest."""
    content = path.read_bytes().replace(b"\r\n", b"\n")
    metrics.require(hash_bytes(content).hexdigest() == expected, f"Frozen input changed: {path}")
    return json.loads(content)


def check_clock(data, grid):
    rows = grid["rows"]
    metrics.require(all(v.shape == (rows,) and np.isfinite(v).all() for v in data.values()),
                    "Incomplete or nonfinite acquisition")
    time = data[TIME]
    nominal = np.arange(rows) * grid["step_s"]
    metrics.require(time[0] == 0 and np.all(np.diff(time) > 0)
                    and np.max(np.abs(time - nominal)) <= 2e-12, "Original electrical clock differs")


def load_reference(protocol, qualification):
    """Admit the raw PSCAD runs and their independently checked SI projections."""
    metrics.require(qualification["whole_native_reference_qualified"] is True, "Native set is not qualified")
    native, inputs = {}, {}

    def admit(path, expected, size=None):
        path = path.resolve(strict=True)
        metrics.require(path.is_relative_to(RESEARCH.resolve()) and path not in inputs,
                        f"Invalid or reused archive path: {path}")
        metrics.require((size is None or path.stat().st_size == size) and sha256(path) == expected,
                        f"Changed native archive: {path}")
        inputs[path] = expected
        return path

    def receipt(record):
        path = admit(ROOT / record["path"], record["sha256"], record["bytes"])
        return path, json.loads(path.read_bytes())

    stem = protocol["native_output"]["stem"]
    expected_raw = {f"{stem}.inf", protocol["native_output"]["feedback"],
                    *(f"{stem}_{part:02d}.out" for part in range(1, 6))}
    runs = qualification["native_runs"]
    for scenario in protocol["scenarios"]:
        for grid in protocol["electrical_grids"]:
            label, rows = grid["id"], grid["rows"]
            run = runs[f"{scenario}_{label}"]
            execution_path, execution = receipt(run["native_execution"])
            terminal_path, terminal = receipt(run["terminal"])
            admission_path, admission = receipt(run["generated_admission"])
            review_path, review = receipt(run["independent_numeric"])
            source_run = execution_path.parent
            worker = json.loads(admit(source_run / "worker.json", execution["worker_sha256"]).read_bytes())
            metrics.require(
                terminal_path.parent == admission_path.parent == source_run
                and execution["terminal_sha256"] == run["terminal"]["sha256"]
                and execution["pre_run_admission_sha256"] == run["generated_admission"]["sha256"]
                and execution["status"] == "NATIVE_RUN_CLOSED_FOR_NUMERIC_REVIEW"
                and execution["protocol_sha256"] == PROTOCOL_SHA
                and (execution["scenario"], execution["grid"], execution["rows"]) == (scenario, label, rows)
                and execution["all_out_clocks_exact_on_original_grid"] is True
                and float(execution["feedback_clock_max_error_s"]) <= 2e-12
                and execution["post_run_audit"]["status"].startswith("PASS_")
                and admission["status"].startswith("PASS")
                and execution["native_emtdc_process_identity"]["name"].lower() == "vdiv.exe"
                and terminal["worker_returncode"] == 0 and terminal["stop_reason"] is None
                and not terminal["remaining_owned"] and terminal["source_hash_unchanged"] is True
                and worker["stage"] == "finished" and worker["causal_build_admitted"] is True
                and worker["run_calls"] == 1 and worker["run_returned"] is True and worker["build_errors"] == 0,
                f"Native build, run and terminal evidence differs: {scenario}_{label}",
            )
            # The worker recorded an absolute Windows path. Resolve its sealed
            # run-relative location so a local archive can move with the project.
            archive = source_run / "project/vdiv.gf46"
            recorded_archive = worker["temp_folder"].replace("\\", "/").rstrip("/")
            metrics.require(recorded_archive.endswith("/" + archive.relative_to(RESEARCH).as_posix()),
                            f"Native worker archive location differs: {source_run}")
            raw = execution["raw_files"]
            metrics.require(set(raw) == expected_raw, "Expected one INF, five OUTs and the feedback log")
            for name, digest in raw.items():
                admit(archive / name, digest)
            metrics.require(
                review["status"] == "ACTUAL_LONG_SINGLE_RUN_PASS"
                and review["protocol_sha256"] == PROTOCOL_SHA
                and review["execution_receipt_sha256"] == run["native_execution"]["sha256"]
                and (review["scenario"], review["grid"], review["rows"]) == (scenario, label, rows)
                and float(review["step_s"]) == grid["step_s"]
                and review["source_raw_files"] == raw
                and review["physical"]["observed_pass"] is True and review["physical"]["failure_count"] == 0
                and review["feedback"]["updates"] == run["updates"]
                and review["feedback"]["next_gate_applications"] == run["gate_applications"]
                and review["feedback"]["half_steps_held"] == run["fine_half_steps_held"]
                and review["tracking"]["passed"] is True,
                f"Independent numerical receipt differs: {scenario}_{label}",
            )
            archive_path = admit(review_path.parent / "plant32_si_with_saturation.npz", review["si_npz_sha256"])
            with np.load(archive_path, allow_pickle=False) as saved:
                data = {name: saved[name] for name in (*physics.names(), "saturated")}
            check_clock(data, grid)
            native[scenario, label] = data
    metrics.require(len(native) == len(runs), "Unexpected native variants")
    return native, inputs


def check_feedback(data, observed, protocol, scenario, grid):
    """Recompute the controller from solved voltages and currents."""
    settings = protocol["controller"]
    plant = protocol["plant"]
    case = protocol["scenarios"][scenario]
    h = grid["step_s"]
    rows = np.arange(grid["rows"])
    sample_period, gate_period = settings["sample_period_s"], settings["gate_period_s"]
    per_sample, per_gate = round(sample_period / h), round(gate_period / h)
    updates = rows[per_sample::per_sample]
    application = updates + per_gate
    gate_tick = rows // per_gate
    carrier_ticks = round(1 / (gate_period * settings["carrier_Hz"]))
    shift = round(settings["carrier_shift_s"] / gate_period)
    carrier_phase_tick = (gate_tick + shift) % carrier_ticks
    carrier = 1 - 4 * np.abs(carrier_phase_tick - carrier_ticks / 2) / carrier_ticks
    frequency = protocol["grid_frequency_Hz"]
    angle = 2*pi*frequency*data[TIME] - pi/2
    voltages = rotating_frame(data, VOLTAGES, frequency).T
    currents = native_dq(data, frequency).T
    command = np.zeros((len(updates) + 1, 2))
    for column, axis in enumerate("dq"):
        step = case["command_steps"][axis]
        if step is not None:
            command[1:, column] = np.where(updates >= round(step["time_s"] / h), step["current_A"], 0)

    # Zero is the initial state. Each following slot is one accepted sample.
    integrals = np.zeros_like(command)
    pending = np.zeros((len(command), 3))
    saturated = np.zeros(len(command), dtype=bool)
    kp = plant["series_L_H"] * 2*pi*100
    ki = plant["series_R_ohm"] * 2*pi*100
    coupling = 2*pi*frequency * plant["series_L_H"]
    limit = settings["bridge_vector_limit_V"]
    phase_angles = np.array([0, -2*pi/3, 2*pi/3])
    for slot, row in enumerate(updates, start=1):
        error = command[slot] - currents[row]
        trial = integrals[slot-1] + ki*sample_period*error
        current_d, current_q = currents[row]
        voltage_d, voltage_q = voltages[row] + coupling*np.array([current_q, -current_d]) - (kp*error + trial)
        norm = np.hypot(voltage_d, voltage_q)
        saturated[slot] = norm > limit
        integrals[slot] = integrals[slot-1] if saturated[slot] else trial
        scale = min(1., limit/norm) if norm else 1.
        angles = angle[row] + phase_angles
        pending[slot] = scale * (voltage_d*np.cos(angles) - voltage_q*np.sin(angles)) / (plant["dc_V"]/2)

    held_sample = np.searchsorted(updates, rows, side="right")
    held_application = np.searchsorted(application, rows, side="right")
    applied = np.column_stack([observed[f"applied_{phase}"] for phase in "abc"])
    reported_pending = np.column_stack([observed[f"pending_{phase}"] for phase in "abc"])
    exact = {
        "j": rows,
        "sample_update": np.isin(rows, updates),
        "gate_tick": gate_tick,
        "id_ref": command[held_sample, 0],
        "iq_ref": command[held_sample, 1],
        "saturated": saturated[held_sample],
    }
    for name, expected in exact.items():
        metrics.require(np.array_equal(observed[name], expected), f"Feedback clock/state differs: {name}")
    metrics.require(observed["z_d"][0] == observed["z_q"][0] == 0
                    and np.array_equal(reported_pending[0], [0, 0, 0]), "Initial feedback state differs")
    metrics.require(np.array_equal(reported_pending, reported_pending[np.r_[0, updates][held_sample]])
                    and np.array_equal(applied, reported_pending[np.r_[0, updates][held_application]]),
                    "Pending or actually applied reference was not held on its original clock")
    samples = {
        "carrier_applied": (carrier, 1e-12),
        "theta": (angle, 1e-12),
        "ed": (voltages[:, 0], 1e-12),
        "eq": (voltages[:, 1], 1e-12),
        "id": (currents[:, 0], 1e-12),
        "iq": (currents[:, 1], 1e-12),
        "z_d": (integrals[held_sample, 0], 1e-10),
        "z_q": (integrals[held_sample, 1], 1e-10),
        **{f"pending_{phase}": (pending[held_sample, index], 1e-12) for index, phase in enumerate("abc")},
    }
    max_errors = {}
    for name, (expected, tolerance) in samples.items():
        error = float(np.max(np.abs(observed[name] - expected)))
        metrics.require(error <= tolerance, f"Feedback {name} error {error:g} exceeds {tolerance:g}")
        max_errors[name] = error
    # Use the independently checked, actually held references for exact PWM ties.
    upper = applied >= carrier[:, None]
    for index, phase in enumerate("abc"):
        for side, bits in (("u", upper[:, index]), ("l", ~upper[:, index])):
            metrics.require(np.array_equal(data[f"applied_g_{phase}_{side}"], bits)
                            and np.array_equal(data[f"R_{phase}_{side}_ohm"],
                                               np.where(bits, plant["switch_Ron_ohm"], plant["switch_Roff_ohm"])),
                            f"Applied gate/resistance differs: {phase} {side}")
    witnesses = [0, len(rows)-1]
    for time in (sample_period, .04, .08, protocol["formal_stop_s"]):
        sample = round(time/h)
        witnesses.extend(range(sample, sample + per_gate + 1))
    return upper, {
        "updates": len(updates),
        "next_gate_applications": int(np.count_nonzero(application < len(rows))),
        "half_steps_held": int(np.count_nonzero(rows % per_gate)),
        "saturated_updates": int(np.count_nonzero(saturated)),
        "max_abs_errors": max_errors,
        "witnesses": [
            {"row": row, "time_s": data[TIME][row], "update": bool(observed["sample_update"][row]),
             "pending": reported_pending[row].tolist(), "applied": applied[row].tolist(), "upper": upper[row].tolist()}
            for row in sorted(set(witnesses))
        ],
    }



def run_candidate(factory, destination, protocol, plant_protocol, scenario, grid):
    """Run the public example on a fresh circuit, including the acquisition tail."""
    start = monotonic()
    case = factory(scenario=scenario, time_step=grid["step_s"], stop_time=protocol["acquisition_stop_s"])
    case = replace(case, output=OutputOptions(show_figure=False), summary=None, plots=())
    result = run_case(case)
    plant = binding.plant_data(result, case.components)
    controller_columns = (
        "j", "sample_update", "gate_tick", "ed", "eq", "id", "iq", "id_ref", "iq_ref", "theta",
        "carrier_applied", "saturated", "z_d", "z_q",
        *(f"{state}_{phase}" for state in ("applied", "pending") for phase in "abc"),
    )
    feedback = {name: result.series(name) for name in controller_columns}
    check_clock({**plant, **feedback}, grid)
    trace_file = destination / "waveforms.npz"
    np.savez(trace_file, **plant, **feedback)
    upper, clock = check_feedback(plant, feedback, protocol, scenario, grid)
    plant_path = destination / "plant32.csv"
    write_plant(plant_path, plant)
    rows = PlantRows(plant_path, grid["rows"], physics.names())
    with localcontext() as context:
        context.prec = 70
        physical = physics.evaluate(
            Projection(rows, 0), Projection(rows, 1), h=Decimal(str(grid["step_s"])), expected_rows=grid["rows"],
            limits=plant_protocol["physical_residual_budgets"],
            precision_caps=plant_protocol["printed_precision_caps_SI"], upper_states=upper,
        )
    data = {**plant, "saturated": feedback["saturated"]}
    track = tracking(data, protocol, protocol["scenarios"][scenario])
    report = {
        "scenario": scenario,
        "grid": grid,
        "feedback": clock,
        "physical": physical,
        "tracking": track,
        "passed": physical["observed_pass"] and all(check["passed"] for check in track),
        "elapsed_s": monotonic()-start,
        "artifacts": {path.name: sha256(path) for path in (trace_file, plant_path)},
    }
    save_json(destination / "report.json", report)
    return data, report


def snapshot_sources(destination, plant_protocol_path):
    sources = [
        EXAMPLE, Path(__file__).resolve(), plant_protocol_path,
        DIRECTORY / "reference_protocol.json", DIRECTORY / "qualified_reference_report.json",
        *(ROOT / name for name in ("pyproject.toml", "uv.lock")),
        *(ROOT / "pycy_emt_lite").rglob("*.py"),
        *(ROOT / "validation/common").rglob("*.py"),
        *(ROOT / "validation/cases/grid_connected_vsc_open_loop").rglob("*.py"),
    ]
    bindings = {}
    for source in sorted(sources):
        relative = source.relative_to(ROOT)
        target = destination / "inputs" / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        bindings[relative.as_posix()] = sha256(target)
        metrics.require(sha256(source) == bindings[relative.as_posix()], f"Candidate source changed: {relative}")
    return bindings


def plot_comparison(destination, candidate, native, protocol):
    matplotlib.use("Agg")
    from matplotlib import pyplot as plt

    figure, axes = plt.subplots(2, 2, sharex=True, sharey=True, layout="constrained", figsize=(11, 7))
    colors = ("#176581", "#aa4b2b")
    for row, scenario in enumerate(protocol["scenarios"]):
        for col, grid in enumerate(protocol["electrical_grids"]):
            label = grid["id"]
            axis = axes[row, col]
            for traces, platform_name, style in ((candidate, "PyCy", "-"), (native, "PSCAD", "--")):
                data = traces[scenario, label]
                for key, signal, color in zip("dq", native_dq(data, protocol["grid_frequency_Hz"]), colors, strict=True):
                    axis.plot(1000*data[TIME], signal, color=color, linestyle=style,
                              linewidth=1.3 if style == "-" else .75, label=f"{platform_name} i{key}")
            heading = "d then q" if scenario == "main" else "d only"
            axis.set_title(f"{heading} · {grid['step_s']*1e6:g} µs")
            axis.grid(alpha=.25)
    axes[0, 0].legend(ncols=2, loc="lower right")
    figure.supxlabel("Time (ms)")
    figure.supylabel("Current (A)")
    figure.savefig(destination, dpi=140)
    plt.close(figure)


def run_comparison(destination):
    protocol = frozen_json(DIRECTORY / "reference_protocol.json", PROTOCOL_SHA)
    qualification = frozen_json(DIRECTORY / "qualified_reference_report.json", QUALIFICATION_SHA)
    plant_input = protocol["basis"]["plant_validation"]
    plant_protocol_path = ROOT / plant_input["path"]
    plant_protocol = frozen_json(plant_protocol_path, plant_input["sha256"])
    limits = plant_protocol[protocol["same_step"]["numeric_budget_key_in_case_28"]]
    native, native_inputs = load_reference(protocol, qualification)

    destination.mkdir(parents=True, exist_ok=False)
    bindings = snapshot_sources(destination, plant_protocol_path)
    head = subprocess.check_output(
        ["git", "-c", f"safe.directory={ROOT.as_posix()}", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()
    manifest = {
        "git_head_before_run": head,
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "numpy_version": np.__version__,
        "matplotlib_version": matplotlib.__version__,
        "source_sha256": bindings,
        "native_sha256": {path.relative_to(ROOT).as_posix(): digest for path, digest in native_inputs.items()},
        "protocol_sha256": PROTOCOL_SHA,
        "qualification_sha256": QUALIFICATION_SHA,
    }
    manifest_path = destination / "inputs.json"
    save_json(manifest_path, manifest)

    factory = runpy.run_path(str(EXAMPLE))["define_case"]
    candidate, independent_runs, same = {}, {}, {}
    for scenario, case in protocol["scenarios"].items():
        for grid in protocol["electrical_grids"]:
            label = grid["id"]
            key = f"{scenario}_{label}"
            run_dir = destination / key
            run_dir.mkdir()
            print(f"Running {key}", flush=True)
            data, checks = run_candidate(factory, run_dir, protocol, plant_protocol, scenario, grid)
            candidate[scenario, label] = data
            independent_runs[key] = {
                "report_sha256": sha256(run_dir / "report.json"),
                "passed": checks["passed"],
            }
            intervals = [*windows(case), (0., protocol["acquisition_stop_s"])]
            same[key] = same_step(data, native[scenario, label], grid["step_s"], intervals, limits)

    cross, paired = {}, {}
    for platform_name, traces in (("PyCy", candidate), ("PSCAD", native)):
        cross[platform_name] = {
            scenario: cross_step(traces[scenario, "5us"], traces[scenario, "2p5us"], protocol, case)
            for scenario, case in protocol["scenarios"].items()
        }
        paired[platform_name] = {
            grid["id"]: paired_scenarios(traces["main", grid["id"]], traces["d_only", grid["id"]],
                                         protocol, grid["step_s"], limits)
            for grid in protocol["electrical_grids"]
        }

    passed = all(check["passed"] for check in independent_runs.values())
    passed &= all(check["passed"] for group in same.values() for check in group)
    passed &= all(check["passed"] for result in (cross, paired) for group in result.values() for check in group.values())
    figure = destination / "dq_comparison.png"
    plot_comparison(figure, candidate, native, protocol)
    metrics.require(all(sha256(ROOT / name) == digest for name, digest in bindings.items()),
                    "Candidate sources changed during comparison")
    metrics.require(all(sha256(path) == digest for path, digest in native_inputs.items()),
                    "Native inputs changed during comparison")
    report = destination / "report.json"
    save_json(report, {
        "passed": passed,
        "inputs_sha256": sha256(manifest_path),
        "native_reference_used": True,
        "native_engine": qualification["commercial_source"]["engine"],
        "candidate_runs": independent_runs,
        "same_step": same,
        "cross_step": cross,
        "paired_scenarios": paired,
        "figure_sha256": sha256(figure),
    })
    return report, passed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="New output directory below local_reference")
    args = parser.parse_args()
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    destination = (args.output or RESEARCH / f"c1_example29_comparison_{stamp}").resolve()
    cache = (ROOT / "local_reference").resolve()
    metrics.require(destination.is_relative_to(cache) and destination != cache, "Output must be below local_reference")
    report, passed = run_comparison(destination)
    print(report, "PASS" if passed else "FAIL")
    return int(not passed)


if __name__ == "__main__":
    raise SystemExit(main())
