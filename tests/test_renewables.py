"""
文件名称：test_renewables.py
文件作用：验证阶段 4 新能源并网、构网和跟网控制简化模型。
"""

import math

from pycy_emt_lite.controls import PIController
from pycy_emt_lite.renewables import (
    BatteryModel,
    DCLink,
    DroopController,
    GridFollowingPowerController,
    LVRTController,
    PVArrayModel,
    VSGController,
)


def test_pv_array_scales_power_with_irradiance() -> None:
    pv_array = PVArrayModel("PV", 10.0, 100.0, 80.0, 9.0)

    full_power = pv_array.mpp_power(irradiance=1000.0)
    half_power = pv_array.mpp_power(irradiance=500.0)

    assert math.isclose(half_power, 0.5 * full_power)
    assert pv_array.current(100.0) == 0.0
    assert pv_array.current(0.0) > pv_array.current(80.0)


def test_battery_discharge_reduces_soc_and_terminal_voltage() -> None:
    battery = BatteryModel("B1", nominal_voltage=400.0, capacity_ah=10.0, internal_resistance=0.1, initial_soc=0.5)

    before_soc = battery.state.state_of_charge
    before_voltage = battery.open_circuit_voltage()
    state = battery.step(current=20.0, time_step=10.0)

    assert state.state_of_charge < before_soc
    assert state.terminal_voltage < before_voltage
    assert state.power > 0.0


def test_dc_link_energy_balance_raises_and_drops_voltage() -> None:
    dc_link = DCLink(capacitance=1e-3, initial_voltage=100.0)

    raised = dc_link.step(source_power=200.0, load_power=0.0, time_step=1e-3)
    dropped = dc_link.step(source_power=0.0, load_power=200.0, time_step=1e-3)

    assert raised > 100.0
    assert dropped < raised


def test_grid_following_power_controller_maps_power_to_current() -> None:
    controller = GridFollowingPowerController(
        PIController(1.0, 10.0),
        PIController(1.0, 10.0),
        filter_inductance=1e-3,
        filter_resistance=0.05,
        current_limit=100.0,
    )

    d_reference, q_reference = controller.current_references(15_000.0, 3_000.0, 300.0, 0.0)

    assert math.isclose(d_reference, 15_000.0 / (1.5 * 300.0))
    assert math.isclose(q_reference, -3_000.0 / (1.5 * 300.0))


def test_droop_and_vsg_change_frequency_when_power_is_unbalanced() -> None:
    droop = DroopController(50.0, 325.0, 10_000.0, 0.0, frequency_droop=1e-3, voltage_droop=0.0)
    droop_state = droop.step(active_power=8_000.0, reactive_power=0.0, time_step=1e-3)

    vsg = VSGController(50.0, 325.0, base_power=20_000.0, inertia_constant=2.0, damping=1.0, active_power_reference=10_000.0)
    vsg_state = vsg.step(active_power=8_000.0, reactive_power=0.0, time_step=1e-2)

    assert droop_state.angular_frequency > 2.0 * math.pi * 50.0
    assert vsg_state.speed_pu > 1.0


def test_lvrt_latches_during_voltage_sag_and_clears_after_recovery() -> None:
    lvrt = LVRTController(nominal_voltage_rms=230.0)

    sag_state = lvrt.step(150.0, active_power_reference=10_000.0, reactive_power_reference=0.0)
    recovery_state = lvrt.step(230.0, active_power_reference=10_000.0, reactive_power_reference=0.0)

    assert sag_state.in_lvrt == 1.0
    assert sag_state.active_power_reference < 10_000.0
    assert sag_state.reactive_power_reference > 0.0
    assert recovery_state.in_lvrt == 0.0
