"""演示储能构网型变流器（虚拟同步机 VSG）孤岛运行。

VSG 控制器模拟同步发电机的惯性与阻尼，通过功率下垂建立孤岛电网的
频率和电压；储能电池通过 DC-link 提供功率支撑。本算例为控制级仿真，
观察负荷阶跃下频率与直流电压的动态响应。
"""

from pycy_emt_lite import BatteryModel, DCLink, SimulationResult, VSGController
from pycy_emt_lite.visualization import plot_series

TIME_STEP = 1e-4
STOP_TIME = 2.0
LOAD_STEP_TIME = 1.0

INITIAL_LOAD_POWER = 20000.0
STEPPED_LOAD_POWER = 32000.0


def main() -> None:
    """运行储能构网孤岛控制仿真。"""

    battery = BatteryModel(
        name="BAT1",
        nominal_voltage=800.0,
        capacity_ah=200.0,
        internal_resistance=0.05,
        initial_soc=0.5,
    )
    dc_link = DCLink(capacitance=20e-3, initial_voltage=800.0)
    vsg = VSGController(
        nominal_frequency=50.0,
        nominal_voltage=230.0,
        base_power=50000.0,
        inertia_constant=2.0,
        damping=20.0,
        active_power_reference=INITIAL_LOAD_POWER,
        reactive_power_reference=0.0,
        voltage_droop=0.01,
    )

    load_power = INITIAL_LOAD_POWER
    battery_power = 0.0

    rows: list[dict[str, float]] = []
    steps = int(round(STOP_TIME / TIME_STEP))
    for index in range(steps + 1):
        time = index * TIME_STEP
        if abs(time - LOAD_STEP_TIME) < 0.5 * TIME_STEP:
            load_power = STEPPED_LOAD_POWER

        # 1. VSG 按当前输出功率推进频率、相角和电压参考
        state = vsg.step(battery_power, 0.0, TIME_STEP)

        # 2. 电池按负荷功率输出并更新 SOC
        battery_power = load_power
        battery_state = battery.step(battery_power / dc_link.voltage, TIME_STEP)

        # 3. DC-link 能量平衡更新直流电压
        dc_link.step(battery_power, load_power, TIME_STEP)

        rows.append(
            {
                "time": time,
                "frequency": state.angular_frequency / (2.0 * 3.141592653589793),
                "voltage_reference": state.voltage_reference,
                "v_dc": dc_link.voltage,
                "soc": battery_state.state_of_charge,
                "p_load": load_power,
            }
        )

    result = SimulationResult(
        circuit_name="storage_grid_forming",
        method="trapezoidal",
        time_step=TIME_STEP,
        stop_time=STOP_TIME,
        rows=rows,
    )
    print(f"负荷阶跃前频率：{result.rows[0]['frequency']:.6f} Hz")
    print(f"负荷阶跃后频率：{result.rows[-1]['frequency']:.6f} Hz")
    print(f"最终 SOC：{result.rows[-1]['soc']:.6f}")
    plot_series(
        result,
        ("frequency", "voltage_reference", "v_dc", "soc"),
        title="储能构网 VSG 负荷阶跃响应",
    )


if __name__ == "__main__":
    main()
