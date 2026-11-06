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
New-Item -ItemType Directory -Force -Path .tmp | Out-Null
$env:UV_CACHE_DIR = "$PWD/.tmp/uv-cache"
$env:MPLBACKEND = "Agg"
uv run --locked pytest -o addopts= -q -p no:cacheprovider --basetemp=.tmp/pytest-local
```

先显式创建 `.tmp`，避免干净下载的项目缺少 `--basetemp` 的父目录。运行前确认没有其他测试使用同一个 `--basetemp`；pytest 会清理该目录。本命令用于区分目录权限问题与代码失败。CI 已配置 Linux 和 Windows；本地检查见第 6 节。

示例默认显示图形，不保存数据或图片。
网络算例需要保存时，把脚本顶部 `SAVE_RESULT_DATA` 或 `SAVE_RESULT_FIGURE` 改为 `1`；输出位于 `outputs/<算例名>/`。
开启相应保存选项后，相同输出根目录下再次运行同名算例，会替换前次同名的数据文件（`result.csv`、`result.json`、`result.npz`）或图片。需要对照时，先复制旧结果或更换算例名，再运行。
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

基础脚本和综合示例组成以下学习单元。编号 13–16 的平均新能源/变流器及 HVDC/MMC 综合候选已移除，现有命令沿用原编号。
先完成 01，再学习 02、03 的储能过程，然后进入 04、17。能解释这些波形后，可阅读[元件推导](docs/component_derivations.md)第 1–5 节，核对一个完整 RLC 矩阵。电机、控制和 HVDC 可留到后面按需学习。

| 单元 | 脚本 | 学完后可以检查的事情 |
|---|---|---|
| R 与 MNA | [01](examples/01_r_circuit.py) | 沿对象式流程运行电路，用欧姆定律预测电流，解释电源电流方向；之后再读矩阵组装。 |
| 多源多节点 | [20](examples/20_multi_source_nodal_network.py) | 在01之后检查七电阻网络的KCL、负节点电压和电压源吸收功率；附[真实Simscape对标](validation/cases/nodal_analysis/README.md)。 |
| 动态 RLC | [02 RC](examples/02_rc_transient.py)、[03 RL](examples/03_rl_transient.py)、[04 RLC](examples/04_rlc_transient.py)、[17 交流 RLC](examples/17_single_phase_ac_rlc.py) | 核对储能初值和时间常数，区分暂态与稳态相量，比较减小步长后的整段波形误差。 |
| 耦合 RC | [19](examples/19_cascaded_rc.py) | 在02之后学习后级负载如何影响前级，以及源下降后后级为何还能短时充电。 |
| 三相与故障 | [05](examples/05_three_phase_steady_state.py)、[06](examples/06_three_phase_short_circuit.py)、[07](examples/07_single_phase_ground_fault.py) | 观察平衡 RL、三相短路和单相接地；用固定时间窗比较故障相与健全相。 |
| 中性点与不平衡 | [21](examples/21_earthing_neutral.py) | 在05之后比较接地/浮动星点、负荷相电压和回线电流；附[真实Simscape对标](validation/cases/earthing/README.md)。 |
| 线路 | [08](examples/08_pi_line_transient.py) | 区分 π 型线路的串联电流和端部电容电流；再选读分段与 Bergeron 模型。 |
| 有限梯级传播 | [22](examples/22_t_section_transmission_line.py) | 在08与17之后学习50T梯级的启动与色散；结合[真实参考和独立状态验证](validation/cases/transmission_line/README.md)区分有限梯级与纯延时。 |
| 变压器 | [09](examples/09_single_phase_transformer.py) | 核对变比，观察漏阻抗和励磁的影响；三相接法见模型说明。 |
| 变压器T等效 | [23](examples/23_transformer_t_equivalent.py) | 在03和09之后学习漏感后的励磁支路、电流连续、双时间常数与能量；附[真实参考及复现说明](validation/cases/transformer_t_equivalent/README.md)。 |
| 三相变压器链 | [24](examples/24_three_phase_transformer_chain.py) | 在09和21之后区分线量/绕组量、浮动星点与Δ参考点，观察中间相移及快速启动；附[真实对标与原步长失败记录](validation/cases/three_phase_transformer_chain/README.md)。 |
| 电源、线路、变压器与负荷 | [25](examples/25_source_line_transformer_network.py) | 在08、17和23之后学习完整网络的正弦稳态初始化、充电和补偿导致的电流差，并核实际负荷功率及损耗；附[接线、初值与验证说明](validation/cases/source_line_transformer/README.md)。 |
| 同步机 | [10](examples/10_park_generator_avr_governor.py) | 从平衡初值出发，观察负荷阶跃后电压和转速的变化，区分 AVR 与调速器的作用。 |
| 离散控制 | [11](examples/11_pll_dynamic_response.py) | 观察独立 SRF-PLL 控制循环的 q 轴电压和角频率，说明何时接近锁定。 |
| PWM | [12](examples/12_two_level_pwm_generator.py) | 对照理想开关的 SPWM 门极与 RL 电流，区分开关纹波和基波；[真实参考研究](validation/cases/two_level_pwm/README.md)保留尚未通过的波形判据。 |
| VSC-HVDC 综合仿真 | [18](examples/18_three_terminal_vsc_hvdc.py) | 沿三个两电平桥、独立 PLL/dq 闭环和双极 DC 网络，跟踪交流故障后的电压、功率变化。 |

[19级联RC真实Simscape对标](validation/cases/cascaded_rc/README.md)给出参数、固定验收、结果和复现命令。教学程序只绘制自身波形，独立验证程序读取真实参考。
[既有02 RC充电算例](validation/cases/rc_charging/README.md)也已补充可复现的Simscape对比。

从 12 进入 18 前，可沿[现有 HVDC 测试模块](tests/test_three_terminal_vsc_hvdc.py)逐步阅读：
`test_single_bridge_open_loop_power_identity` 核对单桥开环功率账；
`test_single_station_pll_and_dq_tracking_with_step_refinement` 加入单站 PLL/dq 闭环；
`test_two_station_intermediate_dc_exchange` 连接双站 DC 网络；
最后看 `test_three_terminal_vsc_hvdc_fast_run` 的完整 FAST 网络。后三项标记为 `slow`。
先用专用临时目录运行较小的单桥开环测试：

```powershell
New-Item -ItemType Directory -Force -Path .tmp | Out-Null
$env:MPLBACKEND = "Agg"
uv run --locked pytest tests/test_three_terminal_vsc_hvdc.py::test_single_bridge_open_loop_power_identity --basetemp=.tmp/pytest-vsc-bridge
```

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
    config = SimulationConfig(time_step=1e-4, stop_time=1e-3, linear_solver_mode="rebuild")
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

第一次调试可在 `define_case()` 创建 `CaseDefinition` 处停下，核对元件与步长。
在 [Simulator](pycy_emt_lite/core/simulation.py) 的 `_assemble` 结束处观察 `matrix`（A）与 `rhs`（b），再在 `_solve_step` 返回前将 `solution`（x）与电路的节点/支路映射对应起来。
在 [Capacitor/Inductor.update_state](pycy_emt_lite/components/basic.py) 写回前后比较 `previous_voltage` 与 `previous_current`，这些历史量会进入下一步的 companion 方程。
`on_step(row)` 在状态更新后读取刚求解的测量，事件点读取右侧值。VSC 控制器在 t=0 只初始化，随后产生下一步使用的保持调制量；其 `m*` 字段表示刚用过的参考，`m*_next` 表示新命令，见 [VSCController.sample](pycy_emt_lite/controls/vsc.py)。

每次运行重新创建元件、`Circuit` 和 `Simulator`；重新调用 `define_case()` 可得到新元件。
同一 `CaseDefinition` 内的元件也不能重复运行。只支持 `start_time=0`；`stop_time` 必须是基础步长的非负整数倍。
例如 100 μs 步长不能终止于 250 μs，可改为 200/300 μs 或使用 50 μs 步长。
初值、源导数和事件规则见[数值约定](docs/numerical_conventions.md)。

仿真前用 `linear_solver_mode` 选择网络求解策略：默认 `"rebuild"` 每次重新 LU 分解；
把上面配置改成 `"reuse"`，只在实际系数矩阵改变时重新分解，其余求解复用上一份 LU。
每步仍装配矩阵/右端项、执行状态更新和数值保护；步长、参数或电机状态变化也可能使 LU 失效。
第三种 `"precompute"` 仅用于开关少、完整状态集合小且满足预算的网络，在时间循环前预分解有限状态和全部实际步长的矩阵，循环中只查表求解。
含大量开关器件的网络不采用预计算，选择 `"rebuild"` 或 `"reuse"`。
目前支持固定参数的 Resistor/Capacitor/Inductor、CurrentSource/VoltageSource、Fault/Breaker/IdealSwitch，
以及 ThreePhaseSource、ThreePhaseLine 和不含饱和的 ThreePhaseTransformer；其他组合模型和电机尚未接入。
默认自动枚举二值状态，最多 1024 种；也可用 `precompute_states` 声明完整有效集合。
未声明状态、系数矩阵改变、奇异或超限会报错，详见[预计算规则与示例](docs/numerical_conventions.md#network-precompute)。
网络策略独立于 BE/梯形积分 `method`；预计算增加启动成本和内存，不保证所有算例都会加速。
HVDC 示例含 18 个桥臂开关，仅允许 rebuild/reuse；选择 precompute 会在创建控制器和网络前报错，所有 MODE 及无故障运行均适用，见[HVDC策略范围](docs/three_terminal_vsc_hvdc.md#network-solver-scope)。
N4 本机三次交错测量中，reuse 虽减少 FAST 的 LU 次数约31.45%，但默认及保存完整流程均未核定稳定加速；小网络预计算也需计入准备成本。
默认仍为 rebuild；时间、峰值工作集及测量范围见[成本验收记录](docs/audit_20261005/项目问题与改进计划.md#network-solver-n4)。

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
| [长期开发路线](docs/development_roadmap/04_long_term_roadmap.md) | 实测优先级、参考目录、任务状态和恢复指令 |
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

## 6. 开发检查

执行 `uv sync --locked` 后，在项目根目录运行：

```powershell
New-Item -ItemType Directory -Force -Path .tmp | Out-Null
$env:MPLBACKEND = "Agg"
$env:OPENBLAS_NUM_THREADS = "1"
uv run --locked ruff check pycy_emt_lite examples tests validation
uv run --locked mypy
uv run --locked pytest -m "not slow" --basetemp=.tmp/pytest-fast
uv run --locked pytest -m slow --basetemp=.tmp/pytest-slow
uv run --locked pytest -p pytest_cov --basetemp=.tmp/pytest-coverage --cov --cov-report=term-missing --cov-report=xml:.tmp/coverage.xml --cov-report=html:.tmp/htmlcov
```

第一条 pytest 命令用于快速反馈；`slow` 包含耗时的 PWM 步长比较、HVDC 控制仿真及所有共用完整 FAST 仿真的测试。普通 pytest 和 CI 仍执行全量测试。标记严格检查，拼写错误会报错。

Ruff 检查错误、导入顺序、现代化写法和选定缺陷规则，不强制格式化或行宽。mypy 依据已有标注检查 39 个包源码模块，不要求所有函数都有标注，也不完整检查未标注函数体。数组协议使用 NumPy 类型，允许第三方缺失类型存根。`py.typed` 使安装后的包继续携带这些标注。

覆盖率包含分支。打开 `.tmp/htmlcov/index.html` 查看未执行的代码行和分支；当前不设覆盖率百分比阈值。覆盖率和测试通过只说明被验证的行为，物理精度仍需[模型与验证](docs/models_and_validation.md)中的检查。

[CI 配置](.github/workflows/ci.yml)定义 Linux 和 Windows 两项任务：任务超时 40 分钟，测试步骤 25 分钟，示例步骤 10 分钟。两项任务均锁定环境，执行上述检查、全部示例、构建发行包，并在源码目录外验证安装 wheel 的版本及 `py.typed`。JUnit、覆盖率 XML 和 HTML 以 `test-coverage-Linux`、`test-coverage-Windows` 上传，保留 14 天。本地通过不代表远端 Actions 已运行成功。

`pyproject.toml`、`uv.lock` 与 `pycy_emt_lite.__version__` 的版本必须一致。版本变更记入[CHANGELOG](CHANGELOG.md)；修改版本不会自动发布。
