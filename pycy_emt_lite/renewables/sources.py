"""
文件名称：sources.py
文件作用：提供阶段 4 新能源直流侧简化模型。
主要内容：
1. 光伏阵列静态 I-V/P-V 教学模型
2. 储能电池 Thevenin 简化模型
3. DC-link 电容能量平衡模型
"""

from __future__ import annotations

import math
from dataclasses import dataclass


def _validate_positive(value: float, name: str) -> None:
    """检查参数是否为正数。"""

    if value <= 0.0:
        raise ValueError(f"{name} 必须大于 0。")


@dataclass(slots=True)
class PVArrayModel:
    """光伏阵列简化静态模型。

    本模型用于并网控制教学算例，不求解半导体单二极管方程，而是用
    `I = Isc * s * max(0, 1 - (V / Voc)^shape)` 近似 I-V 曲线。
    其中 `s` 为辐照度相对 1000 W/m^2 的比例。
    """

    name: str
    short_circuit_current: float
    open_circuit_voltage: float
    mpp_voltage: float
    mpp_current: float
    curve_shape: float = 8.0
    irradiance_ref: float = 1000.0
    voltage_temperature_coefficient: float = -0.003

    def __post_init__(self) -> None:
        _validate_positive(self.short_circuit_current, "光伏短路电流")
        _validate_positive(self.open_circuit_voltage, "光伏开路电压")
        _validate_positive(self.mpp_voltage, "光伏最大功率点电压")
        _validate_positive(self.mpp_current, "光伏最大功率点电流")
        _validate_positive(self.curve_shape, "光伏曲线形状系数")
        _validate_positive(self.irradiance_ref, "参考辐照度")
        if self.mpp_voltage >= self.open_circuit_voltage:
            raise ValueError("光伏最大功率点电压必须小于开路电压。")

    def current(self, voltage: float, *, irradiance: float = 1000.0, cell_temperature: float = 25.0) -> float:
        """返回指定端电压下的光伏输出电流。

        电流方向定义为从光伏阵列流向直流母线。负电压按短路附近处理，
        超过温度修正后开路电压时电流为 0。
        """

        if irradiance < 0.0:
            raise ValueError("辐照度不能小于 0。")
        voltage_scale = 1.0 + self.voltage_temperature_coefficient * (cell_temperature - 25.0)
        effective_voc = max(self.open_circuit_voltage * voltage_scale, 1e-9)
        irradiance_scale = irradiance / self.irradiance_ref
        clipped_voltage = min(max(float(voltage), 0.0), effective_voc)
        shape_term = (clipped_voltage / effective_voc) ** self.curve_shape
        return self.short_circuit_current * irradiance_scale * max(0.0, 1.0 - shape_term)

    def power(self, voltage: float, *, irradiance: float = 1000.0, cell_temperature: float = 25.0) -> float:
        """返回指定端电压下的光伏输出功率。"""

        return max(float(voltage), 0.0) * self.current(
            voltage,
            irradiance=irradiance,
            cell_temperature=cell_temperature,
        )

    def mpp_power(self, *, irradiance: float = 1000.0, cell_temperature: float = 25.0) -> float:
        """返回简化最大功率点功率估计值。"""

        voltage_scale = 1.0 + self.voltage_temperature_coefficient * (cell_temperature - 25.0)
        voltage = self.mpp_voltage * max(voltage_scale, 0.0)
        current = self.mpp_current * max(irradiance, 0.0) / self.irradiance_ref
        return voltage * current

    def mpp_voltage_reference(self, *, cell_temperature: float = 25.0) -> float:
        """返回温度修正后的最大功率点电压参考。"""

        voltage_scale = 1.0 + self.voltage_temperature_coefficient * (cell_temperature - 25.0)
        return self.mpp_voltage * max(voltage_scale, 0.0)


@dataclass(slots=True)
class BatteryState:
    """储能电池单步状态。"""

    state_of_charge: float
    terminal_voltage: float
    power: float


@dataclass(slots=True)
class BatteryModel:
    """储能电池 Thevenin 简化模型。

    电流正方向定义为放电，即电池向直流母线送出功率。SOC 按库仑计量更新，
    端电压近似为 `Voc(SOC) - I * R_internal`。
    """

    name: str
    nominal_voltage: float
    capacity_ah: float
    internal_resistance: float
    initial_soc: float = 0.5
    min_soc: float = 0.1
    max_soc: float = 0.9
    soc_voltage_slope: float = 0.08
    state: BatteryState = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        _validate_positive(self.nominal_voltage, "电池额定电压")
        _validate_positive(self.capacity_ah, "电池容量")
        if self.internal_resistance < 0.0:
            raise ValueError("电池内阻不能小于 0。")
        if not 0.0 <= self.min_soc <= self.max_soc <= 1.0:
            raise ValueError("SOC 上下限必须满足 0 <= min <= max <= 1。")
        initial_soc = min(max(self.initial_soc, self.min_soc), self.max_soc)
        self.state = BatteryState(initial_soc, self.open_circuit_voltage(initial_soc), 0.0)

    def open_circuit_voltage(self, state_of_charge: float | None = None) -> float:
        """返回随 SOC 线性变化的开路电压。"""

        soc = self.state.state_of_charge if state_of_charge is None else float(state_of_charge)
        return self.nominal_voltage * (1.0 + self.soc_voltage_slope * (soc - 0.5))

    def terminal_voltage(self, current: float) -> float:
        """按当前 SOC 和给定电流计算端电压。"""

        return max(self.open_circuit_voltage() - float(current) * self.internal_resistance, 0.0)

    def step(self, current: float, time_step: float) -> BatteryState:
        """用放电电流推进电池 SOC 并返回状态。"""

        if time_step <= 0.0:
            raise ValueError("电池模型时间步长必须大于 0。")
        current_value = float(current)
        delta_soc = current_value * time_step / (self.capacity_ah * 3600.0)
        soc = min(max(self.state.state_of_charge - delta_soc, self.min_soc), self.max_soc)
        voltage = max(self.nominal_voltage * (1.0 + self.soc_voltage_slope * (soc - 0.5)) - current_value * self.internal_resistance, 0.0)
        self.state = BatteryState(soc, voltage, voltage * current_value)
        return self.state


@dataclass(slots=True)
class DCLink:
    """DC-link 电容能量平衡模型。

    使用电容能量 `E = 0.5 C Vdc^2` 更新直流母线电压，适合平均模型中连接
    光伏、电池和交流变流器的功率平衡。
    """

    capacitance: float
    initial_voltage: float
    min_voltage: float = 1.0
    voltage: float = 0.0

    def __post_init__(self) -> None:
        _validate_positive(self.capacitance, "DC-link 电容")
        _validate_positive(self.initial_voltage, "DC-link 初始电压")
        if self.min_voltage <= 0.0:
            raise ValueError("DC-link 最小电压必须大于 0。")
        self.voltage = self.initial_voltage

    def step(self, source_power: float, load_power: float, time_step: float) -> float:
        """按输入功率和输出功率更新直流电压。

        `source_power` 为注入 DC-link 的功率，`load_power` 为从 DC-link 取走的功率。
        """

        if time_step <= 0.0:
            raise ValueError("DC-link 时间步长必须大于 0。")
        energy_voltage_square = self.voltage * self.voltage
        energy_voltage_square += 2.0 * (float(source_power) - float(load_power)) * time_step / self.capacitance
        self.voltage = math.sqrt(max(energy_voltage_square, self.min_voltage * self.min_voltage))
        return self.voltage
