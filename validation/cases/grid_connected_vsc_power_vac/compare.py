"""Compare four fresh case 31 runs with the sealed coherent-window PSCAD reference."""

import argparse
import json
import platform
import re
import runpy
import subprocess
from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal, localcontext
from math import sqrt
from pathlib import Path
from time import monotonic

import matplotlib
import numpy as np

from pycy_emt_lite import OutputOptions, run_case
from validation.cases.grid_connected_vsc_closed_loop import compare as inner
from validation.cases.grid_connected_vsc_open_loop import binding, metrics, physics
from validation.cases.grid_connected_vsc_open_loop.compare import (
    PlantRows,
    Projection,
    save_json,
    write_plant,
)
from validation.cases.grid_connected_vsc_pll import compare as pll
from validation.common.runner import sha256

from . import checks

ROOT = inner.ROOT
DIRECTORY = Path(__file__).resolve().parent
CACHE = ROOT/"local_reference"
EXAMPLE = ROOT/"examples/31_grid_connected_vsc_power_vac.py"
PROTOCOL_SHA = "5724214d6223d074ce2772927afd7af216d41bb49ed025badb48bdc77e53d8f3"
TRIAL_SHA = "c478914ee2c5af94155aaa162dda38dced696947901cf9355aeb20ad8aa0650f"
REFERENCE_SHA = "2506069f9d50b693881cecedc31f872f7998f9270acb254811a213c0b91dd748"
LAYOUT_SHA = "e7cd7ad8c845debfc59953c0292bb237264dd205220fbea1fb9eec40ebc49129"
TIME = inner.TIME
PCC = checks.PCC
STEM = "c1_power_vac"
GRIDS = (("5us", 5e-6), ("2p5us", 2.5e-6))
INF_LINE = re.compile(
    r'PGB\(\s*(\d+)\)\s+Output\s+Desc="([^"]+)"\s+Group="([^"]+)"\s+Max=(\S+)\s+Min=(\S+)\s+Units="([^"]+)"'
)
INNER_FIELDS = (
    "j", "sample_update", "gate_tick", "theta", "ed", "eq", "id", "iq", "z_d", "z_q",
    "carrier_applied", "saturated", "pll_omega", "pll_xi", "pll_error",
    *(f"{state}_{phase}" for state in ("pending", "applied") for phase in "abc"),
)


def read_native(work, grid, proof):
    """Read raw current and outer logs only after their original bytes are admitted."""
    info = (work/f"{STEM}.inf").read_text("ascii").splitlines()
    records = [INF_LINE.fullmatch(line.strip()) for line in info]
    metrics.require(len(records) == 48 and all(records), "Original INF does not contain 48 PGB descriptors")
    names = [match[2] for match in records]
    metrics.require(len(set(names)) == 48 and all(
        int(match[1]) == slot and list(match.groups()[1:]) == proof["pgb_map"][str(slot)]
        for slot, match in enumerate(records, 1)
    ), "Original PGB order or metadata differs from the admitted generated map")
    count = grid["rows"]
    table = {}
    needed = {*physics.names(), *PCC}
    for part in range(5):
        columns = names[part*10:(part+1)*10]
        raw = np.loadtxt(work/f"{STEM}_{part+1:02}.out", skiprows=1)
        metrics.require(raw.shape == (count, len(columns)+1) and np.isfinite(raw).all(),
                        f"Original OUT part {part+1} is incomplete or nonfinite")
        if part:
            metrics.require(np.array_equal(table["out_time"], raw[:, 0]), "Original OUT clocks differ")
        else:
            table["out_time"] = raw[:, 0].copy()
        table.update({name: raw[:, index]*(1000 if physics.unit(name) in {"kV", "kA"} else 1)
                      for index, name in enumerate(columns, 1) if name in needed})
    metrics.require(np.array_equal(table.pop("out_time"), table[TIME]), "Original time channel differs")
    log = np.loadtxt(work/"c1_feedback.csv", delimiter=",")
    outer = np.loadtxt(work/"c1_outer.csv", delimiter=",")
    metrics.require(log.shape == (count, 32) and outer.shape == (count, 15)
                    and np.isfinite(log).all() and np.isfinite(outer).all(), "Original control capture shape differs")
    rows = np.arange(count)
    for control in (log, outer):
        metrics.require(np.array_equal(control[:, 0], rows)
                        and np.max(np.abs(control[:, 1]-table[TIME])) <= 2e-12, "Control and OUT acquisition clocks differ")
    table.update({key: log[:, column].copy() for key, column in (
        ("saturated", 10), ("theta", 27), ("sample_update", 28), ("omega", 29), ("xi", 30), ("normalized_error", 31)
    )})
    table.update({key: outer[:, column].copy() for column, key in enumerate(checks.OUTER_FIELDS, 5)})
    inner.check_clock(table, grid)
    return table


