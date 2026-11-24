"""两台构网源接入同一孤网，观察不同 P–f 下垂斜率如何分担新增负荷。"""

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
STOP_TIME = 0.6
RAMP_TIME = 0.02
LOAD_STEP_TIME = 0.3
PHASES = "abc"
PHASE_SHIFTS = (0.0, -math.tau / 3, math.tau / 3)
SOURCE_PEAK_V = 120.0 * math.sqrt(2.0)
NOMINAL_FREQUENCY_HZ = 60.0
LOAD_RESISTANCE_OHM = 120.0
OPEN_RESISTANCE_OHM = 1e9
STATION_DROOP = {"a": (240.0, 0.001), "b": (120.0, 0.002)}  # 功率基准 W，下垂斜率 Hz/W


def define_case(*, time_step: float = TIME_STEP, stop_time: float = STOP_TIME) -> CaseDefinition:
    """搭建两台独立控制的构网源，支持 5 µs 和 2.5 µs 两档。"""
    if time_step not in (TIME_STEP, FINE_TIME_STEP):
        raise ValueError("本例的电气步长应为 5 µs 或 2.5 µs。")
    ramp_end_tick = round(RAMP_TIME / time_step)
    load_step_tick = round(LOAD_STEP_TIME / time_step)
    angles = dict.fromkeys(STATION_DROOP, 0.0)
    power_filters = {site: FirstOrderLowPass(0.02, reference) for site, (reference, _) in STATION_DROOP.items()}

    def source_peak(time: float) -> float:
        fraction = min(round(time / time_step) / ramp_end_tick, 1.0)
        return SOURCE_PEAK_V * (1.0 - math.cos(math.pi * fraction)) / 2.0

    def added_load_closed(time: float) -> bool:
        return round(time / time_step) >= load_step_tick

    components: list[Component] = []
    # 两台源各经一组三相 R–L 馈线到同一个 PCC，源与负荷共用接地中性点。
    for site in STATION_DROOP:
        for phase, shift in zip(PHASES, PHASE_SHIFTS, strict=True):
            source, middle, pcc = f"src_{site}_{phase}", f"mid_{site}_{phase}", f"pcc_{phase}"
            components.extend((
                VoltageSource(f"Emf_{site}_{phase}", source, "0",
                              lambda time, station=site, offset=shift: source_peak(time) * math.sin(angles[station] + offset),
                              derivative=0.0),
                Resistor(f"FeederR_{site}_{phase}", source, middle, 0.1),
                Inductor(f"FeederL_{site}_{phase}", middle, pcc, 0.003, initial_current=0.0),
            ))
    for phase in PHASES:
        pcc = f"pcc_{phase}"
        components.extend((
            Resistor(f"Base_{phase}", pcc, "0", LOAD_RESISTANCE_OHM),
            IdealSwitch(f"Added_{phase}", pcc, "0", added_load_closed,
                        closed_resistance=LOAD_RESISTANCE_OHM, open_conductance=1 / OPEN_RESISTANCE_OHM),
        ))

    def observe(row: Mapping[str, float]) -> Mapping[str, float]:
        time = row["time"]
        measured = {}
        for site, (reference, droop) in STATION_DROOP.items():
            # 两站使用同一组 PCC 电压，各自乘以流向 PCC 的馈线电流。
            power = sum(row[f"v:pcc_{phase}"] * row[f"i:FeederL_{site}_{phase}"] for phase in PHASES)
            power_filter = power_filters[site]
            if time == 0.0:
                angles[site] = 0.0
                power_filter.reset(reference)
            else:
                power_filter.step(power, time_step)
            measured[f"phase_{site}_rad"] = angles[site]
            measured[f"power_{site}_w"] = power
            measured[f"filtered_{site}_w"] = power_filter.state
            measured[f"frequency_{site}_hz"] = NOMINAL_FREQUENCY_HZ - droop * (power_filter.state - reference)

        measured["phase_difference_mrad"] = 1000.0 * (angles["a"] - angles["b"])
        # 两台源都读取完当拍结果后，再分别用各自的频率推进下一拍的相角。
        for site in STATION_DROOP:
            angles[site] += math.tau * time_step * measured[f"frequency_{site}_hz"]
        load_on = row["state:Added_a"]
        return measured | {"peak_v": source_peak(time), "load_on": load_on,
                           "load_r": LOAD_RESISTANCE_OHM if load_on else OPEN_RESISTANCE_OHM}

    return CaseDefinition(
        name="dual_grid_forming_power_sharing",
        components=tuple(components),
        config=SimulationConfig(time_step, stop_time, method="trapezoidal", linear_solver_mode="reuse"),
        plots=(
            PlotSpec(("power_a_w", "power_b_w"), "pcc_power.png", title="PCC power by source (W)"),
            PlotSpec(("frequency_a_hz", "frequency_b_hz"), "frequency.png", title="Source frequency (Hz)"),
            PlotSpec(("phase_difference_mrad",), "phase_difference.png", title="Phase A minus B (mrad)"),
        ),
        on_step=observe,
    )


if __name__ == "__main__":
    run_case(define_case())
