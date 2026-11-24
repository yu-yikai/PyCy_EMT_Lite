# A4：互感与理想变压器官方参考初查

2026-11-04，仅获取、检查并运行官方参考，未实现 PyCy 候选，也未制定新验收阈值。A7 的模型、数据及协议未变。

## 来源、原件与依赖

官方页面为 [A Comparison of the Mutual Inductor and Ideal Transformer Library Blocks](https://www.mathworks.com/help/simscape/ug/comparison-of-mutual-inductor-and-ideal-transformer.html)，精确 ID 为 `simscape/ComparisonOfMutualInductorAndIdealTransformerExample`。通过 R2025a `openExample` 取得主模型、官方 Live Script 和全部五个支持电路。

| 原件 | SHA-256 |
| --- | --- |
| `CompareCircuits.slx` | `9df7b95e3d0c5b842c1699631e49a5587179088b6afe9281914c52b60964e07b` |
| `ComparisonOfMutualInductorAndIdealTransformerExample.mlx` | `8a6e3f0f1f55dc015619d8462592be4c4ac1910a022fd7315fc6a6ef8ee877b6` |
| `ElectricalEquivalentCircuitTransformer.slx` | `e64bffb228e8f11daf0ffb6475615a82f7e4e20668808bcd3d5edcfe921cf672` |
| `ElectricalEquivalentCircuitMutualInductor.slx` | `eb5ff69d07d15aed0e74183ec6c05c1fea57fad0937a65bbb1c2ab57166146cd` |
| `ElectricalEquivalentCircuitSimplifiedMutualInductor.slx` | `0f47e478f52e4adee90f3ee35518e9dff2eda2232c213305cf8a75fcf0689cc3` |
| `MagneticEquivalentCircuit.slx` | `b6e4b137ee8405d9cf8333cb9d90133c70a15b0f1c1d05454fdcd8f20230706b` |
| `MagneticEquivalentCircuitIdealTransformer.slx` | `6cb185d3d40bdf8974ca606018d9f5cf98e1780d8796abf24a671793204cbc55` |

本机版本为 MATLAB 25.1.0.2973910（R2025a Update 1），运行需要 MATLAB、Simulink、Simscape。主模型中的磁路也全部使用 Foundation Library 线性元件；本次未调用 Simscape Electrical 的非线性变压器、磁滞或饱和模型。原模型运行及电流导出不依赖额外控制工具箱。本次没有执行官方脚本后半部分的 `linmod` 频率分析。

原件、解包 XML、SHA 清单及自有探针保存在忽略的 `local_reference/transformer_comparison/`。未向仓库复制第三方 SLX/MLX 或数据，也不主张其再分发许可。

## 两套不同的官方活动参数

`CompareCircuits` 的 PostLoadFcn 仅在工作区尚无 R1 时填充备用变量。其备用值与官方 Live Script 的实际实验值不同，不能混写为同一默认设置。

共同参数：N1=100、N2=500；泄漏磁阻 R1=R2=1e6 H⁻¹；理想变比 N1/N2=0.2；源串联电阻与二次负载均为 1 Ω；已有五个 Step 的阶跃幅值均为 1 V；停止时间为 8 s。五个用于线性化的根 Inport 保持原始默认零输入。

| 参数 | SLX PostLoad 备用值 | 官方 Live Script 实验值 |
| --- | --- | --- |
| 主磁路磁阻 Rc | 1e4 H⁻¹ | 1e5 H⁻¹ |
| 阶跃时刻 | 100 s | 2 s |
| 原边泄漏 l1=N1²/R1 | 0.01 H | 0.01 H |
| 副边泄漏 l2=N2²/R2 | 0.25 H | 0.25 H |
| 励磁 Lm=N1²/Rc | 1 H | 0.1 H |
| 互感块原边自感 L1 | 1.01 H | 0.11 H |
| 互感块副边自感 L2 | 25.25 H | 2.75 H |
| 完整互感 M=N1N2/Rc | 5 H | 0.5 H |
| 完整互感耦合系数 k | 100/101 | 10/11 |

纯电气互感支持电路的 `perfectCoupling=false`；简化互感支持电路为 `perfectCoupling=true`。后者的 k 字段虽然仍显示变量 k，但在完美耦合模式下不用于模拟有限泄漏。它保留 L1/L2，不可把它等同于无有限励磁的理想变压器。

## 纯电气拓扑与已有能力映射

主模型 `CompareCircuits` 依次包含五组相互独立的原实验网络：线性磁路、理想磁路、纯电气变压器 T 等效、完整互感、完美耦合互感。五个支持 SLX 通过 Subsystem Reference 引用，各自只提供电气 p1/n1/p2/n2 端口，缺少独立激励、终端和 Solver Configuration，不能直接当作完整顶层实验运行。

优先使用第三组 `ElectricalEquivalentCircuitTransformer`：

```text
1V阶跃 ── Rs=1Ω ── l1=.01H ── core_p ── 理想变压器(.2:1)
                                  │                   │
                                Lm=.1H           l2=.25H ── Rload=1Ω
                                  │                   │
                                  0                   0
```

理想变压器的两个负端分别接各自的明确电气参考。l1、l2、Lm 均为纯电感，原生 r=0、g=0；不存在未记录的绕组电阻、铁耗支路或非线性磁化曲线。励磁支路连接在**原边泄漏电感之后**的内部绕组节点。

现有 PyCy 代码中有 `SinglePhaseTransformer`，未发现独立 `MutualInductor` 类。完整 T 电路仍可由现有原语精确构造：使用只保留理想变比的 `SinglePhaseTransformer`，在外部明确连接 l1、Lm、l2 和两个电阻。不能把这套 T 参数直接塞入现有例 09 的聚合泄漏/励磁参数：该聚合模型将励磁支路接在输入端，节点位置不同。更不能仅将两侧泄漏折算为一个电感就忽略中间励磁支路。

第三组与完整互感的端口方程满足 L1=l1+Lm、L2=l2+Lm/ratio²、M=Lm/ratio；官方 Live Script 参数下即 0.11 H、2.75 H、0.5 H。后续可以用纯电气 T 作为候选前的明确参照，而不为本题新增互感核心类。

## 两次真实原模型运行

自有脚本 `local_reference/transformer_comparison/run_reference_probe.m` 在新 MATLAB `-batch` 会话中运行原主模型，核对全部七个原件的 SHA，并通过 `SimulationInput` 显式绑定各组原始变量。没有添加模块、连接、外部输入或新激励；第二组逐项采用官方 Live Script 已有参数。仅开启完整日志，保持原模型求解器自动选择、RelTol/AbsTol=1e-3 与 8 s 停止时间。

| 原生运行 | 实际求解器 | 样本 | 结果 |
| --- | --- | --- | --- |
| `slx_default_fallback` | ode15s，最大步长 0.16 s | 51 | 0–8 s 五路电流全零；阶跃位于窗口之外 |
| `official_live_script_step` | ode45，最大步长 0.16 s | 118 | 2 s 阶跃后出现非零动态；默认仿真用时约 1.26 s |

真实日志确认电气 T 的 l1/l2/Lm 初始电流均为零；完整互感和完美耦合互感的两绕组初始电流也均为零。它们是这次零激励启动所得的实际初值；原模型这些初始目标未全部设为高优先级强约束，未来如修改激励或初始化策略须重新核对。

原生输出 CSV 五列依次为 `i_magnetic_load`、`i_ideal_transformer_load`、`i_transformer_load`、`i_mutual_load`、`i_perfect_mutual_load`，另有原生 time 列。电流方向由接线核定为二次正端经负载和电流传感器流向参考点，与**流入变压器副边正端**的电流反号。

官方实验的线性磁路、纯电气 T、完整互感三组负载电流在本次原生运行中逐点相差不超过 8.30e-15 A。理想组的阶跃负载电流为 0.1923076923 A，符合 ratio/(Rs+ratio²Rload)。前者只是同一次商业平台运行中的等效模型一致性证据，不能冒充独立 PyCy 验证。

每次运行均保存 `simulink_output.mat`、`secondary_currents_native.csv`、活动变量、实际 solver、产品依赖和原件 SHA 的 `provenance.json`；另有 `initial_state_inspection.json` 与 `probe_physics_check.json`。

## 后续建议与状态

建议继续运行现有完整 `CompareCircuits`，只从第三组提取纯电气 T 的电压、源电流、负载电流和励磁电流。主模型很小，当前并无必须另造独立 harness 的性能或许可理由；其余磁路组可继续在原模型中运行，PyCy 比较无需复制它们。

本次状态为**官方模型可运行、参数与纯电气等效路径已核实**。默认宽松容限和 118 点结果仅用于可行性检查，尚未形成高精度跨平台验收参考。若推进 A4，应先冻结所选官方参数版本、端口方向、阶跃边沿和比较窗口，再做参考求解器自身细化；之后才实现候选和数值比较。当前没有新增教学例、验收 PASS 或商业平台对标完成声明。
