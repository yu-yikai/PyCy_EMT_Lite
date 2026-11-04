# 既有02 RC的真实参考补充

教学运行仍为 `uv run python examples/02_rc_transient.py`，默认1 V、1 kΩ、1 µF、零电容电压、10 µs TR步长、5 ms终点。现有解析验证和教学脚本保持原样；本工作不计新增算例。

[官方RC示例](https://www.mathworks.com/help/simscape/ug/rc-circuit-in-simulink-and-simscape.html) `simscape/RCCircuitInSimulinkAndSimscapeExample` 已在MATLAB R2025a Update 1/Simulink/Simscape实际运行。导出器通过SimulationInput把R/C改为1000 Ω/1 µF，脉冲改为1 V、1 s周期、50%占空、0延迟；因此整个5 ms窗口内输入为常值1 V。未改变主网络拓扑；官方电容1 µΩ ESR保留，PyCy为理想电容，差异约1e-9相对电阻量级。

MATLAB：

```matlab
addpath('validation/cases/rc_charging'); export_reference(pwd)
```

Python：

```powershell
$env:MPLBACKEND = 'Agg'
uv run python -m validation.cases.rc_charging.compare
```

原模型/原生CSV/MAT/provenance/log在 `local_reference/rc_charging/`，比较数据/输入快照/图/报告独立存入 `comparison_results/<UTC运行编号>/`。无参考则失败。参考ode15s容差1e-8/1e-10、MaxStep1 µs；5013个原生标准化点，候选501点。没有时间偏移或幅度拟合。

全0–5 ms窗口的判据在适配参考运行前固定：电压基值1 V、NRMSE≤1e-4、最大误差≤1e-4 V；电流基值1 mA、NRMSE≤1e-4、最大误差≤1e-7 A。实际最大误差为1.232e-5 V和1.232e-8 A，NRMSE均2.188e-6，全部通过。完整指标和数据hash见 [validation_report.json](validation_report.json)。

内部解析关系 `v=1-exp(-t/RC)` 仍是独立正确性依据；不能把它替代本次真实Simscape波形。原生重复时刻保留原件，标准化明确取最后样本。
