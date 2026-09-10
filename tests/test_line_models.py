"""
文件名称：test_line_models.py
文件作用：验证 π 型线路和 Bergeron 线路教学模型。
"""

import math

import numpy as np
import pytest

from pycy_emt_lite import Capacitor, Circuit, CurrentSource, Fault, FaultApplyEvent, Inductor, PiLine, Resistor, SimulationConfig, Simulator, VoltageSource
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


def test_pi_line_preserves_dc_divider_with_consistent_initial_voltages() -> None:
    line = PiLine("LINE", "source", "load", resistance=1.0, inductance=0.0, capacitance=1e-6)
    line.sending_cap_state.previous_voltage = 10.0
    line.receiving_cap_state.previous_voltage = 9.0
    components = [
        VoltageSource("V1", "source", "0", 10.0),
        line,
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


def test_segmented_line_preserves_dc_divider_with_consistent_initial_voltages() -> None:
    """分段线路在直流稳态下应退化为总电阻分压。"""

    line = SegmentedLine("SL", "source", "load", resistance=1.0, inductance=0.0, capacitance=1e-6, sections=4)
    for index in range(line.sections):
        line.sending_cap_states[index].previous_voltage = 10.0 - index / line.sections
        line.receiving_cap_states[index].previous_voltage = 10.0 - (index + 1) / line.sections
    components = [
        VoltageSource("V1", "source", "0", 10.0),
        line,
        Resistor("LOAD", "load", "0", 9.0),
    ]
    circuit = Circuit.from_components("segmented_line", components)
    config = SimulationConfig(time_step=1e-4, stop_time=0.02)
    simulator = Simulator(circuit, config)

    result = simulator.run()

    assert math.isclose(result.rows[-1]["v:load"], 9.0, rel_tol=0.0, abs_tol=5e-3)
    assert "i:SL:average" in result.columns


@pytest.mark.parametrize("kind", ["pi", "segmented", "three_phase"])
@pytest.mark.parametrize("method", ["trapezoidal", "backward_euler"])
def test_line_initial_state_and_first_step_match_separate_rlc_branches(kind, method) -> None:
    if kind == "pi":
        line = PiLine("LINE", "send", "recv", 1.0, 2.0, 4.0)
        sending, receiving, sections = ["send"], ["recv"], 1
        current_column = "i:LINE:series"
    elif kind == "segmented":
        line = SegmentedLine("LINE", "send", "recv", 1.0, 2.0, 4.0, sections=2)
        sending, receiving, sections = ["send"], ["recv"], 2
        current_column = "i:LINE:sending"
    else:
        line = ThreePhasePiLine("LINE", "send", "recv", 1.0, 2.0, 4.0)
        sending, receiving, sections = [f"send:{p}" for p in "abc"], [f"recv:{p}" for p in "abc"], 1
        current_column = "i:LINE:series:a"

    def terminals():
        return [part for s, r in zip(sending, receiving) for part in (
            CurrentSource(f"I{s}", "0", s, 1.0), Resistor(f"R{r}", r, "0", 3.0)
        )]

    equivalent = terminals()
    for s, r in zip(sending, receiving):
        endpoints = [s] + [f"mid{j}" for j in range(1, sections)] + [r]
        for j, (p, n) in enumerate(zip(endpoints, endpoints[1:])):
            equivalent.extend([
                Resistor(f"R{s}{j}", p, f"rl{s}{j}", 1.0 / sections),
                Inductor(f"L{s}{j}", f"rl{s}{j}", n, 2.0 / sections),
                Capacitor(f"Cs{s}{j}", p, "0", 2.0 / sections),
                Capacitor(f"Cr{s}{j}", n, "0", 2.0 / sections),
            ])
    config = SimulationConfig(0.1, 0.1, method=method)
    result = Simulator(Circuit.from_components("composite", [line, *terminals()]), config).run()
    reference = Simulator(Circuit.from_components("separate", equivalent), config).run()
    for node in sending + receiving:
        np.testing.assert_allclose(result.series(f"v:{node}"), reference.series(f"v:{node}"), atol=1e-12)
    np.testing.assert_allclose(result.series(current_column), reference.series(f"i:L{sending[0]}0"), atol=1e-12)
    assert result.rows[0][current_column] == pytest.approx(0.0, abs=1e-12)


def test_bergeron_initial_sample_launches_wave_without_advancing_time() -> None:
    line = BergeronLine("BL", "send", "recv", 10.0, 0.2)
    result = Simulator(Circuit.from_components("initial_wave", [
        VoltageSource("V", "send", "0", 10.0), line, Resistor("R", "recv", "0", 10.0),
    ]), SimulationConfig(0.1, 0.3)).run()
    assert [sample.time for sample in line.history] == pytest.approx([0.0, 0.1, 0.2, 0.3])
    assert result.series("v:recv") == pytest.approx([0.0, 0.0, 10.0, 10.0])
    assert result.series("i:BL:receiving") == pytest.approx([0.0, 0.0, -1.0, -1.0])


def test_aligned_bergeron_event_keeps_only_right_side_history_sample() -> None:
    line = BergeronLine("BL", "send", "recv", 10.0, 0.2)
    result = Simulator(Circuit.from_components("line_event", [
        VoltageSource("V", "send", "0", 10.0), line, Resistor("R", "recv", "0", 10.0),
        Fault("F", "recv", 10.0),
    ]), SimulationConfig(0.1, 0.4), events=[FaultApplyEvent(0.2, "F")]).run()
    assert [sample.time for sample in line.history] == pytest.approx(result.series("time"))
    assert line.history[2].receiving_voltage == pytest.approx(20 / 3)
    assert result.rows[-1]["i:BL:sending"] == pytest.approx(5 / 3)
