"""三相Y–Δ–Y变压器链：绕组变比、浮动星点和Δ电压参考。

运行：uv run python examples/24_three_phase_transformer_chain.py

三相内电势 -- 每相Rs、Ls -- lv -- Tup(Y/Δ) -- hv -- Tdown(Δ/Y) -- 固定电阻负荷

源相峰值13kV、60Hz；源电感从零电流启动，最快时间常数约3.97μs。
两台变压器的线额定电压为13/115kV，传入元件的却是每相绕组电压比。
Δ按AB/BC/CA接线，绕组电流与三根外部导线的电流不同。
两个Y星点各自浮动；hv的三相平均电势为零只固定电压参考，不构成接地回路。
变压器不含漏感、励磁或饱和；原网络没有实际线路段。
"""

import math
from dataclasses import dataclass, field

import numpy as np

from pycy_emt_lite import (
    Inductor,
    Resistor,
    SimulationConfig,
    VoltageSource,
)
from pycy_emt_lite.analysis import rms
from pycy_emt_lite.cases import CaseDefinition, OutputOptions, PlotSpec, run_case
from pycy_emt_lite.components.base import Component
from pycy_emt_lite.components.transformers import ThreePhaseTransformer
from pycy_emt_lite.core.context import StampContext
from pycy_emt_lite.core.nodes import NodeManager
from pycy_emt_lite.core.variables import VariableManager
from pycy_emt_lite.io.results import SimulationResult
from pycy_emt_lite.visualization import plot_zoom_window

SAVE_RESULT_DATA = 0
SAVE_RESULT_FIGURE = 0
SHOW_FIGURE = True

SOURCE_PHASE_PEAK = 13000.0
FREQUENCY = 60.0
SHORT_CIRCUIT_POWER = 1e6
SOURCE_X_OVER_R = 15.0
SOURCE_LINE_RMS = math.sqrt(3 / 2) * SOURCE_PHASE_PEAK
SOURCE_RESISTANCE = SOURCE_LINE_RMS**2 / SHORT_CIRCUIT_POWER / math.sqrt(1 + SOURCE_X_OVER_R**2)
SOURCE_INDUCTANCE = SOURCE_X_OVER_R * SOURCE_RESISTANCE / (2 * math.pi * FREQUENCY)
TURNS_RATIO_UP = (13000 / math.sqrt(3)) / 115000
UP_RESISTANCE = 0.0338         # Ω，两绕组铜阻精确折算到Tup的Y一次侧
DOWN_RESISTANCE = 7.935       # Ω，折算到Tdown的Δ一次绕组
LOAD_RESISTANCE = 169000.0    # Ω，固定阻抗；额定1kW不是恒功率控制
TIME_STEP = 0.5e-6
STOP_TIME = 0.05


@dataclass(slots=True)
class DeltaCenterReference(Component):
    """仅本例hv母线的理想中心参考：mean(vhv)=0，各相参考电流λ/3。

    三线岛的总KCL强制λ=0；它不会提供零序回路或消耗功率。
    """

    name: str = "DeltaCenter"
    branch_index: int | None = field(default=None, init=False)

    def nodes(self) -> tuple[str, str, str]:
        return ("hv:a", "hv:b", "hv:c")

    def register(self, node_manager: NodeManager, variable_manager: VariableManager) -> None:
        self.branch_index = variable_manager.add_branch_current(self.name)

    def stamp(self, context: StampContext, matrix: np.ndarray, rhs: np.ndarray) -> None:
        assert self.branch_index is not None
        branch = context.branch_offset + self.branch_index
        for node in self.nodes():
            index = context.node_index(node)
            assert index is not None
            matrix[index, branch] += 1 / 3
            matrix[branch, index] += 1 / 3

    def outputs(self, context: StampContext, solution: np.ndarray) -> dict[str, float]:
        assert self.branch_index is not None
        return {f"i:{self.name}": float(solution[context.branch_offset + self.branch_index])}


