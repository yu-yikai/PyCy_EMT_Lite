# 35 并网储能的充放电反转

沿用 [31 号的三相馈线和换流器](../grid_connected_vsc_power_vac/README.md)。
并网点（PCC）位于馈线与桥侧滤波支路之间，相电压以浮置的交流中性点为参考。
桥的直流侧并联 5 mF 母线电容和储能支路。储能支路含 400 V 固定开路电压源、
0.4 Ω 串联内阻，以及 0.6 Ω 电阻与 50 mF 电容并联形成的极化环节。
这个一阶 RC 模型用于观察短时间内的端口电压和电流。

PSCAD 将开路电压从零缓升至 400 V，为母线预充电，并在 0.800 s 保存状态。
PyCy 以该时刻为 0 s，直接设定两只电容的初值。母线约 399.99968 V，极化电压约 −0.302 mV，
交流电感从零电流开始。
并网后，有功给定在 20–30 ms 升到 +250 W，在 150–170 ms 降到 −250 W，无功给定保持零。
功率给定每 1 ms 更新，电流环每 100 µs 采样。调制指令在下一 5 µs 门极拍生效，
用 2.5 µs 步长时，两次门极更新之间保持原状态。

## 运行

从项目根目录运行。默认步长为 5 µs，仿真时长为 300.005 ms。

```powershell
uv run --locked python examples/35_grid_connected_storage.py
```

默认显示三张图。在项目根目录的 Python 会话可用 2.5 µs 步长复跑，并将图保存到 `outputs/grid_connected_storage/`。

```python
from dataclasses import replace
from runpy import run_path

from pycy_emt_lite.cases import OutputOptions, run_case

define_case = run_path("examples/35_grid_connected_storage.py")["define_case"]
case = define_case(time_step=2.5e-6)
run_case(replace(case, output=OutputOptions(save_figure=True, show_figure=False)))
```

## 读图

- **有功功率。** 在 `active_power.png` 对照给定 `a_p_ref_w`、并网点有功 `pcc_p_w` 和储能端有功
  `storage_p_w`。并网点功率为正表示从电网吸收功率。储能电流以从母线流入储能为正，
  所以储能功率为正表示充电，为负表示放电。比较 90–140 ms 和 250–300 ms 两个窗口的均值。
- **母线电压。** 在 `dc_bus_voltage.png` 观察 `a_vdc_v`，充电时略高于 400 V，放电时略低于 400 V。
- **极化电压。** 在 `polarization_voltage.png` 观察 `v:C1` 的符号变化。反转期间，
  电流改变会立即改变串联内阻的压降，极化电压则需要一段时间过渡。母线电压等于开路电压、内阻压降和极化电压之和。

练习时在 `_power_reference` 中把乘以 `reversal` 的功率从 500 W 改为 375 W。初始给定仍为 +250 W，反转后变为 −125 W。用 `active_power.png` 比较后段的放电功率，预期送出功率的幅值减小。正式对标使用默认给定。

## PSCAD 复核

已验收的两档 PSCAD 原生参考中，储能端在 90–140 ms 平均吸收约 245 W，
在 250–300 ms 平均送出约 250 W。母线均值由约 400.59 V 降到约 399.40 V。
对标程序读取 `local_reference/` 中与原生报告哈希匹配的归档，在同一步长下比较原始波形、
六路开关状态和两个功率窗口。报告 `report.json` 和对照图 `waveform_overlay.png` 保存在指定的新目录中。
两档共对比 180,003 个原生时间点，六路开关状态逐点一致。
对照图用 1 ms 均值显示并网点有功，教学图保留开关纹波。
[验收报告](acceptance_report.json) · [原生参考](../../../docs/development_roadmap/experiments/d1_storage_grid_long_native_20261123.json) · [冻结比较协议](candidate_protocol.json)

```powershell
uv run --locked python -m validation.cases.grid_connected_storage.compare --run-dir local_reference/grid_connected_storage_check
```
