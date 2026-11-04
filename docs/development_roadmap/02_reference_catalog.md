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
| MW-DC | 官方教学库 v2.2.2 的 `NodalAnalysisExample.slx`、`RLCCircuit.slx` | Nodal已**reference_ready**；101点、14个电气信号；RLC仅**inspected**且未运行；metadata R2024a | 线性多源网络已就绪；批量仿真临时禁用孤立未接万用表，主电路不改 |

官方来源：[MathWorks 两级 RC](https://www.mathworks.com/help/simscape/ug/cascaded-rc-circuit-in-simulink-and-simscape.html)、[PSCAD 第3章](https://www.pscad.com/knowledge-base/article/46)、[PNNL Bootcamp](https://github.com/pnnl/i2x/tree/master/emt-bootcamp)、[PyPSCAD](https://github.com/NatLabRockies/PyPSCAD)、[MathWorks DC Circuit Analysis](https://github.com/MathWorks-Teaching-Resources/DC-Circuit-Analysis)。具体下载 URL、文件哈希、依赖和许可判断均在 JSON 中逐项记录。

### 已运行的两级 RC

MATLAB `openExample('simscape/CascadedRCCircuitInSimulinkAndSimscapeExample')` 下载的是适配本机 R2025a 的模型；文件哈希 `54422f5f100c220c0bea9e396d1d1cd3fd015bb923b9ba48f555e054ddf29a06`。R1=R2=10 Ω、C1=C2=100 µF、每个电容ESR=1 µΩ、初始电压0；输入为5 V脉冲，周期10 ms、占空比50%、延迟1 ms。仿真20 ms，`ode15s`，RelTol=1e-8、AbsTol=1e-10、MaxStep=2 µs。

未改变物理网络、参数或初值。原生重复时刻取最后的事件后样本，无时间偏移。原工程、MAT文件、原生CSV、标准化CSV和日志均在 `local_reference/cascaded_rc/`；[导出程序](../../validation/cases/cascaded_rc/export_reference.m)可重跑。该状态只证明参考数据就绪；PyCy算例是否通过对标应查独立验收报告。

### 电力电子已运行资源及其余候选

本机 R2025a 的 `help/docCatalog/exampleapi/simscape.zip`、`sps.zip` 已核对以下精确示例ID和支持文件。除标明runnable的SPWM及reference_ready的TwoLevel和中性点模型外，其余只有目录元数据，不代表已下载。

| ID | 官方示例ID / 文件 | 相容性及待核对事项 |
|---|---|---|
| MW-SPWM | `simscapeelectrical/VSCSinusoidalPWMExample` / `VSCSinusoidalPWM.slx` | **runnable**；R2025a实际运行到33.333 ms、8037样本；已有原始电流CSV/MAT，但物理等价与完整对标信号未准备 |
| MW-PWM | `simscapeelectrical/TwoLevelPWMGeneratorExample` / `TwoLevelPWMGenerator.slx` | **reference_ready**；原模型真实40001点（0–0.2 s）；既有12首次比较波形FAIL、特征PASS，不能据资源状态计完成 |
| MW-LCLINE | `simscapeelectrical/LCLineTestBridgeExample` / `LCLineTestBridge.slx` | 多段LC及双向测试桥；原桥含有源测量部分，不能直接等同于Bergeron；先抽取被动网络 |
| MW-EARTH | `simscapeelectrical/EarthingEffectsExample` / `EarthingEffects.slx` | **reference_ready**；1001点真实数据，13信号/3预设窗口；正确电流映射与PyCy验收报告已分别保存 |
| MW-GRID | `simscapeelectrical/GridTiedInverterExample` / `GridTiedInverter.slx` + `GridTiedInverterData.m` | 0.15 s并网、PI电压环、IGBT；不是现有PyCy dq电流控制的直接等价物 |

对应说明：[SPWM](https://www.mathworks.com/help/simscape-electrical/ug/three-phase-voltage-sourced-converter-spwm.html)、[PWM](https://www.mathworks.com/help/simscape-electrical/ug/three-phase-two-level-pwm-generator.html)、[LC线路](https://www.mathworks.com/help/simscape-electrical/ug/lc-transmission-line-and-test-bridge.html)、[中性点](https://www.mathworks.com/help/simscape-electrical/ug/earthing-effects.html)、[并网逆变器](https://www.mathworks.com/help/simscape-electrical/ug/grid-tied-inverter.html)。后续运行成功应提升JSON状态并保存新证据，不能仅依据网页图像提升。SPWM实际选择`device_type=1`；原生`ee.enum.converters.switchingdevice`枚举确认为GTO，Ron=0.001 Ω、Vf=0.6 V均生效，并含保护二极管。子日志`Converter.Q1.ideal_switch`只是内部实现，不能用来认定顶层选用了理想开关。二极管有效Vf=0.8 V、Ron=0.001 Ω、Goff=1e−5 S。直流侧100 V/R0.1 Ω/C5000 µF真实连接；每相`component_structure=2`只启用500 µH滤波电感，负载`structure=1`只启用1 Ω电阻，mask中200 µH负载电感并不生效。六路控制对正弦和载波同时作offset，存在上下管同关区间及自动二极管续流，不能等同于例12严格互补的0/1门极。已实际运行不代表与PyCy外控理想开关等价；本轮保留为runnable，未冒充正式对标就绪。原始结果位于`local_reference/vsc_spwm/raw_results/`。

### 既有单级RC补对标

`mw-rc-r2025a`也已提升为**reference_ready**：实际运行官方`RCCircuitInSimulinkAndSimscape.slx`，通过SimulationInput覆盖为R=1000 Ω、C=1 µF、1 V恒定输入、0初值、5 ms终止，对应既有example 02；保留1 µΩ ESR。`ode15s`、RelTol=1e-8、AbsTol=1e-10、MaxStep=1 µs，导出5013个真实数值样本。模型、原始MAT/CSV、标准化结果及provenance保存在`local_reference/rc_charging/`。此为既有算例补验证，不计为新增算例。

## 版本、许可与数据障碍

1. 网页默认版本目前是R2026b，本地是R2025a。SPS在R2026a移除，旧SPS与原生Simscape工程不能混用；优先选择原生Simscape，保留确切示例ID和运行版本。[MathWorks官方发布说明](https://www.mathworks.com/help/simscape-electrical/release-notes.html)
2. PSCAD Cookbook 提供公开下载入口，适合本地学习检查；原文版权保留，没有查到宽松再分发许可，原件不上传。PSCAD应用/编译器运行未完成，不能记为runnable。
3. PNNL根目录 `license.txt`允许使用、修改和再分发且要求保留版权、条款及免责声明；压缩包含不同编译器版本的二进制库，未证明跨版本可运行，也没有验证每个附带库的许可。当前仅本地检查。
4. PyPSCAD README明确允许使用和修改并要求引用相关论文；未见标准LICENSE，也未核定生成二进制的授权。仅保留本地，研究时引用作者指定论文。不要执行包内旧 `.exe` 来代替受许可的PSCAD参考运行。
5. MathWorks DC教学库固定标签v2.2.2的[LICENSE](https://github.com/MathWorks-Teaching-Resources/DC-Circuit-Analysis/blob/v2.2.2/LICENSE.md)已实际下载并检查，明确为BSD三条款，版权2023 MathWorks；SHA256为`129423cdd0e66b615de1ee96a192cbf2fe3a8eb4251bba6577e3464630c4e972`，本地保存`LICENSE-v2.2.2.md`。可在保留版权、条款及免责声明且不作名称背书的条件下再分发；本轮原模型仍保留本地。Nodal模型已真实运行并导出101点数值结果；同条目的RLC模型仍未运行。
6. PNNL README提及COMTRADE示例数据，但当前`PSCAD.zip`没有这些文件；仓库的`playback.dat/cfg`不是已确认某个PyCy候选拓扑的输出，不能当作站级验收数据。

## 筛选规则和实施顺序

先过硬门槛：物理模型可相容、可追溯真实参考、符合当前范围。任何一项未满足都不能成为正式完成算例。然后每维0–5分，权重合计100：教学价值15、代表性10、模型可用性15、数据可用性15、当前适配15、开发容易程度8、验证容易程度8、新知识程度5、复用价值5、维护容易程度4。复杂度等成本项以“越容易分越高”编码；总分为 `sum(weight * rating / 5)`。分数只是当前证据下的排序，不能替代验收。

| 候选 | 当前得分/100 | 决定 |
|---|---:|---|
| 两级RC耦合网络 | 99.0 | 首先实施；真实数据已就绪，弥补多状态耦合教学缺口 |
| 三相接地与浮动中性点 | 95.8 | 真实数据及13信号映射就绪，PyCy验收见独立case报告 |
| 多源电阻网络 | 91.4 | 真实101点数据已就绪；先验证源方向和KCL，避免新核心功能 |
| 三相SPWM+RL | 76.4 | 下一电力电子候选；先研究开关/二极管差别 |
| 交流RL合闸相角 | 77.0 | 可由现元件组合，等待PSCAD运行或另取Simscape参考 |
| 多段LC线路传播 | 70.8 | 先取纯被动部分，不能用LC波形证明Bergeron等价 |
| 单站GFL功率阶跃 | 67.8 | 复用现有PLL/PI/dq，先建立完整时序/符号映射 |
| 小型GFM/三母线 | 50.8 | 控制差异与依赖多，延后至单站参考链稳定 |
| 完整IEEE9动态、MMC、39/118节点 | 不评分 | 超出近期；不为追求数量实现 |

各评分向量见JSON。单相RC/RL/RLC和现有故障例优先补参考验证，不重复新增同知识点。变压器优先现有线性两绕组模型；公开的饱和/磁滞/自动调压参考需要去除额外物理效应并留下修改说明，尚未取得可直接等价运行的两绕组参考，不虚列“可用”。同步Buck/Boost只能使用明确受控同步开关场景；普通二极管整流桥、自换流Buck/Boost列为模型能力依赖。固定直流源接口不命名为完整PV或电池系统。

## 本地复核

`reference_catalog.json`中归档SHA256校验已实际完成，XML检查覆盖上述PSCAD工程与依赖名，SLX元数据通过ZIP/XML读取完成；这类检查不等于在参考软件打开。MathWorks两级RC和单级RC均已在本轮完成真实运行和数值导出；SPWM也已实际运行并保留原始数据，其数学等价及对标信号仍待解决。读取最新JSON确认后续状态变化。

### 节点分析参考的方向约定

`MW-DC`的`NodalAnalysisExample.slx`已解析完整物理端子接线，见JSON的`topology_inspection`。Vs=3 V，Is=200 mA；电阻分别200、140、330、2000、330、50、50 Ω。官方Current Source定义参数正电流为负端到正端，即本例d→c；用PyCy c→d定向时应为-0.2 A。[官方电流源文档](https://www.mathworks.com/help/simscape-electrical/ref/currentsource.html)

已通过独立有理数KCL消元获得[解析常数](experiments/nodal_analysis_exact.json)及[推导说明](experiments/nodal_analysis_exact.md)，用来检查方向和功率守恒。这不是Simulink参考数据，不能据此提升reference_ready。12项原有模型/归档SHA已重新计算且全部相符；新增两个RC标准化CSV、SPWM原始CSV和精确标签许可证哈希已并入目录。

### 节点分析真实运行补证

`NodalAnalysisExample.slx`在MATLAB R2025a Update 1中已成功运行1.852 s，导出0–10 ms共101个时刻、14个电气信号。原模型的孤立未接Virtual Multimeter（SID204）没有Solver Configuration，初次编译失败；导出脚本仅通过SimulationInput临时注释该工具，不保存或修改原SLX，不改七电阻主电路的任何电气接线或参数。此必要运行调整在`local_reference/nodal_analysis/provenance.json`中留痕。主模型SHA仍为`9dd139df62546dab31ecd73d591fbdf432ce43eb2f508f8f4a6ee6b053bc28d0`。

标准化数据为`local_reference/nodal_analysis/normalized_results/reference.csv`，SHA256为`86cfee48f5a63efe7c1fddb998a710773773c63ade820d29bb12afae2c82b44e`。真实log确认电流源c→d为−0.2 A，节点电压符合独立有理解；KCL残差最大5.27e−16 A，功率平衡残差1.42e−14 W。该参考资源状态提升为reference_ready仅适用于Nodal文件，同目录RLCCircuit仍为inspected。参考数据就绪不代表PyCy正式算例已完成验收。

### 三相中性点参考的绘图标签问题

官方`EarthingEffects.slx`已在R2025a Update 1实际运行，保留1001点（0–0.1 s）真实MAT和CSV，模型SHA256为`326ccda2fb0eabe11de7d9511714da076726c0f1b82b6f60abddb8f15e7df84f`。100 V峰值、60 Hz理想三相源，A相电阻在0.05 s由1变3 Ω，C相在0.07 s由1变1.5 Ω，B相1 Ω；本地求解器为100 µs后向欧拉。

模型接线与独立解析检查发现，官方`EarthingEffectsPlotResults.m`把接地/浮动网络的电流变量标签颠倒。正确电流来自`Sensing_vi`（接地）与`Sensing_vi2`（浮动），相电压来自`Sensing_vi1`与`Sensing_vi3`。例如0.06 s时接地ia=−19.59284174 A=va/3；浮动ia=−25.19079653 A=(va−vn)/3，vn=16.79386435 V。原错误标签CSV保留为`raw_results/official_plot_label_mapping.csv`；`raw_results/simscape_native.csv`及`normalized_results/reference.csv`采用接线核定的标签。未平移时间或重采样。

资源现为reference_ready：已为保留的接地/浮动网络固定13个信号、3个时间窗和验收阈值；[独立case报告](../../validation/cases/earthing/validation_report.json)记录PyCy验收结果，资源状态本身不代替算例完成条件。第三个独立开路回路网络未纳入PyCy算例，也未误称为浮动中性点。该发现说明必须用完整接线与独立中性点公式确认传感器方向，不能直接照抄官方绘图变量名。

### SPWM有效参数纠正

原生MATLAB `enumeration('ee.enum.converters.switchingdevice')`返回`gto=1, ideal=2, igbt=3, mosfet=4, thyristor=5, averaged=6`；保护二极管枚举为`none=1, nodynamics=2, chargedynamics=3`。完整stdout与SHA保存在[枚举证据](experiments/switchingdevice_enum_r2025a.json)，原始日志为`local_reference/two_level_pwm/enum.log`。由此确认`VSCSinusoidalPWM`的type1是GTO，Vf=0.6 V生效；`TwoLevelPWMGenerator`的type3是IGBT，Vf=0.8 V生效。静态`TypeOptions`排列和内部`ideal_switch`日志均不足以识别顶层器件类型。负载仍为structure1的纯1 Ω电阻，200 µH字段不生效。有效参数与探针依据分别写入JSON的`enabled_parameters`、`inactive_mask_values`及`parameter_evidence`。原始数据与原SLX均保留。源串R改0 Ω及deadband改0的最小参考仿真均实际成功，因此不把正源电阻或非零deadband误记为软件强制限制；六路offset控制与自动保护二极管的物理差别仍需单独解决。


### TwoLevel资源就绪及首次比较失败

`TwoLevelPWMGenerator.slx`已在MATLAB R2025a Update 1真实运行，最终导出时间2026-11-04 09:03:44 UTC；40001个原生5 µs时间点，0–0.2 s，标准列`time,i_a,i_b,i_c`。原模型和控制拓扑未改：400 V刚性直流源，60 Hz/0.8调制参考、1 kHz开关、100 µs参考保持、每相1 Ω+1 mH浮动星形负载。器件type3由原生枚举确认为IGBT，Vf=0.8 V、Ron=1 mΩ、Goff=10 µS；反并联无动态二极管具有相同Vf/Ron/Goff。物理门极确认Q1/Q2、Q3/Q4、Q5/Q6为A/B/C上下管，记录中严格互补。原Spectrum Analyzer显示还依赖DSP System Toolbox，计算电路依赖MATLAB、Simulink、Simscape和Simscape Electrical。

原SLX的SHA256为`ad8ddf5e46dd633b4853d7694067528d5d20ce78a24059a2847c6a97dbc2ea34`；最终`raw_results/simscape_native.csv`与`normalized_results/reference.csv`均为`6ef09d6e4197ebe603d3cc437bf466154aa8e151e214a0c6fcb24f0e7a0db010`。MAT、原生门极、功率审计、provenance及全部实际字节哈希见JSON对应entry，原件与真实数据保留在忽略的`local_reference/two_level_pwm/`。参考资源因此提升为reference_ready。

既有12依据146a279预先固定的0.1–0.2 s窗口和2% NRMSE限值，首次完整波形比较仍为**FAIL**：A/B/C分别2.6995%、2.6577%、2.7167%；RMS、基波幅值/相位及平均电阻功率特征通过。失败报告及其不可变输入快照保留在本地比较目录，[公开case说明](../../validation/cases/two_level_pwm/README.md)记录边界。官方Natural PWM开关时间算法与PyCy载波逐点比较存在门极差异，IGBT/自动二极管也与双向Ron/Goff开关不同，尚未隔离各项贡献。没有平移时间、拟合幅值或放宽判据，资源数据就绪不代表PyCy对标完成。
