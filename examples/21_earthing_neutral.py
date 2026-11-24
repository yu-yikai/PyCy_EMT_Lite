"""不平衡星形电阻负荷：接地中性点与浮动中性点的对照。

运行：uv run python examples/21_earthing_neutral.py
建议在05平衡三相之后学习；两组独立理想三相源的源中性点均接地：

    grounded:a/b/c -- Rg:a/b/c -- 0
    floating:a/b/c -- Rf:a/b/c -- floating:n（共用星点，无接地支路）

电源相电压峰值100 V、60 Hz，abc正序正弦；100 V不是RMS或线电压。
初始三相电阻均为1 Ω，50 ms时A相改为3 Ω，70 ms时C相改为1.5 Ω。
电流正向为相节点到负荷中性点，电源原生支路电流方向与之相反。

接地组的负荷相电压由理想源固定，不平衡电流可经接地回线返回。
浮动组必须满足三相电流和为零，星点电位移动，改变各相负荷电压。
没有电感或电容；负荷改变时电流和星点电压可以跳变，不是储能暂态。

练习：改变A相改变后的电阻，观察浮动星点和其他两相负荷电压；
相间电压仍由理想源决定，不能仅看线电压判断负荷相电压是否正常。
参考仅适用于恢复默认参数后。官方第三组各相回线开路，本例明确省略；
浮动星形不是各相开路。真实参考与官方电流图例互换的证据见
validation/cases/earthing/README.md；这里仅绘制PyCy自身结果。
"""

import math
from collections.abc import Mapping
from dataclasses import dataclass
from numbers import Real

import numpy as np

from pycy_emt_lite import Circuit, Resistor, SimulationConfig, ThreePhaseSource
from pycy_emt_lite.cases import CaseDefinition, OutputOptions, PlotSpec, run_case
from pycy_emt_lite.events import SimulationEvent
from pycy_emt_lite.io.results import SimulationResult

# 1. Parameters (SI units)
SAVE_RESULT_DATA = 0
SAVE_RESULT_FIGURE = 0
SHOW_FIGURE = True
SOURCE_PHASE_PEAK = 100.0  # V; ThreePhaseSource below takes phase RMS.
FREQUENCY = 60.0          # Hz
INITIAL_SOURCE_ANGLE = 0.0  # rad; sine convention, offsets 0/-120/+120 degrees.
INITIAL_RESISTANCE = 1.0  # ohm, each of six load resistors
PHASE_A_RESISTANCE_AFTER = 3.0
PHASE_C_RESISTANCE_AFTER = 1.5
PHASE_A_CHANGE_TIME = 0.05  # s
PHASE_C_CHANGE_TIME = 0.07  # s
TIME_STEP = 100e-6
STOP_TIME = 0.1


@dataclass(frozen=True)
class ResistanceChangeEvent(SimulationEvent):
    """本例的有限正电阻阶跃；沿用既有事件右侧一致求解。"""

    resistance: float = 1.0

    def validate(self, circuit: Circuit) -> None:
        targets = [component for component in circuit.components if component.name == self.target]
        if len(targets) != 1 or not isinstance(targets[0], Resistor):
            raise ValueError(f"电阻事件目标 {self.target!r} 必须为本例中的Resistor；请核对元件名。")
        if (isinstance(self.resistance, bool) or not isinstance(self.resistance, Real)
                or not math.isfinite(self.resistance) or self.resistance <= 0):
            raise ValueError(f"电阻事件 {self.target!r} 的resistance必须为有限正实数；请填写欧姆值。")

    def apply(self, circuit: Circuit, applied_time: float) -> dict[str, float | str]:
        resistor = next(component for component in circuit.components if component.name == self.target)
        assert isinstance(resistor, Resistor)
        before = resistor.resistance
        resistor.resistance = float(self.resistance)
        return {"time": applied_time, "scheduled_time": self.time, "type": "resistance_change",
                "target": self.target, "before": before, "after": resistor.resistance, "name": self.name}


def record_measurements(row: Mapping[str, float]) -> dict[str, float]:
    """只从已求得的节点电压/支路电流派生测量，不更新控制或电气状态。"""
    neutral = row["v:floating:n"]
    return {
        **{f"v:floating_load:{phase}": row[f"v:floating:{phase}"] - neutral for phase in "abc"},
        "i:grounded:return": sum(row[f"i:Rg:{phase}"] for phase in "abc"),
    }


def print_summary(result: SimulationResult) -> None:
    """按采样点说明中性点移动、接地回流和浮动星点KCL。"""
    floating_sum = sum(result.series(f"i:Rf:{phase}") for phase in "abc")
    print(f"浮动星点对地电压采样峰值：{np.max(np.abs(result.series('v:floating:n'))):.6f} V")
    print(f"接地回线电流采样峰值：{np.max(np.abs(result.series('i:grounded:return'))):.6f} A")
    print(f"浮动组三相电流和最大绝对值：{np.max(np.abs(floating_sum)):.3e} A")
    print("两组源相对地电压相同；浮动负荷相电压需减去星点电压。电路无储能。")


def define_case() -> CaseDefinition:
    """2. Build fresh networks; 3. Define load events, configuration and plots."""
    components = []
    for group, resistor_prefix, neutral in (("grounded", "Rg", "0"), ("floating", "Rf", "floating:n")):
        source_name = "Vg" if group == "grounded" else "Vf"
        components.append(ThreePhaseSource(source_name, group, SOURCE_PHASE_PEAK / math.sqrt(2),
                                           FREQUENCY, neutral="0", initial_angle=INITIAL_SOURCE_ANGLE))
        components.extend(Resistor(f"{resistor_prefix}:{phase}", f"{group}:{phase}", neutral, INITIAL_RESISTANCE)
                          for phase in "abc")
    events = tuple(
        ResistanceChangeEvent(time, f"{prefix}:{phase}", f"phase_{phase}_resistance", resistance)
        for time, phase, resistance in ((PHASE_A_CHANGE_TIME, "a", PHASE_A_RESISTANCE_AFTER),
                                        (PHASE_C_CHANGE_TIME, "c", PHASE_C_RESISTANCE_AFTER))
        for prefix in ("Rg", "Rf")
    )
    return CaseDefinition(
        name="earthing_neutral", components=tuple(components),
        config=SimulationConfig(TIME_STEP, STOP_TIME), events=events, on_step=record_measurements,
        plots=(
            PlotSpec(tuple(f"v:{group}:{phase}" for group in ("grounded", "floating_load") for phase in "abc"),
                     "phase_voltages.png", title="Load phase-to-neutral voltages (V)"),
            PlotSpec(tuple(f"i:{prefix}:{phase}" for prefix in ("Rg", "Rf") for phase in "abc"),
                     "currents.png", title="Source-to-load phase currents (A)"),
            PlotSpec(("v:floating:n",), "neutral.png", title="Floating load neutral to ground (V)"),
        ),
        output=OutputOptions(save_data=bool(SAVE_RESULT_DATA), save_figure=bool(SAVE_RESULT_FIGURE), show_figure=SHOW_FIGURE),
        summary=print_summary,
    )


def main() -> None:
    """4. Run; 5. Summarize; 6. Plot PyCy waveforms only."""
    run_case(define_case())


if __name__ == "__main__":
    main()
