"""
文件名称：test_basic_components.py
文件作用：验证基础元件和 MNA 内核的基本数值行为。
"""

import math

import numpy as np
import pytest

import pycy_emt_lite
from pycy_emt_lite import Capacitor, Circuit, CurrentSource, Inductor, Resistor, SimulationConfig, Simulator, VoltageSource


@pytest.mark.parametrize("invalid", ["", "  ", None, 1])
def test_preparation_rejects_invalid_node_names(invalid) -> None:
    circuit = Circuit.from_components("invalid_node", [Resistor("R", invalid, "0", 1.0)])
    with pytest.raises(ValueError, match="节点名称"):
        circuit.prepare()


@pytest.mark.parametrize("invalid", ["", "  ", None, 1])
def test_preparation_rejects_invalid_component_names(invalid) -> None:
    circuit = Circuit.from_components("invalid_name", [Resistor(invalid, "n", "0", 1.0)])
    with pytest.raises(ValueError, match="元件名称"):
        circuit.prepare()


@pytest.mark.parametrize(
    "factory",
    [
        lambda value: Resistor("Rbad", "n", "0", value),
        lambda value: Capacitor("Cbad", "n", "0", value),
        lambda value: Inductor("Lbad", "n", "0", value),
    ],
)
@pytest.mark.parametrize("invalid", [math.nan, math.inf, -math.inf])
def test_basic_component_parameters_reject_nonfinite_values(factory, invalid) -> None:
    with pytest.raises(ValueError, match="有限"):
        factory(invalid)


@pytest.mark.parametrize(
    "factory",
    [
        lambda value: Capacitor("Cbad", "n", "0", 1.0, initial_voltage=value),
        lambda value: Inductor("Lbad", "n", "0", 1.0, initial_current=value),
    ],
)
@pytest.mark.parametrize("invalid", [math.nan, math.inf, -math.inf])
def test_dynamic_initial_conditions_reject_nonfinite_values(factory, invalid) -> None:
    with pytest.raises(ValueError, match="有限"):
        factory(invalid)


def test_zero_initial_conditions_are_valid() -> None:
    capacitor = Capacitor("C0", "n", "0", 1.0, initial_voltage=0.0)
    inductor = Inductor("L0", "n", "0", 1.0, initial_current=0.0)

    assert capacitor.previous_voltage == 0.0
    assert inductor.previous_current == 0.0


@pytest.mark.parametrize(
    ("name", "factory"),
    [
        ("Ibad", lambda value: CurrentSource("Ibad", "0", "n", value)),
        ("Vbad", lambda value: VoltageSource("Vbad", "n", "0", value)),
    ],
)
@pytest.mark.parametrize("invalid", [math.nan, math.inf, -math.inf])
def test_source_constants_reject_nonfinite_values(name, factory, invalid) -> None:
    with pytest.raises(ValueError, match="有限") as exc_info:
        factory(invalid)
    assert name in str(exc_info.value)


@pytest.mark.parametrize(
    ("name", "factory"),
    [
        ("Ibad", lambda function: CurrentSource("Ibad", "0", "n", function)),
        ("Vbad", lambda function: VoltageSource("Vbad", "n", "0", function)),
    ],
)
def test_callable_source_values_are_checked_at_runtime(name, factory) -> None:
    calls: list[float] = []

    def value_at(time: float) -> float:
        calls.append(time)
        return 1.0 if time < 1e-4 else math.nan

    source = factory(value_at)
    assert calls == []
    circuit = Circuit.from_components(name, [source, Resistor("R1", "n", "0", 1.0)])

    with pytest.raises(RuntimeError) as exc_info:
        Simulator(circuit, SimulationConfig(time_step=1e-4, stop_time=1e-4)).run()

    message = str(exc_info.value)
    assert name in message
    assert "0.0001" in message
    assert len(calls) == 2


def test_root_public_api_is_limited_to_the_teaching_workflow() -> None:
    expected = {
        "Breaker",
        "BreakerCloseEvent",
        "BreakerOpenEvent",
        "Capacitor",
        "CaseDefinition",
        "Circuit",
        "CurrentSource",
        "Fault",
        "FaultApplyEvent",
        "FaultClearEvent",
        "IdealSwitch",
        "Inductor",
        "OutputOptions",
        "PiLine",
        "PlotSpec",
        "Resistor",
        "SimulationConfig",
        "SimulationResult",
        "Simulator",
        "SinglePhaseTransformer",
        "ThreePhaseLine",
        "ThreePhaseLoad",
        "ThreePhaseSource",
        "VoltageSource",
        "run_case",
    }

    assert len(pycy_emt_lite.__all__) == len(expected)
    assert set(pycy_emt_lite.__all__) == expected


