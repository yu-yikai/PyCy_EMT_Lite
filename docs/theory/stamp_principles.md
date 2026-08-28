# 元件 stamp 原理说明

本文档说明 PyCy_EMT_Lite 中各类元件如何把自身数学模型写入改进节点分析法 Modified Nodal Analysis，简称 MNA，的系统矩阵和右端项。后续每新增一种元件，都必须在本文档中补充其 stamp 原理、方向约定、矩阵写入规则和代码实现位置。

## 1. stamp 的作用

MNA 暂态仿真在每个时间步都会形成线性方程：

```text
A x = z
```

其中：

- `A`：系统矩阵，也可理解为增广节点导纳矩阵。
- `x`：未知量向量，包括非参考节点电压和必要支路电流。
- `z`：右端向量，包括独立源给定值、动态元件历史源和约束方程右端项。

stamp 是“局部元件方程写入全局矩阵”的过程。每个元件只修改与自身连接节点、支路变量相关的矩阵行列，仿真器把所有元件的 stamp 叠加后得到完整网络方程。

## 2. 本项目的统一符号约定

### 2.1 节点和参考地

每个两端元件使用 `positive` 和 `negative` 表示正端和负端。本文统一记为：

```text
p：positive 节点
n：negative 节点
v = v_p - v_n
```

参考节点使用 `"0"`、`"gnd"` 或 `"ground"` 表示，不进入未知量向量。代码中参考节点索引为 `None`，stamp 时跳过对应矩阵位置，相当于该节点电压固定为 0。

### 2.2 未知量顺序

当前实现中，未知量向量按如下顺序排列：

```text
x = [所有非参考节点电压, 所有额外支路电流]
```

例如：

```text
x = [v:src, v:out, i:V1, i:L1]
```

额外支路电流由需要约束方程的元件注册，例如理想电压源和电感。

### 2.3 电流方向

所有两端元件的电流默认方向为：

```text
i：从 positive 节点流向 negative 节点
```

对节点 KCL 行而言，当前代码采用“流出节点的电流写在矩阵左端，独立注入写在右端”的等价形式。一个从 `p` 流向 `n` 的电流源 `I` 会使：

```text
z[p] -= I
z[n] += I
```

这与 `pycy_emt_lite/core/stamping.py` 中 `add_current_source()` 的实现一致。

## 2.5 PyCy_EMT_Lite 的元件装配机制

PyCy_EMT_Lite 采用单一的对象式装配机制：每个元件继承
`pycy_emt_lite.components.base.Component`，通过 `stamp()` 方法在每个时间步把自身
局部方程写入全局 MNA 矩阵和右端项，动态元件再通过 `update_state()` 更新历史状态。
仿真器 `Simulator` 在每个时间步按元件声明顺序依次调用 `stamp()`，叠加形成完整的
`A x = z` 后求解。本文第 3 章及以下各章就是该机制的完整元件说明，新增元件时必须
同步补充对应章节。

## 3. 通用 stamp 辅助函数

当前基础元件主要使用三个辅助函数：

```python
add_conductance(matrix, p, n, G)
add_current_source(rhs, p, n, I)
add_voltage_probe(solution, p, n)
```

### 3.1 两端电导

连接在 `p`、`n` 之间的电导 `G` 对应电流：

```text
i = G (v_p - v_n)
```

矩阵写入规则：

```text
A[p, p] += G
A[n, n] += G
A[p, n] -= G
A[n, p] -= G
```

如果 `p` 或 `n` 是参考节点，则跳过该节点对应项。

### 3.2 两端电流源

从 `p` 流向 `n` 的电流源 `I` 不改变矩阵 `A`，只改变右端项 `z`：

```text
z[p] -= I
z[n] += I
```

如果 `p` 或 `n` 是参考节点，则跳过该节点对应项。

### 3.3 两端电压读取

`add_voltage_probe(solution, p, n)` 返回：

```text
v_p - v_n
```

参考节点电压按 0 处理。该函数主要用于元件 `outputs()` 和动态元件 `update_state()`。

## 4. 电阻 Resistor

### 4.1 物理方程

线性电阻连接在 `p`、`n` 两节点之间：

```text
i = (v_p - v_n) / R
G = 1 / R
i = G (v_p - v_n)
```

其中电流方向为从 `p` 流向 `n`。

### 4.2 stamp 规则

电阻只向矩阵 `A` 写入电导，不改变右端项 `z`：

```text
A[p, p] += G
A[n, n] += G
A[p, n] -= G
A[n, p] -= G
```

这表示在 `p` 节点 KCL 中增加 `G(v_p - v_n)`，在 `n` 节点 KCL 中增加 `G(v_n - v_p)`。

### 4.3 代码位置

实现位置：

```text
pycy_emt_lite/components/basic.py
Resistor.stamp()

pycy_emt_lite/compilation/models.py
CompiledResistor.declare_pattern()
CompiledResistor.fill_matrix()
```

旧 `Resistor.stamp()` 继续服务 Python Builder/Simulator 兼容路径。A3 新路径在编译期声明上述
四个位置，由 `MatrixPattern` 合并并分配稳定 slot；运行时 `CompiledResistor.fill_matrix()`
只按模型局部声明索引写入 `(+G, +G, -G, -G)`，不接触 NumPy/CSC 矩阵，也不保存状态。

核心代码：

```python
add_conductance(
    matrix,
    context.node_index(self.positive),
    context.node_index(self.negative),
    1.0 / self.resistance,
)
```

输出电流在 `Resistor.outputs()` 中由两端电压重新计算：

```text
i:R = (v_p - v_n) / R
```

