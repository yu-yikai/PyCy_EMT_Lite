"""
文件名称：diagnostics.py
文件作用：提供电路拓扑预检查，尽早发现常见不可求解模型。

主要内容：
1. 基于已实现元件的导通关系构造轻量连通图
2. 检查非参考节点是否存在到参考节点的电气路径
3. 为奇异矩阵之前的常见拓扑错误提供可读诊断
"""

from __future__ import annotations

from collections import defaultdict, deque
from collections.abc import Iterable

from pycy_emt_lite.components.basic import Capacitor, Inductor, Resistor, VoltageSource
from pycy_emt_lite.components.lines import BergeronLine, PiLine, SegmentedLine, ThreePhaseBergeronLine, ThreePhasePiLine
from pycy_emt_lite.components.power_electronics import Diode, IdealSwitch, IGBTSwitch, _bool_at
from pycy_emt_lite.components.switching import Breaker, Fault
from pycy_emt_lite.components.three_phase import PHASES, ThreePhaseLine, ThreePhaseLoad, ThreePhaseSource, phase_node
from pycy_emt_lite.components.transformers import SinglePhaseTransformer, ThreePhaseTransformer, _winding_port
from pycy_emt_lite.core.circuit import Circuit
from pycy_emt_lite.core.nodes import GROUND_NAMES
from pycy_emt_lite.machines import ParkSynchronousGenerator, SynchronousMachine


def diagnose_topology(circuit: Circuit) -> list[str]:
    """返回电路拓扑预检查发现的问题。

    当前诊断聚焦最常见的奇异矩阵来源：非参考节点没有任何可求解路径连接到参考
    节点。该检查是保守的工程提示，不替代最终 MNA 求解器的奇异矩阵诊断。
    """

    graph: dict[str, set[str]] = defaultdict(set)
    grounded_nodes = set(GROUND_NAMES)
    for component in circuit.components:
        for positive, negative in _conductive_edges(component):
            _connect(graph, positive, negative)

    reachable = _reachable_from_ground(graph, grounded_nodes)
    issues: list[str] = []
    for node in circuit.node_manager.names:
        if node not in reachable:
            issues.append(f"节点 {node!r} 没有连接到参考节点的可求解路径。")
    return issues


def _connect(graph: dict[str, set[str]], positive: str, negative: str) -> None:
    """在无向拓扑图中连接两个节点。"""

    graph[positive].add(negative)
    graph[negative].add(positive)


def _reachable_from_ground(graph: dict[str, set[str]], grounded_nodes: set[str]) -> set[str]:
    """返回从参考节点集合可达的节点。"""

    queue: deque[str] = deque(node for node in grounded_nodes if node in graph)
    visited = set(queue)
    while queue:
        node = queue.popleft()
        for neighbor in graph[node]:
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append(neighbor)
    return visited


def _conductive_edges(component: object) -> Iterable[tuple[str, str]]:
    """根据当前已实现元件返回会影响 MNA 可解性的节点连接关系。"""

    if isinstance(component, (Resistor, Capacitor, Inductor, VoltageSource)):
        return [(component.positive, component.negative)]
    if isinstance(component, Fault):
        return [(component.node, component.ground)] if component.enabled else []
    if isinstance(component, Breaker):
        return [(component.positive, component.negative)] if component.closed else []
    if isinstance(component, IdealSwitch):
        if _bool_at(component.closed, 0.0) or component.open_conductance > 0.0:
            return [(component.positive, component.negative)]
        return []
    if isinstance(component, Diode):
        if component.previous_voltage > component.forward_voltage or component.off_conductance > 0.0:
            return [(component.anode, component.cathode)]
        return []
    if isinstance(component, IGBTSwitch):
        gate_on = _bool_at(component.gate, 0.0)
        diode_on = component.anti_parallel_diode and component.previous_voltage < -component.diode_forward_voltage
        if gate_on or diode_on or component.off_conductance > 0.0:
            return [(component.collector, component.emitter)]
        return []
    if isinstance(component, ThreePhaseSource):
        return [(phase_node(component.terminal_bus, phase), component.neutral) for phase in PHASES]
    if isinstance(component, ThreePhaseLine):
        return [(phase_node(component.from_bus, phase), phase_node(component.to_bus, phase)) for phase in PHASES]
    if isinstance(component, ThreePhaseLoad):
        return [(phase_node(component.bus, phase), component.neutral) for phase in PHASES]
    if isinstance(component, PiLine):
        return [(component.sending, component.receiving), (component.sending, component.ground), (component.receiving, component.ground)]
    if isinstance(component, SegmentedLine):
        edges = []
        for index in range(component.sections):
            positive, negative = component._section_nodes(index)
            edges.extend([(positive, negative), (positive, component.ground), (negative, component.ground)])
        return edges
    if isinstance(component, ThreePhasePiLine):
        edges = []
        for phase in PHASES:
            from_node = phase_node(component.from_bus, phase)
            to_node = phase_node(component.to_bus, phase)
            edges.extend([(from_node, to_node), (from_node, component.ground), (to_node, component.ground)])
        return edges
    if isinstance(component, BergeronLine):
        return [(component.sending, component.ground), (component.receiving, component.ground)]
    if isinstance(component, ThreePhaseBergeronLine):
        edges = []
        for phase in PHASES:
            edges.append((phase_node(component.from_bus, phase), component.ground))
            edges.append((phase_node(component.to_bus, phase), component.ground))
        return edges
    if isinstance(component, SinglePhaseTransformer):
        return [
            (component.primary_positive, component.primary_negative),
            (component.secondary_positive, component.secondary_negative),
            (component.primary_positive, component.secondary_positive),
        ]
    if isinstance(component, ThreePhaseTransformer):
        edges = []
        for phase in PHASES:
            primary = _winding_port(component.primary_bus, component.primary_connection, phase, component.primary_neutral)
            secondary = _winding_port(component.secondary_bus, component.secondary_connection, phase, component.secondary_neutral)
            edges.append(primary)
            edges.append(secondary)
            edges.append((primary[0], secondary[0]))
        return edges
    if isinstance(component, (ParkSynchronousGenerator, SynchronousMachine)):
        edges = []
        for phase in PHASES:
            internal = phase_node(component.internal_bus_name, phase)
            terminal = phase_node(component.terminal_bus, phase)
            edges.append((internal, component.neutral))
            edges.append((internal, terminal))
        return edges
    return []
