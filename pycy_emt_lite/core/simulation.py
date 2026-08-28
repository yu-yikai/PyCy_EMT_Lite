"""
文件名称：simulation.py
文件作用：实现固定步长电磁暂态仿真主循环。

主要内容：
1. 仿真配置数据结构
2. MNA 矩阵组装与线性求解
3. 元件状态更新和结果记录
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Literal

import numpy as np

from pycy_emt_lite.core.circuit import Circuit
from pycy_emt_lite.core.context import IntegrationMethod, StampContext
from pycy_emt_lite.core.diagnostics import diagnose_topology
from pycy_emt_lite.core.solvers import DenseLinearSolver, LinearSolveError, LinearSolver
from pycy_emt_lite.events import EventQueue, SimulationEvent
from pycy_emt_lite.io.results import SimulationResult

EventTimePolicy = Literal["insert", "quantize_up", "require_aligned"]


@dataclass(frozen=True, slots=True)
class SimulationConfig:
    """固定步长仿真配置。

    `time_step` 是每次推进的时间间隔，`stop_time` 是仿真结束时间，`method`
    是动态元件离散化方法。当前阶段只支持固定步长。
    """

    time_step: float
    stop_time: float
    start_time: float = 0.0
    method: IntegrationMethod = "trapezoidal"
    event_time_policy: EventTimePolicy = "insert"

    def __post_init__(self) -> None:
        if self.time_step <= 0:
            raise ValueError("仿真步长必须大于 0。")
        if self.stop_time < 0:
            raise ValueError("仿真终止时间不能小于 0。")
        if self.start_time < 0:
            raise ValueError("仿真起始时间不能小于 0。")
        if self.start_time > self.stop_time:
            raise ValueError("仿真起始时间不能大于终止时间。")
        if self.method not in {"trapezoidal", "backward_euler"}:
            raise ValueError(f"不支持的积分方法：{self.method}")
        if self.event_time_policy not in {"insert", "quantize_up", "require_aligned"}:
            raise ValueError(f"不支持的事件时间处理策略：{self.event_time_policy}")


class Simulator:
    """MNA 电磁暂态仿真器。

    仿真器把 `Circuit` 和 `SimulationConfig` 连接起来，负责真正的时间步推进。
    在每个时间点，它会创建空的矩阵 `A` 和右端项 `z`，调用每个元件的 `stamp()`
    方法写入局部模型，然后求解 `A x = z` 得到节点电压和支路电流。
    """

    def __init__(
        self,
        circuit: Circuit,
        config: SimulationConfig,
        events: Iterable[SimulationEvent] = (),
        solver: LinearSolver | None = None,
    ) -> None:
        self.circuit = circuit
        self.config = config
        self.events = list(events)
        self.event_queue = EventQueue(self.events)
        self.event_log: list[dict[str, float | str]] = []
        self.solver = solver or DenseLinearSolver()
        self._last_time: float | None = None
        self._last_solution: np.ndarray | None = None

    def run(self) -> SimulationResult:
        """运行固定步长暂态仿真并返回结果对象。

        核心流程如下：

        1. 准备电路变量：节点电压变量和必要的支路电流变量。
        2. 生成时间序列：从 0 推进到 `stop_time`。
        3. 每个时间步重新组装 MNA 矩阵和右端项。
        4. 求解线性方程，得到当前时刻节点电压和支路电流。
        5. 调用动态元件的 `update_state()`，把当前状态变成下一步历史项。
        6. 记录节点电压、元件电流、电容电压等输出量。
        """

        if not self.circuit.prepared:
            self.circuit._prepare()
        topology_issues = diagnose_topology(self.circuit)
        if topology_issues:
            details = "；".join(topology_issues)
            raise RuntimeError(f"电路拓扑预检查失败：{details}")
        if self.circuit.size == 0:
            raise ValueError("电路没有非参考节点或支路变量，无法求解。")

        times = self._time_points()
        if self.config.start_time > 0.0:
            self.event_queue.skip_until(self.config.start_time, tolerance=self.config.time_step * 1e-9)
        rows: list[dict[str, float]] = []
        solution = np.zeros(self.circuit.size, dtype=float)

        for index, time in enumerate(times):
            if index == 0:
                actual_time_step = self.config.time_step
            else:
                actual_time_step = self._effective_time_step(float(time - times[index - 1]))
            for event in self.event_queue.pop_due(float(time), tolerance=self.config.time_step * 1e-9):
                self.event_log.append(event.apply(self.circuit, float(time)))
            context = StampContext(
                node_manager=self.circuit.node_manager,
                branch_offset=self.circuit.node_manager.count,
                time=float(time),
                time_step=actual_time_step,
                method=self.config.method,
            )
            solution = self._solve_step(context)

            for component in self.circuit.components:
                component.update_state(context, solution)
            rows.append(self._record_row(context, solution))
            self._last_time = float(time)
            self._last_solution = solution.copy()

        return SimulationResult(
            circuit_name=self.circuit.name,
            method=self.config.method,
            time_step=self.config.time_step,
            stop_time=self.config.stop_time,
            rows=rows,
            event_log=self.event_log,
        )

    def _solve_step(self, context: StampContext) -> np.ndarray:
        """装配并求解单个时间步，返回本步解向量。

        `solution` 的前半部分是节点电压，后半部分是电压源、电感等支路电流。
        求解失败统一包装为带求解器名的明确错误。
        """

        matrix, rhs = self._assemble(context)
        try:
            return self.solver.solve(matrix, rhs)
        except LinearSolveError as exc:
            raise RuntimeError(
                f"MNA 矩阵求解失败，当前求解器为 {self.solver.name}；"
                "可能存在孤立节点、缺少参考节点路径或理想源拓扑冲突。"
            ) from exc

    def _assemble(self, context: StampContext) -> tuple[np.ndarray, np.ndarray]:
        """组装当前时间步的 MNA 矩阵和右端项。

        每个元件只知道自己的局部方程。例如电阻只写入两端节点对应的电导，电压源
        只写入自己的电压约束。仿真器负责创建全局矩阵，并让所有元件依次 stamp，
        最终形成完整的 `A x = z`。
        """

        size = self.circuit.size
        matrix = np.zeros((size, size), dtype=float)
        rhs = np.zeros(size, dtype=float)
        for component in self.circuit.components:
            component.stamp(context, matrix, rhs)
        return matrix, rhs

    def _record_row(self, context: StampContext, solution: np.ndarray) -> dict[str, float]:
        """把当前时刻求解结果转换成一行可读结果。

        节点电压字段命名为 `v:节点名`。元件输出由各元件的 `outputs()` 提供，
        例如电阻电流 `i:R1`、电容电压 `v:C1`、电感电流 `i:L1`。
        """

        row: dict[str, float] = {"time": context.time}
        for node_name in self.circuit.node_manager.names:
            node_index = self.circuit.node_manager.index(node_name)
            if node_index is not None:
                row[f"v:{node_name}"] = float(solution[node_index])
        for component in self.circuit.components:
            row.update(component.outputs(context, solution))
        return row

    def _time_points(self) -> np.ndarray:
        """生成仿真时间序列。

        基础时间点按固定步长生成，同时总是包含 `stop_time`。当事件时间策略为
        `insert` 时，事件设定时间也会插入时间序列，使事件在精确设定时间执行；
        当策略为 `quantize_up` 时，事件仍在第一个不早于设定时间的基础时间点执行；
        当策略为 `require_aligned` 时，事件必须与基础步长对齐，否则直接报错。
        """

        time_step = self.config.time_step
        start_time = self.config.start_time
        stop_time = self.config.stop_time
        tolerance = time_step * 1e-9
        if start_time == 0.0:
            count = int(np.floor(stop_time / time_step + tolerance))
            points = [float(index * time_step) for index in range(count + 1)]
        else:
            count = int(np.floor((stop_time - start_time) / time_step + tolerance))
            points = [float(start_time + (index + 1) * time_step) for index in range(count)]
        if not points:
            points = [float(stop_time)]
        if not np.isclose(points[-1], stop_time, rtol=0.0, atol=tolerance):
            points.append(float(stop_time))
        else:
            points[-1] = float(stop_time)

        event_times = [time for time in self.event_queue.times if start_time < time <= stop_time + tolerance]
        if self.config.event_time_policy == "insert":
            points.extend(float(time) for time in event_times)
        elif self.config.event_time_policy == "require_aligned":
            for time in event_times:
                if not self._is_time_aligned(time, tolerance):
                    raise ValueError(
                        f"事件时间 {time} 未与仿真步长 {time_step} 对齐；"
                        "请调整事件时间，或将 event_time_policy 设置为 'insert'。"
                    )

        return np.array(self._sorted_unique_times(points, tolerance), dtype=float)

    @property
    def last_time(self) -> float | None:
        """返回最近一次完成求解的仿真时间。"""

        return self._last_time

    @property
    def last_solution(self) -> np.ndarray | None:
        """返回最近一次完成求解的 MNA 解向量副本。"""

        if self._last_solution is None:
            return None
        return self._last_solution.copy()

    def _is_time_aligned(self, time: float, tolerance: float) -> bool:
        """判断时间是否与基础步长对齐。"""

        nearest_step = round(time / self.config.time_step)
        return abs(time - nearest_step * self.config.time_step) <= tolerance

    def _effective_time_step(self, raw_time_step: float) -> float:
        """把浮点误差造成的步长微小偏差归一到配置步长。"""

        tolerance = self.config.time_step * 1e-9
        if abs(raw_time_step - self.config.time_step) <= tolerance:
            return self.config.time_step
        return raw_time_step

    @staticmethod
    def _sorted_unique_times(points: Iterable[float], tolerance: float) -> list[float]:
        """按容差排序并去重时间点。"""

        unique: list[float] = []
        for point in sorted(points):
            if not unique or abs(point - unique[-1]) > tolerance:
                unique.append(float(point))
            else:
                unique[-1] = float(point)
        return unique
