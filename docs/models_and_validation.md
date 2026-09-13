# 模型与验证

[English](models_and_validation.en.md) · [运行入口](../README.zh-CN.md) · [数值约定](numerical_conventions.md)

本项目保留小型线性网络、显式开关、控制模块和两种同步机教学模型。下面按实际方程说明证据，
“可运行”“参数检查通过”和“物理关系已核对”分别列明，不把一种证据替代另一种。

## 1. 已验证范围

最近的代码基线为 `f9dee81`（2026-09-13 本地验证）：512 项测试通过，13 个保留算例均在无界面模式运行，
默认未生成输出文件；wheel/sdist 构建、包内容检查及源码目录外安装导入检查通过。
这些是本地证据，不是该提交的远端 CI 状态，也没有声称完成实验数据或商业 EMT 软件全模型对标。
本文的文档合并不改变模型实现。

| 范围 | 已有证据 | 证据边界与测试入口 |
|---|---|---|
| R、RC、RL、RLC | 解析初值/暂态、AC 相量、KCL/KVL、无损 LC 能量、共同时间点收敛 | 声明的线性集中参数电路；[基础测试](../tests/test_basic_components.py) |
| 时间、初始化、显式事件 | 整步终点、三种事件策略、左右侧一致状态、同刻顺序及终点事件 | 不自动定位 callable 跳变；[时间](../tests/test_time_grid.py)、[事件](../tests/test_events.py) |
| 三相 R–L 与故障（05–07） | 平衡相量、分段 RL 解析暂态、单相接地电阻分压、固定窗口 RMS/P/Q | 三相独立相网络；[三相测试](../tests/test_three_phase.py) |
| 单相 π 线、分段线 | 相量/二端口参考、KCL、能量、时间或空间收敛 | 无宽频、相间耦合；[线路测试](../tests/test_line_models.py) |
| 单相/三相 Bergeron | 整步时延、到达前无响应、匹配传输、开路/短路反射、事件右侧历史 | 固定网格、独立相；同一线路测试 |
| 线性单相/三相变压器 | 相量、启动解析解、接线相移、端口功/储能、磁链一致性、时间收敛 | 四种声明接法；无共同铁芯耦合；[变压器测试](../tests/test_transformers.py) |
| 两种同步机及示例 10 | 端口方程、功率方向、平衡点、独立连续 ODE、机电状态一阶收敛 | 声明的简化方程；[经典模型](../tests/test_synchronous_machine.py)、[Park 模型](../tests/test_park_synchronous_generator.py) |
| L/LC/LCL 滤波器 | 参数拒绝、接线、独立 ODE、KCL、离散能量及步长收敛 | 被动线性网络；[电力电子测试](../tests/test_power_electronics.py) |
| PWM 示例 12 | 门极、浮置星点、基波 RL 参考、细网格对照 | 细网格不构成器件参考，边沿不自动定位；同一电力电子测试 |
| `ThreePhasePiLine`、`ThreePhaseParallelRLCLoad` | 初值/第一步、输出字段；并联负荷另有额定功率换算检查 | 局部检查，未建立完整独立三相 AC/故障验证；三相/线路测试 |
| 控制块与 SRF-PLL | 限幅、PI、低通、延迟、平衡变换、特定平衡电压下锁频 | 功能及单一工况检查；无闭环电网/弱网工程验证；[控制测试](../tests/test_controls.py) |
| 饱和励磁近似 | 参数与线性磁链/电流关系回归 | **未完成独立饱和曲线、能量或涌流验证**；不能以线性测试替代 |

指标、结果读写、绘图和线性求解器另有 [指标](../tests/test_analysis.py)、[读写](../tests/test_results_io.py)、
[绘图/报告](../tests/test_visualization_reporting.py)、[求解器](../tests/test_solvers.py) 回归；它们验证工具行为，
不能为未验证模型背书。已有 [CI 配置](../.github/workflows/ci.yml) 沿用锁定安装、测试、算例、构建和包外导入，
无需再建第二套运行流程。

## 2. 基础电路与单相交流 RLC

基础电源和 R/L/C 的方向与 stamp 见数值约定。直流阶跃的解析参考为
`vC(t)=Vs+(vC0−Vs)exp(−t/RC)`、`iL(t)=Vs/R+(iL0−Vs/R)exp(−Rt/L)`。
串联 RLC 满足 `L di/dt=vs−Ri−vC`、`C dvC/dt=i`；启动过程不能用稳态相量代替。
无损 LC 的储能为 `(Li²+CvC²)/2`。测试同时检查声明初值和整个暂态，避免只看终值掩盖第一步误差。

[示例 17](../examples/17_single_phase_ac_rlc.py) 使用 220 V RMS、50 Hz 电源，串联 R=20 Ω、L=50 mH、C=100 μF。
正弦源峰值需写成 `sqrt(2)*Vrms`；不要把 220 直接当成峰值。稳态参考为：

```text
Z = R + j(ωL − 1/(ωC))
I = Vrms / Z
VL = jωL I, VC = I/(jωC), VR = R I
```

