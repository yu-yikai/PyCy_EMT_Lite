# 38 并联线路的故障隔离与恢复

送端 S 的三相电源经两条并联线路向受端 R 的电阻负荷供电。一条健康线路直接连接 S 和 R，另一条分为 S–F、R–F 两段，F 是故障点。三相参数相同，每相电源为 120 V 有效值、60 Hz，健康线路和故障线路的两段均为 2 Ω，负荷为 20 Ω。F 经 10 kΩ 接地，两端断开后仍有电位参考。故障投入时，F 经 0.2 Ω 接地。

## 运行与读图

从项目根目录运行。默认步长 50 µs，仿真时长 350 ms。

```powershell
uv run --locked python examples/38_parallel_line_fault_isolation.py
```

| 时刻 | 操作 | 观察 |
| --- | --- | --- |
| 100 ms | 投入三相接地故障 | 两端都向 F 送电，受端负荷功率下降。 |
| 150 ms | 断开故障线路送端 | 电源仍经健康线路到达 R，再从 R 向 F 反送约 27.15 A 每相。 |
| 200 ms | 断开故障线路受端 | 故障电流降到接近零，健康线路继续向负荷供给约 1.785 kW。 |
| 250 ms | 清除故障 | 故障线路保持双端断开，负荷功率几乎不变。 |
| 300 ms | 重合故障线路两端 | 两条线路恢复并联供电，负荷功率回到约 1.898 kW。 |

第一张图显示三相负荷功率，第二张图显示两段支路每相带方向的电流有效值，正值表示流向 F。正常供电时，电流沿 S–F–R 流动，R–F 支路读数为负。开关用固定时间表，线路只含电阻，图中变化集中在切换时刻。

## PSCAD 对标

对标读取本地封存的 50 µs 和 25 µs 两档 PSCAD 原始波形，逐点核对电压、电流和五个切换时刻，并在各状态窗检查负荷功率及反送方向。两档共比较 21,002 个采样点，保留各自的零时刻采样。

```powershell
uv run --locked python -m validation.cases.parallel_line_fault_isolation.compare --run-dir local_reference/parallel_fault_check
```

新目录保存 `report.json`、`waveform_overlay.png` 和两档 PyCy 波形。
[验收报告](acceptance_report.json) · [冻结比较协议](candidate_protocol.json) · [PSCAD 原生实测](../../../docs/development_roadmap/experiments/e_parallel_fault_surrogate_native_20261123.json)
