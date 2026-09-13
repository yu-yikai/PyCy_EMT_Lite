# 电力电子模型说明

[English](power_electronics.en.md)

电力电子部分保留显式理想开关、基础滤波器组合和 PWM 算例，用于观察开关网络与负荷电流。

## 1. 简化开关元件

`pycy_emt_lite.components.power_electronics` 提供：

- `IdealSwitch`：由布尔值或时间函数控制导通状态，导通时写入小电阻电导，关断时写入小泄漏电导。

该模型属于显式电导近似，不代表完整器件级模型。PWM 验证包括门极时序、导通/关断电导、
电流方向和基波；不求解半导体非线性伏安关系或开关损耗。

## 2. 滤波器组合

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

## 3. PWM 教学示例

- `examples/12_two_level_pwm_generator.py`：两电平 PWM 逆变器驱动 RL 负载，使用 `IdealSwitch` 与三角载波比较生成门极信号。

示例 12 在 0.1–0.2 s（6 个 60 Hz 周期和 100 个载波周期）报告三相总 RMS、基波 RMS 及相位差。
相位以各相未保持的正弦参考为准；基波平均模型包含零阶保持的 `sinc(f Ts) exp(-jωTs/2)` 和开关导通电阻。
该参考只适用于线性调制区，不含开关纹波；总 RMS 不等于基波 RMS。

现有测试验证互补门极、浮置星点的相电压、三相电流和为零及基波 RL 阻抗。
5/2.5/1.25 μs 在共同的 0.05–0.10 s 窗口比较：相对 1.25 μs，默认 5 μs 的最大基波相量差约 0.214%，
2.5 μs 约 0.094%；电流波形 RMS 差分别小于 0.6 A、0.3 A。细网格是步长对照，不是器件物理参考。
`event_time_policy` 仅约束显式事件，不会自动定位 callable 门极边沿，因此不承诺 PWM 的二阶波形收敛、死区或器件级行为。
