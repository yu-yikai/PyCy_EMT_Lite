# B2：同步 Buck 官方参考初查

2026-11-09当前状态：本页保留早期探针与相容性研究。后续25/12.5ns真实完整参考已自细化PASS，首次50ns候选商业报告及独立原始数据复核/完整1236回归PASS，26已交付9269350、正式新增8；详见[本轮证据索引](native_reference_attempts_20261109.md)和[合格参考报告](../../../validation/cases/synchronous_buck/qualified_reference_report.json)。下文旧“尚无细化/候选”不作为当前状态。

后续已取得真实非零储能初值、控制坐标及互补结构证据，见[状态与控制补充](synchronous_buck_state_followup.md)。下文保留初查时的结论和失败，不把它当作最新缺口清单。

2026-11-06。原模型已取得并真实运行；本次未写 PyCy 候选、未冻结验收，也未计新增算例。当前结论是：**值得保留的闭环教学参考，但尚未证明能用现有双向受控 Switch 完整复现。**

## 原件与版本

本机 R2025a `sps.zip` 列出的精确 ID 是 `simscapeelectricalsps/SynchronousBuckConverterExample`。当前未分版本的旧说明链接返回404，不能据此认定本机参考已消失。MATLAB 首轮启动受首选项权限影响，后续从 [MathWorks 官方 R2025a 原件地址](https://www.mathworks.com/help/releases/R2025a/exampledata/simscapeelectricalsps/main/SynchronousBuckConverter.slx)实际取得60,569字节。该地址布局来自本机 R2025a 的 `matlab.internal.examples.copyFromWeb`，没有使用镜像或改变 TLS 验证。

SLX 自身 metadata 为 R2025a Update 1，保存版本25.1.0.2966447；本机实际执行版本是25.1.0.2973910（R2025a Update 1）。这是 **Specialized Power Systems（SPS）** 网络，使用 Simulink 与 Simscape Electrical 的 SPS 库，不是前几例的 Simscape Foundation 电路。没有将当前网页 R2026b 的器件说明套到本机原件。

原件、原始结果、原创探针及逐文件 hash 清单位于忽略的 `local_reference/synchronous_buck/`，不上传第三方 SLX 或生成波形。主要 SHA-256：

| 对象 | SHA-256 |
| --- | --- |
| `simulink/SynchronousBuckConverter.slx` | `ea8344f62e2a691456363f0391389cd1675bfe246bd71dc8f15a3b838ca6ab42` |
| `run_native_probe.m` | `41fda26d2d8b248b85e63802eaa5b4694480d0a0a1971ef36371677b786bad21` |
| `default_probe/simulink_output.mat` | `9993f968df74a64c4fb55c6a0944e8ec0a7697e73ebe5e4b39b40f493c444e8d` |
| `default_probe/provenance.json` | `2fce75843a7c430da62eefc942a94f4e8387f769836c50482dfd8ccfd0757f93` |
| `default_probe/output_voltage_native.csv` | `548a4fe47f3e6295e924481e828c2571be72172c20f5d5a71143143faee03947` |
| `run_gate_diode_probe.m` | `7764cdb72928ab1e6c62e5550ca8406315dab5aa159dee5056cb017290edd6fc` |

本机配套 `spsMosfetLib.slx` 与 `spsPWMGenerator2LevelLib.slx` 的 hash 分别为 `382a093e63f3570fda8a689eb4e87a55beb74f0ef1c71213c7e46378dbe5fa77` 和 `e7bd7003e94144a1c4b125b554bf469f235f3eda0e072799b33a8f79d47a07d7`。全部文件、失败日志及失败日志探针 MAT 的 hash 另存 `evidence_inventory.json`。

## 实际拓扑与活动参数

原 SLX、配套库 XML 和成功启动后的只读 `get_param` 相互核对：

- 30V直流源接上下两个直接引用的 `spsMosfetLib/Mosfet`；桥臂中点经1mH电感到输出。10kΩ电阻**并联在电感两端**，不是电感串联绕组电阻。
- 输出并联22µF电容、3.75Ω固定负载与脉动电流负载。脉动负载是原有受控电流源：0/2A、200Hz、50%脉宽、2.5ms相位延迟；其正端接输出、负端接地。
- 两个 Mosfet 的 Ron=0.1Ω、Lon=0、反并联二极管 Rd=0.01Ω、Vfd=0.8V；snubber 为 Rs=100kΩ、Cs=inf，即电阻支路。Powergui 的 DisableSnubberDevices/DisableRonSwitches/DisableVfSwitches 均off，没有忽略这些效应。
- 本题没有“器件选择数字枚举”。直接引用的原库中明确包含双向 `Ideal Switch` 和独立 `Diode`；不能套用 B1 的六种可选器件序号。也不能因库中出现 Ideal Switch 就忽略同一组件的反并联二极管。
- `L` 的 BranchType=L，因此保留字段 Resistance=15 不活动；电容 BranchType=C，其 Resistance=1 字段也不表示1Ω ESR。固定负载 BranchType=R，不能把未活动的 L/C 字段加入电路。

原 `Feedback controller` 的活动选择是 `LabelModeActiveChoice=Variant1`，即连续 PI：误差先经1µs一阶滞后，再计算 `0.5*e_filtered + 200*integral(e_filtered)`，最后在控制器外限幅到[0.01,0.95]。参考电压15V。未活动的离散/定点分支具有5µs采样及延迟，不能混作本次连续支路。

PWM 为原 SPS 两脉冲半桥发生器，50kHz、Unsynchronized、Natural、载波相位90°、Ts=0，外部输入 `2*duty-1`。库 XML 的比较器与 NOT 支路给出互补逻辑，模型没有另设死区块；这属于接线/方程证据，**本次尚未取得两路实际门极序列**。

## 真实运行与失败记录

成功运行完全保留原物理网络、控制器和求解器设置，只用 `SimulationInput` 打开既有 Scope 的日志并将多端口 Scope 改为 Dataset 记录格式。原 SLX hash 未变，成功运行后的 loaded model Dirty=off。

| 量 | 实测值 |
| --- | --- |
| 仿真区间与样本 | 0–10ms，3634点 |
| 实际求解器 | ode23tb，MaxStepSize=10µs |
| 运行耗时 | 4.0101072s，不含 MATLAB 启动 |
| 输出电压末值 / 最大值 | 15.03151066V / 18.14776213V |
| 源电流范围 | 0.000299989–6.90253723A，测量方向为源向桥臂 |
| 实际限幅后 duty 范围 | 0.01–0.95 |

上述结果是可行性记录，没有把末值当成稳态验收、也没有设置事后容差。SLX 保存的 MaxStep=100µs，实际 auto 求解记录为10µs；以真实 metadata 为准。

原模型电感 `SetiL0=off`、电容 `Setx0=off`；字段中的 InitialCurrent/InitialVoltage=0 并非高优先级初值约束。实际 t=0 输出电压约1.124916mV、源电流约0.299989mA。本次没有直接导出电感/电容内部状态，**尚不能声明储能初值严格为零**。如要成为正式参考，须先明确并核对实际初始化规则。

首次原生探针由于原多端口 Scope 使用 Array 格式而拒绝日志，第二轮因原创脚本把两个参数写进一次 `setBlockParameter` 调用而报错；对应日志分别保留为 `native_probe_array_logging_failure.log` 和 `native_probe_setblockparameter_failure.log`。改为逐项设置 Dataset 后成功。这两次是日志配置失败，不能解释成电路不可运行。

另一次 `run_gate_diode_probe.m` 仅尝试对现有两路门极及两个内部 Diode 测量输出使用 DataLoggingOverride，原生仿真执行3.282915s后没有产生 logsout：运行时自动删除了不可用的 override，并把 loaded model 标为Dirty=on。完整警告、MAT和exit1均已保留在 `gate_diode_probe/` 与 `gate_diode_probe_batch.log`；该独立 batch 进程已终止，未保存模型，未关闭用户其他 MATLAB 会话。原件 hash 仍相同。

[官方 ModelLoggingInfo 说明](https://www.mathworks.com/help/simulink/slref/simulink.simulationdata.modellogginginfo.html)将该功能界定为修改已经标记日志的信号设置；它不能替本例标记新的内部信号。现有成功保存的 `out` 只有 Control/Isrc_sps/Vout_sps，没有可供恢复的内部二极管电流数据。

本次已读的 [building-simulink-models/SKILL.md](C:/Users/yu_yi/.agents/skills/building-simulink-models/SKILL.md)要求：

> Use `model_edit` for Simulink, System Composer, and Simscape models (structural changes and parameter configuration).

并明确：

> Don't use `evaluate_matlab_code` with `set_param`/`add_block` to bypass `model_edit` — it skips autolayout, undo tracking, and error recovery

当前可调用工具中没有 model_edit，因此本轮没有用裸 set_param 改信号属性或添加测量端口。此处是**补齐日志的工具限制**，不是已证明的物理不相容，更不是 MATLAB 无法运行该模型。

## 是否进入下一候选

暂不进入实现。互补门极不保证二极管电流为零：即使开通，Ron 电压达到 Vf 时反并联支路也可能分流；开关时刻与初始状态亦需核验。现有源电流日志不能替代下桥臂内部电流，所以既不宣称依赖自动续流，也不宣称可以删除二极管。

若内部日志证实相应工作范围内二极管不活动，电路部分可复用 Switch/Inductor/Capacitor/Resistor/CurrentSource，外加原 snubber 与并联10kΩ。控制仍有维护成本：原来是连续积分与1µs滞后、连续 Natural PWM；现有 PIController 是离散更新，配置上下限还会启用条件积分抗饱和，和本例外置限幅并不相同。不能把当前 PI 限幅参数直接照填便称同一算法。现有 FirstOrderLowPass 采用后退欧拉，也须纳入时间步收敛验证。

对初学者而言，本题同时引入闭环 PI、饱和、测量滞后、50kHz门极时序和器件支路，说明负担大于单纯同步 Buck 功率级。只有在上述边界清楚后才值得作为下一正式教学例；不为本题引入通用自动二极管或新控制框架。更简单的、原本就采用受控双向开关且时间语义清楚的官方参考仍可独立调查。

## 恢复操作

本机启动普通沙箱上下文先出现既有 prefdir 不可写；另一次工作区 prefdir 最小启动遇 MathWorks 服务错误5201。已确认可运行的方式是正常许可上下文配合本次独立目录（只对当前命令生效）：

```powershell
$env:MATLAB_PREFDIR = 'D:/VibeCoding/PyCy_EMT_Lite/.tmp/longterm/matlab-pref-b2-normal'
& 'C:/Program Files/MATLAB/R2025a/bin/matlab.exe' -batch "addpath('local_reference/synchronous_buck'); run_native_probe(pwd)" -logfile D:/VibeCoding/PyCy_EMT_Lite/local_reference/synchronous_buck/native_probe_batch.log
```

已有成功结果不必重复覆盖。下一项有价值的工作是取得可用的模型编辑工具后，在独立本地副本中规范标记现有支路日志，再核实际初始化、门极互补及两体二极管电流；此后才决定是否固定正式协议。尚无 PyCy 对比、参考细化或跨平台验收完成声明。
