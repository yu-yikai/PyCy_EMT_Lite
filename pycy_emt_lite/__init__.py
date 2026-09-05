"""
文件名称：__init__.py
文件作用：定义 PyCy_EMT_Lite 包的公开入口。

主要内容：
1. 暴露当前版本号
2. 暴露常用建模类、仿真器和算例接口，便于示例和用户脚本直接导入
"""

from pycy_emt_lite.cases import CaseDefinition, OutputOptions, PlotSpec, run_case
from pycy_emt_lite.components.basic import Capacitor, CurrentSource, Inductor, Resistor, VoltageSource
from pycy_emt_lite.components.lines import PiLine
from pycy_emt_lite.components.power_electronics import IdealSwitch
from pycy_emt_lite.components.switching import Breaker, Fault
from pycy_emt_lite.components.three_phase import (
    ThreePhaseLine,
    ThreePhaseLoad,
    ThreePhaseSource,
)
from pycy_emt_lite.components.transformers import SinglePhaseTransformer
from pycy_emt_lite.core.circuit import Circuit
from pycy_emt_lite.core.simulation import SimulationConfig, Simulator
from pycy_emt_lite.events import BreakerCloseEvent, BreakerOpenEvent, FaultApplyEvent, FaultClearEvent
from pycy_emt_lite.io.results import SimulationResult

__all__ = [
    "Breaker",
    "BreakerCloseEvent",
    "BreakerOpenEvent",
    "Capacitor",
    "CaseDefinition",
    "Circuit",
    "CurrentSource",
    "Fault",
    "FaultApplyEvent",
    "FaultClearEvent",
    "IdealSwitch",
    "Inductor",
    "OutputOptions",
    "PlotSpec",
    "PiLine",
    "Resistor",
    "SimulationConfig",
    "SimulationResult",
    "Simulator",
    "SinglePhaseTransformer",
    "ThreePhaseLine",
    "ThreePhaseLoad",
    "ThreePhaseSource",
    "VoltageSource",
    "run_case",
]

__version__ = "0.1.0"