在 0.08–0.12 s 的两个周期核对电流/电压 RMS、相位与 KVL，电压、电流分别绘图；默认不保存。
修改电源幅值、频率或 R/L/C 后，也应重新选择稳态窗口并检查最短时间尺度。
详细的建例模板和保存方式只在 README 维护。

## 3. 三相网络与故障

`ThreePhaseSource` 以 `phase_rms`（V）、`frequency`（Hz）及相角构造 abc 正序正弦电压；
默认相角差为 0/−120/+120°。对称 Y 系统线电压 RMS 为相电压的 √3 倍，不能混用两个额定值。
`ThreePhaseLine` 为三条独立串联 R–L 支路，`ThreePhaseLoad` 为各相到 `neutral` 的星形串联 R–L 负荷。
电阻用 Ω、电感用 H；允许省略零电感，具体零阻抗组合在构造时检查。没有相间互感或自动不平衡负荷分配。

`pycy_emt_lite.components.three_phase.ThreePhaseParallelRLCLoad` 把三相总额定 P、QL、QC 换算成每相并联支路。
令 `Vp=nominal_line_voltage/sqrt(3)`、`ω=2π frequency`，则
`R=Vp²/(P/3)`、`L=Vp²/[ω(QL/3)]`、`C=(QC/3)/(ωVp²)`。
`active_power` 用 W，`inductive_power/capacitive_power` 用非负 var；为零时省略对应支路，三者不能全为零。
它是额定点换算的**固定阻抗负荷**，端电压变化后功率随之变化，不维持恒 P/Q。
现有检查限于换算、输出及初始化/第一步，不外推完整故障验证。

`Fault` 在投入时把指定节点经有限正电阻接到地，退出时无支路电导；`Breaker` 在闭合时用有限正电阻，
断开时无支路电导。先把它们放入电路，再使用标准事件切换。事件执行顺序与不支持冲量的边界见数值约定。

示例 05 每相负荷为 20 Ω 串联 50 mH，线路电阻为 0.5 Ω。50 Hz 时感抗约 15.7 Ω，
`I=Vsource/(Rline+Rload+jωLload)`、`Vload=I(Rload+jωLload)`。
0.06–0.10 s 的两个周期用于 RMS 和三相 P/Q，电流相对本相电源电压滞后约 37.46°。
三相电感电流从零启动，包括 t=0 电源电压非零的 B/C 相。

示例 06 每相线路为 0.8 Ω、5 mH，负荷 50 Ω，故障电阻 0.1 Ω；0.04 s 投入、0.08 s 清除。
每阶段满足 `L di/dt+(Rline+Req)i=vsource`，正常时 `Req=Rload`，故障时 `Req=Rload || Rfault`。
电感电流连续，`vbus=Req i` 和故障电流可以跳变。清除时线路电流转入负荷，默认母线峰值约 7.79 kV，
按约 98 μs 的时间常数 `L/(Rline+Rload)` 衰减，故步长为 10 μs。
这是未含寄生电容、避雷器和电弧的教学电路；不是设备绝缘水平预测。三种量分别绘图。
测试以分段正弦特解加指数暂态核对初值、切换电流、全波形及固定窗口指标。

06/07 采用 0.01–0.03、0.05–0.07、0.09–0.11 s 的完整 50 Hz 周期。
06 的故障窗口仍含衰减分量，各相 RMS 可以不同；每相电阻负荷平均有功为 `Vbus_rms²/Rload`。
07 的单相接地电阻网络另以故障相/健全相分压验证。跨事件积分限制见数值约定。

## 4. π 型与分段线路

`PiLine` 是单相集中参数线路模型，`ThreePhasePiLine` 是三相独立相版本。每相由以下部分组成：

```text
发送端 -- 串联 R-L -- 接收端
发送端 -- C/2 -- 地
接收端 -- C/2 -- 地
```

参数单位：

- `resistance`：串联电阻，单位 Ω。
- `inductance`：串联电感，单位 H，可取 0。
- `capacitance`：线路总对地电容，单位 F，可取 0。

三者必须有限且非负，R/L 不能同时为零。

适用范围：

- 适合中短线路的集中参数暂态教学。
- 暂不考虑频率相关参数、相间互感和分布参数行波效应。

示例 08 在 0.02–0.06 s 的两个完整周期内，用有效值相量核对受端电压与串联电流：

```text
Yrecv = 1/Rload + jωC/2
Vrecv = Vsend / (1 + (R + jωL)Yrecv)
Iseries = Yrecv Vrecv
```

已验证两端电容电流、KCL、整个启动过程的储能/端口功平衡，以及相同物理时间点上的误差收敛：
梯形法步长减半误差约缩为 1/4，后退欧拉约缩为 1/2。梯形法的离散能量检查用区间两端电压/电流的平均值计算端口功；
储能为 `L Iseries²/2 + C(Vsend²+Vrecv²)/4`。示例的 RMS 和电阻有功采用现有分段线性指标。

