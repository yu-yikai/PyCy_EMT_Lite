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


@pytest.mark.parametrize("three_phase", [False, True])
@pytest.mark.parametrize(("delay", "stop", "event_time"), [
    (0.05, 0.4, None),              # 不足一个步长：所需历史尚未求解
    (0.15, 0.4, None),              # 非整数延时
    (0.2, 0.4, 0.15),              # 默认 insert 产生短步
    (0.1 + 9 * math.ulp(0.1), 0.4, None),
    (0.1 - 9 * math.ulp(0.1), 0.4, None),
])
def test_bergeron_rejects_unsupported_grid_before_first_solve(three_phase, delay, stop, event_time) -> None:
    if three_phase:
        line = ThreePhaseBergeronLine("BL", "send", "recv", 10.0, delay)
        ports = [(f"send:{p}", f"recv:{p}") for p in "abc"]
        histories = [phase.history for phase in line.lines.values()]
    else:
        line = BergeronLine("BL", "send", "recv", 10.0, delay)
        ports = [("send", "recv")]
        histories = [line.history]
    terminals = [part for s, r in ports for part in (
        VoltageSource(f"V{s}", s, "0", 10.0), Resistor(f"R{r}", r, "0", 10.0),
    )]
    circuit = Circuit.from_components("unsupported_grid", [line, *terminals, Fault("F", ports[0][1], 10.0)])
    events = [FaultApplyEvent(0.0, "F")]
    if event_time is not None:
        events.append(FaultApplyEvent(event_time, "F"))
    simulator = Simulator(circuit, SimulationConfig(0.1, stop), events=events)
    with pytest.raises(ValueError, match="Bergeron.*固定.*步长"):
        simulator.run()
    assert simulator.solver.solve_count == 0
    assert simulator.event_log == []
    assert all(history == [] for history in histories)


@pytest.mark.parametrize("delay", [0.1 + 0.2, 3 * 0.1 + 8 * math.ulp(0.3), 3 * 0.1 - 8 * math.ulp(0.3)])
def test_bergeron_arrives_at_canonical_stop_without_roundoff_delay(delay) -> None:
    line = BergeronLine("BL", "send", "recv", 10.0, delay)
    result = Simulator(Circuit.from_components("canonical_arrival", [
        VoltageSource("V", "send", "0", 10.0), line, Resistor("R", "recv", "0", 10.0),
    ]), SimulationConfig(0.1, 0.3)).run()
    assert result.series("time") == pytest.approx([0.0, 0.1, 0.2, 0.3])
    assert result.series("v:recv") == pytest.approx([0.0, 0.0, 0.0, 10.0], abs=1e-12)


@pytest.mark.parametrize("delay", [0.1, 0.1 - 8 * math.ulp(0.1), 0.1 + 8 * math.ulp(0.1)])
def test_bergeron_one_step_delay_transmits_sampled_pulse_without_smearing(delay) -> None:
    line = BergeronLine("BL", "send", "recv", 10.0, delay)
    result = Simulator(Circuit.from_components("pulse", [
        VoltageSource("V", "send", "0", lambda t: 10.0 if t == 0.0 else 0.0),
        line, Resistor("R", "recv", "0", 10.0),
    ]), SimulationConfig(0.1, 0.4)).run()
    assert result.series("v:recv") == pytest.approx([0.0, 10.0, 0.0, 0.0, 0.0], abs=1e-12)


