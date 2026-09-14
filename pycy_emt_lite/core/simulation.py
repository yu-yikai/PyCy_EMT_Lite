"""
文件名称：simulation.py
文件作用：实现固定步长电磁暂态仿真主循环。

主要内容：
1. 仿真配置数据结构
2. MNA 矩阵组装与线性求解
3. 元件状态更新和结果记录
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from numbers import Integral, Real
from collections.abc import Callable, Mapping
from types import MappingProxyType
from typing import Iterable, Literal

import numpy as np

from pycy_emt_lite.components.lines import BergeronLine, ThreePhaseBergeronLine
from pycy_emt_lite.core.circuit import Circuit
from pycy_emt_lite.core.context import IntegrationMethod, StampContext
from pycy_emt_lite.core.solvers import DenseLinearSolver, LinearSolveError, LinearSolver
from pycy_emt_lite.core.stamping import _InitialConditions
from pycy_emt_lite.events import EventQueue, SimulationEvent
from pycy_emt_lite.events.base import _time_close, _time_tolerance
from pycy_emt_lite.io.results import SimulationResult

EventTimePolicy = Literal["insert", "quantize_up", "require_aligned"]
StepCallback = Callable[[Mapping[str, float]], Mapping[str, float]]


@dataclass(frozen=True, slots=True)
class SimulationConfig:
    """固定步长仿真配置。

    `time_step` 是每次推进的时间间隔，`stop_time` 是仿真结束时间，`method`
    是动态元件离散化方法。终止时间必须是基础步长的整数倍；显式事件可按所选
    策略插入非对齐时刻，储能元件使用对应的实际区间步长。
    """

    time_step: float
    stop_time: float
    start_time: float = 0.0
    method: IntegrationMethod = "trapezoidal"
    event_time_policy: EventTimePolicy = "insert"
    record_every: int = 1

    def __post_init__(self) -> None:
        if isinstance(self.record_every, bool) or not isinstance(self.record_every, Integral) or self.record_every < 1:
            raise ValueError("record_every 必须为正整数；请填写每隔多少个求解点保存一次结果。")
        for field_name, value in (
            ("time_step", self.time_step),
            ("stop_time", self.stop_time),
            ("start_time", self.start_time),
        ):
            if isinstance(value, bool) or not isinstance(value, Real) or not np.isfinite(value):
                raise ValueError(
                    f"仿真时间字段 {field_name}={value!r} 必须为有限实数；"
                    "请填写以秒为单位的数值，不使用布尔值、字符串、数组、NaN 或 Inf。"
                )
        if self.time_step <= 0:
            raise ValueError(f"time_step={self.time_step!r} 非法；请将仿真步长设为大于 0 的秒数。")
        if self.stop_time < 0:
            raise ValueError(f"stop_time={self.stop_time!r} 非法；请使用非负终止时间，0 表示只求初值。")
        if self.start_time != 0.0:
            raise ValueError(
                f"start_time={self.start_time!r} 非法，仿真起始时间目前只支持 0；"
                "请设为 start_time=0 并声明元件初值，当前不支持状态恢复续算。"
            )
        if not isinstance(self.method, str) or self.method not in {"trapezoidal", "backward_euler"}:
            raise ValueError(f"不支持 method={self.method!r}；请选择 'trapezoidal' 或 'backward_euler'。")
        if not isinstance(self.event_time_policy, str) or self.event_time_policy not in {"insert", "quantize_up", "require_aligned"}:
            raise ValueError(
                f"不支持 event_time_policy={self.event_time_policy!r}；"
                "请选择 'insert'、'quantize_up' 或 'require_aligned'。"
            )
        ratio = self.stop_time / self.time_step
        if not np.isfinite(ratio):
            raise ValueError(
                f"stop_time={self.stop_time!r} 与 time_step={self.time_step!r} 的比值超出有限数范围；"
                "请减小终止时间或增大步长。"
            )
        steps = round(ratio)
        if self.stop_time > 0 and (steps < 1 or not _time_close(self.stop_time, steps * self.time_step)):
            nearest_stop = max(1, steps) * self.time_step
            raise ValueError(
                f"stop_time={self.stop_time!r} s 不是 time_step={self.time_step!r} s 的整数倍；"
                f"请将终止时间设为整数步（例如 {float(nearest_stop)!r} s），或调整 time_step 使其整除终止时间。"
            )


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
        *,
        on_step: StepCallback | None = None,
    ) -> None:
        self.circuit = circuit
        self.config = config
        self.events = list(events)
        self.event_queue = EventQueue(self.events)
        self.event_log: list[dict[str, float | str]] = []
        self.solver = solver or DenseLinearSolver()
        if on_step is not None and not callable(on_step):
            raise ValueError("on_step 必须为可调用对象或 None。")
        self.on_step = on_step
        self._last_time: float | None = None
        self._last_solution: np.ndarray | None = None
        self._run_started = False

    def run(self) -> SimulationResult:
        """运行固定步长暂态仿真并返回结果对象。

        核心流程如下：

        1. 准备电路变量：节点电压变量和必要的支路电流变量。
        2. 在 t=0 应用事件，固定储能初值求一致代数量并记录。
        3. 只在正时间区间组装积分 companion、求解并更新储能状态。
        4. 事件先积分至左侧，再依声明顺序修改网络，固定状态求右侧代数量。
        5. 写回历史并记录，每个时刻只输出一行；事件行使用右侧值。
        """

        if self._run_started:
            raise RuntimeError("Simulator 实例只能运行一次。")
        self._run_started = True
        self.circuit._claim_run()
        if not self.circuit.prepared:
            self.circuit._prepare()
        if self.circuit.size == 0:
            raise ValueError("电路没有非参考节点或支路变量，无法求解。")

        times = self._time_points()
        self._prepare_delay_lines(times)
        for event in self.events:
            event.validate(self.circuit)
        rows: list[dict[str, float]] = []
        solution = np.zeros(self.circuit.size, dtype=float)

        for index, time in enumerate(times):
            if index == 0:
                actual_time_step = 0.0
            else:
                actual_time_step = self._effective_time_step(float(time - times[index - 1]))
            due_events = self.event_queue.pop_due(float(time))
            context = StampContext(
                node_manager=self.circuit.node_manager,
                branch_offset=self.circuit.node_manager.count,
                time=float(time),
                time_step=actual_time_step,
                method=self.config.method,
            )
            if index > 0:
                solution = self._solve_step(context)
                for component in self.circuit.components:
                    component.update_state(context, solution)
            for event in due_events:
                self.event_log.append(event.apply(self.circuit, float(time)))
            if index == 0 or due_events:
                context = replace(context, time_step=0.0, _initial=_InitialConditions())
                solution = self._solve_step(context)
                for component in self.circuit.components:
                    component.update_state(context, solution)
            row = self._record_row(context, solution)
            # 每个求解点只回调一次，事件点读取右侧值；控制输出作用于下一步。
            # t=0 也调用，但控制器须只观察/初始化，不把零间隔传给 PI/PLL.step。
            if self.on_step is not None:
                extra = self.on_step(MappingProxyType(row))
                if not isinstance(extra, Mapping):
                    raise ValueError("on_step 必须返回新增结果字段的映射（无需字段时返回空字典）。")
                for key, value in extra.items():
                    if not isinstance(key, str) or not key or key in row:
                        raise ValueError(f"on_step 输出字段 {key!r} 非法或与已有结果冲突。")
                    if isinstance(value, bool) or not isinstance(value, Real) or not np.isfinite(value):
                        raise ValueError(f"on_step 输出 {key!r} 必须为有限实数。")
                row.update(extra)
            if index % self.config.record_every == 0 or due_events or index == len(times) - 1:
                rows.append(row)
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

    def _prepare_delay_lines(self, times: np.ndarray) -> None:
        """Bergeron 只读取整步历史；在求解或应用事件前检查实际网格。"""

        lines = []
        for component in self.circuit.components:
            if isinstance(component, BergeronLine):
                lines.append(component)
            elif isinstance(component, ThreePhaseBergeronLine):
                lines.extend(component.lines.values())
        if not lines:
            return
        time_step = self.config.time_step
        for index, time in enumerate(times):
            if not _time_close(float(time), index * time_step):
                raise ValueError(
                    f"Bergeron 线路只支持固定时间步长 {time_step:g}；停止时间和实际事件时间须对齐网格，"
                    f"当前时间 {time:g} 未对齐。可调整时间，或用 quantize_up 将事件延后到网格点。"
                )
        for line in lines:
            ratio = line.travel_time / time_step
            delay_steps = round(ratio) if np.isfinite(ratio) else 0
            if delay_steps < 1 or not _time_close(line.travel_time, delay_steps * time_step):
                raise ValueError(
                    f"Bergeron 线路 {line.name!r} 的传播时延 {line.travel_time:g} 必须是固定时间步长 "
                    f"{time_step:g} 的正整数倍（至少一步）。"
                )
            line._time_step = time_step
            line._delay_steps = delay_steps

    def _solve_step(self, context: StampContext) -> np.ndarray:
        """装配并求解单个时间步，返回本步解向量。

        `solution` 的前半部分是节点电压，后半部分是电压源、电感等支路电流。
        求解失败统一包装为带求解器名的明确错误。
        """

        matrix, rhs = self._assemble(context)
        try:
            if context._initial is not None:
                matrix, rhs = context._initial.assemble(matrix, rhs)
            solution = self.solver.solve(matrix, rhs)
            if context._initial is not None:
                try:
                    context._initial.accept(solution, self.circuit.size)
                except ValueError:
                    # 高压储能与近零源约束并存时，LU 消减误差可能通过整体残差检查
                    # 却不满足逐行约束。只补一次残差方程，原有初值检查仍须通过。
                    solution += self.solver.solve(matrix, rhs - matrix @ solution)
                    context._initial.accept(solution, self.circuit.size)
            return solution[:self.circuit.size]
        except (LinearSolveError, ValueError) as exc:
            initial_note = "一致求解" if context._initial is not None else ""
            raise RuntimeError(
                f"MNA {initial_note}矩阵求解失败：仿真时间 {context.time:g}，"
                f"当前求解器为 {self.solver.name}；{exc}"
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
            try:
                component.stamp(context, matrix, rhs)
            except Exception as exc:
                raise RuntimeError(
                    f"元件 {component.name!r} 在仿真时间 {context.time:g} stamp 失败：{exc}"
                ) from exc
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
            outputs = component.outputs(context, solution)
            duplicates = row.keys() & outputs.keys()
            if duplicates:
                raise ValueError(
                    f"元件 {component.name!r} 在仿真时间 {context.time:g} 的输出字段与已有结果冲突："
                    f"{', '.join(sorted(duplicates))}；请重命名对应节点或元件，避免覆盖节点电压、时间或其他元件输出。"
                )
            row.update(outputs)
        return row

    def _time_points(self) -> np.ndarray:
        """生成仿真时间序列。

        终止时间已检查为整数步；基础时间点按固定步长生成，并保留声明的 `stop_time`。
        当事件时间策略为
        `insert` 时，事件设定时间也会插入时间序列，使事件在精确设定时间执行；
        当策略为 `quantize_up` 时，事件仍在第一个不早于设定时间的基础时间点执行；
        当策略为 `require_aligned` 时，事件必须与基础步长对齐，否则直接报错。
        """

        time_step = self.config.time_step
        stop_time = self.config.stop_time
        count = round(stop_time / time_step)
        points = [float(index * time_step) for index in range(count + 1)]
        points[-1] = float(stop_time)

        event_times = []
        for event_time in self.event_queue.times:
            if event_time <= 0.0:
                continue
            if event_time > stop_time and not _time_close(event_time, stop_time):
                continue
            if _time_close(event_time, stop_time):
                event_times.append(float(stop_time))
                continue
            nearest_index = round(event_time / time_step)
            if 0 < nearest_index < len(points) and _time_close(event_time, points[nearest_index]):
                event_times.append(points[nearest_index])
            else:
                event_times.append(event_time)
        if self.config.event_time_policy == "insert":
            points.extend(event_times)
        elif self.config.event_time_policy == "require_aligned":
            for time in event_times:
                if not self._is_time_aligned(time):
                    raise ValueError(
                        f"事件时间 {time} 未与仿真步长 {time_step} 对齐；"
                        "请调整事件时间，或将 event_time_policy 设置为 'insert'。"
                    )

        return np.array(self._sorted_unique_times(points), dtype=float)

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

    def _is_time_aligned(self, time: float) -> bool:
        """判断时间是否与基础步长对齐。"""

        nearest_step = round(time / self.config.time_step)
        if time > 0.0 and nearest_step == 0:
            return False
        return _time_close(time, nearest_step * self.config.time_step)

    def _effective_time_step(self, raw_time_step: float) -> float:
        """把浮点误差造成的步长微小偏差归一到配置步长。"""

        tolerance = _time_tolerance(raw_time_step, self.config.time_step)
        if abs(raw_time_step - self.config.time_step) <= tolerance:
            return self.config.time_step
        return raw_time_step

    @staticmethod
    def _sorted_unique_times(points: Iterable[float]) -> list[float]:
        """按容差排序并去重时间点。"""

        unique: list[float] = []
        for point in sorted(points):
            if not unique or not _time_close(point, unique[-1]):
                unique.append(float(point))
        return unique
