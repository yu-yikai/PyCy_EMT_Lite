# B1：从原库结构解释门极差异

2026-11-09。只读取既有原模型、安装库和2026-11-04的真实记录；未运行MATLAB或候选，未修改12、参数、原2%限值或比较窗口。
**B1仍未验收**：[原报告](../../../validation/cases/two_level_pwm/validation_report.json)的三相NRMSE 2.66%–2.72%仍为FAIL。
本次补上[先前研究](spwm_feasibility.md)尚未隔离的控制时序证据，不把门极解释改称默认12的商业PASS。

## 100µs来自跨任务缓存

原控制器的SID4451把5µs正弦参考保持到100µs。原库`eePwmGeneratorTwoLevel.slx`中：

- Natural模式令输入RateTransition继承采样时间，初始计时器为0；SPWM选择`PWM=1`。
- 三相Switching Time Calculation调用安装源码`+ee/+control/pwmSwitchingTimeTwoLevel.m`。
- Gate Signal Generator内SID428/429把100µs的开/关时刻送到5µs计时器，使用默认保护、确定性RateTransition；原模型开启多任务执行。

[R2025a官方说明](https://www.mathworks.com/help/releases/R2025a/simulink/ug/handle-rate-transitions.html)规定，此种慢到快转换引入一个慢任务周期的延迟；
快到慢转换表现为保持。[参数说明](https://www.mathworks.com/help/releases/R2025a/simulink/slref/ratetransition.html)给出了默认确定性、完整性和初值设置。
因此这里的100µs由结构与任务周期得到，没有搜索波形延迟或拟合相位。

令`m=2*Vabc/Vdc`、`T=1/fsw`。原SPWM源码可直接化为：

```text
Ton  = T*(1-m)/4
Toff = T*(3+m)/4
upper = (counter >= Ton) XOR (counter >= Toff)
```

在相同参考和计时器条件下，这与12从峰值开始的三角比较在本线性调制范围内等价；“Natural”标签本身不能解释全部差异。
本次按原库离散计时器、上述100µs缓存及原初值重建，**全部40001点、三相六路真实门极逐点相同**，含启动和所有边界，未删点。
这不是直接记录到的内部参考信号：编译后各RateTransition的活动模式未重新读取，结论为原结构所导出的重建与全部实际物理门极一致。

| 同一绝对时间上的检查 | A上管 | B上管 | C上管 |
|---|---:|---:|---:|
| 12原门极公式对真实门极，0.1–0.2s | 198点不同 | 194点不同 | 194点不同 |
| 原结构及缓存/计时器重建对真实门极，0–0.2s | 0点不同 | 0点不同 | 0点不同 |

原保存候选CSV在自己的时间戳上与原公式完全一致；将公式改在原生CSV打印的时间戳评价时，A相另有3个全窗边界点因末位浮点差异改变比较结果。
例如0.10005与0.10005000000000001使近零比较差改变符号。故原“同原生时刻公式”198点和“已保存候选网格”200点的稳态计数分别保留，不能互相替换或删除边界点。
100µs在60Hz下对应2.16°，能说明相位差的主要时序来源，但不是全部电流误差贡献的独立定量分解。

## 器件和负荷差异仍真实存在

从真实`vce`得到各相极点电压，在同一真实门极及相电流下，减去双向1mΩ通道的代数电压`400*upper-0.001*i`，
剩余约为`-0.8*sign(i)` V；在`|i|>0.1A`的全部点上，该关系最大残差8.04µV。稳态残余电压每相RMS约0.800004V。
原六只反并联二极管最大绝对电流约156–157A，**不能满足二极管不活动的等效前提**。门极互补不使IGBT加二极管等价于12的双向开关。

原负荷的1µS寄生并联支路也已通过波形核实：令`v_load`为极点电压减三相均值，`j=i_native-1e-6*v_load`，
代入每相`1mH*(j[n]-j[n-1])/5µs+1Ω*j[n]=v_load[n]`，全窗最大残差2.06e-10V。
因此原电流包含该寄生支路，并按本地后退欧拉积分；12为梯形法。这些电路与积分差异不能用门极相同代替验证。
本次没有计算它们各自对电流NRMSE的独立贡献。

## 证据与下一步

全部新证据在忽略目录`local_reference/two_level_pwm/followup/20261109T065409566123Z/`：
`report.json`、`boundary_and_load_checks.json`、全部原生与重建上门极CSV、库结构摘录及18项`evidence_inventory.json`。
原MAT、原始门极/电流和已保存候选CSV均保持原字节；下表SHA-256可核身份。

| 文件 | SHA-256 |
|---|---|
| 原`TwoLevelPWMGenerator.slx` | `ad8ddf5e46dd633b4853d7694067528d5d20ce78a24059a2847c6a97dbc2ea34` |
| 安装库`eePwmGeneratorTwoLevel.slx` | `65008a6e40a4eba272e46b682ac02e6be916250488d8229d9a3f9fe230be95b4` |
| 安装源码`pwmSwitchingTimeTwoLevel.m` | `7d4edfa65a2d62cadf1d8b2f4ac0712772841edfd5cb6df42479b1d63b5e6b7b` |
| 实际门极`physical_device_gates.csv` | `7f46e19f63d781c549d612f82a76e2be67c2f06c65d5cc87a4769fb898b64e61` |
| 新18项库存`evidence_inventory.json` | `5a2a495341955a0e2643a8bf4bbac45bce50fd7dd1a54c7ab9d6d2c547d1badb` |

下一步须先独立说明验证意图：保持12现有的即时保持参考数学，还是另立明确的跨任务参考时序协议；不能为迎合供应商调度直接改默认12。
选择后仍需先冻结隔离实验，分别检验时序、器件与积分贡献，保留原2%FAIL及全部原始点。
未创建新候选，不引入自动二极管框架，也不把更简单的参考或调参结果替代原验收。
