"""
文件名称：average.py
文件作用：实现变流器平均模型辅助类。

主要内容：
1. 三相两电平并网逆变器平均相电压模型
2. MMC 教学平均模型
3. VSC-HVDC 简化直流链路模型
"""

from __future__ import annotations

from dataclasses import dataclass

from pycy_emt_lite.controls.transforms import dq_to_abc


@dataclass(frozen=True, slots=True)
class ThreePhaseAverageInverter:
    """三相两电平逆变器平均模型。

    在直流母线电压 `dc_voltage` 下，桥臂调制量 `m_a/m_b/m_c` 位于 `[-1, 1]`，
    相对直流中点的平均相电压近似为：

    ```text
    v_phase = 0.5 * Vdc * m_phase
    ```
    """

    dc_voltage: float

    def __post_init__(self) -> None:
        if self.dc_voltage <= 0.0:
            raise ValueError("直流母线电压必须大于 0。")

    def phase_voltages_from_modulation(self, modulation_abc: tuple[float, float, float]) -> tuple[float, float, float]:
        """根据三相调制量返回平均相电压。"""

        return tuple(0.5 * self.dc_voltage * self._clip_modulation(value) for value in modulation_abc)

    def phase_voltages_from_dq(self, d_axis_voltage: float, q_axis_voltage: float, angle: float) -> tuple[float, float, float]:
        """把 dq 电压指令转换为受直流母线约束的三相平均电压。"""

        abc = dq_to_abc(d_axis_voltage, q_axis_voltage, angle)
        modulation = tuple(2.0 * value / self.dc_voltage for value in abc)
        return self.phase_voltages_from_modulation(modulation)

    @staticmethod
    def _clip_modulation(value: float) -> float:
        """把调制量约束到两电平平均模型的线性范围。"""

        return min(max(float(value), -1.0), 1.0)


@dataclass(frozen=True, slots=True)
class ModularMultilevelConverterAverage:
    """MMC 简化平均模型。

    第一版用于系统级教学：忽略子模块开关排序、环流、臂内二倍频能量波动和均压控制，
    仅用等效直流电压、调制比和桥臂电感电阻估算交流侧平均相电压。
    """

    dc_voltage: float
    arm_inductance: float = 0.0
    arm_resistance: float = 0.0
    submodules_per_arm: int = 20
    nominal_submodule_capacitance: float = 1e-3

    def __post_init__(self) -> None:
        if self.dc_voltage <= 0.0:
            raise ValueError("MMC 直流电压必须大于 0。")
        if self.arm_inductance < 0.0 or self.arm_resistance < 0.0:
            raise ValueError("MMC 桥臂电感和电阻不能小于 0。")
        if self.submodules_per_arm <= 0:
            raise ValueError("MMC 每臂子模块数量必须大于 0。")
        if self.nominal_submodule_capacitance <= 0.0:
            raise ValueError("MMC 子模块电容必须大于 0。")

    @property
    def nominal_submodule_voltage(self) -> float:
        """返回额定子模块电容电压。"""

        return self.dc_voltage / self.submodules_per_arm

    def phase_voltages_from_modulation(self, modulation_abc: tuple[float, float, float]) -> tuple[float, float, float]:
        """根据调制比返回交流侧平均相电压。"""

        return tuple(0.5 * self.dc_voltage * self._clip_modulation(value) for value in modulation_abc)

    def phase_voltages_from_dq(self, d_axis_voltage: float, q_axis_voltage: float, angle: float) -> tuple[float, float, float]:
        """把 dq 电压指令转换为 MMC 交流侧平均相电压。"""

        abc = dq_to_abc(d_axis_voltage, q_axis_voltage, angle)
        modulation = tuple(2.0 * value / self.dc_voltage for value in abc)
        return self.phase_voltages_from_modulation(modulation)

    def arm_energy(self, average_capacitor_voltage: float | None = None) -> float:
        """估算六个桥臂子模块电容总能量。"""

        voltage = self.nominal_submodule_voltage if average_capacitor_voltage is None else float(average_capacitor_voltage)
        return 6.0 * self.submodules_per_arm * 0.5 * self.nominal_submodule_capacitance * voltage * voltage

    @staticmethod
    def _clip_modulation(value: float) -> float:
        return min(max(float(value), -1.0), 1.0)


@dataclass(frozen=True, slots=True)
class VSCHVDCLinkAverage:
    """VSC-HVDC 简化平均直流链路。

    用直流电容和线路电阻描述两端 VSC 之间的功率交换。该模型用于参数扫描、
    报告和教学案例，不包含外环控制器、交流网络暂态或 MMC 内部动态。
    """

    dc_voltage: float
    dc_capacitance: float
    dc_resistance: float

    def __post_init__(self) -> None:
        if self.dc_voltage <= 0.0:
            raise ValueError("VSC-HVDC 直流电压必须大于 0。")
        if self.dc_capacitance <= 0.0:
            raise ValueError("VSC-HVDC 直流电容必须大于 0。")
        if self.dc_resistance < 0.0:
            raise ValueError("VSC-HVDC 直流电阻不能小于 0。")

    def step(self, voltage: float, sending_power: float, receiving_power: float, time_step: float) -> float:
        """推进一个直流电压时间步。

        功率约定：`sending_power` 为送端注入直流链路的功率，`receiving_power` 为受端
        从直流链路吸收的功率。
        """

        if time_step <= 0.0:
            raise ValueError("VSC-HVDC 时间步长必须大于 0。")
        current = (sending_power - receiving_power) / max(abs(voltage), 1e-9)
        loss_power = current * current * self.dc_resistance
        loss_current = loss_power / max(abs(voltage), 1e-9)
        dv_dt = (current - loss_current) / self.dc_capacitance
        return float(voltage + dv_dt * time_step)
