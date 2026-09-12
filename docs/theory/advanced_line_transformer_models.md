# 高级线路与变压器模型说明

[English](advanced_line_transformer_models.en.md)

本文说明 π 型线路、Bergeron 线路教学版、单相变压器、三相变压器和同步机教学模型。当前实现定位为教学和算法验证版本，优先保证模型边界清楚、stamp 原理可读、结果可测试。

## 1. π 型线路

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

## 2. Bergeron 线路教学版

`BergeronLine` 是单相分布参数线路教学版，`ThreePhaseBergeronLine` 是三相独立相版本。模型使用特性阻抗 `surge_impedance` 和传播时延 `travel_time` 表示行波延迟。

端口电流采用如下形式：

```text
i_s(t) = v_s(t) / Zc + I_s_hist(t)
i_r(t) = v_r(t) / Zc + I_r_hist(t)
```

其中历史源来自对端延迟时刻的电压和电流：

```text
I_s_hist(t) = -v_r(t - τ) / Zc - i_r(t - τ)
I_r_hist(t) = -v_s(t - τ) / Zc - i_s(t - τ)
```

当前实现只支持固定时间网格，`travel_time` 必须是步长的正整数倍；停止及实际事件时间须对齐网格，采用与仿真器一致的成对 8 ULP 舍入容差。非法配置在首次求解前报错；非对齐事件可选择 `quantize_up` 延后执行。历史按整数步读取，负时间端口历史为零，缺失历史明确报错；同刻事件只保留右侧端口帧。匹配负载到达、到达前无响应及开路/短路反射已有测试。`attenuation` 表示教学用传播衰减；不考虑非整步延时、历史插值、频率相关衰减、模量变换和相间耦合。

## 3. 单相变压器

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

## 4. 饱和励磁简化模型

饱和励磁采用显式滞后教学模型：本时间步使用上一时刻磁链决定励磁电感。

```text
|ψ| < ψ_knee      使用 magnetizing_inductance
|ψ| >= ψ_knee     使用 saturated_magnetizing_inductance
```

磁链用一次侧电压积分：

```text
ψ_k = ψ_{k-1} + v_p,k Δt
```

该做法避免引入非线性迭代，适合解释“饱和后励磁电感下降、励磁电流增大”的趋势。它不是完整铁芯磁滞模型，也不包含剩磁、回线和频率相关损耗。

## 5. 三相变压器

`ThreePhaseTransformer` 支持：

- Y/Y
- Y/Δ
- Δ/Y

接法通过 `primary_connection` 和 `secondary_connection` 指定，取值为 `"Y"` 或 `"D"`。

三相模型由三个单相绕组相组成。Y 接每相连接在 `bus:相别` 与中性点之间；Δ 接采用：

```text
a 绕组：bus:a -> bus:b
b 绕组：bus:b -> bus:c
c 绕组：bus:c -> bus:a
```

`turns_ratio` 表示一次每相绕组电压与二次每相绕组电压之比。含 Δ 接法时，纯理想变压器会形成理想电压约束环；因此教学模型要求设置非零 `leakage_resistance` 或 `leakage_inductance`，以避免 MNA 矩阵奇异。

## 6. 同步机：保留两种有明确边界的模型

两种模型均从 `pycy_emt_lite.machines` 导入，接入现有 `Circuit/Simulator`；示例
[10](../../examples/10_park_generator_avr_governor.py) 使用 `CaseDefinition`。

| 模型 | 保留的方程 | 适用范围 |
|---|---|---|
| `SynchronousMachine` | 固定幅值三相内电势、每相定子 R–L、转子角与转速 | 电路暂态和机电功率教学；不包含励磁、调速器或完整磁链电机 |
| `ParkSynchronousGenerator` | 四阶暂态电势模型，加一阶 AVR 和一阶调速器，共六个状态 | 平衡、近工频的负荷与调节响应；定子快速暂态用代数端口近似 |

Park 模型不用于短路直流偏置、次暂态、不平衡故障、饱和或磁滞分析。
其零序端口只剩定子电阻，不能解释为完整 dq0 模型。恢复模型并不意味着这些效应已经实现。

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

## 7. 使用示例

```python
from pycy_emt_lite import Circuit, PiLine, Resistor, SimulationConfig, Simulator, VoltageSource

components = [
    VoltageSource("V1", "source", "0", 10.0),
    PiLine("LINE", "source", "load", resistance=1.0, inductance=1e-3, capacitance=1e-6),
    Resistor("LOAD", "load", "0", 9.0),
]

circuit = Circuit.from_components("pi_line_demo", components)
config = SimulationConfig(time_step=1e-5, stop_time=0.02)
simulator = Simulator(circuit, config)
result = simulator.run()
```

三相变压器示例：

```python
from pycy_emt_lite import Circuit, Resistor, SimulationConfig, Simulator, ThreePhaseSource, ThreePhaseTransformer

components = [
    ThreePhaseSource("VS", "primary", phase_rms=100.0),
    ThreePhaseTransformer(
        "T1",
        "primary",
        "secondary",
        turns_ratio=2.0,
        primary_connection="Y",
        secondary_connection="Y",
        leakage_resistance=0.01,
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
