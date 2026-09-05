# PyCy_EMT_Lite 用户指南

[English](user_guide.en.md)

本文说明如何安装、运行示例、编写算例和运行测试。

## 1. 环境要求

- Python 3.14
- [uv](https://docs.astral.sh/uv/) 包管理器（推荐）

## 2. 安装依赖

在项目根目录执行：

```bash
uv sync
```

首次运行会自动创建虚拟环境并安装 numpy、scipy、matplotlib 等依赖。

## 3. 运行示例

所有示例位于 `examples/` 目录，按学习路径编号：

```bash
uv run python examples/01_r_circuit.py
uv run python examples/04_rlc_transient.py
uv run python examples/16_vsc_hvdc_average.py
```

每个示例运行后会自动绘制并显示结果波形（无显示环境下自动跳过窗口显示，
不影响计算和保存）。示例默认不保存结果数据和图像文件；如需保存，把算例
代码顶部的 `SAVE_RESULT_DATA`、`SAVE_RESULT_FIGURE` 标签改为 `1` 即可。

## 4. 运行测试

```bash
uv run pytest
```

测试覆盖基础元件、三相系统、事件、线路、变压器、同步机、控制、新能源、
结果读写、求解器和可视化等全部核心功能。

## 5. 编写自己的算例

推荐流程见 [new_simulation_workflow.md](new_simulation_workflow.md)。

最小算例：

```python
from pycy_emt_lite import Resistor, SimulationConfig, VoltageSource
from pycy_emt_lite.cases import CaseDefinition, OutputOptions, PlotSpec, run_case

SAVE_RESULT_DATA = 0
SAVE_RESULT_FIGURE = 0

def main() -> None:
    components = (
        VoltageSource("V1", "n1", "0", 10.0),
        Resistor("R1", "n1", "0", 5.0),
    )
    config = SimulationConfig(time_step=1e-4, stop_time=1e-3, method="trapezoidal")
    plots = (PlotSpec(columns=("v:n1", "i:R1"), title="R 电路电压与电流"),)
    case = CaseDefinition(
        name="r_circuit",
        components=components,
        config=config,
        plots=plots,
        output=OutputOptions(
            save_data=bool(SAVE_RESULT_DATA),
            save_figure=bool(SAVE_RESULT_FIGURE),
        ),
    )
    run_case(case)

if __name__ == "__main__":
    main()
```

## 6. 结果对象

`run_case()` 返回 `SimulationResult`，支持：

- `result.series("v:out")`：读取某一列数据（NumPy 数组）。
- `result.to_csv(path)` / `to_json(path)` / `to_npz(path)`：保存结果。
- `SimulationResult.from_json(path)` 等：读回结果。

分析函数见 `pycy_emt_lite.analysis`（RMS、峰值、三相功率、电压跌落等），
绘图函数见 `pycy_emt_lite.visualization`。

## 7. 常见问题

- **无显示环境运行示例**：matplotlib 使用非交互后端时自动跳过 `plt.show()`，不影响运行。
- **矩阵奇异报错**：检查电路是否存在孤立节点，或理想电压源/变压器绕组是否缺少
  到参考地的路径。
- **数值发散**：减小仿真步长，或检查动态元件参数是否合理（如电容过小、电感过大）。
