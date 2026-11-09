# 既有12：两电平PWM逆变器的真实参考补验证

本任务补充 `examples/12_two_level_pwm_generator.py` 的外部证据，不改动教学算例，也不计入正式新增算例数量。来源为 MathWorks [Three-Phase Two-Level PWM Generator](https://www.mathworks.com/help/simscape-electrical/ug/three-phase-two-level-pwm-generator.html)，模型 `TwoLevelPWMGenerator.slx`。本机真实执行环境为 MATLAB R2025a Update 1、Simulink、Simscape、Simscape Electrical；原Spectrum Analyzer显示还依赖DSP System Toolbox。第三方模型、真实波形和图仅保存在忽略的 `local_reference/two_level_pwm/`，不主张再分发许可。

## 物理映射与边界

两侧均为400 V直流源、三相两电平桥和浮动星形R-L负载，每相1 Ω、1 mH，初始电流0；基波60 Hz，调制比0.8，载波1 kHz，调制参考100 μs保持。PyCy以5 μs网格直接比较三角载波和保持参考；官方PWM模块采用Natural算法计算开关时间。它们没有通过波形拟合、延迟补偿或振幅修正对齐。

已实际核验官方活动器件枚举为 **IGBT**，不是根据未启用mask字段推断器件。IGBT的Vf为0.8 V、Ron为1 mΩ、Goff为10 μS；反并联二极管无动态，Vf为0.8 V、Ron为1 mΩ、Goff为10 μS。Q1/Q2为A相上下管、Q3/Q4为B相、Q5/Q6为C相，已记录的0/1 V物理门极在每个桥臂严格互补，无同关区间。PyCy使用现有受控双向Ron/Goff开关，Ron为1 mΩ，没有自动二极管或IGBT压降模型。本对比只验证声明配置的负载电流与稳态特征，不能证明器件模型等价或自动续流能力。

参考列为 `time,i_a,i_b,i_c`，40001个原生5 μs时间点，范围0–0.2 s。三相电流正方向均从桥臂流向负荷，分别映射到 `i:La,i:Lb,i:Lc`。方向通过A上管首次导通时的相端电压与正向di核定，浮动星点三相电流和也独立检查。活动器件电压、电流及二极管支流保留在本地原始记录中；完整参数及来源由实际导出器的provenance记录。

## 候选比较前冻结的验收

[manifest.json](manifest.json) 和 [parameters.json](parameters.json) 在首次PyCy对商业结果比较前提交于 `146a279`。窗口固定为0.1–0.2 s，含6个60 Hz基波周期和100个载波周期；零时移，不能按结果修改阈值。

- 每相完整电流波形：固定150 A工程基值，NRMSE ≤ 0.02，最大绝对误差 ≤ 10 A。
- 每相总RMS与基波RMS：相对真实参考误差分别 ≤ 5%。
- 每相基波相位：以绝对时间60 Hz正弦/余弦投影，带符号相量的最小包角误差 ≤ 3°。
- 三相平均负载电阻耗散功率：相对误差 ≤ 5%，两侧均为正吸收。

总RMS复用 `analysis.rms`，直流均值复用 `analysis.mean_value`，均按实际时间权重计算。基波对每个原生采样区间的分段线性电流与固定正弦/余弦作解析积分，不搜索频率或时移。相量约定为 `i(t)=sqrt(2)*I_rms*sin(2πft+phase)`；相位比较保留正负方向。功率定义为 `R*Σ(I_phase_rms²)`，即负载电阻平均耗散，不含器件损耗，也不把电感瞬时储能功率误认为耗散。电流反号不改变i²，因此方向必须同时通过相位与完整波形检验。

## 复现与记录

MATLAB从仓库根目录执行：

```matlab
addpath('validation/cases/two_level_pwm');
export_reference(pwd);
```

导出器读取实际SLX的SHA-256并校验已检查的R2025a字节，同时拒绝不同路径的同名已加载模型或未保存修改。若未来 `openExample` 下载了不同版本，必须重新检查并建立对应协议，不能把新模型结果写成旧模型的来源记录。

在具有实际参考数据的本机，从仓库根目录执行：

```powershell
$env:MPLBACKEND='Agg'
uv run --locked python -m validation.cases.two_level_pwm.compare
```

工具先保存公共波形比较，再在同一运行目录的 `report.json` 中加入 `features` 和 `waveform_passed`。最终 `passed` 要求波形、三相特征与功率全部通过；计算异常也会把该次报告置为失败。命令退出码跟随最终结果。每次独立保存候选CSV/JSON/NPZ、叠图、实际provenance、原始/标准化/模型/输入脚本和参数hash。报告中的 `compare.py` 快照包含本例特征实现。

`tests/test_pwm_reference_features.py` 使用已知解析正弦和非均匀采样斜坡验证投影、RMS、功率与失败行为，包括180°反向在RMS/功率不变时仍失败。这些合成数据只验证数学工具，不能冒充商业平台输出。

## 当前证据状态

**本配置尚未通过商业平台完整对标。** 真实导出成功后，首次比较保持 `146a279` 全部限值，结果为完整波形失败、特征通过、总体失败。失败报告保留在 [validation_report.json](validation_report.json)，不得仅凭基波或图形接近宣布完成。

| 相 | 波形NRMSE（限2%） | 最大误差（限10 A） | 总RMS相对误差（限5%） | 基波RMS相对误差（限5%） | 基波相位误差（限3°） |
|---|---:|---:|---:|---:|---:|
| A | **2.6995%** | 8.7640 A | 0.6338% | 0.6360% | 2.0970° |
| B | **2.6577%** | 8.6802 A | 0.5739% | 0.5769% | 2.0716° |
| C | **2.7167%** | 9.0962 A | 0.5651% | 0.5680% | 2.1134° |

三相平均电阻耗散为PyCy 33689.24 W、参考33294.58 W，相对误差1.1854%，在冻结5%内。完整0–0.2 s叠图已实际查看，电流方向、相序与量纲一致，纹波及相位差仍可见；验收只用预先固定的0.1–0.2 s窗口。

独立无时移门极检查在此窗口的20001个原生采样点上，A上管有198点、B/C各194点与既有12的门极不同，约0.97%–0.99%；双方各桥臂仍分别严格互补。首个A上管导通采样时刻也不同：官方100 μs、PyCy 50 μs。官方Natural开关时间算法、RateTransition与直接载波比较之间存在时序差异；已核对RateTransition配置，但其内部保持序列未成功取得，不能宣称与PyCy逐点相同。IGBT/反并联二极管的0.8 V导通压降和寄生电导也与PyCy开关模型有差异。以上贡献尚未逐项隔离，不能把全部误差单独归因于一种机制。原始门极、参数、失败日志及无时移审计保留供后续研究；没有通过移相、改12、修改参数或放宽阈值消除这次失败。

2026-11-09[只读时序补充](../../../docs/development_roadmap/experiments/spwm_timing_followup.md)：按原安装库的100µs跨任务缓存与离散计时器重建，全部40001点六路实际门极均一致；这是结构所导出的重建，未另直接读到编译RT活动模式或内部参考序列。
原二极管实际导通、额外器件压降及负荷1µS/后退欧拉差异也已有独立代数证据。默认12和原报告不变，以上2%波形FAIL继续保留。