新路径的 `CompiledResistor.current()` 使用同一方向和公式，结果记录不得改变符号约定。

## 5. 理想电流源 CurrentSource

### 5.1 物理方程

理想电流源给定电流 `I`，方向定义为从 `p` 流向 `n`。它不需要额外未知量，也不提供电压约束。

```text
i = I(t)
```

`I(t)` 可以是常数，也可以是时间函数。

### 5.2 stamp 规则

电流源只写入右端项：

```text
z[p] -= I
z[n] += I
```

含义是：电流从 `p` 节点流出、注入 `n` 节点。

### 5.3 代码位置

实现位置：

```text
pycy_emt_lite/components/basic.py
CurrentSource.stamp()
```

核心代码：

```python
add_current_source(
    rhs,
    context.node_index(self.positive),
    context.node_index(self.negative),
    _value_at(self.current, context.time),
)
```

## 6. 理想电压源 VoltageSource

### 6.1 为什么需要支路电流变量

理想电压源直接约束两端电压：

```text
v_p - v_n = V_s(t)
```

仅使用节点电压写 KCL 时，无法直接知道理想电压源支路电流。因此 MNA 为每个理想电压源增加一个支路电流未知量 `i:V1`。

该支路电流方向定义为从 `p` 流向 `n`。

### 6.2 增广方程

电压源 stamp 包含两部分。

第一部分是节点 KCL 中支路电流的贡献：

```text
p 节点：+ i_V
n 节点：- i_V
```

第二部分是电压约束方程：

```text
v_p - v_n = V_s(t)
```

若电压源支路变量对应全局索引为 `b`，则矩阵写入为：

```text
A[p, b] += 1
A[n, b] -= 1
A[b, p] += 1
A[b, n] -= 1
z[b] += V_s(t)
```

参考节点对应项跳过。

### 6.3 电压源电流符号

`i:V1` 的正方向是从 `positive` 到 `negative`。如果一个电压源向外部电阻供电，求解得到的 `i:V1` 可能为负，表示实际电流从 `negative` 流向 `positive`，即电源向外送出功率。

### 6.4 A3 编译装配位置

独立电流源由 `pycy_emt_lite.compilation.CompiledCurrentSource` 只通过 RHS writer 写入上述符号；它没有
矩阵 slot 或支路未知量。独立电压源由 `CompiledVoltageSource.declare_pattern()` 冻结节点—支路
耦合位置，再由 `fill_matrix()` 按声明顺序写入 `+1/-1`，由 `fill_rhs()` 写入规定电压。运行引擎
不再为电压源保留第二套坐标 stamp。该迁移只改变装配所有权，不改变本节方程和电流方向。

### 6.4 代码位置

实现位置：

```text
pycy_emt_lite/components/basic.py
VoltageSource.register()
VoltageSource.stamp()
```

注册支路电流：

```python
self.branch_index = variable_manager.add_branch_current(self.name)
```

stamp 时通过：

```python
branch = context.branch_offset + self.branch_index
```

得到全局支路变量位置。

## 7. 电容 Capacitor

### 7.1 连续时间模型

电容电流方向定义为从 `p` 流向 `n`：

```text
v = v_p - v_n
i = C dv/dt
```

为了在固定时间步内用线性方程求解，需要把微分方程离散化为当前时间步的 companion model：

```text
i_k = G v_k + I_hist
```

其中 `G` 是等效并联电导，`I_hist` 是由上一时间步状态决定的历史电流源。

### 7.2 梯形积分 stamp

梯形积分公式：

```text
i_k + i_{k-1} = (2C / dt) (v_k - v_{k-1})
```

整理为：

```text
i_k = G v_k + I_hist
G = 2C / dt
I_hist = -i_{k-1} - G v_{k-1}
```

因此电容在当前时间步等效为：

```text
一个并联电导 G
一个从 p 流向 n 的历史电流源 I_hist
```

stamp 写入：

```text
add_conductance(A, p, n, G)
add_current_source(z, p, n, I_hist)
```

### 7.3 后退欧拉 stamp

后退欧拉公式：

```text
i_k = C (v_k - v_{k-1}) / dt
```

整理为：

```text
i_k = G v_k + I_hist
G = C / dt
I_hist = -G v_{k-1}
```

stamp 形式与梯形积分相同，只是 `G` 和 `I_hist` 的计算不同。

### 7.4 状态更新

求解得到当前两端电压 `v_k` 后，电容用当前 companion model 计算：

```text
i_k = G v_k + I_hist
```

并保存：

```text
previous_voltage = v_k
previous_current = i_k
last_current = i_k
```

这些状态会在下一时间步生成历史电流源。

### 7.5 代码位置

实现位置：

```text
pycy_emt_lite/components/basic.py
Capacitor.stamp()
Capacitor.update_state()
Capacitor._companion()
```

其中 `_companion()` 负责根据积分方法返回：

```text
(conductance, history_current)
```

## 8. 电感 Inductor

### 8.1 连续时间模型

电感电压方向定义为从 `p` 到 `n`：

```text
v = v_p - v_n
v = L di/dt
```

电感电流方向定义为从 `p` 流向 `n`。

当前实现把电感电流作为 MNA 额外支路电流未知量，因此每个电感会注册一个支路变量 `i:L1`。

### 8.2 离散 companion 方程

电感离散化后写成支路约束方程：

```text
v_k - R_eq i_k = V_hist
```

其中：

```text
v_k = v_p,k - v_n,k
```

该方程占用电感支路变量对应的矩阵行。

### 8.3 梯形积分 stamp

梯形积分公式：

```text
i_k - i_{k-1} = (dt / 2L) (v_k + v_{k-1})
```

整理为：