def create_components() -> tuple[Component, ...]:
    """先列出各相源/R/L/负荷，再连接两个现有三相变压器。"""

    components: list[Component] = []
    for phase, angle in zip("abc", (0.0, -2 * math.pi / 3, 2 * math.pi / 3), strict=True):
        components.extend((
            VoltageSource(f"Vs_{phase}", f"emf_{phase}", "0",
                          lambda time, angle=angle: SOURCE_PHASE_PEAK * math.sin(2 * math.pi * FREQUENCY * time + angle)),
            Resistor(f"Rs_{phase}", f"emf_{phase}", f"rl_{phase}", SOURCE_RESISTANCE),
            Inductor(f"Ls_{phase}", f"rl_{phase}", f"lv:{phase}", SOURCE_INDUCTANCE, initial_current=0),
            Resistor(f"Rload_{phase}", f"load:{phase}", "0", LOAD_RESISTANCE),
        ))
    components.extend((
        ThreePhaseTransformer("Tup", "lv", "hv", TURNS_RATIO_UP, "Y", "D",
                              primary_neutral="n_up", leakage_resistance=UP_RESISTANCE),
        ThreePhaseTransformer("Tdown", "hv", "load", 1 / TURNS_RATIO_UP, "D", "Y",
                              secondary_neutral="n_down", leakage_resistance=DOWN_RESISTANCE),
        DeltaCenterReference(),
    ))
    return tuple(components)


def print_summary(result: SimulationResult) -> None:
    """显示固定阻抗实际工作点，并区分线比和绕组比。"""

    voltage = rms(result, "v:load:a", start_time=1 / FREQUENCY, end_time=STOP_TIME)
    current = rms(result, "i:Rload_a", start_time=1 / FREQUENCY, end_time=STOP_TIME)
    print(f"负荷A相稳态：{voltage:.3f} V RMS，{current:.6f} A RMS；三相总功率约{3 * voltage * current:.3f} W。")
    print(f"升压绕组变比{TURNS_RATIO_UP:.9f}，额定线电压比13/115；两者相差√3。")
    print("i:Tup:secondary:a/b/c为Δ绕组电流；流入Tup副侧的a线电流为绕组a减c，沿链送电方向再取反。")
    print("中间母线相对lv滞后30°，负荷侧恢复同相；两个浮动Y星点与Δ中心参考作用不同。")
    print(f"参考总电流最大{np.max(np.abs(result.series('i:DeltaCenter'))):.3g} A。")


def define_case() -> CaseDefinition:
    plots = (
        PlotSpec(("v:lv:a", "v:lv:b", "v:lv:c"), "lv_voltages.png", kind="three_phase",
                 title="Transformer primary terminal voltages (V)"),
        PlotSpec(("v:hv:a", "v:hv:b", "v:hv:c"), "hv_voltages.png", kind="three_phase",
                 title="Delta bus voltages relative to its center (V)"),
        PlotSpec(("v:load:a", "v:load:b", "v:load:c"), "load_voltages.png", kind="three_phase",
                 title="Fixed resistor load voltages (V)"),
        PlotSpec(("i:Ls_a", "i:Ls_b", "i:Ls_c"), "source_currents.png", kind="three_phase",
                 title="Source currents: zero-current startup (A)"),
    )
    return CaseDefinition(
        name="three_phase_transformer_chain", components=create_components(),
        config=SimulationConfig(TIME_STEP, STOP_TIME, method="trapezoidal", linear_solver_mode="reuse"),
        plots=plots, summary=print_summary,
        output=OutputOptions(save_data=bool(SAVE_RESULT_DATA), save_figure=bool(SAVE_RESULT_FIGURE),
                             show_figure=SHOW_FIGURE),
    )


def main() -> None:
    case = define_case()
    result = run_case(case)
    startup_path = case.output.output_root / case.name / "startup_currents.png" if case.output.save_figure else None
    plot_zoom_window(result, ("i:Ls_a", "i:Ls_b", "i:Ls_c"), 0, 40e-6, startup_path,
                     show=case.output.show_figure, title="Source currents during the first 40 microseconds (A)")


if __name__ == "__main__":
    main()
