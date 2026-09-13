"""
文件名称：filters.py
文件作用：提供电力电子滤波器的元件组合辅助类。

主要内容：
1. L 滤波器
2. LC 滤波器
3. LCL 滤波器
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from numbers import Real

from pycy_emt_lite.components import Capacitor, Component, Inductor, Resistor


def _validate_parameter(name: str, parameter: str, value: float, *, allow_zero: bool = False) -> None:
    """在选择拓扑前检查参数，避免把非法电阻当作省略支路。"""
    if (isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(value)
            or value < 0.0 or (value == 0.0 and not allow_zero)):
        required_range = "大于或等于 0" if allow_zero else "大于 0"
        raise ValueError(
            f"滤波器 {name} 的 {parameter}={value!r} 必须为{required_range}的有限实数；"
            "请按参数单位设置合法数值，不使用布尔值、NaN 或 Inf。"
        )


@dataclass(frozen=True, slots=True)
class LFilter:
    """单相 L 滤波器元件组合。"""

    name: str
    input_node: str
    output_node: str
    inductance: float
    series_resistance: float = 0.0

    def __post_init__(self) -> None:
        _validate_parameter(self.name, "inductance", self.inductance)
        _validate_parameter(self.name, "series_resistance", self.series_resistance, allow_zero=True)

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

    def __post_init__(self) -> None:
        _validate_parameter(self.name, "inductance", self.inductance)
        _validate_parameter(self.name, "capacitance", self.capacitance)
        _validate_parameter(self.name, "series_resistance", self.series_resistance, allow_zero=True)

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

    def __post_init__(self) -> None:
        for parameter in ("converter_inductance", "grid_inductance", "capacitance"):
            _validate_parameter(self.name, parameter, getattr(self, parameter))
        for parameter in ("converter_resistance", "grid_resistance", "damping_resistance"):
            _validate_parameter(self.name, parameter, getattr(self, parameter), allow_zero=True)

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
