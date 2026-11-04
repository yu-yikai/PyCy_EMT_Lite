# 19：级联RC、负载耦合与真实Simscape对标

先学习02单RC，再运行 `uv run python examples/19_cascaded_rc.py`。教学脚本只运行PyCy；保存开关与其他算例相同。

src—R1—n1—R2—n2，C1/C2从对应节点接地；R1=R2=10 Ω，C1=C2=100 µF，零初值。输入在1/6/11/16 ms升/降/升/降，幅值5 V。电流沿电阻从左向右、电容向地。

两个节点的KCL是 `C1*v1'=(u-v1)/R1-(v1-v2)/R2`、`C2*v2'=(v1-v2)/R2`。同参数时后级传递函数为 `1 / ((RC*s)^2 + 3*RC*s + 1)`；若错误地把两个互不加载的RC单向串接，中间系数是2，响应会不同。这是本例相较02的新知识。

观察n2的滞后和约4.251 V峰值。源下降时R1电流立即变负，R2还短时为正，后级继续充电；两个电容电压连续。增大C2会同时影响n1和n2，增大R2会减弱耦合。参数修改后应重新定义参考与验收，原报告只覆盖默认值。

## 实际参考与复现

[官方来源](https://www.mathworks.com/help/simscape/ug/cascaded-rc-circuit-in-simulink-and-simscape.html)，示例ID `simscape/CascadedRCCircuitInSimulinkAndSimscapeExample`。实际软件为MATLAB R2025a Update 1、Simulink、Simscape。参考取**Simscape物理网络**，不取教程中用于演示负载效应错误的单向Simulink分支。

MATLAB从仓库根目录执行：

```matlab
addpath('validation/cases/cascaded_rc'); export_reference(pwd)
```

原模型、MAT、原生CSV、标准化CSV、日志与provenance留在 `local_reference/cascaded_rc/`。导出器不改变物理参数，使用ode15s、RelTol1e-8、AbsTol1e-10、MaxStep2 µs。重复原生时间保留原件，标准化取最后的右侧样本，无时移。官方每个电容有1 µΩ ESR；PyCy忽略它，远小于10 Ω电阻，差异明确保留。

Python独立对比：

```powershell
$env:MPLBACKEND = 'Agg'
uv run python -m validation.cases.cascaded_rc.compare
```

参考不存在会失败，不回退到合成数据。程序在 `local_reference/cascaded_rc/comparison_results/<UTC运行编号>/` 保存PyCy三格式、完整叠图、逐窗报告和输入快照（模型、参考CSV、参数、验收、源码）。`report.json` 记录真实版本、Git状态、原始数据/候选/模型/图片hash。每次独立保存，避免覆盖此前比较。

## 本轮结果

固定判据在候选实现前提交于 `f462cde`：四个窗口避开源跳变20 µs；电压基值5 V、NRMSE≤0.003、最大误差≤0.02 V；电流基值0.5 A、NRMSE≤0.003、最大误差≤0.002 A。窗口并集上的分段线性精确积分使用绝对时间，不拟合相位或幅度。完整图保留被保护间隔排除的边沿。

10001个PyCy点对10052个真实参考点，全部16组“窗口×信号”通过：

| 信号 | 各窗最大绝对误差的最大值 | 最大NRMSE |
|---|---:|---:|
| n1电压 | 4.851e-6 V | 1.374e-7 |
| n2电压 | 2.375e-6 V | 8.251e-8 |
| R1电流 | 4.851e-7 A | 1.374e-7 |
| R2电流 | 6.985e-7 A | 2.107e-7 |

完整可审阅指标在 [validation_report.json](validation_report.json)。这是本次配置的证据，不是任意参数/步长的误差承诺。

[自动测试](../../../tests/test_cascaded_rc.py)另以独立分段矩阵指数核对整段轨迹、KCL、事件右侧电流/电压、离散能量和TR/BE步长细化。源电压阶跃沿用现有自定义事件，未修改核心MNA或成熟元件方程。
