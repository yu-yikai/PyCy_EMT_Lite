"""增加直流负荷，观察电容放能和并网变流器的母线电压恢复。

电容以 400 V 起步。0.400 s 时接入第二路负荷，电容先补足增加的功率，
电压外环再提高 d 轴电流指令，使电网向直流侧送入更多有功。
"""

import math
from collections.abc import Mapping

from pycy_emt_lite import (
    Capacitor,
    IdealSwitch,
    Resistor,
    SimulationConfig,
    VoltageSource,
)
from pycy_emt_lite.cases import CaseDefinition, OutputOptions, PlotSpec, run_case
from pycy_emt_lite.controls import SRFPLL, PIController
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
STOP_TIME = 0.800005
LOAD_STEP_TIME = 0.400
LOAD_RESISTANCE = 320.0
CAPACITANCE = 0.005
VOLTAGE_REFERENCE = _grid_vsc.DC_VOLTAGE
OUTER_PERIOD = 0.001

# PSCAD 预充快照断开后，1 GΩ 支路仍有极小泄漏。两档保留各自的预充电源设定。
PRECHARGE_VOLTAGE = {
    TIME_STEP: 401.2531363814022,
    _grid_vsc.FINE_TIME_STEP: 401.25282290247816,
}


def _voltage_reference(time_step: float) -> ReferenceCallback:
    regulator = PIController(0.276, 4.96, lower=0.0, upper=5.0)
    steps_per_outer = round(OUTER_PERIOD / time_step)

    def reference_after_solve(
        row: Mapping[str, float], index: int, _angle: float,
    ) -> tuple[tuple[float, float], Mapping[str, float]]:
        voltage = row["v:Cdc"]
        outer_update = index > 0 and index % steps_per_outer == 0
        if outer_update:
            regulator.step(VOLTAGE_REFERENCE - voltage, OUTER_PERIOD)
        return (regulator.last_output, 0.0), {
            "outer_update": float(outer_update),
            "dc_pi_integrator": regulator.integrator,
            "vdc_ref_v": VOLTAGE_REFERENCE,
            "p_dc_load_w": voltage * (row["i:Rload"] + row["i:Rstep"]),
        }

    return reference_after_solve


def print_summary(result: SimulationResult) -> None:
    last = result.rows[-1]
    print(f"末点母线电压为 {last['v:Cdc']:.3f} V，总负荷功率为 {last['p_dc_load_w']:.2f} W。")


def define_case(*, time_step: float = TIME_STEP, stop_time: float = STOP_TIME) -> CaseDefinition:
    """用母线实测电压闭环，支持 5 µs 和 2.5 µs 两档电气步长。"""
    time_step = _grid_vsc.checked_time_step(time_step)
    load_tick = _grid_vsc.electrical_index(LOAD_STEP_TIME, time_step)

    def load_closed(time: float) -> bool:
        # 让第二路负荷参与 0.400 s 当行的电气求解。
        return _grid_vsc.electrical_index(time, time_step) >= load_tick

    dc_link = (
        Capacitor("Cdc", "dc_p", "dc_n", CAPACITANCE, initial_voltage=VOLTAGE_REFERENCE),
        Resistor("Rload", "dc_p", "dc_n", LOAD_RESISTANCE),
        Resistor("Rstep", "dc_p", "load_switch", LOAD_RESISTANCE),
        IdealSwitch("Sload", "load_switch", "dc_n", load_closed,
                    closed_resistance=_grid_vsc.SWITCH_ON_RESISTANCE,
                    open_conductance=_grid_vsc.SWITCH_OFF_CONDUCTANCE),
        VoltageSource("Vpre", "pre_supply", "dc_n", PRECHARGE_VOLTAGE[time_step]),
        Resistor("Rpre", "dc_p", "pre_supply", 1.0 / _grid_vsc.SWITCH_OFF_CONDUCTANCE),
    )
    pll = SRFPLL(100.0, 1000.0, GRID_ANGULAR_FREQUENCY, 19 * math.pi / 12)
    components, observe = create_current_loop(
        time_step, pll=pll, dc_link=dc_link, reference=_voltage_reference(time_step),
    )
    return CaseDefinition(
        name="grid_connected_vsc_dc_voltage",
        components=components,
        config=SimulationConfig(time_step, stop_time, method="trapezoidal", linear_solver_mode="reuse",
                                event_time_policy="require_aligned"),
        plots=(
            PlotSpec(("v:Cdc", "vdc_ref_v"), "dc_voltage.png", title="DC bus voltage (V)"),
            PlotSpec(("id", "id_ref"), "d_axis_current.png", title="d-axis current (A peak)"),
            PlotSpec(("p_dc_load_w",), "dc_load_power.png", title="DC load power (W)"),
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
