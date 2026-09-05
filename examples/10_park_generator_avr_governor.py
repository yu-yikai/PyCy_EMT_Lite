"""演示带 AVR 和调速器的 Park dq0 同步发电机暂态响应。

在负荷阶跃扰动下观察机端电压、转速、励磁电压和机械功率的调节过程，
理解励磁调节器与调速器对暂态稳定性的作用。"""

from pycy_emt_lite import (
    Breaker,
    BreakerCloseEvent,
    Resistor,
    SimulationConfig,
)
from pycy_emt_lite.cases import CaseDefinition, OutputOptions, PlotSpec, run_case
from pycy_emt_lite.io.results import SimulationResult
from pycy_emt_lite.machines import ParkSynchronousGenerator

SAVE_RESULT_DATA = 0
SAVE_RESULT_FIGURE = 0
SHOW_FIGURE = True

LOAD_STEP_TIME = 0.2


def print_summary(result: SimulationResult) -> None:
    """打印 Park dq0 发电机算例关键结果。"""

    print(
        "末值："
        f" vt_pu={result.rows[-1]['vt_pu:GEN']:.6f},"
        f" speed_pu={result.rows[-1]['speed_pu:GEN']:.6f},"
        f" efd_pu={result.rows[-1]['efd_pu:GEN']:.6f},"
        f" pm_pu={result.rows[-1]['pm_pu:GEN']:.6f}"
    )


def define_case() -> CaseDefinition:
    """定义 Park dq0 发电机 AVR/调速器算例。"""

    components = (
        ParkSynchronousGenerator(
            "GEN",
            "bus",
            base_power=3000.0,
            base_phase_rms=100.0,
            stator_resistance_pu=0.04,
            d_axis_reactance_pu=1.8,
            q_axis_reactance_pu=1.7,
            d_axis_transient_reactance_pu=0.08,
            q_axis_transient_reactance_pu=0.3,
            d_axis_open_circuit_time_constant=0.6,
            q_axis_open_circuit_time_constant=0.2,
            inertia_constant=3.5,
            damping=0.3,
            voltage_reference_pu=1.0,
            avr_gain=12.0,
            avr_time_constant=0.04,
            mechanical_power_reference_pu=0.85,
            initial_mechanical_power_pu=0.55,
            governor_droop=0.05,
            governor_time_constant=0.08,
            frequency=50.0,
            initial_eq_prime_pu=1.0,
            initial_efd_pu=1.0,
        ),
        Resistor("BASE_A", "bus:a", "0", 30.0),
        Resistor("BASE_B", "bus:b", "0", 30.0),
        Resistor("BASE_C", "bus:c", "0", 30.0),
        Breaker("BRK_A", "bus:a", "step_load:a", closed=False),
        Breaker("BRK_B", "bus:b", "step_load:b", closed=False),
        Breaker("BRK_C", "bus:c", "step_load:c", closed=False),
        Resistor("STEP_A", "step_load:a", "0", 18.0),
        Resistor("STEP_B", "step_load:b", "0", 18.0),
        Resistor("STEP_C", "step_load:c", "0", 18.0),
    )

    config = SimulationConfig(
        time_step=1e-4,
        stop_time=0.6,
        method="trapezoidal",
    )

    events = (
        BreakerCloseEvent(LOAD_STEP_TIME, "BRK_A", "A 相额外负荷投入"),
        BreakerCloseEvent(LOAD_STEP_TIME, "BRK_B", "B 相额外负荷投入"),
        BreakerCloseEvent(LOAD_STEP_TIME, "BRK_C", "C 相额外负荷投入"),
    )

    plots = (
        PlotSpec(
            columns=("vt_pu:GEN", "speed_pu:GEN", "efd_pu:GEN", "pm_pu:GEN", "p_pu:GEN"),
            kind="series",
            title="Park dq0 发电机控制响应",
        ),
    )

    output = OutputOptions(
        save_data=bool(SAVE_RESULT_DATA),
        save_figure=bool(SAVE_RESULT_FIGURE),
        show_figure=SHOW_FIGURE,
    )

    return CaseDefinition(
        name="park_generator_avr_governor",
        components=components,
        config=config,
        events=events,
        plots=plots,
        output=output,
        summary=print_summary,
    )


def main() -> None:
    """按统一算例流程运行仿真。"""

    case = define_case()
    run_case(case)


if __name__ == "__main__":
    main()
