"""双端 VSC-HVDC。A 站控制并网点的有功和无功，B 站控制直流电压和无功。

从预充电和投入负荷后的状态开始。0.200–0.220 s 提高 A 站有功给定，
观察 B 站从吸收有功转为送出有功，以及两站母线电压的变化。
"""

import math
from collections.abc import Mapping

from pycy_emt_lite import (
    Capacitor,
    Inductor,
    Resistor,
    SimulationConfig,
    VoltageSource,
)
from pycy_emt_lite.cases import CaseDefinition, OutputOptions, PlotSpec, run_case
from pycy_emt_lite.components.base import Component
from pycy_emt_lite.controls import FirstOrderLowPass, PIController, abc_to_dq
from pycy_emt_lite.converters import _grid_vsc
from pycy_emt_lite.converters._grid_vsc_current_loop import (
    ReferenceCallback,
    create_floating_station,
)
from pycy_emt_lite.core.simulation import StepCallback
from pycy_emt_lite.io.results import SimulationResult

TIME_STEP = _grid_vsc.TIME_STEP
STOP_TIME = 0.550005
LINE_RESISTANCE = 0.25  # Ω，每个半段
LINE_INDUCTANCE = 0.002  # H，每个半段
OUTER_PERIOD = 0.001
VDC_REFERENCE = 400.0
PEAK_CURRENT_LIMIT = 4.0
MIN_PCC_PEAK_VOLTAGE = 24.0 * math.sqrt(2)

# 来自 0.402 s 原生快照。每极电压均对地，正负极的电流箭头均从 A 经 M 指向 B。
INITIAL_CAP_VOLTAGES = {
    TIME_STEP: {
        "a_p": 199.9998344024368, "m_p": 199.9507980705613, "b_p": 199.9004211247924,
        "a_n": -199.999834402712, "m_n": -199.9507980708462, "b_n": -199.90042112508598,
    },
    _grid_vsc.FINE_TIME_STEP: {
        "a_p": 199.99983531081762, "m_p": 199.95091790063222, "b_p": 199.9005439557315,
        "a_n": -199.9998353117388, "m_n": -199.9509179015707, "b_n": -199.9005439566759,
    },
}
INITIAL_LINE_CURRENTS = {
    TIME_STEP: {
        "p_am": 0.0071814386743539, "p_mb": 0.016827239313263548,
        "n_am": -0.007181438489965014, "n_mb": -0.01682723912981772,
    },
    _grid_vsc.FINE_TIME_STEP: {
        "p_am": 0.0071518572612620365, "p_mb": 0.01679838381377688,
        "n_am": -0.007151856922041299, "n_mb": -0.01679838347677718,
    },
}


def _dc_link(time_step: float) -> tuple[Component, ...]:
    """连接双极 T 型线路、已投入的负荷和断开后的预充支路。"""
    initial_voltages = INITIAL_CAP_VOLTAGES[time_step]
    initial_currents = INITIAL_LINE_CURRENTS[time_step]
    components: list[Component] = []
    for pole in "pn":
        for point, capacitance in (("a", 0.01), ("m", 0.0001), ("b", 0.01)):
            node = f"{point}_{pole}"
            components.append(Capacitor(f"cap_{node}", node, "0", capacitance, initial_voltages[node]))
        for start, end in ("am", "mb"):
            name = f"{pole}_{start}{end}"
            components.extend((
                Resistor(f"R_{name}", f"{start}_{pole}", f"rl_{name}", LINE_RESISTANCE),
                Inductor(f"I_{name}", f"rl_{name}", f"{end}_{pole}", LINE_INDUCTANCE, initial_currents[name]),
            ))
        supply = f"pre_{pole}"
        components.extend((
            VoltageSource(f"Vpre_{pole}", supply, "0", 200.0 if pole == "p" else -200.0),
            Resistor(f"Rpre_{pole}", supply, f"a_{pole}", 1e9),
        ))
    components.append(Resistor("Rload", "b_p", "b_n", 400.0))
    return tuple(components)


def _ramp(tick: int, start: int, end: int) -> float:
    return min(max((tick - start) / (end - start), 0.0), 1.0)


