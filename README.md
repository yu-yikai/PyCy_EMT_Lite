# PyCy_EMT_Lite

PyCy_EMT_Lite 是一个面向新型电力系统电磁暂态仿真的 **Python 教学项目**，是 PyCy_EMT
的精简易用版。它只保留一条清晰的主线：

```text
定义元件对象列表 -> 形成电路 -> 配置仿真 -> 运行 -> 绘图
```

没有 YAML 配置、没有多套并行接口、没有架构专项文档——把注意力集中在"电磁暂态
仿真的原理与程序实现"本身。

## 快速开始

```bash
uv sync                      # 安装依赖（首次运行）
uv run python examples/01_r_circuit.py          # 运行第一个算例
uv run pytest                # 运行全部测试
```

也可以一次运行完整学习路径：

```bash
uv run python examples/04_rlc_transient.py      # RLC 二阶暂态
uv run python examples/06_three_phase_short_circuit.py   # 三相短路
uv run python examples/10_park_generator_avr_governor.py # 同步机
uv run python examples/16_vsc_hvdc_average.py   # VSC-HVDC 平均模型
```

## 一个算例长什么样

以 `examples/01_r_circuit.py` 为例，一个算例就是"元件对象 -> 算例定义 -> 运行"三步：

```python
from pycy_emt_lite import Resistor, SimulationConfig, VoltageSource
from pycy_emt_lite.cases import CaseDefinition, OutputOptions, PlotSpec, run_case

SAVE_RESULT_DATA = 0   # 改为 1 才保存数据
SAVE_RESULT_FIGURE = 0  # 改为 1 才保存图像
SHOW_FIGURE = True

def define_case() -> CaseDefinition:
    components = (
        VoltageSource("V1", "n1", "0", 10.0),   # 10 V 直流源
        Resistor("R1", "n1", "0", 5.0),         # 5 Ω 电阻
    )
    config = SimulationConfig(time_step=1e-4, stop_time=1e-3, method="trapezoidal")
    plots = (PlotSpec(columns=("v:n1", "i:R1"), title="R 电路电压与电流"),)
    output = OutputOptions(show_figure=SHOW_FIGURE)
    return CaseDefinition(
        name="r_circuit", components=components, config=config,
        plots=plots, output=output,
    )

def main() -> None:
    case = define_case()
    run_case(case)   # 自动仿真、打印结果摘要、绘图

if __name__ == "__main__":
    main()
```

`run_case()` 自动完成：仿真 -> 打印完成信息与结果摘要（含解析解/理论值对比）-> 绘制波形。
基础算例（01–05）都在摘要中把仿真结果与解析解对比，让"结果可验证"看得见。

## 学习路径（16 个示例）

| 编号 | 示例 | 主题 |
|---|---|---|
| 01 | `r_circuit` | 直流电阻电路，最基本的建模流程 |
| 02 | `rc_transient` | RC 一阶充电暂态 |
| 03 | `rl_transient` | RL 一阶电流建立 |
| 04 | `rlc_transient` | RLC 二阶振荡 |
| 05 | `three_phase_steady_state` | 三相稳态波形与 RMS 分析 |
| 06 | `three_phase_short_circuit` | 三相短路故障与事件系统 |
| 07 | `single_phase_ground_fault` | 单相接地不对称故障 |
| 08 | `pi_line_transient` | π 型线路集中参数模型 |
| 09 | `single_phase_transformer` | 单相变压器（变比/漏抗/励磁） |
| 10 | `park_generator_avr_governor` | Park dq0 同步机与 AVR/调速器 |
| 11 | `pll_dynamic_response` | SRF-PLL 锁相过程 |
| 12 | `two_level_pwm_generator` | 两电平 PWM 逆变器（开关模型） |
| 13 | `three_phase_grid_inverter_average` | 三相平均逆变器 dq 电流环 |
| 14 | `pv_grid_following` | 光伏跟网系统（辐照度阶跃） |
| 15 | `storage_grid_forming` | 储能构网 VSG 孤岛运行 |
| 16 | `vsc_hvdc_average` | VSC-HVDC 平均模型功率阶跃 |

## 项目结构

```text
pycy_emt_lite/     # 核心源码（单一路径：Circuit/Simulator 对象式接口）
  core/            # 仿真内核：电路、配置、稠密求解器、仿真主循环
  components/      # 元件：RLC、源、三相、线路、变压器、开关、电力电子
  controls/        # 控制：PI、限幅、滤波、坐标变换、PLL、PWM
  converters/      # 变流器：平均逆变器、MMC、VSC-HVDC、滤波器组合
  machines/        # 同步机：经典二阶与 Park dq0 模型
  renewables/      # 新能源：光伏、电池、DC-link、跟网/构网/LVRT 控制
  events/          # 事件：故障投入/清除、断路器开合
  io/              # 结果：SimulationResult、CSV/JSON/NPZ
  visualization/   # 绘图与 Markdown 报告
  analysis/        # 分析：RMS、峰值、功率、电压跌落
  cases.py         # 统一算例接口：CaseDefinition / run_case
examples/          # 16 个按学习路径编号的示例
tests/             # 单元测试
docs/              # 文档（理论、用户指南、算例流程）
```

## 环境要求

- Python 3.14（使用 `uv` 管理）
- 依赖：numpy、scipy、matplotlib

## 理论阅读顺序

建议先运行示例、再按顺序读理论文档，把"程序行为"和"数学模型"对应起来：

1. [改进节点分析法 MNA](docs/theory/mna.md)：为什么用 MNA、方程形式、变量约定
2. [基础元件建模](docs/theory/basic_components.md)：R、L、C、电源的离散化
3. [元件 stamp 原理](docs/theory/stamp_principles.md)：每个元件如何写入矩阵（最详细）
4. [三相系统](docs/theory/three_phase_systems.md)：三相电源/线路/负荷
5. [控制系统](docs/theory/control_systems.md)：PI、PLL、坐标变换
6. [电力电子](docs/theory/power_electronics.md)：开关与平均逆变器
7. [线路与变压器](docs/theory/advanced_line_transformer_models.md)：π 型/Bergeron 线路、变压器
8. [新能源模型](docs/theory/renewable_grid_models.md)：光伏、电池、跟网/构网控制

## 文档入口

- [用户指南](docs/user_guide.md)：详细的安装、运行、结果对象与常见问题（比 README 更完整）。
- [仿真程序详细说明](docs/simulation_program_guide.md)：MNA 组装、求解、状态更新在代码里怎么实现。
- [新增算例流程](docs/new_simulation_workflow.md)：如何写一个新的仿真算例。

## 与 PyCy_EMT 的关系

PyCy_EMT_Lite 是从完整版 PyCy_EMT（v0.6 对象式接口）中整理出的精简易用版：
保留全部对象式模型与仿真内核，去掉 YAML/CaseSpec 编译管线、架构专项代码与
相关文档，代码包名改为 `pycy_emt_lite`，示例按教学路径重新编号。
