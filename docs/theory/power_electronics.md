# 电力电子模型说明

[English](power_electronics.en.md)

电力电子部分保留显式理想开关、基础滤波器组合和 PWM 算例，用于观察开关网络与负荷电流。

## 1. 简化开关元件

`pycy_emt_lite.components.power_electronics` 提供：

- `IdealSwitch`：由布尔值或时间函数控制导通状态，导通时写入小电阻电导，关断时写入小泄漏电导。

该模型属于显式电导近似，不代表完整器件级模型。PWM 验证包括门极时序、导通/关断电导、
电流方向和基波；不求解半导体非线性伏安关系或开关损耗。

## 2. 滤波器组合

`pycy_emt_lite.converters.filters` 提供 L、LC、LCL 滤波器组合类。它们不是新的 MNA 元件，而是把已有 `Resistor`、`Inductor`、`Capacitor` 组合成常见滤波结构：

- `LFilter`
- `LCFilter`
- `LCLFilter`

这种方式复用已有 stamp 和动态状态更新逻辑，降低新增模型风险。

## 3. PWM 教学示例

- `examples/12_two_level_pwm_generator.py`：两电平 PWM 逆变器驱动 RL 负载，使用 `IdealSwitch` 与三角载波比较生成门极信号。

示例 12 在 0.1–0.2 s（6 个 60 Hz 周期和 100 个载波周期）报告三相总 RMS、基波 RMS 及相位差。
相位以各相未保持的正弦参考为准；基波平均模型包含零阶保持的 `sinc(f Ts) exp(-jωTs/2)` 和开关导通电阻。
该参考只适用于线性调制区，不含开关纹波；总 RMS 不等于基波 RMS。

现有测试验证互补门极、浮置星点的相电压、三相电流和为零及基波 RL 阻抗。
5/2.5/1.25 μs 在共同的 0.05–0.10 s 窗口比较：相对 1.25 μs，默认 5 μs 的最大基波相量差约 0.214%，
2.5 μs 约 0.094%；电流波形 RMS 差分别小于 0.6 A、0.3 A。细网格是步长对照，不是器件物理参考。
`event_time_policy` 仅约束显式事件，不会自动定位 callable 门极边沿，因此不承诺 PWM 的二阶波形收敛、死区或器件级行为。
