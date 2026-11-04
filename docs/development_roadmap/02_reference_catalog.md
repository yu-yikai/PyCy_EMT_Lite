# 参考模型目录与筛选依据

调查日期：2026-11-04。机器可读记录见 [reference_catalog.json](reference_catalog.json)。本轮已下载的第三方原件仅保存在忽略 Git 的 `local_reference/`；下载不代表获得再分发许可。

## 证据状态

`discovered` 仅确认来源；`downloaded` 有本地原件；`inspected` 已检查文件内容、版本或参数；`runnable` 已在对应软件成功运行；`reference_ready` 有可追溯的真实数值输出。运行障碍独立写入 `blockers`，避免把已检查但无法运行的资源误记为未发现。`blocked` 用于尚不能推进的资源；不会把图像、解析公式或 Python 重算当作外部数值参考。

## 已获得的工程与结果

| ID | 资源与实际文件 | 本轮证据 | 当前使用决定 |
|---|---|---|---|
| MW-RC2 | MathWorks 两级 RC：`CascadedRCCircuitInSimulinkAndSimscape.slx` | **reference_ready**；MATLAB R2025a Update 1 + Simulink + Simscape 实际运行；10,052 个严格递增原生样本 | 第一项新增算例；保留两级负载耦合、初值、源时序和 ESR |
| PSCAD-RLDC | 官方 Cookbook 第 3 章 `Circuit_Response_study_01.pscx` | **inspected**；XML v4.6.0，R=1 Ω、L=0.1 H，50 µs 步长，1 s 合闸 | 既有 RL 的未来参考，不重复新增教学例 |
| PSCAD-RLAC | 同包 `_02.pscx` | **inspected**；XML v4.6.0，R=1.963 Ω、L=74 mH，开关 Ron=0.005 Ω | 研究合闸相角与直流偏置，有别于仅稳态 RL |
| PSCAD-RLC | 同包 `_03.pscx` | **inspected**；XML v4.6.0，R=1.392 Ω、L=26 mH、C=3.761 µF，0.1 s 合闸 | 已有交流 RLC 的参数化参考候选 |
| PSCAD-LC | 同包 `_04.pscx` | **inspected**；XML v4.5.3，C=3.2 nF、L=353 mH，另含15 mH支路，0.0174 s合闸 | 先检查完整接线与高频分辨率，不直接称为纯并联 LC |
| PNNL-IBR | `PSCAD.zip`：17 个 `.pscx`、`Solar_Lib.pslx`、3 个工作空间及编译库 | **inspected**；主要工程 v5.0.1/5.0.2；有开关/平均模型和扰动变体，无波形输出 | 用作单站 GFL 的参数与控制调查；不得直接复制完整100 MW站级模型 |
| NLR-GFLGFM | `GFL-GFM.zip`：`9_Bus_Zero_Inertia.pscx`、`Kenyon_Library.pslx` | **inspected**；v4.6.3，20 µs计算、500 µs输出；含生成Fortran和二进制 | 长期控制研究；包内6个 `.out` 均为线路常数报告，**不是时域波形** |
| NLR-3BUS | `Kenyon_PSCC_3bus.zip`：实际主文件 `SC_Testing/SyncCon_Tests.pscx` | **inspected**；v5.0.0，依赖 ETRAN/PRSIM/Wallace_201004_Lib | 延后；文件名有“3bus”不能证明是最小无依赖三节点例 |
| MW-DC | 官方教学库 v2.2.2 的 `NodalAnalysisExample.slx`、`RLCCircuit.slx` | **inspected**；metadata R2024a，由R2024b导出；前者含7电阻、电压和电流源 | 多源线性网络参考候选；需先运行并解析测量定义 |

