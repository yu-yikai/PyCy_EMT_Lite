"""照度下降后，并网光伏的送出功率降低，电压外环将直流母线调回 390 V。"""

import math
from collections.abc import Mapping

from pycy_emt_lite import (
    Capacitor,
    CurrentSource,
    Resistor,
    SimulationConfig,
    VoltageSource,
)
from pycy_emt_lite.cases import CaseDefinition, OutputOptions, PlotSpec, run_case
from pycy_emt_lite.controls import FirstOrderLowPass, PIController, abc_to_dq
from pycy_emt_lite.converters import _grid_vsc
from pycy_emt_lite.converters._grid_vsc_current_loop import (
    ReferenceCallback,
    create_floating_station,
)

TIME_STEP = _grid_vsc.TIME_STEP
STOP_TIME = 1.000005
IRRADIANCE_STEP_TIME = 0.500
VDC_REFERENCE = 390.0
OUTER_PERIOD = 0.001
CURRENT_LIMIT = 4.0  # A，相电流指令峰值
MIN_PCC_RMS = 24.0  # V

# 650 节串联光伏的局部等效。并联电阻由单节伏安斜率换算，电流源按照度查表。
PV_SHUNT_RESISTANCE = 650 / 0.5542833196093568
PV_SOURCE_CURRENT = {1000: 2.7767676890116997, 900: 2.5424749984809205}

# 两档分别取 PSCAD 0.800 s 预充快照的电容电压，作为本例的 0 s。
INITIAL_BUS_VOLTAGE = {
    TIME_STEP: 391.76884528616,
    _grid_vsc.FINE_TIME_STEP: 391.768737973459,
}


def _voltage_reference(time_step: float) -> ReferenceCallback:
    """把母线电压偏差换成沿并网点电压方向的有符号电流指令。"""
    regulator = PIController(0.276, 4.96, lower=-CURRENT_LIMIT, upper=CURRENT_LIMIT)
    d_filter, q_filter = FirstOrderLowPass(0.01), FirstOrderLowPass(0.01)
    steps_per_outer = round(OUTER_PERIOD / time_step)
    dq_request = (0.0, 0.0)
    ip_ref = 0.0

    def update(
        row: Mapping[str, float], index: int, angle: float,
    ) -> tuple[tuple[float, float], Mapping[str, float]]:
        nonlocal dq_request, ip_ref
        vd, vq = abc_to_dq(row["v:pcc_a"], row["v:pcc_b"], row["v:pcc_c"], angle)
        if index:
            d_filter.step(vd, time_step)
            q_filter.step(vq, time_step)
        peak = math.hypot(d_filter.state, q_filter.state)
        outer_due = index > 0 and index % steps_per_outer == 0
        outer_enabled = outer_due and peak >= MIN_PCC_RMS * math.sqrt(2.0)
        if outer_due:
            if outer_enabled:
                vdc = row["v:dc_p"] - row["v:dc_n"]
                ip_ref = regulator.step(VDC_REFERENCE - vdc, OUTER_PERIOD)
                dq_request = (d_filter.state / peak * ip_ref, q_filter.state / peak * ip_ref)
            else:
                ip_ref = 0.0
                dq_request = (0.0, 0.0)
        return dq_request, {
            "outer_due": float(outer_due),
            "outer_enabled": float(outer_enabled),
            "ip_ref_a": ip_ref,
            "dc_integrator": regulator.integrator,
            "pcc_filtered_rms_v": peak / math.sqrt(2.0),
            "filtered_pcc_d_v": d_filter.state,
            "filtered_pcc_q_v": q_filter.state,
        }

    return update


def define_case(*, time_step: float = TIME_STEP, stop_time: float = STOP_TIME) -> CaseDefinition:
    """从预充后的状态开始，支持 5 µs 和 2.5 µs 两档。"""
    time_step = _grid_vsc.checked_time_step(time_step)
    step_tick = _grid_vsc.electrical_index(IRRADIANCE_STEP_TIME, time_step)

    def irradiance(time: float) -> int:
        return 900 if _grid_vsc.electrical_index(time, time_step) >= step_tick else 1000

    def pv_source(time: float) -> float:
        return PV_SOURCE_CURRENT[irradiance(time)]

    bridge, observe_station = create_floating_station("a", time_step, _voltage_reference(time_step))
    dc_link = (
        VoltageSource("VdcReference", "a_n", "0", 0.0),
        Capacitor("Cdc", "a_p", "a_n", 0.01, initial_voltage=INITIAL_BUS_VOLTAGE[time_step]),
        CurrentSource("Ipv", "a_n", "a_p", pv_source, derivative=0.0),
        Resistor("Rpv", "a_p", "a_n", PV_SHUNT_RESISTANCE),
        Resistor("Rload", "a_p", "a_n", 390.0),
    )

    def observe(row: Mapping[str, float]) -> Mapping[str, float]:
        station = observe_station(row)
        va, vb, vc = (station[f"a_pcc_{phase}_v"] for phase in "abc")
        ia, ib, ic = (row[f"i:a_L{phase}"] for phase in "abc")
        sunlight = irradiance(row["time"])
        pv_current = PV_SOURCE_CURRENT[sunlight] - row["i:Rpv"]
        # 相电流按电网流向桥为正，向电网送出的有功需取反号。
        return {
            **station,
            "irradiance_w_m2": float(sunlight),
            "pv_delivered_a": pv_current,
            "pv_delivered_w": row["v:Cdc"] * pv_current,
            "pcc_export_w": -(va * ia + vb * ib + vc * ic),
            "pcc_q_var": ((vb - vc) * ia + (vc - va) * ib + (va - vb) * ic) / math.sqrt(3.0),
        }

    return CaseDefinition(
        name="grid_connected_pv",
        components=(*dc_link, *bridge),
        config=SimulationConfig(time_step, stop_time, method="trapezoidal", linear_solver_mode="reuse",
                                event_time_policy="require_aligned"),
        plots=(
            PlotSpec(("irradiance_w_m2",), "irradiance.png", title="Irradiance (W/m²)"),
            PlotSpec(("pv_delivered_w", "pcc_export_w"), "pv_and_grid_power.png", title="PV and grid power (W)"),
            PlotSpec(("v:Cdc",), "dc_bus_voltage.png", title="DC bus voltage (V)"),
        ),
        output=OutputOptions(show_figure=True),
        on_step=observe,
    )


if __name__ == "__main__":
    run_case(define_case())