### 分段线路：比较空间离散误差

`pycy_emt_lite.components.lines.SegmentedLine` 把总 R/L/C 等分为 N 个 π 段；每段两端各有 C/(2N)，
内部节点相邻两只电容合计 C/N。R/L/C 分别使用 Ω/H/F，`sections` 为正整数，允许 L 或 C 为 0，R/L 不能同时为 0。
它保留为集中参数线路课程的可选对照，不另建仿真流程；增加段数不会自动消除时间步长误差，也不包含相间耦合或频率相关参数。

现有 `i:LINE:sending`、`i:LINE:receiving` 分别是首段和末段的**串联电流**，
`i:LINE:average` 是各段串联电流的算术平均，均沿发送端到接收端为正。
端口总电流另包含端部电容：`Iin=Ifirst+C/(2N)·dVsend/dt`，`Iout=Ilast-C/(2N)·dVrecv/dt`，
这里 Iin 流入发送端，Iout 流出接收端。不能直接用上述串联电流输出计算端口功率。
例如 C=40 μF、N=4、发送电压 `10 sin(2π50t)` V、零储能初值时，t=0 的 Ifirst=0，Iin=0.015708 A。

独立交流参考从单段二端口矩阵级联得到：

```text
Z = R + jωL, Y = jωC, z = Z/N, y = Y/N
Mπ = [[1+zy/2, z], [y(1+zy/4), 1+zy/2]]
[Vsend, Iin]ᵀ = Mπᴺ [Vrecv, Iout]ᵀ
```

连续均匀线参考为 `exp([[0,Z],[Y,0]])`，对应从受端向送端、归一化长度 0–1 上的电压电流空间方程。
在总 R=8 Ω、L=60 mH、C=40 μF、负荷 30 Ω、100 V RMS/50 Hz 下，测试用独立相量初始化，
固定 10 μs 步长和 0–0.02 s 窗口。N=1/2/4/8 的受端复相量误差依次约为
1.6680/0.40882/0.10171/0.025407 V，段数加倍后误差约缩为 1/4。
另验证零初值、无电容退化、端部电容 KCL，以及无线路电阻时的储能与端口功/负荷耗能平衡。
这些证据针对声明的线性均匀参数模型，不代表完整分布参数线路的宽频暂态验证。

## 5. Bergeron 线路

`BergeronLine` 是单相分布参数线路教学版，`ThreePhaseBergeronLine` 是三相独立相版本。模型使用特性阻抗 `surge_impedance` 和传播时延 `travel_time` 表示行波延迟。

端口电流采用如下形式：

```text
i_s(t) = v_s(t) / Zc + I_s_hist(t)
i_r(t) = v_r(t) / Zc + I_r_hist(t)
```

两端电流均以流入线路为正；Zc 用 Ω，τ 用 s。`attenuation=1` 时，历史源来自对端延迟时刻的电压和电流：

```text
I_s_hist(t) = -v_r(t - τ) / Zc - i_r(t - τ)
I_r_hist(t) = -v_s(t - τ) / Zc - i_s(t - τ)
```

当前实现只支持固定时间网格，`travel_time` 必须是步长的正整数倍；停止及实际事件时间须对齐网格，采用与仿真器一致的成对 8 ULP 舍入容差。非法配置在首次求解前报错；非对齐事件可选择 `quantize_up` 延后执行。历史按整数步读取，负时间端口历史为零，缺失历史明确报错；同刻事件只保留右侧端口帧。匹配负载到达、到达前无响应及开路/短路反射已有测试。`surge_impedance` 必须为有限正数，`attenuation` 在 (0,1] 内，表示教学用传播衰减；不考虑非整步延时、历史插值、频率相关衰减、模量变换和相间耦合。

## 6. 单相线性变压器

`SinglePhaseTransformer` 使用以下结构：

```text
一次绕组端口 -- 一次侧折算漏阻抗 -- 理想变比 -- 二次绕组端口
一次绕组端口并联励磁支路
```

参数说明：

- `turns_ratio`：一次绕组电压与二次绕组电压之比，即 `Vp / Vs`。
- `leakage_resistance`：折算到一次侧的漏电阻，单位 Ω。
- `leakage_inductance`：折算到一次侧的漏感，单位 H。
- `magnetizing_inductance`：线性励磁电感，单位 H。
- `core_loss_resistance`：铁耗电阻，单位 Ω。

变比必须有限且为正；漏阻/漏感有限且非负。励磁电感与铁耗电阻可为 `None` 以省略支路，否则必须有限且为正。
饱和拐点与饱和电感必须同时给出有限正值，并提供线性励磁电感。

理想变比约束为：

```text
v_p - n v_s - Z_leak i_p = 历史项
i_s + n i_p = 0
```

其中 `n = turns_ratio` 是理想绕组变比；带载端电压比还受漏阻抗影响。电流方向均定义为流入对应绕组正端。
`i:T1:primary` 是漏阻抗/理想变比支路电流，不含并联励磁或铁耗电流；示例 09 的电源输入总电流为 `-i:V1`。
对于一次侧正弦电压和二次电阻负载，线性模型的有效值相量满足：

