"""演示三相并网逆变器平均模型与 dq 电流环控制。

逆变器通过 L 滤波器接入理想三相电网，dq 电流环用两个 PI 控制器分别调节
有功电流和无功电流。本算例为控制级仿真：每个控制周期内依次完成测量、
PI 调节、平均模型电压生成和 L 滤波器电流推进。
"""

import math

from pycy_emt_lite.controls import PIController, abc_to_dq, dq_to_abc
from pycy_emt_lite.converters import ThreePhaseAverageInverter
from pycy_emt_lite.io.results import SimulationResult
from pycy_emt_lite.visualization import plot_series

FREQUENCY = 50.0
GRID_RMS = 230.0
TIME_STEP = 2e-5
STOP_TIME = 0.1

FILTER_INDUCTANCE = 5e-3
FILTER_RESISTANCE = 0.1
DC_VOLTAGE = 650.0

D_CURRENT_REFERENCE = 30.0
Q_CURRENT_REFERENCE = 0.0


def main() -> None:
    """运行平均逆变器并网电流环控制仿真。"""

    d_pi = PIController(proportional_gain=0.5, integral_gain=50.0, lower=-200.0, upper=200.0)
    q_pi = PIController(proportional_gain=0.5, integral_gain=50.0, lower=-200.0, upper=200.0)
    inverter = ThreePhaseAverageInverter(dc_voltage=DC_VOLTAGE)

    omega = 2.0 * math.pi * FREQUENCY
    grid_amplitude = math.sqrt(2.0) * GRID_RMS
    d_current = 0.0
    q_current = 0.0

    rows: list[dict[str, float]] = []
    steps = int(round(STOP_TIME / TIME_STEP))
    for index in range(steps + 1):
        time = index * TIME_STEP
        grid_angle = omega * time

        # 1. 电网三相电压与 dq 分量（q 轴与 a 相电压对齐）
        grid_d = grid_amplitude
        grid_q = 0.0

        # 2. 电流内环：误差 -> PI -> dq 电压指令
        d_error = D_CURRENT_REFERENCE - d_current
        q_error = Q_CURRENT_REFERENCE - q_current
        d_voltage_command = d_pi.step(d_error, TIME_STEP) + grid_d - omega * FILTER_INDUCTANCE * q_current
        q_voltage_command = q_pi.step(q_error, TIME_STEP) + grid_q + omega * FILTER_INDUCTANCE * d_current

        # 3. 平均逆变器：dq 电压指令 -> 三相平均相电压
        inverter_voltage_abc = inverter.phase_voltages_from_dq(d_voltage_command, q_voltage_command, grid_angle)

        # 4. L 滤波器：前向欧拉推进电流
        v_d, v_q = abc_to_dq(*inverter_voltage_abc, grid_angle)
        d_current += TIME_STEP / FILTER_INDUCTANCE * (v_d - grid_d - FILTER_RESISTANCE * d_current + omega * FILTER_INDUCTANCE * q_current)
        q_current += TIME_STEP / FILTER_INDUCTANCE * (v_q - grid_q - FILTER_RESISTANCE * q_current - omega * FILTER_INDUCTANCE * d_current)

        rows.append(
            {
                "time": time,
                "i_d": d_current,
                "i_q": q_current,
                "i_d_ref": D_CURRENT_REFERENCE,
                "v_d_command": d_voltage_command,
            }
        )

    result = SimulationResult(
        circuit_name="three_phase_grid_inverter_average",
        method="trapezoidal",
        time_step=TIME_STEP,
        stop_time=STOP_TIME,
        rows=rows,
    )
    print(f"稳态 d 轴电流：{result.rows[-1]['i_d']:.3f} A（参考 {D_CURRENT_REFERENCE} A）")
    print(f"稳态 q 轴电流：{result.rows[-1]['i_q']:.3f} A（参考 {Q_CURRENT_REFERENCE} A）")
    plot_series(
        result,
        ("i_d", "i_q", "i_d_ref"),
        title="平均逆变器 dq 电流环响应",
    )


if __name__ == "__main__":
    main()
