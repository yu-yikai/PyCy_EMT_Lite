# 三相系统建模说明

[English](three_phase_systems.en.md)

本文说明阶段 2 中三相系统的命名、元件模型和结果字段约定。

## 1. 节点命名

阶段 2 采用 `母线:相别` 的节点命名方式：

```text
source:a
source:b
source:c
load:a
load:b
load:c
```

参考地仍使用 `"0"`、`"gnd"` 或 `"ground"`，不附加相别。仿真结果中的节点电压字段会在节点名前加 `v:`，例如：

```text
v:load:a
v:load:b
v:load:c
```

## 2. 三相电源

`ThreePhaseSource` 表示三相对称正序正弦电压源。第一版以相电压有效值 `phase_rms` 为输入，每相等效为一个理想电压源，连接在 `terminal_bus:相别` 与中性点之间。

默认相角为：

```text
a 相：0°
b 相：-120°
c 相：+120°
```

默认频率为 `50 Hz`，单位采用 SI。

## 3. 三相线路

`ThreePhaseLine` 表示三相简化线路。每相从 `from_bus:相别` 连接到 `to_bus:相别`，采用串联 `R-L` 模型。

- `resistance`：每相串联电阻，单位 Ω。
- `inductance`：每相串联电感，单位 H，可取 0。

当 `inductance = 0` 时，线路退化为纯电阻模型；当 `inductance > 0` 时，每相会注册一个支路电流未知量。

## 4. 三相负荷

`ThreePhaseLoad` 表示三相星形负荷。每相从 `bus:相别` 连接到 `neutral`，同样采用串联 `R-L` 模型。

第一版用于教学和故障示例，暂不考虑三角形接法、相间互感、频率相关线路参数和不平衡复杂负荷。

## 5. 事件和故障

显式事件先按旧网络积分到事件左侧，再改变元件状态，固定储能状态求右侧代数量并记录。故障算例通常预先在电路中放置 `Fault` 元件，再通过事件投入和清除：

```python
events = [
    FaultApplyEvent(0.04, "FA"),
    FaultClearEvent(0.08, "FA"),
]
simulator = Simulator(circuit, config, events=events)
result = simulator.run()
```

事件日志保存在 `result.event_log` 中，并会随 JSON 和 NPZ 结果一起保存。

## 6. 基础分析

阶段 2 提供 `pycy_emt_lite.analysis` 中的基础分析函数：

- `rms(result, column)`：计算某一字段 RMS。
- `peak_abs(result, column)`：计算绝对峰值。
- `mean_value(result, column)`：计算平均值。
- `three_phase_rms(result, columns)`：计算三相字段 RMS。

示例：

```python
from pycy_emt_lite.analysis import three_phase_rms

rms_values = three_phase_rms(result, ("v:load:a", "v:load:b", "v:load:c"), start_time=0.05, end_time=0.07)
```

均值和 RMS 按真实时间对分段线性信号积分；窗口端点可以落在采样点之间。时间列必须
有限、严格递增，积分窗口须有正时长且位于数据范围内。不能跨事件或使用包含跳变的
原始采样区间做插值；示例 07 分别使用 0.01–0.03、0.05–0.07、0.09–0.11 s 的完整
50 Hz 周期。`peak_abs` 仍返回窗口内的采样峰值，允许单点窗口。

三相瞬时总有功为 `va*ia + vb*ib + vc*ic`，包含零序功率；平均有功对线性重建的
电压、电流乘积积分。无功采用 αβ 定义，由平均 P/Q 计算的 S/PF 仅用于平衡正弦场景，
不能据此解释通用的不平衡或畸变功率质量。
