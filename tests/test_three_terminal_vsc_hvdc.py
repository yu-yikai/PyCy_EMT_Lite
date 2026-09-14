"""开关级三端示例：分阶段控制验证、端口守恒和完整 FAST 故障回归。"""

from pathlib import Path
import math
import runpy

import numpy as np
import pytest

from pycy_emt_lite import Circuit, IdealSwitch, SimulationConfig, Simulator, VoltageSource
from pycy_emt_lite.components.transformers import ThreePhaseTransformer
from pycy_emt_lite.controls import dq_to_abc


@pytest.fixture(scope="module")
def example():
    return runpy.run_path(str(Path(__file__).parents[1] / "examples/18_three_terminal_vsc_hvdc.py"))


def arrays(result):
    columns = list(result.rows[0])
    data = np.array([[row[k] for k in columns] for row in result.rows])
    return {key: data[:, k] for k, key in enumerate(columns)}


def average(a, key, start, end):
    mask = (a["time"] >= start) & (a["time"] <= end)
    t = a["time"][mask]
    return np.trapezoid(a[key][mask], t) / (t[-1] - t[0])


@pytest.fixture(scope="module")
def fast(example):
    case = example["define_case"]()
    circuit = Circuit.from_components(case.name, case.components)
    result = Simulator(circuit, case.config, events=case.events, on_step=case.on_step).run()
    return case, result, arrays(result)


def test_single_bridge_open_loop_power_identity(example):
    controller = example["VSCController"]("S2", 50, 420e3, 230e3, 200e6, 1000)
    components = (*example["station_components"](controller),
                  VoltageSource("DCp", "S2:dc_p", "0", 200e3), VoltageSource("DCn", "S2:dc_n", "0", -200e3))
    def open_loop(row):
        controller.modulation = tuple(2*v/400e3 for v in dq_to_abc(
            math.sqrt(2/3)*230e3, 0, 2*math.pi*50*row["time"] - math.pi/2))
        return {}
    result = Simulator(Circuit.from_components("open_loop_vsc", components),
                       SimulationConfig(20e-6, .04, method="backward_euler"), on_step=open_loop).run()
    a = arrays(result)
    assert np.max(np.abs(a["i:S2:reactor:a"])) > 100  # 六开关实际激励网络。
    _assert_bridge_power(a, "S2", example)


def test_single_station_pll_and_dq_tracking_with_step_refinement(example):
    means = []
    for step in (20e-6, 10e-6):
        controller = example["VSCController"]("S2", 50, 420e3, 230e3, 200e6, 1000)
        components = (*example["station_components"](controller),
                      VoltageSource("DCp", "S2:dc_p", "0", 200e3), VoltageSource("DCn", "S2:dc_n", "0", -200e3))
        def sample(row):
            extra = controller.sample(row)
            if row["time"] == 0:
                controller.pll.angle += .1  # 只在初值人为偏置 PLL，随后由实测 PCC 纠正。
            return extra
        result = Simulator(Circuit.from_components("single_closed_loop", components),
                           SimulationConfig(step, .3, method="backward_euler"), on_step=sample).run()
        a = arrays(result)
        assert abs(average(a, "S2:P", .2, .3) - 200e6) < 5e6
        assert abs(average(a, "S2:PLL_frequency_Hz", .2, .3) - 50) < .05
        assert abs(average(a, "S2:PLL_Vq_pu", .2, .3)) < .01
        for axis in ("Id", "Iq"):
            assert abs(average(a, f"S2:{axis}", .2, .3) - average(a, f"S2:{axis}_ref", .2, .3)) < 25
        means.append(average(a, "S2:P", .2, .3))
    assert abs(means[0] - means[1]) < 4e6  # 相同 PWM/物理窗口；只检查平均 P，不声称波形二阶收敛。


