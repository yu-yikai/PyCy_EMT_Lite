"""
文件名称：test_transformers.py
文件作用：验证单相和三相变压器教学模型。
"""

import math
from dataclasses import replace
from pathlib import Path
import runpy

import numpy as np
import pytest

from pycy_emt_lite import (
    Circuit,
    Fault,
    FaultApplyEvent,
    Inductor,
    Resistor,
    SimulationConfig,
    Simulator,
    SinglePhaseTransformer,
    ThreePhaseSource,
    VoltageSource,
)
from pycy_emt_lite.analysis import mean_value, rms, three_phase_rms
from pycy_emt_lite.components.transformers import ThreePhaseTransformer


@pytest.mark.parametrize(
    ("parameter", "value"),
    (
        ("turns_ratio", math.nan),
        ("leakage_resistance", math.nan),
        ("leakage_inductance", math.nan),
        ("magnetizing_inductance", math.nan),
        ("core_loss_resistance", math.nan),
        ("saturation_knee_flux", math.nan),
        ("saturated_magnetizing_inductance", math.nan),
    ),
)
def test_transformer_rejects_nonfinite_parameters(parameter: str, value: float) -> None:
    values: dict[str, float | None] = {
        "turns_ratio": 1.0,
        "leakage_resistance": 0.0,
        "leakage_inductance": 0.0,
        "magnetizing_inductance": 1.0,
        "core_loss_resistance": 1.0,
        "saturation_knee_flux": 1.0,
        "saturated_magnetizing_inductance": 0.5,
    }
    values[parameter] = value

    with pytest.raises(ValueError, match="有限"):
        SinglePhaseTransformer("T1", "primary", "0", "secondary", "0", **values)


def test_single_phase_transformer_voltage_ratio() -> None:
    components = [
        VoltageSource("V1", "primary", "0", 100.0),
        SinglePhaseTransformer("T1", "primary", "0", "secondary", "0", turns_ratio=2.0),
        Resistor("LOAD", "secondary", "0", 50.0),
    ]
    circuit = Circuit.from_components("single_phase_transformer", components)
    config = SimulationConfig(time_step=1e-4, stop_time=1e-4)
    simulator = Simulator(circuit, config)

    result = simulator.run()

    assert math.isclose(result.rows[-1]["v:secondary"], 50.0, rel_tol=0.0, abs_tol=1e-9)
    assert math.isclose(result.rows[-1]["i:LOAD"], 1.0, rel_tol=0.0, abs_tol=1e-9)


def test_single_phase_transformer_saturation_state_is_recorded() -> None:
    components = [
        VoltageSource("V1", "primary", "0", 100.0),
        SinglePhaseTransformer(
            "T1",
            "primary",
            "0",
            "secondary",
            "0",
            turns_ratio=2.0,
            magnetizing_inductance=10.0,
            saturation_knee_flux=1e-4,
            saturated_magnetizing_inductance=1.0,
        ),
        Resistor("LOAD", "secondary", "0", 100.0),
    ]
    circuit = Circuit.from_components("single_phase_transformer_saturation", components)
    config = SimulationConfig(time_step=1e-4, stop_time=2e-4)
    simulator = Simulator(circuit, config)

    result = simulator.run()

    assert "flux:T1:magnetizing" in result.columns
    assert abs(result.rows[-1]["flux:T1:magnetizing"]) > 0.0
    assert np.isfinite(result.series("i:T1:magnetizing")).all()


def test_three_phase_yy_transformer_voltage_ratio() -> None:
    components = [
        ThreePhaseSource("VS", "primary", phase_rms=100.0),
        ThreePhaseTransformer(
            "T3",
            "primary",
            "secondary",
            turns_ratio=2.0,
            primary_connection="Y",
            secondary_connection="Y",
        ),
        Resistor("LA", "secondary:a", "0", 50.0),
        Resistor("LB", "secondary:b", "0", 50.0),
        Resistor("LC", "secondary:c", "0", 50.0),
    ]
    circuit = Circuit.from_components("three_phase_yy_transformer", components)
    config = SimulationConfig(time_step=1e-4, stop_time=0.1)
    simulator = Simulator(circuit, config)

    result = simulator.run()
    rms_values = three_phase_rms(
        result,
        ("v:secondary:a", "v:secondary:b", "v:secondary:c"),
        start_time=0.06,
    )

    assert all(49.5 < value < 50.5 for value in rms_values.values())