```text
Ileak = Vpri / (Rleak + jωLleak + n²Rload)
Vsec = n Rload Ileak
Isecondary = -n Ileak
Iinput = Ileak + Imag + Vpri/Rcore   # 未设置铁耗电阻时省略末项
```

零初值且一次电压为 `sqrt(2) Vrms sin(ωt)` 时，理想励磁电感电流为
`im(t) = sqrt(2) Vrms (1-cos(ωt))/(ωLm)`；直流分量不会自行衰减，计算电源总 RMS 时必须计入。
示例 09 在 0.02–0.06 s 比较带载电压、总电流与解析值，并检查输入有功减负载有功、铜损的残差。
测试另覆盖可选铁耗支路、全启动过程能量平衡和两种方法的步长收敛。这些结果仅验证线性模型，不扩展到饱和或磁滞。

## 7. 磁链与未验证的饱和近似

饱和励磁采用显式滞后教学模型：本时间步使用上一时刻磁链决定励磁电感。

```text
|ψ| < ψ_knee      使用 magnetizing_inductance
|ψ| >= ψ_knee     使用 saturated_magnetizing_inductance
```

磁链用一次侧电压积分，方法与励磁电感保持一致：

```text
梯形法：    ψ_k = ψ_{k-1} + (v_p,k-1 + v_p,k) Δt/2
后向欧拉：  ψ_k = ψ_{k-1} + v_p,k Δt
```

线性 Lm 下应满足 `ψ(t)-ψ(0)=Lm·(im(t)-im(0))`；单相/三相、两种积分方法及非整步/终点事件已有回归。
旧实现一律用后向欧拉积磁链，导致梯形法下磁链与电流不一致，现已修正。
饱和电感仍按上一时刻磁链选择，不引入非线性迭代；该近似未通过独立饱和曲线或能量验证，不能由线性回归推断涌流准确性。
不包含完整铁芯磁滞、剩磁、回线和频率相关损耗。

## 8. 三相变压器

`ThreePhaseTransformer` 支持：

- Y/Y
- Y/Δ
- Δ/Y
- Δ/Δ

接法通过 `primary_connection` 和 `secondary_connection` 指定，取值为 `"Y"` 或 `"D"`。

三相模型由三个单相绕组相组成。Y 接每相连接在 `bus:相别` 与中性点之间；Δ 接采用：

```text
a 绕组：bus:a -> bus:b
b 绕组：bus:b -> bus:c
c 绕组：bus:c -> bus:a
```

`turns_ratio=n` 为理想绕组匝数比；漏阻抗折算到一次每相，单位 Ω/H，励磁电感和铁损电阻也按一次绕组定义。
二次侧为 Δ 且漏阻抗为零时，绕组环流无法唯一确定，创建时要求将 `leakage_resistance` 或 `leakage_inductance` 设为正数。
Δ/Y 可以使用零漏阻抗；程序不再将一次侧含 Δ 直接判为不可求解。Y 中性点默认接地；浮置网络仍须有实际电路约束，程序不自动补泄漏电阻。

按以上绕组方向和 abc 正序，无漏阻抗压降时的线电压关系为：

| 一次/二次 | 二次/一次线电压 RMS | 二次相对一次的相移 |
|---|---|---|
| Y/Y | 1/n | 0° |
| Y/Δ | 1/(√3 n) | −30° |
| Δ/Y | √3/n | +30° |
| Δ/Δ | 1/n | 0° |

表中含二次 Δ 的理想值是非零漏阻抗趋近于零时的参考；带载压降和相角还受实际漏阻抗影响。
输出 `i:T:primary:a` 是 a 绕组漏阻抗支路电流，不含励磁/铁损；`i:T:secondary:a` 沿二次绕组正端流入，满足 `Is=-n Ip`。
Δ 侧的线电流是相邻绕组电流之差：`Iline,a=Iw,a-Iw,c`，其余两相轮换；一次侧要先把励磁与铁损电流加到 Iw。
接地星形负荷上的输出线电流方向与二次绕组流入方向相反，不能把绕组电流直接当作负荷相电流。

四种接法均已用电感电流从零启动的独立 RL 解析解检验。测试设置一次相电压 100 V RMS/50 Hz、n=2、
Rleak=0.2 Ω、Lleak=20 mH、Lm=2 H、Rcore=1000 Ω，二次每相接地负荷为 10 Ω。
平衡星形负荷折算到 Δ 绕组为 3Rload；每个绕组用 `Vp/(Rleak+jωLleak+n²Rw)` 得到稳态电流，叠加零初值指数暂态。
核对整个 0–0.02 s 区间的端口电压、两侧线/绕组电流、励磁直流分量、磁链与铜损/铁损/储能平衡。
20/10 μs 的共同时间点误差比，梯形法约 4，后向欧拉约 1.95–2.00；后者的能量账包含数值耗散。
另验证零漏阻抗 Y/Y、Δ/Y 在不平衡电阻负荷下的电压和功率。该模型用于比较三相接线的变比与相移；证据不外推到共同铁芯耦合、任意矢量组或饱和故障。

