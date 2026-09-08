"""
文件名称：test_transformers.py
文件作用：验证单相和三相变压器教学模型。
"""

import math

import numpy as np
import pytest

from pycy_emt_lite import (
    Circuit,
    Resistor,
    SimulationConfig,
    Simulator,
    SinglePhaseTransformer,
    ThreePhaseSource,
    VoltageSource,
)
from pycy_emt_lite.analysis import three_phase_rms
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


def test_three_phase_yd_and_dy_transformers_are_solvable() -> None:
    yd_components = [
        ThreePhaseSource("VS1", "p1", phase_rms=100.0),
        ThreePhaseTransformer(
            "TYD",
            "p1",
            "s1",
            turns_ratio=2.0,
            primary_connection="Y",
            secondary_connection="D",
            leakage_resistance=0.01,
        ),
        Resistor("DAB", "s1:a", "s1:b", 60.0),
        Resistor("DBC", "s1:b", "s1:c", 60.0),
        Resistor("DCA", "s1:c", "s1:a", 60.0),
        Resistor("REF", "s1:a", "0", 1e9),
    ]
    yd_circuit = Circuit.from_components("three_phase_yd_transformer", yd_components)
    yd_config = SimulationConfig(time_step=1e-4, stop_time=0.02)
    yd_simulator = Simulator(yd_circuit, yd_config)

    yd_result = yd_simulator.run()

    dy_components = [
        ThreePhaseSource("VS2", "p2", phase_rms=100.0),
        ThreePhaseTransformer(
            "TDY",
            "p2",
            "s2",
            turns_ratio=2.0,
            primary_connection="D",
            secondary_connection="Y",
            leakage_resistance=0.01,
        ),
        Resistor("LA", "s2:a", "0", 50.0),
        Resistor("LB", "s2:b", "0", 50.0),
        Resistor("LC", "s2:c", "0", 50.0),
    ]
    dy_circuit = Circuit.from_components("three_phase_dy_transformer", dy_components)
    dy_config = SimulationConfig(time_step=1e-4, stop_time=0.02)
    dy_simulator = Simulator(dy_circuit, dy_config)

    dy_result = dy_simulator.run()

    assert np.isfinite(yd_result.series("i:TYD:primary:a")).all()
    assert np.isfinite(dy_result.series("i:TDY:secondary:a")).all()
