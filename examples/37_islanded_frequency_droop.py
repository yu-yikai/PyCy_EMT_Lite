"""孤网接入第二组负荷后，P–f 下垂让频率随有功功率上升而降低。"""

import math
from collections.abc import Mapping

from pycy_emt_lite import (
    IdealSwitch,
    Inductor,
    Resistor,
    SimulationConfig,
    VoltageSource,
)
from pycy_emt_lite.cases import CaseDefinition, PlotSpec, run_case
from pycy_emt_lite.components import Component
from pycy_emt_lite.controls import FirstOrderLowPass

TIME_STEP = 5e-6
FINE_TIME_STEP = 2.5e-6
STOP_TIME = 0.4
RAMP_TIME = 0.02
LOAD_STEP_TIME = 0.2
PHASES = "abc"
PHASE_SHIFTS = (0.0, -math.tau / 3, math.tau / 3)
SOURCE_PEAK_V = 120.0 * math.sqrt(2.0)
POWER_REFERENCE_W = 360.0
NOMINAL_FREQUENCY_HZ = 60.0
DROOP_HZ_PER_W = 0.001
LOAD_RESISTANCE_OHM = 120.0
OPEN_RESISTANCE_OHM = 1e9


def define_case(*, time_step: float = TIME_STEP, stop_time: float = STOP_TIME) -> CaseDefinition:
    """从零相角和零馈线电流启动，支持 5 µs 和 2.5 µs 两档。"""
    if time_step not in (TIME_STEP, FINE_TIME_STEP):
        raise ValueError("本例的电气步长应为 5 µs 或 2.5 µs。")
    ramp_end_tick = round(RAMP_TIME / time_step)
    load_step_tick = round(LOAD_STEP_TIME / time_step)
    power_filter = FirstOrderLowPass(0.02, POWER_REFERENCE_W)
    angle = 0.0

    def source_peak(time: float) -> float:
        fraction = min(round(time / time_step) / ramp_end_tick, 1.0)
        return SOURCE_PEAK_V * (1 - math.cos(math.pi * fraction)) / 2

    def added_load_closed(time: float) -> bool:
        return round(time / time_step) >= load_step_tick

    components: list[Component] = []
    for phase, shift in zip(PHASES, PHASE_SHIFTS, strict=True):
        source, feeder, pcc = f"src_{phase}", f"feeder_{phase}", f"pcc_{phase}"
        # 每相经 R–L 馈线到 PCC，两个负荷支路分别接到公共中性点 0。
        components.extend((
            VoltageSource(f"Emf_{phase}", source, "0",
                          lambda time, offset=shift: source_peak(time) * math.sin(angle + offset), derivative=0.0),
            Resistor(f"FeederR_{phase}", source, feeder, 0.1),
            Inductor(f"FeederL_{phase}", feeder, pcc, 0.003, initial_current=0.0),
            Resistor(f"Base_{phase}", pcc, "0", LOAD_RESISTANCE_OHM),
            # 用开关的两档电阻表示负荷支路，导通时整条支路为 120 Ω。
            IdealSwitch(f"Added_{phase}", pcc, "0", added_load_closed,
                        closed_resistance=LOAD_RESISTANCE_OHM, open_conductance=1 / OPEN_RESISTANCE_OHM),
        ))

    def observe(row: Mapping[str, float]) -> Mapping[str, float]:
        nonlocal angle
        time = row["time"]
        # 馈线电流以流向 PCC 为正，三相电压与电流的乘积之和就是送到负荷的有功。
        power = sum(row[f"v:pcc_{phase}"] * row[f"i:FeederL_{phase}"] for phase in PHASES)
        if time == 0.0:
            angle = 0.0
            power_filter.reset(POWER_REFERENCE_W)
        else:
            power_filter.step(power, time_step)
        frequency = NOMINAL_FREQUENCY_HZ - DROOP_HZ_PER_W * (power_filter.state - POWER_REFERENCE_W)
        load_on = row["state:Added_a"]
        observed = {
            "source_peak_v": source_peak(time),
            "source_phase_rad": angle,
            "frequency_hz": frequency,
            "pcc_power_w": power,
            "filtered_power_w": power_filter.state,
            "added_resistance_ohm": LOAD_RESISTANCE_OHM if load_on else OPEN_RESISTANCE_OHM,
            "added_load_on": load_on,
        }
        # 当前拍已用过这个相角，求解后再用当前频率推进到下一拍。
        angle += math.tau * time_step * frequency
        return observed

    return CaseDefinition(
        name="islanded_frequency_droop",
        components=tuple(components),
        config=SimulationConfig(time_step, stop_time, method="trapezoidal"),
        plots=(
            PlotSpec(("pcc_power_w", "filtered_power_w"), "pcc_power.png", title="PCC power (W)"),
            PlotSpec(("frequency_hz",), "frequency.png", title="Source frequency (Hz)"),
            PlotSpec(("v:pcc_a", "v:pcc_b", "v:pcc_c"), "pcc_voltage.png", kind="three_phase",
                     title="PCC voltage (V)"),
        ),
        on_step=observe,
    )


if __name__ == "__main__":
    run_case(define_case())
