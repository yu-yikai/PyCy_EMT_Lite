# 高级线路与变压器模型说明

[English](advanced_line_transformer_models.en.md)

本文说明阶段 5 中新增的 π 型线路、Bergeron 线路教学版、单相变压器、三相变压器和同步机教学模型。当前实现定位为教学和算法验证版本，优先保证模型边界清楚、stamp 原理可读、结果可测试。

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

当前实现对历史样本进行线性插值，并提供 `attenuation` 表示教学用传播衰减。该模型暂不考虑频率相关衰减、模量变换和相间耦合。

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

其中 `n = turns_ratio`，电流方向均定义为流入对应绕组正端。

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

## 6. 同步机经典二阶教学模型

`SynchronousMachine` 使用经典电力系统暂态稳定模型中常见的“内电势后接定子阻抗”结构：

```text
三相内电势 Eabc -- 定子 R-L -- 机端母线
```

参数说明：

- `internal_phase_rms`：三相内电势相电压 RMS，单位 V；若算例采用标幺制，可直接填入相电压标幺值。
- `stator_resistance`：定子等效电阻，单位 Ω 或对应标幺值。
- `stator_inductance`：定子等效电感，单位 H 或对应标幺值。
- `base_power`：摆动方程的三相基准容量，单位 VA。
- `inertia_constant`：惯性常数 H，单位 s。
- `mechanical_power`：机械输入功率，单位 W，可为常数或时间函数。
- `damping`：阻尼系数，使用标幺功率/标幺转速偏差。

转子动态采用二阶摆动方程：

```text
dω_pu/dt = (P_m - P_e - D(ω_pu - 1)) / (2H)
dδ/dt = ω_sync (ω_pu - 1)
```

当前模型用于教学、负荷流初始化复现和系统级暂态趋势验证。它不包含励磁绕组、阻尼绕组、磁饱和、AVR、PSS、调速器和轴系多质量模型；这些高保真结构应在后续非线性迭代和控制器接口更完善后再扩展。

本项目提供 `examples/reproductions/reproduce_loadflow_sm_initialization.py`，用于对比 Simscape Electrical R2026a `LoadflowSMInitializationExample` 中同步机 swing bus 的初始负荷流目标。该对比重点验证机端电压标幺值和相角，而不是完整复刻 Simscape 的励磁/机械暂态细节。

若需要观察励磁和调速动态，可使用 `ParkSynchronousGenerator`。该模型使用 Park dq0 暂态电势方程、一阶 AVR、一阶调速器和摆动方程，验证算例位于 `examples/park_generator_avr_governor.py`。它仍是教学模型，不包含阻尼绕组、磁饱和、PSS 和多质量轴系。

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

同步机示例：

```python
from pycy_emt_lite import Circuit, SimulationConfig, Simulator, SynchronousMachine

components = [
    SynchronousMachine(
        "SM",
        "bus",
        internal_phase_rms=1.02,
        stator_resistance=1e-3,
        stator_inductance=0.0,
        base_power=30e6,
        inertia_constant=3.5,
        mechanical_power=0.0,
        frequency=60.0,
    )
]

circuit = Circuit.from_components("sm_swing_bus_demo", components)
config = SimulationConfig(time_step=1e-4, stop_time=0.2)
simulator = Simulator(circuit, config)
result = simulator.run()
```
