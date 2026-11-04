"""Exact rational KCL solution and signed power for the seven-resistor example."""

import runpy
from pathlib import Path

import numpy as np
import pytest

from pycy_emt_lite import Circuit, Simulator


def test_nodal_voltages_kcl_and_both_sources_power():
    example = Path(__file__).resolve().parents[1] / "examples/20_multi_source_nodal_network.py"
    case = runpy.run_path(str(example))["define_case"]()
    result = Simulator(Circuit.from_components(case.name, case.components), case.config, on_step=case.on_step).run()
    # Independent exact elimination is documented in experiments/nodal_analysis_exact.md:
    # 47*a - 14*b = 1023; -380*a + 3845*b = -1419; c=a+400; d=(5*b-330)/38.
    expected = {"src": 3, "a": 118593 / 5315, "b": 9759 / 5315,
                "c": 2244593 / 5315, "d": -17949 / 2126}
    for name, value in expected.items():
        np.testing.assert_allclose(result.series("v:" + name), value, rtol=0, atol=1e-10)
    row = result.rows[0]
    currents = {name: row["i:" + name] for name in ("R1", "R2", "R3", "R4", "R5", "R6", "R7", "Vs", "Is")}
    assert currents["Is"] == -0.2
    assert currents["R4"] == pytest.approx(-0.2, abs=1e-14)
    assert currents["Vs"] == pytest.approx(70227 / 531500, abs=1e-14)
    residuals = [currents["R1"] + currents["R2"] + currents["Vs"],
                 -currents["R2"] + currents["R3"] + currents["R4"],
                 -currents["R1"] - currents["R3"] + currents["R5"] + currents["R6"],
                 -currents["R4"] + currents["Is"], -currents["Is"] - currents["R5"] + currents["R7"]]
    assert max(abs(value) for value in residuals) < 1e-13
    source_power = 3 * currents["Vs"] + (expected["c"] - expected["d"]) * currents["Is"]
    loss = sum(currents[f"R{k}"] ** 2 * resistance for k, resistance in enumerate((200, 140, 330, 2000, 330, 50, 50), 1))
    assert loss == pytest.approx(45578629 / 531500, abs=1e-10)
    assert abs(loss + source_power) < 1e-10
    assert 3 * currents["Vs"] > 0  # Voltage source absorbs, current source supplies.
    assert result.rows[-1] | {"time": 0.0} == result.rows[0]
