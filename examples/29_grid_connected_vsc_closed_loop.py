"""并网 VSC 闭环：先阶跃 d 轴参考，再观察 q 轴阶跃及两轴电流。

电流以电网流向变流器为正。借用电网的已知相角将三相量变换到 dq 坐标，
使用两个 PI、网压前馈和电感交叉项。桥侧电压升高会减小正向电流，
因此 PI 输出从桥侧电压指令中减去。

每 100 µs 在电气求解后采样。新指令从下一 5 µs 门极拍生效，
2.5 µs 电气网格的中点也保持同一门极状态。
"""

from pycy_emt_lite import SimulationConfig
from pycy_emt_lite.cases import CaseDefinition, OutputOptions, PlotSpec, run_case
from pycy_emt_lite.converters import _grid_vsc
from pycy_emt_lite.converters._grid_vsc_current_loop import (
    VOLTAGE_LIMIT,
    create_current_loop,
)
from pycy_emt_lite.io.results import SimulationResult

SAVE_RESULT_DATA = 0
SAVE_RESULT_FIGURE = 0
SHOW_FIGURE = True

TIME_STEP = _grid_vsc.TIME_STEP
STOP_TIME = 0.2


def print_summary(result: SimulationResult) -> None:
    print(f"并网 VSC 闭环。电气步长 {result.time_step * 1e6:g} 微秒，控制周期 100 微秒，门极周期 5 微秒。")
    print(f"交流电流以电网流向变流器为正。dq 电压指令限幅 {VOLTAGE_LIMIT:g} V。")
    print(f"末点电流参考为 d = {result.series('id_ref')[-1]:g} A，q = {result.series('iq_ref')[-1]:g} A。")


def define_case(
    *, scenario: str = "main", time_step: float = TIME_STEP, stop_time: float = STOP_TIME,
) -> CaseDefinition:
    """每次建立独立的 PI 和门极。main 在 40/80 ms 依次阶跃 d/q 轴，d_only 只阶跃 d 轴。"""
    if scenario not in ("main", "d_only"):
        raise ValueError("scenario 必须为 main 或 d_only。")
    time_step = _grid_vsc.checked_time_step(time_step)
    components, observe = create_current_loop(time_step, scenario=scenario)

    return CaseDefinition(
        name="grid_connected_vsc_closed_loop",
        components=components,
        config=SimulationConfig(time_step, stop_time, method="trapezoidal", linear_solver_mode="reuse",
                                event_time_policy="require_aligned"),
        plots=(
            PlotSpec(("id", "id_ref", "iq", "iq_ref"), "dq_currents.png", title="dq currents and references (A)"),
            PlotSpec(("i:La", "i:Lb", "i:Lc"), "phase_currents.png", kind="three_phase",
                     title="Grid-to-bridge phase currents (A)"),
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