## 9. 同步机

两种模型均从 `pycy_emt_lite.machines` 导入，接入现有 `Circuit/Simulator`；示例
[10](../examples/10_park_generator_avr_governor.py) 使用 `CaseDefinition`。

| 模型 | 保留的方程 | 适用范围 |
|---|---|---|
| `SynchronousMachine` | 固定幅值三相内电势、每相定子 R–L、转子角与转速 | 电路暂态和机电功率教学；不包含励磁、调速器或完整磁链电机 |
| `ParkSynchronousGenerator` | 四阶暂态电势模型，加一阶 AVR 和一阶调速器，共六个状态 | 平衡、近工频的负荷与调节响应；定子快速暂态用代数端口近似 |

Park 模型不用于短路直流偏置、次暂态、不平衡故障、饱和或磁滞分析。
其零序端口只剩定子电阻，不能解释为完整 dq0 模型。

### 单位、方向和端口

电流从内部电势流向机端为正，端口功率 `p` 为向外部网络送出的三相总有功（W）。
`base_power` 是三相总容量（VA），`base_phase_rms` 是相电压有效值（V）：

```text
Zbase = 3 Vbase_rms² / Sbase
Vbase_peak = sqrt(2) Vbase_rms
Ibase_peak = sqrt(2) Sbase / (3 Vbase_rms)
theta = 2 pi frequency t + rotor_angle
```

经典模型的 `stator_resistance/stator_inductance` 分别用 Ω/H，不能直接传入标幺电抗。
`inertia_constant` 用 s，`frequency` 用 Hz，`rotor_angle` 用电角度 rad，`speed_pu` 为转速标幺值。
`damping` 表示相对同步转速偏差对应的标幺阻尼功率系数。经典模型的 `mechanical_power` 用 W，
可以为常数或时间函数；Park 的 `mechanical_power_*_pu` 用三相容量基准。

Park 定义 d 轴为 `-cos(theta)`、q 轴为 `sin(theta)`：调用通用 `abc_to_dq` 后，
两个分量均取负再除以峰值基准；反变换为 `dq_to_abc(-ed, -eq, theta)`。
因此不能直接沿用旧实现只翻转 q 轴的电流符号。
各相角为 `theta`、`theta-2pi/3`、`theta+2pi/3`。标幺端口方程为：

```text
Vd = Ed' - Rs Id + Xq' Iq
Vq = Eq' - Rs Iq - Xd' Id
```

两轴暂态电抗分别进入端口。令矩阵 M 的各行为 `[-cos(theta_phase), sin(theta_phase)]`，
则实际值 abc 支路满足 `Eabc - Vabc = Zabc Iabc`，其中：

```text
Zabc = Rs_ohm I3 + Zbase M [[0, -Xq'], [Xd', 0]] (2/3 M^T)
```

该线性、随转角变化的耦合 stamp 沿用现有求解器。Park 定子电流为代数量；
旧 `stator_inductance` 推导属性和电感历史项已取消，不再把 `X'd` 当成三相独立动态电感。

### 功率、状态和初值

经典模型使用 `P_em = sum(e_phase*i_phase)`；它与端口功率之差包含铜损及定子 R–L 储能交换。
Park 忽略定子快速储能，使用 `P_em = P_terminal + P_copper`。平衡条件下：

```text
P_terminal / Sbase = Vd Id + Vq Iq
P_copper / Sbase = Rs (Id² + Iq²)
P_em / Sbase = Ed' Id + Eq' Iq + (Xq' - Xd') Id Iq
```

最后一项为凸极磁阻项；两轴暂态电抗不同时，不能只把暂态内电势与电流的乘积当作气隙功率。
两种模型输出 `p`（端口）、`p_copper`（铜损）和 `p_em`（电磁/气隙功率），单位均为 W。
机械状态使用功率形式的摆动方程，保留速度分母：

```text
dspeed_pu/dt = (Pm/Sbase - P_em/Sbase - D(speed_pu-1)) / (2 H speed_pu)
drotor_angle/dt = 2 pi frequency (speed_pu-1)
```

Park 的其余状态方程为：

```text
dEq'/dt = (Efd - Eq' - (Xd-Xd') Id) / Tdo'
dEd'/dt = (-Ed' + (Xq-Xq') Iq) / Tqo'
dEfd/dt = (Efd_initial + Kavr (Vref-Vt) - Efd) / Tavr
dPm_pu/dt = (Pm_reference - (speed_pu-1)/droop - Pm_pu) / Tgov
```

`Vt=hypot(Vd,Vq)`；励磁以 `initial_efd_pu` 为偏置，因此 `avr_gain=0` 时保持给定励磁。
所有时间常数以 s 表示，电压、电抗、控制限幅及参考采用对应标幺量。
励磁和机械功率更新后分别限制在 `efd_min/max_pu`、`mechanical_power_min/max_pu` 内。

