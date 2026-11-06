# 24：三相 Y–Δ–Y 变压器链

运行 `uv run --locked python examples/24_three_phase_transformer_chain.py`。
建议先读09的理想变比、21的浮动中性点和23的漏感/励磁支路。
本例观察三相线量与绕组量的区别、两台变压器中间的相位变化，以及浮动三角形母线的电压参考。

## 接线与参数

```text
三相内电势 ─ 每相 Rs、Ls ─ lv ─ Y/Δ 升压 ─ hv ─ Δ/Y 降压 ─ load ─ 三相星形电阻
    中性点接地              n_up 浮动       均值电压参考      n_down 浮动       中性点接地
```

内电势为相峰值13 kV、60 Hz、0/−120/+120°。源阻抗每相 Rs=16.862569 Ω、Ls=0.670940309 H，
电感初始电流均为零。默认梯形法步长0.5 µs，停止50 ms；最初约4 µs的时间常数由电感与整个电阻网络决定。
即使稳态只有60 Hz，也不能只按交流周期选择步长。源R/L由线RMS、短路容量和X/R计算；
脚本中改变源峰值也会改变这两个阻抗，不能假定其他参数仍固定。

两台变压器额定100 MVA，线额定电压13/115 kV，绕组电阻均0.01 pu，
没有漏感、励磁、铁损或饱和支路。储能来自源电感。
星形绕组每相电阻0.0169 Ω，三角形绕组每支路3.9675 Ω；用理想电流比折算后，
分别用一次侧串阻0.0338 Ω和7.935 Ω表示两台的铜阻，未丢弃铜耗。

每相负荷为169000 Ω。官方“13 kV、1 kW”用于计算固定阻抗，不能把它当成恒功率负荷。
本次内电势对应的线RMS约15.922 kV，因此实际负荷总功率约1.5 kW。

## 线量、绕组量与参考点

`ThreePhaseTransformer.turns_ratio` 是绕组电压比。升压台使用
`n=(13000/√3)/115000`，不能直接填线电压比13/115；降压台为1/n。
Δ支路顺序是 AB、BC、CA。若流入绕组侧的支路电流为 j，则同方向的母线线电流为
`[j_ab-j_ca, j_bc-j_ab, j_ca-j_bc]`；用Tup副侧端口电流时，沿链送电的线电流还需取反，不能把两组电流混比。

`i:Ls_a` 从源流向负荷。元件的变压器端口电流流入绕组正端，
所以升压台副绕组电流为 `−n*i:Ls_a`，降压台副绕组电流为 `−i:Ls_a`。
`i:Rload_a` 则是负荷吸收电流。对应b/c相同。

hv母线没有物理接地回路；同时给三个相电压加同一常数不会改变任何绕组电压。
本例局部的 `DeltaCenterReference` 选择 `mean(v:hv:a,b,c)=0`，使绝对电压具有唯一读数。
约束的总电流 `i:DeltaCenter` 应为零，参考点不耗能。
它不能为不平衡的净电流提供真实返回通道，不能代替接地模型。
两个变压器Y星点各自保留浮动节点；不能和源或负荷中性点混接。

稳态中，hv相电压相对于对应lv相电压滞后30°；第二台变压器使末端相移抵消为0°。
这里相位基准是lv端电压，内部源电势还包含源阻抗压降引起的小相移。

可每次只做一个参数练习，观察后恢复默认值：

- 将 `LOAD_RESISTANCE` 从169000 Ω改为338000 Ω：电流和总负荷功率大致减半，
  启动更快；端电压基本不变。用 `Ls/(Rs+0.0676+LOAD_RESISTANCE)` 解释时间常数变化。
- 将 `TIME_STEP` 从0.5 µs改为0.25 µs：观察最初40 µs的电流，稳态60 Hz曲线变化很小，启动误差应减小。

默认参数报告不自动验证这些修改后的实验。本例也不验证故障零序、磁饱和或其他绕组接线。
官方名称含Transmission，但原网络没有实际线路段。

## 独立解与真实参考

内部测试从物理电路独立消元：

```text
Ls*di/dt + (Rs + 0.0676 + 169000)*i = 13000*sin(2π60t+φ), i(0)=0
```

使用精确正弦加指数解，再用固定绕组关系重构端口，不调用生产MNA作为参考。
检查完整启动、KCL、铜耗与端口功率、零参考电流、源电感能量、TR细化、稳态RMS和相位。
数学解属于内部验证，不能冒充商业平台输出。

