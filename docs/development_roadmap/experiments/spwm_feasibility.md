# B1：官方 SPWM 参考可行性研究

2026-11-04，在本机 MATLAB 25.1.0.2973910（R2025a Update 1）实际运行官方模型。B1 复用既有 `examples/12_two_level_pwm_generator.py`，未新增教学例，未修改其器件、控制、门极或默认参数。当前结论：**真实参考已取得；预设特征指标通过，连续电流波形指标未通过，整体待验证。**

## 1. 来源与模型选择

| 官方参考 | 实际原模型 SHA-256 | 本次用途 |
| --- | --- | --- |
| [Three-Phase Two-Level PWM Generator](https://www.mathworks.com/help/simscape-electrical/ug/three-phase-two-level-pwm-generator.html)，`simscapeelectrical/TwoLevelPWMGeneratorExample` | `ad8ddf5e46dd633b4853d7694067528d5d20ce78a24059a2847c6a97dbc2ea34` | B1 正式比较参考 |
| [Three-Phase Voltage-Sourced Converter (SPWM)](https://www.mathworks.com/help/simscape-electrical/ug/three-phase-voltage-sourced-converter-spwm.html)，`simscapeelectrical/VSCSinusoidalPWMExample` | `5190cbf17c30578d7611f012186a4c736529b8d15c3eab94ffa86bb4f061d81e` | 原模型检查及少量参数可行性探针；不强行匹配例 12 |

官方 SLX、脚本、MATLAB 输出、原生 CSV 和失败日志仅保存在忽略的 `local_reference/` 中。公开仓库只保留本报告、自有导出脚本、验收协议与比较工具，不主张第三方模型或数据的再分发许可。

## 2. TwoLevelPWMGenerator 的实际参数与适用边界

| 项目 | 官方原模型 | 既有例 12 |
| --- | --- | --- |
| DC 侧 | 理想 400 V 电压源直接连接 DC 端，无串联 DC 阻抗或额外 DC 电容 | 理想 400 V 电压源 |
| 三相参考 | 60 Hz，相位 `[0,-120,+120]+90°`，调制比 0.8 | 相同频率、相位和调制比 |
| 参考保持 | 外层 RateTransition 输出周期 100 μs；Integrity/Deterministic 均 on，初值 0 | `floor(t/100μs)` 更新的保持参考 |
| PWM | CPWM/SPWM、Natural，开关频率 1 kHz，离散周期 5 μs；官方块计算导通/关断时间 | 三角载波从峰值开始，在 5 μs 网格直接比较保持参考 |
| 负载 | 浮置星形串联 R-L，每相 1 Ω、1 mH，初始电感电流为 0 | 相同主电路参数与初值 |
| 主器件 | **IGBT**，正向压降 0.8 V，Ron=1 mΩ，Goff=10 μS | 双向 Ron=1 mΩ 理想受控开关；开路不导通 |
| 续流支路 | 各 IGBT 反并联无动态二极管，Vf=0.8 V、Ron=1 mΩ、Goff=10 μS | 无独立二极管 |
| 求解 | Simscape 本地 Backward Euler，5 μs；残差容限 1e-9 | 梯形积分，5 μs |

模型不含死区、热端口或 RC 吸收支路。R-L 块还保留原生 `G_parasitic=1e-6 S` 参数，未为比较而删除。

必须按原生枚举而非下拉框位置解释器件。实际 MATLAB `enumeration('ee.enum.converters.switchingdevice')` 返回：GTO=1、ideal=2、IGBT=3、MOSFET=4、thyristor=5、averaged=6。TwoLevel 的 `device_type=3` 是 IGBT。器件内部日志出现 `ideal_switch`，并不能据此把整个 IGBT/GTO 认作顶层理想开关。已纠正早期检查中的这种误判，整数证据另见 `switchingdevice_enum_r2025a.json`。

IGBT 正向电流经选中的主通道，反向电流经反并联二极管；原生二极管日志中确有约 157 A 的导通电流。因此即使门极互补，仍不能把本参考宣称为 PyCy 自动二极管、死区换流或器件瞬态验证。只有在另外明确选用双向理想通道、规定关断漏电与二极管状态的协议中，才可讨论逐点器件等价。将二极管 Vf 直接设为零也不是普适等价变换：若它与选中的双向通道同时导通，可能改变反向等效电阻。

## 3. 实际门极、方向与时间记录

原模型默认运行 0–0.2 s，得到 40,001 个原生 5 μs 样本。导出器用 `SimulationInput` 明确设置的 Ts、fsw 和 stop time 均等于原始默认值，没有外部 Gate 输入或模型结构修改。

从真实 `Converter.Qk.G`、`vce`、`ice` 和 `diode.i` 日志核对：

- Q1/Q2 是 A 相上/下管，Q3/Q4 是 B 相，Q5/Q6 是 C 相。上管满足 `vce=400-v_phase_pole`，最大恒等式残差小于 6e-13 V。
- 每路物理门极值都是 0/1 V，各相上下门极在全部记录点严格互补；未发现同关或同开。
- 比较列 `i_a/i_b/i_c` 直接取官方绘图同样使用的 `Converter.phase_splitter.i_a/i_b/i_c`。主电路连接和首次 A 相上管导通后的电压、电流增量确认方向为源/转换器流向负载。三相电流和最大残差约 1.03e-12 A。
- 原生参考与既有例 12 门极函数在**相同绝对时间**检查，0.1–0.2 s 每相 20,001 个点中，上管不同的点分别为 A=198、B=194、C=194，约占 0.97–0.99%。没有通过拟合平移消除这些差异。
- 第一处 A 上管导通：官方模型 100 μs，例 12 为 50 μs。后续边沿也有网格差异；不能将两者称为逐点相同门极。

[官方 PWM 文档](https://www.mathworks.com/help/simscape-electrical/ref/pwmgeneratorthreephasetwolevel.html)明确说明该块根据输入计算门极时间，而非直接执行载波比较。模型外层及库内部还包含 RateTransition。额外使用 `SimulationInput` 的 `DataLoggingOverride` 尝试记录未标记的内部参考，MATLAB 实际移除了这些覆盖，未生成 `logsout`；失败日志已保留。未绕过模型编辑技能去改端口日志属性。因此本研究确认了原生参数和最终物理门极，**尚未把约 2° 的电流相位差独立归因到某一级保持或延迟**。

可复现导出脚本为 `validation/cases/two_level_pwm/export_reference.m`。脚本先核对实际 SLX SHA-256、已加载同名模型的路径和未修改状态，避免未来新版本或未保存模型冒用当前来源。输出包括：

- `normalized_results/reference.csv`：原生时间、电流四列 `time,i_a,i_b,i_c`；无时移、幅值拟合或重采样。
- `raw_results/simulink_output.mat`、`simscape_native.csv`、`physical_device_gates.csv`。
- `raw_results/load_power_audit.csv`：端口功率与每相 R=1 Ω 的 `sum(i²R)`；固定验收使用后者比较负载电阻吸收，避免把转换器损耗或电感瞬时储能混入指标。
- `provenance.json`、MATLAB 批处理日志，以及独立门极映射/未平移审计 JSON。

原模型与导出器多次独立运行的电流逐点完全相同。参考 CSV SHA-256 为 `6ef09d6e4197ebe603d3cc437bf466154aa8e151e214a0c6fcb24f0e7a0db010`。

## 4. 先冻结验收，再保留失败结果

提交 `146a279` 在首次数值比较前固定了 0.1–0.2 s、零时移、三相电流工程基准 150 A，NRMSE≤2%、最大误差≤10 A；并同时要求三相总 RMS/60 Hz 基波幅值误差≤5%、基波相位差≤3°、负载平均电阻功率误差≤5%且吸收方向为正。所有条件均须满足。

首次真实比较结果为：

| 指标 | 实际结果 | 预设限值 | 状态 |
| --- | --- | --- | --- |
| A/B/C 波形 NRMSE | 2.6995% / 2.6577% / 2.7167% | 各相≤2% | **失败** |
| A/B/C 最大误差 | 8.764 / 8.680 / 9.096 A | 各相≤10 A | 通过 |
| 总 RMS 相对误差 | 0.565–0.634% | 各相≤5% | 通过 |
| 基波 RMS 相对误差 | 0.568–0.636% | 各相≤5% | 通过 |
| 基波相位差 | 2.072–2.113° | 各相≤3° | 通过 |
| 平均电阻吸收功率 | PyCy 33,689.24 W；参考 33,294.58 W；误差 1.185% | ≤5%，方向为正 | 通过 |

整体为 **FAIL**，不能标为完成的跨平台验证。门极边沿、IGBT/二极管压降、漏电与积分方法存在已知差别，但当前实验未分别隔离其误差贡献；不能把失败单独归因于任何一项，也不能据此判定 PyCy 主求解器存在缺陷。保留全部原始比较目录和输入快照，导出器完善后由根代理统一再次比较，数值参考和阈值不变。

若继续此题，必须先另行冻结物理参数与控制协议，逐项隔离器件、采样和积分差别；不得看结果后平移波形、调整调制比/门极、放宽本次阈值，或把特征通过改写为整体通过。

## 5. VSCSinusoidalPWM 的少量真实探针

该模型实际默认是 100 V 源、串联 DC 电阻 0.1 Ω、DC 电容 5000 μF；每相额外纯电感 500 μH 后接纯 R=1 Ω 浮星负载。负载掩码中显示的 L=200 μH 在 `component_structure=1` 下未启用，不能误记为额外 R-L 负载。

转换器 `device_type=1` 实际为 **GTO**，其 Vf=0.6 V、Ron=1 mΩ、Goff=1 μS 是活动参数，门极开/关阈值 0.5/0.1 V，维持电流 1 A；另有 Vf=0.8 V、Ron=1 mΩ 的无动态保护二极管。控制用六个相差 60° 的偏移同时影响正弦和三角支路，默认三角倍数 40，即 60 Hz 基准下约 2400 Hz；有符号门极和 deadband 也与例 12 的简单互补比较器不同。

| SimulationInput 单项探针 | 实际结果 | 能说明什么 |
| --- | --- | --- |
| `triangleMultiPulse=50/3`，尝试 1000/60 倍数 | 仿真在 LUT 的 `repmat` 整数重复因子检查处失败 | 不能仅将现有倍数参数改成分数就得到目标 1 kHz |
| DC 串联 `R=0` | 真实仿真成功，0.01 s、2501 样本 | 此实例允许精确零电阻；不能声称工具强制正电阻 |
| `deadband=0`、`ts=100 μs` | 真实仿真成功，0.01 s、708 样本 | 可运行不意味着六路相移控制已等价为例 12 门极 |

这些探针及默认运行原件保存在 `local_reference/vsc_spwm/`。没有把其结果当作已匹配例 12 的正式参考，也没有为匹配它重写既有控制或新增同题例子。
