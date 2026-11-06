# B2：同步 Buck 初值、互补开关与控制坐标

2026-11-06。继[原件初查](synchronous_buck_reference_probe.md)后的真实参考核验。
已取得原先缺少的储能状态和生效控制参数；尚未编写26候选、冻结正式判据或进行PyCy商业比较，正式新增仍为7项。

## 新运行及保存范围

原SLX与物理/控制/求解配置保持不变，用SimulationInput额外保存time与完整state Dataset。
真实运行`20261106T060137544Z`到10ms；原有四份Scope CSV与旧run逐字相同。
原始`in/out` MAT先保存，随后提取器错误地要求所有state都覆盖0..10ms而退出1。
修复仅在`20261106T060649984Z`读取已有MAT，没有重复仿真或掩盖首次失败。

共有4组、总宽度5：PI积分、测量滞后、Triangle Unit Delay、两列电气储能。
三个连续组各3634点；Unit Delay另有1000点，原轴5µs..9.995ms，不补首尾、不插值。
后续compile/read/term查询`20261106T062509113Z`退出0，无sim、Dirty off；首次不支持RuntimeObject字段的查询失败另存。
原20项、state归档41项及query补充29项hash均由主审重新核对；第三方模型与缓存留在忽略目录。

## 真实初值与开关相容条件

实际`iL(0)=0.000299977501687373 A`、`UC(0)=0.00112491563132765 V`，控制两状态为0。
电气值与native x0、两管阻断时由100kΩ snubber和3.75Ω负载形成的DC分压一致。
它不是15V闭环工作点，也不能把未启用的mask零值当作初值。

在全部3633个`t>0`点，用实际iL/UC分别计算上下管互补的两个线性网络，再与实际源电流核对。
预定代数残差限1e-8 A：1999点唯一上管开、1634点唯一下管开，零歧义/不匹配，最大残差7.82e-14 A。
首点按四器件均阻断另核，未删除。这是物理模式重构，**不是直接门极或二极管电流日志**。

在预定域`|iL|≤7.99 A, |UC|≤40 V`内，两管互补时可保守证明体二极管不达正向阈值。
以导数界桥接全部3633段，最保守全局余量仍有0.3307 A、12.5536 V。
生效selector及NOT连接现已读到，支持互补结构；但原生默认解的绝对状态误差尚未由真实精化约束。
因此这仍是有数据余量的充分条件核验，不能扩大成所有Buck工况或商业连续轨迹的无条件证明。

## 控制坐标与PWM

生效分支是连续PI：Kp=0.5、Ki=200，测量滞后`[1]/[1e-6,1]`，限幅在PI外，积分器不限幅。
根据实际连接和标准型推导固定映射，再逐点交叉核对原Scope duty：

```text
filtered_error = 1e6 * xlag
integral_contribution = 200 * xint
duty = clip(0.5 * filtered_error + integral_contribution, 0.01, 0.95)
```

3634点最大代数残差2.3523e-15；全部3192个严格未饱和点也用未clip原式通过，无拟合。
这里的filtered_error是经独立duty验证的状态坐标映射，不能称它被直接记录。
现有FirstOrderLowPass可保存该物理量；PIController应不设内部限值，外接Limiter，避免增加原模型没有的抗饱和。
现有LP后退欧拉和PI离散积分仍需单独核验步长及调用顺序；这个代数残差不证明动态精度。

实际载波50kHz、相移+5µs，比较器`>=`，两个输出为P和NOT(P)。
重算3633点中2010点距比较根≤1e-9，其余1623点与物理模式全一致。
根内双精度布尔重算有989个差异；主审用另一等价浮点表达得到987个，最大离根均约2.20e-11。
完整点表、差异索引和guard敏感性保留；guard仅诊断左右侧/舍入敏感性，不删点或充当验收误差。
活动Unit Delay采样为`[10µs,5µs]`，仅自环而不驱动载波值，但会增加求解命中点，参考模型不删除它。

## 证据入口与下一步

以下路径相对`local_reference/b2_followup/`；原41项清单未因后续查询而重写。

| 入口 | SHA-256 |
| --- | --- |
| `observability/evidence_inventory.json` | `b66702195a9e60eb5f56e1fbf8c6c2bd760050b12770a096b7bd8b3dfdbb7344` |
| `observability/control_query/supplemental_inventory.json` | `e6f33518ca6c07aff5cd670b7ec0013ffb854061b75eef9854a997324391948a` |
| `physics_audit/native_state_certificate.json` | `959c48cf3a219a19a65d546ee6db52a250783635948da9a9c2b2f23cdfdd71ad` |
| `physics_audit/control_coordinate_and_carrier.json` | `c0078eebdd70675df81d70097d23ea616fbe278c73779df49fd0f0b927d89a8b` |

原始新MAT为`native_states/20261106T060137544Z/simulink_output.mat`，SHA-256
`66de341ad60356295cc398bad2db155426359959c342db2e1bc90989d7da2adf`。
主审独立重算在`.tmp/longterm/audit_b2_a3_followup.py`及对应`b2-a3-followup-root-audit-final.json`。

下一步在候选前固定完整参数/非零初值、连续与离散更新顺序、负荷事件、参考精化预算、比较窗和阈值。
先确认现有Switch、无内部限幅PI、LP与外部Limiter能够在上述有效域内组成可读教学例。
若数值/事件边界无法可靠验证，则保留研究状态并继续其他独立任务；不扩自动二极管或连续控制框架。