def test_resistor_voltage_source_solution() -> None:
    circuit = Circuit("resistor_solution")
    circuit.add(VoltageSource("V1", "n1", "0", 10.0))
    circuit.add(Resistor("R1", "n1", "0", 5.0))

    config = SimulationConfig(time_step=1e-4, stop_time=1e-4)
    simulator = Simulator(circuit, config)
    result = simulator.run()

    assert math.isclose(result.rows[-1]["v:n1"], 10.0, rel_tol=0.0, abs_tol=1e-12)
    assert math.isclose(result.rows[-1]["i:R1"], 2.0, rel_tol=0.0, abs_tol=1e-12)


def test_circuit_can_be_created_from_user_component_objects() -> None:
    components = [
        VoltageSource("V1", "n1", "0", 10.0),
        Resistor("R1", "n1", "0", 5.0),
    ]
    circuit = Circuit.from_components("from_components", components)

    config = SimulationConfig(time_step=1e-4, stop_time=1e-4)
    simulator = Simulator(circuit, config)
    result = simulator.run()

    assert math.isclose(result.rows[-1]["v:n1"], 10.0, rel_tol=0.0, abs_tol=1e-12)
    assert math.isclose(result.rows[-1]["i:R1"], 2.0, rel_tol=0.0, abs_tol=1e-12)


def test_current_source_direction_satisfies_kcl() -> None:
    circuit = Circuit("current_source_direction")
    circuit.add(CurrentSource("I1", "0", "n1", 2.0))
    circuit.add(Resistor("R1", "n1", "0", 5.0))

    config = SimulationConfig(time_step=1e-4, stop_time=1e-4)
    result = Simulator(circuit, config).run()

    assert math.isclose(result.rows[-1]["v:n1"], 10.0, rel_tol=0.0, abs_tol=1e-12)
    assert math.isclose(result.rows[-1]["i:R1"], 2.0, rel_tol=0.0, abs_tol=1e-12)


def test_rc_step_response_reaches_expected_value() -> None:
    circuit = Circuit("rc_step")
    circuit.add(VoltageSource("V1", "src", "0", 1.0))
    circuit.add(Resistor("R1", "src", "out", 1_000.0))
    circuit.add(Capacitor("C1", "out", "0", 1e-6))

    config = SimulationConfig(time_step=1e-5, stop_time=5e-3)
    simulator = Simulator(circuit, config)
    result = simulator.run()

    final_voltage = result.rows[-1]["v:out"]
    assert 0.99 < final_voltage < 1.01


def test_rl_step_response_reaches_expected_current() -> None:
    circuit = Circuit("rl_step")
    circuit.add(VoltageSource("V1", "src", "0", 1.0))
    circuit.add(Resistor("R1", "src", "mid", 10.0))
    circuit.add(Inductor("L1", "mid", "0", 10e-3))

    config = SimulationConfig(time_step=1e-5, stop_time=5e-3)
    simulator = Simulator(circuit, config)
    result = simulator.run()

    final_current = result.rows[-1]["i:L1"]
    assert 0.099 < final_current < 0.101


def test_rlc_response_is_bounded_and_settles_near_source_voltage() -> None:
    circuit = Circuit("rlc_step")
    circuit.add(VoltageSource("V1", "src", "0", 1.0))
    circuit.add(Resistor("R1", "src", "n1", 20.0))
    circuit.add(Inductor("L1", "n1", "out", 10e-3))
    circuit.add(Capacitor("C1", "out", "0", 10e-6))

    config = SimulationConfig(time_step=2e-6, stop_time=10e-3)
    simulator = Simulator(circuit, config)
    result = simulator.run()
    out = result.series("v:out")

    assert out.max() < 1.4
    assert out.min() > -0.1
    assert 0.95 < out[-1] < 1.05


@pytest.mark.parametrize("method", ["trapezoidal", "backward_euler"])
@pytest.mark.parametrize("stop", [0.0, 0.1, 0.15])
@pytest.mark.parametrize("initial", [0.0, 0.25])
def test_rc_initial_state_and_first_interval(method, stop, initial) -> None:
    cap = Capacitor("C", "out", "0", 1.0, initial_voltage=initial)
    circuit = Circuit.from_components("rc_initial", [
        VoltageSource("V", "src", "0", 1.0), Resistor("R", "src", "out", 1.0), cap,
    ])
    result = Simulator(circuit, SimulationConfig(0.1, stop, method=method)).run()
    assert result.rows[0]["v:C"] == pytest.approx(initial, abs=1e-14)
    assert result.rows[0]["i:C"] == pytest.approx(1.0 - initial)
    voltage = initial
    for before, row in zip(result.rows, result.rows[1:]):
        h = row["time"] - before["time"]
        decay = (1 - h / 2) / (1 + h / 2) if method == "trapezoidal" else 1 / (1 + h)
        voltage = 1 + (voltage - 1) * decay
        assert row["v:C"] == pytest.approx(voltage)
        assert row["i:C"] == pytest.approx(1 - voltage)
    assert cap.previous_current == pytest.approx(result.rows[-1]["i:C"])


