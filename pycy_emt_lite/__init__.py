"""
文件名称：__init__.py
文件作用：定义 PyCy_EMT_Lite 包的公开入口。

主要内容：
1. 暴露当前版本号
2. 暴露常用建模类、仿真器和算例接口，便于示例和用户脚本直接导入
"""

from pycy_emt_lite.cases import CaseDefinition, OutputOptions, PlotSpec, run_case
from pycy_emt_lite.components.base import Component
from pycy_emt_lite.components.basic import Capacitor, CurrentSource, Inductor, Resistor, VoltageSource
from pycy_emt_lite.components.lines import BergeronLine, PiLine, SegmentedLine, ThreePhaseBergeronLine, ThreePhasePiLine
from pycy_emt_lite.components.power_electronics import Diode, IdealSwitch, IGBTSwitch
from pycy_emt_lite.components.switching import Breaker, Fault
from pycy_emt_lite.components.three_phase import (
    ThreePhaseLine,
    ThreePhaseLoad,
    ThreePhaseParallelRLCLoad,
    ThreePhaseSource,
    phase_node,
)
from pycy_emt_lite.components.transformers import SinglePhaseTransformer, ThreePhaseTransformer
from pycy_emt_lite.controls import (
    SRFPLL,
    FirstOrderLowPass,
    Limiter,
    PIController,
    PLLState,
    SampleDelay,
    abc_to_dq,
    dq_to_abc,
    sine_pwm_duty,
    triangular_carrier,
)
from pycy_emt_lite.converters import (
    LCFilter,
    LCLFilter,
    LFilter,
    ModularMultilevelConverterAverage,
    ThreePhaseAverageInverter,
    VSCHVDCLinkAverage,
)
from pycy_emt_lite.core.circuit import Circuit
from pycy_emt_lite.core.simulation import SimulationConfig, Simulator
from pycy_emt_lite.core.solvers import DenseLinearSolver, LinearSolveError, LinearSolver
from pycy_emt_lite.events import BreakerCloseEvent, BreakerOpenEvent, FaultApplyEvent, FaultClearEvent
from pycy_emt_lite.io.results import SimulationResult
from pycy_emt_lite.machines import ParkSynchronousGenerator, SynchronousMachine
from pycy_emt_lite.renewables import (
    BatteryModel,
    BatteryState,
    DCLink,
    DroopController,
    DroopControlState,
    GridFollowingControlState,
    GridFollowingPowerController,
    LVRTController,
    LVRTState,
    PVArrayModel,
    VSGController,
    VSGControlState,
)
from pycy_emt_lite.visualization import plot_result_comparison, plot_zoom_window, write_markdown_report

__all__ = [
    "Breaker",
    "BreakerCloseEvent",
    "BreakerOpenEvent",
    "BergeronLine",
    "BatteryModel",
    "BatteryState",
    "Capacitor",
    "CaseDefinition",
    "Circuit",
    "Component",
    "CurrentSource",
    "DCLink",
    "DenseLinearSolver",
    "Diode",
    "DroopControlState",
    "DroopController",
    "Fault",
    "FaultApplyEvent",
    "FaultClearEvent",
    "FirstOrderLowPass",
    "GridFollowingControlState",
    "GridFollowingPowerController",
    "IGBTSwitch",
    "IdealSwitch",
    "Inductor",
    "LCLFilter",
    "LCFilter",
    "LFilter",
    "LVRTController",
    "LVRTState",
    "LinearSolveError",
    "LinearSolver",
    "Limiter",
    "ModularMultilevelConverterAverage",
    "OutputOptions",
    "PVArrayModel",
    "ParkSynchronousGenerator",
    "PIController",
    "PlotSpec",
    "PLLState",
    "PiLine",
    "Resistor",
    "SRFPLL",
    "SampleDelay",
    "SegmentedLine",
    "SimulationConfig",
    "SimulationResult",
    "Simulator",
    "SinglePhaseTransformer",
    "SynchronousMachine",
    "ThreePhaseBergeronLine",
    "ThreePhaseLine",
    "ThreePhaseLoad",
    "ThreePhaseParallelRLCLoad",
    "ThreePhasePiLine",
    "ThreePhaseSource",
    "ThreePhaseTransformer",
    "ThreePhaseAverageInverter",
    "VSGControlState",
    "VSGController",
    "VSCHVDCLinkAverage",
    "VoltageSource",
    "abc_to_dq",
    "dq_to_abc",
    "phase_node",
    "plot_result_comparison",
    "plot_zoom_window",
    "run_case",
    "sine_pwm_duty",
    "triangular_carrier",
    "write_markdown_report",
]

__version__ = "0.1.0"
