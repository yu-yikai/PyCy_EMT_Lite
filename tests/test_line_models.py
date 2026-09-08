"""
文件名称：test_line_models.py
文件作用：验证 π 型线路和 Bergeron 线路教学模型。
"""

import math

import numpy as np
import pytest

from pycy_emt_lite import Circuit, PiLine, Resistor, SimulationConfig, Simulator, VoltageSource
from pycy_emt_lite.components.lines import (
    BergeronLine,
    SegmentedLine,
    ThreePhaseBergeronLine,
    ThreePhasePiLine,
)


@pytest.mark.parametrize(
    ("parameter", "value"),
    (("resistance", math.nan), ("inductance", math.inf), ("capacitance", math.nan)),
)
def test_pi_line_rejects_nonfinite_parameters(parameter: str, value: float) -> None:
    values = {"resistance": 1.0, "inductance": 0.0, "capacitance": 1e-6}
    values[parameter] = value

    with pytest.raises(ValueError, match="有限"):
        PiLine("LINE", "source", "load", **values)


@pytest.mark.parametrize("sections", (0, 1.5, True))
def test_segmented_line_requires_a_positive_integer_section_count(sections: int | float | bool) -> None:
    with pytest.raises(ValueError, match="正整数"):
        SegmentedLine("LINE", "source", "load", 1.0, 0.0, 1e-6, sections)


def test_segmented_line_accepts_numpy_integer_section_count() -> None:
    line = SegmentedLine("LINE", "source", "load", 1.0, 0.0, 1e-6, np.int64(1))

    assert len(line.series_states) == 1


@pytest.mark.parametrize(
    ("surge_impedance", "travel_time"),
    ((math.nan, 1e-3), (10.0, math.inf), (math.inf, 1e-3), (10.0, -math.inf)),
)
def test_bergeron_line_rejects_nonfinite_construction_parameters(
    surge_impedance: float, travel_time: float
) -> None:
    with pytest.raises(ValueError):
        BergeronLine("LINE", "source", "load", surge_impedance, travel_time)


def test_pi_line_reaches_resistive_divider_at_steady_state() -> None:
    components = [
        VoltageSource("V1", "source", "0", 10.0),
        PiLine("LINE", "source", "load", resistance=1.0, inductance=0.0, capacitance=1e-6),
        Resistor("LOAD", "load", "0", 9.0),
    ]
    circuit = Circuit.from_components("pi_line_divider", components)
    config = SimulationConfig(time_step=1e-4, stop_time=0.02)
    simulator = Simulator(circuit, config)

    result = simulator.run()

    assert math.isclose(result.rows[-1]["v:load"], 9.0, rel_tol=0.0, abs_tol=5e-3)
    assert math.isclose(result.rows[-1]["i:LINE:series"], 1.0, rel_tol=0.0, abs_tol=5e-3)


def test_bergeron_line_runs_and_records_terminal_currents() -> None:
    components = [
        VoltageSource("V1", "source", "0", 10.0),
        BergeronLine("BL", "source", "load", surge_impedance=10.0, travel_time=1e-3),
        Resistor("LOAD", "load", "0", 10.0),
    ]
    circuit = Circuit.from_components("bergeron_line", components)
    config = SimulationConfig(time_step=2e-4, stop_time=4e-3)
    simulator = Simulator(circuit, config)

    result = simulator.run()

    assert "i:BL:sending" in result.columns
    assert "i:BL:receiving" in result.columns
    assert np.isfinite(result.series("i:BL:sending")).all()


def test_three_phase_line_models_expose_phase_outputs() -> None:
    components = [
        ThreePhasePiLine("TPL", "from", "to", resistance=1.0, inductance=0.0, capacitance=1e-6),
        ThreePhaseBergeronLine("TBL", "to", "remote", surge_impedance=50.0, travel_time=1e-3),
        Resistor("RA", "from:a", "0", 10.0),
        Resistor("RB", "from:b", "0", 10.0),
        Resistor("RC", "from:c", "0", 10.0),
    ]
    circuit = Circuit.from_components("three_phase_line_outputs", components)
    config = SimulationConfig(time_step=1e-4, stop_time=1e-4)
    simulator = Simulator(circuit, config)

    result = simulator.run()

    assert "i:TPL:series:a" in result.columns
    assert "i:TBL:sending:a" in result.columns


def test_segmented_line_matches_resistive_divider_at_steady_state() -> None:
    """分段线路在直流稳态下应退化为总电阻分压。"""

    components = [
        VoltageSource("V1", "source", "0", 10.0),
        SegmentedLine("SL", "source", "load", resistance=1.0, inductance=0.0, capacitance=1e-6, sections=4),
        Resistor("LOAD", "load", "0", 9.0),
    ]
    circuit = Circuit.from_components("segmented_line", components)
    config = SimulationConfig(time_step=1e-4, stop_time=0.02)
    simulator = Simulator(circuit, config)

    result = simulator.run()

    assert math.isclose(result.rows[-1]["v:load"], 9.0, rel_tol=0.0, abs_tol=5e-3)
    assert "i:SL:average" in result.columns
