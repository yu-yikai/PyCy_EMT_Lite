"""同步Buck：从低电压启动到15V，再观察2A脉冲负荷扰动。

30V直流源经互补上下管和1mH电感供电，输出22uF电容并联3.75ohm负荷。
测量滤波、PI和外部限幅均复用现有控制积木；没有积分抗饱和。
门极按50ns网格采样，控制在电气求解后更新，作用于下一步。
本例的双向受控开关仅覆盖已核定的体二极管不活动工况。
"""

from collections.abc import Mapping
from dataclasses import dataclass

from pycy_emt_lite import (
    Capacitor,
    Circuit,
    CurrentSource,
    Inductor,
    Resistor,
    SimulationConfig,
    VoltageSource,
)
from pycy_emt_lite.analysis import peak_abs
from pycy_emt_lite.cases import CaseDefinition, OutputOptions, PlotSpec, run_case
from pycy_emt_lite.components import IdealSwitch
from pycy_emt_lite.controls import (
    FirstOrderLowPass,
    Limiter,
    PIController,
    carrier_compare,
    triangular_carrier,
)
from pycy_emt_lite.events import SimulationEvent
from pycy_emt_lite.events.base import EventRecord
from pycy_emt_lite.io.results import SimulationResult

SAVE_RESULT_DATA = 0
SAVE_RESULT_FIGURE = 0
SHOW_FIGURE = True

DC_VOLTAGE = 30.0
VOLTAGE_REFERENCE = 15.0
INDUCTANCE = 1e-3               # H
INDUCTOR_PARALLEL_RESISTANCE = 10000.0
CAPACITANCE = 22e-6             # F
LOAD_RESISTANCE = 3.75
SWITCH_ON_RESISTANCE = 0.1
SNUBBER_RESISTANCE = 100000.0   # 每管并联一个电阻，保留关断时的小电流路径
PULSE_CURRENT = 2.0            # A，2.5–5ms及7.5–10ms额外吸收
MEASUREMENT_LAG = 1e-6         # s
PROPORTIONAL_GAIN = 0.5
INTEGRAL_GAIN = 200.0
DUTY_MIN, DUTY_MAX = 0.01, 0.95
SWITCHING_FREQUENCY = 50000.0
CARRIER_TIME_SHIFT = 5e-6
TIME_STEP = 50e-9
STOP_TIME = 10e-3


def initial_storage() -> tuple[float, float]:
    """两管初始关断：电感视为直流短路，电容开路，按snubber分压初始化。"""
    lower_resistance = 1 / (1 / SNUBBER_RESISTANCE + 1 / LOAD_RESISTANCE)
    voltage = DC_VOLTAGE * lower_resistance / (SNUBBER_RESISTANCE + lower_resistance)
    return voltage / LOAD_RESISTANCE, voltage


class VoltageControl:
    """把三个已有积木接成电压环；限幅在PI外，保留饱和时积分。"""

    def __init__(self) -> None:
        self.filter = FirstOrderLowPass(MEASUREMENT_LAG)
        self.pi = PIController(PROPORTIONAL_GAIN, INTEGRAL_GAIN)
        self.limiter = Limiter(DUTY_MIN, DUTY_MAX)
        self.duty = DUTY_MIN
        self.previous_time = 0.0

    def upper_closed(self, time: float) -> bool:
        # 载波用当前求解时刻；duty是前一次回调计算的保持值。
        return time > 0 and bool(carrier_compare(
            2 * self.duty - 1, triangular_carrier(time + CARRIER_TIME_SHIFT, SWITCHING_FREQUENCY),
        ))

    def lower_closed(self, time: float) -> bool:
        return time > 0 and not self.upper_closed(time)

    def update(self, row: Mapping[str, float]) -> dict[str, float]:
        """先观察已解出的电压，再推进滤波和PI；t0不积分。"""
        time = row["time"]
        if abs(row["i:L"]) > 7.99 or abs(row["v:out"]) > 40:
            raise ValueError("超出本例已核定的体二极管不活动域；此双向开关等效不再适用。")
        if time > self.previous_time:
            dt = time - self.previous_time
            error = self.filter.step(VOLTAGE_REFERENCE - row["v:out"], dt)
            self.duty = self.limiter.step(self.pi.step(error, dt), dt)
        self.previous_time = time
        return {"duty": self.duty, "filtered_error": self.filter.state, "integral_term": self.pi.integrator}


