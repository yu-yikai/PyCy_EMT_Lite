# 新增仿真算例统一编写流程

PyCy_EMT_Lite 的所有算例都遵循同一条流程：

```text
定义元件对象列表 -> 形成电路 -> 配置仿真 -> 定义绘图 -> run_case() 运行
```

核心原则：先形成 `case = define_case()`，再调用 `run_case(case)`；不要写成
`run_case(define_case())`。显式命名中间结果让教学代码的执行顺序清晰可读。

## 1. 标准模板

每个算例提供 `define_case() -> CaseDefinition` 和 `main()` 两步写法：

```python
from pycy_emt_lite import Resistor, SimulationConfig, VoltageSource
from pycy_emt_lite.cases import CaseDefinition, OutputOptions, PlotSpec, run_case

SAVE_RESULT_DATA = 0
SAVE_RESULT_FIGURE = 0
SHOW_FIGURE = True


def define_case() -> CaseDefinition:
    """定义 R 电路算例。"""

    components = (
        VoltageSource("V1", "n1", "0", 10.0),
        Resistor("R1", "n1", "0", 5.0),
    )

    config = SimulationConfig(
        time_step=1e-4,
        stop_time=1e-3,
        method="trapezoidal",
    )

    plots = (
        PlotSpec(
            columns=("v:n1", "i:R1"),
            title="R 电路电压与电流",
        ),
    )

    output = OutputOptions(
        save_data=bool(SAVE_RESULT_DATA),
        save_figure=bool(SAVE_RESULT_FIGURE),
        show_figure=SHOW_FIGURE,
    )

    return CaseDefinition(
        name="r_circuit",
        components=components,
        config=config,
        plots=plots,
        output=output,
    )


def main() -> None:
    """按统一算例流程运行仿真。"""

    case = define_case()
    run_case(case)


if __name__ == "__main__":
    main()
```

## 2. 元件与节点

- 元件构造参数直接写在对应元件对象中，例如 `Resistor("R1", "n1", "0", 5.0)`：
  名称、正端节点、负端节点、参数值。
- 参考节点通常写 `"0"`；三相节点用 `phase_node("bus", "a")` 形式（或直接写
  `"bus:a"`）。
- 元件名称必须唯一，否则结果字段会互相覆盖。

## 3. 动态元件与事件

- 电容 `Capacitor(name, p, n, capacitance, initial_voltage)`，电感
  `Inductor(name, p, n, inductance)`；积分方法在 `SimulationConfig.method` 选择
  `"trapezoidal"` 或 `"backward_euler"`。
- 事件对象传入 `CaseDefinition(events=...)`，例如 `FaultApplyEvent(0.04, "FA")`、
  `BreakerOpenEvent(0.1, "BRK")`。事件默认在精确设定时间插入时间序列执行。

## 4. 复杂算例的拆分

短小基础算例直接在 `main()` 中定义元件列表。三相故障、电力电子、新能源、
HVDC 等复杂算例应拆出真正有内容、便于复用的函数，例如 `define_case()`、
`print_summary()`、控制循环等；只有一行且没有额外语义的 `build_circuit()` 不要
单独封装。

## 5. 控制级仿真

新能源、构网、HVDC 等平均模型算例（如 `examples/13`～`16`）不使用 MNA 网络
求解，而是在脚本中显式编写控制循环：每个时间步内依次调用控制对象的 `step()`
方法，再把结果收集为 `SimulationResult` 行用于绘图。这种写法直接展示"网络
求解器 + 离散控制器"在每个步长内的交互，是理解新型电力系统仿真的关键。

## 6. 组织规则

- 算例文件之间互相独立，不互相导入；通用工具才放入公共模块。
- 参数就近书写，不拆成大量分散常量。
- 新增元件时同步更新 `docs/theory/stamp_principles.md`。
- 新增算例时在 README 学习路径表中补充说明。
