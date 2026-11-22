"""Check the PLL's connection to the controller and the solved switching circuit."""

import math
import runpy
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from pycy_emt_lite.cases import OutputOptions, run_case

EXAMPLE = Path(__file__).resolve().parents[1] / "examples/30_grid_connected_vsc_pll.py"
PHASES = "abc"
SAMPLE_PERIOD = 100e-6
GATE_PERIOD = 5e-6
INITIAL_ANGLE = 19 * math.pi / 12
GRID_OMEGA = math.tau * 60


@pytest.fixture(scope="module")
def define_case():
    return runpy.run_path(str(EXAMPLE))["define_case"]


def project_dq(values, angle):
    """Project measured phase values independently of the production Clarke/Park code."""
    angles = (angle, angle - math.tau / 3, angle + math.tau / 3)
    d = 2 / 3 * sum(value * math.cos(a) for value, a in zip(values, angles, strict=True))
    q = -2 / 3 * sum(value * math.sin(a) for value, a in zip(values, angles, strict=True))
    return d, q


@pytest.mark.parametrize("step", [5e-6, 2.5e-6])
def test_pll_advances_at_solved_samples_and_gates_use_the_next_tick(define_case, step):
    case = define_case(time_step=step, stop_time=.000605)
    result = run_case(replace(case, plots=(), output=OutputOptions(show_figure=False), summary=None))
    sample_stride = round(SAMPLE_PERIOD / step)
    gate_stride = round(GATE_PERIOD / step)
    rows = np.arange(len(result.rows))
    samples = np.arange(1, 7) * sample_stride
    assert rows[-1] == samples[-1] + gate_stride
    np.testing.assert_array_equal(np.flatnonzero(result.series("sample_update")), samples)

    theta, omega, integral = INITIAL_ANGLE, GRID_OMEGA, 0.
    initial = result.rows[0]
    assert initial["theta"] == pytest.approx(theta, abs=1e-12, rel=0)
    assert initial["pll_omega"] == pytest.approx(omega, abs=1e-10, rel=0)
    assert initial["pll_xi"] == initial["pll_error"] == 0
    for number, index in enumerate(samples):
        row = result.rows[index]
        theta = (theta + omega * SAMPLE_PERIOD) % math.tau
        voltage = tuple(row[f"v:grid_{phase}"] for phase in PHASES)
        ed, eq = project_dq(voltage, theta)
        assert eq < 0
        base = max(abs(ed), abs(eq), 1.)
        assert (base == 1.) == (number == 0)
        error = eq / base
        integral += 1_000 * SAMPLE_PERIOD * error
        omega = GRID_OMEGA + 100 * error + integral
        assert omega < GRID_OMEGA
        assert (row["ed"], row["eq"]) == pytest.approx((ed, eq), abs=1e-12, rel=0)
        assert row["theta"] == pytest.approx(theta, abs=1e-12, rel=0)
        assert row["pll_error"] == pytest.approx(error, abs=1e-12, rel=0)
        assert row["pll_xi"] == pytest.approx(integral, abs=1e-12, rel=0)
        assert row["pll_omega"] == pytest.approx(omega, abs=1e-10, rel=0)

    held_sample = rows // sample_stride * sample_stride
    for field in ("theta", "pll_omega", "pll_xi"):
        state = np.asarray(result.series(field))
        np.testing.assert_array_equal(state, state[held_sample])
    errors = np.asarray(result.series("pll_error"))
    assert np.all(errors[rows % sample_stride != 0] == 0)

    carrier = np.abs((rows // gate_stride) % 200 - 100) / 50 - 1
    np.testing.assert_allclose(result.series("carrier_applied"), carrier, atol=1e-14, rtol=0)
    assert any(result.series(f"pending_{phase}")[samples[0]] != 0 for phase in PHASES)
    for phase in PHASES:
        pending = result.series(f"pending_{phase}")
        expected = np.zeros(len(rows))
        for sample in samples:
            expected[sample + gate_stride:] = pending[sample]
        np.testing.assert_array_equal(result.series(f"applied_{phase}"), expected)
        upper = expected >= carrier
        np.testing.assert_array_equal(result.series(f"state:S{phase}_upper"), upper)
        np.testing.assert_array_equal(result.series(f"state:S{phase}_lower"), ~upper)


def first_sample():
    """Use a balanced voltage and currents with both dq components present."""
    angle = GRID_OMEGA * SAMPLE_PERIOD - math.pi / 2
    shifts = (0., -math.tau / 3, math.tau / 3)
    voltages = {f"v:grid_{phase}": 30 * math.cos(angle + shift)
                for phase, shift in zip(PHASES, shifts, strict=True)}
    currents = {f"i:L{phase}": current for phase, current in zip(PHASES, (2., -.5, -1.5), strict=True)}
    return {"time": SAMPLE_PERIOD, **voltages, **currents}


def test_current_loop_uses_estimated_angle_and_nominal_decoupling(define_case):
    observe = define_case().on_step
    assert observe is not None
    sample = first_sample()
    row = observe(sample)
    theta = INITIAL_ANGLE + GRID_OMEGA * SAMPLE_PERIOD
    ed, eq = project_dq(tuple(sample[f"v:grid_{phase}"] for phase in PHASES), theta)
    id_, iq = project_dq(tuple(sample[f"i:L{phase}"] for phase in PHASES), theta)
    assert (row["id"], row["iq"]) == pytest.approx((id_, iq), abs=1e-12, rel=0)
    assert row["pll_omega"] < GRID_OMEGA and row["saturated"] == 0

    # The first current PI output uses zero initial integral, R=1 Ω and L=10 mH.
    first_pi_gain = math.tau * 100 * (.01 + SAMPLE_PERIOD)
    cross_coupling = GRID_OMEGA * .01
    expected = (ed + cross_coupling * iq + first_pi_gain * id_,
                eq - cross_coupling * id_ + first_pi_gain * iq)
    pending_voltage = tuple(200 * row[f"pending_{phase}"] for phase in PHASES)
    assert project_dq(pending_voltage, theta) == pytest.approx(expected, abs=1e-12, rel=0)


def test_case_instances_keep_separate_pll_and_modulation_state(define_case):
    first, second = (define_case().on_step for _ in range(2))
    assert first is not None and second is not None
    sample = first_sample()
    advanced = first(sample)
    initial = second(dict.fromkeys(sample, 0.))
    assert initial["theta"] != advanced["theta"]
    assert initial["theta"] == pytest.approx(INITIAL_ANGLE, abs=1e-12, rel=0)
    assert initial["pll_omega"] == pytest.approx(GRID_OMEGA, abs=1e-10, rel=0)
    assert initial["pll_xi"] == initial["pll_error"] == initial["sample_update"] == 0
    assert all(initial[f"pending_{phase}"] == initial[f"applied_{phase}"] == 0 for phase in PHASES)
    assert second(sample) == advanced
