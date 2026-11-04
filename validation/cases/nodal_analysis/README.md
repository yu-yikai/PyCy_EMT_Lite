# 20：七电阻双源网络、方向与功率

运行 `uv run python examples/20_multi_source_nodal_network.py`，建议放在01之后学习。按脚本中的网表画出七电阻网络，先求四个未知节点，再检查各支路KCL。

Vs为src对地3 V；电流源从d向c提供0.2 A。R1..7依次为200/140/330/2000/330/50/50 Ω，完整端子映射见脚本与 [parameters.json](parameters.json)。所有支路电流以声明的positive→negative为正；PyCy `Is(c,d,-0.2)` 对应d→c注入。

官方电流源的正参数方向为负端→正端，与PyCy参数约定相反，必须映射，不能照抄0.2 A。[官方定义](https://www.mathworks.com/help/simscape-electrical/ref/currentsource.html)。本例CurrentSource没有内置输出列，`on_step`明确记录已知输入 `i:Is=-0.2 A`，其实际网络作用由电阻电流和KCL检验。

| 节点 | 电压 V |
|---|---:|
| src | 3 |
| a | 22.312888053 |
| b | 1.836124177 |
| c | 422.312888053 |
| d | -8.442615240 |

c需要相对a高400 V，才能经2 kΩ向a送0.2 A。理想电流源没有合规电压限制，不代表实际电源能承受这些电压。电压源吸收0.396389464 W，电流源提供86.151100659 W，电阻耗散85.754711195 W。负节点电压与电压源吸收功率均符合物理方向，不应通过取绝对值掩盖。

这是静态代数网络，所有时间点相同，不把它称为暂态或积分精度验证。修改R4或电流源幅值后先预测压差/功率变化，恢复默认值后再复现本报告。

## 参考与复现

来源为 [MathWorks DC Circuit Analysis v2.2.2](https://github.com/MathWorks-Teaching-Resources/DC-Circuit-Analysis/tree/v2.2.2)，文件 `Models/NodalAnalysisExample.slx`。同标签BSD三条款许可已取得；本轮原件仍留local_reference。模型metadata R2024a（由R2024b导出），实际用R2025a Update 1/Simulink/Simscape/Simscape Electrical运行。

原模型有未接主电路的Virtual Multimeter，因独立测量子网络缺少Solver Configuration而编译失败。失败日志保留为 `local_reference/nodal_analysis/unmodified_failure.log`。导出器只通过SimulationInput临时禁用SID204的未接测量子系统，主电路/所有物理参数不变，原SLX不保存。缺图标依赖已按同标签补齐；未接Dashboard的日志警告不改变网络。

MATLAB从仓库根目录执行：

```matlab
addpath('validation/cases/nodal_analysis'); export_reference(pwd)
```

Python：

```powershell
$env:MPLBACKEND = 'Agg'
uv run python -m validation.cases.nodal_analysis.compare
```

101个真实参考时间点，五节点电压/七电阻与两电源电流共14信号。使用ode15s、容差1e-9/1e-11、MaxStep100 µs、0–10 ms。原始MAT/CSV、参考、provenance、日志及独立运行快照在 `local_reference/nodal_analysis/`；每次比较保存完整图、候选三格式、输入快照和报告。

验收在候选前提交于 `4c78c38`：全时间窗、零时移；电压基值100 V、NRMSE≤1e-8、最大误差≤1e-7 V；电流基值0.2 A、NRMSE≤1e-8、最大误差≤1e-9 A。全部通过，实际指标及原始/标准化/模型/脚本hash见 [validation_report.json](validation_report.json)。这是本配置的数值证据，不能扩张到非线性或高阻病态网络。

[独立有理数推导](../../../docs/development_roadmap/experiments/nodal_analysis_exact.md)通过四节点KCL消元得到精确分数；[自动测试](../../../tests/test_nodal_analysis.py)核对节点、电流源真实作用、各节点KCL与功率余额，不调用生产stamp生成参考。
