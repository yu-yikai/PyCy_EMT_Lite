"""
文件名称：test_results_io.py
文件作用：验证仿真结果 CSV、JSON、NPZ 保存和读入。
"""

import json
import math

import numpy as np
import pytest

from pycy_emt_lite import (
    Circuit,
    Resistor,
    SimulationConfig,
    SimulationResult,
    Simulator,
    VoltageSource,
)


@pytest.mark.parametrize("format", ["csv", "json", "npz"])
def test_sparse_and_nonfinite_signal_values_roundtrip_consistently(tmp_path, format) -> None:
    result = SimulationResult("missing", "manual", 1.0, 1.0,
        [{"time": 0.0, "x": 2.0, "r:load:phase": math.inf}, {"time": 1.0, "r:load:phase": math.inf}])
    path = tmp_path / f"missing.{format}"
    getattr(result, f"to_{format}")(path)
    loaded = getattr(SimulationResult, f"from_{format}")(path)
    np.testing.assert_equal(loaded.series("x"), [2.0, np.nan])
    np.testing.assert_equal(loaded.series("r:load:phase"), [np.inf, np.inf])
    if format == "json":
        json.loads(path.read_text(encoding="utf-8"), parse_constant=lambda token: pytest.fail(f"非法 JSON 常量 {token}"))


@pytest.mark.parametrize("column", ["__meta__", "__columns__", "file", "allow_pickle"])
def test_npz_reserved_columns_rejected_before_write(tmp_path, column) -> None:
    result = SimulationResult("reserved", "manual", 1.0, 0.0, [{"time": 0.0, column: 1.0}])
    path = tmp_path / "reserved.npz"
    with pytest.raises(ValueError, match=column):
        result.to_npz(path)
    assert not path.exists()


@pytest.mark.parametrize("array", [np.ones(1), np.ones(3), np.ones((2, 1)), np.array(["1", "2"])])
def test_npz_rejects_malformed_columns_without_truncation(tmp_path, array) -> None:
    path = tmp_path / "bad.npz"
    np.savez(path, time=np.array([0.0, 1.0]), x=array, __columns__=np.array(["time", "x"]),
             __meta__=np.array(json.dumps({"circuit_name": "bad", "method": "manual", "time_step": 1.0, "stop_time": 1.0})))
    with pytest.raises(ValueError, match="bad.npz.*x"):
        SimulationResult.from_npz(path)


def test_csv_bad_value_reports_file_line_and_field(tmp_path) -> None:
    path = tmp_path / "bad.csv"
    path.write_text("time,x\n0,1\n1,broken\n", encoding="utf-8")
    with pytest.raises(ValueError, match="bad.csv.*3.*x"):
        SimulationResult.from_csv(path)


@pytest.mark.parametrize("fault", ["duplicate_columns", "repeated_time", "nan_time", "boolean_meta"])
def test_json_rejects_corrupt_structure_and_metadata(tmp_path, fault) -> None:
    payload = {"circuit_name": "bad", "method": "manual", "time_step": 1.0, "stop_time": 1.0,
               "columns": ["time", "x"], "rows": [{"time": 0.0, "x": 1.0}, {"time": 1.0, "x": 2.0}]}
    if fault == "duplicate_columns":
        payload["columns"] = ["time", "x", "x"]
    elif fault == "boolean_meta":
        payload["time_step"] = True
    else:
        payload["rows"][1]["time"] = 0.0 if fault == "repeated_time" else None
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="bad.json"):
        SimulationResult.from_json(path)


@pytest.mark.parametrize("format", ["csv", "json", "npz"])
def test_numpy_scalars_in_result_metadata_are_valid(tmp_path, format) -> None:
    result = _result()
    result.time_step = np.float32(1e-4)
    result.stop_time = np.float64(2e-4)
    result.event_log = [{"time": np.float32(1e-4), "type": "custom", "count": np.int64(1)}]
    path = tmp_path / f"numeric.{format}"
    getattr(result, f"to_{format}")(path)
    loaded = getattr(SimulationResult, f"from_{format}")(path)
    np.testing.assert_equal(loaded.series("v:n1"), result.series("v:n1"))


def test_npz_suffix_rule_is_explicit(tmp_path) -> None:
    path = tmp_path / "result"
    _result().to_npz(path)
    assert not path.exists()
    assert path.with_suffix(".npz").is_file()


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
