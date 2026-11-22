"""并网 VSC 闭环：先阶跃 d 轴参考，再观察 q 轴阶跃及两轴电流。

电流以电网流向变流器为正。借用电网的已知相角将三相量变换到 dq 坐标，
使用两个 PI、网压前馈和电感交叉项。桥侧电压升高会减小正向电流，
因此 PI 输出从桥侧电压指令中减去。

每 100 µs 在电气求解后采样。新指令从下一 5 µs 门极拍生效，
2.5 µs 电气网格的中点也保持同一门极状态。
"""

import math
from collections.abc import Callable, Mapping

from pycy_emt_lite import SimulationConfig
from pycy_emt_lite.cases import CaseDefinition, OutputOptions, PlotSpec, run_case
from pycy_emt_lite.controls import (
    PIController,
    abc_to_dq,
    carrier_compare,
    dq_to_abc,
    triangular_carrier,
)
from pycy_emt_lite.converters import _grid_vsc
from pycy_emt_lite.io.results import SimulationResult

SAVE_RESULT_DATA = 0
SAVE_RESULT_FIGURE = 0
SHOW_FIGURE = True

TIME_STEP = _grid_vsc.TIME_STEP
STOP_TIME = 0.2
CONTROL_PERIOD = 100e-6
GATE_PERIOD = 5e-6
SWITCHING_FREQUENCY = 1000.0
CARRIER_TIME_SHIFT = -0.0005  # 首拍载波为 +1
CURRENT_BANDWIDTH = 100.0  # Hz
HALF_DC_VOLTAGE = _grid_vsc.DC_VOLTAGE / 2
VOLTAGE_LIMIT = 0.95 * HALF_DC_VOLTAGE
GRID_ANGULAR_FREQUENCY = 2 * math.pi * _grid_vsc.FREQUENCY
CROSS_COUPLING = GRID_ANGULAR_FREQUENCY * _grid_vsc.INDUCTANCE
PHASES = tuple(_grid_vsc.PHASE_SHIFTS)


def print_summary(result: SimulationResult) -> None:
    print(f"并网 VSC 闭环。电气步长 {result.time_step * 1e6:g} 微秒，控制周期 100 微秒，门极周期 5 微秒。")
    print(f"交流电流以电网流向变流器为正。dq 电压指令限幅 {VOLTAGE_LIMIT:g} V。")
    print(f"末点电流参考为 d = {result.series('id_ref')[-1]:g} A，q = {result.series('iq_ref')[-1]:g} A。")


