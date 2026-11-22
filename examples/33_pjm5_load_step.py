"""在 PJM5 五母线网中投入负荷，观察母线电压和两条进线的功率分担。

线路数据源自 IEEE PES PGLib-OPF v23.07 的 PJM5（CC BY 4.0）。
本例在 4 号母线接理想三相源，将基线负荷折算成并联电阻和电感。
"""

import math
from collections.abc import Mapping

from pycy_emt_lite import (
    IdealSwitch,
    Inductor,
    Resistor,
    SimulationConfig,
    VoltageSource,
)
from pycy_emt_lite.cases import CaseDefinition, OutputOptions, PlotSpec, run_case
from pycy_emt_lite.components import ThreePhasePiLine
from pycy_emt_lite.components.base import Component
from pycy_emt_lite.components.three_phase import PhaseName, phase_node
from pycy_emt_lite.io.results import SimulationResult

SAVE_RESULT_DATA = 0
SAVE_RESULT_FIGURE = 0
SHOW_FIGURE = True

TIME_STEP = 5e-6
STOP_TIME = 0.600
SOURCE_RAMP_TIME = 0.050
LOAD_STEP_TIME = 0.300
STEP_OPEN_OHM = 1e9
STEP_CLOSED_OHM = 10580.0
PHASE_OFFSETS: dict[PhaseName, float] = {"a": 0.0, "b": -2 * math.pi / 3, "c": 2 * math.pi / 3}
SOURCE_PEAK_V = math.sqrt(2 / 3) * 230_000.0  # 相电压峰值，230 kV 是线电压有效值。
ANGULAR_FREQUENCY = math.tau * 60.0

# 始端、末端、每相串联电阻 (Ω)、电感 (H)、单端并联电容 (F)。
LINES = (
    (1, 2, 1.48649, 0.039430371892778586, 1.78510270134577e-08),
    (1, 4, 1.60816, 0.042657768880443744, 1.6497156987156134e-08),
    (1, 5, 0.33856, 0.008980582922198683, 7.837403152256851e-08),
    (2, 3, 0.57132, 0.015154733681210278, 4.643272756871301e-08),
    (3, 4, 1.57113, 0.04167551762332826, 1.6898303661615858e-08),
    (4, 5, 1.57113, 0.04167551762332826, 1.6898303661615858e-08),
)

# 母线号、每相并联电阻 (Ω)、每相并联电感 (H)。
BASE_LOADS = (
    (2, 1763.3333333333335, 14.229957221311672),
    (3, 1763.3333333333335, 14.229957221311672),
    (4, 1322.5000000000002, 10.673279695698973),
)


def _grid_source(phase: PhaseName, angle: float) -> VoltageSource:
    def voltage(time: float) -> float:
        envelope = min(time / SOURCE_RAMP_TIME, 1.0)
        return SOURCE_PEAK_V * envelope * math.sin(ANGULAR_FREQUENCY * time + angle)

    # 理想电源与线路端电容并联，一致初值求解需要零时刻的右导数。
    initial_slope = SOURCE_PEAK_V * math.sin(angle) / SOURCE_RAMP_TIME
    return VoltageSource(f"Vsource_{phase}", phase_node("b4", phase), "0", voltage, derivative=initial_slope)


def _measure_load_sharing(row: Mapping[str, float]) -> Mapping[str, float]:
    voltage_square = import_from_1 = import_from_3 = added_power = 0.0
    for phase in PHASE_OFFSETS:
        voltage = row[f"v:{phase_node('b2', phase)}"]
        # 到达 2 号母线的电流要扣掉该端 π 线路的电容电流。
        from_1 = row[f"i:line_12:series:{phase}"] - row[f"i:line_12:to_cap:{phase}"]
        from_3 = -row[f"i:line_23:series:{phase}"] - row[f"i:line_23:from_cap:{phase}"]
        voltage_square += voltage**2
        import_from_1 += voltage * from_1
        import_from_3 += voltage * from_3
        added_power += voltage * row[f"i:Rstep_{phase}"]
    return {
        "v_bus2_rms_v": math.sqrt(voltage_square / 3),
        "p_import_12_w": import_from_1,
        "p_import_32_w": import_from_3,
        "p_step_w": added_power,
        "step_resistance_ohm": STEP_CLOSED_OHM if row["state:Rstep_a"] else STEP_OPEN_OHM,
    }


def _print_summary(result: SimulationResult) -> None:
    last = result.rows[-1]
    print(f"末点 2 号母线相电压有效值为 {last['v_bus2_rms_v'] / 1000:.3f} kV，"
          f"新增支路功率为 {last['p_step_w'] / 1e6:.3f} MW。")


def define_case(*, time_step: float = TIME_STEP, stop_time: float = STOP_TIME) -> CaseDefinition:
    """五母线、六条 π 线路及 2 号母线的平衡负荷投入。"""
    if time_step not in (TIME_STEP, 2.5e-6):
        raise ValueError("本例支持 5 µs 或 2.5 µs 的电气步长。")
    load_tick = round(LOAD_STEP_TIME / time_step)
    load_time = math.nextafter(load_tick * time_step, -math.inf)

    def step_closed(time: float) -> bool:
        # 0.300 s 当行使用投入后的阻值，参与该步梯形积分。
        return time >= load_time

    sources = tuple(_grid_source(phase, shift) for phase, shift in PHASE_OFFSETS.items())
    lines = tuple(
        ThreePhasePiLine(f"line_{start}{end}", f"b{start}", f"b{end}", resistance, inductance, 2 * end_cap)
        for start, end, resistance, inductance, end_cap in LINES
    )
    loads: list[Component] = []
    for bus, resistance, inductance in BASE_LOADS:
        for phase in PHASE_OFFSETS:
            node = phase_node(f"b{bus}", phase)
            loads.extend((
                Resistor(f"Rload_{bus}_{phase}", node, "0", resistance),
                Inductor(f"Lload_{bus}_{phase}", node, "0", inductance, initial_current=0.0),
            ))
    # 两档开关阻值直接表示新增负荷支路的等效电阻。
    step = tuple(
        IdealSwitch(f"Rstep_{phase}", phase_node("b2", phase), "0", step_closed,
                    closed_resistance=STEP_CLOSED_OHM, open_conductance=1.0 / STEP_OPEN_OHM)
        for phase in PHASE_OFFSETS
    )
    return CaseDefinition(
        name="pjm5_load_step",
        components=(*sources, *lines, *loads, *step),
        config=SimulationConfig(time_step, stop_time, method="trapezoidal", linear_solver_mode="reuse",
                                event_time_policy="require_aligned"),
        plots=(
            PlotSpec(("v_bus2_rms_v",), "bus2_voltage.png", title="Bus 2 phase voltage (V RMS)"),
            PlotSpec(("p_import_12_w", "p_import_32_w", "p_step_w"), "load_sharing.png", title="Power at bus 2 (W)"),
        ),
        output=OutputOptions(save_data=bool(SAVE_RESULT_DATA), save_figure=bool(SAVE_RESULT_FIGURE),
                             show_figure=SHOW_FIGURE),
        summary=_print_summary,
        on_step=_measure_load_sharing,
    )


def main() -> None:
    run_case(define_case())


if __name__ == "__main__":
    main()
