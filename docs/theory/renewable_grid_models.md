# 新能源并网、构网与跟网简化模型

本文说明阶段 4 新增的新能源并网模型。第一版定位为教学型平均模型，重点解释光伏、储能、DC-link、跟网控制、构网控制、VSG 和 LVRT 的变量关系与程序实现，不模拟开关纹波和厂商级保护细节。

## 1. 光伏阵列

`PVArrayModel` 位于 `pycy_emt_lite/renewables/sources.py`。模型使用静态 I-V 近似：

```text
I = Isc * (G / Gref) * max(0, 1 - (V / Voc)^k)
P = V * I
```

其中 `G` 为辐照度，`k` 为曲线形状系数。最大功率点功率使用 `mpp_voltage * mpp_current` 并按辐照度比例缩放。该模型适合跟网逆变器平均模型的直流侧功率输入。

## 2. 储能电池

`BatteryModel` 使用 Thevenin 简化模型。电流正方向定义为放电，即电池向 DC-link 送出功率：

```text
Vt = Voc(SOC) - I * R_internal
SOC_k = SOC_{k-1} - I * dt / (capacity_Ah * 3600)
```

SOC 会被限制在 `min_soc` 和 `max_soc` 之间。该模型用于储能构网孤岛算例，展示负荷功率变化对 SOC 和直流母线的影响。

## 3. DC-link

`DCLink` 使用电容能量平衡更新直流电压：

```text
0.5 * C * Vdc_k^2 = 0.5 * C * Vdc_{k-1}^2 + (P_source - P_load) * dt
```

其中 `P_source` 为注入直流母线的功率，`P_load` 为交流侧或负荷从直流母线取走的功率。

## 4. 跟网型变流器控制

`GridFollowingPowerController` 包含功率外环和 dq 电流内环。功率外环根据：

```text
P = 1.5 * (vd * id + vq * iq)
Q = 1.5 * (vq * id - vd * iq)
```

求解 `id_ref` 和 `iq_ref`，并使用电流限幅保护。电流内环使用 PI 控制器，并加入 L 滤波器交叉耦合前馈：

```text
vd_cmd = vd_grid - omega * L * iq + R * id + PI(id_ref - id)
vq_cmd = vq_grid + omega * L * id + R * iq + PI(iq_ref - iq)
```

## 5. 构网型控制和 VSG

`DroopController` 实现 P-f/Q-V 下垂：

```text
omega = omega0 + Kp * (Pref - P)
V = V0 + Kq * (Qref - Q)
```

`VSGController` 使用虚拟同步机摆动方程的显式离散形式：

```text
d omega_pu / dt = ((Pref - P) / Sbase - D * (omega_pu - 1)) / (2H)
d theta / dt = omega0 * omega_pu
```

第一版 VSG 适合说明构网变流器的惯量和阻尼趋势，不包含励磁系统、虚拟阻抗和限流切换。

## 6. LVRT 简化逻辑

`LVRTController` 用窗口电压 RMS 的标幺值判断是否进入低电压穿越状态。进入 LVRT 后：

- 有功参考按电压标幺值缩减，保留电流容量。
- 无功参考按电压跌落深度增加，用于电压支撑。
- 电压恢复到清除阈值后退出 LVRT。

该逻辑是教学简化模型，后续若要贴近具体并网规范，应扩展电流优先级、持续时间曲线和保护动作。

## 7. 示例

阶段 4 新增示例（控制级仿真，位于 `examples/`）：

- `examples/14_pv_grid_following.py`：光伏跟网系统，辐照度阶跃下观察直流电压与有功输出。
- `examples/15_storage_grid_forming.py`：储能构网孤岛运行，负荷阶跃下观察频率与直流电压。
- `examples/13_three_phase_grid_inverter_average.py`：三相平均逆变器并网 dq 电流环。

以上算例在 `examples/` 中按学习路径编号，可直接运行查看波形。
