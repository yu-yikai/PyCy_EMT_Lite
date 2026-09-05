# PyCy_EMT_Lite 仿真程序详细说明

[English](simulation_program_guide.en.md)

> 本文说明 PyCy_EMT_Lite 的 `Circuit`/`Simulator` 仿真内核从元件建模、MNA 矩阵组装
> 到求解和状态更新的完整流程。建议配合 [user_guide.md](user_guide.md) 与
> [new_simulation_workflow.md](new_simulation_workflow.md) 阅读。

## 1. 仿真程序的总体流程

PyCy_EMT 当前阶段采用固定步长电磁暂态仿真流程。一个完整算例通常按以下顺序执行：

1. 用户给定仿真参数，例如仿真步长、仿真结束时间和积分方法。
2. 用户直接定义元件对象列表，每个对象包含元件名称、连接节点和参数值。
   对教学算例而言，电源幅值、电阻、电感、电容等元件参数应优先直接写在对应元件对象中。
3. 程序读取元件对象列表并创建 `Circuit` 电路对象。
4. 程序创建 `SimulationConfig` 仿真配置对象。
5. 程序创建 `Simulator` 仿真器对象。
6. 仿真器准备 MNA 变量，包括节点电压变量和必要的支路电流变量。
7. 每个时间步组装增广节点导纳矩阵和右端项。
8. 求解线性方程，得到节点电压和支路电流。
9. 更新电容、电感等动态元件的历史状态。
10. 记录当前时刻结果。
11. 如配置了事件队列，仿真器会按事件时间策略处理事件；默认把事件设定时间插入时间序列，在对应时间点前先执行故障投入、故障清除或断路器开合事件，并记录事件日志。
12. 显示结果图，并根据算例顶部保存标签决定是否保存数据和图像。

## 2. 算例代码结构约定

每个算例文件应按教学友好的顺序组织。短小基础算例可以采用直写结构：

```python
# 1. 保存标签
SAVE_RESULT_DATA = 0
SAVE_RESULT_FIGURE = 0

# 2. 仿真参数
TIME_STEP = ...
STOP_TIME = ...
INTEGRATION_METHOD = "trapezoidal"

# 3. 运行仿真
def main() -> None:
    # 用户在仿真前直接给定元件对象列表。
    components = [
        VoltageSource("V1", "src", "0", 1.0),
        Resistor("R1", "src", "out", 1000.0),
        Capacitor("C1", "out", "0", 1e-6),
    ]

    # 仿真程序读取元件对象并形成电路。
    circuit = Circuit.from_components("case_name", components)
    ...
```

当算例包含大量元件、多个运行场景、事件、控制器、参数扫描或复杂绘图时，应只把真正会变长、需要复用或需要单独测试的逻辑拆成函数：

```python
def create_components() -> list[Component]:
    """定义并返回本算例的元件对象列表。"""

    return [
        ThreePhaseSource(...),
        ThreePhaseLine(...),
        ThreePhaseLoad(...),
    ]


def plot_results(result: SimulationResult) -> None:
    """绘制并显示本算例关心的结果。"""

    plot_series(result, ["v:a", "v:b", "v:c"])


def main() -> None:
    components = create_components()
    circuit = Circuit.from_components("case_name", components)

    config = SimulationConfig(time_step=..., stop_time=...)
    simulator = Simulator(circuit, config)
    result = simulator.run()

    plot_results(result)
```

判断标准很直接：如果元件列表很短，直接写在 `main()` 中更适合教学；如果元件列表会明显拉长 `main()`，或需要被测试、复用、参数扫描、外部配置生成，就应拆成 `create_components()`。如果绘图逻辑较长，就拆成 `plot_results()`。

为了保持代码执行顺序清楚，不要把函数调用结果直接作为另一个函数的参数。应先求出函数返回值，再传给下一步。例如：

```python
components = create_components()
circuit = Circuit.from_components("case_name", components)

events = create_events()
simulator = Simulator(circuit, config, events=events)
result = simulator.run()
```

不要把 `create_components()` 直接写进 `Circuit.from_components()` 的参数里，也不要把 `create_events()` 直接写进 `Simulator()` 的参数里。这种显式写法更适合教学文档，也方便后续在中间插入检查、打印、参数扫描或事件调试逻辑。对象创建之后也应先形成实例变量，再调用方法；例如先写 `simulator = Simulator(circuit, config, events=events)`，再写 `result = simulator.run()`。

