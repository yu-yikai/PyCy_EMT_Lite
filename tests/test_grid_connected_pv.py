"""Check the PV example's affine port, precharged start and solved-row timing."""

import json
from dataclasses import replace
from pathlib import Path
from runpy import run_path

import numpy as np
import pytest

from pycy_emt_lite import Capacitor, CurrentSource, OutputOptions, Resistor, run_case

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples/36_grid_connected_pv.py"
PROTOCOL = ROOT / "validation/cases/grid_connected_pv/candidate_protocol.json"


@pytest.fixture(scope="module")
def example():
    return run_path(str(EXAMPLE))["define_case"], json.loads(PROTOCOL.read_bytes())


@pytest.mark.parametrize("grid", ("5us", "2p5us"))
def test_pv_port_and_exact_irradiance_edge(example, grid):
    define_case, protocol = example
    step = protocol["grids"][grid]["step_s"]
    dc = protocol["dc_circuit"]
    case = define_case(time_step=step)
    assert case.config.stop_time == protocol["example"]["stop_s"]
    parts = {part.name: part for part in case.components}
    source, shunt, load, cap = (parts[name] for name in ("Ipv", "Rpv", "Rload", "Cdc"))
    assert isinstance(source, CurrentSource) and (source.positive, source.negative) == ("a_n", "a_p")
    assert isinstance(shunt, Resistor) and shunt.resistance == dc["string_shunt_ohm"]
    assert isinstance(load, Resistor) and load.resistance == dc["load_ohm"]
    assert isinstance(cap, Capacitor) and cap.capacitance == dc["bus_cap_f"]
    assert {(part.positive, part.negative) for part in (shunt, load, cap)} == {("a_p", "a_n")}
    edge = protocol["schedule"]["irradiance_step_s"]
    high, low = (dc["norton_source_by_irradiance_a"][key] for key in ("1000", "900"))
    assert callable(source.current)
    assert source.current(edge - step) == high
    assert source.current(edge) == source.current(edge + step) == low


@pytest.mark.parametrize("grid", ("5us", "2p5us"))
def test_pv_snapshot_and_first_grid_control_ticks(example, grid):
    define_case, protocol = example
    profile, schedule = protocol["grids"][grid], protocol["schedule"]
    step = profile["step_s"]
    case = define_case(time_step=step, stop_time=.012)
    result = run_case(replace(case, output=OutputOptions(show_figure=False), plots=()))
    assert result.method == schedule["integration"]
    initial = result.rows[0]
    initial_bus = profile["initial_bus_v"]
    assert initial["v:Cdc"] == pytest.approx(initial_bus, rel=0, abs=2e-6)
    assert initial["a_dc_integrator"] == initial["a_ip_ref_a"] == 0
    assert all(initial[f"i:a_L{phase}"] == initial[f"i:a_Lg{phase}"] == 0 for phase in "abc")
    pv, load, cap = (result.series(field) for field in ("pv_delivered_a", "i:Rload", "i:Cdc"))
    switch = sum(result.series(f"i:a_S{phase}_upper") for phase in "abc")
    np.testing.assert_allclose(pv - load - cap, switch, rtol=0, atol=protocol["physical_limits"]["kcl_abs_a"])

    indices = np.arange(len(result.rows))
    gate, inner, outer = (round(schedule[name] / step) for name in ("gate_period_s", "inner_period_s", "outer_period_s"))
    np.testing.assert_array_equal(result.series("a_j"), indices)
    np.testing.assert_array_equal(np.flatnonzero(result.series("a_sample_update")), indices[inner::inner])
    np.testing.assert_array_equal(np.flatnonzero(result.series("a_outer_due")), indices[outer::outer])
    enabled = np.flatnonzero(result.series("a_outer_enabled"))
    assert enabled[0] == round(schedule["first_enabled_outer_s"] / step)
    assert result.series("a_ip_ref_a")[enabled[0]] < 0

    actual = np.column_stack([result.series(f"a_applied_{phase}") for phase in "abc"])
    pending = np.column_stack([result.series(f"a_pending_{phase}") for phase in "abc"])
    np.testing.assert_array_equal(actual, pending[np.maximum(indices // gate * gate - 1, 0)])
    first_effect = np.flatnonzero(np.any(actual != 0, axis=1))[0]
    assert first_effect == round(schedule["first_nonzero_gate_s"] / step)