@pytest.mark.parametrize("primary", ["Y", "D"])
def test_ideal_transformer_with_secondary_y_has_unique_loaded_solution(primary) -> None:
    transformer = ThreePhaseTransformer("T", "in", "out", 2.0, primary, "Y")
    loads = np.array([10.0, 20.0, 30.0])
    result = Simulator(Circuit.from_components("ideal_secondary_y", [
        ThreePhaseSource("V", "in", 100.0), transformer,
        *[Resistor(f"R{p}", f"out:{p}", "0", r) for p, r in zip("abc", loads)],
    ]), SimulationConfig(1e-4, 0.02)).run()
    vin = np.array([result.series(f"v:in:{p}") for p in "abc"])
    vout = np.array([result.series(f"v:out:{p}") for p in "abc"])
    winding_voltage = vin if primary == "Y" else vin - np.roll(vin, -1, axis=0)
    np.testing.assert_allclose(vout, winding_voltage / 2, atol=1e-12)
    input_current = -np.array([result.series(f"i:V:{p}") for p in "abc"])
    np.testing.assert_allclose(np.sum(vin * input_current, axis=0),
                               np.sum(vout**2 / loads[:, None], axis=0), atol=1e-10)


@pytest.mark.parametrize("primary", ["Y", "D"])
def test_secondary_delta_requires_leakage_to_determine_circulating_current(primary) -> None:
    with pytest.raises(ValueError, match="二次.*Δ.*leakage_resistance.*leakage_inductance"):
        ThreePhaseTransformer("T", "in", "out", 2.0, primary, "D")


@pytest.mark.parametrize("three_phase", [False, True])
@pytest.mark.parametrize("method", ["trapezoidal", "backward_euler"])
@pytest.mark.parametrize("event_time", [None, 0.0075, 0.02])
def test_linear_magnetizing_flux_equals_inductance_times_current(three_phase, method, event_time) -> None:
    if three_phase:
        transformer = ThreePhaseTransformer("T", "in", "out", 2.0, magnetizing_inductance=3.0)
        source = ThreePhaseSource("V", "in", 10.0, frequency=5.0, initial_angle=0.3)
        ports = [(f"out:{p}", f":{p}") for p in "abc"]
    else:
        transformer = SinglePhaseTransformer("T", "in", "0", "out", "0", 2.0, magnetizing_inductance=3.0)
        source = VoltageSource("V", "in", "0", lambda t: 10 * math.sin(2 * math.pi * 5 * t + 0.3))
        ports = [("out", "")]
    result = Simulator(Circuit.from_components("linear_flux", [source, transformer,
        *[Resistor(f"R{suffix}", node, "0", 10.0) for node, suffix in ports],
        Fault("F", ports[0][0], 10.0),
    ]), SimulationConfig(0.001, 0.02, method=method),
        events=[] if event_time is None else [FaultApplyEvent(event_time, "F")]).run()
    for _, suffix in ports:
        np.testing.assert_allclose(result.series(f"flux:T:magnetizing{suffix}"),
                                   3.0 * result.series(f"i:T:magnetizing{suffix}"), atol=1e-12)


