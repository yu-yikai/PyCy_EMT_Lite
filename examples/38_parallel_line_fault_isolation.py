"""并联线路发生故障后，观察双端隔离、健康线路保供和重合恢复。"""

from collections.abc import Mapping

from pycy_emt_lite import (
    IdealSwitch,
    SimulationConfig,
    ThreePhaseLine,
    ThreePhaseLoad,
    ThreePhaseSource,
)
from pycy_emt_lite.cases import CaseDefinition, PlotSpec, run_case
from pycy_emt_lite.components import Component

TIME_STEP = 50e-6
FINE_TIME_STEP = 25e-6
STOP_TIME = 0.35
SOURCE_RMS_V = 120.0
OPEN_RESISTANCE_OHM = 1e9
PHASES = "abc"


def _observe(row: Mapping[str, float]) -> Mapping[str, float]:
    voltages = {f"v:{bus}_{phase}": row[f"v:{bus}:{phase}"]
                for bus in ("src", "recv", "fault") for phase in PHASES}

    power = sum(row[f"v:recv:{phase}"] * row[f"i:Load:{phase}"] for phase in PHASES)

    def signed_rms(branch: str) -> float:
        # 平衡纯电阻网络中，将三相电流投影到源电压方向，得到带方向的每相有效值。
        return sum(row[f"v:src:{phase}"] * row[f"i:{branch}_{phase}"] for phase in PHASES) / (3 * SOURCE_RMS_V)

    return voltages | {"receiving_power_w": power, "sf_signed_rms_a": signed_rms("SF"), "rf_signed_rms_a": signed_rms("RF")}


def define_case(*, time_step: float = TIME_STEP, stop_time: float = STOP_TIME) -> CaseDefinition:
    """搭建共地三母线模型，支持 50 µs 和 25 µs 两档。"""
    if time_step not in (TIME_STEP, FINE_TIME_STEP):
        raise ValueError("本例的电气步长应为 50 µs 或 25 µs。")

    # 依次投入故障、断开送端和受端、清除故障，最后合上两端。
    fault_tick, send_open_tick, receive_open_tick, clear_tick, reclose_tick = (
        round(time / time_step) for time in (0.10, 0.15, 0.20, 0.25, 0.30)
    )

    def send_end_closed(time: float) -> bool:
        return not send_open_tick <= round(time / time_step) < reclose_tick

    def receive_end_closed(time: float) -> bool:
        return not receive_open_tick <= round(time / time_step) < reclose_tick

    def fault_on(time: float) -> bool:
        return fault_tick <= round(time / time_step) < clear_tick

    components: list[Component] = [
        ThreePhaseSource("Source", "src", phase_rms=SOURCE_RMS_V, frequency=60.0),
        ThreePhaseLine("Healthy", "src", "recv", resistance=2.0),
        ThreePhaseLoad("Load", "recv", resistance=20.0),
        # 两端都断开时，故障点仍通过高阻接地。
        ThreePhaseLoad("Reference", "fault", resistance=10_000.0),
    ]
    for phase in PHASES:
        source, receiving, fault = f"src:{phase}", f"recv:{phase}", f"fault:{phase}"
        # SF 和 RF 均以流向故障点为正。开关按支路的接通电阻和断开电导求解。
        for name, start, end, closed, resistance in (
            ("SF", source, fault, send_end_closed, 2.0),
            ("RF", receiving, fault, receive_end_closed, 2.0),
            ("Fault", fault, "0", fault_on, 0.2),
        ):
            components.append(IdealSwitch(f"{name}_{phase}", start, end, closed,
                                          closed_resistance=resistance, open_conductance=1 / OPEN_RESISTANCE_OHM))

    return CaseDefinition(
        name="parallel_line_fault_isolation",
        components=tuple(components),
        config=SimulationConfig(time_step, stop_time, method="trapezoidal"),
        plots=(
            PlotSpec(("receiving_power_w",), "receiving_power.png", title="Receiving load power (W)"),
            PlotSpec(("sf_signed_rms_a", "rf_signed_rms_a"), "fault_path_currents.png", title="Signed fault-path currents (A RMS)"),
        ),
        on_step=_observe,
    )


if __name__ == "__main__":
    run_case(define_case())
