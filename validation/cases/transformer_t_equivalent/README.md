# 23：外置三电感的变压器 T 等效回路

运行 `uv run --locked python examples/23_transformer_t_equivalent.py`。本例用现有电阻、电感和理想 `SinglePhaseTransformer`，观察零初值下的阶跃响应、漏感和励磁支路的作用。建议先学02的储能初值及09的变比和端口电流方向。

## 接线与观察

```text
src -- Rs -- pri_in -- L1 -- core_p -- ideal T(.2:1) -- sec_p -- L2 -- load -- Rload -- 0
                               |
                              Lm
                               |
                               0
```

理想T的两个负端分别接各自参考0，原副边电压比 `a=N1/N2=0.2`。Rs和Rload均1 Ω，L1=0.01 H、L2=0.25 H、Lm=0.1 H，三个电感初始电流均为0。常值源在2 s通过显式事件从0变为1 V，默认梯形法步长1 ms，停止8 s，复用现有线性分解。

Lm接在原边漏感L1之后。T1内部漏阻、漏感均为0，内部励磁与铁损支路未启用；储能完全由三个外置电感承担。励磁电流应读 `i:Lm`，不是未启用的 `i:T1:magnetizing`。09的聚合模型励磁支路位置不同，不能仅换它的参数便视作同一回路。

`i:L1`从源流向core_p，`i:L2`从sec_p流向负载，`i:Lm`从core_p流向地。T端口电流均以流入正端为正，故

```text
i_source = i_magnetizing + i_load/a
i:T1:primary = i_load/a
i:T1:secondary = -i_load
v:core_p = a*v:sec_p
v:core_p*i:T1:primary + v:sec_p*i:T1:secondary = 0
```

阶跃瞬间电感电流仍为0，core_p与sec_p电压分别跳至10/21 V和50/21 V；负载电压此时仍为0。负载电流随后上升，再缓慢衰减。独立连续时间解的峰值约0.170257318 A，时刻2.093647085 s；默认离散运行的采样峰值为0.170258475 A，时刻2.094 s。8 s时负载电流仍约0.021439778 A，不应误判为未达到理想变比或要求它已经为0。

在本线性方程的渐近直流极限，源与励磁电流趋于1 A，负载电流趋于0。这个实验不含磁饱和、磁滞和铁损，不能解释为真实铁芯允许持续直流。两个电阻位于绕组外部，耗散不命名为绕组铜损或铁损。

## 独立物理与数值检查

从三个电感和理想变比消去代数量，取 `x=[i_source,i_load]`，可独立得到

```text
M*dx/dt + diag(1,1)*x = [u,0]
M = [[.11,-.5],[-.5,2.75]] H
i_magnetizing = i_source-i_load/.2
E = .5*x.T*M*x
  = .5*.01*i_source² + .5*.25*i_load² + .5*.1*i_magnetizing²
dE/dt = u*i_source-i_source²-i_load²
```

M对称正定，行列式0.0525 H²，两模态时间常数约18.476 ms和2.841524 s。测试用该矩阵的谱分解计算完整阶跃精确解，不调用生产MNA盖章或伴随模型，也不从采样电流差分构造参考电压。推导和左右侧事件处理见 [独立验收方案](../../../docs/development_roadmap/experiments/transformer_t_validation_plan.md)。数学解用于内部验证，商业参考另行真实运行。

八项自动测试覆盖三初值、完整暂态及8 s有限响应、理想端口电流方向/电压比/零净功率、励磁KCL（1e-9 A）、2 s唯一右侧事件行与电流连续性、总能量加外部电阻损耗相对于源工作平衡（相对限值0.001）、梯形法2/1/0.5 ms细化（两次误差比均至少3）、非整步事件插入，以及有限响应与渐近极限的区别。能量积分在事件区间终点恢复左侧源值，另核对梯形法离散能量恒等式。

## 真实 Simscape 来源与参数选择

