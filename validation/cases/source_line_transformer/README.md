# 25：电源、两π段线路、变压器和负荷

运行 `uv run --locked python examples/25_source_line_transformer_network.py`。
建议先读08的线路充电、17的正弦稳态和23的变压器T等效。
本例把这些部件接成一个完整单相网络，重点观察各处电流为何不同，以及怎样从非零稳态初值开始。
脚本只使用现有线性元件；复阻抗递推和组网都留在本例，没有增加核心框架或依赖。

## 接线与参数

```text
Vs ─ Rs ─ B1 ─ 两π段线路（中点mid）─ B2 ─ R1,L1 ─ core ─ 理想T ─ R2+Rz1,Lz1 ─ B3 ─ 0V表 ─ Rload∥Cload
          │                         │              │                           │
       补偿Rs,Ls                 补偿Rr,Lr       Rm∥Lm                       Rzs,Lzs
          │                         │              │                           │
          0                         0              0                           0
```

B1、mid、B2另各有线路对地电容和电导。脚本节点分别叫`send`、`mid`、`recv`；
B3为`load_bus`，电流表后的`load`与它等电位。参考官方模型的实际顺序为**电源→线路→变压器→负荷**。

| 部分 | 单相参数与含义 |
| --- | --- |
| 电源 | 60 Hz，峰值600124.986982 V，初相0°，源电阻2 Ω |
| 线路 | 150 km、两个有限π段；原始每km为0.011 Ω、0.8674 mH、13.41 nF |
| 每段修正串联支路 | R=0.822444576606 Ω，L=0.064954337154 H |
| 每段总分路 | C=1.006530091125 µF，G=9.902004195214 nS；端点各取一半，中点两个半支路相加 |
| 两端补偿 | 每支为串联R=5.456757551179 Ω、L=4.342349687621 H，对地连接 |
| 变压器 | 250 MVA，绕组额定735/√3与315/√3 kV RMS，理想变比n=7/3 |
| 原边漏阻抗 | R1=0.7203 Ω，L1=0.286598263773 H |
| 励磁与铁损 | Rm=360150 Ω，Lm=955.327545909102 H，位于原边漏阻抗之后 |
| 副边与Z1 | R2=0.1323 Ω、Rz1=0.734 Ω，同一串流可合并为0.8663 Ω；Lz1=0.02085 H |
| B3对地支路 | Rzs=11 Ω，Lzs=0.2925 H，串联 |
| 固定RC负荷 | Rload=165.375 Ω，Cload=4.009950695185 µF，并联 |

线路按原模型的60 Hz双曲函数修正计算R/L/C/G，不能直接把每km数值乘75代替。
输入没有指定电导，修正后的等效网络仍含三条很小的正电导；脚本用三个大电阻保留它们。
它是两个有限π段，学习重点是本网络的稳态关系，不能据此声称宽频传播或Bergeron延时精度。

副边R2与Rz1之间没有分流，合并不改变本例电路；损耗核算仍分别计算两者。
`secondary`是理想绕组端，原变压器外端在R2之后，不能把两个端电压混用。
额定200 MW、50 Mvar容性负荷用于在315/√3 kV下计算固定R/C；它们不是实际恒功率指令，也不能再除以3。

## 为什么t=0的储能不为零

虽然源电压在t=0为零，电感电流和各节点电压具有不同相位，因此12个储能状态都不为零。
`steady_phasors()`从负荷向电源合并复阻抗，再向负荷方向求节点电压和支流。
以峰值相量q表示`x(t)=Im(q·exp(jωt))`，各电感/电容初值便是对应q的虚部。
这些初值由本网络参数计算，没有读取商业波形、原生状态或冻结的审计相量。
若改用零初值，会产生另一个物理启动过程，不能再和本参考直接比较。

默认梯形法h=10 µs，停止50 ms，正好三个60 Hz周期。
快模态时间常数约0.226和1.007 µs；连续稳态初值也未必恰好落在离散梯形法的周期解上。
因此首1 ms仍需检查数值初始化误差。独立先验分析同时考虑了这一误差及采样点之间的线性插值。
首窗并不表示物理冷启动，也不能只看采样点误差来代替整条曲线的误差。

## 先读电压，再核电流和功率

三张图分别显示变换前后的电压、源与两段线路串流、末端分流。电流正方向沿源向负荷，分流朝地。
可沿下列关系读图：

- 源总流`i:Rs`还供应B1补偿及端部C/G，所以不等于`i:Lline1`。
- 两段串流之差供应中点C/G；B2的线路端口流还需扣除末端C/G及补偿，才得到变压器原边流。
- `i:Lp`分为理想变压器原边流、励磁流`i:Lm`和铁损电流`v:core/Rm`。
- `i:Lz1 = i:Lzs + i:Iload`。0 V表只测RC负荷总流，不包含B3的Zs支流；表本身不耗能。

运行摘要用三个周期的实际电压/电流计算RMS和单相P/Q；负荷容性Q为负。
默认负荷约137.545 kV RMS，实际P=114.398 MW、Q=−28.600 Mvar；其余电阻耗散约21.864 MW。
源有功等于RC负荷有功、其他所有电阻损耗及储能变化之和，不能只计线路和铜损。
稳态一个整周期的储能净变化接近零，但初始储能并不为零。

可以把`TIME_STEP`改为5 µs再运行，比较最初1 ms及全周期曲线；默认验收报告只覆盖未修改的参数。
也可将`LOAD_ACTIVE_POWER`减半，观察固定电阻增大、端电压和实际P/Q同时变化，再恢复默认值。

