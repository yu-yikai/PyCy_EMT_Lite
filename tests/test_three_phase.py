"""
文件名称：test_three_phase.py
文件作用：验证三相电源、线路和负荷模型的基础数值行为。
"""

import math
import runpy
from pathlib import Path

import pytest

from pycy_emt_lite import (
    Circuit,
    SimulationConfig,
    Simulator,
    ThreePhaseLine,
    ThreePhaseLoad,
    ThreePhaseSource,
)
from pycy_emt_lite.analysis import three_phase_rms
from pycy_emt_lite.components.three_phase import ThreePhaseParallelRLCLoad


@pytest.mark.parametrize(
    ("parameter", "value"),
    (("phase_rms", math.nan), ("frequency", math.inf), ("initial_angle", -math.inf)),
)
def test_three_phase_source_rejects_nonfinite_parameters(parameter: str, value: float) -> None:
    values = {"phase_rms": 230.0, "frequency": 50.0, "initial_angle": 0.0}
    values[parameter] = value

    with pytest.raises(ValueError):
        ThreePhaseSource("VS", "source", **values)


@pytest.mark.parametrize(("resistance", "inductance"), ((math.nan, 0.0), (1.0, math.inf)))
def test_three_phase_line_rejects_nonfinite_series_parameters(resistance: float, inductance: float) -> None:
    with pytest.raises(ValueError):
        ThreePhaseLine("LINE", "source", "load", resistance, inductance)


@pytest.mark.parametrize(
    ("parameter", "value"),
    (("nominal_line_voltage", math.nan), ("frequency", math.inf), ("active_power", math.nan),
     ("inductive_power", math.nan), ("capacitive_power", math.nan)),
)
def test_parallel_rlc_load_rejects_nonfinite_parameters(parameter: str, value: float) -> None:
    values = {"nominal_line_voltage": 400.0, "active_power": 1_000.0, "frequency": 50.0}
    values[parameter] = value

    with pytest.raises(ValueError, match="有限"):
        ThreePhaseParallelRLCLoad("LOAD", "bus", **values)


def test_single_phase_fault_example_matches_resistive_dividers() -> None:
    example = runpy.run_path(str(Path(__file__).resolve().parents[1] / "examples/07_single_phase_ground_fault.py"))
    case = example["define_case"]()
    result = Simulator(Circuit.from_components(case.name, case.components), case.config, case.events).run()
    normal_voltage = 230.0 * 50.0 / (0.8 + 50.0)
    fault_resistance = 50.0 * 0.1 / (50.0 + 0.1)
    fault_voltage = 230.0 * fault_resistance / (0.8 + fault_resistance)
    for start, end, expected_a in ((0.01, 0.03, normal_voltage), (0.05, 0.07, fault_voltage), (0.09, 0.11, normal_voltage)):
        values = three_phase_rms(result, ("v:load:a", "v:load:b", "v:load:c"), start_time=start, end_time=end)
        # 50 Hz / 100 μs 分段线性重建的 RMS 相对误差小于 1e-4。
        assert values["v:load:a"] == pytest.approx(expected_a, rel=1e-4)
        assert values["v:load:b"] == pytest.approx(normal_voltage, rel=1e-4)
        assert values["v:load:c"] == pytest.approx(normal_voltage, rel=1e-4)


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
