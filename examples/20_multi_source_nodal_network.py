"""七电阻双源网络：节点电压、支路方向和理想源的功率。

运行：uv run python examples/20_multi_source_nodal_network.py
建议在01欧姆定律之后学习，先按网表画图，再用各节点KCL核对电流。

Vs: src→0, 3V；Is: c→d, -0.2A（即从d向c注入0.2A）。
电阻正向：R1 src→b，R2 src→a，R3 a→b，R4 a→c，
R5 b→d，R6 b→0，R7 d→0。阻值集中列在下方。

c节点约422V、d约-8.44V；理想电流源不受电源电压/合规电压约束。
R4需传输0.2A，2kΩ产生400V压差。Vs吸收功率，Is提供能量。
这不是实际200mA电源在任意电压下都可工作的器件模型。
i:Is列记录电流源的已知输入；源对网络的实际作用由节点和电阻电流KCL验证。

网络没有储能，全部时间点相同；此例检验代数网络和功率方向，不检验暂态。
练习：改变CURRENT_D_TO_C或R4，观察c电压和损耗；反转电流源会改变
部分支路方向。恢复默认参数后，才适用validation/cases/nodal_analysis的参考。
"""

from pycy_emt_lite import CurrentSource, Resistor, SimulationConfig, VoltageSource
from pycy_emt_lite.cases import CaseDefinition, OutputOptions, PlotSpec, run_case
from pycy_emt_lite.io.results import SimulationResult

# 1. Parameters (V, A, ohm, s)
SAVE_RESULT_DATA = 0
SAVE_RESULT_FIGURE = 0
SHOW_FIGURE = True
VOLTAGE_SOURCE = 3.0
CURRENT_D_TO_C = 0.2
RESISTORS = (
    ("R1", "src", "b", 200.0), ("R2", "src", "a", 140.0),
    ("R3", "a", "b", 330.0), ("R4", "a", "c", 2000.0),
    ("R5", "b", "d", 330.0), ("R6", "b", "0", 50.0), ("R7", "d", "0", 50.0),
)
TIME_STEP = 100e-6
STOP_TIME = 0.01


def print_summary(result: SimulationResult) -> None:
    """5. Passive-sign power: positive means absorbed, negative supplied."""
    row = result.rows[-1]
    for node in ("src", "a", "b", "c", "d"):
        print(f"节点{node}: {row[f'v:{node}']:+.6f} V")
    loss = sum(row[f"i:{name}"] ** 2 * resistance for name, _, _, resistance in RESISTORS)
    voltage_source_power = row["v:src"] * row["i:Vs"]
    current_source_power = (row["v:c"] - row["v:d"]) * row["i:Is"]
    print(f"电阻总损耗：{loss:.9f} W")
    print(f"Vs吸收功率：{voltage_source_power:+.9f} W；Is吸收功率：{current_source_power:+.9f} W")
    print(f"功率余额：{loss + voltage_source_power + current_source_power:+.3e} W")


def define_case() -> CaseDefinition:
    """2. Build circuit; 3. Record the prescribed source current and define plots."""
    source = CurrentSource("Is", "c", "d", -CURRENT_D_TO_C)
    # CurrentSource has no built-in output column. This callback records its
    # prescribed constant input; KCL and resistor currents verify its action.
    prescribed_current = float(source.current)

    def record_source_current(_row):
        return {"i:Is": prescribed_current}

    components = (
        VoltageSource("Vs", "src", "0", VOLTAGE_SOURCE), source,
        *(Resistor(name, positive, negative, resistance) for name, positive, negative, resistance in RESISTORS),
    )
    return CaseDefinition(
        name="multi_source_nodal_network", components=components,
        config=SimulationConfig(TIME_STEP, STOP_TIME), on_step=record_source_current,
        plots=(
            PlotSpec(("v:src", "v:a", "v:b", "v:d"), "node_voltages.png", title="Nodal network: voltages (V)"),
            PlotSpec(("v:c",), "current_source_node.png", title="Ideal current source: node c (V)"),
            PlotSpec(("i:R2", "i:R4", "i:Vs", "i:Is"), "currents.png", title="Nodal network: signed currents (A)"),
        ),
        output=OutputOptions(save_data=bool(SAVE_RESULT_DATA), save_figure=bool(SAVE_RESULT_FIGURE), show_figure=SHOW_FIGURE),
        summary=print_summary,
    )


def main() -> None:
    """4. Run; 5. Summarize; 6. Plot PyCy results."""
    run_case(define_case())


if __name__ == "__main__":
    main()