def load_reference(qualification, grids, protocol):
    """Bind separate raw native execution, independent readback and final reference qualification."""
    metrics.require(qualification["status"] == "PASS_NATIVE_PCC_POWER_VAC_COHERENT_REFERENCE"
                    and qualification["base_protocol_sha256"] == PROTOCOL_SHA
                    and qualification["window_trial_sha256"] == TRIAL_SHA, "Reference did not pass the frozen trial")
    evidence, native, receipts = {}, {}, {}

    def admit(path, expected):
        file = path.resolve(strict=True)
        metrics.require(file.is_relative_to(CACHE.resolve()) and sha256(file) == expected,
                        f"Changed or invalid local reference bytes: {file}")
        evidence[file] = expected
        return file

    def read(path, expected):
        return json.loads(admit(path, expected).read_bytes())

    entries = qualification["conditions"]
    stem = STEM
    raw_names = {f"{stem}.inf", "c1_feedback.csv", "c1_outer.csv", *(f"{stem}_{part:02}.out" for part in range(1, 6))}
    metrics.require(len({entry["run"] for entry in entries.values()}) == len(entries) == 4, "Expected four independent runs")
    for label, grid in grids.items():
        for scenario in protocol["acquisition"]["conditions"]:
            key = f"{label}_{scenario}"
            entry = entries[key]
            run = ROOT/entry["run"]
            work = run/"project/vdiv.gf46"
            receipt = read(run/"native_execution_receipt.json", entry["native_receipt_sha256"])
            terminal = read(run/"terminal.json", receipt["terminal_sha256"])
            admission = read(run/"pre_run_admission.json", receipt["pre_run_admission_sha256"])
            runtime = receipt["native_runtime"]
            proof = admission["proof"]
            metrics.require(
                receipt["status"] == "NATIVE_OUTER_CAPTURE_READY_NUMERIC_REVIEW"
                and (receipt["scenario"], float(receipt["electrical_step_s"])) == (scenario, grid["step_s"])
                and receipt["protocol_sha256"] == admission["protocol_sha256"] == PROTOCOL_SHA
                and receipt["layout_sha256"] == admission["layout_sha256"] == LAYOUT_SHA
                and (label == "5us" or receipt["window_trial_sha256"] == TRIAL_SHA)
                and terminal["worker_returncode"] == 0 and terminal["source_hash_unchanged"] is True
                and terminal["stop_reason"] is None and not terminal["remaining_owned"]
                and runtime["emtdc_pid_observed"] is True and runtime["emtdc_process_identity"]["name"].lower() == "vdiv.exe"
                and set(receipt["raw_files_sha256"]) == raw_names
                and (proof["subsystems"], proof["nonzero_nodes"], proof["branches"], proof["pgb_count"]) == (1, 17, 22, 48)
                and proof["old_graph_preserved_after_feeder_contraction"] is True, f"Invalid native admission: {key}",
            )
            post = receipt["post_run_generated_sha256"]
            metrics.require(set(post) == set(admission["generated_sha256"]) and
                            all(post[name] == digest for name, digest in admission["generated_sha256"].items()
                                if name not in {"vdiv.map", "vdiv.exe"}), f"Native generated inputs differ: {key}")
            for name, digest in (post | receipt["raw_files_sha256"]).items():
                admit(work/name, digest)
            for name, digest in runtime["vendor_run_artifacts_sha256"].items():
                admit(run/name, digest)
            original = read(run/"independent_reference_review.json", entry["original_review_sha256"])
            metrics.require(original["passed"] is False, f"Preserved original verdict changed: {key}")
            review = (read(run/"independent_reference_review_corrected.json", entry["corrected_review_sha256"])
                      if "corrected_review_sha256" in entry else original)
            cycles = review["feeder_and_cycles"]
            metrics.require(review["receipt_sha256"] == entry["native_receipt_sha256"]
                            and review["outer_control"]["passed"] and review["inner_and_gates"]["passed"]
                            and cycles["feeder_tr"]["passed"] and cycles["rows"] == grid["rows"],
                            f"Independent clock/control/feeder evidence differs: {key}")
            native[label, scenario] = read_native(work, grid, proof)
            receipts[key] = entry["native_receipt_sha256"]
    for key, record in qualification["pair_reports"].items():
        pair = read(ROOT/entries[record["run_key"]]["run"]/record["file"], record["sha256"])
        metrics.require(pair["passed"] is True, f"Native pair or cross-grid report failed: {key}")
        if key != "cross_step":
            for scenario in protocol["acquisition"]["conditions"]:
                expected = receipts[record["run_key"].split("_")[0] + "_" + scenario]
                metrics.require(pair[scenario]["native_receipt_sha256"] == expected
                                and pair[scenario]["trial_sha256"] == TRIAL_SHA, "Native pair archive binding differs")
        else:
            metrics.require(pair["trial_sha256"] == TRIAL_SHA and len(pair["comparisons"]) == 8, "Native trial pair differs")
    return native, evidence


