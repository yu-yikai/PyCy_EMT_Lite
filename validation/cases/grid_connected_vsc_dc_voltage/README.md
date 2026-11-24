# 32 并网 VSC 直流母线调压

沿用 [30 号的三相桥、PLL 和电流环](../grid_connected_vsc_pll/README.md)。直流侧用
初压 400 V 的 5 mF 电容，三相电感从零电流开始。母线常接一路 320 Ω 负荷，
仿真到 0.400 s 时再并联一路 320 Ω 负荷，所需功率约从 500 W 增至 1,000 W。

## 运行

从项目根目录运行。默认电气步长为 5 µs。末尾多算一个门极拍，记录 0.800 s 的新调制生效。

```powershell
uv run --locked python examples/32_grid_connected_vsc_dc_voltage.py
```

在项目根目录的 Python 会话可用 2.5 µs 步长复跑。

```python
from runpy import run_path

from pycy_emt_lite.cases import run_case

define_case = run_path("examples/32_grid_connected_vsc_dc_voltage.py")["define_case"]
run_case(define_case(time_step=2.5e-6))
```

## 读图

- **母线电压。** `v:Cdc` 是直流正、负极的电压差。负荷投入时电容先补足功率缺口，
  储能 \(CV_{dc}^2/2\) 减少，因此电压先降后回升。
- **d 轴电流。** 电压外环每 1 ms 根据 400 V 目标和实测电压更新 `id_ref`，取值为 0–5 A。
  正 d 轴电流从电网向桥输送有功，q 轴目标为零。较快的内环每 100 µs 跟踪电流，
  同拍使用新的外环指令。调制在下一 5 µs 门极拍生效，细档中点保持原门极。
- **负荷功率。** 对照 `p_dc_load_w` 的阶跃、电压最低点和电流回升。用 340–390 ms 与
  690–740 ms 的均值比较负荷和母线电压，两段各覆盖三个 60 Hz 周期。

**试改一个参数。** 在算例脚本中把 `CAPACITANCE` 从 `0.005` 改为 `0.006` F。对比 400 ms 负荷投入后 `v:Cdc` 的最初下降段。同样的电流缺口下，电容越大，母线电压下降越慢。

## PSCAD 复核

PSCAD 5.0 从已核对的 400 V 快照开始独立续算，两档的原生窗口均通过。负荷投入后
母线最低约 395.22 V，690–740 ms 的均值约 400.04 V。
在 PyCy 中使用同一电容初压，预充支路在仿真段保持 1 GΩ。
[原生参考与判据](../../../docs/development_roadmap/experiments/c1_dc_live_feedback_long_20261123.json)

对标程序读取 `local_reference/` 中与报告哈希匹配的原生归档，并从 32 号入口重新运行
两档 PyCy。两档共核对 480,005 行，包含各自初值。六路门极逐行相同，母线差分电压
最大差约 4.51 nV。对照图聚焦负荷投入前后，按实际电网相角计算 d 轴电流，
再取 1 ms 载波周期均值。
[验收报告](acceptance_report.json)

```powershell
uv run --locked python -m validation.cases.grid_connected_vsc_dc_voltage.compare
```
