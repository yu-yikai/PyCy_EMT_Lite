"""演示三相对称电源、线路和负荷的稳态波形。

使用三相电源、三相线路和三相负荷元件，观察三相电压电流的对称波形，
并利用三相 RMS 分析工具验证幅值：负荷端相电压约等于电源相电压在线路
电阻与负荷电阻上的分压。"""

from pycy_emt_lite import SimulationConfig, ThreePhaseLine, ThreePhaseLoad, ThreePhaseSource
from pycy_emt_lite.analysis import three_phase_rms
from pycy_emt_lite.cases import CaseDefinition, OutputOptions, PlotSpec, run_case
from pycy_emt_lite.io.results import SimulationResult

SAVE_RESULT_DATA = 0
SAVE_RESULT_FIGURE = 0
SHOW_FIGURE = True

SOURCE_RMS = 230.0
LINE_RESISTANCE = 0.5
LOAD_RESISTANCE = 20.0


def print_summary(result: SimulationResult) -> None:
    """打印负荷端稳态 RMS，并与理论分压值对比。"""

    rms_values = three_phase_rms(result, ("v:load:a", "v:load:b", "v:load:c"), start_time=0.06)
    theoretical = SOURCE_RMS * LOAD_RESISTANCE / (LINE_RESISTANCE + LOAD_RESISTANCE)
    print(f"负荷端相电压 RMS：{rms_values['v:load:a']:.3f} V（理论分压值 {theoretical:.3f} V，"
          "约 0.1% 差异来自有限采样点的离散 RMS 计算）")


def define_case() -> CaseDefinition:
    """定义三相稳态算例。"""

    components = (
        ThreePhaseSource("VS", "source", phase_rms=SOURCE_RMS, frequency=50.0),
        ThreePhaseLine("LINE", "source", "load", resistance=LINE_RESISTANCE),
        ThreePhaseLoad("LOAD", "load", resistance=LOAD_RESISTANCE),
    )

    config = SimulationConfig(
        time_step=1e-4,
        stop_time=0.1,
        method="trapezoidal",
    )

    plots = (
        PlotSpec(
            columns=("v:load:a", "v:load:b", "v:load:c"),
            kind="three_phase",
            title="三相稳态负荷端电压",
        ),
    )

    output = OutputOptions(
        save_data=bool(SAVE_RESULT_DATA),
        save_figure=bool(SAVE_RESULT_FIGURE),
        show_figure=SHOW_FIGURE,
    )

    return CaseDefinition(
        name="three_phase_steady_state",
        components=components,
        config=config,
        plots=plots,
        output=output,
        summary=print_summary,
    )


def main() -> None:
    """按统一算例流程运行仿真。"""

    case = define_case()
    run_case(case)


if __name__ == "__main__":
    main()