真实来源是MathWorks [Transmission System with Delta Reference](https://www.mathworks.com/help/simscape-electrical/ug/transmission-system-with-delta-reference.html)，
R2025a的 `ee_delta_transmission.slx`，SHA-256为
`02be3b7168ed504a6a585c3aa29aba3369b294d6bed2a517d6408a1931abe4ca`。
`export_reference.m` 用SimulationInput只调整运行求解/日志设置，保持原物理模型。
原件、完整MAT/CSV和图保存在忽略的 `local_reference/three_phase_transformer_chain/`。
最初449点默认探索证据仍独立保留在旧 `local_reference/three_phase_transformer/`；正式精化使用上述新目录。

[验收协议](acceptance_plan.md)、[manifest](manifest.json) 和原参数在候选前提交4edd4a1；
c88c2bb随后在候选创建前只纠正原生字段名。冻结完整启动窗[0,40 µs]及后窗[40 µs,50 ms]，
19量全部同时满足绝对误差和固定工程尺度的时间加权NRMSE，不移动时间或拟合幅值/相位。

两项补充保留了实际研究中的问题及解决依据：

- [参考求解器补充](reference_solver_addendum.md)，926138d：严格ode15s资源中止，
  极小绝对容差的daessc也曾最小步长停滞。改用可运行的daessc配置后，仍以原实测误差预算验收，
  不能用容差数字或短诊断代替完整参考。原模型和失败日志保留。
- [候选步长补充](candidate_step_addendum.md)，08a0156：首次1 µs对比的启动窗11量超过绝对限，
  后窗和全部NRMSE通过。[失败摘要](initial_step_failure.json)保留原报告hash和结果。
  原先只估计采样点误差，遗漏线性插值误差；独立闭式准确预测该峰值，随后才将默认步长细化为0.5 µs，
  不改变任何物理参数、信号、窗口或误差限。

```matlab
clear export_reference
addpath('validation/cases/three_phase_transformer_chain');
export_reference(pwd);
```

```powershell
$env:MPLBACKEND='Agg'
uv run --locked python examples/24_three_phase_transformer_chain.py
uv run --locked pytest tests/test_three_phase_transformer_chain.py
uv run --locked python -m validation.cases.three_phase_transformer_chain.compare
```

比较缺少真实数据时直接报错。每次比较保存独立UTC目录、输入快照、候选CSV/JSON/NPZ、
叠图、逐量报告及版本/hash。协议文本的冻结hash按LF核对，快照及原生MAT/波形保留原字节hash；
不为换行差异修改模型或全仓Git配置。两项补充的完整文本、提交和hash均嵌入参考provenance，随比较输入归档。

## 实测结果

2026-11-06，最终参考运行20261106T041347000Z：原网基准58899点/9.970005 s，
细化76502点/2.808688 s，38项自身比较全部通过原参考误差预算。
两次原模型SHA、路径、Dirty=off、三相零初值和实际物理参数守卫均通过。
基准/细化配置为daessc、RelTol=1e−9/1e−10、AbsTol均1e−8、MaxStep=25/12.5 µs，
并非将未完成的ode15s输出写作成功。监测峰值私有内存约2.87 GiB，用户原有MATLAB会话未被操作。

0.5 µs候选九项物理测试全部通过，专项XML记录76.926 s；新增第九项用10 ns网格检查生产结果的线性插值。
其他检查覆盖独立精确全暂态、零初值/连续性、KCL与绕组/线流、正铜耗、端口功率、
连续及TR离散能量、2/1/0.5 µs细化、稳态RMS与相位。独立Agg执行100001点/50 ms成功，
负荷总功率1499.696 W，参考总电流最大5.25e−18 A。

最终真实比较run **20261106T041603177270Z**：两窗×19量全部通过。
启动窗主要最坏误差如下，后窗最大低压/高压误差仅0.006284/0.064131 V。

| 量（全部三相最大值） | 最大绝对误差 | 原限值 |
|---|---:|---:|
| lv端电压 | 20.17655 V | 50 V |
| hv相对中心电压 | 205.91860 V | 500 V |
| load电压 | 20.17654 V | 50 V |
| 源/负荷电流 | 119.38782 µA | 300 µA |
| Tup副绕组电流 | 7.79193 µA | 20 µA |
| 总参考电流 | 6.45e−18 A（全窗） | 1e−8 A |

全局最大NRMSE为0.000246239，原普通信号限值0.002；参考总电流使用更严的独立限值。
[完整报告](validation_report.json)与本机运行归档逐字节一致，原CRLF SHA-256为
`e9f691859fa16185c4b44a8853f50113fe34b24596e2b7c81cbaf4415a270061`；
Git的LF blob SHA为`f473786f36267fbe112f336e3dcb042e4e939540e29379ec3b51baacbcafc1c6`。
完整19量叠图及额外0–40 µs放大图已实际检查；后者的脚本和hash另存于该运行的startup_artifacts.json，未改原报告。

最终本地全量 **1179 passed，490.61 s**（含slow），锁定依赖同步、Ruff全范围和mypy39文件通过。
Git交付和跨OS CI状态见[持久验证状态](../../../docs/development_roadmap/validation_status.md)。
本地数值通过不能代替尚未运行的远端CI，也不覆盖其他绕组组别、零序故障、磁饱和或真实线路组合。