@pytest.mark.parametrize("primary,secondary", [("Y", "Y"), ("Y", "D"), ("D", "Y"), ("D", "D")])
@pytest.mark.parametrize("method,order_ratio", [("trapezoidal", 4.0), ("backward_euler", 2.0)])
def test_three_phase_connections_match_analytical_transients_and_energy(primary, secondary, method, order_ratio) -> None:
    ratio, resistance, inductance, magnetizing, core, load = 2.0, 0.2, 0.02, 2.0, 1000.0, 10.0
    omega = 2 * math.pi * 50
    source_phasor = 100 * np.exp(1j * np.array([0.0, -2 * math.pi / 3, 2 * math.pi / 3]))
    primary_phasor = source_phasor if primary == "Y" else source_phasor - np.roll(source_phasor, -1)
    # 平衡星形负荷折算到 Δ 绕组为 3 Rload；每相用独立 RL 解析启动解。
    winding_load = load if secondary == "Y" else 3 * load
    total_resistance = resistance + ratio**2 * winding_load
    leakage_phasor = primary_phasor / complex(total_resistance, omega * inductance)
    errors = []
    for step in [2e-5, 1e-5]:
        transformer = ThreePhaseTransformer("T", "in", "out", ratio, primary, secondary,
            leakage_resistance=resistance, leakage_inductance=inductance,
            magnetizing_inductance=magnetizing, core_loss_resistance=core)
        result = Simulator(Circuit.from_components("three_phase_connections", [
            ThreePhaseSource("V", "in", 100.0), transformer,
            *[Resistor(f"R{p}", f"out:{p}", "0", load) for p in "abc"],
        ]), SimulationConfig(step, 0.02, method=method)).run()
        time = result.series("time")
        vin = np.array([result.series(f"v:in:{p}") for p in "abc"])
        vout = np.array([result.series(f"v:out:{p}") for p in "abc"])
        ip = np.array([result.series(f"i:T:primary:{p}") for p in "abc"])
        im = np.array([result.series(f"i:T:magnetizing:{p}") for p in "abc"])
        secondary_current = np.array([result.series(f"i:T:secondary:{p}") for p in "abc"])
        input_current = -np.array([result.series(f"i:V:{p}") for p in "abc"])
        winding_voltage = vin if primary == "Y" else vin - np.roll(vin, -1, axis=0)
        winding_input = ip + im + winding_voltage / core
        expected_input = winding_input if primary == "Y" else winding_input - np.roll(winding_input, 1, axis=0)
        expected_output = -secondary_current if secondary == "Y" else -secondary_current + np.roll(secondary_current, 1, axis=0)
        np.testing.assert_allclose(input_current, expected_input, atol=1e-11)
        np.testing.assert_allclose(vout / load, expected_output, atol=1e-11)
        np.testing.assert_allclose(secondary_current, -ratio * ip, atol=1e-11)
        np.testing.assert_allclose(np.sum(input_current, axis=0), 0.0, atol=1e-11)
        np.testing.assert_allclose([ip[:, 0], im[:, 0]], 0.0, atol=1e-12)

        stride = round(2e-5 / step)
        common_time = time[::stride]
        rotating = np.exp(1j * omega * common_time)
        exact_ip = math.sqrt(2) * ((leakage_phasor[:, None] * rotating).imag
            - leakage_phasor.imag[:, None] * np.exp(-total_resistance * common_time / inductance))
        exact_im = math.sqrt(2) * (primary_phasor.real[:, None]
            - (primary_phasor[:, None] * rotating).real) / (omega * magnetizing)
        exact_vout = ratio * winding_load * exact_ip
        if secondary == "D":
            exact_vout = (exact_vout - np.roll(exact_vout, 1, axis=0)) / 3
        errors.append(np.array([np.max(np.abs(actual[:, ::stride] - exact))
            for actual, exact in [(ip, exact_ip), (im, exact_im), (vout, exact_vout)]]))
        flux = np.array([result.series(f"flux:T:magnetizing:{p}") for p in "abc"])
        np.testing.assert_allclose(flux, magnetizing * im, atol=1e-12)

        energy = 0.5 * np.sum(inductance * ip**2 + magnetizing * im**2, axis=0)
        if method == "trapezoidal":
            vi, ii, vo, iw, vw = [(x[:, :-1] + x[:, 1:]) / 2
                for x in [vin, input_current, vout, ip, winding_voltage]]
            numerical_loss = 0.0
        else:
            vi, ii, vo, iw, vw = [x[:, 1:] for x in [vin, input_current, vout, ip, winding_voltage]]
            numerical_loss = 0.5 * np.sum(inductance * np.diff(ip)**2 + magnetizing * np.diff(im)**2, axis=0)
        power = np.sum(vi * ii - vo**2 / load - resistance * iw**2 - vw**2 / core, axis=0)
        work = np.cumsum(np.diff(time) * power - numerical_loss)
        np.testing.assert_allclose(work, energy[1:] - energy[0], atol=1e-10, rtol=0)

    limits = [2.5e-4, 7e-7, 0.008] if method == "trapezoidal" else [0.025, 0.0013, 0.75]
    assert np.all(errors[1] < limits), errors  # A、A、V，整个启动区间
    np.testing.assert_allclose(errors[0] / errors[1], order_ratio, rtol=0.08)