```text
v_k - R_eq i_k = V_hist
R_eq = 2L / dt
V_hist = -R_eq i_{k-1} - v_{k-1}
```

若电感支路变量全局索引为 `b`，矩阵写入为：

```text
A[p, b] += 1
A[n, b] -= 1
A[b, p] += 1
A[b, n] -= 1
A[b, b] -= R_eq
z[b] += V_hist
```

前两项来自节点 KCL 中的支路电流，后几项来自电感支路约束方程。

### 8.4 后退欧拉 stamp

后退欧拉公式：

```text
v_k = L (i_k - i_{k-1}) / dt
```

整理为：

```text
v_k - R_eq i_k = V_hist
R_eq = L / dt
V_hist = -R_eq i_{k-1}
```

矩阵写入形式与梯形积分相同，只是 `R_eq` 和 `V_hist` 的计算不同。

### 8.5 状态更新

求解后，电感保存当前支路电流和两端电压：

```text
previous_current = i_k
previous_voltage = v_k
last_voltage = v_k
```

这些量会在下一时间步生成历史电压源。

### 8.6 代码位置

实现位置：

```text
pycy_emt_lite/components/basic.py
Inductor.register()
Inductor.stamp()
Inductor.update_state()
Inductor._companion()
```

其中 `_companion()` 负责根据积分方法返回：

```text
(resistance, history_voltage)
```

## 9. 三相对称电压源 ThreePhaseSource

### 9.1 物理模型

`ThreePhaseSource` 是三相复合元件，内部等效为三只相对中性点的理想电压源。节点命名采用 `母线:相别`：

```text
p_a = terminal_bus:a
p_b = terminal_bus:b
p_c = terminal_bus:c
n = neutral
```

每相电压为：

```text
v_a = sqrt(2) V_rms sin(ωt + θ0)
v_b = sqrt(2) V_rms sin(ωt + θ0 - 2π/3)
v_c = sqrt(2) V_rms sin(ωt + θ0 + 2π/3)
```

每相支路电流方向均定义为从对应相节点流向中性点。

### 9.2 stamp 规则

每相都按理想电压源规则写入 MNA。若某相支路变量全局索引为 `b`，相节点为 `p`，中性点为 `n`：

```text
A[p, b] += 1
A[n, b] -= 1
A[b, p] += 1
A[b, n] -= 1
z[b] += v_phase(t)
```

三相电源需要为 a、b、c 三相分别注册支路电流变量。

### 9.3 状态更新

三相理想电压源没有动态历史状态。`outputs()` 返回各相支路电流：

```text
i:VS:a
i:VS:b
i:VS:c
```

### 9.4 代码位置

```text
pycy_emt_lite/components/three_phase.py
ThreePhaseSource.register()
ThreePhaseSource.stamp()
ThreePhaseSource.outputs()
```

## 10. 三相线路 ThreePhaseLine

### 10.1 物理模型

`ThreePhaseLine` 将每相线路建模为从 `from_bus:相别` 到 `to_bus:相别` 的串联 `R-L` 支路。每相电流方向为从 `from_bus` 流向 `to_bus`。

连续时间方程为：

```text
v = R i + L di/dt
```

其中 `v = v_from - v_to`。当 `L = 0` 时退化为纯电阻线路。

### 10.2 stamp 规则

纯电阻线路直接写入电导：

```text
G = 1 / R
A[p, p] += G
A[n, n] += G
A[p, n] -= G
A[n, p] -= G
```

含电感线路为每相注册一个支路电流变量。电感部分沿用电感 companion model：

```text
v_L - R_eq i = V_hist
```

线路总电压为 `v = R i + v_L`，因此写成：

```text
v - (R + R_eq) i = V_hist
```

若支路变量全局索引为 `b`：

```text
A[p, b] += 1
A[n, b] -= 1
A[b, p] += 1
A[b, n] -= 1
A[b, b] -= R + R_eq
z[b] += V_hist
```

### 10.3 状态更新

求解后保存每相支路电流和电感电压：

```text
i_k = solution[b]
v_L,k = (v_from,k - v_to,k) - R i_k
```

`outputs()` 返回：

```text
i:LINE:a, i:LINE:b, i:LINE:c
v:LINE:a, v:LINE:b, v:LINE:c
```

### 10.4 代码位置

```text
pycy_emt_lite/components/three_phase.py
ThreePhaseLine.register()
ThreePhaseLine.stamp()
ThreePhaseLine.update_state()
ThreePhaseLine.outputs()
```

## 11. 三相星形负荷 ThreePhaseLoad

### 11.1 物理模型

`ThreePhaseLoad` 将每相负荷建模为从 `bus:相别` 到 `neutral` 的串联 `R-L` 支路。每相电流方向为从相节点流向中性点。

连续时间方程同样为：

```text
v = R i + L di/dt
```

### 11.2 stamp 规则

三相负荷每相 stamp 与 `ThreePhaseLine` 的单相串联 `R-L` 支路相同，只是负端节点固定为 `neutral`。纯电阻负荷写入电导；含电感负荷注册每相支路电流，并写入：

```text
v_phase - (R + R_eq) i = V_hist
```

### 11.3 状态更新

求解后保存每相电流和电感电压。`outputs()` 返回：

```text
i:LOAD:a, i:LOAD:b, i:LOAD:c
v:LOAD:a, v:LOAD:b, v:LOAD:c
```

### 11.4 代码位置

```text
pycy_emt_lite/components/three_phase.py
ThreePhaseLoad.register()
ThreePhaseLoad.stamp()
ThreePhaseLoad.update_state()
ThreePhaseLoad.outputs()
```

