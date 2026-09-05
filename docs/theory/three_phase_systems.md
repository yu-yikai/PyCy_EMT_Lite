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

阶段 2 的事件系统支持在固定时间步开始前改变元件状态。故障算例通常预先在电路中放置 `Fault` 元件，再通过事件投入和清除：

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

rms_values = three_phase_rms(result, ("v:load:a", "v:load:b", "v:load:c"), start_time=0.06)
```