def plant_physics(result, plant, upper, step, plant_protocol, protocol, folder):
    """Verify both real branch segments, then run the existing 19-budget equivalent-loop check."""
    data = dict(plant)
    config = protocol["plant"]
    limits = plant_protocol["physical_residual_budgets"]
    r_f, l_f = config["per_phase_feeder_r_ohm"], config["per_phase_feeder_l_h"]
    r_b, l_b = config["per_phase_bridge_filter_r_ohm"], config["per_phase_bridge_filter_l_h"]
    segment = {}
    for phase, e, pcc, current in zip("abc", inner.VOLTAGES, PCC, inner.CURRENTS, strict=True):
        ir = plant[current]
        feeder_i = result.series(f"i:Lg{phase}")
        middle = result.series(f"v:rg_out_{phase}")
        feeder_r = plant[e] - middle
        feeder_l = middle - plant[pcc]
        vr, vl = f"VR_{phase}_kV", f"VL_{phase}_kV"
        data[vr] = plant[vr] + feeder_r
        data[vl] = plant[vl] + feeder_l
        residual = {
            "series_current_A": float(np.max(np.abs(feeder_i-ir))),
            "feeder_resistor_V": float(np.max(np.abs(feeder_r-r_f*feeder_i))),
            "bridge_resistor_V": float(np.max(np.abs(plant[vr]-r_b*ir))),
            "feeder_tr_V": float(np.max(np.abs(2*l_f/step*np.diff(feeder_i)-feeder_l[1:]-feeder_l[:-1]))),
            "bridge_tr_V": float(np.max(np.abs(2*l_b/step*np.diff(ir)-plant[vl][1:]-plant[vl][:-1]))),
            "bridge_kvl_V": float(np.max(np.abs(plant[pcc]-plant[vr]-plant[vl]-plant[f"V_{phase}_pole_kV"]))),
        }
        metrics.require(residual["series_current_A"] <= limits["three_line_KCL_with_tokens_A"]
                        and max(residual[key] for key in ("feeder_resistor_V", "bridge_resistor_V")) <= limits["resistor_with_tokens_V"]
                        and residual["feeder_tr_V"] <= protocol["native_gates"]["feeder_trapezoid_max_v"]
                        and residual["bridge_tr_V"] <= limits["full_TR_with_tokens_V"]
                        and residual["bridge_kvl_V"] <= limits["phase_KVL_with_tokens_V"],
                        f"Physical feeder or converter segment differs: {phase}, {residual}")
        segment[phase] = residual
    path = folder/"plant32_equivalent.csv"
    write_plant(path, {name: data[name] for name in physics.names()})
    rows = PlantRows(path, len(plant[TIME]), physics.names())
    with localcontext() as context:
        context.prec = 70
        physical = physics.evaluate(
            Projection(rows, 0), Projection(rows, 1), h=Decimal(str(step)), expected_rows=len(plant[TIME]),
            limits=limits, precision_caps=plant_protocol["printed_precision_caps_SI"], upper_states=upper,
            series_r=Decimal(str(r_f))+Decimal(str(r_b)), series_l=Decimal(str(l_f))+Decimal(str(l_b)),
        )
    return {"equivalent_series_residuals": physical, "segments": segment, "csv_sha256": sha256(path),
            "passed": physical["observed_pass"]}