### 11.5 三相并联 RLC/PQ 负荷 ThreePhaseParallelRLCLoad

`ThreePhaseParallelRLCLoad` 用于复现 Simscape Specialized Power Systems 中的三相并联 RLC 负荷块。输入参数采用线电压额定值和三相总有功、感性无功、容性无功功率，内部按对称三相星形接法换算为每相并联 R、L、C 支路。

相电压额定值和每相参数为：

```text
V_phase = V_line / sqrt(3)
G_R = (P / 3) / V_phase^2
L = V_phase^2 / (ω (Q_L / 3))
C = (Q_C / 3) / (ω V_phase^2)
```

其中 `P` 为三相总有功功率，`Q_L` 为三相总感性无功功率，`Q_C` 为三相总容性无功功率。每相电流方向定义为从 `bus:相别` 流向 `neutral`。

电阻支路直接按并联电导写入：

```text
A[p, p] += G_R
A[n, n] += G_R
A[p, n] -= G_R
A[n, p] -= G_R
```

感性无功支路为每相注册一个支路电流变量 `i_L`，采用与电感相同的 companion model。若相节点为 `p`、中性点为 `n`、支路变量为 `b`，写入：

```text
A[p, b] += 1
A[n, b] -= 1
A[b, p] += 1
A[b, n] -= 1
A[b, b] -= R_eq
z[b] += V_hist
```

容性无功支路采用电容并联等效：

```text
i_C = G_C v + I_hist
G_C = 2C / dt          # 梯形积分
I_hist = -i_{k-1} - G_C v_{k-1}
```

`G_C` 按电导写入矩阵，`I_hist` 按从相节点流向中性点的历史电流源写入右端项。后退欧拉时使用 `G_C = C / dt`、`I_hist = -G_C v_{k-1}`。

求解后，模型更新每相电感电流、电感电压、电容电压和电容电流，并记录总负荷电流：

```text
i_load = i_R + i_L + i_C
```

`outputs()` 返回：

```text
i:LOAD:a, i:LOAD:b, i:LOAD:c
v:LOAD:a, v:LOAD:b, v:LOAD:c
i:LOAD:L:a, i:LOAD:L:b, i:LOAD:L:c
i:LOAD:C:a, i:LOAD:C:b, i:LOAD:C:c
r:LOAD:phase, l:LOAD:phase, c:LOAD:phase
```

代码位置：

```text
pycy_emt_lite/components/three_phase.py
ThreePhaseParallelRLCLoad.register()
ThreePhaseParallelRLCLoad.stamp()
ThreePhaseParallelRLCLoad.update_state()
ThreePhaseParallelRLCLoad.outputs()
```

## 12. 接地故障 Fault

### 12.1 物理模型

`Fault` 是连接在故障节点和参考地之间的可投切电阻支路。故障电流方向为从故障节点流向地。

```text
i_f = (v_node - v_ground) / R_f
```

### 12.2 stamp 规则

当 `enabled = False` 时，故障支路不写入矩阵。当 `enabled = True` 时，按电阻支路写入：

```text
G_f = 1 / R_f
A[p, p] += G_f
A[n, n] += G_f
A[p, n] -= G_f
A[n, p] -= G_f
```

### 12.3 状态更新

故障投入时记录故障电流；故障清除时电流记为 0。`outputs()` 返回：

```text
i:故障名
state:故障名
```

其中 `state` 为 1 表示投入，为 0 表示清除。

### 12.4 代码位置

```text
pycy_emt_lite/components/switching.py
Fault.stamp()
Fault.update_state()
Fault.outputs()
```

## 13. 断路器 Breaker

### 13.1 物理模型

`Breaker` 是可开合的两端电阻支路。闭合时使用小电阻 `R_closed`，断开时不写入矩阵。电流方向为从 `positive` 流向 `negative`。

### 13.2 stamp 规则

闭合时：

```text
G = 1 / R_closed
A[p, p] += G
A[n, n] += G
A[p, n] -= G
A[n, p] -= G
```

断开时不写入矩阵。如果断开后造成孤立网络，仿真器会按 MNA 奇异矩阵给出拓扑诊断。

### 13.3 状态更新

闭合时记录断路器电流，断开时电流记为 0。`outputs()` 返回：

```text
i:断路器名
state:断路器名
```

### 13.4 代码位置

```text
pycy_emt_lite/components/switching.py
Breaker.stamp()
Breaker.update_state()
Breaker.outputs()
```

## 14. π 型线路 PiLine 与 ThreePhasePiLine

### 14.1 物理模型

π 型线路由串联 `R-L` 支路和两端各一半的对地电容组成：

```text
p -- R,L -- n
p -- C/2 -- ground
n -- C/2 -- ground
```

串联电流方向定义为从发送端 `p` 流向接收端 `n`。三相版本 `ThreePhasePiLine` 对 a、b、c 三相分别写入同样的单相 π 型支路，暂不考虑相间耦合。

### 14.2 stamp 规则

串联支路满足：

```text
v_p - v_n = R i + L di/dt
```

当 `L = 0` 时按普通电阻写入电导。当 `L > 0` 时注册支路电流变量，并写入：

```text
v_p - v_n - (R + R_eq) i = V_hist
```

其中 `R_eq` 和 `V_hist` 与电感 companion model 相同。

两端并联电容各取 `C/2`，按电容 companion model 写入：

```text
i_k = G v_k + I_hist
```

### 14.3 状态更新

求解后保存串联支路电流、串联支路电压和两端并联电容的历史电压/电流。输出字段包括：

```text
i:LINE:series
v:LINE:series
i:LINE:send_cap
i:LINE:recv_cap
```

