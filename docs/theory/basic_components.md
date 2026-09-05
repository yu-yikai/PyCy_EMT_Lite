# 基础元件建模说明

[English](basic_components.en.md)

本文档说明基础元件的物理模型和离散化公式。各元件如何具体写入 MNA 矩阵、右端项和支路变量，详见 `stamp_principles.md`。

## 1. 电阻

电阻满足：

```text
i = (v_p - v_n) / R
```

在 MNA 中直接写入电导：

```text
G = 1 / R
```

## 2. 电容

电容电流方向定义为从正端流向负端：

```text
i = C dv/dt
```

采用梯形积分时：

```text
i_k = G v_k + I_hist
G = 2C / dt
I_hist = -i_{k-1} - G v_{k-1}
```

采用后退欧拉法时：

```text
i_k = G v_k + I_hist
G = C / dt
I_hist = -G v_{k-1}
```

因此电容可等效为一个并联电导和一个历史电流源。

## 3. 电感

电感电压方向定义为正端到负端：

```text
v = L di/dt
```

电感在本项目中使用支路电流作为 MNA 未知量。采用梯形积分时：

```text
v_k - R_eq i_k = V_hist
R_eq = 2L / dt
V_hist = -R_eq i_{k-1} - v_{k-1}
```

采用后退欧拉法时：

```text
v_k - R_eq i_k = V_hist
R_eq = L / dt
V_hist = -R_eq i_{k-1}
```

## 4. 电压源

理想电压源增加一个支路电流未知量，并添加约束：

```text
V_positive - V_negative = V_source
```

## 5. 电流源

理想电流源方向定义为从正端流向负端。它只影响 MNA 右端向量，不增加未知量。
