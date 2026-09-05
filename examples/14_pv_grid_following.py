"""演示光伏并网系统简化模型与跟网控制。

光伏阵列通过 DC-link 与平均逆变器相连，跟网控制器按功率参考计算 dq
电流参考，逆变器把光伏功率送入电网。本算例为控制级仿真，观察辐照度
阶跃下直流电压与有功输出的动态响应。
"""

from pycy_emt_lite.controls import PIController
from pycy_emt_lite.io.results import SimulationResult
from pycy_emt_lite.renewables import DCLink, GridFollowingPowerController, PVArrayModel
from pycy_emt_lite.visualization import plot_series

TIME_STEP = 2e-5
STOP_TIME = 0.2
IRRADIANCE_STEP_TIME = 0.1
CURRENT_TIME_CONSTANT = 5e-3

GRID_PHASE_RMS = 230.0
GRID_D_VOLTAGE = 1.5 * 230.0  # 幅值不变变换下 d 轴电压为相电压幅值
GRID_Q_VOLTAGE = 0.0


def main() -> None:
    """运行光伏跟网控制仿真。"""

    pv_array = PVArrayModel(
        name="PV1",
        short_circuit_current=60.0,
        open_circuit_voltage=900.0,
        mpp_voltage=700.0,
        mpp_current=50.0,
    )
    dc_link = DCLink(capacitance=10e-3, initial_voltage=800.0)
    controller = GridFollowingPowerController(
        d_current_controller=PIController(proportional_gain=1.0, integral_gain=80.0, lower=-1000.0, upper=1000.0),
        q_current_controller=PIController(proportional_gain=1.0, integral_gain=80.0, lower=-1000.0, upper=1000.0),
        filter_inductance=5e-3,
        filter_resistance=0.1,
        current_limit=100.0,
    )

    irradiance = 1000.0
    d_current = 0.0
    q_current = 0.0
    inverter_power = 0.0

    rows: list[dict[str, float]] = []
    steps = int(round(STOP_TIME / TIME_STEP))
    for index in range(steps + 1):
        time = index * TIME_STEP
        if abs(time - IRRADIANCE_STEP_TIME) < 0.5 * TIME_STEP:
            irradiance = 600.0

        # 1. 光伏输出功率：按当前直流电压与辐照度查 I-V 曲线
        pv_power = pv_array.power(dc_link.voltage, irradiance=irradiance)

        # 2. 跟网控制器：把光伏功率作为有功参考，生成 dq 电流参考
        current_state = controller.current_references(
            pv_power,
            0.0,
            GRID_D_VOLTAGE,
            GRID_Q_VOLTAGE,
        )

        # 3. 电流动态：一阶近似 L 滤波器跟踪电流参考
        d_current += TIME_STEP / CURRENT_TIME_CONSTANT * (current_state[0] - d_current)
        q_current += TIME_STEP / CURRENT_TIME_CONSTANT * (current_state[1] - q_current)
        inverter_power = 1.5 * GRID_D_VOLTAGE * d_current

        # 4. DC-link 能量平衡更新直流电压
        dc_link.step(pv_power, inverter_power, TIME_STEP)

        rows.append(
            {
                "time": time,
                "v_dc": dc_link.voltage,
                "p_pv": pv_power,
                "p_inverter": inverter_power,
                "i_d": d_current,
                "i_d_ref": current_state[0],
            }
        )

    result = SimulationResult(
        circuit_name="pv_grid_following",
        method="trapezoidal",
        time_step=TIME_STEP,
        stop_time=STOP_TIME,
        rows=rows,
    )

    def value_at(target_time: float, column: str) -> float:
        """返回最接近指定时刻的记录值。"""

        return float(min(rows, key=lambda row: abs(row["time"] - target_time))[column])

    print(f"辐照度阶跃前（t=0.09 s）：Vdc={value_at(0.09, 'v_dc'):.2f} V，P_inv={value_at(0.09, 'p_inverter'):.0f} W")
    print(f"辐照度阶跃后（t=0.19 s）：Vdc={value_at(0.19, 'v_dc'):.2f} V，P_inv={value_at(0.19, 'p_inverter'):.0f} W")
    plot_series(
        result,
        ("v_dc", "p_pv", "p_inverter"),
        title="光伏跟网系统辐照度阶跃响应",
    )


if __name__ == "__main__":
    main()
