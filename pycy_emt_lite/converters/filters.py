"""
文件名称：filters.py
文件作用：提供电力电子滤波器的元件组合辅助类。

主要内容：
1. L 滤波器
2. LC 滤波器
3. LCL 滤波器
"""

from __future__ import annotations

from dataclasses import dataclass

from pycy_emt_lite.components import Capacitor, Component, Inductor, Resistor


@dataclass(frozen=True, slots=True)
class LFilter:
    """单相 L 滤波器元件组合。"""

    name: str
    input_node: str
    output_node: str
    inductance: float
    series_resistance: float = 0.0

    def components(self) -> list[Component]:
        """返回组成该 L 滤波器的元件对象列表。"""

        if self.series_resistance > 0.0:
            mid = f"{self.name}:mid"
            return [
                Resistor(f"{self.name}:R", self.input_node, mid, self.series_resistance),
                Inductor(f"{self.name}:L", mid, self.output_node, self.inductance),
            ]
        return [Inductor(f"{self.name}:L", self.input_node, self.output_node, self.inductance)]


@dataclass(frozen=True, slots=True)
class LCFilter:
    """单相 LC 滤波器元件组合。"""

    name: str
    input_node: str
    output_node: str
    ground: str
    inductance: float
    capacitance: float
    series_resistance: float = 0.0

    def components(self) -> list[Component]:
        """返回组成该 LC 滤波器的元件对象列表。"""

        l_filter = LFilter(self.name, self.input_node, self.output_node, self.inductance, self.series_resistance)
        components = l_filter.components()
        components.append(Capacitor(f"{self.name}:C", self.output_node, self.ground, self.capacitance))
        return components


@dataclass(frozen=True, slots=True)
class LCLFilter:
    """单相 LCL 并网滤波器元件组合。"""

    name: str
    converter_node: str
    capacitor_node: str
    grid_node: str
    ground: str
    converter_inductance: float
    grid_inductance: float
    capacitance: float
    converter_resistance: float = 0.0
    grid_resistance: float = 0.0
    damping_resistance: float = 0.0

    def components(self) -> list[Component]:
        """返回组成该 LCL 滤波器的元件对象列表。"""

        components = LFilter(
            f"{self.name}:converter",
            self.converter_node,
            self.capacitor_node,
            self.converter_inductance,
            self.converter_resistance,
        ).components()
        if self.damping_resistance > 0.0:
            damping_node = f"{self.name}:damping"
            components.append(Resistor(f"{self.name}:Rd", self.capacitor_node, damping_node, self.damping_resistance))
            components.append(Capacitor(f"{self.name}:C", damping_node, self.ground, self.capacitance))
        else:
            components.append(Capacitor(f"{self.name}:C", self.capacitor_node, self.ground, self.capacitance))
        components.extend(
            LFilter(
                f"{self.name}:grid",
                self.capacitor_node,
                self.grid_node,
                self.grid_inductance,
                self.grid_resistance,
            ).components()
        )
        return components
