"""外置三电感T等效变压器：漏感、励磁支路与阶跃响应。

运行：uv run python examples/23_transformer_t_equivalent.py

src--Rs--pri_in--L1--core_p--理想T(.2:1)--sec_p--L2--load--Rload--0
                       |
                      Lm
                       |
                       0

Lm在原边漏感之后；不能直接替换例09的输入端聚合励磁参数。
L1/L2/Lm分别.01/.25/.1H，Rs与Rload均1Ω。零初值，2s时源0→1V。
电感电流连续而内部电压瞬变，负载电流先上升再衰减。8s仍不是最终DC极限。
线性回路不包含磁饱和、磁滞或铁损，也不证明真实变压器允许持续直流。
真实参考与独立验收见validation/cases/transformer_t_equivalent。
"""

import math
from dataclasses import dataclass

import numpy as np

from pycy_emt_lite import (
    Circuit,
    Inductor,
    Resistor,
    SimulationConfig,
    SinglePhaseTransformer,
    VoltageSource,
)
from pycy_emt_lite.cases import CaseDefinition, OutputOptions, PlotSpec, run_case
from pycy_emt_lite.events import SimulationEvent
from pycy_emt_lite.io.results import SimulationResult

SAVE_RESULT_DATA = 0
SAVE_RESULT_FIGURE = 0
SHOW_FIGURE = True

TURNS_RATIO = 0.2               # primary voltage / secondary voltage
PRIMARY_LEAKAGE = 0.01          # H
SECONDARY_LEAKAGE = 0.25        # H
MAGNETIZING_INDUCTANCE = 0.1    # H, external branch after L1
SOURCE_RESISTANCE = 1.0         # ohm
LOAD_RESISTANCE = 1.0           # ohm
SOURCE_AFTER_STEP = 1.0         # V
STEP_TIME = 2.0                # s
TIME_STEP = 1e-3               # s
STOP_TIME = 8.0                # s


@dataclass(frozen=True)
class SourceLevelEvent(SimulationEvent):
    """显式改变常值源，沿用既有左右侧一致求解与储能连续机制。"""

    level: float = 0.0

    def validate(self, circuit: Circuit) -> None:
        sources = [item for item in circuit.components if item.name == self.target]
        if len(sources) != 1 or not isinstance(sources[0], VoltageSource):
            raise ValueError("电压阶跃目标必须是本例的VoltageSource")
        if isinstance(self.level, bool) or not math.isfinite(self.level) or callable(sources[0].voltage):
            raise ValueError("电压阶跃需要有限实数和常值电压源")

    def apply(self, circuit: Circuit, applied_time: float) -> dict[str, float | str]:
        source = next(item for item in circuit.components if item.name == self.target)
        assert isinstance(source, VoltageSource) and not callable(source.voltage)
        before = source.voltage
        source.voltage = self.level
        return {"time": applied_time, "scheduled_time": self.time, "type": "source_level",
                "target": self.target, "before": before, "after": self.level, "name": self.name}


def create_components() -> tuple:
    return (
        VoltageSource("V1", "src", "0", 0.0),
        Resistor("Rs", "src", "pri_in", SOURCE_RESISTANCE),
        Inductor("L1", "pri_in", "core_p", PRIMARY_LEAKAGE, initial_current=0),
        Inductor("Lm", "core_p", "0", MAGNETIZING_INDUCTANCE, initial_current=0),
        SinglePhaseTransformer("T1", "core_p", "0", "sec_p", "0", turns_ratio=TURNS_RATIO),
        Inductor("L2", "sec_p", "load", SECONDARY_LEAKAGE, initial_current=0),
        Resistor("Rload", "load", "0", LOAD_RESISTANCE),
    )


def print_summary(result: SimulationResult) -> None:
    load = result.series("i:L2")
    peak = int(np.argmax(load))
    print(f"负载电流采样峰值{load[peak]:.9f}A，时刻{result.series('time')[peak]:.6f}s。")
    print(f"{STOP_TIME:g}s时：输入{result.series('i:L1')[-1]:.9f}A，"
          f"负载{load[-1]:.9f}A，励磁{result.series('i:Lm')[-1]:.9f}A。")
    print(f"线性回路渐近DC极限：输入与励磁{SOURCE_AFTER_STEP / SOURCE_RESISTANCE:g}A，负载0A；"
          "有限停止时刻不能代替渐近极限。")
    print("T1内部励磁未启用；实际励磁电流记录为i:Lm，理想副边端口电流与负载电流反号。")


def define_case() -> CaseDefinition:
    config = SimulationConfig(TIME_STEP, STOP_TIME, method="trapezoidal", linear_solver_mode="reuse")
    events = (SourceLevelEvent(time=STEP_TIME, target="V1", level=SOURCE_AFTER_STEP, name="source_step"),)
    plots = (
        PlotSpec(columns=("v:src", "v:core_p", "v:sec_p", "v:load"), figure_name="voltages.png",
                 title="T-equivalent transformer: source and winding voltages (V)"),
        PlotSpec(columns=("i:L1", "i:L2", "i:Lm"), figure_name="currents.png",
                 title="Source, load and external magnetizing currents (A)"),
    )
    return CaseDefinition(
        name="transformer_t_equivalent", components=create_components(), config=config, events=events,
        plots=plots, summary=print_summary,
        output=OutputOptions(save_data=bool(SAVE_RESULT_DATA), save_figure=bool(SAVE_RESULT_FIGURE),
                             show_figure=SHOW_FIGURE),
    )


def main() -> None:
    run_case(define_case())


if __name__ == "__main__":
    main()