def test_two_station_intermediate_dc_exchange(example):
    controllers = tuple(example["VSCController"](s, f, hv, 230e3, p, 1000) for s, f, hv, p in example["STATIONS"][:2])
    components = tuple(part for c in controllers for part in example["station_components"](c))
    components += example["dc_link_components"]("S1", "S2", 400e3)
    callback = example["HVDCControl"](controllers, (("S1", "S2"),))
    result = Simulator(Circuit.from_components("two_station_intermediate", components),
                       SimulationConfig(20e-6, .4, method="backward_euler"), on_step=callback).run()
    a = arrays(result)
    assert abs(average(a, "S1:Vdc", .3, .4) - 400e3) < 4e3
    assert average(a, "S1:Pdc", .3, .4) < -150e6
    assert average(a, "S2:Pdc", .3, .4) > 150e6
    assert np.max(np.abs(a["DC:balance_residual"])) < 1.0


def test_three_terminal_vsc_hvdc_fast_run(fast):
    case, result, a = fast
    assert sum(isinstance(c, IdealSwitch) for c in case.components) == 18
    assert sum(isinstance(c, ThreePhaseTransformer) for c in case.components) == 3
    assert len(result.rows) == round(case.config.stop_time / case.config.time_step) + 1
    assert all(np.isfinite(values).all() for values in a.values())
    for s in ("S1", "S2", "S3"):
        assert a[f"{s}:Vdc"][0] == pytest.approx(400e3)
        assert 320e3 < np.min(a[f"{s}:Vdc"]) <= np.max(a[f"{s}:Vdc"]) < 500e3
        for p in "abc":
            assert a[f"i:{s}:reactor:{p}"][0] == pytest.approx(0, abs=1e-9)
    # RC 清除缓冲应产生有限 EMT 暂态，不能重新出现纯 1 Mohm 开断的 GV 峰值。
    assert max(np.max(np.abs(a[f"v:S3:hv:{p}"])) for p in "abc") < 5e6


def test_three_plls_lock(fast):
    _, _, a = fast
    for start, end in ((.18, .28), (.7, .8)):
        for s, nominal in (("S1", 60), ("S2", 50), ("S3", 50)):
            assert abs(average(a, f"{s}:PLL_frequency_Hz", start, end) - nominal) < .05
            assert abs(average(a, f"{s}:PLL_Vq_pu", start, end)) < .01


def test_dc_slack_station_regulates_voltage_and_outer_controls_track(fast):
    _, _, a = fast
    for start, end in ((.18, .28), (.7, .8)):
        assert abs(average(a, "S1:Vdc", start, end) - 400e3) < 4e3
        for s, power in (("S2", 200e6), ("S3", -200e6)):
            assert abs(average(a, f"{s}:P", start, end) - power) < 10e6
        for s in ("S1", "S2", "S3"):
            assert abs(average(a, f"{s}:Vac_pu", start, end) - 1) < .02
            for axis in ("Id", "Iq"):
                assert abs(average(a, f"{s}:{axis}", start, end) - average(a, f"{s}:{axis}_ref", start, end)) < 25


def _assert_bridge_power(a, s, example):
    pac, dc_out, loss = np.zeros_like(a["time"]), np.zeros_like(a["time"]), np.zeros_like(a["time"])
    vp, vn = a[f"v:{s}:dc_p"], a[f"v:{s}:dc_n"]
    for p in "abc":
        va = a[f"v:{s}:bridge:{p}"]
        top, bottom = a[f"i:{s}:{p}_top"], a[f"i:{s}:{p}_bottom"]
        np.testing.assert_allclose(a[f"i:{s}:reactor:{p}"] + top, bottom, atol=1e-5, rtol=0)
        pac += va * a[f"i:{s}:reactor:{p}"]
        dc_out += -vp * top + vn * bottom
        for switch, voltage in (("top", vp-va), ("bottom", va-vn)):
            gate = a[f"state:{s}:{p}_{switch}"]
            conductance = gate/example["SWITCH_RON"] + (1-gate)*example["SWITCH_GOFF"]
            loss += conductance * voltage**2
    np.testing.assert_allclose(pac, dc_out + loss, atol=2, rtol=0)