def define_case(
    *, scenario: str = "main", time_step: float = TIME_STEP, stop_time: float = STOP_TIME,
) -> CaseDefinition:
    """每次建立独立的 PI 和门极。main 在 40/80 ms 依次阶跃 d/q 轴，d_only 只阶跃 d 轴。"""
    if scenario not in ("main", "d_only"):
        raise ValueError("scenario 必须为 main 或 d_only。")
    time_step = _grid_vsc.checked_time_step(time_step)
    steps_per_gate = round(GATE_PERIOD / time_step)
    steps_per_sample = round(CONTROL_PERIOD / time_step)
    d_step = round(0.04 / time_step)
    q_step = round(0.08 / time_step)

    bandwidth = 2 * math.pi * CURRENT_BANDWIDTH
    kp = _grid_vsc.INDUCTANCE * bandwidth
    ki = _grid_vsc.RESISTANCE * bandwidth
    d_pi = PIController(kp, ki)
    q_pi = PIController(kp, ki)
    previous = pending = (0.0, 0.0, 0.0)
    last_sample_tick = 0
    id_ref = iq_ref = 0.0
    saturated = False

    def applied_reference(gate_tick: int) -> tuple[float, float, float]:
        # 在采样所在的门极拍内，仍然使用刚才求解所用的指令。
        return pending if gate_tick > last_sample_tick else previous

    def carrier_at(gate_tick: int) -> float:
        return triangular_carrier(gate_tick * GATE_PERIOD + CARRIER_TIME_SHIFT, SWITCHING_FREQUENCY)

    def gate_pair(phase: str) -> tuple[Callable[[float], bool], Callable[[float], bool]]:
        phase_index = PHASES.index(phase)

        def upper(time: float) -> bool:
            gate_tick = _grid_vsc.electrical_index(time, time_step) // steps_per_gate
            reference = applied_reference(gate_tick)[phase_index]
            return bool(carrier_compare(reference, carrier_at(gate_tick)))

        def lower(time: float) -> bool:
            return not upper(time)

        return upper, lower

    def observe(row: Mapping[str, float]) -> Mapping[str, float]:
        nonlocal previous, pending, last_sample_tick, id_ref, iq_ref, saturated
        time = row["time"]
        index = _grid_vsc.electrical_index(time, time_step)
        gate_tick = index // steps_per_gate
        applied = applied_reference(gate_tick)
        sample_update = index > 0 and index % steps_per_sample == 0

        theta = GRID_ANGULAR_FREQUENCY * time - math.pi / 2
        ed, eq = abc_to_dq(row["v:grid_a"], row["v:grid_b"], row["v:grid_c"], theta)
        id_, iq = abc_to_dq(row["i:La"], row["i:Lb"], row["i:Lc"], theta)
        if sample_update:
            previous, last_sample_tick = applied, gate_tick
            id_ref = 2.0 if index >= d_step else 0.0
            iq_ref = 1.5 if scenario == "main" and index >= q_step else 0.0
            integrators = d_pi.integrator, q_pi.integrator
            ud = d_pi.step(id_ref - id_, CONTROL_PERIOD)
            uq = q_pi.step(iq_ref - iq, CONTROL_PERIOD)
            vd = ed + CROSS_COUPLING * iq - ud
            vq = eq - CROSS_COUPLING * id_ - uq
            magnitude = math.hypot(vd, vq)
            saturated = magnitude > VOLTAGE_LIMIT
            if saturated:
                # 限幅改变了电压矢量，保留两个积分器的上次状态。
                scale = VOLTAGE_LIMIT / magnitude
                vd *= scale
                vq *= scale
                d_pi.integrator, q_pi.integrator = integrators
            va, vb, vc = dq_to_abc(vd, vq, theta)
            pending = va / HALF_DC_VOLTAGE, vb / HALF_DC_VOLTAGE, vc / HALF_DC_VOLTAGE

        return {
            "j": float(index),
            "sample_update": float(sample_update),
            "gate_tick": float(gate_tick),
            "theta": theta,
            "ed": ed, "eq": eq,
            "id": id_, "iq": iq,
            "id_ref": id_ref, "iq_ref": iq_ref,
            "carrier_applied": carrier_at(gate_tick),
            "saturated": float(saturated),
            "z_d": d_pi.integrator, "z_q": q_pi.integrator,
            **{f"applied_{phase}": value for phase, value in zip(PHASES, applied, strict=True)},
            **{f"pending_{phase}": value for phase, value in zip(PHASES, pending, strict=True)},
        }

    return CaseDefinition(
        name="grid_connected_vsc_closed_loop",
        components=_grid_vsc.create_bridge(gate_pair),
        config=SimulationConfig(time_step, stop_time, method="trapezoidal", linear_solver_mode="reuse",
                                event_time_policy="require_aligned"),
        plots=(
            PlotSpec(("id", "id_ref", "iq", "iq_ref"), "dq_currents.png", title="dq currents and references (A)"),
            PlotSpec(("i:La", "i:Lb", "i:Lc"), "phase_currents.png", kind="three_phase",
                     title="Grid-to-bridge phase currents (A)"),
        ),
        output=OutputOptions(save_data=bool(SAVE_RESULT_DATA), save_figure=bool(SAVE_RESULT_FIGURE),
                             show_figure=SHOW_FIGURE),
        summary=print_summary,
        on_step=observe,
    )


def main() -> None:
    run_case(define_case())


if __name__ == "__main__":
    main()