@pytest.mark.parametrize(("termination", "arrival_voltage", "arrival_current", "return_voltage", "return_current"), [
    ("matched", 5.0, -0.5, 5.0, 0.5),
    ("open", 10.0, 0.0, 10.0, 0.0),
    ("short", 0.0, -1.0, 0.0, 1.0),
])
def test_bergeron_matched_source_arrival_and_open_short_reflection(
    termination, arrival_voltage, arrival_current, return_voltage, return_current,
) -> None:
    line = BergeronLine("BL", "send", "recv", 10.0, 0.2)
    parts = [VoltageSource("V", "src", "0", 10.0), Resistor("RS", "src", "send", 10.0), line]
    if termination == "matched":
        parts.append(Resistor("RL", "recv", "0", 10.0))
    elif termination == "short":
        parts.append(VoltageSource("SHORT", "recv", "0", 0.0))
    result = Simulator(Circuit.from_components(termination, parts), SimulationConfig(0.1, 0.8)).run()
    assert result.series("v:recv")[:2] == pytest.approx([0.0, 0.0], abs=1e-12)
    assert result.series("i:BL:receiving")[:2] == pytest.approx([0.0, 0.0], abs=1e-12)
    assert result.series("v:recv")[2:] == pytest.approx([arrival_voltage] * 7, abs=1e-12)
    assert result.series("i:BL:receiving")[2:] == pytest.approx([arrival_current] * 7, abs=1e-12)
    assert result.series("v:send")[:4] == pytest.approx([5.0] * 4, abs=1e-12)
    assert result.series("i:BL:sending")[:4] == pytest.approx([0.5] * 4, abs=1e-12)
    assert result.series("v:send")[4:] == pytest.approx([return_voltage] * 5, abs=1e-12)
    assert result.series("i:BL:sending")[4:] == pytest.approx([return_current] * 5, abs=1e-12)


@pytest.mark.parametrize(("policy", "scheduled_time", "applied_time"), [
    ("quantize_up", 0.15, 0.2),
    ("insert", 0.2 + 8 * math.ulp(0.2), 0.2),
    ("require_aligned", 0.2, 0.2),
    ("insert", 0.45, None),        # 仿真外事件不改变实际网格
])
def test_bergeron_validates_actual_grid_and_propagates_event_right_side(policy, scheduled_time, applied_time) -> None:
    line = BergeronLine("BL", "send", "recv", 10.0, 0.2)
    result = Simulator(Circuit.from_components("event_grid", [
        VoltageSource("V", "send", "0", 10.0), line, Resistor("R", "recv", "0", 10.0),
        Fault("F", "recv", 10.0),
    ]), SimulationConfig(0.1, 0.4, event_time_policy=policy), events=[FaultApplyEvent(scheduled_time, "F")]).run()
    assert [sample.time for sample in line.history] == pytest.approx([0.0, 0.1, 0.2, 0.3, 0.4])
    if applied_time is None:
        assert result.event_log == []
        assert result.rows[-1]["i:BL:sending"] == pytest.approx(1.0)
    else:
        assert result.event_log[0]["time"] == pytest.approx(applied_time)
        assert line.history[2].receiving_voltage == pytest.approx(20 / 3)
        assert result.rows[-1]["i:BL:sending"] == pytest.approx(5 / 3)


def test_three_phase_bergeron_propagates_independent_matched_port_waves() -> None:
    line = ThreePhaseBergeronLine("BL", "send", "recv", 10.0, 0.2)
    terminals = []
    for phase, voltage in zip("abc", [10.0, -4.0, 2.0]):
        terminals.extend([
            VoltageSource(f"V{phase}", f"src:{phase}", "0", voltage),
            Resistor(f"RS{phase}", f"src:{phase}", f"send:{phase}", 10.0),
            Resistor(f"RL{phase}", f"recv:{phase}", "0", 10.0),
        ])
    result = Simulator(Circuit.from_components("three_phase_waves", [line, *terminals]), SimulationConfig(0.1, 0.4)).run()
    for phase, voltage in zip("abc", [5.0, -2.0, 1.0]):
        assert result.series(f"v:recv:{phase}") == pytest.approx([0.0, 0.0, voltage, voltage, voltage])
        assert result.series(f"i:BL:receiving:{phase}") == pytest.approx([0.0, 0.0, -voltage / 10, -voltage / 10, -voltage / 10])