def test_three_terminal_power_balance_reasonable_and_discrete_energy(fast, example):
    _, _, a = fast
    assert np.max(np.abs(a["DC:balance_residual"])) < 1.0  # W，对 200 MW 级功率。
    for s in ("S1", "S2", "S3"):
        _assert_bridge_power(a, s, example)
    # 独立按 C/L 状态计算后向欧拉离散能量：ΔE=h(Pin-Ri²)-数值耗散。
    energy, numerical_loss, resistance_loss = np.zeros_like(a["time"]), np.zeros(len(a["time"])-1), np.zeros_like(a["time"])
    for s in ("S1", "S2", "S3"):
        for pole in ("p", "n"):
            v = a[f"v:{s}:dc_{pole}"]
            energy += .5*example["POLE_CAPACITANCE"]*v*v
            numerical_loss += .5*example["POLE_CAPACITANCE"]*np.diff(v)**2
    for link in ("S1_S2", "S1_S3"):
        for pole in ("p", "n"):
            v = a[f"v:{link}:{pole}:mid"]
            energy += .5*example["LINE_MID_C"]*v*v
            numerical_loss += .5*example["LINE_MID_C"]*np.diff(v)**2
            for side in ("from", "to"):
                i = a[f"i:{link}:{pole}:L_{side}"]
                energy += .5*example["LINE_HALF_L"]*i*i
                numerical_loss += .5*example["LINE_HALF_L"]*np.diff(i)**2
                resistance_loss += example["LINE_HALF_R"]*i*i
    power_in = sum(a[f"{s}:Pdc"] for s in ("S1", "S2", "S3"))
    work = np.diff(a["time"])*(power_in[1:]-resistance_loss[1:])-numerical_loss
    # 事件行仅有右侧量；不跨越清除/投入所在区间作能量核对。
    mask = ~np.isclose(a["time"][1:, None], [.3, .45], rtol=0, atol=1e-12).any(axis=1)
    np.testing.assert_allclose(np.diff(energy)[mask], work[mask], atol=.02, rtol=0)
    assert abs(average(a, "DC:power_in", .7, .8)-average(a, "DC:loss", .7, .8)) < 5e6


def test_pwm_complementary_and_matches_recorded_carrier(fast):
    _, _, a = fast
    for s in ("S1", "S2", "S3"):
        for p in "abc":
            top, bottom = a[f"state:{s}:{p}_top"], a[f"state:{s}:{p}_bottom"]
            np.testing.assert_array_equal(top + bottom, 1)
            np.testing.assert_array_equal(top, a[f"{s}:m{p}"] >= a[f"{s}:carrier"])
            assert np.max(np.abs(a[f"{s}:m{p}_next"])) <= .98 + 1e-12
            assert np.count_nonzero(np.diff(top)) > 500


def test_fault_event_applies_and_clears(fast):
    _, result, a = fast
    assert len(result.event_log) == 6
    np.testing.assert_allclose(sorted({e["time"] for e in result.event_log}), [.3, .45], atol=1e-15, rtol=0)
    for p in "abc":
        np.testing.assert_array_equal(a[f"state:S3:fault:{p}"], (a["time"] >= .3) & (a["time"] < .45))
        active = a[f"state:S3:fault:{p}"] == 1
        np.testing.assert_allclose(a[f"i:S3:fault:{p}"][active], a[f"v:S3:hv:{p}"][active]/5, atol=1e-8, rtol=0)
    assert .1 < average(a, "S3:Vac_pu", .32, .43) < .3
    assert abs(average(a, "S3:Vac_pu", .7, .8)-1) < .02
    fault_window = (a["time"] >= .3) & (a["time"] <= .5)
    assert np.ptp(a["S3:Vdc"][fault_window]) > 10e3