@pytest.mark.parametrize("method", ["trapezoidal", "backward_euler"])
@pytest.mark.parametrize("initial", [0.0, 0.2])
def test_rl_initial_state_and_first_interval(method, initial) -> None:
    coil = Inductor("L", "out", "0", 1.0, initial_current=initial)
    circuit = Circuit.from_components("rl_initial", [
        VoltageSource("V", "src", "0", 1.0), Resistor("R", "src", "out", 1.0), coil,
    ])
    result = Simulator(circuit, SimulationConfig(0.1, 0.1, method=method)).run()
    assert result.rows[0]["i:L"] == pytest.approx(initial, abs=1e-14)
    assert result.rows[0]["v:L"] == pytest.approx(1 - initial)
    decay = 0.95 / 1.05 if method == "trapezoidal" else 1 / 1.1
    assert result.rows[1]["i:L"] == pytest.approx(1 + (initial - 1) * decay)
    assert coil.previous_voltage == pytest.approx(result.rows[1]["v:L"])


def test_parallel_capacitors_share_initial_current_by_capacitance() -> None:
    result = Simulator(Circuit.from_components("parallel_c", [
        CurrentSource("I", "0", "n", 3.0),
        Capacitor("C1", "n", "0", 1.0, initial_voltage=0.25),
        Capacitor("C2", "n", "0", 2.0, initial_voltage=0.25),
    ]), SimulationConfig(0.1, 0.1)).run()
    assert result.series("v:n") == pytest.approx([0.25, 0.35])
    assert result.series("i:C1") == pytest.approx([1.0, 1.0])
    assert result.series("i:C2") == pytest.approx([2.0, 2.0])


def test_floating_inductor_star_satisfies_kcl_and_its_derivative() -> None:
    components = []
    for phase, voltage in zip("abc", [400.0, 0.0, 0.0]):
        components.extend([VoltageSource(f"V{phase}", phase, "0", voltage),
                           Inductor(f"L{phase}", phase, "star", 1.0)])
    result = Simulator(Circuit.from_components("star", components), SimulationConfig(0.1, 0.1)).run()
    assert result.series("v:star") == pytest.approx([400 / 3, 400 / 3])
    for phase, voltage in zip("abc", [400.0, 0.0, 0.0]):
        assert result.rows[0][f"i:L{phase}"] == pytest.approx(0.0, abs=1e-12)
        assert result.rows[0][f"v:L{phase}"] == pytest.approx(voltage - 400 / 3)
    assert sum(result.rows[1][f"i:L{phase}"] for phase in "abc") == pytest.approx(0.0, abs=1e-12)


def test_inconsistent_capacitor_voltage_is_rejected() -> None:
    circuit = Circuit.from_components("conflict", [
        VoltageSource("V", "n", "0", 1.0), Capacitor("C", "n", "0", 1.0),
    ])
    with pytest.raises(RuntimeError, match="初值.*冲突"):
        Simulator(circuit, SimulationConfig(0.1, 0.0)).run()


def test_consistent_voltage_source_parallel_capacitor_has_zero_dc_current() -> None:
    result = Simulator(Circuit.from_components("voltage_c", [
        VoltageSource("V", "n", "0", 1.0), Capacitor("C", "n", "0", 2.0, initial_voltage=1.0),
    ]), SimulationConfig(0.1, 0.1)).run()
    assert result.series("v:C") == pytest.approx([1.0, 1.0])
    assert result.series("i:C") == pytest.approx([0.0, 0.0], abs=1e-12)


def test_lossless_lc_preserves_initial_energy() -> None:
    result = Simulator(Circuit.from_components("lc", [
        Capacitor("C", "n", "0", 1.0, initial_voltage=1.0), Inductor("L", "n", "0", 1.0),
    ]), SimulationConfig(0.05, 5.0)).run()
    energy = 0.5 * (result.series("v:C") ** 2 + result.series("i:L") ** 2)
    np.testing.assert_allclose(energy, 0.5, atol=1e-12, rtol=0)
    assert result.rows[0]["i:C"] == pytest.approx(0.0, abs=1e-12)
    assert result.rows[0]["v:L"] == pytest.approx(1.0)


