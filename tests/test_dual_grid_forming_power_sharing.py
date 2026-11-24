"""Check the shared PCC, switched load and two independent P–f controllers."""

import json
import math
from dataclasses import replace
from pathlib import Path
from runpy import run_path

import numpy as np
import pytest

from pycy_emt_lite import (
    IdealSwitch,
    Inductor,
    OutputOptions,
    Resistor,
    VoltageSource,
    run_case,
)
from validation.cases.dual_grid_forming_power_sharing.checks import pcc_powers
from validation.cases.dual_grid_forming_power_sharing.compare import trace_from_result

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "validation/cases/dual_grid_forming_power_sharing/candidate_protocol.json"
EXAMPLE = ROOT / "examples/39_dual_grid_forming_power_sharing.py"


@pytest.fixture(scope="module")
def example():
    return run_path(str(EXAMPLE))["define_case"], json.loads(PROTOCOL.read_bytes())


@pytest.mark.parametrize("grid", ("5us", "2p5us"))
def test_both_feeders_meet_the_grounded_load_at_each_phase(example, grid):
    define_case, protocol = example
    fixture, timing = protocol["fixture"], protocol["timing"]
    step = protocol["grids"][grid]["step_s"]
    case = define_case(time_step=step)
    assert case.config.stop_time == timing["duration_s"] and case.events == ()
    parts = {part.name: part for part in case.components}
    assert len(parts) == 24
    for phase in "abc":
        pcc = f"pcc_{phase}"
        for site in "ab":
            label = f"{site}_{phase}"
            source, resistance, reactor = (parts[f"{name}_{label}"] for name in ("Emf", "FeederR", "FeederL"))
            assert isinstance(source, VoltageSource) and (source.positive, source.negative) == (f"src_{label}", "0")
            assert isinstance(resistance, Resistor) and resistance.resistance == fixture["feeder_ohm"]
            assert isinstance(reactor, Inductor) and reactor.inductance == fixture["feeder_h"]
            assert resistance.positive == source.positive and resistance.negative == reactor.positive
            assert reactor.negative == pcc and reactor.initial_current == 0
        base, added = parts[f"Base_{phase}"], parts[f"Added_{phase}"]
        assert isinstance(base, Resistor) and (base.positive, base.negative) == (pcc, "0")
        assert base.resistance == fixture["base_load_ohm"]
        assert isinstance(added, IdealSwitch) and callable(added.closed)
        assert (added.positive, added.negative) == (pcc, "0")
        assert added.closed_resistance == fixture["added_load_ohm"]
        assert added.open_conductance == 1 / fixture["open_load_ohm"]
        edge = timing["load_step_s"]
        assert not added.closed(0) and not added.closed(edge - step)
        assert added.closed(edge) and added.closed(edge + step)


@pytest.mark.parametrize("grid", ("5us", "2p5us"))
def test_each_controller_uses_its_own_solved_power_to_advance_phase(example, grid):
    define_case, protocol = example
    fixture, controller = protocol["fixture"], protocol["controller"]
    step = protocol["grids"][grid]["step_s"]
    stop = 0.025
    case = define_case(time_step=step, stop_time=stop)
    result = run_case(replace(case, plots=(), output=OutputOptions(show_figure=False)))
    assert len(result.rows) == round(stop / step) + 1 and result.method == "trapezoidal"
    trace = trace_from_result(result, fixture)
    phase, frequency, filtered = (trace[key] for key in ("phase_rad", "frequency_hz", "filtered_w"))
    power = pcc_powers(trace)
    limits = protocol["control_limits"]
    references = [controller["stations"][site]["reference_power_w"] for site in "ab"]
    slopes = np.array([controller["stations"][site]["droop_hz_per_w"] for site in "ab"])
    np.testing.assert_array_equal(phase[0], [0, 0])
    np.testing.assert_array_equal(frequency[0], [60, 60])
    np.testing.assert_array_equal(filtered[0], references)
    np.testing.assert_allclose(trace["meter_w"], power, rtol=0, atol=limits["power_meter_abs_w"])
    ratio = step / controller["filter_tau_s"]
    np.testing.assert_allclose(filtered[1:], (filtered[:-1] + ratio * power[1:]) / (1 + ratio),
                               rtol=0, atol=limits["filter_recurrence_abs_w"])
    np.testing.assert_allclose(frequency, 60 - slopes * (filtered - references),
                               rtol=0, atol=limits["droop_recurrence_abs_hz"])
    np.testing.assert_allclose(np.diff(phase, axis=0), math.tau * step * frequency[:-1],
                               rtol=0, atol=limits["angle_recurrence_abs_rad"])
    expected_voltages = trace["peak_v"][:, None, None] * np.sin(phase[:, :, None] + fixture["phase_shifts_rad"])
    np.testing.assert_allclose(trace["source_v"], expected_voltages,
                               rtol=0, atol=protocol["physical_limits"]["source_wave_abs_v"])
    assert np.max(np.abs(frequency[:, 0] - frequency[:, 1])) > .001
    np.testing.assert_array_equal(result.series("phase_difference_mrad"), 1000 * (phase[:, 0] - phase[:, 1]))
