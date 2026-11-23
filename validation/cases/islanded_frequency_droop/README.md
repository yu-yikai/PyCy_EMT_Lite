# 37 孤网的有功–频率下垂

一台三相电压源通过 R–L 馈线向对称电阻负荷供电。三相共用接地中性点，每相串联 0.1 Ω 和 3 mH，再接到公共连接点（PCC）。每相原有 120 Ω 负荷，200 ms 时并联接入另一组 120 Ω 负荷。

## 功率怎样改变频率

源电压幅值用半余弦在 20 ms 内升到额定值，随后保持每相 120 V 有效值。每次求解后，算例用 PCC 的三相电压和馈线电流计算总有功。电流正方向从电源指向负荷，功率为正表示岛内负荷获得电能。

先用时间常数为 20 ms 的低通滤波器得到 $P_f$，再按 $f=60-0.001(P_f-360)$ 算出频率，功率用 W，频率用 Hz。功率越高，频率越低。当拍电源使用已确定的相角，算出的频率用来推进下一拍相角。初始相角和馈线电流均为零，滤波功率从 360 W 开始，所以初始频率为 60 Hz。

## 运行与读图

从项目根目录运行。默认步长 5 µs，仿真时长 400 ms。

```powershell
uv run --locked python examples/37_islanded_frequency_droop.py
```

- `pcc_power.png` 同时画出 PCC 有功和滤波功率。200 ms 投入负荷时，电感电流来不及突变，PCC 电压和功率先短暂跌落，之后平均功率由约 359 W 升到 717 W。
- `frequency.png` 显示频率随滤波功率变化，负荷接入后由约 60.001 Hz 降到 59.643 Hz。
- `pcc_voltage.png` 保留三相瞬时电压，可放大负荷接入附近读图。源相角按每拍的频率连续推进。

## PSCAD 对标

独立对标读取本地封存的 5 µs 和 2.5 µs 两档原始 PSCAD 波形。它逐点核对电路守恒、滤波和相角递推，并分别用 140–190 ms 与 340–390 ms 比较功率、频率和 PCC 电压有效值。两档共比较 240,002 个原始采样点。

```powershell
uv run --locked python -m validation.cases.islanded_frequency_droop.compare --run-dir local_reference/island_droop_check
```

新的运行目录保存 `report.json`、`waveform_overlay.png` 和两档候选数据。
[验收报告](acceptance_report.json) · [冻结比较协议](candidate_protocol.json) · [PSCAD 原生实测](../../../docs/development_roadmap/experiments/d1_gfm_island_native_20261123.json)
