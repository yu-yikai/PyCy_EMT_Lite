"""
文件名称：test_three_phase.py
文件作用：验证三相电源、线路和负荷模型的基础数值行为。
"""

import math

import pytest

from pycy_emt_lite import (
    Circuit,
    SimulationConfig,
    Simulator,
    ThreePhaseLine,
    ThreePhaseLoad,
    ThreePhaseParallelRLCLoad,
    ThreePhaseSource,
)
from pycy_emt_lite.analysis import three_phase_rms


def test_three_phase_source_load_has_balanced_rms() -> None:
    components = [
        ThreePhaseSource("VS", "source", phase_rms=230.0),
        ThreePhaseLine("LINE", "source", "load", resistance=0.5, inductance=0.0),
        ThreePhaseLoad("LOAD", "load", resistance=20.0),
    ]
    circuit = Circuit.from_components("three_phase_balanced", components)

    config = SimulationConfig(time_step=1e-4, stop_time=0.1)
    simulator = Simulator(circuit, config)
    result = simulator.run()
    rms_values = three_phase_rms(
        result,
        ("v:load:a", "v:load:b", "v:load:c"),
        start_time=0.06,
        end_time=0.1,
    )

    assert all(220.0 < value < 230.0 for value in rms_values.values())
    assert math.isclose(rms_values["v:load:a"], rms_values["v:load:b"], rel_tol=2e-3)
    assert math.isclose(rms_values["v:load:b"], rms_values["v:load:c"], rel_tol=2e-3)


def test_three_phase_line_records_phase_currents() -> None:
    components = [
        ThreePhaseSource("VS", "source", phase_rms=100.0),
        ThreePhaseLine("LINE", "source", "load", resistance=1.0),
        ThreePhaseLoad("LOAD", "load", resistance=9.0),
    ]
    circuit = Circuit.from_components("three_phase_current", components)

    config = SimulationConfig(time_step=1e-4, stop_time=0.02)
    simulator = Simulator(circuit, config)
    result = simulator.run()

    assert "i:LINE:a" in result.columns
    assert "i:LINE:b" in result.columns
    assert "i:LINE:c" in result.columns
    assert max(abs(value) for value in result.series("i:LINE:a")) > 1.0


def test_three_phase_parallel_rlc_load_converts_nominal_power_to_branches() -> None:
    load = ThreePhaseParallelRLCLoad(
        "LOAD",
        "bus",
        nominal_line_voltage=230_000.0,
        active_power=90e6,
        inductive_power=30e6,
        capacitive_power=3e6,
        frequency=60.0,
    )

    phase_voltage = 230_000.0 / math.sqrt(3.0)
    assert math.isclose(load.phase_conductance, (90e6 / 3.0) / phase_voltage**2)
    assert math.isclose(load.phase_inductance, phase_voltage**2 / (2.0 * math.pi * 60.0 * (30e6 / 3.0)))
    assert math.isclose(load.phase_capacitance, (3e6 / 3.0) / (2.0 * math.pi * 60.0 * phase_voltage**2))


def test_three_phase_parallel_rlc_load_records_outputs() -> None:
    components = [
        ThreePhaseSource("VS", "source", phase_rms=100.0, frequency=60.0),
        ThreePhaseLine("LINE", "source", "load", resistance=0.1),
        ThreePhaseParallelRLCLoad(
            "LOAD",
            "load",
            nominal_line_voltage=math.sqrt(3.0) * 100.0,
            active_power=3000.0,
            inductive_power=900.0,
            frequency=60.0,
        ),
    ]
    circuit = Circuit.from_components("three_phase_parallel_load", components)

    config = SimulationConfig(time_step=1e-4, stop_time=0.04)
    simulator = Simulator(circuit, config)
    result = simulator.run()

    assert "i:LOAD:a" in result.columns
    assert "i:LOAD:L:a" in result.columns
    assert "r:LOAD:phase" in result.columns
    assert max(abs(value) for value in result.series("i:LOAD:a")) > 1.0


def test_three_phase_parallel_rlc_load_rejects_empty_load() -> None:
    with pytest.raises(ValueError, match="不能同时为 0"):
        ThreePhaseParallelRLCLoad(
            "LOAD",
            "bus",
            nominal_line_voltage=230_000.0,
            active_power=0.0,
            inductive_power=0.0,
            capacitive_power=0.0,
        )