三相版本在字段末尾增加相别，例如 `i:TPL:series:a`。

### 14.4 代码位置

```text
pycy_emt_lite/components/lines.py
PiLine
ThreePhasePiLine
```

## 15. Bergeron 线路 BergeronLine 与 ThreePhaseBergeronLine

### 15.1 物理模型

Bergeron 教学线路使用特性阻抗 `Zc` 和传播时延 `τ` 表示行波关系。发送端、接收端电流方向均定义为从对应端口流入线路。

```text
i_s(t) = v_s(t) / Zc + I_s_hist(t)
i_r(t) = v_r(t) / Zc + I_r_hist(t)
```

历史源由对端延时电压和电流决定：

```text
I_s_hist(t) = -v_r(t - τ) / Zc - i_r(t - τ)
I_r_hist(t) = -v_s(t - τ) / Zc - i_s(t - τ)
```

### 15.2 stamp 规则

每个端口写入一个对地电导 `1 / Zc`，并写入从端口流向地的历史电流源：

```text
A[s, s] += 1 / Zc
A[r, r] += 1 / Zc
z[s] -= I_s_hist
z[r] -= I_r_hist
```

如果使用 `attenuation`，历史源乘以该衰减系数。三相版本每相独立写入上述 stamp。

A3 单相编译路径把上述历史实现为 Session 内的定长环形缓冲，容量为
`ceil(τ / nominal_dt) + 2`。求解本步时只读 committed 样本；目标时刻落在两个样本之间时按时间
线性插值，早于首样本时使用零波，晚于末样本时保持末样本。求解成功后才把本步两端电压和电流
写入 trial 槽并统一提交，因此失败回滚不会污染延时波。

A3 单相线性双绕组变压器保持本章既有理想变比约束和一次侧漏阻抗方程。一次、二次绕组各有
一条 MNA 支路；漏感 companion 历史由 Session committed/trial 状态持有，可选铁耗作为一次侧
并联电导。b1 不创建励磁支路，避免把后续励磁/饱和状态提前混入线性切片。

b2 在线性一次侧励磁电感非空时增加独立 companion 支路，状态为上步电流、上步电压和磁链。
磁链按 `φ_k = φ_{k-1} + v_p,k Δt` 更新；求解成功前只写 trial，输出单位为 Wb。

b3 按 committed `|φ|` 与拐点比较选择线性或饱和励磁电感。选择发生在装配本步矩阵之前，两个
电感值复用同一已声明对角 slot；post-solve 的新磁链只影响下一步。

### 15.3 状态更新

求解后保存当前发送端/接收端电压和端口电流，并在后续时间步按 `t - τ` 插值读取。输出字段包括：

```text
i:BL:sending
i:BL:receiving
```

三相版本在字段末尾增加相别，例如 `i:TBL:sending:a`。

### 15.4 代码位置

```text
pycy_emt_lite/components/lines.py
BergeronLine
ThreePhaseBergeronLine
```

## 15.5 分段线路 SegmentedLine

### 15.5.1 物理模型

`SegmentedLine` 将一条单相线路拆成 `sections` 个等长 π 型集中参数小段。总参数按段数均分：

```text
R_seg = R_total / sections
L_seg = L_total / sections
C_seg = C_total / sections
```

每段由串联 `R-L` 支路和两端各 `C_seg/2` 的对地电容组成。段间节点由程序自动命名为 `LINE:internal:k`。串联电流方向为从发送端逐段流向接收端。

### 15.5.2 stamp 规则

每个小段复用 π 型线路的 stamp。串联支路满足：

```text
v_p - v_n - (R_seg + R_eq) i = V_hist
```

两端并联电容按 companion model 写入：

```text
i_C = G_C v + I_hist
```

因此分段线路本质上是在同一个元件内部循环写入多个 π 型线路局部 stamp。

A3 编译路径保持同一方程，但把每段的支路索引、内部节点和 companion 历史在编译期展开。总参数
严格除以 `sections`，每段按声明顺序写入固定 Pattern slot；跨步历史只存于 Session。发送端电流
取首段串联电流，接收端电流取末段串联电流，平均电流按全部分段电流的算术平均计算，正方向均为
发送端到接收端。

### 15.5.3 状态更新

每个小段保存独立的串联支路电流、电感历史电压和两端并联电容历史电压/电流。输出字段包括：

```text
i:LINE:sending
i:LINE:receiving
i:LINE:average
```

### 15.5.4 代码位置

```text
pycy_emt_lite/components/lines.py
SegmentedLine
```

## 16. 单相变压器 SinglePhaseTransformer

### 16.1 物理模型

单相变压器由理想变比、一次侧折算漏阻抗和一次侧并联励磁支路组成。`turns_ratio = n = Vp / Vs`。一次、二次电流方向均定义为从对应绕组正端流入变压器。

理想变比和电流关系为：

```text
v_p = n v_s
i_s + n i_p = 0
```

含漏阻抗后，电压方程写为：

```text
v_p - n v_s - Z_leak i_p = 0
```

### 16.2 stamp 规则

模型注册一次绕组电流 `i_p` 和二次绕组电流 `i_s`。若一次支路变量索引为 `bp`，二次支路变量索引为 `bs`：

```text
一次侧 KCL 写入 i_p
二次侧 KCL 写入 i_s
```

漏感通过 companion model 写入：

```text
v_p - n v_s - (R_leak + R_eq) i_p = V_hist
```

电流关系写入第二条支路方程：

```text
n i_p + i_s = 0
```

铁耗电阻按普通并联电导写入一次侧。励磁电感注册独立励磁支路电流，并按电感 companion model 并联在一次侧。

### 16.3 状态更新