def run_candidate(factory, folder, scenario, grid, protocol, trial, current_protocol, pll_protocol, plant_protocol):
    start = monotonic()
    case = factory(scenario=scenario, time_step=grid["step_s"], stop_time=protocol["acquisition"]["solver_tail_s"])
    result = run_case(replace(case, output=OutputOptions(show_figure=False), plots=(), summary=None))
    plant = binding.plant_data(result, case.components)
    for phase, name in zip("abc", PCC, strict=True):
        plant[name] = result.series(f"v:pcc_{phase}")
        plant[f"VR_{phase}_kV"] = plant[name] - result.series(f"v:r_{phase}")
    observer = {key: result.series(key) for key in (*INNER_FIELDS, *checks.OUTER_FIELDS)}
    inner.check_clock({**plant, **observer}, grid)
    replay_pll = pll.replay_pll(plant, observer, pll_protocol, grid)
    commands, outer = checks.replay_outer(plant, observer, protocol, scenario, grid)
    upper, feedback = inner.check_feedback(
        plant, observer, current_protocol, "main", grid, angle=observer["theta"], sampled_commands=commands,
    )
    points = protocol["acquisition"]["current_sample_and_next_gate_per_run"]
    metrics.require(feedback["updates"] == feedback["next_gate_applications"] == points, "Incomplete inner clock")
    physical = plant_physics(result, plant, upper, grid["step_s"], plant_protocol, protocol, folder)
    del result
    trace = {**plant, **observer, **{name: observer[key] for name, (key, _) in pll.PLL_FIELDS.items()}}
    waveforms = folder/"waveforms.npz"
    np.savez(waveforms, **trace)
    perf = checks.performance(trace, protocol, trial, scenario)
    report = {"grid": grid, "scenario": scenario, "pll_replay": replay_pll, "outer": outer, "feedback": feedback,
              "physical": physical, "performance": perf, "elapsed_s": monotonic()-start,
              "waveforms_sha256": sha256(waveforms), "passed": physical["passed"] and perf["passed"]}
    save_json(folder/"report.json", report)
    return trace, report


def compare_same_step(candidate, native, grid, intervals, limits, protocol, pll_protocol, performance, reference):
    step = grid["step_s"]
    data_windows = inner.same_step(candidate, native, step, intervals, limits)
    for window in data_windows:
        start, stop = window["interval_s"]
        first, last = round(start/step), round(stop/step)
        for name in PCC:
            error = candidate[name][first:last+1] - native[name][first:last+1]
            grid_time = np.arange(first, last+1)*step
            stats = {"max_abs": float(np.max(np.abs(error))), "PWL_RMSE_abs": sqrt(metrics.square_mean(grid_time, error))}
            check = metrics.continuous_gate(stats, limits["all_other_plant_voltages_V"])
            window["metrics"][name] = check
            window["passed"] &= check["passed"]
    pll_windows = pll.compare_states(candidate, native, pll_protocol, intervals, step)
    outer_limits = protocol["native_gates"]
    states = {}
    for name in checks.OUTER_FIELDS:
        delta = candidate[name] - native[name]
        if name == "pcc_theta":
            delta = pll.wrap_error(delta)
            limit = outer_limits["source_pll_angle_abs_rad"]
        elif name in {"outer_update", "p_ref_w"}:
            limit = 0.
        elif name.endswith("_filtered"):
            limit = outer_limits["outer_replayed_filter_abs_v"]
        else:
            limit = outer_limits["outer_replayed_current_or_integrator_abs_a"]
        maximum = float(np.max(np.abs(delta)))
        states[name] = {"max_abs": maximum, "limit": limit, "passed": maximum <= limit}
    cycles = [
        row for table in ("single_cycles", "coherent_windows") for stage in ("mid", "settled")
        for row in checks.compare_performance(performance[table][stage], reference[table][stage],
                                              {"pcc_power_w": 1., "pcc_q1_var": 1.})
    ]
    return {"physical": data_windows, "pll": pll_windows, "outer": states, "power_and_reactive": cycles,
            "passed": all(row["passed"] for row in (*data_windows, *pll_windows, *states.values(), *cycles))}


