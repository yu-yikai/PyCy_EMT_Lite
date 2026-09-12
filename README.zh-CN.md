# PyCy_EMT_Lite

[English](README.md) | 简体中文

PyCy_EMT_Lite 是一个面向新型电力系统电磁暂态仿真的小型纯 Python 教学项目。
推荐的唯一公开流程是：

```text
CaseDefinition -> Circuit -> Simulator -> SimulationResult
```

> **教学边界：** 当前 0.1 版本正在收缩为少量可信模型。项目不是厂站级 EMT
> 工具，不应用于保护整定、并网合规、设备设计、工程定值或运行决策。

## 快速开始

环境要求为 Python 3.14，并使用 [uv](https://docs.astral.sh/uv/) 管理依赖。

```bash
uv sync --locked
uv run python examples/01_r_circuit.py
uv run pytest
```

示例 01 是当前可信起点：它走完整对象式流程，并把仿真电压与解析值对比。

每次仿真应新建 `Simulator`、`Circuit` 和元件对象；同一 `CaseDefinition` 中的元件
也不能重复运行。时间参数必须有限，当前只支持 `start_time=0`。`stop_time` 必须为
`time_step` 的非负整数倍；非法配置在仿真前报错并给出修复建议。允许 8 ULP 浮点舍入误差，
例如 `0.1+0.2` 可用于 0.1 s 步长。结果直接使用原始字段，
不再提供 `result_transform` 回调。首行保持声明的电容电压和电感电流，并求一致的电流/电压历史。
显式事件先按旧网络推进到事件时刻，再固定储能状态求右侧代数量；需要冲激的状态跳变明确拒绝。
受理想约束的 callable 源可能需要解析 `derivative`（V/s 或 A/s），见[初始化约定](docs/simulation_program_guide.md#一致初始化与事件)。
均值、RMS 和平均功率按真实时间统计；故障结果应分别选择连续窗口，避免跨事件插值。

## 模型层级与近似

保留模型采用以下层级与近似：

| 层级 | 含义 | 当前用途 |
|---|---|---|
| 网络 EMT | 每个时间步组装并求解 MNA 网络 | RLC、三相电路、故障、π 型线路、变压器 |
| 开关 EMT | 理想开关在离散时间网格上改变网络 | 两电平 PWM 教学示例 |
| 机电近似 | dq 代数定子端口，显式推进机电/控制状态 | 四阶同步发电机示例 10 |
| 离散控制 | 手写控制/状态更新，不求解电气网络 | 独立 PLL 示例 11 |

示例 11 的结果标签 `explicit_control` 表示手写显式状态更新，仅作为结果说明，
不是 `SimulationConfig.method` 的选项。该控制演示不经过 `Circuit/Simulator` EMT 主流程。
13–16 及其平均逆变器、光储和 HVDC/MMC 模型已按计划移除，同时移除 Diode/IGBT 近似。
本版不保留 GFL/GFM 综合算例。按用户要求保留并完善两种同步机及示例 10：修正功率计入、
状态时刻和 Park 两轴暂态电抗的端口作用。保留脚本沿用原编号 01–12、17。

## 当前示例范围

以下结论来自当前脚本、测试和实际无界面运行。表中区分已验证的修改与后续去向；
后续删减尚未全部实施。

| 编号 | 唯一教学目标 | 层级 | 当前证据与问题 | 决定 |
|---:|---|---|---|---|
| 01 | 对象式流程、静态 MNA、欧姆定律 | 网络 EMT | 精确电压/电流单元测试 | 保留为唯一 Quick Start |
| 02 | RC companion 与一阶时间常数 | 网络 EMT | 初值/初始电流、首区间及解析步长减半测试 | 与 03/04 合并候选 |
| 03 | RL 对偶与电感支路未知量 | 网络 EMT | 初值/初始电压、首区间及解析步长减半测试 | 与 02/04 合并候选 |
| 04 | 欠阻尼 RLC 与双状态耦合 | 网络 EMT | 阻尼全过程、KCL、收敛及无损 LC 能量测试 | 作为动态基础合并锚点 |
| 05 | 平衡三相 RL 负荷、相序和 RMS | 网络 EMT | 每相 20 Ω + 50 mH；零初值启动、稳态幅相与 P/Q 检查通过 | 保留独立短脚本，便于观察电流滞后 |
| 06 | 含电感线路的三相短路和清除 | 网络 EMT | 每相线路 0.8 Ω + 5 mH，步长 10 μs；分段解析解、故障前/中/后 RMS 与负荷功率通过 | 保留，分别显示线路连续电流、故障电流及清除过电压 |
| 07 | 单相接地不对称故障 | 网络 EMT | 固定 pre/fault/post 周期 RMS 与解析电阻分压测试通过 | 保留为不对称故障单元 |
| 08 | π 型集中参数线路 | 网络 EMT | 交流电压/电流相量、全暂态 KCL/能量及步长收敛通过 | 保留，摘要给出幅相和电阻功率 |
| 09 | 单相变压器变比、漏抗和励磁 | 网络 EMT | 带载相量、励磁 DC 分量、含铁耗的能量及收敛通过 | 保留，区分绕组与电源总电流 |
| 10 | 同步发电机平衡运行点、负荷阶跃、AVR 和调速器 | 四阶 dq 代数端口与机电动态 | 两轴端口、铜损/气隙功率、事件状态及独立 ODE/一阶收敛检查 | 保留并完善；不用于定子快速暂态、次暂态或不平衡故障 |
| 11 | SRF-PLL 锁相 | 离散控制 | 有 q 轴和频率误差测试；结果方法标签已修正 | 保留独立控制演示 |
| 12 | SPWM、理想开关和 RL 电流 | 开关 EMT | 互补门极、浮置星点/KCL、RL 基波和三档步长对照通过 | 保留，摘要区分总 RMS 与基波 |
| 17 | 单相交流源与串联 RLC | 网络 EMT | 零初值、稳态相量/RMS 与 KCL/KVL 检查通过 | 按用户要求新增，归入基础 RLC 学习单元 |

当前保留 13 个脚本；“运行结束”不等于物理正确。
物理阈值应由 pytest 维护，示例只负责输出带单位的关键观察量。

新增交流算例运行命令：`uv run python examples/17_single_phase_ac_rlc.py`。
接线为 220 V 有效值、50 Hz 电源串联 20 Ω、50 mH 和 100 μF；电压、电流分图显示，
默认不保存数据和图片。参数及输出开关集中在脚本顶部。默认在 0.08–0.12 s 窗口用
`Z = R + j(ωL - 1/ωC)` 核对电流有效值与相位；修改频率或阻尼后，应重新选择稳态整周期窗口。

同步机算例：`uv run python examples/10_park_generator_avr_governor.py`。
模型从平衡运行点开始，在 0.2 s 投入三相负荷；电压/励磁、转速、功率分图显示。
参数、初值计算、功率方向和适用范围见[同步机说明](docs/theory/advanced_line_transformer_models.md)。

### 目标学习顺序

目标约 6–8 个学习单元，不强制压缩脚本数量，也不建设课程运行器：

1. R 电路与对象式 Quick Start；
2. RC/RL/RLC companion、初值和收敛；
3. 平衡三相、RMS、故障事件与恢复；
4. π 型集中参数线路；
5. 单相变压器；
6. PWM 开关模型；
7. PLL 离散控制演示。
8. 同步机平衡初值、机电响应与 AVR/调速器。

本版暂不建设控制采样与网络耦合框架，因此已移除未接入主流程的综合候选。实例复用已明确拒绝；
初值、显式动态事件、Bergeron 固定网格及示例 08/09/12 的专项验证已有回归；
05/06 已加入电感并补齐启动及故障窗口验证；下一步审查剩余组合模型，再合并文档；详见[改进计划](docs/project_improvement_plan.md)。

## 公开入口

顶层 `pycy_emt_lite` 只推荐导入：

- `CaseDefinition`、`Circuit`、`Simulator`、`SimulationResult`；
- R、L、C、独立源；
- 理想开关、断路器、故障及其事件；
- 三相电源、线路和负荷；
- π 型线路和单相变压器。

求解器协议、状态数据类、绘图报告和高阶线路不从顶层重复导出；剩余候选从对应
子包显式导入，不表示它们已进入可信课程范围。同步机从 `pycy_emt_lite.machines` 导入；原新能源和变流器平均模型类已移除；
`pycy_emt_lite.converters` 仅保留现有 L/LC/LCL 滤波器组合。

## 文档收敛方向

现有文档按下表收敛，不建立文档站或归档副本：

| 当前文档 | 去向 |
|---|---|
| `user_guide.md`、`new_simulation_workflow.md` | 必要操作并入本 README，随后删除原文件 |
| `simulation_program_guide.md`、`theory/mna.md`、`theory/basic_components.md`、`theory/stamp_principles.md` | 只保留全局 MNA、基础 stamp、时间/事件、单位和方向约定，合并为 `docs/numerical_conventions.md` |
| `theory/three_phase_systems.md`、`theory/advanced_line_transformer_models.md`、`theory/control_systems.md`、`theory/power_electronics.md` | 只保留最终模型的层级、必要方程、限制和验证证据，合并为 `docs/models_and_validation.md` |
| `visualization_reporting.md` | 内容重复且含过时接口，直接删除 |
| `project_improvement_plan.md` | 仅在改进期间保留；全部阶段完成后删除，不作为产品文档 |

合并完成前，以源码 docstring 和测试为实现依据。

## 当前结构

```text
pycy_emt_lite/   # 仿真内核和模型实现
examples/        # 可运行教学案例
tests/           # 数值与物理回归检查
docs/            # 正在收敛的说明文档
```

## 与 PyCy_EMT 的关系

PyCy_EMT_Lite 源自 PyCy_EMT v0.6 的对象式工作流，主动去掉 YAML/CaseSpec 管线及
其它平台级架构，把重点放在小规模教学模型、数值语义和可验证结果上。

## 许可证

[MIT](LICENSE)