求解后保存一次电流、二次电流、漏感历史电压、励磁电流和励磁磁链。输出字段包括：

```text
i:T1:primary
i:T1:secondary
i:T1:magnetizing
flux:T1:magnetizing
```

### 16.4 代码位置

```text
pycy_emt_lite/components/transformers.py
SinglePhaseTransformer
```

## 17. 三相变压器 ThreePhaseTransformer

### 17.1 物理模型

`ThreePhaseTransformer` 由三个单相绕组相组成，支持 Y/Y、Y/Δ、Δ/Y。Y 接每相连接在 `bus:相别` 与中性点之间；Δ 接使用：

```text
a 绕组：bus:a -> bus:b
b 绕组：bus:b -> bus:c
c 绕组：bus:c -> bus:a
```

`turns_ratio` 表示一次每相绕组电压与二次每相绕组电压之比。

### 17.2 stamp 规则

每个相绕组复用 `SinglePhaseTransformer` 的理想变比、漏阻抗和励磁支路 stamp。三相模型为每相分别注册一次、二次和可选励磁支路变量。

含 Δ 接法时，纯理想电压约束会形成约束环。当前教学模型要求设置非零漏电阻或漏感，使 MNA 矩阵有物理阻尼和唯一解。

### 17.3 状态更新

逐相保存一次电流、二次电流、励磁电流和励磁磁链。输出字段包括：

```text
i:T3:primary:a
i:T3:secondary:a
i:T3:magnetizing:a
flux:T3:magnetizing:a
```

### 17.4 代码位置

```text
pycy_emt_lite/components/transformers.py
ThreePhaseTransformer
```

## 18. 饱和励磁简化模型

### 18.1 物理模型

饱和励磁使用显式滞后近似：本时间步根据上一时刻磁链选择励磁电感。

```text
|ψ| < ψ_knee      Lm = L_unsat
|ψ| >= ψ_knee     Lm = L_sat
```

磁链由一次侧电压积分：

```text
ψ_k = ψ_{k-1} + v_p,k Δt
```

### 18.2 stamp 规则

饱和励磁不引入非线性迭代。本步 stamp 仍按线性电感写入，只是 companion model 使用由上一时刻磁链决定的有效励磁电感。

### 18.3 状态更新

求解后更新励磁电流、一次侧电压和磁链。该模型用于教学演示饱和趋势，不包含磁滞回线、剩磁和频率相关铁耗。

### 18.4 代码位置

```text
pycy_emt_lite/components/transformers.py
_effective_magnetizing_inductance()
SinglePhaseTransformer
ThreePhaseTransformer
```

## 19. 理想开关 IdealSwitch

### 19.1 物理模型

`IdealSwitch` 是两端可控开关，端口为 `positive` 和 `negative`，电流正方向为从 `positive` 流向 `negative`。第一版使用显式电导近似：

```text
闭合：i = (v_p - v_n) / R_on
断开：i = G_off (v_p - v_n)
```

其中 `closed` 可以是布尔值或时间函数，`R_on` 为闭合电阻，`G_off` 为关断泄漏电导。

### 19.2 stamp 规则

理想开关不注册额外支路变量，只根据当前控制状态写入两端电导：

```text
G = 1 / R_on    闭合
G = G_off       断开

A[p, p] += G
A[n, n] += G
A[p, n] -= G
A[n, p] -= G
```

如果 `G_off = 0`，断开时不写入矩阵。

### 19.3 状态更新

求解后读取 `v_p - v_n`，并按本步写入的电导计算支路电流。输出字段包括：

```text
i:开关名
state:开关名
```

`state = 1` 表示闭合，`state = 0` 表示断开。

### 19.4 代码位置

```text
pycy_emt_lite/components/power_electronics.py
IdealSwitch
```

## 20. 二极管 Diode

### 20.1 物理模型

`Diode` 的端口为 `anode` 和 `cathode`，正向电流从阳极流向阴极。第一版不进行非线性迭代，而使用上一时间步端电压决定本步状态：

```text
previous_voltage > forward_voltage  -> 导通
otherwise                           -> 关断
```

导通和关断分别使用 `on_resistance` 和 `off_conductance` 的电导近似。

### 20.2 stamp 规则

二极管不注册额外支路变量。本步根据上一时刻电压选择电导：

```text
G = 1 / R_on    导通
G = G_off       关断
```

随后按普通两端电导写入：

```text
A[p, p] += G
A[n, n] += G
A[p, n] -= G
A[n, p] -= G
```

### 20.3 状态更新

求解后保存当前端电压作为下一时间步的显式判据，并记录本步电流。输出字段包括：

```text
i:二极管名
state:二极管名
```

该模型适合教学和开关逻辑验证，不适合作为高精度器件级二极管模型。

### 20.4 代码位置

```text
pycy_emt_lite/components/power_electronics.py
Diode
```

## 21. IGBT 简化模型 IGBTSwitch

### 21.1 物理模型

`IGBTSwitch` 的端口为 `collector` 和 `emitter`，主通道电流正方向从集电极流向发射极。门极信号 `gate` 为布尔值或时间函数。门极导通时主通道按小电阻写入；关断时按泄漏电导写入。

若 `anti_parallel_diode=True`，当上一时间步端电压满足反向二极管导通条件时，也按导通电导写入：

```text
previous_voltage < -diode_forward_voltage
```

### 21.2 stamp 规则

IGBT 不注册额外支路变量。本步状态为：

```text
state = gate_on or anti_parallel_diode_on
G = 1 / R_on    state = 1
G = G_off       state = 0
```

矩阵写入仍为普通两端电导：