def comparisons(traces, performance, grids, trial, *, control_details=()):
    rules = trial["trial_rules"]
    pair = {}
    for label, grid in grids.items():
        held, regulated = (traces[label, name] for name in ("held", "regulated"))
        step = grid["step_s"]
        stop, control_stop = round(.240005/step), round(.24/step)
        physical = (*physics.names(), *PCC)
        control = {"saturated", "sample_update", *pll.PLL_FIELDS, *checks.OUTER_FIELDS, *control_details}
        prefix = {
            "physical_rows": stop,
            "control_rows": control_stop,
            "physical_exact": all(np.array_equal(held[name][:stop], regulated[name][:stop]) for name in physical),
            "control_exact": all(np.array_equal(held[name][:control_stop], regulated[name][:control_stop]) for name in control),
        }
        baseline, active = (performance[label, name]["coherent_windows"]["settled"] for name in ("held", "regulated"))
        improvement = []
        limits = rules["each_coherent_window"]
        for a, b in zip(baseline, active, strict=True):
            voltage = b["pcc_v1_v_rms"]-a["pcc_v1_v_rms"]
            reactive = a["pcc_q1_var"]-b["pcc_q1_var"]
            improvement.append({
                "window_s": a["window_s"], "voltage_improvement_v_rms": voltage, "reactive_reduction_var": reactive,
                "passed": voltage >= limits["paired_v_improvement_min_v_rms"] and reactive >= limits["paired_q_reduction_min_var"],
            })
        pair[label] = {"prefix": prefix, "windows": improvement,
                       "passed": prefix["physical_exact"] and prefix["control_exact"] and all(row["passed"] for row in improvement)}
    limits = {key: rules["cross_h_each_coherent_window"][name] for key, name in checks.METRIC_LIMITS.items()}
    cross = {scenario: [
        row for stage in ("mid", "settled") for row in checks.compare_performance(
            performance["5us", scenario]["coherent_windows"][stage],
            performance["2p5us", scenario]["coherent_windows"][stage], limits,
        )
    ] for scenario in ("held", "regulated")}
    return {"same_grid_pair": pair, "cross_grid": cross,
            "passed": all(row["passed"] for row in pair.values()) and all(row["passed"] for group in cross.values() for row in group)}


def plot_comparison(path, candidate, native):
    matplotlib.use("Agg")
    from matplotlib import pyplot as plt

    figure, axes = plt.subplots(2, 2, sharex=True, sharey="row", layout="constrained", figsize=(11, 7))
    for column, scenario in enumerate(("held", "regulated")):
        for axis, (label, _) in zip(axes[:, column], GRIDS, strict=True):
            for name, data, style in (("PSCAD", native, "--"), ("PyCy", candidate, "-")):
                trace = data[label, scenario]
                estimate = np.hypot(trace["pcc_d_filtered"], trace["pcc_q_filtered"])/sqrt(2)
                keep = trace["outer_update"].astype(bool)
                axis.plot(1000*trace[TIME][keep], estimate[keep], style, label=name)
            axis.axhline(120, color="#777777", linewidth=.8)
            axis.axvspan(600, 650, color="#bbbbbb", alpha=.18)
            axis.set_title(f"{scenario}, {label}")
            axis.set_ylim(115, 124)
            axis.grid(alpha=.25)
    axes[0, 0].legend()
    figure.supylabel("Filtered PCC phase voltage (V RMS)")
    figure.supxlabel("Time (ms)")
    figure.savefig(path, dpi=145)
    plt.close(figure)


