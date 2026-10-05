# PyCy_EMT_Lite

[English](README.md) | 简体中文

PyCy_EMT_Lite 是小规模电磁暂态（EMT）仿真的纯 Python 教学项目：按很短的时间间隔计算电路中的电压和电流。
主流程为
`CaseDefinition → Circuit → Simulator → SimulationResult`。基础电路也可直接使用 `Circuit/Simulator`。
模型方程、验证证据和适用边界见[模型与验证](docs/models_and_validation.md)。
从物理方程到离散模型、矩阵盖章与历史更新的逐项推导见[元件推导](docs/component_derivations.md)，包含可运行的 RLC 矩阵核对例子。
当前范围用于教学与算法核对，不作为厂站级 EMT、保护整定、设备设计或运行决策工具。

## 1. 安装与运行

### 第一次运行（Windows）

1. 从[项目主页](https://github.com/yu-yikai/PyCy_EMT_Lite)选择 **Code → Download ZIP**，解压后打开同时包含 `pyproject.toml`、`README.md` 和 `examples` 的文件夹。这就是“项目根目录”；已有本地代码时直接打开该目录。
2. 在资源管理器地址栏输入 `powershell` 并按 Enter，打开位于该目录的终端。后面的命令都在这里运行，每条命令完成后再执行下一条。
3. 如未安装 [uv](https://docs.astral.sh/uv/getting-started/installation/)，在 PowerShell 中执行官方安装命令：

   ```powershell
   powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
   ```

   安装后关闭终端，再按第 2 步打开，运行 `uv --version`；能看到版本号即可继续。
4. 逐行执行以下命令：

```powershell
uv sync --locked
uv run python --version
uv run python examples/01_r_circuit.py
```

`uv sync --locked` 按 `uv.lock` 安装依赖，并创建项目专用的 `.venv` 环境。
项目要求 Python 3.14；缺少兼容版本时 uv 会自动下载，首次运行需要联网。版本检查应显示 `Python 3.14.x`。
以后运行脚本仍使用 `uv run python ...`，无需手动激活环境。macOS/Linux 用户按 uv 安装页完成安装后，在项目根目录使用同样的三条命令。

### 看到什么，怎样改一个参数

示例 01 把 10 V 电源接在 5 Ω 电阻两端。终端应出现以下摘要，图中电压和电流均为水平直线：

```text
节点 n1 电压：10.000000 V（解析值 10.000000 V）
电阻 R1 电流：2.000000 A（解析值 2.000000 A）
电源 V1 支路电流：-2.000000 A（负号表示电源向外供电）
```

先关闭电压图窗口，程序才会显示电流图；全部图窗关闭后，终端恢复输入提示符。
这里电流满足欧姆定律 `I = V/R = 10/5 = 2 A`。电源电流以流入其正端为正，所以供电时记为负值。

用文本编辑器打开 `examples/01_r_circuit.py`，把 `RESISTANCE = 5.0` 改成 `RESISTANCE = 10.0`，保存后重新运行同一条命令。
预期电压仍为 10 V，电阻电流变为 1 A，电源电流变为 −1 A。做完后恢复 5.0，再继续下一个例子。

依赖为 NumPy、SciPy、Matplotlib，测试使用 pytest；需要检查安装或修改后的行为时，可运行 `uv run pytest`。

Windows 若默认临时目录出现 `PermissionError`，可在项目根目录使用项目内临时目录复验：

```powershell
$env:UV_CACHE_DIR = "$PWD/.tmp/uv-cache"
$env:MPLBACKEND = "Agg"
uv run --locked pytest -o addopts= -q -p no:cacheprovider --basetemp=.tmp/pytest-local
```

运行前确认没有其他测试使用同一个 `--basetemp`；pytest 会清理该目录。本命令用于区分目录权限问题与代码失败。现有自动 CI 仍为 Linux，Windows 自动 CI 属于未来计划。

示例默认显示图形，不保存数据或图片。
网络算例需要保存时，把脚本顶部 `SAVE_RESULT_DATA` 或 `SAVE_RESULT_FIGURE` 改为 `1`；输出位于 `outputs/<算例名>/`。
独立 PLL 示例 11 只显示图形，没有保存开关。
非交互后端（如 `MPLBACKEND=Agg`）跳过窗口显示，仍可计算与保存。

遇到问题时先检查下面几项：

| 现象 | 检查与处理 |
|---|---|
| 提示找不到 `uv` | 完成安装后重新打开终端，先确认 `uv --version` 可运行。 |
| 找不到 `pyproject.toml` 或示例文件 | 回到同时包含 `pyproject.toml` 和 `examples` 的目录；不要在 ZIP 内或 `examples` 子目录运行。 |
| `ModuleNotFoundError: pycy_emt_lite` | 在项目根目录执行 `uv sync --locked`，再使用 `uv run python ...`。 |
| 已打印摘要但终端还不能输入 | 检查是否有图窗等待关闭；多幅图会依次显示。 |
| 没有图窗 | 若设置了 `MPLBACKEND=Agg`，会按设计跳过显示。需要图片时将对应示例的 `SAVE_RESULT_FIGURE` 改为 `1`。 |

## 2. 学习顺序

13 个基础脚本和 1 个综合示例组成九个学习单元。编号 13–16 的平均新能源/变流器及 HVDC/MMC 综合候选已移除，现有命令沿用原编号。
先完成 01，再学习 02、03 的储能过程，然后进入 04、17。能解释这些波形后，可阅读[元件推导](docs/component_derivations.md)第 1–5 节，核对一个完整 RLC 矩阵。电机、控制和 HVDC 可留到后面按需学习。

| 单元 | 脚本 | 学完后可以检查的事情 |
|---|---|---|
| R 与 MNA | [01](examples/01_r_circuit.py) | 沿对象式流程运行电路，用欧姆定律预测电流，解释电源电流方向；之后再读矩阵组装。 |
| 动态 RLC | [02 RC](examples/02_rc_transient.py)、[03 RL](examples/03_rl_transient.py)、[04 RLC](examples/04_rlc_transient.py)、[17 交流 RLC](examples/17_single_phase_ac_rlc.py) | 核对储能初值和时间常数，区分暂态与稳态相量，比较减小步长后的整段波形误差。 |
| 三相与故障 | [05](examples/05_three_phase_steady_state.py)、[06](examples/06_three_phase_short_circuit.py)、[07](examples/07_single_phase_ground_fault.py) | 观察平衡 RL、三相短路和单相接地；用固定时间窗比较故障相与健全相。 |
| 线路 | [08](examples/08_pi_line_transient.py) | 区分 π 型线路的串联电流和端部电容电流；再选读分段与 Bergeron 模型。 |
| 变压器 | [09](examples/09_single_phase_transformer.py) | 核对变比，观察漏阻抗和励磁的影响；三相接法见模型说明。 |
| 同步机 | [10](examples/10_park_generator_avr_governor.py) | 从平衡初值出发，观察负荷阶跃后电压和转速的变化，区分 AVR 与调速器的作用。 |
| 离散控制 | [11](examples/11_pll_dynamic_response.py) | 观察独立 SRF-PLL 控制循环的 q 轴电压和角频率，说明何时接近锁定。 |
| PWM | [12](examples/12_two_level_pwm_generator.py) | 对照理想开关的 SPWM 门极与 RL 电流，区分开关纹波和基波。 |
| VSC-HVDC 综合仿真 | [18](examples/18_three_terminal_vsc_hvdc.py) | 沿三个两电平桥、独立 PLL/dq 闭环和双极 DC 网络，跟踪交流故障后的电压、功率变化。 |

前四个示例可先做以下练习。每次只改一项、保存并重新运行，观察后恢复原值。脚本开头也有电路连接、预期现象和源码位置。

| 示例 | 默认结果的检查点 | 修改与预期 |
|---|---|---|
| 01 电阻 | 10 V、5 Ω，对应 2 A | `RESISTANCE` 从 `5.0` 改为 `10.0`：电流变为 1 A。 |
| 02 RC | `R*C = 1 ms`；电容电压从 0 V 开始，在 1 ms 时约 0.6321 V，5 ms 时约 0.9933 V | `CAPACITANCE` 从 `1e-6` 改为 `2e-6`：时间常数变为 2 ms，充电更慢；长期极限仍是 1 V。 |
| 03 RL | `L/R = 1 ms`；电感电流从 0 A 开始，在 1 ms 时约 0.06321 A，5 ms 时约 0.09933 A | `INDUCTANCE` 从 `10e-3` 改为 `20e-3`：时间常数变为 2 ms，电流建立更慢；长期极限仍是 0.1 A。 |
| 04 RLC | 电容电压先超过 1 V，再振荡衰减并接近 1 V | `RESISTANCE` 从 `20.0` 改为 `40.0`：第一处电压峰值降低。改成 `100.0` 后仍可绘图，摘要提示跳过欠阻尼解析对比。 |

这里的“长期极限”不等于脚本停止时已经达到的数值。改变参数后，原有仿真时长可能只覆盖部分暂态。

读代码时先认清这些写法：

| 写法 | 在本项目中的含义 |
|---|---|
| `import` / `from ... import ...` | 引入要使用的元件或函数。 |
| `Resistor("R1", "n1", "0", 5.0)` | 创建一个电阻对象：名称 R1、连接节点 n1 和 0、阻值 5 Ω。相同节点名表示导线相连，`"0"` 是参考地。 |
| `1e-6`、`10e-3` | 分别是 0.000001、0.01；元件参数使用 F、H、Ω，时间使用 s。 |
| `def define_case()` / `define_case()` | 前者定义函数，后者调用函数来创建一份新算例。 |
| `result: SimulationResult` / `-> None` | 类型提示，说明参数或返回值的类型；`-> None` 表示函数不返回计算结果。 |
| `CaseDefinition` / `run_case(case)` | 前者保存元件和设置；后者创建电路、运行仿真并处理输出。第一次阅读时可先关注元件参数与仿真设置。 |
| `result.series("i:R1")[-1]` | 读取 R1 的全部电流采样，再取最后一个值；`result.series("time")` 给出对应时刻。 |
| MNA / `stamp()` | MNA 是改进节点分析法；`stamp()` 把每个元件的方程写入共同的矩阵，详见元件推导。 |

运行 `uv run python examples/18_three_terminal_vsc_hvdc.py`，默认 FAST 为 20 μs、0.8 s。
修改脚本顶部 `MODE` 可选择 `FULL`（5 μs）或 `BENCHMARK`（2 μs），两者均运行 2.5 s。
[完整说明](docs/three_terminal_vsc_hvdc.md) 给出来源映射、参数、验证和模型调整，包括故障清除 RC 缓冲支路。

示例 17 为 220 V RMS、50 Hz 电源串联 20 Ω、50 mH、100 μF，电压和电流分图；
默认用 0.08–0.12 s 稳态窗口核对相量。修改频率或阻尼后需重新选取窗口。
示例 10 保留四阶同步发电机，从平衡点开始，在 0.2 s 投入负荷，分别显示电压/励磁、转速和功率。
经典同步机也保留，二者模型层级不同。示例 11 的 `explicit_control` 标签说明其显式控制循环，不是 EMT 积分方法选项。

## 3. 编写自己的算例

将以下代码保存为项目根目录下的 `my_r_circuit.py`（扩展名为 `.py`），运行 `uv run python my_r_circuit.py`。
参数在元件旁定义，电压与电流分别绘图。

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

将下面代码追加到同一个 `my_r_circuit.py` 文件末尾，再运行脚本。它使用上面生成的 `result`，显式保存 JSON 并读回对照：

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
                      summary={"Voltage RMS / V": voltage_rms}, figure_paths=["outputs/my_r_circuit/zoom.png"])
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
| [元件推导](docs/component_derivations.md) | 各元件物理方程、TR/BE 离散式、局部 MNA 矩阵、历史更新与完整 EMT 循环 |
| [模型与验证](docs/models_and_validation.md) | 保留模型方程、算例参数、验证证据及未验证范围 |
| [三端 VSC-HVDC](docs/three_terminal_vsc_hvdc.md) | 参考映射、开关网络、闭环控制、模式、故障与验证 |

顶层保留 `CaseDefinition`、`Circuit`、`Simulator`、`SimulationResult`，基础 RLC/独立源、开关/故障/事件、
三相源/线路/负荷、π 线路和单相变压器。具体导出见[顶层接口](pycy_emt_lite/__init__.py)。
同步机从 `pycy_emt_lite.machines` 导入，L/LC/LCL 从 `pycy_emt_lite.converters` 导入，
分段/Bergeron/三相 π 线路及三相变压器从相应 `components` 模块导入。
控制、分析、绘图使用各自子包；子包可导入不等于已完成全部物理验证。

`pycy_emt_lite/` 放实现，`examples/` 放案例，`tests/` 放回归，`docs/` 放上述四项专题的完整双语版本。
新增元件需说明物理方程、离散式、单位/方向、初值/事件行为，并增加解析、守恒或独立参考检查。
新增案例更新学习表即可；避免仅为组织形式增加包装层、依赖或入口。
文档中的仓库文件链接使用相对路径，运行与输出路径以项目根目录为基准；外部参考资料提供公开来源链接和文件名，不写个人绝对路径或临时验证目录。

PyCy_EMT_Lite 源自 PyCy_EMT v0.6 的对象式工作流，保留适合小规模教学的内容。[MIT 许可证](LICENSE)。
