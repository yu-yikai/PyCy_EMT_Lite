# 31 并网 VSC 的有功前馈与 PCC 电压调节

在 [30 号并网桥](../grid_connected_vsc_pll/README.md)前加入每相 0.8 Ω、8 mH 的馈线。
馈线与桥侧滤波器之间是并网点（PCC）。理想源在升压完成后保持 120 V 相有效值，
流过馈线的电流会改变 PCC 电压。PLL 仍从源端取相角，有功和调压都从 PCC 取测量量。
直流侧使用 400 V 定压源。

## 运行与对照

在项目根目录运行默认调节工况，电气步长为 5 µs，仿真至 0.650005 s。

```powershell
uv run --locked python examples/31_grid_connected_vsc_power_vac.py
```

在项目根目录的 Python 会话运行固定 q 工况，与默认结果比较。

```python
from runpy import run_path

from pycy_emt_lite.cases import run_case

define_case = run_path("examples/31_grid_connected_vsc_power_vac.py")["define_case"]
run_case(define_case(scenario="held"))
```

两组的有功指令都在 120–140 ms 从 0 升到 500 W。默认工况在 240 ms 开始调压，
固定 q 工况继续保持 PCC 电压坐标中的无功电流指令为零。在 600–650 ms 比较两组电压和有功均值，
观察调压如何提高 PCC 电压，同时有功仍接近同一个目标。求有功均值时，对这段瞬时功率积分后除以 50 ms。
可在两组的 `define_case` 调用中加
`time_step=2.5e-6`，以细步长重复对照。

## 读图

- 电压图显示滤波后的 PCC 相电压有效值及 120 V 目标。PCC 电压的 d、q 分量在每个电气步低通，
  外环每 1 ms 读取一次。同拍 100 µs 电流内环使用新指令，调制在下一 5 µs 门极拍生效。
  细档中点继续保持原门极。
- 有功图画的是瞬时 PCC 功率，开关动作会带来纹波。正有功表示从电网流向桥。把有功目标除以
  1.5 倍的 PCC 相电压峰值，就得到同向的有功电流指令。2.5 A 的相电流峰值限额优先分给有功，其余用于调压。
- PCC 电压坐标中的正无功电流指令 `iq_pcc_ref` 对应向电网提供容性无功，能提高本例感性馈线的
  PCC 电压。两轴指令随后转回源端 PLL 坐标，作为电流内环的 `id_ref` 和 `iq_ref`。

## PSCAD 参考

两种工况、两档步长均已通过 PSCAD 5.0 对标。在 5 µs 的 600–650 ms 窗口，固定 q 的 PCC 基波
相有效值约为 118.80 V，调节组约为 120.02 V。比较基波采用 50 ms 窗，
刚好覆盖三个 60 Hz 电网周期和 50 个载波周期。参考报告保留了原单周波压降的检查记录。
[验收报告](acceptance_report.json) · [原生参考报告](coherent_reference_report.json) · [冻结协议](reference_protocol.json) · [评价窗说明](fundamental_window_trial.json)

复核需要 `local_reference/` 中与报告哈希匹配的原生归档。

```powershell
uv run --locked python -m validation.cases.grid_connected_vsc_power_vac.compare
```
