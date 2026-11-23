# 34 双端 VSC-HVDC

把 [31 号的并网馈线](../grid_connected_vsc_power_vac/README.md)和
[32 号的直流母线调压](../grid_connected_vsc_dc_voltage/README.md)连在一起。
两站各有三相电网、馈线和两电平电压源换流器（VSC）。馈线和桥侧滤波电感之间是并网点（PCC）。
各站交流中性点独立浮置，相电压以本站中性点为参考。直流各极电压对地测量。
两座桥通过双极 T 型直流线路相连，B 站正负极之间接 400 Ω 负荷。

- A 站按并网点的有功和无功给定调节电流。两站交流电压在前 20 ms 升至 120 V 相电压有效值，频率为 60 Hz。
  A 站有功给定在 20–30 ms 升至 250 W，在 200–220 ms 再升至 650 W。
- B 站调节 400 V 直流母线并跟踪无功给定。它的有功电流指令可取正负值，以便从交流电网吸收或向电网送出功率。
- 两站各有锁相环和积分器。外环每 1 ms 更新，电流环每 100 µs 读取当前求解结果。
  并网点相电压的滤波有效值达到 24 V 后，外环才发出电流指令。
  新调制指令在下一 5 µs 门极拍生效。用 2.5 µs 步长时，中间一拍沿用原门极状态。

PyCy 的 0 s 对应 PSCAD 原生快照的 0.402 s。此时预充已断开，B 站负荷已接入，
两端母线接近 400 V，直流两极已有小电流。教学脚本通过电容初压和电感初始电流设定这一状态，可独立运行。

## 运行与读图

从项目根目录运行。默认电气步长为 5 µs，时长为 0.550005 s。

```powershell
uv run --locked python examples/34_two_terminal_vsc_hvdc.py
```

默认显示三幅图。在项目根目录的 Python 会话可用 2.5 µs 步长复跑，并将图保存到 `outputs/two_terminal_vsc_hvdc/`。

```python
from dataclasses import replace
from runpy import run_path

from pycy_emt_lite.cases import OutputOptions, run_case

define_case = run_path("examples/34_two_terminal_vsc_hvdc.py")["define_case"]
case = define_case(time_step=2.5e-6)
run_case(replace(case, output=OutputOptions(save_figure=True, show_figure=False)))
```

- **并网点有功。** 在 `pcc_active_power.png` 对比 `a_pcc_p_w` 和 `b_pcc_p_w`。
  电流以电网流向桥为正，功率为正表示该站从电网吸收。
  先看 140–190 ms，再看 500–550 ms，判断 A 站提高有功给定后 B 站的功率方向。
- **直流电压。** 在 `dc_voltage.png` 观察 `b_vdc_v`，也就是 B 站正负极电压差。
  对比 250–300 ms 的升高和 500–550 ms 向 400 V 的恢复。
- **直流线路功率。** 在 `dc_link_power.png` 对比 A 端送入线路的 `dc_sent_w` 和 B 端从线路收到的 `dc_received_w`。
  两极电流都按 A 到 B 为正。功率从 A 传向 B 时，负极电流读数为负，与负极对地电压相乘仍贡献正功率。
  `dc_series_loss_w` 是四段串联电阻的损耗，线路储能变化也会影响两端瞬时功率之差。

**试改一个参数。** 在算例脚本中把 `VDC_REFERENCE` 从 `400.0` 改为 `398.0` V。对比 500–550 ms 内的 `b_vdc_v`，观察 B 站母线电压如何趋近较低的目标。

## PSCAD 复核

两档原生参考已通过长窗复核。对标程序读取 `local_reference/` 中哈希匹配的原始归档，
按 0.402 s 快照对齐两平台时钟，再比较逐点波形、开关状态及三个 50 ms 功率窗。
两档对标共核对 330,003 个原生正时间点，12 路开关状态逐点一致。
B 站在第一个窗吸收约 190 W，在末窗向交流电网送出约 221 W，末窗母线均值约 399.6 V。
重跑生成的报告和 `waveform_overlay.png` 保存在新运行目录。
[验收报告](acceptance_report.json) · [原生参考](../../../docs/development_roadmap/experiments/d1_dual_vsc_long_native_20261123.json) · [冻结比较协议](candidate_protocol.json)

```powershell
uv run --locked python -m validation.cases.two_terminal_vsc_hvdc.compare --run-dir local_reference/two_terminal_vsc_hvdc_check
```
