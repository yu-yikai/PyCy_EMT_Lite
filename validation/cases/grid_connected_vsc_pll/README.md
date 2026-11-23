# 30 并网 VSC 锁相环电流闭环

把 [11 号的同步旋转坐标系锁相环](../pll_dynamic_response/README.md)接入
[29 号的并网电流环](../grid_connected_vsc_closed_loop/README.md)。PLL 从串联电阻前、
相对交流中性点的三相电压估计相角。电流变换和调制逆变换使用同一个估计角，
交叉耦合补偿继续使用 60 Hz 对应的额定角频率乘以电感。

## 运行

从项目根目录运行。默认步长为 5 µs，仿真至 0.2 s，显示相角误差、估计频率和 dq 电流。

```powershell
uv run --locked python examples/30_grid_connected_vsc_pll.py
```

在项目根目录的 Python 会话可切换到 2.5 µs 电气步长。

```python
from runpy import run_path

from pycy_emt_lite.cases import run_case

define_case = run_path("examples/30_grid_connected_vsc_pll.py")["define_case"]
run_case(define_case(time_step=2.5e-6))
```

## 读图

- 初始估计角比电网角超前 15°。零时刻网压为零，只记录初始角和 60 Hz，PLL 从第一个正的 100 µs 采样点开始更新。此时 q 轴电压为负，估计频率短暂低于 60 Hz。
- 每 100 µs 先求解电路，再用上一拍的角频率推进相角。用同一行网压和推进后的角度更新频率，新频率用于下一个采样区间。新调制参考在下一 5 µs 门极拍生效，2.5 µs 步长的中点保持原参考和门极。
- 40 ms 和 80 ms 的 d、q 电流指令分别升至 2 A 和 1.5 A。开关纹波会出现在瞬时电流中，跟踪用一个 60 Hz 周期的电流均值判断。双 PI 和 190 V 电压限幅沿用 29 号。

**试改一个参数。** 在 `define_case()` 中把 PLL 的 `initial_angle` 从 `19 * math.pi / 12` 改为 `3 * math.pi / 2`。此时初始角与电网相角对齐，初始角差从 15° 变为 0°，估计频率在启动时的下探应减小。

## 复核 PSCAD 对标

真实 PSCAD 5.0 参考已完成双档[短窗](short_reference_report.json)和[长窗](full_reference_report.json)核验。
正式比较使用两份按整数电气拍生成电源电压的新归档，PLL 仍读取求解后的差分电压。[电源精度参考](source_precision_reference_report.json)
[冻结协议](reference_protocol.json)给出 110–160 ms 的锁相和电流跟踪判据。
比较命令从 30 号入口重新运行两档，需要 `local_reference/` 中有与报告哈希匹配的原始参考归档。

```powershell
uv run --locked python -m validation.cases.grid_connected_vsc_pll.compare
```

两档采集延至 0.200005 s，保留最后一次采样生效的门极拍。报告、对照波形及各档候选输入快照保存在独立的 `local_reference/` 目录。

30 号已通过正式验收。两档共 18 个同档窗口的电气量、门极和 PLL 状态检查均通过。首轮状态误差超限与后续单变量对照均留有证据。[验收报告](acceptance_report.json) · [首轮验证报告](validation_report.json)
