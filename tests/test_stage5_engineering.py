"""
文件名称：test_stage5_engineering.py
文件作用：验证变流器平均模型等工程化教学模型。
"""

from __future__ import annotations

import math

from pycy_emt_lite.converters import ModularMultilevelConverterAverage, VSCHVDCLinkAverage


def test_mmc_average_model_reports_voltage_and_energy() -> None:
    converter = ModularMultilevelConverterAverage(dc_voltage=320e3, submodules_per_arm=40)

    voltages = converter.phase_voltages_from_modulation((1.2, 0.0, -1.2))

    assert voltages == (160e3, 0.0, -160e3)
    assert math.isclose(converter.nominal_submodule_voltage, 8000.0)
    assert converter.arm_energy() > 0.0


def test_vsc_hvdc_link_voltage_changes_with_power_mismatch() -> None:
    link = VSCHVDCLinkAverage(dc_voltage=320e3, dc_capacitance=0.1, dc_resistance=0.5)

    next_voltage = link.step(320e3, sending_power=100e6, receiving_power=90e6, time_step=1e-4)

    assert next_voltage > 320e3
