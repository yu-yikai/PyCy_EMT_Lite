"""演示 VSC-HVDC 简化平均模型的功率传输与直流电压调节。

送端 VSC 按功率参考向直流链路注入有功，受端 VSC 通过电压调节器维持
直流电压并吸收功率。本算例为控制级仿真，观察送端功率阶跃下直流电压
与两端功率的动态响应。
"""

import math

from pycy_emt_lite.converters import VSCHVDCLinkAverage
from pycy_emt_lite.io.results import SimulationResult
from pycy_emt_lite.visualization import plot_series

RATED_DC_VOLTAGE = 300e3
RATED_POWER = 300e6
DC_CAPACITANCE = 1e-4
DC_RESISTANCE = 3.76
TIME_STEP = 1e-4
STOP_TIME = 2.0
POWER_STEP_TIME = 0.5
POWER_TIME_CONSTANT = 0.04
VOLTAGE_REGULATOR_GAIN = 1e3


def first_order_step(current: float, target: float, time_step: float, time_constant: float) -> float:
    """用一阶滞后近似功率控制器的跟踪过程。"""

    if time_constant <= 0.0:
        return target
    factor = min(time_step / time_constant, 1.0)
    return current + factor * (target - current)


def main() -> None:
    """运行 VSC-HVDC 平均模型功率阶跃仿真。"""

    dc_link = VSCHVDCLinkAverage(
        dc_voltage=RATED_DC_VOLTAGE,
        dc_capacitance=DC_CAPACITANCE,
        dc_resistance=DC_RESISTANCE,
    )

    sending_power = 0.2 * RATED_POWER
    receiving_power = 0.2 * RATED_POWER
    dc_voltage = RATED_DC_VOLTAGE

    rows: list[dict[str, float]] = []
    steps = int(round(STOP_TIME / TIME_STEP))
    for index in range(steps + 1):
        time = index * TIME_STEP

        # 1. 送端功率参考：0.5 s 时从 0.2 pu 阶跃到 0.8 pu
        sending_target = 0.8 * RATED_POWER if time >= POWER_STEP_TIME else 0.2 * RATED_POWER
        sending_power = first_order_step(sending_power, sending_target, TIME_STEP, POWER_TIME_CONSTANT)

        # 2. 受端电压调节：按直流电压偏差调整受端吸收功率
        voltage_error = dc_voltage - RATED_DC_VOLTAGE
        receiving_target = sending_power + VOLTAGE_REGULATOR_GAIN * voltage_error
        receiving_power = first_order_step(receiving_power, receiving_target, TIME_STEP, POWER_TIME_CONSTANT)

        # 3. 直流链路能量平衡更新直流电压
        dc_voltage = dc_link.step(dc_voltage, sending_power, receiving_power, TIME_STEP)

        rows.append(
            {
                "time": time,
                "v_dc": dc_voltage,
                "p_sending_pu": sending_power / RATED_POWER,
                "p_receiving_pu": receiving_power / RATED_POWER,
                "p_sending_ref_pu": sending_target / RATED_POWER,
            }
        )

    result = SimulationResult(
        circuit_name="vsc_hvdc_average",
        method="explicit_control",
        time_step=TIME_STEP,
        stop_time=STOP_TIME,
        rows=rows,
    )
    print(f"功率阶跃前直流电压：{result.rows[0]['v_dc'] / 1000.0:.1f} kV")
    print(f"功率阶跃后直流电压：{result.rows[-1]['v_dc'] / 1000.0:.1f} kV（额定 {RATED_DC_VOLTAGE / 1000.0:.0f} kV）")
    print(f"最终送端功率：{result.rows[-1]['p_sending_pu']:.4f} pu")
    plot_series(
        result,
        ("v_dc", "p_sending_pu", "p_receiving_pu", "p_sending_ref_pu"),
        title="VSC-HVDC 平均模型功率阶跃响应",
    )


if __name__ == "__main__":
    main()
