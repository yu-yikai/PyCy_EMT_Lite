"""Minimal feasibility experiment; not a formal teaching example or vendor reference.

Run from the repository root with python -m docs.development_roadmap.experiments.cascaded_rc_probe.
"""

import json
from pathlib import Path

import numpy as np
from scipy.linalg import expm

from pycy_emt_lite import Capacitor, Circuit, Resistor, SimulationConfig, Simulator, VoltageSource


def main():
    # KCL gives C1*v1'=(5-v1)/R1-(v1-v2)/R2 and C2*v2'=(v1-v2)/R2.
    matrix = np.array([[-2000.0, 1000.0], [1000.0, -1000.0]])
    steady = np.array([5.0, 5.0])
    observations = {}
    for method in ("trapezoidal", "backward_euler"):
        errors = []
        for step in (20e-6, 10e-6, 5e-6):
            circuit = Circuit.from_components("probe", (
                VoltageSource("V", "src", "0", 5.0),
                Resistor("R1", "src", "n1", 10.0), Resistor("R2", "n1", "n2", 10.0),
                Capacitor("C1", "n1", "0", 100e-6), Capacitor("C2", "n2", "0", 100e-6),
            ))
            result = Simulator(circuit, SimulationConfig(step, 0.01, method=method)).run()
            reference = np.array([steady - expm(matrix * time) @ steady for time in result.series("time")])
            actual = np.column_stack([result.series("v:n1"), result.series("v:n2")])
            errors.append(float(np.max(np.abs(actual - reference))))
            residual1 = result.series("i:R1") - result.series("i:R2") - result.series("i:C1")
            residual2 = result.series("i:R2") - result.series("i:C2")
            assert max(np.max(np.abs(residual1)), np.max(np.abs(residual2))) < 1e-10
        ratios = [errors[0] / errors[1], errors[1] / errors[2]]
        lower, upper = (3.8, 4.2) if method == "trapezoidal" else (1.9, 2.1)
        assert all(lower < ratio < upper for ratio in ratios)
        observations[method] = {"max_voltage_errors": errors, "refinement_ratios": ratios}
    target = Path(".tmp/longterm/cascaded-rc-probe.json")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(observations, indent=2), encoding="utf-8")
    print(json.dumps(observations, indent=2))


if __name__ == "__main__":
    main()
