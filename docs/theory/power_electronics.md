# 电力电子模型说明

[English](power_electronics.en.md)

阶段 3 第一版电力电子模型以“可验证、可解释、便于教学”为优先目标，先实现显式简化模型，再逐步扩展到非线性迭代和更高保真开关器件。

## 1. 简化开关元件

`pycy_emt_lite.components.power_electronics` 提供：

- `IdealSwitch`：由布尔值或时间函数控制导通状态，导通时写入小电阻电导，关断时写入小泄漏电导。
- `Diode`：使用上一时间步端电压决定本步导通状态，避免在第一版中引入非线性迭代。
- `IGBTSwitch`：门极控制主通道导通，可选反并联二极管近似。

这些模型都属于显式电导近似，不代表完整器件级模型。它们适合验证 PWM、桥臂拓扑、事件时序和基础 EMT 数值流程。

## 2. 滤波器组合

`pycy_emt_lite.converters.filters` 提供 L、LC、LCL 滤波器组合类。它们不是新的 MNA 元件，而是把已有 `Resistor`、`Inductor`、`Capacitor` 组合成常见滤波结构：

- `LFilter`
- `LCFilter`
- `LCLFilter`

这种方式复用已有 stamp 和动态状态更新逻辑，降低新增模型风险。

## 3. 平均逆变器模型

`ThreePhaseAverageInverter` 用两电平逆变器平均关系把调制量或 dq 电压指令转换为三相平均相电压：

```text
v_phase = 0.5 * Vdc * m_phase
```

其中 `m_phase` 限制在 `[-1, 1]`。该模型不模拟开关纹波，适合 dq 电流环、PLL 和并网控制教学算例。后续开关级逆变器应基于 `IdealSwitch`、`IGBTSwitch` 和 PWM 生成模块扩展。

## 4. 教学示例

- `examples/12_two_level_pwm_generator.py`：两电平 PWM 逆变器驱动 RL 负载，使用 `IdealSwitch` 与三角载波比较生成门极信号。
- `examples/13_three_phase_grid_inverter_average.py`：三相平均逆变器并网 dq 电流环控制。

示例 12 在 0.1–0.2 s（6 个 60 Hz 周期和 100 个载波周期）报告三相总 RMS、基波 RMS 及相位差。
相位以各相未保持的正弦参考为准；基波平均模型包含零阶保持的 `sinc(f Ts) exp(-jωTs/2)` 和开关导通电阻。
该参考只适用于线性调制区，不含开关纹波；总 RMS 不等于基波 RMS。

现有测试验证互补门极、浮置星点的相电压、三相电流和为零及基波 RL 阻抗。
5/2.5/1.25 μs 在共同的 0.05–0.10 s 窗口比较：相对 1.25 μs，默认 5 μs 的最大基波相量差约 0.214%，
2.5 μs 约 0.094%；电流波形 RMS 差分别小于 0.6 A、0.3 A。细网格是步长对照，不是器件物理参考。
`event_time_policy` 仅约束显式事件，不会自动定位 callable 门极边沿，因此不承诺 PWM 的二阶波形收敛、死区或器件级行为。
