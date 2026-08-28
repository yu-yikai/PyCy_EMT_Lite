# 控制系统建模说明

阶段 3 第一版控制系统采用自研离散控制模块，放在 `pycy_emt_lite.controls` 包中。控制器不直接写入 MNA 矩阵，而是在采样时刻根据测量量输出参考量、调制量或等效电压指令，供电力电子模型和算例使用。

## 1. 统一接口

控制模块遵守 `ControlBlock` 协议：

```python
output = block.step(input_value, time_step)
block.reset()
```

`time_step` 必须是本次控制采样的实际间隔，不能默认等于某个全局固定值。这样后续与事件插入点、短尾步长和多速率控制扩展时保持一致。

## 2. 基础模块

- `Limiter`：对输入量限幅，无动态状态。
- `PIController`：离散 PI 控制器，积分项使用显式矩形积分；配置上下限后带冻结式抗积分饱和。
- `FirstOrderLowPass`：一阶低通滤波器，连续模型为 `dy/dt = (u - y) / tau`，离散化采用后退欧拉。
- `SampleDelay`：整采样周期延迟，用固定长度队列保存历史采样值。

## 3. 坐标变换

`pycy_emt_lite.controls.transforms` 使用幅值不变 Clarke 变换和 Park 变换：

```text
alpha = 2/3 * (a - b/2 - c/2)
beta  = sqrt(3)/3 * (b - c)

d = alpha cos(theta) + beta sin(theta)
q = -alpha sin(theta) + beta cos(theta)
```

对应反变换由 `dq_to_abc()` 提供。第一版默认三相平衡、无零序分量；后续如需零序或功率不变变换，应新增显式函数名，避免含义混淆。

## 4. SRF-PLL

`SRFPLL` 使用当前估计角度把三相电压变换到 dq 坐标，并用 q 轴电压误差修正角频率：

```text
omega = omega_nominal + PI(v_q / V_base)
theta_k = theta_{k-1} + omega * dt
```

第一版 PLL 适合教学和并网逆变器平均模型算例，不包含负序解耦、陷波器、限幅恢复逻辑或弱电网专用增强结构。

## 5. PWM

PWM 辅助函数包括：

- `triangular_carrier()`：生成 `[-1, 1]` 三角载波。
- `sine_pwm_duty()`：由调制比和电角度生成单相占空比。
- `carrier_compare()`：执行参考波和载波比较，输出 0/1 开关状态。

这些函数优先服务阶段 3 的开关模型和教学测试，后续可扩展空间矢量 PWM、三电平 PWM 和死区时间。


## 6. 与编译管线的说明

本文第 1～5 节描述 PyCy_EMT_Lite 的对象式控制模块（`pycy_emt_lite.controls`）。
控制模块在采样时刻由算例代码显式调用（例如 `examples/13_three_phase_grid_inverter_average.py`
中的 dq 电流环、`examples/11_pll_dynamic_response.py` 中的 SRF-PLL），不直接写入 MNA 矩阵。
新能源相关的跟网/构网控制器见 [renewable_grid_models.md](renewable_grid_models.md)。