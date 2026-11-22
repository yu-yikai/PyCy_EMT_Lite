"""Check PJM5 startup, line-port signs and exact load switching on both grids."""

import math
import runpy
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from pycy_emt_lite import IdealSwitch
from pycy_emt_lite.cases import OutputOptions, run_case

EXAMPLE = Path(__file__).resolve().parents[1] / "examples/33_pjm5_load_step.py"
STEPS = (5e-6, 2.5e-6)
PHASES = "abc"
# PGLib branch charging susceptance in p.u. on 230 kV / 100 MVA.
LINES = ((1, 2, .00712), (1, 4, .00658), (1, 5, .03126),
         (2, 3, .01852), (3, 4, .00674), (4, 5, .00674))
OMEGA = math.tau * 60
BASE_IMPEDANCE = 230000.0**2 / 100e6
SOURCE_PEAK = math.sqrt(2 / 3) * 230000


@pytest.fixture(scope="module")
def define_case():
    return runpy.run_path(str(EXAMPLE))["define_case"]


@pytest.fixture(scope="module", params=STEPS)
def short_run(define_case, request):
    step = request.param
    case = define_case(time_step=step, stop_time=.002)
    result = run_case(replace(case, plots=(), summary=None, output=OutputOptions(show_figure=False)))
    return step, result


def phase_series(result, prefix):
    return np.array([result.series(f"{prefix}{phase}") for phase in PHASES])


def test_zero_storage_and_source_capacitor_current_from_ramp_slope(short_run):
    step, result = short_run
    time = result.series("time")
    assert len(time) == round(.002 / step) + 1
    np.testing.assert_allclose(time, np.arange(len(time)) * step, atol=2e-12, rtol=0)
    initial = result.rows[0]
    assert [initial[f"v:b{bus}:{phase}"] for bus in range(1, 6) for phase in PHASES] == pytest.approx([0] * 15, abs=1e-10)
    assert [initial[f"i:Lload_{bus}_{phase}"] for bus in (2, 3, 4) for phase in PHASES] == pytest.approx([0] * 9, abs=1e-10)

    offsets = np.array([0., -math.tau / 3, math.tau / 3])
    source_voltage = SOURCE_PEAK * (time / .05) * np.sin(OMEGA * time + offsets[:, None])
    np.testing.assert_allclose(phase_series(result, "v:b4:"), source_voltage, atol=1e-9, rtol=0)
    source_slope = SOURCE_PEAK * np.sin(offsets) / .05
    source_capacitance = 0.
    for start, end, susceptance in LINES:
        name = f"line_{start}{end}"
        assert [initial[f"i:{name}:series:{phase}"] for phase in PHASES] == pytest.approx([0] * 3, abs=1e-10)
        capacitance = susceptance / (2 * OMEGA * BASE_IMPEDANCE)
        for side, bus in (("from", start), ("to", end)):
            currents = [initial[f"i:{name}:{side}_cap:{phase}"] for phase in PHASES]
            expected = capacitance * source_slope if bus == 4 else np.zeros(3)
            assert currents == pytest.approx(expected, abs=1e-10)
            if bus == 4:
                source_capacitance += capacitance
    # VoltageSource reports current into the source; delivery has the opposite sign.
    delivery = [-initial[f"i:Vsource_{phase}"] for phase in PHASES]
    assert delivery == pytest.approx(source_capacitance * source_slope, abs=1e-10)


def test_bus2_imports_use_both_signed_line_ends(short_run):
    _, result = short_run
    voltage = phase_series(result, "v:b2:")
    from_bus1 = phase_series(result, "i:line_12:series:") - phase_series(result, "i:line_12:to_cap:")
    from_bus3 = -phase_series(result, "i:line_23:series:") - phase_series(result, "i:line_23:from_cap:")
    added = phase_series(result, "i:Rstep_")
    base = phase_series(result, "i:Rload_2_") + phase_series(result, "i:Lload_2_")
    np.testing.assert_allclose(from_bus1 + from_bus3, base + added, atol=1e-8, rtol=0)
    np.testing.assert_allclose(added, voltage / 1e9, atol=1e-14, rtol=0)
    np.testing.assert_array_equal(result.series("step_resistance_ohm"), np.full(voltage.shape[1], 1e9))
    np.testing.assert_allclose(result.series("v_bus2_rms_v"), np.sqrt(np.mean(voltage**2, axis=0)))
    for output, current in (("p_import_12_w", from_bus1), ("p_import_32_w", from_bus3), ("p_step_w", added)):
        power = np.sum(voltage * current, axis=0)
        assert np.max(np.abs(power)) > 0
        np.testing.assert_allclose(result.series(output), power, atol=1e-10, rtol=1e-12)


@pytest.mark.parametrize("step", STEPS)
def test_added_load_closes_on_the_300_ms_electrical_row(define_case, step):
    case = define_case(time_step=step, stop_time=.002)
    load_tick = round(.300 / step)
    for phase in PHASES:
        switch = next(part for part in case.components if part.name == f"Rstep_{phase}")
        assert isinstance(switch, IdealSwitch) and callable(switch.closed)
        assert switch.open_conductance == 1e-9 and switch.closed_resistance == 10580
        assert [switch.closed(j * step) for j in range(load_tick - 1, load_tick + 2)] == [False, True, True]
        assert not switch.closed(.300 - .25 * step)
