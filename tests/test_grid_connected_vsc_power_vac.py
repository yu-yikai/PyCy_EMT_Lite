"""Check PCC references and their connection to the switched circuit."""

import math
import runpy
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from pycy_emt_lite.cases import OutputOptions, run_case
from pycy_emt_lite.controls import PIController

EXAMPLE = Path(__file__).resolve().parents[1] / "examples/31_grid_connected_vsc_power_vac.py"
PHASES = "abc"
INITIAL_ANGLE = 19 * math.pi / 12
OMEGA = math.tau * 60


@pytest.fixture(scope="module")
def example():
    return runpy.run_path(str(EXAMPLE))


def test_active_priority_and_voltage_pi_anti_windup(example):
    current_reference = example["_current_reference"]
    voltage_pi = PIController(.15, 6.)
    magnitude = 100 * math.sqrt(2)
    vd, vq = .6 * magnitude, .8 * magnitude
    (id_ref, iq_ref), active, reactive = current_reference(vd, vq, 500., voltage_pi)
    assert active == pytest.approx(500 / (1.5 * magnitude))
    assert reactive == pytest.approx(math.sqrt(2.5**2 - active**2))
    assert math.hypot(id_ref, iq_ref) == pytest.approx(2.5)
    assert 1.5 * (vd * id_ref + vq * iq_ref) == pytest.approx(500.)
    assert voltage_pi.integrator == 0

    reference, active, reactive = current_reference(25 * math.sqrt(2), 0., 500., voltage_pi)
    assert (reference, active, reactive) == ((2.5, 0.), 2.5, 0.)
    assert voltage_pi.integrator == 0

    voltage_pi = PIController(.15, 6., integrator=4.)
    _, active, reactive = current_reference(122 * math.sqrt(2), 0., 500., voltage_pi)
    assert reactive == pytest.approx(math.sqrt(2.5**2 - active**2))
    assert voltage_pi.integrator == pytest.approx(4. - 6 * 2 * .001)
    before = voltage_pi.integrator, voltage_pi.last_output
    assert current_reference(0., 0., 500., voltage_pi) == ((0., 0.), 0., 0.)
    assert (voltage_pi.integrator, voltage_pi.last_output) == before


def pcc_row(time, amplitude, angle):
    shifts = (0., -math.tau / 3, math.tau / 3)
    return {
        "time": time,
        **dict.fromkeys((f"v:grid_{phase}" for phase in PHASES), 0.),
        **dict.fromkeys((f"i:L{phase}" for phase in PHASES), 0.),
        **{f"v:pcc_{phase}": amplitude * math.cos(angle + shift)
           for phase, shift in zip(PHASES, shifts, strict=True)},
    }


def test_voltage_loop_enables_on_the_shared_sample_and_held_uses_pcc_axes(example):
    step = 5e-6
    magnitude = 120 * math.sqrt(2)
    define_case = example["define_case"]
    held = define_case(scenario="held", time_step=step).on_step
    regulated = define_case(time_step=step).on_step
    assert held is not None and regulated is not None
    initial = pcc_row(0., 0., INITIAL_ANGLE)
    assert held(initial) == regulated(initial)

    # Warm the filter with controlled measurements before the 240 ms edge.
    # Zero upstream voltage keeps the PLL at nominal frequency in this check.
    start, enable = round(.210 / step), round(.240 / step)
    for index in range(start, enable):
        angle = INITIAL_ANGLE + OMEGA * (100e-6 + (index - start) * step)
        row = pcc_row(index * step, magnitude, angle + .3)
        before = regulated(row)
        assert held(row) == before
    assert before["iq_pcc_ref"] == before["vac_integrator"] == before["outer_update"] == 0

    angle = INITIAL_ANGLE + OMEGA * (100e-6 + (enable - start) * step)
    row = pcc_row(enable * step, magnitude, angle + .6)
    actual, baseline = regulated(row), held(row)
    assert actual["outer_update"] == actual["sample_update"] == 1
    assert actual["p_ref_w"] == baseline["p_ref_w"] == 500
    weight = step / .01
    vd = (before["pcc_d_filtered"] + weight * magnitude * math.cos(.6)) / (1 + weight)
    vq = (before["pcc_q_filtered"] + weight * magnitude * math.sin(.6)) / (1 + weight)
    assert (actual["pcc_d_filtered"], actual["pcc_q_filtered"]) == pytest.approx((vd, vq))
    voltage = math.hypot(vd, vq)
    active = 500 / (1.5 * voltage)
    reactive = (.15 + 6 * .001) * (120 - voltage / math.sqrt(2))
    assert actual["iq_pcc_ref"] == pytest.approx(reactive) and reactive > 0
    assert (actual["id_ref"], actual["iq_ref"]) == pytest.approx(
        ((vd * active - vq * reactive) / voltage, (vq * active + vd * reactive) / voltage)
    )
    assert baseline["iq_pcc_ref"] == baseline["vac_integrator"] == 0
    assert baseline["iq_ref"] == pytest.approx(vq * active / voltage)
    after = regulated(pcc_row((enable + 1) * step, magnitude, angle + OMEGA * step + .6))
    assert after["outer_update"] == after["sample_update"] == 0
    assert after["iq_pcc_ref"] == actual["iq_pcc_ref"]


@pytest.mark.parametrize("step", [5e-6, 2.5e-6])
def test_solved_switching_rows_use_next_tick_including_fine_midpoints(example, step):
    case = example["define_case"](time_step=step, stop_time=.001005)
    result = run_case(replace(case, plots=(), output=OutputOptions(show_figure=False), summary=None))
    index = np.arange(len(result.rows))
    sample_stride, gate_stride = round(100e-6 / step), round(5e-6 / step)
    samples = np.arange(1, 11) * sample_stride
    np.testing.assert_array_equal(np.flatnonzero(result.series("sample_update")), samples)
    np.testing.assert_array_equal(np.flatnonzero(result.series("outer_update")), [samples[-1]])
    theta = np.asarray(result.series("theta"))
    omega = np.asarray(result.series("pll_omega"))
    np.testing.assert_allclose(
        result.series("pcc_theta"), theta + (index % sample_stride) * step * omega, atol=1e-12, rtol=0,
    )

    carrier = np.abs((index // gate_stride) % 200 - 100) / 50 - 1
    for phase in PHASES:
        pending = result.series(f"pending_{phase}")
        applied = np.zeros(len(index))
        for sample in samples:
            applied[sample + gate_stride:] = pending[sample]
        np.testing.assert_array_equal(result.series(f"applied_{phase}"), applied)
        upper = applied >= carrier
        np.testing.assert_array_equal(result.series(f"state:S{phase}_upper"), upper)
        np.testing.assert_array_equal(result.series(f"state:S{phase}_lower"), ~upper)
    assert any(result.series(f"pending_{phase}")[samples[0]] != 0 for phase in PHASES)
