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
也不能重复运行。时间参数必须有限，当前只支持 `start_time=0`。结果直接使用原始字段，
不再提供 `result_transform` 回调。首行保持声明的电容电压和电感电流，并求一致的电流/电压历史。
显式事件先按旧网络推进到事件时刻，再固定储能状态求右侧代数量；需要冲激的状态跳变明确拒绝。
受理想约束的 callable 源可能需要解析 `derivative`（V/s 或 A/s），见[初始化约定](docs/simulation_program_guide.md#一致初始化与事件)。
均值、RMS 和平均功率按真实时间统计；故障结果应分别选择连续窗口，避免跨事件插值。

## 三种模型层级

仓库目前同时存在三种模型层级，不能混为一谈：

| 层级 | 含义 | 当前用途 |
|---|---|---|
| 网络 EMT | 每个时间步组装并求解 MNA 网络 | RLC、三相电路、故障、π 型线路、变压器 |
| 开关 EMT | 理想开关在离散时间网格上改变网络 | 两电平 PWM 教学示例 |
| 平均控制 | 手写控制/状态更新，不产生器件开关波形 | 并网逆变器、光储和 HVDC 候选示例 |

示例 11、13–16 的结果标签 `explicit_control` 表示手写显式状态更新，仅作为结果说明，
不是 `SimulationConfig.method` 的选项。这些示例不经过 `Circuit/Simulator` EMT 主流程。

## 当前示例范围

以下结论来自当前脚本、测试和实际无界面运行。表中区分已验证的修改与后续去向；
后续删减尚未全部实施。

| 编号 | 唯一教学目标 | 层级 | 当前证据与问题 | 决定 |
|---:|---|---|---|---|
| 01 | 对象式流程、静态 MNA、欧姆定律 | 网络 EMT | 精确电压/电流单元测试 | 保留为唯一 Quick Start |
| 02 | RC companion 与一阶时间常数 | 网络 EMT | 初值/初始电流、首区间及解析步长减半测试 | 与 03/04 合并候选 |
| 03 | RL 对偶与电感支路未知量 | 网络 EMT | 初值/初始电压、首区间及解析步长减半测试 | 与 02/04 合并候选 |
| 04 | 欠阻尼 RLC 与双状态耦合 | 网络 EMT | 阻尼全过程、KCL、收敛及无损 LC 能量测试 | 作为动态基础合并锚点 |
| 05 | 平衡三相、相序和 RMS | 网络 EMT | 有平衡 RMS 测试，脚本仅打印 A 相近似分压 | 并入 06 候选 |
| 06 | 同时事件、三相短路和清除 | 网络 EMT | 能检查事件日志和峰值，缺 pre/fault/post 窗口门 | 保留为三相/事件锚点 |
| 07 | 单相接地不对称故障 | 网络 EMT | 固定 pre/fault/post 周期 RMS 与解析电阻分压测试通过 | 保留为不对称故障单元 |
| 08 | π 型集中参数线路 | 网络 EMT | 只有 DC 分压测试，交流脚本没有定量摘要 | 保留，补 RMS/幅相或能量验证 |
| 09 | 单相变压器变比、漏抗和励磁 | 网络 EMT | 只有理想变比测试，交流脚本没有定量摘要 | 保留，补 RMS 比和功率平衡 |
| 10 | 同步机负荷阶跃、AVR 和调速器 | 网络 EMT 代理 | 只有宽范围趋势测试，模型名称与 dq 端口证据不充分 | 退出默认路径或改用简单代理 |
| 11 | SRF-PLL 锁相 | 平均控制 | 有 q 轴和频率误差测试；结果方法标签已修正 | 并入最终 GFL 单元候选 |
| 12 | SPWM、理想开关和 RL 电流 | 开关 EMT | 只有元件/载波测试，完整桥仅打印末值 | 保留，补相电流和基波检查 |
| 13 | 平均逆变器 dq 电流环 | 平均控制 | 只打印 id/iq，闭环无直接测试；结果方法标签已修正 | 最小 GFL 合并锚点候选 |
| 14 | PV、DC-link 和跟网控制 | 平均控制 | 只有组件趋势测试，PV/DC 功率合同尚不自洽 | 并入 13 或删除 |
| 15 | 储能 GFM/VSG 和负荷阶跃 | 平均控制 | 只有方向测试，当前 DC-link 功率差被人为抵消 | 修正能量合同后条件保留 |
| 16 | VSC-HVDC 功率阶跃 | 平均控制 | 线路电流/损耗合同不可信，首末电压摘要无判别力 | 退出默认学习路径 |

所有 16 个脚本目前都能在 `MPLBACKEND=Agg` 下退出 0，但“运行结束”不等于物理正确。
物理阈值应由 pytest 维护，示例只负责输出带单位的关键观察量。

### 目标学习顺序

目标约 6–8 个学习单元，不强制压缩脚本数量，也不建设课程运行器：

1. R 电路与对象式 Quick Start；
2. RC/RL/RLC companion、初值和收敛；
3. 平衡三相、RMS、故障事件与恢复；
4. π 型集中参数线路；
5. 单相变压器；
6. PWM 开关模型；
7. PLL，以及最多一个通过功率、能量和独立参考验证的平均值 GFL 或 GFM 案例。

综合案例若需要新增耦合框架才能接入主流程，当前版本暂缓保留。实例复用已明确拒绝；
下一步重点是初值和动态事件边界，再收缩模型与文档；详见[改进计划](docs/project_improvement_plan.md)。

## 公开入口

顶层 `pycy_emt_lite` 只推荐导入：

- `CaseDefinition`、`Circuit`、`Simulator`、`SimulationResult`；
- R、L、C、独立源；
- 理想开关、断路器、故障及其事件；
- 三相电源、线路和负荷；
- π 型线路和单相变压器。

求解器协议、状态数据类、绘图报告、高阶线路、电机、变流器和新能源候选不再从顶层
重复导出。现阶段如需审查这些实现，应从对应子包显式导入；这不表示它们已进入可信
课程范围。

## 文档收敛方向

现有文档按下表收敛，不建立文档站或归档副本：

| 当前文档 | 去向 |
|---|---|
| `user_guide.md`、`new_simulation_workflow.md` | 必要操作并入本 README，随后删除原文件 |
| `simulation_program_guide.md`、`theory/mna.md`、`theory/basic_components.md`、`theory/stamp_principles.md` | 只保留全局 MNA、基础 stamp、时间/事件、单位和方向约定，合并为 `docs/numerical_conventions.md` |
| `theory/three_phase_systems.md`、`theory/advanced_line_transformer_models.md`、`theory/control_systems.md`、`theory/power_electronics.md`、`theory/renewable_grid_models.md` | 只保留最终模型的层级、必要方程、限制和验证证据，合并为 `docs/models_and_validation.md` |
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