```text
A[p, p] += G
A[n, n] += G
A[p, n] -= G
A[n, p] -= G
```

### 21.3 状态更新

求解后保存 `v_collector - v_emitter` 和支路电流。输出字段包括：

```text
i:IGBT名
state:IGBT名
```

第一版模型不包含门极电荷、尾电流、开通关断损耗、结温或非线性输出特性。

### 21.4 代码位置

```text
pycy_emt_lite/components/power_electronics.py
IGBTSwitch
```

## 22. 同步机经典二阶模型 SynchronousMachine

### 22.1 物理模型

`SynchronousMachine` 是三相同步电机的教学简化模型，端口为 `terminal_bus:a`、`terminal_bus:b`、`terminal_bus:c` 和中性点 `neutral`。内部为三相对称内电势，内部节点记为 `SM_internal:a`、`SM_internal:b`、`SM_internal:c`。

每相定子支路电流方向定义为从内部电势节点流向机端节点，正值表示同步机向外部网络送出该相电流。每相电气方程为：

```text
e_phase - v_terminal = R_s i + L_s di/dt
```

内电势为：

```text
e_a = sqrt(2) E_rms sin(ω_sync t + δ)
e_b = sqrt(2) E_rms sin(ω_sync t + δ - 2π/3)
e_c = sqrt(2) E_rms sin(ω_sync t + δ + 2π/3)
```

机械动态采用经典摆动方程：

```text
dω_pu/dt = (P_m - P_e - D(ω_pu - 1)) / (2H)
dδ/dt = ω_sync (ω_pu - 1)
```

其中 `P_e` 由三相机端电压和送出电流的瞬时功率求和得到。

### 22.2 stamp 规则

每相内电势按理想电压源写入 MNA。若内电势节点为 `e`，中性点为 `n`，内电势源支路索引为 `b_e`：

```text
A[e, b_e] += 1
A[n, b_e] -= 1
A[b_e, e] += 1
A[b_e, n] -= 1
z[b_e] += e_phase(t)
```

当 `stator_inductance = 0` 时，定子支路按普通电阻写入内部节点 `e` 与机端节点 `p` 之间的电导：

```text
G = 1 / R_s
A[e, e] += G
A[p, p] += G
A[e, p] -= G
A[p, e] -= G
```

当 `stator_inductance > 0` 时，为每相定子支路注册支路电流变量 `b_s`，并按串联 R-L companion model 写入：

```text
e - v_terminal - (R_s + R_eq) i = V_hist
```

矩阵写入为：

```text
A[e, b_s] += 1
A[p, b_s] -= 1
A[b_s, e] += 1
A[b_s, p] -= 1
A[b_s, b_s] -= R_s + R_eq
z[b_s] += V_hist
```

其中 `R_eq` 和 `V_hist` 与电感 companion model 相同。

### 22.3 状态更新

求解后，模型读取每相机端电压、内部节点电压和定子支路电流。若含定子电感，则保存：

```text
previous_current = i_k
previous_inductor_voltage = (e_k - v_terminal,k) - R_s i_k
```

随后计算三相瞬时电磁功率：

```text
P_e = v_a i_a + v_b i_b + v_c i_c
```

并用显式欧拉更新 `speed_pu` 和 `rotor_angle`。该显式更新方式避免在第一版模型中引入非线性迭代，适合教学和 Simscape 负荷流初始化目标复现。

`outputs()` 返回：

```text
i:SM:a, i:SM:b, i:SM:c
v:SM:a, v:SM:b, v:SM:c
e:SM:a, e:SM:b, e:SM:c
p:SM, p_pu:SM, pm:SM
rotor_angle:SM, speed_pu:SM
```

### 22.4 代码位置

```text
pycy_emt_lite/machines/synchronous.py
SynchronousMachine.register()
SynchronousMachine.stamp()
SynchronousMachine.update_state()
SynchronousMachine.outputs()
```

## 23. Park dq0 同步发电机 ParkSynchronousGenerator

### 23.1 物理模型

`ParkSynchronousGenerator` 是带一阶 AVR 和一阶调速器的同步发电机教学模型。外部端口为 `terminal_bus:a`、`terminal_bus:b`、`terminal_bus:c` 和中性点 `neutral`；内部端口为 `GEN_internal:a`、`GEN_internal:b`、`GEN_internal:c`。每相定子电流方向仍定义为从内部电势节点流向机端节点，正值表示发电机向外部网络送出电流。

模型使用幅值不变 Park 变换。内部暂态电势状态为 `E'_q` 和 `E'_d`，标幺方程为：

```text
dE'_q/dt = (E_fd - E'_q - (X_d - X'_d) I_d) / T'_do
dE'_d/dt = (-E'_d + (X_q - X'_q) I_q) / T'_qo
```

AVR 采用一阶励磁近似：

```text
dE_fd/dt = (V_ref + K_A (V_ref - V_t) - E_fd) / T_A
```

调速器采用一阶下垂近似：

```text
dP_m/dt = (P_ref - (ω_pu - 1) / R - P_m) / T_g
```

机械方程为：

```text
dω_pu/dt = (P_m - P_e - D(ω_pu - 1)) / (2H)
dδ/dt = ω_sync (ω_pu - 1)
```

### 23.2 stamp 规则

`ParkSynchronousGenerator` 的 MNA 接口与经典同步机类似：先把 `E'_d`、`E'_q` 通过反 Park 变换得到三相内部电势，再把每相内部电势作为理想电压源写入矩阵。当前实现使用 `X'_d` 对应的等效定子暂态电感作为三相 abc 接口支路：

```text
R_s = R_s,pu Z_base
L_s = X'_d,pu Z_base / ω_base
Z_base = 3 V_phase,rms^2 / S_base
```

