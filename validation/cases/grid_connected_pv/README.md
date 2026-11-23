# 36 并网光伏的照度阶跃

沿用 [35 号的单站三相桥与电流环](../grid_connected_storage/README.md)。并网点（PCC）位于电网馈线与桥侧滤波支路之间。直流母线并联一只 10 mF 电容、一只 390 Ω 本地负荷和光伏串。

光伏串用电流源和并联电阻表示。电阻约为 1.173 kΩ，照度决定电流源的给定值，实际送入母线的电流等于源电流减去并联电阻电流。这个局部等效对应 650 节串联、25 °C、1000 或 900 W/m²，以及约 356.6–403.7 V 的端口电压。

## 预充与启动

PSCAD 在预充支路断开后保存电容电压。PyCy 从该状态起算，两档初值均约为 391.77 V，交流电感从零电流开始。交流电压在前 20 ms 升起。母线偏差由有符号 PI 换成有功电流指令，允许从电网吸收功率，也允许向电网送出功率。外环每 1 ms 更新，电流环每 100 µs 更新，调制指令在下一个 5 µs 门极拍生效。

## 运行与读图

从项目根目录运行，默认步长 5 µs，仿真时长 1.000005 s。

```powershell
uv run --locked python examples/36_grid_connected_pv.py
```

- `irradiance.png` 标出 **500 ms** 处的照度变化，由 1000 降至 900 W/m²。
- `pv_and_grid_power.png` 比较光伏送入母线的功率与并网点向电网送出的功率，取正表示送出。光伏还要供给本地负荷和电路损耗。可比较 440–490 ms 与 940–990 ms 的功率均值。
- `dc_bus_voltage.png` 显示母线在照度下降时短暂降低，随后被外环调回 390 V 附近。

## PSCAD 对标

对标程序读取本地封存的 PSCAD 两档原始波形，在相同时间点核对母线、光伏端口和电路守恒。开关功率用固定窗口的均值比较，图用 5 ms 平均显示功率趋势。两档的电流环采样、门极发布和细档中间拍保持分别按其求解结果核对。

```powershell
uv run --locked python -m validation.cases.grid_connected_pv.compare --run-dir local_reference/grid_connected_pv_check
```

在新的运行目录查阅 `report.json`、`waveform_overlay.png` 和两档 PyCy 数据。
两档对比共覆盖 600,003 个原生正时间点。PyCy 的两个照度窗口之间，平均送出功率均下降约 88 W，母线电压与 PSCAD 的最大差为 0.135 V。
[验收报告](acceptance_report.json) · [冻结比较协议](candidate_protocol.json) · [PSCAD 原生参考](../../../docs/development_roadmap/experiments/d1_pv_grid_irradiance_native_20261123.json)
