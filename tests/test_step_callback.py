"""闭环采样时序：初值、事件右侧、下一步作用与保存抽样。"""

import numpy as np
import pytest

from pycy_emt_lite import (Capacitor, Circuit, Fault, FaultApplyEvent, FaultClearEvent,
                         Resistor, SimulationConfig, Simulator, VoltageSource)


def test_callback_reads_right_side_once_and_controls_next_step():
    applied = [1.0]
    seen = []
    def callback(row):
        with pytest.raises(TypeError):
            row["v:n"] = 999
        seen.append(dict(row))
        applied[0] = 2.0
        return {"command_next": applied[0]}
    circuit = Circuit.from_components("feedback", (
        VoltageSource("V", "src", "0", lambda time: applied[0]),
        Resistor("R", "src", "n", 1.0), Capacitor("C", "n", "0", 1.0), Fault("F", "n", 1.0),
    ))
    result = Simulator(circuit, SimulationConfig(0.1, 0.3, method="backward_euler", record_every=10),
                       events=(FaultApplyEvent(0.15, "F"), FaultClearEvent(0.15, "F"), FaultApplyEvent(0.15, "F")),
                       on_step=callback).run()
    assert len(seen) == 5  # t=0, .1, .15, .2, .3；同刻三事件只采样一次。
    np.testing.assert_allclose([r["time"] for r in seen], [0, .1, .15, .2, .3])
    assert seen[0]["i:C"] == pytest.approx(1.0)
    assert seen[0]["v:src"] == 1.0
    assert seen[1]["v:src"] == 2.0
    assert seen[1]["v:n"] == pytest.approx(2 / 11)
    assert seen[2]["state:F"] == 1
    assert seen[2]["v:n"] == pytest.approx((2/11 + .05*2) / 1.05)
    assert seen[2]["i:C"] == pytest.approx(2 - 2*seen[2]["v:n"])
    np.testing.assert_allclose([r["time"] for r in result.rows], [0, .15, .3])
    assert all(row["command_next"] == 2 for row in result.rows)


def test_record_every_does_not_change_solution_or_controller_calls():
    snapshots = []
    for stride in (1, 3):
        count = [0]
        def callback(row):
            count[0] += 1
            return {"sample_count": float(count[0])}
        circuit = Circuit.from_components("decimated", (
            VoltageSource("V", "src", "0", 1.0), Resistor("R", "src", "n", 1.0),
            Capacitor("C", "n", "0", 1.0), Fault("F", "n", 1.0)))
        result = Simulator(circuit, SimulationConfig(.1, .5, record_every=stride),
                           events=(FaultApplyEvent(.2, "F"),), on_step=callback).run()
        assert count[0] == 6
        snapshots.append({row["time"]: row for row in result.rows})
    for time, row in snapshots[1].items():
        assert row == snapshots[0][time]


@pytest.mark.parametrize("value", [0, -1, True, 1.5, "2", np.nan])
def test_record_every_requires_positive_integer(value):
    with pytest.raises(ValueError, match="record_every"):
        SimulationConfig(.1, .5, record_every=value)


@pytest.mark.parametrize("extra", [{"time": 2.0}, {"x": np.nan}, {"x": True}, {"": 1.0}, None])
def test_callback_cannot_overwrite_fields_or_record_invalid_data(extra):
    circuit = Circuit.from_components("callback_error", (VoltageSource("V", "n", "0", 1.0), Resistor("R", "n", "0", 1.0)))
    with pytest.raises(ValueError, match="on_step"):
        Simulator(circuit, SimulationConfig(.1, 0), on_step=lambda row: extra).run()