def run_comparison(destination):
    protocol_path = DIRECTORY/"reference_protocol.json"
    trial_path = DIRECTORY/"fundamental_window_trial.json"
    reference_path = DIRECTORY/"coherent_reference_report.json"
    layout_path = ROOT/"docs/development_roadmap/experiments/c1_pcc_feeder_native_layout_20261122.json"
    protocol = inner.frozen_json(protocol_path, PROTOCOL_SHA)
    trial = inner.frozen_json(trial_path, TRIAL_SHA)
    reference = inner.frozen_json(reference_path, REFERENCE_SHA)
    inner.frozen_json(layout_path, LAYOUT_SHA)
    pll_path = pll.DIRECTORY/"reference_protocol.json"
    pll_protocol = inner.frozen_json(pll_path, pll.PROTOCOL_SHA)
    current_input = pll_protocol["basis"]["plant_and_current_loop"]
    current_path = ROOT/current_input["path"]
    current = inner.frozen_json(current_path, current_input["sha256"])
    plant_input = current["basis"]["plant_validation"]
    plant_path = ROOT/plant_input["path"]
    plant = inner.frozen_json(plant_path, plant_input["sha256"])
    acquisition = protocol["acquisition"]
    grids = {label: {"id": label, "step_s": step, "rows": rows}
             for (label, step), rows in zip(GRIDS, acquisition["rows_by_grid"], strict=True)}
    native, evidence = load_reference(reference, grids, protocol)
    scenarios = acquisition["conditions"]
    native_perf = {key: checks.performance(trace, protocol, trial, key[1]) for key, trace in native.items()}
    native_pairs = comparisons(native, native_perf, grids, trial)
    metrics.require(all(value["passed"] for value in native_perf.values()) and native_pairs["passed"],
                    "Read-back original native performances or prefix differ from the archived verdict")
    design = protocol["plant"]
    design_current = {**current, "formal_stop_s": .65,
                      "plant": {**current["plant"],
                                "series_R_ohm": design["per_phase_feeder_r_ohm"]+design["per_phase_bridge_filter_r_ohm"],
                                "series_L_H": design["per_phase_feeder_l_h"]+design["per_phase_bridge_filter_l_h"]}}
    destination.mkdir(parents=True, exist_ok=False)
    sources = [EXAMPLE, Path(__file__), Path(checks.__file__), Path(inner.__file__), Path(pll.__file__),
               protocol_path, trial_path, reference_path, layout_path, pll_path, current_path, plant_path,
               ROOT/"pyproject.toml", ROOT/"uv.lock",
               *(ROOT/"pycy_emt_lite").rglob("*.py"), *(ROOT/"validation/common").rglob("*.py"),
               *(ROOT/"validation/cases/grid_connected_vsc_open_loop").rglob("*.py")]
    bindings = inner.snapshot_inputs(destination, sources)
    manifest = destination/"inputs.json"
    save_json(manifest, {
        "git_head_before_run": subprocess.check_output(
            ["git", "-c", f"safe.directory={ROOT.as_posix()}", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "python_version": platform.python_version(), "platform": platform.platform(),
        "numpy_version": np.__version__, "matplotlib_version": matplotlib.__version__, "source_sha256": bindings,
        "native_sha256": {path.relative_to(ROOT).as_posix(): digest for path, digest in evidence.items()},
    })
    factory = runpy.run_path(str(EXAMPLE))["define_case"]
    candidate, candidate_perf, results, same = {}, {}, {}, {}
    limits = plant[current["same_step"]["numeric_budget_key_in_case_28"]]
    for label, grid in grids.items():
        for scenario in scenarios:
            key = label, scenario
            run = f"{label}_{scenario}"
            folder = destination/run
            folder.mkdir()
            print(f"Running {run}", flush=True)
            trace, result = run_candidate(factory, folder, scenario, grid, protocol, trial, design_current, pll_protocol, plant)
            candidate[key], candidate_perf[key] = trace, result["performance"]
            results[run] = {"passed": result["passed"], "report_sha256": sha256(folder/"report.json")}
            same[run] = compare_same_step(trace, native[key], grid, protocol["candidate_gates"]["windows_s"],
                                          limits, protocol, pll_protocol, candidate_perf[key], native_perf[key])
    pairs = comparisons(candidate, candidate_perf, grids, trial, control_details=INNER_FIELDS)
    passed = (all(row["passed"] for row in results.values())
              and all(row["passed"] for row in same.values()) and pairs["passed"])
    figure = destination/"pcc_voltage_comparison.png"
    plot_comparison(figure, candidate, native)
    metrics.require(all(sha256(ROOT/name) == digest for name, digest in bindings.items())
                    and all(sha256(path) == digest for path, digest in evidence.items()), "Comparison inputs changed during execution")
    report = destination/"report.json"
    save_json(report, {"passed": passed, "inputs_sha256": sha256(manifest), "candidate_runs": results,
                       "same_step": same, "candidate_pairs": pairs, "native_pairs": native_pairs,
                       "native_performance": {f"{label}_{scenario}": value for (label, scenario), value in native_perf.items()},
                       "figure_sha256": sha256(figure), "native_engine": acquisition["platform"]})
    return report, passed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="New comparison directory below local_reference")
    args = parser.parse_args()
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    destination = (args.output or inner.RESEARCH/f"c1_example31_comparison_{stamp}").resolve()
    metrics.require(destination.is_relative_to(CACHE.resolve()) and destination != CACHE.resolve(), "Output must be below local_reference")
    report, passed = run_comparison(destination)
    print(report, "PASS" if passed else "FAIL")
    return int(not passed)


if __name__ == "__main__":
    raise SystemExit(main())