@pytest.mark.parametrize("method", ["trapezoidal", "backward_euler"])
@pytest.mark.parametrize("event_time", [None, 0.05])
def test_transformer_initial_state_and_first_step_match_separate_equivalent(method, event_time) -> None:
    transformer = SinglePhaseTransformer("T", "src", "0", "out", "0", 2.0,
        leakage_resistance=1.0, leakage_inductance=2.0, magnetizing_inductance=4.0, core_loss_resistance=100.0)
    transformer.state.leakage_previous_current = 0.2
    transformer.state.magnetizing_previous_current = 0.3
    circuit = Circuit.from_components("transformer", [
        VoltageSource("V", "src", "0", 10.0), transformer, Resistor("LOAD", "out", "0", 3.0), Fault("F", "out", 3.0),
    ])
    equivalent = Circuit.from_components("equivalent", [
        VoltageSource("V", "src", "0", 10.0), Resistor("R", "src", "mid", 1.0),
        Inductor("L", "mid", "primary", 2.0, initial_current=0.2),
        SinglePhaseTransformer("T", "primary", "0", "out", "0", 2.0),
        Inductor("LM", "src", "0", 4.0, initial_current=0.3),
        Resistor("CORE", "src", "0", 100.0), Resistor("LOAD", "out", "0", 3.0), Fault("F", "out", 3.0),
    ])
    config = SimulationConfig(0.1, 0.1, method=method)
    events = [] if event_time is None else [FaultApplyEvent(event_time, "F")]
    result = Simulator(circuit, config, events=events).run()
    reference = Simulator(equivalent, config, events=events).run()
    for actual, expected in [("v:out", "v:out"), ("i:T:primary", "i:L"),
                             ("i:T:magnetizing", "i:LM"), ("i:V", "i:V")]:
        np.testing.assert_allclose(result.series(actual), reference.series(expected), atol=1e-12)
    assert result.rows[0]["flux:T:magnetizing"] == 0.0
    assert result.rows[0]["v:out"] == pytest.approx(1.2)


def test_three_phase_transformer_freezes_each_winding_current_at_zero() -> None:
    transformer = ThreePhaseTransformer("T", "src", "out", 2.0, leakage_inductance=1.0, magnetizing_inductance=2.0)
    result = Simulator(Circuit.from_components("three_phase_initial", [
        ThreePhaseSource("V", "src", 100.0), transformer,
        *[Resistor(f"R{phase}", f"out:{phase}", "0", 10.0) for phase in "abc"],
    ]), SimulationConfig(0.1, 0.0)).run()
    row = result.rows[0]
    for phase in "abc":
        assert row[f"i:T:primary:{phase}"] == pytest.approx(0.0, abs=1e-12)
        assert row[f"i:T:magnetizing:{phase}"] == pytest.approx(0.0, abs=1e-12)
        assert transformer.states[phase].leakage_previous_voltage == pytest.approx(row[f"v:src:{phase}"])
        assert transformer.states[phase].magnetizing_previous_voltage == pytest.approx(row[f"v:src:{phase}"])


