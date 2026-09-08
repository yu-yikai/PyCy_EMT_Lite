"""演示同步旋转坐标系锁相环 SRF-PLL 的锁定过程。

三相电压实际相位超前 30°，PLL 从 0 相位开始通过 PI 调节 q 轴电压，
逐步锁定到电网电压的相位和频率。本算例为纯控制仿真，不涉及 MNA 网络。
"""

import math

from pycy_emt_lite.controls import SRFPLL
from pycy_emt_lite.io.results import SimulationResult
from pycy_emt_lite.visualization import plot_series

FREQUENCY = 50.0
PHASE_RMS = 230.0
TIME_STEP = 1e-4
STOP_TIME = 1.0
ANGLE_OFFSET_DEG = 30.0


def grid_voltages(time: float) -> tuple[float, float, float]:
    """返回电网三相瞬时电压（相位超前 ANGLE_OFFSET_DEG 度）。"""

    omega = 2.0 * math.pi * FREQUENCY
    offset = math.radians(ANGLE_OFFSET_DEG)
    amplitude = math.sqrt(2.0) * PHASE_RMS
    return (
        amplitude * math.sin(omega * time + offset),
        amplitude * math.sin(omega * time + offset - 2.0 * math.pi / 3.0),
        amplitude * math.sin(omega * time + offset + 2.0 * math.pi / 3.0),
    )


def main() -> None:
    """运行 PLL 动态响应控制仿真。"""

    pll = SRFPLL(
        proportional_gain=100.0,
        integral_gain=1000.0,
        nominal_frequency=2.0 * math.pi * FREQUENCY,
        initial_angle=0.0,
    )

    rows: list[dict[str, float]] = []
    steps = int(round(STOP_TIME / TIME_STEP))
    for index in range(steps + 1):
        time = index * TIME_STEP
        state = pll.step(grid_voltages(time), TIME_STEP)
        rows.append(
            {
                "time": time,
                "angle": state.angle,
                "frequency": state.frequency,
                "q_axis_voltage": state.q_axis_voltage,
            }
        )

    result = SimulationResult(
        circuit_name="pll_dynamic_response",
        method="explicit_control",
        time_step=TIME_STEP,
        stop_time=STOP_TIME,
        rows=rows,
    )
    last = result.rows[-1]
    # PLL 收敛判据：q 轴电压趋近 0（d 轴对齐电网电压矢量），频率趋近额定角频率
    print(f"最终 q 轴电压：{last['q_axis_voltage']:.3f} V（收敛目标 0 V）")
    print(f"最终频率：{last['frequency']:.6f} rad/s（额定 {2.0 * math.pi * FREQUENCY:.6f} rad/s）")
    print(f"最终锁相角度：{last['angle']:.6f} rad")
    plot_series(
        result,
        ("angle", "frequency", "q_axis_voltage"),
        title="SRF-PLL 锁定过程",
    )


if __name__ == "__main__":
    main()