`t=0` 保持声明的动态状态后解网络。经典模型定子电流初值为零；Park 电流由上述端口方程求得，
一般不为零。机电和控制状态始终用同一左端反馈显式欧拉推进一次，然后求当前网络并记录；
同一结果行的转角、暂态电势和 abc 输出属于同一时刻。正时间区间上的机电耦合是一阶精度，
`SimulationConfig.method` 只决定经典模型定子 R–L 及外部储能元件的积分方法。
显式事件固定动态状态求右侧网络；Park 电流允许代数跳变，经典模型电感电流连续。

本模型不自动做潮流初始化。示例 10 用平衡电阻负荷的解析关系生成初值：
`I=1/Rload_pu`、`A=Rload_pu+Rs`、`Iq=I A/hypot(A,Xq)`、`Id=I Xq/hypot(A,Xq)`，
再由端口及状态方程求 `Ed'/Eq'/Efd/Pm`。初始端口为 100 V RMS、1000 W，铜损 13.333333 W，
机械输入为 1013.333333 W。0.2 s 时每相并入 18 Ω（加断路器 1 mΩ），默认计算到 0.6 s；
这个终点用于观察暂态，不声称已经达到新的稳态。

运行 `uv run python examples/10_park_generator_avr_governor.py`。修改顶部容量、电压、阻抗、
负荷、时间和保存开关即可；`define_case()` 中保留励磁、调速器和惯性参数。
默认分别显示电压/励磁、转速、功率三张图，不保存文件；启用保存后每张图有固定文件名。
任意非有限数、负阻抗、非正时间常数/惯性、倒置限幅或越界初值会报出参数及修复方法。
应减小步长并做收敛检查；Park 内部理想电势节点若被额外理想约束要求求导，明确报不支持，
应解除内部约束并从带有限阻抗的机端连接外部电路。

### 现有验证与限制

- 经典模型：纯电阻分压、铜损造成的解析减速；独立积分转子和三相 R–L 电流、离散储能平衡、转角一阶收敛。
- Park 模型：非相等 d/q 暂态电抗的解析端口电流、abc/dq 方向、气隙功率含磁阻项、同刻状态与内电势一致。
- 示例 10：阶跃前平衡点保持、阶跃后 KCL/端口方程、独立分段连续 ODE 对照；200/100/50 μs 在共同时间点呈一阶收敛；t=0、非对齐和终点事件不重复推进状态。
- 数值/参数检查是本项目近似方程的验证，不等于与厂商完整电机模型或实验数据对标。复杂故障与控制器工程定值不在上述证据范围内。

