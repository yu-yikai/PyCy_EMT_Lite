# 电力电子模型说明

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
