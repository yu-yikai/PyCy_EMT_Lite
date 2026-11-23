# 33 五母线网状网络的负荷阶跃

从 [08 号的 π 型线路](../../../examples/08_pi_line_transient.py)出发，观察同一个负荷怎样由两条线路供电。
本例从 PGLib-PJM5 取五母线、六线路拓扑及线路参数，每相使用相同的 π 型线路。
4 号母线接 230 kV 线电压有效值、60 Hz 的理想电源，电源幅值在前 50 ms 从零升起。

```text
    2------3
   /        \
  1----------4（电源）
   \---5----/
```

基线负荷取原数据名义功率的 10%，折算成 2、3、4 号母线各自的并联电阻和电感。
到 0.300 s，2 号母线的新增电阻每相从 1 GΩ 变为 10,580 Ω。
按额定 230 kV 线电压计算，该支路的三相名义功率是 5 MW。固定电阻的功率随实际电压平方变化。

线路数据取自 IEEE PES PGLib-OPF v23.07 的 PJM5，原始数据由 F. Li 和 R. Bo 整理。
本例按 CC BY 4.0 使用该数据。 [PJM5 数据](https://github.com/power-grid-lib/pglib-opf/blob/dc6be4b2f85ca0e776952ec22cbd4c22396ea5a3/pglib_opf_case5_pjm.m) · [许可](https://github.com/power-grid-lib/pglib-opf/blob/dc6be4b2f85ca0e776952ec22cbd4c22396ea5a3/LICENSE)

## 运行与读图

在项目根目录运行。默认电气步长为 5 µs，仿真至 0.600 s。

```powershell
uv run --locked python examples/33_pjm5_load_step.py
```

在项目根目录的 Python 会话可用 2.5 µs 步长复跑。

```python
from runpy import run_path

from pycy_emt_lite.cases import run_case

define_case = run_path("examples/33_pjm5_load_step.py")["define_case"]
run_case(define_case(time_step=2.5e-6))
```

- `v_bus2_rms_v` 用同一时刻的三相对地电压计算平方平均再开根。观察 300 ms 附近的暂态，
  再用 240–290 ms 和 550–600 ms 的窗口比较稳态电压。
- `p_import_12_w` 和 `p_import_32_w` 是 1→2、3→2 两条进线送入 2 号母线的三相瞬时有功。
  线路端电流按从母线流入线路为正，包含该端并联电容的电流。计算进口有功时将该端电流取反，
  与三相相电压相乘后相加。
- 对照负荷支路的 `p_step_w`。PSCAD 原生参考中，两条进线在稳态分别多送入约 2.36 MW 和
  2.60 MW，新增支路约消耗 4.96 MW，2 号母线相电压下降约 15.38 V。

**试改一个参数。** 在算例脚本中把 `STEP_CLOSED_OHM` 从 `10580.0` 改为 `13225.0` Ω。按 230 kV 额定线电压计算，新增负荷由 5 MW 降至 4 MW。再从 `p_step_w` 图上比较实际投入的功率。

## PSCAD 复核

原生 5 µs 和 2.5 µs 参考已通过逐行物理和窗口复核。两平台都从零储能开始。直接接在
理想源上的电容在 PSCAD 零时刻记录为零电流，PyCy 按电源初始斜率计算电流。
对标保留原始差值，按预期的逐步交替符号检查电流，并核对相邻两行的平均电流。
[原生参考](../../../docs/development_roadmap/experiments/d1_pjm5_pscad_reference_20261123.json) · [冻结比较协议](candidate_protocol.json)

对标需要 `local_reference/` 中与原生参考哈希匹配的归档，并将报告和对照图写到新的输出目录。
两档共核对 360,002 行，含各自初值。PyCy 与 PSCAD 的母线相电压逐点最大差约 14.6 nV。
对照图的上排展示投入瞬态，下排比较两条进线的稳态功率增量。
[验收报告](acceptance_report.json)

```powershell
uv run --locked python -m validation.cases.pjm5_load_step.compare --run-dir local_reference/pjm5_load_step_check
```