官方来源：[MathWorks 两级 RC](https://www.mathworks.com/help/simscape/ug/cascaded-rc-circuit-in-simulink-and-simscape.html)、[PSCAD 第3章](https://www.pscad.com/knowledge-base/article/46)、[PNNL Bootcamp](https://github.com/pnnl/i2x/tree/master/emt-bootcamp)、[PyPSCAD](https://github.com/NatLabRockies/PyPSCAD)、[MathWorks DC Circuit Analysis](https://github.com/MathWorks-Teaching-Resources/DC-Circuit-Analysis)。具体下载 URL、文件哈希、依赖和许可判断均在 JSON 中逐项记录。

### 已运行的两级 RC

MATLAB `openExample('simscape/CascadedRCCircuitInSimulinkAndSimscapeExample')` 下载的是适配本机 R2025a 的模型；文件哈希 `54422f5f100c220c0bea9e396d1d1cd3fd015bb923b9ba48f555e054ddf29a06`。R1=R2=10 Ω、C1=C2=100 µF、每个电容ESR=1 µΩ、初始电压0；输入为5 V脉冲，周期10 ms、占空比50%、延迟1 ms。仿真20 ms，`ode15s`，RelTol=1e-8、AbsTol=1e-10、MaxStep=2 µs。

未改变物理网络、参数或初值。原生重复时刻取最后的事件后样本，无时间偏移。原工程、MAT文件、原生CSV、标准化CSV和日志均在 `local_reference/cascaded_rc/`；[导出程序](../../validation/cases/cascaded_rc/export_reference.m)可重跑。该状态只证明参考数据就绪；PyCy算例是否通过对标应查独立验收报告。

### 已发现但尚未运行的近期参考

本机 R2025a 的 `help/docCatalog/exampleapi/simscape.zip`、`sps.zip` 已核对以下精确示例ID和支持文件。目录元数据不是已下载的模型。

| ID | 官方示例ID / 文件 | 相容性及待核对事项 |
|---|---|---|
| MW-SPWM | `simscapeelectrical/VSCSinusoidalPWMExample` / `VSCSinusoidalPWM.slx` | 正弦与三角载波比较；先核对开关与保护二极管、电压参考、滤波器和浮动中性点 |
| MW-PWM | `simscapeelectrical/TwoLevelPWMGeneratorExample` / `TwoLevelPWMGenerator.slx` | 400 V直流输入；PWM模块的门极时刻计算不能自动等同于PyCy离散载波逐点比较 |
| MW-LCLINE | `simscapeelectrical/LCLineTestBridgeExample` / `LCLineTestBridge.slx` | 多段LC及双向测试桥；原桥含有源测量部分，不能直接等同于Bergeron；先抽取被动网络 |
| MW-EARTH | `simscapeelectrical/EarthingEffectsExample` / `EarthingEffects.slx` | 平衡到不平衡的接地/浮地中性点对比；电阻变化时序与中性点约束需严格映射 |
| MW-GRID | `simscapeelectrical/GridTiedInverterExample` / `GridTiedInverter.slx` + `GridTiedInverterData.m` | 0.15 s并网、PI电压环、IGBT；不是现有PyCy dq电流控制的直接等价物 |

对应说明：[SPWM](https://www.mathworks.com/help/simscape-electrical/ug/three-phase-voltage-sourced-converter-spwm.html)、[PWM](https://www.mathworks.com/help/simscape-electrical/ug/three-phase-two-level-pwm-generator.html)、[LC线路](https://www.mathworks.com/help/simscape-electrical/ug/lc-transmission-line-and-test-bridge.html)、[中性点](https://www.mathworks.com/help/simscape-electrical/ug/earthing-effects.html)、[并网逆变器](https://www.mathworks.com/help/simscape-electrical/ug/grid-tied-inverter.html)。后续运行成功应提升JSON状态并保存新证据，不能仅依据网页图像提升。

### 既有单级RC补对标

`mw-rc-r2025a`也已提升为**reference_ready**：实际运行官方`RCCircuitInSimulinkAndSimscape.slx`，通过SimulationInput覆盖为R=1000 Ω、C=1 µF、1 V恒定输入、0初值、5 ms终止，对应既有example 02；保留1 µΩ ESR。`ode15s`、RelTol=1e-8、AbsTol=1e-10、MaxStep=1 µs，导出5013个真实数值样本。模型、原始MAT/CSV、标准化结果及provenance保存在`local_reference/rc_charging/`。此为既有算例补验证，不计为新增算例。

## 版本、许可与数据障碍

1. 网页默认版本目前是R2026b，本地是R2025a。SPS在R2026a移除，旧SPS与原生Simscape工程不能混用；优先选择原生Simscape，保留确切示例ID和运行版本。[MathWorks官方发布说明](https://www.mathworks.com/help/simscape-electrical/release-notes.html)
2. PSCAD Cookbook 提供公开下载入口，适合本地学习检查；原文版权保留，没有查到宽松再分发许可，原件不上传。PSCAD应用/编译器运行未完成，不能记为runnable。
3. PNNL根目录 `license.txt`允许使用、修改和再分发且要求保留版权、条款及免责声明；压缩包含不同编译器版本的二进制库，未证明跨版本可运行，也没有验证每个附带库的许可。当前仅本地检查。
4. PyPSCAD README明确允许使用和修改并要求引用相关论文；未见标准LICENSE，也未核定生成二进制的授权。仅保留本地，研究时引用作者指定论文。不要执行包内旧 `.exe` 来代替受许可的PSCAD参考运行。
5. MathWorks DC教学库当前`release`分支提供BSD三条款许可。下载的固定标签v2.2.2模型已检查，获取标签自身LICENSE时网络EOF；本轮不再分发原模型，未来如需入库应先保存同标签许可。当前目录模型metadata已核验，尚未在MATLAB运行。
6. PNNL README提及COMTRADE示例数据，但当前`PSCAD.zip`没有这些文件；仓库的`playback.dat/cfg`不是已确认某个PyCy候选拓扑的输出，不能当作站级验收数据。

## 筛选规则和实施顺序

先过硬门槛：物理模型可相容、可追溯真实参考、符合当前范围。任何一项未满足都不能成为正式完成算例。然后每维0–5分，权重合计100：教学价值15、代表性10、模型可用性15、数据可用性15、当前适配15、开发容易程度8、验证容易程度8、新知识程度5、复用价值5、维护容易程度4。复杂度等成本项以“越容易分越高”编码；总分为 `sum(weight * rating / 5)`。分数只是当前证据下的排序，不能替代验收。

| 候选 | 当前得分/100 | 决定 |
|---|---:|---|
| 两级RC耦合网络 | 99.0 | 首先实施；真实数据已就绪，弥补多状态耦合教学缺口 |
| 三相接地与浮动中性点 | 80.8 | 下一组基础候选；运行官方模型后确定参数和验收 |
| 多源电阻网络 | 79.4 | 用已下载官方节点例先验证源方向和KCL，避免新核心功能 |
| 三相SPWM+RL | 76.4 | 下一电力电子候选；先研究开关/二极管差别 |
| 交流RL合闸相角 | 77.0 | 可由现元件组合，等待PSCAD运行或另取Simscape参考 |
| 多段LC线路传播 | 70.8 | 先取纯被动部分，不能用LC波形证明Bergeron等价 |
| 单站GFL功率阶跃 | 67.8 | 复用现有PLL/PI/dq，先建立完整时序/符号映射 |
| 小型GFM/三母线 | 50.8 | 控制差异与依赖多，延后至单站参考链稳定 |
| 完整IEEE9动态、MMC、39/118节点 | 不评分 | 超出近期；不为追求数量实现 |

各评分向量见JSON。单相RC/RL/RLC和现有故障例优先补参考验证，不重复新增同知识点。变压器优先现有线性两绕组模型；公开的饱和/磁滞/自动调压参考需要去除额外物理效应并留下修改说明，尚未取得可直接等价运行的两绕组参考，不虚列“可用”。同步Buck/Boost只能使用明确受控同步开关场景；普通二极管整流桥、自换流Buck/Boost列为模型能力依赖。固定直流源接口不命名为完整PV或电池系统。

## 本地复核

`reference_catalog.json`中归档SHA256校验已实际完成，XML检查覆盖上述PSCAD工程与依赖名，SLX元数据通过ZIP/XML读取完成；这类检查不等于在参考软件打开。MathWorks两级RC和单级RC均已在本轮完成真实运行和数值导出。读取最新JSON确认后续状态变化。