@dataclass(frozen=True, slots=True)
class LoadCurrentStep(SimulationEvent):
    """本例负荷事件：旧电流积分到边沿，再切新电流并保持L/C状态。"""

    value: float = 0.0

    def source(self, circuit: Circuit) -> CurrentSource:
        for component in circuit.components:
            if component.name == self.target and isinstance(component, CurrentSource):
                return component
        raise ValueError(f"负荷事件目标{self.target!r}必须为本例CurrentSource。")

    def validate(self, circuit: Circuit) -> None:
        self.source(circuit)

    def apply(self, circuit: Circuit, applied_time: float) -> EventRecord:
        source = self.source(circuit)
        before = source.current
        if callable(before):
            raise ValueError("负荷事件使用标量电流，由事件切换，不与时间函数混用。")
        before = float(before)
        source.current = self.value
        return {"time": applied_time, "scheduled_time": self.time, "type": "load_current_step",
                "target": self.target, "before": before, "after": self.value, "name": self.name}


def create_components(control: VoltageControl) -> tuple:
    current, voltage = initial_storage()
    return (
        VoltageSource("Vdc", "dc", "0", DC_VOLTAGE),
        IdealSwitch("Supper", "dc", "mid", control.upper_closed,
                    closed_resistance=SWITCH_ON_RESISTANCE, open_conductance=0),
        IdealSwitch("Slower", "mid", "0", control.lower_closed,
                    closed_resistance=SWITCH_ON_RESISTANCE, open_conductance=0),
        Resistor("Rupper", "dc", "mid", SNUBBER_RESISTANCE),
        Resistor("Rlower", "mid", "0", SNUBBER_RESISTANCE),
        Inductor("L", "mid", "out", INDUCTANCE, initial_current=current),
        Resistor("Rparallel", "mid", "out", INDUCTOR_PARALLEL_RESISTANCE),
        Capacitor("C", "out", "0", CAPACITANCE, initial_voltage=voltage),
        Resistor("Rload", "out", "0", LOAD_RESISTANCE),
        CurrentSource("Ipulse", "out", "0", 0.0),
    )


def print_summary(result: SimulationResult) -> None:
    print(f"同步Buck：{DC_VOLTAGE:g}V降至{VOLTAGE_REFERENCE:g}V；步长{result.time_step * 1e9:g}ns。")
    print("负荷在2.5/5/7.5/10ms切换；无抗饱和，观察启动过冲和负荷扰动恢复。")
    print(f"最终输出：{result.series('v:out')[-1]:.6f}V；"
          f"电感电流峰值：{peak_abs(result, 'i:L'):.6f}A。")


def define_case() -> CaseDefinition:
    control = VoltageControl()
    events = tuple(LoadCurrentStep(time, "Ipulse", value=value) for time, value in (
        (0.0025, PULSE_CURRENT), (0.005, 0.0), (0.0075, PULSE_CURRENT), (0.01, 0.0),
    ))
    return CaseDefinition(
        name="synchronous_buck", components=create_components(control),
        config=SimulationConfig(TIME_STEP, STOP_TIME, method="trapezoidal",
                                linear_solver_mode="reuse", event_time_policy="require_aligned"),
        events=events, on_step=control.update,
        plots=(PlotSpec(("v:out",), "voltage.png", title="Buck output voltage (V)"),
               PlotSpec(("i:L",), "current.png", title="Inductor current: mid to output (A)"),
               PlotSpec(("duty",), "duty.png", title="Voltage-controller duty command")),
        output=OutputOptions(save_data=bool(SAVE_RESULT_DATA), save_figure=bool(SAVE_RESULT_FIGURE),
                             show_figure=SHOW_FIGURE), summary=print_summary,
    )


def main() -> None:
    run_case(define_case())


if __name__ == "__main__":
    main()
