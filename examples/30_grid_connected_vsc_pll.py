"""用锁相环估计并网 VSC 电流控制所需的角度。

电网电压从零升起，PLL 以超前 15 度的角度和 60 Hz 起步。
每 100 微秒求解后用同一行的电网电压和电感电流更新控制。
从下一 5 微秒门极拍开始使用新的调制指令。

先观察相角误差和频率，再看 d、q 轴电流分别跟随 40、80 毫秒的参考阶跃。
"""

import math

from pycy_emt_lite import SimulationConfig
from pycy_emt_lite.cases import CaseDefinition, OutputOptions, PlotSpec, run_case
from pycy_emt_lite.controls import SRFPLL
from pycy_emt_lite.converters import _grid_vsc
from pycy_emt_lite.converters._grid_vsc_current_loop import (
    GRID_ANGULAR_FREQUENCY,
    create_current_loop,
)
from pycy_emt_lite.io.results import SimulationResult

SAVE_RESULT_DATA = 0
SAVE_RESULT_FIGURE = 0
SHOW_FIGURE = True

TIME_STEP = _grid_vsc.TIME_STEP
STOP_TIME = 0.2


def print_summary(result: SimulationResult) -> None:
    frequency = result.series("pll_frequency_hz")[-1]
    angle_error = result.series("pll_angle_error_deg")[-1]
    print(f"PLL 末点估计频率为 {frequency:.6f} Hz，最近控制采样的相角误差为 {angle_error:.6f} 度。")
    print("电流以电网流向变流器为正。dq 电流图使用 PLL 估计的相角。")


def define_case(*, time_step: float = TIME_STEP, stop_time: float = STOP_TIME) -> CaseDefinition:
    """默认运行 0.2 秒，可用 5 或 2.5 微秒电气步长。"""
    time_step = _grid_vsc.checked_time_step(time_step)
    pll = SRFPLL(
        proportional_gain=100.0,
        integral_gain=1000.0,
        nominal_frequency=GRID_ANGULAR_FREQUENCY,
        initial_angle=19 * math.pi / 12,
    )
    components, observe = create_current_loop(time_step, pll=pll)
    return CaseDefinition(
        name="grid_connected_vsc_pll",
        components=components,
        config=SimulationConfig(time_step, stop_time, method="trapezoidal", linear_solver_mode="reuse",
                                event_time_policy="require_aligned"),
        plots=(
            PlotSpec(("pll_angle_error_deg",), "pll_angle_error.png", title="PLL angle error at control samples (deg)"),
            PlotSpec(("pll_frequency_hz", "grid_frequency_hz"), "pll_frequency.png", title="PLL and grid frequency (Hz)"),
            PlotSpec(("id", "id_ref", "iq", "iq_ref"), "dq_currents.png", title="Currents in the PLL dq frame (A)"),
        ),
        output=OutputOptions(save_data=bool(SAVE_RESULT_DATA), save_figure=bool(SAVE_RESULT_FIGURE),
                             show_figure=SHOW_FIGURE),
        summary=print_summary,
        on_step=observe,
    )


def main() -> None:
    run_case(define_case())


if __name__ == "__main__":
    main()