若内电势节点为 `e`、机端节点为 `p`、中性点为 `n`，内电势源支路为 `b_e`，定子支路为 `b_s`，则内电势源 stamp 为：

```text
A[e, b_e] += 1
A[n, b_e] -= 1
A[b_e, e] += 1
A[b_e, n] -= 1
z[b_e] += e_phase(t)
```

当 `X'_d = 0` 时，定子支路退化为纯电阻，按 `G = 1 / R_s` 写入 `e` 与 `p` 之间。若 `X'_d > 0`，则使用串联 R-L companion model：

```text
e - p - (R_s + R_eq) i = V_hist
```

矩阵写入规则与 `SynchronousMachine` 的含电感定子支路相同。

### 23.3 状态更新

求解后，模型读取三相机端电压和定子支路电流，变换为 dq 量，得到：

```text
V_t = sqrt(V_d^2 + V_q^2)
P_e = v_a i_a + v_b i_b + v_c i_c
```

随后按显式欧拉依次更新 AVR、调速器、`E'_q`、`E'_d`、`ω_pu` 和 `δ`。显式更新避免在第一版 Park 模型中引入非线性迭代，适合教学和控制响应验证；高保真工程模型后续可在非线性求解框架完成后进一步扩展。

`outputs()` 返回：

```text
i:GEN:a, i:GEN:b, i:GEN:c
v:GEN:a, v:GEN:b, v:GEN:c
e:GEN:a, e:GEN:b, e:GEN:c
id_pu:GEN, iq_pu:GEN, vd_pu:GEN, vq_pu:GEN, vt_pu:GEN
eq_prime_pu:GEN, ed_prime_pu:GEN, efd_pu:GEN
pm_pu:GEN, p:GEN, p_pu:GEN
rotor_angle:GEN, speed_pu:GEN
```

### 23.4 代码位置

```text
pycy_emt_lite/machines/park_generator.py
ParkSynchronousGenerator.register()
ParkSynchronousGenerator.stamp()
ParkSynchronousGenerator.update_state()
ParkSynchronousGenerator.outputs()
```

## 24. 新能源平均模型说明

阶段 4 新增的 `PVArrayModel`、`BatteryModel`、`DCLink`、`GridFollowingPowerController`、`DroopController`、`VSGController` 和 `LVRTController` 位于：

```text
pycy_emt_lite/renewables/sources.py
pycy_emt_lite/renewables/controls.py
```

这些对象不是继承 `Component` 的 MNA 元件，不直接写入 `A x = z` 的系统矩阵，也不实现 `stamp()`。它们属于直流侧能源模型和离散控制模型，用于平均变流器算例中生成功率、电压、电流或相角参考。

若后续把光伏、电池或 DC-link 扩展为真正接入 MNA 网络的电气元件，则必须为对应类补充端口方向、支路变量、矩阵写入规则、右端项符号和状态更新规则。

## 24.5 MMC 与 VSC-HVDC 平均模型说明

阶段 5 新增的 `ModularMultilevelConverterAverage` 和 `VSCHVDCLinkAverage` 位于：

```text
pycy_emt_lite/converters/average.py
```

这些对象是系统级教学平均模型，不继承 `Component`，不直接写入 MNA 矩阵。`ModularMultilevelConverterAverage` 用直流电压和调制比估算交流相电压，并给出子模块电容总能量估算；`VSCHVDCLinkAverage` 用直流电容、线路电阻和送受端功率差推进直流电压。

P5-T10 的统一 Scheduler 路径把旧 VSC-HVDC 教学算例冻结为端站恒功率边界和直流电容链路，而不是
把控制信号伪装成 MNA 电气端口。送端功率按注入为正，受端功率按吸收为正：

```text
Idc = (Psend - Preceive) / max(abs(Vdc), Vfloor)
Ploss = Idc^2 * Rdc
Vdc_next = Vdc + (Idc - Ploss / max(abs(Vdc), Vfloor)) * dt / Cdc
```

每个样点先记录 `Vdc`，再提交 `Vdc_next`，这是旧算例的显式预更新时序。两端 MMC 臂能量在该
简化边界中由额定子模块电压和电容直接计算，不包含内部均压、环流或开关动态；这些限制不得通过
调度迁移被悄然解释为完整 VSC 控制系统。

若后续将 MMC 扩展为开关级或臂级 MNA 元件，必须新增独立元件类，并补充桥臂电流方向、子模块等效电容、电压约束、环流状态和矩阵写入规则。

## 25. 新增元件时必须补充的内容

后续每新增一种元件，都必须在本文档中新增对应章节，至少包含以下内容：

1. 元件名称和代码类名。
2. 端口、节点、支路电流方向和输出量方向约定。
3. 连续时间或代数数学模型。
4. 如为动态元件，说明数值积分或离散化公式。
5. 是否需要额外支路变量，以及 `register()` 的作用。
6. 写入矩阵 `A` 的具体行列位置。
7. 写入右端项 `z` 的具体符号和物理含义。
8. `update_state()` 中保存哪些历史状态。
9. `outputs()` 返回哪些结果字段。
10. 代码实现位置和关键方法名称。

建议新增章节模板如下：

```markdown
## X. 元件名称 ClassName

### X.1 物理模型

说明端口方向、变量定义和基本方程。

### X.2 stamp 规则

说明矩阵和右端项如何写入。

### X.3 状态更新

动态元件说明历史状态，静态元件说明不需要更新。

### X.4 代码位置

列出实现文件、类名和关键方法。
```

如果新增元件没有同步补充本文档，则该元件不视为完成。
