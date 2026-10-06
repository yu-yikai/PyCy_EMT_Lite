# 三端两电平 VSC-HVDC 综合仿真示例

[English](three_terminal_vsc_hvdc.en.md) · [运行入口](../README.zh-CN.md) · [示例源码](../examples/18_three_terminal_vsc_hvdc.py)

本例复现参考 Benchmark 的三端核心电路和控制职责，采用真正参与 MNA 的 18 个理想开关。
它是来源明确的教学重实现，**不是已经通过逐波形验收的 1:1 跨平台复现**。
控制增益、测量滤波、启动、故障清除缓冲和数值方法有调整，具体见下文。
基础模型的推导见[元件推导](component_derivations.md)，其中第 9 节解释变压器矩阵，第 11–12 节展开滤波、dq 控制与六开关桥的盖章，第 13–15 节说明初值、事件及能量核对。

建议先完成示例 [05 三相网络](../examples/05_three_phase_steady_state.py)、[11 PLL](../examples/11_pll_dynamic_response.py) 和 [12 PWM](../examples/12_two_level_pwm_generator.py)。
首次运行本例先看[第 10 节模式](#10-simulation-modes)，使用默认 FAST；再对照[第 6 节拓扑](#6-final-topology)、[第 7 节控制职责](#7-station-controls)阅读源码，最后用[第 12 节验证](#12-validation)解释结果。第 1–3 节保留参考来源与模型映射，便于核对来源。

## 1. Reference Benchmark

唯一主要电气参考为 DIgSILENT 发布的 **MATLAB-Simulink Three-Terminal Two-Level VSC-HVDC Benchmark**。
[官方发布页](https://www.digsilent.de/index.php/en/faq-reader-powerfactory/benchmark-of-a-three-terminal-vsc-hvdc-system-in-powerfactory.html)
同时提供白皮书及 PSCAD/Simulink 模型；本例以其中的 Simulink 模型为主参考，不混入其他 HVDC 示例作为主参考。

参考文件可从上述官方发布页获取；下表列出本次核对的文件名与 SHA-256，用于识别所用版本。
核对内容包括 PDF 第 1–4 页、SLX 的元件掩膜/连接线及参数脚本；PDF 第 2/3 页的拓扑与控制图另外做了图像检查。

| 文件 | SHA-256 |
|---|---|
| `Three_terminal_VSC_HVDC_MATLAB_Simulink.slx` | `25c643eb66cbe97842229d046c55fe32a6f71b7a6cc7bc1b6a5617d51cd76e92` |
| `Parameterisation_Three_terminal_VSC_HVDC_MATLAB_Simulink.m` | `bfe8c4b05de6feae1dc376bc4fbee1664018c6b9bbc57ea06a6381bdc6d6133d` |
| `HVDC-VSC-2L-Benchmark.pdf` | `4f12fc424fcd96475a181a73f16f3f3baec4ab93c4fd6c876c7e771a101cba43` |

原文件保持不变。R2022b 运行使用参考模型的独立副本，先运行参数脚本，再使用 `Simulink.SimulationInput`。
原设置 2 μs、1980 Hz、2.5 s 的运行已完成；另外开启 Scope 记录，以 50 μs 间隔导出 Vdc1/2/3。
R2022b 报告了转换器布尔比较参数 0.5 量化为 1 的警告，因此该运行也不能当作无条件认证的参考数据。

## 2. Benchmark Analysis

- 三个站分别接入 420 kV/60 Hz、420 kV/50 Hz、500 kV/50 Hz 电网；额定电压均为线电压 RMS。
- 三台换流变均为 1500 MVA、低压 230 kV，Yg/Yn；低压中性点经 1 MΩ 接地，并非 Y/Δ。
- 每站有 72.4 mH 相电抗器、接地高通滤波器、两电平桥和分裂直流电容。
- DC+ 与 DC− 各通过 T 型 RLC 线路形成 1–2、1–3 分支；没有 2–3 直连。
- VSC1 负责 Vdc/Vac，VSC2 从交流侧吸收 200 MW，VSC3 向交流侧送出 200 MW；后两站均调节 Vac。
- 原例为三个独立 PLL、dq 电流内环、PI 电压外环及载波 PWM；故障位于 VSC3 换流变高压侧，三相接地，1.5–1.65 s。

1500 MVA 是变压器铭牌容量；本例仅验证约 ±200 MW 的运行点，不声称验证了额定满载能力。
不能只读参数脚本：脚本遗留的 `Filter.Lf/Rf/Cf` 没有决定当前 SLX 高通滤波模块，实际模块使用 Qc、调谐频率和品质因数。

## 3. Benchmark Mapping

| Reference Benchmark | PyCy-EMT Implementation |
|---|---|
| 2-level VSC switching devices | 每站六个 `IdealSwitch`，真实写入 MNA；不是受控电压源替代 |
| AC system with internal R/L | `ThreePhaseSource` + `ThreePhaseLine` |
| Converter transformer Yg/Yn | `ThreePhaseTransformer`，一次侧集中漏感 + 中性点 `Resistor` |
| Phase reactor | `ThreePhaseLine`，R=0、L=72.4 mH/相 |
| Split DC capacitor | 每站两个 `Capacitor`，各 300 μF、初值 200 kV |
| Bipolar T-type DC line | 每极两段 `Resistor`/`Inductor` + 中点对地 `Capacitor` |
| Grounded high-pass filter | 每相 C 串联 (L ∥ R)，用现有基础元件组合 |
| Independent SRF-PLL | 三个 `SRFPLL`，测量各自高压 PCC |
| abc/dq and inverse | `abc_to_dq` / `dq_to_abc`；幅值不变 |
| PI controllers | `PIController`，原有冻结式 anti-windup；外加下游限幅积分冻结 |
| SPWM | `triangular_carrier` + `carrier_compare` + 互补 gate callable |
| AC fault and clearing | 三个 `Fault` + `FaultApplyEvent` / `FaultClearEvent` + 现有 `EventQueue` |
| Controller/network coupling | `CaseDefinition.on_step` → `Simulator.on_step`，每个求解点的步后回调 |

## 4. 实现与测试入口

| 文件 | 用途 |
|---|---|
| [示例 18](../examples/18_three_terminal_vsc_hvdc.py) | 参数、单站接线、双极线路、三站组合、故障、指标与绘图 |
| [controls/vsc.py](../pycy_emt_lite/controls/vsc.py) | 共用站控制器与控制参数；每站独立状态 |
| [系统测试](../tests/test_three_terminal_vsc_hvdc.py) | 单站开环/闭环、双站、三站 FAST、PWM、端口功率与 DC 离散能量 |
| [回调测试](../tests/test_step_callback.py) | 初值/事件采样顺序、下一步作用、只读输入、结果抽样 |
| 本文及英文伴随文档 | 参数来源、控制推导、运行和验证边界 |

电路推进使用现有 `Circuit/Simulator`；步后回调的时间约定见[数值约定](numerical_conventions.md#time-grid)。

## 5. 共用求解与结果接口

`core/simulation.py` 提供可选步后回调与结果抽样；`cases.py` 将算例的回调传给仿真器。
`io/results.py` 改用有序字典去重结果字段，避免数百列综合结果反复进行线性成员查找；仍保留首次出现顺序及后续新增列。
NPZ 读取改为每列从归档加载一次，再组装结果行；原先逐行反复加载整列不适合此例的大结果。
1001 行、21 列的读回核对由约 0.646 s 降至 0.00374 s，数据相同；完整 50001 行、377 列压缩结果约 2.46 s 读回。
文件职责和具体函数入口见[数值约定的源码阅读表](numerical_conventions.md#source-route)。

故障投入发现高压过零条件下的初值检查误报，已用四元件电路复现并加入
[基础测试](../tests/test_basic_components.py)：1 nV 电压源、两个 1 Ω 电阻和初充 200 kV 的电容。
LU 解的约 10 pV 消减误差会超过近零源约束的原绝对容差。
现在仅在一致解未通过原检查时补求一次 `A δx=b−Ax`，再按**原阈值**复查；没有放松初值容差或允许冲激。

## 6. Final Topology

```text
Grid1 420 kV/60 Hz -- Rg,Lg -- HV1 -- Yg/Yn T1 -- LV1 -- Lphase1 -- 6 switches VSC1
Grid2 420 kV/50 Hz -- Rg,Lg -- HV2 -- Yg/Yn T2 -- LV2 -- Lphase2 -- 6 switches VSC2
Grid3 500 kV/50 Hz -- Rg,Lg -- HV3 -- Yg/Yn T3 -- LV3 -- Lphase3 -- 6 switches VSC3
                                |               |
                       S3 three-phase fault     C -- (L || R) -- ground [each station]
                       and finite RC snubber

DC+1 -- R,L -- Cmid-to-ground -- R,L -- DC+2
  |
  +---- R,L -- Cmid-to-ground -- R,L -- DC+3
DC-1 -- R,L -- Cmid-to-ground -- R,L -- DC-2
  |
  +---- R,L -- Cmid-to-ground -- R,L -- DC-3

Each station: DC+ -- 300 uF -- ground -- 300 uF -- DC-
Each transformer: LV neutral -- 1 Mohm -- ground
Each S1/S2/S3 HV phase -- 1 Mohm -- ground
```

T 型线路图中 Cmid 是从中点向地的并联电容，不串联在 DC 通道中。
桥上下管分别连接 DC+/DC−；直流源仅在单站中间验证中使用，最终三站模型没有独立直流电压源。

## 7. Station Controls

| 站 | 参考职责 → 本例实现 | 正方向 |
|---|---|---|
| S1 / VSC1 | Vdc + Vac → DC 电压 PI 给 Id*，AC 电压 PI 给 Iq* | 补偿系统损耗/暂态；P 可正可负 |
| S2 / VSC2 | P + Vac → `Id*=P*/(1.5 Vd)`，Vac PI 给 Iq* | P*=+200 MW，AC → converter |
| S3 / VSC3 | P + Vac → 同上 | P*=−200 MW，converter → AC |

所有站 `Pac>0` 表示 AC → converter；测量面在相电抗器的交流端。
`Q>0` 表示从 AC 吸收感性无功；`Pdc>0` 表示 converter → DC 网络。
因此稳态 DC 账为 `ΣPdc=线路电阻损耗`；动态时还须加上电容、电感储能变化。
电抗器交流端 Pac 与桥交流端功率还相差电抗器储能变化，不能直接相减后称为半导体损耗。

## 8. Control Architecture

项目实际变换为 `d=α cosθ+β sinθ`、`q=−α sinθ+β cosθ`，θ 正向旋转，d 对齐电压空间矢量。
对 a 相正弦源，理想初始空间角为 −π/2，不是 0；无零序时逆变换严格对应。

```text
P = va ia + vb ib + vc ic
P = 1.5 (vd id + vq iq)             [zero sequence absent]
Q = 1.5 (vq id - vd iq)
L did/dt = vg_d - vc_d + omega L iq
L diq/dt = vg_q - vc_q - omega L id
vc_d* = vg_d + omega L iq - PI(Id* - Id)
vc_q* = vg_q - omega L id - PI(Iq* - Iq)
```

前馈取实测低压电抗器端电压，PLL/Vac 测量取本站高压 PCC。电流内环模型仅含相电抗器，换流变漏感已在网络中单独建模，不重复计入。
P 保留实际 abc 零序功率；dq 控制不增加零序调节环。
调制经 dq→abc、按实测 Vdc/2 归一化，与三角载波比较；下管为上管逻辑反。
无载额定调制比 `2 sqrt(2/3)×230/400≈0.939`；控制将 dq 电压矢量限制在 m≤0.98。

各站独立 PLL 使用现有归一化 Vq 输入和 PI；角频率限额为本站额定值 ±10 Hz，传入 PLL 时换成 rad/s。
低压 dq 电压、Vac、Vdc 采用 1 ms 一阶低通；dq 电流采用 0.2 ms 低通。
三种模式均在每个 EMT 求解点更新 PLL/内外环，PWM 同样按 EMT 网格取样；没有暗藏另一套多速率调度。

回调顺序为：积分/求解 → 更新元件 → 应用显式事件并求右侧一致解 → 形成只读测量行 → 一次控制回调 → 保存所选结果。
回调在 t=0 只观察/初始化，不调用零间隔 PI/PLL；正时刻使用实际采样间隔。
调制更新仅作用于下一网络步，无代数控制环；事件左侧与右侧求解不会重复推进控制器。
`m{a,b,c}` 对应刚完成网络求解使用的保持值，`m{a,b,c}_next` 对应本次新命令。

电容初充至额定极电压，DC 线路中点电容也预充；交流滤波/RC 电容使用额定正弦电压初值，所有电感电流从零开始。
这是预充启动，**不是完整潮流稳态初始化**。P 命令在 0.02–0.12 s 线性建立，启动暂态保留在结果中。
初次 PCC 幅值足够时 PLL 用实测空间角初始化，否则保留额定正弦源的空间角先验，后续仍由本站电压闭环同步。

## 9. Main Parameters

| 参数 | 值 | 来源 |
|---|---|---|
| 三站 HV 电压、频率 | 420/420/500 kV；60/50/50 Hz | Reference Benchmark：脚本、SLX、PDF |
| 换流变容量/LV 电压 | 1500 MVA / 230 kV | Reference Benchmark |
| 源阻抗 | 4.59 Ω；L=26.04/(2πf) H/相 | Reference Benchmark |
| 变压器漏阻抗 | R=0；总 X=0.10 pu；L=0.10 VHV²/(Sbase 2πf) | Reference 两绕组各 0.05 pu，集中到一次侧 |
| 相电抗器 | 72.4 mH/相，R=0 | Reference Benchmark |
| DC 电压/电容 | ±200 kV；每极每站 300 μF | Reference Benchmark；极间等效电容为 150 μF |
| DC 线路每极每半段 | R=7 Ω、L=0.596 H；中点 C=26 μF 对地 | Reference SLX 接线与脚本；每极全长 R=14 Ω、L=1.192 H |
| LV 高通滤波器 | Qc=75 Mvar、fr=450 Hz、q=0.08、接地 Y | Reference SLX，而非脚本遗留滤波参数 |
| 滤波器元件换算 | `C=Qc[1−(f/fr)²]/(2πf VLL²)`，`L=1/[(2πfr)² C]`，`R=q√(L/C)` | 二阶高通等效公式；未逐项校准 SPS 内部实现 |
| 开关 | Ron=0.005 Ω、Goff=1 μS | Ron/关断电阻取 Reference；双向电导模型为简化 |
| PLL Kp/Ki | 80 / 1000 | PyCy-adjusted；不是对原脚本 Ti 的直接换算 |
| 电流 PI Kp/Ki | 60 V/A / 6000 V/(A·s) | PyCy-adjusted |
| Vdc PI Kp/Ki | 0.05 A/V / 1.1 A/(V·s) | PyCy-adjusted |
| Vac PI Kp/Ki | 10000 A/pu / 400000 A/(pu·s) | PyCy-adjusted，适应显式闭环与短 FAST 启动 |
| 参考电流矢量/调制限制 | 1500 A / 0.98 | PyCy-adjusted；d 轴优先，Iq 用剩余圆形裕量 |
| 故障 Ron/原缓冲 R | 5 Ω / 1 MΩ | Reference SLX |
| S3 高压侧附加串联 RC | R=200 Ω，C=0.5 μF/相 | PyCy-adjusted，有限故障清除缓冲；不是原模型参数 |

原脚本控制量含 kV、kA、MW 和自定义 Ti 表达式；本例没有机械复制数值。
高通滤波器结构可参照 [MathWorks 官方模型说明](https://www.mathworks.com/help/sps/ref/passiveharmonicfilterthreephase.html)。

## 10. Simulation Modes

```bash
uv run python examples/18_three_terminal_vsc_hvdc.py
```

在脚本顶部设置 `MODE`；也可在 Python 中调用 `define_case("FULL")` 再交给现有 `run_case()`。

| 模式 | EMT 步长 | PWM | 时长 | 故障投入/清除 | 结果保存间隔 |
|---|---|---|---|---|---|
| FAST（默认） | 20 μs | 1000 Hz | 0.8 s | 0.30 / 0.45 s | 20 μs |
| FULL | 5 μs | 1980 Hz | 2.5 s | 1.50 / 1.65 s | 50 μs |
| BENCHMARK | 2 μs | 1980 Hz | 2.5 s | 1.50 / 1.65 s | 50 μs |

全部采用现有后向欧拉 MNA，不自动定位 PWM 连续时间交点。
FULL/BENCHMARK 通过 `record_every=10/25` 控制内存；控制与网络仍每步执行，初始点、事件点、终点始终保存。
`result.time_step` 是 EMT 步长，统计必须读取实际 `time` 列，不能把结果抽样间隔当成积分步长。
50 μs 输出足以观察低频动态及粗略 PWM，不用于精确边沿时间或谐波幅值验收；需要时把 `record_every` 改为 1，缩短仿真窗口。
后向欧拉会耗散开关纹波能量，FAST 尤其明显；不能据其 AC 功率差估算真实转换效率。

默认只显示、不保存；使用顶部两个保存开关输出 CSV/JSON/NPZ 和各图到 `outputs/three_terminal_vsc_hvdc_<mode>/`。
大规模数据宜用 NPZ；标准 `run_case()` 开启数据保存时仍按项目约定同时写三种格式，磁盘占用会较大。

## 11. Fault Case

S3 换流变高压 PCC 三相各经 5 Ω 接地，持续 150 ms；FULL/BENCHMARK 采用原时序。
FAST 将投入提前到 0.30 s，仍保留 150 ms 持续时间；来源为白皮书第 4 页和参数脚本。
各站每个 HV 相均有 1 MΩ 对地支路，S3 原故障模块的缓冲支路也保留。S1/S2 的对地支路同样属于当前实际拓扑，不应只把 S3 画出或当作故障投入时才存在。

严格保持电感电流时，原纯电阻缓冲结构在清除瞬间会产生约 14 GV 的代数尖峰：清除前的故障电流必须瞬间改经 1 MΩ 支路。
本例在 S3 每相增加独立的有限串联 RC 缓冲，为电流换流提供储能通路。
该调整影响故障前无功与清除暂态，不能声称清除波形与原模型等价。
FAST 仍出现约 3.13 MV 的短时高压侧峰值；这只是所声明简化电路的结果，不用于开断过电压或绝缘配合分析。
没有避雷器、电弧、自然过零开断、保护整定或 VSC 闭锁模型。

## 12. Validation

每站记录 Vdc、P/Q、Vac、Id/Iq 与参考值、PLL 角度/频率/Vq、当前/下一步调制；18 个门极状态和支路电流均由实际网络记录。
同时记录两条双极 DC 线路各半段电流、各站 Pdc、分裂电容储能和 DC 全网络储能/损耗/功率残差。
默认绘制三站电压、P/Q、Vac、各站 Id/Iq 跟踪、PLL 频率、故障相电压/电流、DC 电流及 0.2–0.203 s PWM 局部图。

统计窗口为：FAST 0.18–0.28 s / 0.70–0.80 s；FULL/BENCHMARK 1.38–1.48 s / 2.40–2.50 s。
每个窗口为 0.1 s，包含六个 60 Hz 周期和五个 50 Hz 周期，不跨显式故障事件。
前后窗口报告时间加权均值，电流误差为 `|mean(I)−mean(I*)|`，**不是瞬时纹波 RMS 跟踪误差**。
前后窗口边界不落在采样点时，先按分段线性信号插值补端点，再积分完整声明窗口；结果必须覆盖两端。
`fault:S3:Vac_pu_mean` 保留故障内区间（投入后20ms至清除前20ms）的采样算术均值；非均匀采样时它不等于时间加权均值，窗口无采样点时明确报错。
均值只衡量偏置。当前汇总另报告分段线性信号的频差/Vq/dq 误差 RMS、窗口内 Vd 最小值，以及 `control_accuracy_met`。该标志要求频差 RMS<0.05 Hz、Vq RMS<0.01 pu、Id/Iq 误差 RMS<25 A 且 Vd>0；不能用有符号均值抵消振荡后代替精度验收。`PLL_Vq_pu` 现与内部 PI 相同，使用 `Vq/max(|Vd|,|Vq|,1 V)`。

2026-10-05/06的当前代码复验使用默认PLL增益Kp=80、Ki=1000和FAST的20 µs步长。下表为三站范围；Id/Iq合并列出。Vd最小值均为正，六个站/窗口的严格精度标志均为0：**验收假通过已纠正，默认FAST严格控制精度仍未达标。**

| 瞬时误差的分段线性RMS | 前故障 | 恢复窗口 | 严格门槛 |
|---|---:|---:|---:|
| 频差/Hz | 0.336–0.445 | 0.331–0.460 | <0.05 |
| PLL Vq/pu | 0.02641–0.03495 | 0.02613–0.03613 | <0.01 |
| Id/Iq跟踪/A | 148.4–170.7 | 147.9–171.6 | <25 |

后续调查只解释误差与候选试验，不替换默认结果。详细公式、逐站数值和原始证据集中保存在总文档：

| 记录（2026-10-06） | 结论及证据范围 |
|---|---|
| [R7独立核定](audit_20261005/项目问题与改进计划.md#r7-control-diagnosis) | 24项RMS与现有汇总最大差2.59e-12（原单位）；投影、P/Q、PLL/PI、滤波、调制及18个门极核对通过，未确认新实现错误。理想平衡PCC的离线频差约1e-12 Hz；离线输入对照不证明闭环电流达标。 |
| [R8试验方案](audit_20261005/项目问题与改进计划.md#r8-accuracy-design) | 分开定义原始严格RMS、低频跟踪、PWM纹波和外部频率估计，保持门槛；滤波及标量电流环推导只用于设计，不证明包含PWM/网络耦合的三站稳定性。 |
| [R9隔离试验](audit_20261005/项目问题与改进计划.md#r9-pll-experiment) | Kp=80/40、20/10 µs共四组，固定1000 Hz PWM、0–0.8 s与0.3/0.45 s事件。20 µs基线与R7数组逐值一致；候选HF频差比为0.4923–0.5176 / 0.4988–0.5018，但原始频差仍为0.1562–0.2315 Hz、dq误差143.0–171.4 A，四组24个严格标志全为0。 |
| [R10离线复核](audit_20261005/项目问题与改进计划.md#r10-rejection-review) | 24条交叉PLL回放；12条自身输入/原增益频率最大差7.11e-15 Hz。S3恢复固定输入下的HF频差比为0.49984–0.50018，低频频差/Vq比却为1.940–3.181 / 1.267–1.349；增益变化本身已能产生该低频退化。 |

频带和平滑量只是诊断口径。R7 DFT每窗5000点、10 Hz间隔、无加窗，≥500 Hz为诊断分界；采样均方不替代分段线性RMS。默认结果中的滤波电流反馈、1 ms周期均值及S1低频Iq仍有不达标项，具体频谱和数值见R7/R8。不能删除纹波或换成平滑信号后宣称全部达标。

**Kp=40候选已拒绝，默认80/1000保持。** R9的S3恢复低频频差增至基线2.220/2.423倍；20 µs/S1及10 µs/S2清除采样电流峰值分别增加7.884%/5.765%，超过预定5%上限。24次现有集成检查及独立控制/积分检查通过，只说明相应保护通过。10 µs同时细化电气积分和控制采样，两档对照不证明连续物理精度或收敛阶。

清除峰值在基线/候选的不同相、不同时间出现；R10核对匹配点的控制时序、电感压降和网络状态，所列点未发生调制矢量饱和。记录支持网络耦合解释，未唯一定位导致退化的环节，也不能排除更早饱和影响。离线PLL不重新生成网络电流，RMS比例不能相加分解因果贡献。调查与文档收尾已完成；当前状态和独立未来计划见[总文档](audit_20261005/项目问题与改进计划.md#delivery-status)。

以下 FAST/FULL/BENCHMARK 表格及其耗时、跨模型对照来自原文保留的历史记录；原生产提交、完整 Python/数值库环境和命令未完整绑定，标为未核定。当前纠错/调查阶段只重跑过FAST，未重跑FULL/BENCHMARK；R11仅整理文档，不以历史均值证明当前RMS精度或商业模型一致性。

历史 FAST 结果（20 μs、1000 Hz）：

| 指标 | 故障前 | 恢复窗口 |
|---|---:|---:|
| S1 Vdc / kV | 399.401 | 399.995 |
| S2 P / MW | 198.961 | 198.223 |
| S3 P / MW | −203.870 | −204.457 |
| 三站最大平均 PLL 频差 / Hz | 0.00105 | 0.00478 |
| 三站最大 dq 平均跟踪误差 / A | 5.28 | 3.63 |
| DC 储能变化功率 / MW | 2.865 | 0.121 |

全部结果有限，Vdc 全时域范围 338.748–475.492 kV，故障中段 S3 Vac 平均约 0.18783 pu。
DC 瞬时功率账最大残差约 0.0273 W；FAST 网络 131 个 MNA 未知量，单独仿真约 29.9 s（不含大文件保存/绘图）。
这些是指定本机的一次本地测量，不是跨硬件性能承诺。

原历史记录记载：FULL与BENCHMARK已完成，并通过有限值与Vdc/P/Vac/PLL/dq均值及DC功率阈值核对。
两者各保存 50001 行、377 列；网络仍为 131 个未知量。

| 指标 | FULL 故障前 | FULL 恢复 | BENCHMARK 故障前 | BENCHMARK 恢复 |
|---|---:|---:|---:|---:|
| S1 Vdc / kV | 399.984 | 400.005 | 399.995 | 400.014 |
| S2 P / MW | 200.171 | 200.072 | 200.078 | 200.147 |
| S3 P / MW | −202.354 | −202.314 | −202.335 | −202.392 |
| 三站最大平均 PLL 频差 / Hz | 0.000322 | 0.000955 | 0.000205 | 0.000357 |
| 三站最大 dq 平均跟踪误差 / A | 0.753 | 0.664 | 0.152 | 0.226 |
| DC 储能变化功率 / MW | 0.261 | 0.624 | 0.242 | 0.788 |

FULL/BENCHMARK 单独仿真耗时约 328.9/800.9 s，DC 功率残差最大值约 0.03212/0.03250 W。
故障中段 S3 Vac 均约 0.188 pu；全时域 Vdc 分别为 334.860–486.098 / 334.999–488.213 kV。
在已保存的 50 μs 网格上，S3 高压侧峰值为 3.186/3.198 MV，相电抗器电流峰值为 7.366/7.434 kA。
这些峰值进一步说明参考限流不等于实际故障电流受限；未保存的步间峰值可能更大。

同 PWM、同物理参数的 5/2 μs 对照采用完全对应的 50 μs 输出时间点，逐点
`RMSE=sqrt(mean((V5us−V2us)^2))`，`NRMSE=100×RMSE/400000 V`。

| 窗口 / s | S1 RMSE / V | S2 RMSE / V | S3 RMSE / V | 三站最大 NRMSE / % |
|---|---:|---:|---:|---:|
| 1.38–1.48 | 138.712 | 263.552 | 229.147 | 0.06589 |
| 1.50–1.80 | 213.064 | 315.928 | 1083.627 | 0.27091 |
| 2.40–2.50 | 155.390 | 310.710 | 159.462 | 0.07768 |

每段包含两端点，样本数分别为 2001/6001/2001。这是步长敏感性检查，不是证明 PWM 波形具有某阶收敛。
例如故障前 S1 的 Pac 均值在 FULL/BENCHMARK 中为 25.684/21.092 MW，仍受开关纹波与数值耗散影响。
不能因为 Vdc 接近，就把 AC 功率差解释为已收敛的真实损耗。

另将 BENCHMARK 与隔离副本导出的原 Simulink Vdc 在相同网格比较。
1.50–1.80 s 的 S1/S2/S3 RMSE 分别为 10.464/11.747/48.686 kV，按 400 kV 归一化为 2.616/2.937/12.171%。
这直接表明故障动态存在明显跨模型差异；没有通过精确复现验收。
上述数值为已执行的验证记录，原始仿真结果不随 Git 分发；运行与结果保存方法见第 10 节。
验证所用的两组压缩 NPZ 遵循项目标准 schema，可由 `SimulationResult.from_npz()` 读回，含 EMT 步长、方法和事件日志。

功率核对包含独立的桥端口式 `Pac_bridge=Pdc+ΣGsw Vsw²`，以及 DC 网络后向欧拉能量式：

```text
E[k] - E[k-1] = h (sum(Pdc[k]) - sum(R i[k]^2))
               - 0.5 sum(C (v[k]-v[k-1])^2)
               - 0.5 sum(L (i[k]-i[k-1])^2)
```

最后两项是数值耗散，不是导通/开关器件损耗。事件跨越区间因只保存右侧量，从此项积分检查中排除；事件时刻另核对状态和 KCL。
R2022b 原模型故障前 Vdc 均值约为 399.987/413.507/385.358 kV，用于核对电压等级和功率流方向；存在上述模型差异，不能只凭接近的均值认定跨平台通过。

## 13. Tests

```bash
uv run pytest tests/test_step_callback.py tests/test_three_terminal_vsc_hvdc.py
uv run pytest
```

Windows的锁定环境、创建.tmp父目录和项目内basetemp命令见[README测试说明](../README.zh-CN.md)；首次运行测试先完成这些步骤。

分阶段检查为：单站开环开关/端口功率 → 独立 PLL 扰动恢复与 dq 跟踪 → 20/10 μs 同 PWM 平均功率对照 → 双站交换/Vdc 调节 → 三站 FAST → 故障与恢复。
单站验证可以用恒定 DC 源；最终三站测试明确检查 18 个开关、三台换流变和实际动态 DC 网络。
共享 FAST fixture 避免每项指标重复运行整个系统。

关键阈值为：平均 PLL 频差 <0.05 Hz、平均 Vq <0.01 pu、S1 平均 Vdc 误差 <1%、P2/P3 平均误差 <5%、Vac 平均误差 <2%、dq 平均误差 <25 A、DC 功率残差 <1 W。
另外独立核对门极/载波、桥节点 KCL、导通损耗、DC 离散能量及故障电阻电流。
历史验收记录：全回归681项、14个无界面示例及NPZ读取修改后的7项读写/绘图测试通过，50001×377的两组结果完成标准格式读回。生产版本/环境/命令绑定限制见第12节，不能作为当前重新执行的结果。
2026-10-05的R5主环境（CPython3.14.6）和R6干净副本（CPython3.14.2）分别完成832项全量回归及14个默认示例，见[总计划R5](audit_20261005/项目问题与改进计划.md#r5-follow-up)和[R6](audit_20261005/项目问题与改进计划.md#r6-delivery)。旧测试与阈值保持；R11只进行文档核对，未重跑全量回归。以上为相应本地证据，不代表远端CI，也不证明第12节的严格控制精度达标。

## 14. Deviations From Reference Benchmark

| 项目 | 差异及影响 |
|---|---|
| 半导体 | 双向 Ron/Goff 开关，无独立反并联二极管，不能复现关断闭锁后的整流通路 |
| 变压器 | 保留 Yg/Yn、变比、接地和总漏感；忽略 1e10 pu 励磁分支及共同铁芯 |
| DC 网络 | 保留双极 T 型集中 RLC；中点电容预充，启动不与原零初值一致 |
| 控制 | 保留站职责/PLL/dq/SPWM；SI 增益重选、测量低通、冻结式 anti-windup；不是原回算式实现 |
| 调制/限流 | m≤0.98，参考电流矢量限幅；原模型的限幅、初始化及器件细节不同 |
| 故障清除 | S3 增加 200 Ω/0.5 μF 串联 RC 缓冲，改变无功与清除暂态 |
| 求解 | 后向欧拉、步后显式控制、网格采样门极；原 Simulink 配置为 ode4 + SPS 离散网络 |
| FAST | 放大步长、降低 PWM、缩短时长、提前故障；仅用于开发回归 |

## 15. Remaining Limitations

本模型可称为 **Two-level VSC modeled using ideal switching devices**，不能称为完整器件级 IGBT 模型。
没有 dead time、独立二极管反向恢复、半导体开关损耗、温升、饱和励磁、宽频/频变 DC 电缆、负序控制或弱网稳定性验证。
开关 Ron/Goff 会产生电阻损耗，后向欧拉另有数值耗散，两者必须分开。
1500 A 限制作用于 Id/Iq **参考**，不是把实际电流裁剪到 1500 A；故障初期实际电流可超出参考限制。
不含同步机、AVR、调速器、发电机侧线路、MMC、DC 故障/DC 断路器、复杂保护或 grid-forming 控制。
故障后恢复、功率守恒和细步长对照支持这个具体示例的教学用途，不等同于所有运行点的物理验证。
