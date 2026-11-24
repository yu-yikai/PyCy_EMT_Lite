# 39 双构网源有功分担

在 [37 号单源孤网](../../../examples/37_islanded_frequency_droop.py) 的基础上，A、B 两台三相源各经一条 R–L 馈线接到同一个公共连接点（PCC）。每相馈线为 0.1 Ω 和 3 mH。两台源的电压幅值都在 20 ms 内升到每相 120 V 有效值。PCC 原有每相 120 Ω 的接地星形负荷，300 ms 时并联接入一组相同负荷，每相等效电阻降到 60 Ω。

## 两台源怎样分担

每台源用同一组 PCC 电压乘以自己的馈线电流，再把三相乘积相加。电流以流向 PCC 为正。算出的功率经 20 ms 低通滤波，得到 $P_f$，再用 $f=60-m(P_f-P_{ref})$ 算频率。A 的功率基准为 240 W，斜率为 0.001 Hz/W。B 的基准为 120 W，斜率为 0.002 Hz/W。

两台源都读完当拍的求解结果，再用各自的频率推进下一拍相角。频率趋于一致后，两台源的频率下降量接近相同，斜率较小的 A 因此多承担约两倍的新增有功。

## 运行与读图

从项目根目录运行。默认步长 5 µs，仿真时长 600 ms。

```powershell
uv run --locked python examples/39_dual_grid_forming_power_sharing.py
```

默认依次显示三张图。下列括号注明[启用保存](../../../README.zh-CN.md#save-existing-case)后的文件名。

- **PCC power by source (W)**（`pcc_power.png`）显示两台源向 PCC 输送的有功。负荷投入首拍，馈线电流来不及增加，PCC 电压和功率先跌落。恢复后，A、B 分别多供约 239.37 W 和 119.67 W。
- **Source frequency (Hz)**（`frequency.png`）显示两台源各自的响应。最后都接近 59.761 Hz，比投负荷前低约 0.239 Hz。
- **Phase A minus B (mrad)**（`phase_difference.png`）显示相角差。投负荷后从约 3.17 mrad 增至 6.31 mrad。两站接近同频时，相角差趋于稳定。

## 试改一个参数

将 `STATION_DROOP` 中 B 站的斜率从 0.002 改为 0.001 Hz/W，保留它的 120 W 功率基准。两站斜率相同时，用各站投负荷前后的功率平台计算增量，分担比会接近 1:1。对标前恢复原值。

## PSCAD 对标

对标读取本地封存的 5 µs 和 2.5 µs 原始波形，共 360,002 个采样点。逐拍检查两台源的功率与相角更新，并在 240–290 ms 和 540–590 ms 两窗比较分担和频率。

```powershell
uv run --locked python -m validation.cases.dual_grid_forming_power_sharing.compare --run-dir local_reference/dual_source_check
```

新目录保存 `report.json`、`waveform_overlay.png` 和两档 PyCy 波形。
[验收报告](acceptance_report.json) · [冻结比较协议](candidate_protocol.json) · [PSCAD 原生实测](../../../docs/development_roadmap/experiments/e_dual_gfm_sharing_native_20261123.json)
