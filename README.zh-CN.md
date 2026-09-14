# PyCy_EMT_Lite

[English](README.md) | 简体中文

PyCy_EMT_Lite 是小规模电磁暂态仿真的纯 Python 教学项目，主流程为
`CaseDefinition → Circuit → Simulator → SimulationResult`。基础电路也可直接使用 `Circuit/Simulator`。
模型方程、验证证据和适用边界见[模型与验证](docs/models_and_validation.md)。
当前范围用于教学与算法核对，不作为厂站级 EMT、保护整定、设备设计或运行决策工具。

## 1. 安装与运行

在项目根目录使用 Python 3.14 和 [uv](https://docs.astral.sh/uv/)：

```bash
uv sync --locked
uv run python examples/01_r_circuit.py
uv run pytest
```

依赖为 NumPy、SciPy、Matplotlib，测试使用 pytest。示例默认显示图形，不保存数据或图片。
网络算例需要保存时，把脚本顶部 `SAVE_RESULT_DATA` 或 `SAVE_RESULT_FIGURE` 改为 `1`；输出位于 `outputs/<算例名>/`。
独立 PLL 示例 11 只显示图形，没有保存开关。
非交互后端（如 `MPLBACKEND=Agg`）跳过窗口显示，仍可计算与保存。

## 2. 学习顺序

13 个基础脚本和 1 个综合示例组成九个学习单元。编号 13–16 的平均新能源/变流器及 HVDC/MMC 综合候选已移除，现有命令沿用原编号。

| 单元 | 脚本 | 内容 |
|---|---|---|
| R 与 MNA | [01](examples/01_r_circuit.py) | 对象式流程、欧姆定律和电源电流方向 |
| 动态 RLC | [02 RC](examples/02_rc_transient.py)、[03 RL](examples/03_rl_transient.py)、[04 RLC](examples/04_rlc_transient.py)、[17 交流 RLC](examples/17_single_phase_ac_rlc.py) | 初值、时间常数、储能、相量与步长误差 |
| 三相与故障 | [05](examples/05_three_phase_steady_state.py)、[06](examples/06_three_phase_short_circuit.py)、[07](examples/07_single_phase_ground_fault.py) | 平衡 RL、三相短路、单相接地及固定窗口指标 |
| 线路 | [08](examples/08_pi_line_transient.py) | π 型线路；分段与 Bergeron 模型可作为对照 |
| 变压器 | [09](examples/09_single_phase_transformer.py) | 变比、漏阻抗、励磁；三相接法见模型说明 |
| 同步机 | [10](examples/10_park_generator_avr_governor.py) | 平衡初值、负荷阶跃、AVR 和调速器 |
| 离散控制 | [11](examples/11_pll_dynamic_response.py) | SRF-PLL，独立控制循环 |
| PWM | [12](examples/12_two_level_pwm_generator.py) | 理想开关、SPWM 和 RL 电流 |
| VSC-HVDC 综合仿真 | [18](examples/18_three_terminal_vsc_hvdc.py) | 三个两电平桥、独立 PLL/dq 闭环、双极 DC 网络和交流故障 |

运行 `uv run python examples/18_three_terminal_vsc_hvdc.py`，默认 FAST 为 20 μs、0.8 s。
修改脚本顶部 `MODE` 可选择 `FULL`（5 μs）或 `BENCHMARK`（2 μs），两者均运行 2.5 s。
[完整说明](docs/three_terminal_vsc_hvdc.md) 给出来源映射、参数、验证和模型调整，包括故障清除 RC 缓冲支路。

示例 17 为 220 V RMS、50 Hz 电源串联 20 Ω、50 mH、100 μF，电压和电流分图；
默认用 0.08–0.12 s 稳态窗口核对相量。修改频率或阻尼后需重新选取窗口。
示例 10 保留四阶同步发电机，从平衡点开始，在 0.2 s 投入负荷，分别显示电压/励磁、转速和功率。
经典同步机也保留，二者模型层级不同。示例 11 的 `explicit_control` 标签说明其显式控制循环，不是 EMT 积分方法选项。

## 3. 编写自己的算例

以下保存为 Python 脚本即可运行；参数在元件旁定义，电压与电流分别绘图。

```python
from pycy_emt_lite import Resistor, SimulationConfig, VoltageSource
from pycy_emt_lite.cases import CaseDefinition, OutputOptions, PlotSpec, run_case

SAVE_RESULT_DATA = 0
SAVE_RESULT_FIGURE = 0

def define_case() -> CaseDefinition:
    components = (
        VoltageSource("V1", "n1", "0", 10.0),
        Resistor("R1", "n1", "0", 5.0),
    )
    config = SimulationConfig(time_step=1e-4, stop_time=1e-3)
    plots = (
        PlotSpec(("v:n1",), figure_name="voltage.png", title="Voltage / V"),
        PlotSpec(("i:R1",), figure_name="current.png", title="Current / A"),
    )
    output = OutputOptions(save_data=bool(SAVE_RESULT_DATA),
                           save_figure=bool(SAVE_RESULT_FIGURE), show_figure=True)
    return CaseDefinition("my_r_circuit", components, config, plots=plots, output=output)

if __name__ == "__main__":
    case = define_case()
    result = run_case(case)
```

长算例可把摘要放入 `CaseDefinition.summary`，事件放入 `events`，三相图用 `PlotSpec(kind="three_phase")` 并提供三个字段。
保存图像时，每个 `PlotSpec` 必须有 `figure_name`。只有真正变长或需要复用的逻辑才拆成函数；示例之间不互相导入。
先形成 `case`、`circuit`、`simulator` 等中间对象，再运行下一步，方便阅读和调试。

每次运行重新创建元件、`Circuit` 和 `Simulator`；重新调用 `define_case()` 可得到新元件。
同一 `CaseDefinition` 内的元件也不能重复运行。只支持 `start_time=0`；`stop_time` 必须是基础步长的非负整数倍。
例如 100 μs 步长不能终止于 250 μs，可改为 200/300 μs 或使用 50 μs 步长。
初值、源导数和事件规则见[数值约定](docs/numerical_conventions.md)。

## 4. 读取、绘图与保存结果

`result.columns` 列出字段；`result.series("v:n1")` 返回 NumPy 数组。节点电压为 `v:<节点>`，
普通支路电流为 `i:<元件>`，三相与组合件字段见模型说明。节点电压相对参考地；电源供出电流与其支路电流方向相反。

下面代码接续上一段的 `result`，显式保存 JSON 并读回对照：

```python
from pycy_emt_lite import SimulationResult
from pycy_emt_lite.analysis import rms
from pycy_emt_lite.visualization import plot_result_comparison, plot_zoom_window, write_markdown_report

voltage_rms = rms(result, "v:n1", start_time=0.0, end_time=1e-3)
result.to_json("outputs/my_r_circuit/result.json")
loaded = SimulationResult.from_json("outputs/my_r_circuit/result.json")
plot_result_comparison([result, loaded], "v:n1", labels=["original", "loaded"], show=False)
plot_zoom_window(result, ["v:n1"], 0.0, 5e-4,
                 output_path="outputs/my_r_circuit/zoom.png", show=False)
write_markdown_report(result, "outputs/my_r_circuit/report.md",
                      summary={"Voltage RMS / V": voltage_rms}, figure_paths=["zoom.png"])
```

同样支持 `to_csv/from_csv`、`to_npz/from_npz`。JSON/NPZ 保留元数据与 `event_log`；CSV 只保存表格，
读回时需补充算例名/方法，推断的首区间长度不一定等于原基础步长。读取文件不会恢复可续算的仿真状态。
绘图还包括 `plot_series`、`plot_three_phase`；`output_path` 可使用 PNG/SVG/PDF 等后缀。
报告只整理现有结果和用户提供的摘要，不自动证明模型正确。
RMS、均值、三相功率、采样峰值和跌落统计的窗口/方向规则见[数值约定](docs/numerical_conventions.md)。

## 5. 文档与源码

| 文档 | 内容 |
|---|---|
| 本 README | 安装、学习顺序、编写算例、结果操作 |
| [数值约定](docs/numerical_conventions.md) | MNA/stamp、单位、初值、时间、事件、指标和错误诊断 |
| [模型与验证](docs/models_and_validation.md) | 保留模型方程、算例参数、验证证据及未验证范围 |
| [三端 VSC-HVDC](docs/three_terminal_vsc_hvdc.md) | 参考映射、开关网络、闭环控制、模式、故障与验证 |

顶层保留 `CaseDefinition`、`Circuit`、`Simulator`、`SimulationResult`，基础 RLC/独立源、开关/故障/事件、
三相源/线路/负荷、π 线路和单相变压器。具体导出见[顶层接口](pycy_emt_lite/__init__.py)。
同步机从 `pycy_emt_lite.machines` 导入，L/LC/LCL 从 `pycy_emt_lite.converters` 导入，
分段/Bergeron/三相 π 线路及三相变压器从相应 `components` 模块导入。
控制、分析、绘图使用各自子包；子包可导入不等于已完成全部物理验证。

`pycy_emt_lite/` 放实现，`examples/` 放案例，`tests/` 放回归，`docs/` 放上述三项专题的完整双语版本。
新增元件需说明物理方程、离散式、单位/方向、初值/事件行为，并增加解析、守恒或独立参考检查。
新增案例更新学习表即可；避免仅为组织形式增加包装层、依赖或入口。
文档中的仓库文件链接使用相对路径，运行与输出路径以项目根目录为基准；外部参考资料提供公开来源链接和文件名，不写个人绝对路径或临时验证目录。

PyCy_EMT_Lite 源自 PyCy_EMT v0.6 的对象式工作流，保留适合小规模教学的内容。[MIT 许可证](LICENSE)。