来源为MathWorks [Comparison of Mutual Inductor and Ideal Transformer](https://www.mathworks.com/help/simscape/ug/comparison-of-mutual-inductor-and-ideal-transformer.html)，示例标识 `simscape/ComparisonOfMutualInductorAndIdealTransformerExample`，顶层模型 `CompareCircuits.slx`。真实执行使用MATLAB R2025a Update 1、Simulink和Simscape。原始顶层的五个独立网络全部运行，本例只取第三个纯电气T网络。五个支持SLX是四电气端口的Subsystem Reference，不能当作独立仿真顶层。

本例采用官方Live Script的2 s阶跃和Lm=0.1 H实验设置。SLX的PostLoad备用设置为100 s阶跃、Lm=1 H，默认停止8 s会得到全零波形；不能用它作为本实验参考，也不能混用两组参数。导出器显式绑定17个区分大小写的变量：`R1,R2,Rc,N1,N2,ratio,l1,l2,Lm,L1,L2,M,k,r1,r2,vStep,tStep`。其中`R1/R2`与外部电阻`r1/r2`、漏感`l1/l2`与等效自感`L1/L2`含义不同。

导出器核对顶层、五个支持SLX及MLX的SHA-256，并拒绝路径上或已加载的同名异源模型及未保存更改。原件、真实MAT/CSV和图保留在忽略的 `local_reference/transformer_t_equivalent/`，不主张第三方原件再分发许可。

| PyCy信号 | 原生参考路径/方向 |
|---|---|
| `v:src` | `Controlled_Voltage_Source3.v` |
| `v:core_p` | `Subsystem_Reference2.Ideal_Transformer.v1` |
| `v:sec_p` | `Subsystem_Reference2.Ideal_Transformer.v2` |
| `v:load` | `Resistor5.v` |
| `i:L1` | `-Controlled_Voltage_Source3.i`，等于原生l1正向电流 |
| `i:L2` | `Resistor5.i`，等于原生l2正向电流 |
| `i:Lm` | `Subsystem_Reference2.Lm.i_L` |

## 冻结验收与复现

[manifest.json](manifest.json) 和 [parameters.json](parameters.json) 已在候选实现与数值比较之前提交为 `0ec723933a64e5d1dfacd214eb850228c0d5b015`。正式比较固定七量、绝对时间、窗口 `[0,1.999]` 和 `[2.001,8]` s，不作时移、相位或幅值拟合。1 ms事件保护区防止线性插值跨越跳变；完整波形及独立事件检查仍保留。

每量均要求NRMSE≤0.001。电压工程基值分别为1/1/5/0.2 V，最大绝对误差限值为0.005/0.005/0.025/0.001 V；电流基值为1/0.2/1 A，绝对限值为0.001/0.0002/0.001 A。参考先独立使用ode15s、RelTol=1e-9、AbsTol=1e-11，以1/0.5 ms最大步长运行，七量自身差异在两窗内均须小于各正式绝对限值的1/10。

在仓库根目录运行MATLAB导出器：

```matlab
clear export_reference
addpath('validation/cases/transformer_t_equivalent');
export_reference(pwd);
```

真实导出完成后，可运行：

```powershell
$env:MPLBACKEND='Agg'
uv run --locked python examples/23_transformer_t_equivalent.py
uv run --locked pytest tests/test_transformer_t_equivalent.py
uv run --locked python -m validation.cases.transformer_t_equivalent.compare
```

缺少真实数据时比较命令报错，不回退到合成参考。每次比较保留独立UTC运行目录、全部输入快照、候选CSV/JSON/NPZ、叠图、逐量报告、Git状态及SHA-256。复原历史报告应使用该运行的输入快照，不能用后来修改的文件替代。

## 实测记录

2026-11-04的专项XML记录为8 passed、4.388 s；独立Agg教学执行通过，8001点，2 s一条源事件。首次正常写出追溯报告的运行是 `20261104T115036486994Z`，两窗×七量全部通过。更早的 `20261104T114938718950Z` 在写Git追溯字段时因safe.directory中止，保留未完成目录，不记作数值FAIL或成功报告。2026-11-06仅整理候选import换行后，重新执行比较得到 `20261106T025650374531Z`，14项再次全部通过。

真实参考分别有8063和16042个原生样本，全部三电感初值严格0；自身细化最大电压差0.000155956 V、电流差0.0000679904 A，所有逐量限值均通过。原生KCL最大残差2.22e-16 A、变比残差5.56e-17 V、负载Ohm关系残差0。

最新运行的暂态窗口指标如下，与首次正常比较数值一致，阶跃前窗口七量误差均为0。叠图已实际检查，七量符号、单位、全时间及窗口正确。

| 信号 | 最大绝对误差 | NRMSE（固定基值） |
|---|---:|---:|
| 源电压 | 0 V | 0 |
| 原边core_p电压 | 1.39343e-4 V | 3.34534e-6 |
| 副边sec_p电压 | 6.96717e-4 V | 3.34534e-6 |
| 负载电压 | 5.55963e-5 V | 6.67383e-6 |
| 源至变压器电流 | 3.03740e-4 A | 7.29216e-6 |
| 负载电流 | 5.55963e-5 A | 6.67383e-6 |
| 外置励磁电流 | 2.57590e-5 A | 6.18340e-7 |

完整逐量结果见 [validation_report.json](validation_report.json)，与最新运行目录中的报告逐字节一致，SHA-256为 `a64c0677349799eb0f3b7874b6cbedba071fd07c3e0498cc6933bc48ee71c0bc`。最新报告的全部输入快照、候选CSV/JSON/NPZ、原始参考、包源码和叠图hash已逐项核验。全量回归、提交及跨平台CI状态由主任务记录，不将旧HEAD结果扩展为未测试代码的验证。