@pytest.mark.parametrize("source_kind", ["voltage", "current"])
def test_constrained_callable_source_requires_and_uses_analytic_derivative(source_kind) -> None:
    def make_circuit(derivative=None):
        if source_kind == "voltage":
            parts = [VoltageSource("S", "n", "0", lambda t: 1 + 3 * t, derivative=derivative),
                     Capacitor("C", "n", "0", 2.0, initial_voltage=1.0)]
        else:
            parts = [CurrentSource("S", "0", "n", lambda t: 1 + 3 * t, derivative=derivative),
                     Inductor("L", "n", "0", 2.0, initial_current=1.0)]
        return Circuit.from_components("constrained_callable", parts)

    with pytest.raises(RuntimeError, match="S.*derivative"):
        Simulator(make_circuit(), SimulationConfig(0.1, 0.0)).run()
    for invalid in [math.nan, math.inf]:
        with pytest.raises(RuntimeError, match="derivative.*有限"):
            Simulator(make_circuit(lambda t: invalid), SimulationConfig(0.1, 0.0)).run()
    result = Simulator(make_circuit(lambda t: 3.0), SimulationConfig(0.1, 0.1)).run()
    algebraic = "i:C" if source_kind == "voltage" else "v:L"
    assert result.series(algebraic) == pytest.approx([6.0, 6.0])


def test_unconstrained_callable_does_not_require_derivative() -> None:
    result = Simulator(Circuit.from_components("ordinary_callable", [
        VoltageSource("V", "src", "0", lambda t: 1 + t), Resistor("R", "src", "n", 1.0),
        Capacitor("C", "n", "0", 1.0),
    ]), SimulationConfig(0.1, 0.0)).run()
    assert result.rows[0]["i:C"] == pytest.approx(1.0)


@pytest.mark.parametrize("case", ["parallel_c", "inductor_cutset", "redundant_sources"])
def test_initial_conflicts_and_nonunique_branch_currents_are_rejected(case) -> None:
    parts = {
        "parallel_c": [Capacitor("C1", "n", "0", 1.0), Capacitor("C2", "n", "0", 2.0, initial_voltage=1.0)],
        "inductor_cutset": [CurrentSource("I", "0", "n", 1.0), Inductor("L", "n", "0", 1.0)],
        "redundant_sources": [VoltageSource("V1", "n", "0", 1.0), VoltageSource("V2", "n", "0", 1.0)],
    }[case]
    with pytest.raises(RuntimeError, match="冲突|欠定"):
        Simulator(Circuit.from_components(case, parts), SimulationConfig(0.1, 0.0)).run()


@pytest.mark.parametrize("kind", ["RC", "RL"])
@pytest.mark.parametrize("method", ["trapezoidal", "backward_euler"])
def test_rc_rl_analytic_error_converges_on_common_physical_grid(kind, method) -> None:
    errors = []
    for h in [0.1, 0.05]:
        storage = Capacitor("C", "n", "0", 1.0, initial_voltage=0.2) if kind == "RC" else Inductor("L", "n", "0", 1.0, initial_current=0.2)
        result = Simulator(Circuit.from_components(kind, [
            VoltageSource("V", "src", "0", 1.0), Resistor("R", "src", "n", 1.0), storage,
        ]), SimulationConfig(h, 1.0, method=method)).run()
        stride = round(0.1 / h)
        times = result.series("time")[::stride]
        values = result.series("v:C" if kind == "RC" else "i:L")[::stride]
        errors.append(np.max(np.abs(values - (1 - 0.8 * np.exp(-times)))))
    expected_order_ratio = 4.0 if method == "trapezoidal" else 2.0
    assert errors[0] / errors[1] == pytest.approx(expected_order_ratio, rel=0.06)


def test_rlc_whole_curve_matches_analytic_damped_response() -> None:
    errors = []
    omega = math.sqrt(3) / 2
    for h in [0.05, 0.025]:
        result = Simulator(Circuit.from_components("rlc_analytic", [
            VoltageSource("V", "src", "0", 1.0), Resistor("R", "src", "mid", 1.0),
            Inductor("L", "mid", "out", 1.0), Capacitor("C", "out", "0", 1.0),
        ]), SimulationConfig(h, 5.0)).run()
        stride = round(0.05 / h)
        t = result.series("time")[::stride]
        expected_v = 1 - np.exp(-t / 2) * (np.cos(omega * t) + np.sin(omega * t) / (2 * omega))
        expected_i = np.exp(-t / 2) * np.sin(omega * t) / omega
        errors.append(max(np.max(np.abs(result.series("v:C")[::stride] - expected_v)),
                          np.max(np.abs(result.series("i:L")[::stride] - expected_i))))
        np.testing.assert_allclose(result.series("i:C"), result.series("i:L"), atol=1e-12)
    assert errors[1] < 5e-5
    assert 3.9 < errors[0] / errors[1] < 4.1