@pytest.mark.parametrize("core_loss_resistance", [None, 1000.0])
def test_loaded_transformer_ac_matches_phasors_dc_magnetizing_current_and_energy(core_loss_resistance) -> None:
    example = runpy.run_path(str(Path(__file__).parents[1] / "examples/09_single_phase_transformer.py"))
    case = example["define_case"]()
    source, transformer, load = case.components
    transformer = replace(transformer, core_loss_resistance=core_loss_resistance)
    result = Simulator(Circuit.from_components(case.name, [source, transformer, load]), case.config).run()
    omega = 2 * math.pi * example["FREQUENCY"]
    source_rms = example["SOURCE_RMS"]
    ratio = transformer.turns_ratio
    primary_phasor = source_rms / complex(
        transformer.leakage_resistance + ratio**2 * load.resistance, omega * transformer.leakage_inductance,
    )
    secondary_phasor = ratio * load.resistance * primary_phasor
    magnetizing_phasor = source_rms / (1j * omega * transformer.magnetizing_inductance)
    magnetizing_dc = math.sqrt(2) * abs(magnetizing_phasor)  # 零初值理想电感保留 DC 分量
    core_conductance = 0.0 if core_loss_resistance is None else 1 / core_loss_resistance
    input_phasor = primary_phasor + magnetizing_phasor + core_conductance * source_rms
    time = result.series("time")
    window = time >= 0.02
    rotating = np.exp(1j * omega * time[window])
    for column, phasor in {"v:sec": secondary_phasor, "i:T1:primary": primary_phasor,
                           "i:T1:secondary": -ratio * primary_phasor}.items():
        np.testing.assert_allclose(result.series(column)[window], math.sqrt(2) * (phasor * rotating).imag,
                                   atol=1e-5 * abs(phasor), rtol=0)
        assert rms(result, column, start_time=0.02) == pytest.approx(abs(phasor), rel=1e-4)
    expected_magnetizing = magnetizing_dc * (1 - np.cos(omega * time))
    np.testing.assert_allclose(result.series("i:T1:magnetizing"), expected_magnetizing, atol=2e-4, rtol=0)
    assert mean_value(result, "i:T1:magnetizing", start_time=0.02) == pytest.approx(magnetizing_dc, rel=1e-4)
    assert rms(result, "i:V1", start_time=0.02) == pytest.approx(
        math.sqrt(abs(input_phasor)**2 + magnetizing_dc**2), rel=2e-4,
    )

    primary = result.series("i:T1:primary")
    secondary = result.series("i:T1:secondary")
    magnetizing = result.series("i:T1:magnetizing")
    voltage = result.series("v:pri")
    input_current = -result.series("i:V1")
    np.testing.assert_allclose(ratio * primary + secondary, 0.0, atol=1e-12)
    np.testing.assert_allclose(input_current, primary + magnetizing + core_conductance * voltage, atol=1e-12)

    def midpoint(values):
        return (values[:-1] + values[1:]) / 2

    energy = 0.5 * (transformer.leakage_inductance * primary**2 + transformer.magnetizing_inductance * magnetizing**2)
    net_work = np.cumsum(np.diff(time) * (
        midpoint(voltage) * midpoint(input_current) - midpoint(result.series("v:sec")) * midpoint(result.series("i:LOAD"))
        - transformer.leakage_resistance * midpoint(primary)**2 - core_conductance * midpoint(voltage)**2
    ))
    np.testing.assert_allclose(net_work, energy[1:] - energy[0], atol=1e-11, rtol=0)


@pytest.mark.parametrize("method,order_ratio", [("trapezoidal", 4.0), ("backward_euler", 2.0)])
def test_loaded_transformer_ac_error_converges_on_common_physical_grid(method, order_ratio) -> None:
    example = runpy.run_path(str(Path(__file__).parents[1] / "examples/09_single_phase_transformer.py"))
    errors = []
    for step in [2e-4, 1e-4]:
        case = example["define_case"]()
        transformer, load = case.components[1:]
        result = Simulator(Circuit.from_components(case.name, case.components), replace(case.config, time_step=step, method=method)).run()
        stride = round(2e-4 / step)
        time = result.series("time")[::stride]
        window = time >= 0.02
        time = time[window]
        omega = 2 * math.pi * example["FREQUENCY"]
        primary = example["SOURCE_RMS"] / complex(
            transformer.leakage_resistance + transformer.turns_ratio**2 * load.resistance,
            omega * transformer.leakage_inductance,
        )
        expected = {
            "v:sec": math.sqrt(2) * (transformer.turns_ratio * load.resistance * primary * np.exp(1j * omega * time)).imag,
            "i:T1:magnetizing": math.sqrt(2) * example["SOURCE_RMS"] / (omega * transformer.magnetizing_inductance) * (1 - np.cos(omega * time)),
        }
        errors.append([np.max(np.abs(result.series(column)[::stride][window] - reference)) for column, reference in expected.items()])
    np.testing.assert_allclose(np.array(errors[0]) / errors[1], order_ratio, rtol=0.02)
