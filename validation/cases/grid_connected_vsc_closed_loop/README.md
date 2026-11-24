# 29 并网 VSC 已知角度 dq 电流环

在 [28 号六开关桥](../grid_connected_vsc_open_loop/README.md)上增加两个 PI 电流调节器。三相电流按电网给定的电角度换算成两个分量，d 轴沿电网电压矢量，q 轴与它垂直。

电网频率为 60 Hz，相电压有效值在前 20 ms 升至 120 V。每相串联 1 Ω 电阻和 10 mH 电感，初始电流为零。直流侧由 400 V 理想电源固定两条浮置直流轨之间的电压。

电网电压取电阻前端相对交流中性点的值，交流电流以电网流向桥为正。`i:Vdc` 以流入直流源正端为正，表示直流源吸收电流。在本例的功率方向约定下，正 `i_d` 对应电网向桥输入有功，正 `i_q` 对应负无功。 [控制方程与方向](../../../docs/specs/algorithms/known-angle-dq-current/known-angle-dq-current-system-architecture.md)

## 运行

从项目根目录运行主工况，默认步长 5 µs，终止时间 0.2 s。图中显示 d、q 电流及其指令，还有三相电感电流。

```powershell
uv run --locked python examples/29_grid_connected_vsc_closed_loop.py
```

| 工况 | 40 ms 的 d 轴指令 | 80 ms 的 q 轴指令 |
|---|---:|---:|
| `main` | 0 → 2 A | 0 → 1.5 A |
| `d_only` | 0 → 2 A | 保持 0 A |

例如，在项目根目录的 Python 会话可用下面的代码切换到 2.5 µs 和 `d_only`。

```python
from runpy import run_path

from pycy_emt_lite.cases import run_case

define_case = run_path("examples/29_grid_connected_vsc_closed_loop.py")["define_case"]
run_case(define_case(scenario="d_only", time_step=2.5e-6))
```

## 观察采样和限幅

- 初始调制参考和两轴积分为零，上管全关、下管全开。每到正的 100 µs 整数倍，先求解电路，再用该时刻的电压和电流计算新的调制参考。
- 待用参考在下一 5 µs 门极拍与三角载波比较。以主工况 80 ms 的 q 指令为例，80.0025 ms 的细档中点继续用旧参考、门极和电阻。80.005 ms 才施加新参考，门极依据该拍的比较结果决定。
- 两个 PI 先各算一个试积分。加入电网电压前馈和交叉耦合项后，若桥侧 dq 电压矢量的模超过 190 V，按原方向缩至 190 V，并把两个积分都恢复到采样前的值。下一采样重新计算是否限幅。

查看 40 和 80 ms 前后的电流。开关纹波在瞬时波形上很明显，用一个 60 Hz 周期的均值来判断跟踪。主工况的 q 轴平均电流向 1.5 A 靠近，`d_only` 可帮助观察 d 阶跃时的 q 轴响应。

## 复核 PSCAD 对标

[冻结协议](reference_protocol.json)给出电路、时序、比较窗和门限。[参考资格报告](qualified_reference_report.json)记录 PSCAD 5.0 的四次原生仿真。正式算例对标的 32 个同档窗口全部通过，最大周期平均跟踪误差为 0.0627 A，原门限为 0.4 A。[验收报告](validation_report.json)

运行教学脚本只需仓库中的 Python 环境。复核对标需要 `local_reference/` 中与报告哈希匹配的本地归档，含 PSCAD 原始输出、运行回执和独立核验产物。

```powershell
uv run --locked python -m validation.cases.grid_connected_vsc_closed_loop.compare
```

比较器为两个工况各运行两档步长，采集延长至 0.200005 s，分别保留 40,002 点和 80,003 点。同档按原时刻核对电气量、门极、电阻和限幅状态，并按冻结窗口检查粗细档差异及两个工况的共同前段与 q 轴增量。运行结束会打印报告位置，输入快照、结果和图位于同一个独立的 `local_reference/` 运行目录。
