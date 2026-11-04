"""两级RC的负载耦合：后一级会改变前一级的充放电响应。

从仓库根目录运行：uv run python examples/19_cascaded_rc.py

电路（0为地）：src -- R1 -- n1 -- R2 -- n2
                           |             |
                          C1            C2
                           |             |
                           0             0

R1电流从src流向n1，R2从n1流向n2；电容电流从节点流向地。
5V方波在1/6/11/16ms升/降/升/降。显式事件保持电容电压连续，
源电压与电阻电流允许跳变。n2起初比n1上升慢；撤去电源后，
C2可能继续短时充电，因为此时n1仍高于n2。

学习点：不能把两个独立RC传递函数单向串接来代替这个有负载作用的网络。
练习：增大C2会延长后级响应，也改变n1曲线；增大R2会减弱负载耦合。
参数修改后，原有商业参考验收不再适用。默认模型为理想R/C与外部电压源，
不含电容ESR；外部参考及误差说明在validation/cases/cascaded_rc/。
"""

import math
from dataclasses import dataclass

import numpy as np

from pycy_emt_lite import Capacitor, Circuit, Resistor, SimulationConfig, VoltageSource
from pycy_emt_lite.cases import CaseDefinition, OutputOptions, PlotSpec, run_case
from pycy_emt_lite.events import SimulationEvent
from pycy_emt_lite.io.results import SimulationResult

# 1. Parameters (SI units)
SAVE_RESULT_DATA = 0
SAVE_RESULT_FIGURE = 0
SHOW_FIGURE = True
RESISTANCE_1 = 10.0       # ohm
RESISTANCE_2 = 10.0       # ohm
CAPACITANCE_1 = 100e-6    # F
CAPACITANCE_2 = 100e-6    # F
SOURCE_AMPLITUDE = 5.0   # V
PULSE_PERIOD = 0.01      # s
PULSE_DELAY = 0.001      # s
PULSE_HIGH_TIME = 0.005  # s
TIME_STEP = 2e-6         # s
STOP_TIME = 0.02         # s


@dataclass(frozen=True)
class SourceLevelEvent(SimulationEvent):
    """本例的电压源阶跃；复用既有事件左右侧求解，不修改积分公式。"""

    level: float = 0.0

    def validate(self, circuit: Circuit) -> None:
        sources = [item for item in circuit.components if item.name == self.target]
        if len(sources) != 1 or not isinstance(sources[0], VoltageSource):
            raise ValueError("电压阶跃目标必须是本例中的VoltageSource。")
        if not math.isfinite(self.level) or callable(sources[0].voltage):
            raise ValueError("本例事件需要有限电压和常值电压源。")

    def apply(self, circuit: Circuit, applied_time: float) -> dict[str, float | str]:
        source = next(item for item in circuit.components if item.name == self.target)
        assert isinstance(source, VoltageSource) and not callable(source.voltage)
        before = source.voltage
        source.voltage = self.level
        return {"time": applied_time, "scheduled_time": self.time, "type": "source_level",
                "target": self.target, "before": before, "after": self.level, "name": self.name}


def print_summary(result: SimulationResult) -> None:
    """5 ms高电平不足以达到5V终值；撤去电源后观察级间能量转移。"""
    print(f"后级电容电压峰值：{np.max(result.series('v:n2')):.6f} V")
    print(f"仿真终点后级电压：{result.series('v:n2')[-1]:.6f} V（仍在放电）")
    print("观察n1/n2及R2电流：源下降后，后级可能继续短时充电。")


def define_case() -> CaseDefinition:
    """2. Build circuit; 3. Define source events, simulation and plots."""
    config = SimulationConfig(TIME_STEP, STOP_TIME, method="trapezoidal")
    if not math.isfinite(PULSE_PERIOD) or PULSE_PERIOD <= 0:
        raise ValueError("PULSE_PERIOD必须为有限正秒数。")
    if not math.isfinite(PULSE_HIGH_TIME) or not 0 < PULSE_HIGH_TIME < PULSE_PERIOD:
        raise ValueError("PULSE_HIGH_TIME必须在0与PULSE_PERIOD之间。")
    if not math.isfinite(PULSE_DELAY) or PULSE_DELAY < 0:
        raise ValueError("PULSE_DELAY必须为有限非负秒数。")
    if not math.isfinite(SOURCE_AMPLITUDE):
        raise ValueError("SOURCE_AMPLITUDE必须有限。")
    if STOP_TIME / PULSE_PERIOD > 100_000:
        raise ValueError("本教学例最多支持100000个脉冲周期；请减少时长或增大周期。")
    components = (
        VoltageSource("V1", "src", "0", 0.0),
        Resistor("R1", "src", "n1", RESISTANCE_1),
        Resistor("R2", "n1", "n2", RESISTANCE_2),
        Capacitor("C1", "n1", "0", CAPACITANCE_1, initial_voltage=0.0),
        Capacitor("C2", "n2", "0", CAPACITANCE_2, initial_voltage=0.0),
    )
    events = []
    cycle = 0
    while PULSE_DELAY + cycle * PULSE_PERIOD <= STOP_TIME:
        rising = PULSE_DELAY + cycle * PULSE_PERIOD
        events.append(SourceLevelEvent(rising, "V1", "pulse_on", SOURCE_AMPLITUDE))
        falling = rising + PULSE_HIGH_TIME
        if falling <= STOP_TIME:
            events.append(SourceLevelEvent(falling, "V1", "pulse_off", 0.0))
        cycle += 1
    return CaseDefinition(
        name="cascaded_rc", components=components,
        config=config,
        events=tuple(events),
        plots=(
            PlotSpec(("v:src", "v:n1", "v:n2"), "voltages.png", title="Cascaded RC: voltages (V)"),
            PlotSpec(("i:R1", "i:R2"), "currents.png", title="Cascaded RC: currents (A)"),
        ),
        output=OutputOptions(save_data=bool(SAVE_RESULT_DATA), save_figure=bool(SAVE_RESULT_FIGURE), show_figure=SHOW_FIGURE),
        summary=print_summary,
    )


def main() -> None:
    """4. Run simulation; 5. Summarize; 6. Plot only PyCy waveforms."""
    run_case(define_case())


if __name__ == "__main__":
    main()
