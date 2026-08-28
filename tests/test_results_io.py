"""
文件名称：test_results_io.py
文件作用：验证仿真结果 CSV、JSON、NPZ 保存和读入。
"""

import math

from pycy_emt_lite import Circuit, Resistor, SimulationConfig, SimulationResult, Simulator, VoltageSource


def _result() -> SimulationResult:
    components = [
        VoltageSource("V1", "n1", "0", 2.0),
        Resistor("R1", "n1", "0", 4.0),
    ]
    circuit = Circuit.from_components("io_test", components)
    config = SimulationConfig(time_step=1e-4, stop_time=2e-4)
    simulator = Simulator(circuit, config)
    result = simulator.run()
    return result


def test_repr_shows_concise_summary() -> None:
    """打印结果对象时应显示简洁摘要，而不是庞大的行数据。"""

    summary = repr(_result())

    assert "io_test" in summary
    assert "samples=3" in summary
    assert "columns=4" in summary
    assert "events=0" in summary


def test_json_roundtrip(tmp_path) -> None:
    result = _result()
    path = tmp_path / "result.json"

    result.to_json(path)
    loaded = SimulationResult.from_json(path)

    assert loaded.circuit_name == "io_test"
    assert loaded.columns == result.columns
    assert math.isclose(loaded.rows[-1]["v:n1"], 2.0)


def test_csv_roundtrip(tmp_path) -> None:
    result = _result()
    path = tmp_path / "result.csv"

    result.to_csv(path)
    loaded = SimulationResult.from_csv(path)

    assert loaded.columns == result.columns
    assert math.isclose(loaded.rows[-1]["i:R1"], 0.5)


def test_npz_roundtrip(tmp_path) -> None:
    result = _result()
    path = tmp_path / "result.npz"

    result.to_npz(path)
    loaded = SimulationResult.from_npz(path)

    assert loaded.columns == result.columns
    assert math.isclose(loaded.rows[-1]["v:n1"], 2.0)


def test_json_and_npz_keep_event_log(tmp_path) -> None:
    result = _result()
    result.event_log.append(
        {
            "time": 1e-4,
            "scheduled_time": 1e-4,
            "type": "fault_apply",
            "target": "F1",
            "before": 0.0,
            "after": 1.0,
            "name": "",
        }
    )

    json_path = tmp_path / "with_event.json"
    npz_path = tmp_path / "with_event.npz"
    result.to_json(json_path)
    result.to_npz(npz_path)

    assert SimulationResult.from_json(json_path).event_log == result.event_log
    assert SimulationResult.from_npz(npz_path).event_log == result.event_log