建模层级和显式推进顺序可参见 [PowerWorld 的暂态稳定建模说明](https://www.powerworld.com/files/T01ModelRelationships.pdf)；
完整电机 dq 变换和绕组结构参见 [PSCAD Basic Machine Theory](https://www.pscad.com/webhelp/EMTDC/Rotating_Machines/basic_machine_theory.htm)。
本节明确给出本项目实际采用的近似和符号约定，不把这些参考软件的功能视为项目已实现的功能。

## 10. 开关、滤波器与 PWM

### 显式开关

`pycy_emt_lite.components.power_electronics` 提供：

- `IdealSwitch`：由布尔值或时间函数控制导通状态，导通时写入 `1/closed_resistance`，关断时写入 `open_conductance`。
  前者电阻必须为有限正数（Ω），后者电导必须有限且非负（S），可为零。

该模型属于显式电导近似，不代表完整器件级模型。PWM 验证包括门极时序、导通/关断电导、
电流方向和基波；不求解半导体非线性伏安关系或开关损耗。

### 滤波器组合

`pycy_emt_lite.converters` 导出三个可选的单相组合类，用于学习滤波器接线和阻尼。
调用 `.components()` 得到普通 R/L/C 列表，直接接入现有 `Circuit/Simulator`；组合本身没有动态状态或独立求解流程。

| 组合 | 接线与电流方向 |
|---|---|
| `LFilter` | `input_node → series_resistance → inductance → output_node`；电流沿输入到输出为正 |
| `LCFilter` | 同一串联 R–L 支路，输出节点另接 C 到 `ground`；电容电流沿输出到地为正 |
| `LCLFilter` | `converter_node → R1/L1 → capacitor_node → R2/L2 → grid_node`；中间节点经串联 Rd–C 接地，i1 流入中间节点，i2 流向电网 |

电感单位 H、电容单位 F、电阻单位 Ω；L/C 必须大于 0，三个组合中的电阻均可为 0，表示省略对应电阻。
`damping_resistance` 是与 C **串联**的阻尼电阻。Rd=0 时 C 直接接中间节点，不能解释为省略电容。
所有电气参数须为有限实数；创建组合时即拒绝负值、NaN/Inf、布尔值或非数值，并指出名称、参数和修复范围。
例如 `series_resistance=-1` 原来会静默省略电阻，现在报错；无损支路请明确写 0。

以下 LC 接线可直接运行；电源为 10 V 峰值、50 Hz，负荷为 10 Ω：

```python
import math
from pycy_emt_lite import Circuit, Resistor, SimulationConfig, Simulator, VoltageSource
from pycy_emt_lite.converters import LCFilter

filter_ = LCFilter("F", "src", "load", "0", inductance=0.01,
                   capacitance=1e-4, series_resistance=0.5)
components = [
    VoltageSource("V", "src", "0", lambda t: 10 * math.cos(2 * math.pi * 50 * t)),
    *filter_.components(),
    Resistor("LOAD", "load", "0", 10.0),
]
result = Simulator(Circuit.from_components("lc_filter", components),
                   SimulationConfig(time_step=1e-5, stop_time=0.02)).run()
print(result.rows[-1]["v:load"])
```

组合生成的 iL/vC 初值均为 0；需要非零初值时，在构建电路前使用 `dataclasses.replace`
替换列表中电感的 `initial_current` 或电容的 `initial_voltage`。每次仿真重新调用 `.components()` 取得新元件。
结果沿用各基础元件名称，例如 LC 的 `i:F:L`、`i:F:C`；LCL 的 `i:F:converter:L`、`i:F:grid:L`、`i:F:C`。
Rd>0 时，中间节点相对 `ground` 的电压为 `vC + Rd·(i1-i2)`，电容上端是内部节点 `F:damping`；Rd=0 时两者电压相同。

独立参考直接积分下列电路方程，不调用组合的 stamp 或状态更新：

- LC 接电阻负荷 Rload：`L·di/dt = vin-Rs·i-vC`，`C·dvC/dt = i-vC/Rload`。
- LCL 两端接独立电压源：`ic=i1-i2`，`vm=vC+Rd·ic`，
  `L1·di1/dt=vconv-R1·i1-vm`，`L2·di2/dt=vm-R2·i2-vgrid`，`C·dvC/dt=ic`。
- LCL 储能 `E=(L1·i1²+L2·i2²+C·vC²)/2`；功率关系为
  `dE/dt=vconv·i1-vgrid·i2-R1·i1²-R2·i2²-Rd·ic²`。

现有回归覆盖零初值、源端电流方向、KCL、Rd 压降和全过程离散能量平衡，包含零电阻及有阻尼情况。
L 的串联结构由 LC/LCL 复用并一同检查。参考采用 SciPy DOP853，比较窗口为 0–0.02 s 的共同时间点：
LC 使用上面的参数并对照 Rs=0，步长 20/10 μs；LCL 使用 L1=10 mH、L2=5 mH、C=100 μF，
两端电压为 `10 cos(2π50t)` V 和 `6 cos(2π50t-0.2)` V，电阻为全零或 `(R1,R2,Rd)=(0.4,0.3,2)` Ω，步长 5/2.5 μs。
步长减半的最大状态误差比，梯形法约 4，后向欧拉约 1.93–1.99。

梯形法用区间端值的平均电压/电流核对储能与端口功、真实电阻损耗；后向欧拉还需计入每步
`(ΣL·Δi²+ΣC·Δv²)/2` 的数值耗散。无阻尼 LCL 在 2.5 μs 下的最大 vC 误差仍约 0.541 V，
梯形法约 0.000387 V；后向欧拉的衰减不能解释为真实阻尼。这些检查针对线性被动滤波网络，不代表闭环并网变流器验证。

### PWM 教学示例

- `examples/12_two_level_pwm_generator.py`：两电平 PWM 逆变器驱动 RL 负载，使用 `IdealSwitch` 与三角载波比较生成门极信号。

示例 12 在 0.1–0.2 s（6 个 60 Hz 周期和 100 个载波周期）报告各相电流总 RMS、基波 RMS 及相位差。
相位以各相未保持的正弦参考为准；基波平均模型包含零阶保持的 `sinc(f Ts) exp(-jωTs/2)` 和开关导通电阻。
该参考只适用于线性调制区，不含开关纹波；总 RMS 不等于基波 RMS。

现有测试验证互补门极、浮置星点的相电压、三相电流和为零及基波 RL 阻抗。
5/2.5/1.25 μs 在共同的 0.05–0.10 s 窗口比较：相对 1.25 μs，默认 5 μs 的最大基波相量差约 0.214%，
2.5 μs 约 0.094%；电流波形 RMS 差分别小于 0.6 A、0.3 A。细网格是步长对照，不是器件物理参考。
`event_time_policy` 仅约束显式事件，不会自动定位 callable 门极边沿，因此不承诺 PWM 的二阶波形收敛、死区或器件级行为。

## 11. 控制模块与 SRF-PLL

`pycy_emt_lite.controls` 提供由算例显式调用的离散控制块，不直接写入 MNA。
`block.step(input_value, time_step)` 使用本次控制采样间隔；`block.reset()` 重置控制块自身，
不能据此恢复 `Simulator`。采样、测量和控制输出如何连接由调用代码负责，没有隐藏的闭环调度器。

| 模块 | 实际离散关系 |
|---|---|
| `Limiter` | 上下限裁剪，无动态状态 |
| `PIController` | 候选积分 `xi_new=xi+Ki*e*h`，输出为限幅后的 `Kp*e+xi_new`；饱和且误差继续推动同一方向时不保存候选积分 |
| `FirstOrderLowPass` | `dy/dt=(u−y)/tau` 的后向欧拉：`y_new=(y+h*u/tau)/(1+h/tau)` |
| `SampleDelay` | 整采样周期队列延迟；初始队列由 `initial_value` 填充，零步延迟直接输出输入 |

幅值不变 Clarke/Park 变换为：

```text
alpha = 2/3 * (a - b/2 - c/2)
beta  = sqrt(3)/3 * (b - c)
d = alpha cos(theta) + beta sin(theta)
q = -alpha sin(theta) + beta cos(theta)
```

`dq_to_abc()` 按零序为零反变换；无零序分量的平衡信号往返已有测试，不应认为它保留任意输入的零序。
同步机的 d/q 轴取向见第 9 节，不能与上述通用变换直接混用。

`SRFPLL.step(voltages_abc, time_step)` 先用旧角度得到 d/q，再推进 PI、频率和角度：

```text
Vbase = max(abs(vd), abs(vq), 1.0)
Δω = PI(vq / Vbase)
ω_new = nominal_frequency + Δω
θ_new = wrap_0_to_2pi(θ_old + ω_new h)
```

`nominal_frequency` 和输出 `frequency` 都是 **rad/s**，不是 Hz；50 Hz 应传 `2π50`。
现有 `minimum_frequency/maximum_frequency` 实际传入 PI 输出限幅，约束 **Δω**，不是绝对 ω。
返回 `PLLState` 的角度/频率已推进，d/q 电压仍由本次输入和推进前角度计算，不能直接视为同刻重构的一组量。

[示例 11](../examples/11_pll_dynamic_response.py) 是纯控制循环，结果方法标记为 `explicit_control`，没有 MNA 网络。
它在标记 t=0 的首行就调用了一次 `step`；该行不是网络仿真器意义的未推进一致初值。
它使用 230 V RMS、50 Hz、30° 相位偏移、100 μs 采样和 1 s 时长，仅展示该输入下的锁定过程。
现有测试用 325 V 峰值、50 Hz、100 μs、PI 增益 80/1000 的平衡输入检查约 0.1 s 后
`|vq|<5 V`、角频率误差 `<2 rad/s`。这不验证频率/相位突变的动态指标、完整参数异常处理或弱网稳定性。
没有负序解耦、陷波器、专用限幅恢复或闭环并网控制的验证。

PWM 辅助函数 `triangular_carrier()` 生成 [-1,1] 三角载波，`sine_pwm_duty()` 根据调制比和电角度给出占空比，
`carrier_compare()` 输出 0/1 比较结果。空间矢量调制、三电平调制和死区不是当前承诺的功能。

## 12. 可选接线示例

分段线路示例（零储能初值，10 V 峰值/50 Hz 电源）：

```python
import math
from pycy_emt_lite import Circuit, Resistor, SimulationConfig, Simulator, VoltageSource
from pycy_emt_lite.components.lines import SegmentedLine

components = [
    VoltageSource("V1", "source", "0", lambda t: 10 * math.sin(2 * math.pi * 50 * t),
                  derivative=lambda t: 10 * 2 * math.pi * 50 * math.cos(2 * math.pi * 50 * t)),
    SegmentedLine("LINE", "source", "load", resistance=1.0, inductance=1e-3, capacitance=1e-6, sections=4),
    Resistor("LOAD", "load", "0", 9.0),
]

circuit = Circuit.from_components("segmented_line_demo", components)
config = SimulationConfig(time_step=1e-5, stop_time=0.02)
simulator = Simulator(circuit, config)
result = simulator.run()
```

Δ/Y 三相变压器示例（零漏阻抗，二次相电压约 86.6025 V RMS）：

```python
from pycy_emt_lite import Circuit, Resistor, SimulationConfig, Simulator, ThreePhaseSource
from pycy_emt_lite.components.transformers import ThreePhaseTransformer

components = [
    ThreePhaseSource("VS", "primary", phase_rms=100.0),
    ThreePhaseTransformer(
        "T1",
        "primary",
        "secondary",
        turns_ratio=2.0,
        primary_connection="D",
        secondary_connection="Y",
        magnetizing_inductance=10.0,
    ),
    Resistor("LA", "secondary:a", "0", 50.0),
    Resistor("LB", "secondary:b", "0", 50.0),
    Resistor("LC", "secondary:c", "0", 50.0),
]

circuit = Circuit.from_components("transformer_demo", components)
config = SimulationConfig(time_step=1e-4, stop_time=0.1)
simulator = Simulator(circuit, config)
result = simulator.run()
```