def _station_reference(station: str, time_step: float) -> ReferenceCallback:
    vd_filter, vq_filter = FirstOrderLowPass(0.01), FirstOrderLowPass(0.01)
    # 只有 B 站调直流电压，允许它从交流系统吸收有功，也允许向交流系统送出有功。
    voltage_pi = PIController(0.276, 4.96, -PEAK_CURRENT_LIMIT, PEAK_CURRENT_LIMIT) if station == "b" else None
    steps_per_outer = round(OUTER_PERIOD / time_step)
    dq_request = (0.0, 0.0)
    ip_ref = iq_pcc_ref = p_ref = q_ref = 0.0

    def reference(row: Mapping[str, float], index: int, angle: float) -> tuple[
        tuple[float, float], Mapping[str, float],
    ]:
        nonlocal dq_request, ip_ref, iq_pcc_ref, p_ref, q_ref
        vd, vq = abc_to_dq(row["v:pcc_a"], row["v:pcc_b"], row["v:pcc_c"], angle)
        id_, iq = abc_to_dq(row["i:La"], row["i:Lb"], row["i:Lc"], angle)
        if index:
            vd_filter.step(vd, time_step)
            vq_filter.step(vq, time_step)
        magnitude = math.hypot(vd_filter.state, vq_filter.state)
        vdc = row["v:dc_p"] - row["v:dc_n"]
        outer_due = index > 0 and index % steps_per_outer == 0
        outer_enabled = outer_due and magnitude >= MIN_PCC_PEAK_VOLTAGE
        if outer_due:
            tick = index // steps_per_outer
            startup = _ramp(tick, 20, 30)
            p_ref = 250.0 * startup + 400.0 * _ramp(tick, 200, 220) if station == "a" else 0.0
            q_ref = (40.0 if station == "a" else -40.0) * startup
            if outer_enabled:
                if voltage_pi is None:
                    ip_ref = min(max(p_ref / (1.5 * magnitude), -PEAK_CURRENT_LIMIT), PEAK_CURRENT_LIMIT)
                else:
                    ip_ref = voltage_pi.step(VDC_REFERENCE - vdc, OUTER_PERIOD)
                # 先满足有功方向，再用剩余电流幅值跟踪无功。
                available = math.sqrt(max(PEAK_CURRENT_LIMIT**2 - ip_ref**2, 0.0))
                iq_pcc_ref = min(max(-q_ref / (1.5 * magnitude), -available), available)
                c, s = vd_filter.state / magnitude, vq_filter.state / magnitude
                dq_request = c * ip_ref - s * iq_pcc_ref, s * ip_ref + c * iq_pcc_ref
            else:
                ip_ref = iq_pcc_ref = 0.0
                dq_request = (0.0, 0.0)

        return dq_request, {
            "outer_due": float(outer_due), "outer_enabled": float(outer_enabled),
            "p_ref_w": p_ref, "q_ref_var": q_ref, "ip_ref_a": ip_ref, "iq_pcc_ref_a": iq_pcc_ref,
            "pcc_p_w": 1.5 * (vd * id_ + vq * iq), "pcc_q_var": 1.5 * (vq * id_ - vd * iq),
            "vdc_v": vdc, "pcc_filtered_rms_v": magnitude / math.sqrt(2),
            "dc_pi_integrator": 0.0 if voltage_pi is None else voltage_pi.integrator,
        }

    return reference


def _station(station: str, time_step: float) -> tuple[tuple[Component, ...], StepCallback]:
    return create_floating_station(station, time_step, _station_reference(station, time_step))


def print_summary(result: SimulationResult) -> None:
    last = result.rows[-1]
    print(f"A 站末点有功给定 {last['a_p_ref_w']:.0f} W，B 站末点母线电压 {last['b_vdc_v']:.3f} V。")


def define_case(*, time_step: float = TIME_STEP, stop_time: float = STOP_TIME) -> CaseDefinition:
    """从线路已预充的状态续算，支持 5 µs 和 2.5 µs 两档。"""
    time_step = _grid_vsc.checked_time_step(time_step)
    station_a, observe_a = _station("a", time_step)
    station_b, observe_b = _station("b", time_step)

    def observe(row: Mapping[str, float]) -> Mapping[str, float]:
        return {
            **observe_a(row), **observe_b(row),
            "dc_sent_w": sum(row[f"v:a_{pole}"] * row[f"i:I_{pole}_am"] for pole in "pn"),
            "dc_received_w": sum(row[f"v:b_{pole}"] * row[f"i:I_{pole}_mb"] for pole in "pn"),
            "dc_series_loss_w": LINE_RESISTANCE * sum(
                row[f"i:I_{pole}_{half}"]**2 for pole in "pn" for half in ("am", "mb")
            ),
        }

    return CaseDefinition(
        name="two_terminal_vsc_hvdc",
        components=(*_dc_link(time_step), *station_a, *station_b),
        config=SimulationConfig(time_step, stop_time, method="trapezoidal", linear_solver_mode="reuse",
                                event_time_policy="require_aligned"),
        plots=(
            PlotSpec(("a_p_ref_w", "a_pcc_p_w", "b_pcc_p_w"), "pcc_active_power.png", title="PCC active power (W)"),
            PlotSpec(("a_vdc_v", "b_vdc_v"), "dc_voltage.png", title="Station DC voltage (V)"),
            PlotSpec(("dc_sent_w", "dc_received_w"), "dc_link_power.png", title="Bipolar link power (W)"),
        ),
        output=OutputOptions(show_figure=True),
        summary=print_summary,
        on_step=observe,
    )


def main() -> None:
    run_case(define_case())


if __name__ == "__main__":
    main()