## 真实参考与复现

来源是MathWorks [Analyzing a Simple Circuit](https://www.mathworks.com/help/releases/R2025a/sps/powersys/ug/analyzing-a-simple-circuit.html)
随R2025a安装的完整`power_gui.slx`，原件SHA-256为
`a46b7c34658c65ce58c6e51a6d167244c06f4e839063c00bd1ff75c78bdc5a08`。
模型保存元数据为R2025a Prerelease Update 2，本机实际软件为R2025a Update 1。
没有为凑事件加入开关，没有改变物理参数或稳态初始化。

[验收协议](acceptance_plan.md)、[manifest](manifest.json)及[参数](parameters.json)在候选和测试创建前提交于65d89bb。
436c266另提交[原生状态块守卫勘误](native_state_guard_addendum.md)：路径名State-Space实际是S-Function，
修正不存在字段的检查，保留原运行和完整基线MAT；电路、运行配置和验收限值均未改变。
冻结14量、[0,1 ms]及[1 ms,50 ms]两完整窗，时间偏移0；每项同时检查固定工程尺度NRMSE与最大绝对误差。
原Scope没有保存输出，因此参考明确为商业原生12态及其原生采样点上的`Cx+Du`线性测量投影。
投影后再插值；不能先插值节点电压、再混入连续源电压求源流，否则会改变大数相减的插值误差。

内部测试另用物理复数节点方程求解，不以脚本的初始化递推作唯一依据；同时核参数、12初值、KCL、
理想T关系、全部损耗、连续与梯形离散能量、RMS/PQ/相位及20/10/5 µs二阶细化。
解析正弦仅用于内部正确性和真实参考的绝对精度审计，不能充当商业输出。

2026-11-06正式参考run为`20261106T054135322Z`：5023/10023个原生时刻，
两窗×14量自身精化全部通过，两组各自对独立物理解的sample/PWL精度审计也通过。
其中baseline只读复用`20261106T052652719Z`的上述完整MAT；refined是新完成的真实50 ms运行，
没有把缓存抽取称为重新仿真。两组保存的求解配置及实际12初值均经核对。

正式候选run为`20261106T054356596388Z`：5001点，**28项双限值检查全部通过**。
最大电压误差0.864127 V，最大电流误差0.00623452 A，最大NRMSE为1.74756e−6；
最接近上限的最大绝对误差仍只占其冻结限值的4.375%。完整指标见[机器报告](validation_report.json)。
图`comparison_results/20261106T054356596388Z/comparison.png`已实际查看，14量三周期波形重合、方向及标注正确。
比较时HEAD为436c266，候选尚未提交，报告如实保存dirty状态及确切源码/输入快照hash；交付提交再包含这些源码和报告。

11项独立物理测试、独立Agg运行5001点、锁定同步27包、全范围Ruff、mypy39源文件及两个新Python入口均通过。
完整回归为**1190 passed，478.96 s（含slow）**；XML记录1190项、零失败/错误/跳过。
日志及XML位于`.tmp/longterm/d0-final-full-pytest.log`和`d0-final-full-tests.xml`。
本地结果不代替双操作系统CI：最近实查的1423c7d作业因GitHub账单锁未启动，25还没有远端执行结论。

| 证据 | SHA-256 |
| --- | --- |
| canonical provenance.json | d96f571c89494109d805c8ab09e2b3c01d8043479f1de73bbc08e5764899eccd |
| baseline reference.csv | 735206b2de6af08f162d35ac2a40f7986d266269ffd6d1e6d0f18dafc9af22f3 |
| self_refinement.json | 7e0a1e6a99249c5148b2ae1644a8749b952e8f39c38f807ac09d86ab2565c699 |
| refined simulink_output.mat | 9324cdf6a6274f060a92e71dfa29a3e0815d4971eb7a3d0481ff494fbdd250c0 |
| report.json原字节（与工作区validation_report.json相同） | 67a49999c4959a601c786401d3415d1bf69e095d4e5b84faeb662baf75ea03ad |
| validation_report.json的Git LF文本 | a7a7d0556f6bd3e3b6b761f2465bfb118accfc73d6345df1ba1e82b4d12cb88b |

Windows原报告使用CRLF，Git提交规范化为LF；上表分别标识原始字节和LF文本，不混作同一hash。
参考原件、原MAT、状态/测量矩阵、输入快照、日志和每次独立运行目录留在忽略的`local_reference/source_line_transformer/`。

导出脚本针对已审计的Windows R2025a Update 1及安装文件身份，并需要本机
[前置调查归档](../../../docs/development_roadmap/experiments/source_line_transformer_reference_probe.md)中的`local_reference/d0_research/`输入。
迁移软件或操作系统需重新审计身份，不能跳过守卫。有匹配环境时，在MATLAB中将本目录放在路径首位后调用
`export_reference`；它默认重新生成两组真实参考。第三参数仅允许复用上文固定hash的原baseline MAT，并明确记录缓存来源。
已有本次参考时，回项目根目录运行：

```powershell
$env:MPLBACKEND = 'Agg'
uv run --locked python -m validation.cases.source_line_transformer.compare
uv run --locked pytest tests/test_source_line_transformer_network.py
```

比较适配器先核当前协议、原模型、导出脚本及原始数据身份，拒绝陈旧参考；公共比较程序另存本次结果、图和报告。
没有真实参考时可独立运行教学脚本和内部测试，但不能声称已经通过商业平台对比。