不要为了形式统一而封装只有一行、没有额外语义的函数。例如，如果 `build_circuit()` 只是 `return Circuit.from_components(...)`，或 `run_simulation()` 只是创建 `SimulationConfig`、创建 `Simulator` 并运行，直接写在 `main()` 中更好理解。只有当这些步骤包含事件初始化、checkpoint、日志、异常处理、批量运行或参数扫描等多步逻辑时，才建议拆成函数。

保存标签含义如下：

- `SAVE_RESULT_DATA = 0`：不保存 CSV、JSON、NPZ 数据。
- `SAVE_RESULT_DATA = 1`：保存 CSV、JSON、NPZ 数据。
- `SAVE_RESULT_FIGURE = 0`：不保存图像文件。
- `SAVE_RESULT_FIGURE = 1`：保存图像文件。

默认值必须都是 `0`。算例运行后仍然必须自动绘制并显示结果图。

普通教学算例放在 `examples/` 根目录。凡是复现 MATLAB/Simulink/Simscape 官方示例并读取参考数据进行误差对比的算例，必须放在 `examples/reproductions/` 目录；对应输出默认写入 `outputs/reproductions/<case_name>/`，参考数据由 `scripts/export_simscape_references.m` 统一导出。

当前算例统一使用 `examples._utils.run_components_case()` 承担常规 MNA 仿真的公共流程：由元件对象列表形成 `Circuit`，创建 `SimulationConfig`，创建 `Simulator` 并运行。复杂算例仍应先显式生成 `components`、`events` 等中间对象，再传入公共函数。对于不走 MNA 内核、而是手写控制器或平均模型时间循环的算例，应提供 `simulate_xxx()` 返回 `SimulationResult`。新增算例的完整编写流程见 `docs/new_simulation_workflow.md`。

`SimulationConfig` 的 `event_time_policy` 用于控制事件时间与基础步长不对齐时的处理方式：

- `"insert"`：默认策略，把事件时间插入时间序列，事件在设定时间精确执行。
- `"quantize_up"`：保持基础步点，事件在第一个不早于设定时间的时间点执行。
- `"require_aligned"`：要求事件时间与基础步长对齐，否则直接报错。

仿真器会始终把 `stop_time` 放入时间序列。若 `stop_time` 不是 `time_step` 的整数倍，最后一步会使用较短的实际步长推进动态元件状态。后续新增动态元件时，必须使用 `StampContext.time_step`，不能直接假设每一步都等于配置中的基础步长。

`SimulationConfig.start_time` 用于 checkpoint 续算。默认值为 `0.0`，表示从仿真初始时刻运行；当从 checkpoint 恢复时，应将 `start_time` 设置为 checkpoint 的 `current_time`，仿真器会从下一时间步继续推进，并跳过该时刻及之前已经发生的事件。

## 3. Circuit 如何形成电路对象

`Circuit` 是电路容器，用于保存元件和节点连接关系。推荐写法是先由用户直接定义元件对象列表，再由 `Circuit.from_components()` 自动形成电路：

```python
components = [
    VoltageSource("V1", "src", "0", 1.0),
    Resistor("R1", "src", "out", 1000.0),
    Capacitor("C1", "out", "0", 1e-6),
]
circuit = Circuit.from_components("rc_transient", components)
```

每个元件对象都包含名称、连接节点和参数值。例如 `Resistor("R1", "src", "out", 1000.0)` 表示名称为 `R1` 的电阻，连接在 `src` 和 `out` 两个节点之间，阻值为 `1000.0 Ω`。

基础教学算例不推荐把电路参数单独写成 `SOURCE_VOLTAGE`、`RESISTANCE` 这类常量后再引用。这样做在复杂元件较多时会产生大量分散常量，也会让读者在参数表和元件列表之间来回跳转。除非参数需要被多个元件共享、参与批量扫描或来自外部配置文件，否则应优先把参数直接写在对应元件对象中。

这里 `"0"` 是参考节点，也就是地节点。`"src"` 和 `"out"` 是普通节点，会在 MNA 方程中成为节点电压未知量。

调用 `Circuit.add()` 时，程序只是把元件保存进电路对象，并不会立刻求解。真正的节点编号和支路变量注册发生在仿真开始前的 `Circuit.prepare()`。

## 4. prepare 如何准备 MNA 变量

仿真器运行时会检查电路是否已经准备好。如果没有，就调用：

```python
circuit.prepare()
```

该过程分两步：

1. 遍历所有元件的 `nodes()`，收集非参考节点并编号。
2. 遍历所有元件的 `register()`，注册额外支路电流变量。

