"""Independent piecewise state solution, conservation and events for example 19."""

import runpy
from dataclasses import replace
from itertools import pairwise
from pathlib import Path

import numpy as np
import pytest
from scipy.linalg import expm

from pycy_emt_lite import Circuit, Simulator

EXAMPLE = Path(__file__).resolve().parents[1] / "examples/19_cascaded_rc.py"


def simulate(step=2e-6, method="trapezoidal"):
    case = runpy.run_path(str(EXAMPLE))["define_case"]()
    return Simulator(Circuit.from_components(case.name, case.components),
                     replace(case.config, time_step=step, method=method), events=case.events).run()


def exact_states(times):
    # Independently derived KCL, not production companion/stamp/update.
    matrix = np.array([[-2000.0, 1000.0], [1000.0, -1000.0]])
    eigenvalues, vectors = np.linalg.eigh(matrix)
    edges = [0.0, 0.001, 0.006, 0.011, 0.016, 0.0200001]
    levels = [0.0, 5.0, 0.0, 5.0, 0.0]
    reference = np.empty((times.size, 2))
    state = np.zeros(2)
    for start, end, level in zip(edges[:-1], edges[1:], levels, strict=True):
        steady = np.full(2, level)
        mask = (times >= start) & (times < end)
        elapsed = times[mask] - start
        reference[mask] = steady + ((np.exp(elapsed[:, None] * eigenvalues) * (vectors.T @ (state - steady))) @ vectors.T)
        state = steady + expm(matrix * (end - start)) @ (state - steady)
    return reference


def test_coupled_states_source_edges_kcl_and_energy():
    result = simulate()
    time = result.series("time")
    voltages = np.column_stack((result.series("v:n1"), result.series("v:n2")))
    assert np.max(np.abs(voltages - exact_states(time))) < 2e-6
    assert np.all(np.isfinite(voltages))
    assert [(event["time"], event["after"]) for event in result.event_log] == pytest.approx(
        [(0.001, 5.0), (0.006, 0.0), (0.011, 5.0), (0.016, 0.0)])
    i1, i2 = result.series("i:R1"), result.series("i:R2")
    assert np.max(np.abs(i1 - i2 - result.series("i:C1"))) < 1e-10
    assert np.max(np.abs(i2 - result.series("i:C2"))) < 1e-10
    falling = np.argmin(np.abs(time - 0.006))
    assert result.series("v:src")[falling] == 0
    assert i1[falling] < 0 < i2[falling]  # C2 still charging briefly after source falls.

    # TR discrete work balance. Event samples are right-sided, so recover the
    # left source/current at an interval's endpoint before accounting its work.
    source_left = result.series("v:src")[1:].copy()
    for event in result.event_log:
        index = np.argmin(np.abs(time - event["time"]))
        source_left[index - 1] = event["before"]
    current_left = (source_left - voltages[1:, 0]) / 10.0
    midpoint_i1 = (i1[:-1] + current_left) / 2
    midpoint_i2 = (i2[:-1] + i2[1:]) / 2
    midpoint_source = (result.series("v:src")[:-1] + source_left) / 2
    energy = 0.5e-4 * np.sum(voltages**2, axis=1)
    work = np.diff(time) * (midpoint_source * midpoint_i1 - 10 * midpoint_i1**2 - 10 * midpoint_i2**2)
    assert np.max(np.abs(np.diff(energy) - work)) < 1e-13


@pytest.mark.parametrize("method, bounds", [("trapezoidal", (3.8, 4.2)), ("backward_euler", (1.9, 2.1))])
def test_piecewise_step_refinement(method, bounds):
    errors = []
    for step in (8e-6, 4e-6, 2e-6):
        # 1 ms is not aligned to 8 us: this also exercises inserted edge times.
        result = simulate(step, method)
        actual = np.column_stack((result.series("v:n1"), result.series("v:n2")))
        errors.append(float(np.max(np.abs(actual - exact_states(result.series("time"))))))
    assert all(bounds[0] < a / b < bounds[1] for a, b in pairwise(errors))
