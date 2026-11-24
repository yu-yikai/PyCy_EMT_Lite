"""并网变流器给一阶 RC 储能端口充电，再反转有功给定向电网放电。"""

import math
from collections.abc import Mapping

from pycy_emt_lite import Capacitor, Resistor, SimulationConfig, VoltageSource
from pycy_emt_lite.cases import CaseDefinition, OutputOptions, PlotSpec, run_case
from pycy_emt_lite.controls import FirstOrderLowPass, abc_to_dq
from pycy_emt_lite.converters import _grid_vsc
from pycy_emt_lite.converters._grid_vsc_current_loop import (
    ReferenceCallback,
    create_floating_station,
)

TIME_STEP = _grid_vsc.TIME_STEP
STOP_TIME = 0.300005
OUTER_PERIOD = 0.001
CURRENT_LIMIT = 4.0  # A，相电流指令峰值
MIN_PCC_RMS = 24.0  # V

# 来自 PSCAD 0.800 s 快照。两档各自使用其母线电压与极化电压。
INITIAL_CAP_VOLTAGES = {
    TIME_STEP: (399.9996779744659, -0.0003022141969455383),
    _grid_vsc.FINE_TIME_STEP: (399.99967797399387, -0.00030221467733904106),
}


def _power_reference(time_step: float) -> ReferenceCallback:
    """把并网点有功给定换成沿其滤波电压方向的电流指令。"""
    d_filter, q_filter = FirstOrderLowPass(0.01), FirstOrderLowPass(0.01)
    steps_per_outer = round(OUTER_PERIOD / time_step)
    dq_request = (0.0, 0.0)
    p_ref = ip_ref = 0.0

    def update(
        row: Mapping[str, float], index: int, angle: float,
    ) -> tuple[tuple[float, float], Mapping[str, float]]:
        nonlocal dq_request, p_ref, ip_ref
        vd, vq = abc_to_dq(row["v:pcc_a"], row["v:pcc_b"], row["v:pcc_c"], angle)
        if index:
            d_filter.step(vd, time_step)
            q_filter.step(vq, time_step)
        peak = math.hypot(d_filter.state, q_filter.state)
        rms = peak / math.sqrt(2.0)
        outer_due = index > 0 and index % steps_per_outer == 0
        outer_enabled = outer_due and peak >= MIN_PCC_RMS * math.sqrt(2.0)
        if outer_due:
            tick = index // steps_per_outer
            # 升至 +250 W 充电，再用 20 个外环间隔降至 −250 W 放电。
            startup = min(max((tick - 20) / 10, 0.0), 1.0)
            reversal = min(max((tick - 150) / 20, 0.0), 1.0)
            p_ref = 250.0 * startup - 500.0 * reversal
            if outer_enabled:
                ip_ref = min(max(p_ref / (1.5 * peak), -CURRENT_LIMIT), CURRENT_LIMIT)
                dq_request = (d_filter.state / peak * ip_ref, q_filter.state / peak * ip_ref)
            else:
                ip_ref = 0.0
                dq_request = (0.0, 0.0)

        return dq_request, {
            "p_ref_w": p_ref, "q_ref_var": 0.0, "ip_ref_a": ip_ref,
            "outer_due": float(outer_due), "outer_enabled": float(outer_enabled), "pcc_filtered_rms_v": rms,
        }

    return update


def define_case(*, time_step: float = TIME_STEP, stop_time: float = STOP_TIME) -> CaseDefinition:
    """从预充后的状态续算，支持 5 µs 和 2.5 µs 两档。"""
    time_step = _grid_vsc.checked_time_step(time_step)
    bus_voltage, polarization_voltage = INITIAL_CAP_VOLTAGES[time_step]
    bridge, observe_station = create_floating_station("a", time_step, _power_reference(time_step))
    storage = (
        VoltageSource("VdcReference", "a_n", "0", 0.0),
        Capacitor("Cdc", "a_p", "a_n", 0.005, initial_voltage=bus_voltage),
        Resistor("R0", "a_p", "pol", 0.4),
        Resistor("R1", "pol", "ocv", 0.6),
        Capacitor("C1", "pol", "ocv", 0.05, initial_voltage=polarization_voltage),
        VoltageSource("Vocv", "ocv", "a_n", 400.0),
    )

    def observe(row: Mapping[str, float]) -> Mapping[str, float]:
        station = observe_station(row)
        va, vb, vc = (station[f"a_pcc_{phase}_v"] for phase in "abc")
        ia, ib, ic = (row[f"i:a_L{phase}"] for phase in "abc")
        # PCC 正功率流向桥，储能端正功率流入储能支路。
        return {
            **station,
            "pcc_p_w": va * ia + vb * ib + vc * ic,
            "pcc_q_var": ((vb - vc) * ia + (vc - va) * ib + (va - vb) * ic) / math.sqrt(3.0),
            "a_vdc_v": row["v:Cdc"],
            "storage_p_w": row["v:Cdc"] * row["i:R0"],
        }

    return CaseDefinition(
        name="grid_connected_storage",
        components=(*storage, *bridge),
        config=SimulationConfig(time_step, stop_time, method="trapezoidal", linear_solver_mode="reuse",
                                event_time_policy="require_aligned"),
        plots=(
            PlotSpec(("a_p_ref_w", "pcc_p_w", "storage_p_w"), "active_power.png", title="Absorbed active power (W)"),
            PlotSpec(("a_vdc_v",), "dc_bus_voltage.png", title="DC bus voltage (V)"),
            PlotSpec(("v:C1",), "polarization_voltage.png", title="Polarization voltage (V)"),
        ),
        output=OutputOptions(show_figure=True),
        on_step=observe,
    )


if __name__ == "__main__":
    run_case(define_case())