普通电阻、电容、电流源只需要节点电压变量。理想电压源和电感需要额外的支路电流变量。

因此 MNA 未知量向量结构为：

```text
x = [节点电压变量, 支路电流变量]
```

例如：

```text
x = [v:src, v:out, i:V1]
```

## 5. stamp 如何组装矩阵和右端项

每个时间步中，仿真器都会创建：

```text
A x = z
```

其中：

- `A` 是增广节点导纳矩阵。
- `x` 是未知量，包括节点电压和支路电流。
- `z` 是右端项，包括电流源、电压源给定值和动态元件历史项。

程序调用每个元件的 `stamp()` 方法，把局部元件模型写入全局矩阵。

电阻写入导纳，电流源写入右端项，电压源写入电压约束，电容和电感则先通过数值积分转换为当前时间步的等效模型，再写入矩阵和右端项。

## 6. 如何求解节点电压和支路电流

矩阵组装完成后，仿真器调用：

```python
solution = np.linalg.solve(matrix, rhs)
```

得到当前时刻的解向量。解向量前半部分是节点电压，后半部分是支路电流。

如果矩阵奇异，通常说明电路拓扑有问题，例如孤立节点、节点缺少到参考地的路径，或理想电压源构成冲突拓扑。

## 7. 如何更新支路状态

求解完成后，仿真器会调用每个元件的：

```python
component.update_state(context, solution)
```

静态元件通常不做任何事。动态元件会更新历史状态：

- 电容保存当前电压和电流，供下一时间步计算历史电流源。
- 电感保存当前电流和电压，供下一时间步计算历史电压源。

这一步是电磁暂态仿真能够逐步推进的关键。

## 8. 如何记录和显示结果

每个时间步求解后，仿真器会记录一行结果：

- `time`：当前时间。
- `v:节点名`：节点电压。
- `i:元件名`：元件电流。
- `v:元件名`：元件两端电压。

算例运行结束后，使用 `plot_series()` 显示结果图。例如：

```python
plot_series(result, ["v:out"])
```

如果算例顶部 `SAVE_RESULT_DATA = 1`，程序保存 CSV、JSON、NPZ 数据。如果 `SAVE_RESULT_FIGURE = 1`，程序保存图像文件。默认两者都是 `0`，即只显示图，不保存文件。

阶段 2 中，`SimulationResult` 还包含 `event_log`。事件日志会保存事件发生时间、事件类型、目标元件以及状态变化。JSON 和 NPZ 会保存事件日志；CSV 作为纯表格格式，只保存逐时间步数据。

三相结果字段采用 `v:母线:相别` 或 `i:元件:相别` 命名，例如：

```text
v:load:a
v:load:b
v:load:c
i:LINE:a
```

可使用 `plot_three_phase()` 绘制三相波形：

```python
from pycy_emt_lite.visualization import plot_three_phase

plot_three_phase(result, ("v:load:a", "v:load:b", "v:load:c"))
```

## 9. 推荐学习顺序

建议按以下顺序阅读和运行（示例编号即学习路径顺序）：

1. `examples/01_r_circuit.py`
2. `examples/02_rc_transient.py`
3. `examples/03_rl_transient.py`
4. `examples/04_rlc_transient.py`
5. `examples/05_three_phase_steady_state.py`
6. `examples/06_three_phase_short_circuit.py`
7. `examples/07_single_phase_ground_fault.py`
8. `examples/08_pi_line_transient.py`
9. `examples/09_single_phase_transformer.py`
10. `examples/10_park_generator_avr_governor.py`
11. `examples/11_pll_dynamic_response.py`
12. `examples/12_two_level_pwm_generator.py`
13. `examples/13_three_phase_grid_inverter_average.py`
14. `examples/14_pv_grid_following.py`
15. `examples/15_storage_grid_forming.py`
16. `examples/16_vsc_hvdc_average.py`

配套理论文档：

- `docs/theory/mna.md`
- `docs/theory/basic_components.md`
- `docs/theory/three_phase_systems.md`
- `docs/theory/control_systems.md`
- `docs/theory/power_electronics.md`
- `docs/theory/renewable_grid_models.md`
- `docs/theory/advanced_line_transformer_models.md`
- `docs/theory/stamp_principles.md`

进阶工程能力：

- `docs/visualization_reporting.md`

核心源码文件：

- `pycy_emt_lite/core/circuit.py`
- `pycy_emt_lite/core/simulation.py`
- `pycy_emt_lite/components/basic.py`
