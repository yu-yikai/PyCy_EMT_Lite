"""用有功前馈和交流电压外环调节并网点。

每相馈线把理想电网电源和并网点（PCC）分开。先把有功指令升至 500 W，
再在 240 ms 启用电压调节。可通过 held 工况观察固定无功电流时的压降。
"""

import math
from collections.abc import Mapping

from pycy_emt_lite import SimulationConfig
from pycy_emt_lite.cases import CaseDefinition, OutputOptions, PlotSpec, run_case
from pycy_emt_lite.controls import SRFPLL, FirstOrderLowPass, PIController, abc_to_dq
from pycy_emt_lite.converters import _grid_vsc
from pycy_emt_lite.converters._grid_vsc_current_loop import (
    GRID_ANGULAR_FREQUENCY,
    ReferenceCallback,
    create_current_loop,
)
from pycy_emt_lite.io.results import SimulationResult

SAVE_RESULT_DATA = 0
SAVE_RESULT_FIGURE = 0
SHOW_FIGURE = True

TIME_STEP = _grid_vsc.TIME_STEP
STOP_TIME = 0.650005
FEEDER_RESISTANCE = 0.8
FEEDER_INDUCTANCE = 0.008
OUTER_PERIOD = 0.001
POWER_REFERENCE = 500.0
VOLTAGE_REFERENCE = _grid_vsc.GRID_PHASE_RMS_VOLTAGE
VOLTAGE_FLOOR = 24.0
CURRENT_LIMIT = 2.5
SQRT_TWO = math.sqrt(2)


def _current_reference(
    vd: float, vq: float, power: float, voltage_pi: PIController | None,
) -> tuple[tuple[float, float], float, float]:
    """先在 PCC 电压坐标中分配电流容量，再转回源端 PLL 坐标。"""
    magnitude = math.hypot(vd, vq)
    if magnitude < VOLTAGE_FLOOR * SQRT_TWO:
        return (0.0, 0.0), 0.0, 0.0

    active = min(max(power / (1.5 * magnitude), -CURRENT_LIMIT), CURRENT_LIMIT)
    reactive = 0.0
    if voltage_pi is not None:
        reactive_limit = math.sqrt(max(CURRENT_LIMIT**2 - active**2, 0.0))
        voltage_pi.lower, voltage_pi.upper = -reactive_limit, reactive_limit
        reactive = voltage_pi.step(VOLTAGE_REFERENCE - magnitude / SQRT_TWO, OUTER_PERIOD)

    cos_angle, sin_angle = vd / magnitude, vq / magnitude
    reference = cos_angle * active - sin_angle * reactive, sin_angle * active + cos_angle * reactive
    return reference, active, reactive


def _pcc_reference(time_step: float, *, regulate_voltage: bool) -> ReferenceCallback:
    d_filter, q_filter = FirstOrderLowPass(0.01), FirstOrderLowPass(0.01)
    voltage_pi = PIController(0.15, 6.0)
    steps_per_outer = round(OUTER_PERIOD / time_step)
    reference = 0.0, 0.0
    power = active = reactive = 0.0

    def reference_after_solve(
        row: Mapping[str, float], index: int, angle: float,
    ) -> tuple[tuple[float, float], Mapping[str, float]]:
        nonlocal reference, power, active, reactive
        va, vb, vc = row["v:pcc_a"], row["v:pcc_b"], row["v:pcc_c"]
        if index > 0:
            vd, vq = abc_to_dq(va, vb, vc, angle)
            d_filter.step(vd, time_step)
            q_filter.step(vq, time_step)
        outer_update = index > 0 and index % steps_per_outer == 0
        if outer_update:
            tick = index // steps_per_outer
            power = POWER_REFERENCE * min(max((tick - 120) / 20, 0.0), 1.0)
            pi = voltage_pi if regulate_voltage and tick >= 240 else None
            reference, active, reactive = _current_reference(d_filter.state, q_filter.state, power, pi)

        return reference, {
            "pcc_theta": angle,
            "pcc_d_filtered": d_filter.state,
            "pcc_q_filtered": q_filter.state,
            "outer_update": float(outer_update),
            "p_ref_w": power,
            "ip_ref": active,
            "iq_pcc_ref": reactive,
            "vac_integrator": voltage_pi.integrator,
            "vac_pcc_v_rms": math.hypot(d_filter.state, q_filter.state) / SQRT_TWO,
            "vac_ref_v_rms": VOLTAGE_REFERENCE,
            "p_pcc_w": va * row["i:La"] + vb * row["i:Lb"] + vc * row["i:Lc"],
        }

    return reference_after_solve


def print_summary(result: SimulationResult) -> None:
    voltage = result.series("vac_pcc_v_rms")[-1]
    reactive = result.series("iq_pcc_ref")[-1]
    print(f"末点并网点相电压的估计有效值为 {voltage:.3f} V，PCC q 轴电流指令为 {reactive:.3f} A 峰值。")


def define_case(
    *, scenario: str = "regulated", time_step: float = TIME_STEP, stop_time: float = STOP_TIME,
) -> CaseDefinition:
    """默认启用电压外环。held 工况把 PCC q 轴参考固定在零。"""
    if scenario not in ("held", "regulated"):
        raise ValueError("scenario 必须为 held 或 regulated。")
    time_step = _grid_vsc.checked_time_step(time_step)
    pll = SRFPLL(100.0, 1000.0, GRID_ANGULAR_FREQUENCY, 19 * math.pi / 12)
    components, observe = create_current_loop(
        time_step, pll=pll, feeder=(FEEDER_RESISTANCE, FEEDER_INDUCTANCE),
        reference=_pcc_reference(time_step, regulate_voltage=scenario == "regulated"),
    )
    return CaseDefinition(
        name="grid_connected_vsc_power_vac",
        components=components,
        config=SimulationConfig(time_step, stop_time, method="trapezoidal", linear_solver_mode="reuse",
                                event_time_policy="require_aligned"),
        plots=(
            PlotSpec(("vac_pcc_v_rms", "vac_ref_v_rms"), "pcc_voltage.png", title="PCC phase voltage (V RMS)"),
            PlotSpec(("p_pcc_w", "p_ref_w"), "pcc_power.png", title="PCC instantaneous and requested power (W)"),
            PlotSpec(("iq_pcc_ref",), "pcc_q_reference.png", title="PCC q-axis current reference (A peak)"),
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
