# 接地与浮动中性点的不平衡电阻负荷

参考为 MathWorks [Earthing Effects](https://www.mathworks.com/help/simscape-electrical/ug/earthing-effects.html)，模型 `EarthingEffects.slx`，本机已用 MATLAB R2025a Update 1 真实运行。需要 MATLAB、Simulink、Simscape 和 Simscape Electrical；原工程和数值输出保留在忽略的 `local_reference/earthing/`，不主张再分发许可。

## 研究范围与接线

只复现官方三个独立网络中的两组：源中性点均接地，负荷中性点分别接地和浮置。官方第三组负荷回线各自开路，电流为零；本例省略该组，不能将其称为浮动星形负荷。两组保留网络没有相互电气耦合。

各相理想源电压为 `100 sin(2π·60t+φ)` V，φ 为 0/−120/+120°。**100 V 是相电压峰值**，相 RMS 约 70.71 V，线 RMS 约 122.47 V。每组 A/B/C 电阻初始均为 1 Ω，50 ms 时 A 相变为 3 Ω，70 ms 时 C 相变为 1.5 Ω，B 相不变。正电流从源相节点流向对应负荷中性点。

无电感、电容及控制器状态。电阻改变后，电流和浮动星点电压可以立即跳变；本例不展示储能暂态，不据此比较积分阶次。对浮动星点：

```text
vn = (va/Ra + vb/Rb + vc/Rc) / (1/Ra + 1/Rb + 1/Rc)
i_phase = (v_phase-vn)/R_phase
ia+ib+ic = 0
```

接地组 `vn=0`，不平衡时三相电流之和可经接地回线返回，不应强制为零。浮动组的负荷相电压是相节点减浮动星点，不能拿相对地电压冒充。相电源输出功率之和等于电阻耗散；浮动组的中性点功率项为 `vn*(ia+ib+ic)=0`。

## 官方绘图标签错误与真实映射

官方 `EarthingEffectsPlotResults.m` 把 `Sensing_vi` 赋给 `Ifloating`，把 `Sensing_vi2` 赋给 `Igrounding`。这两个**电流标签互换**。SLX 的顶层连接证明：`Sensing_vi`（SID150）连接接地组源（SID74），`Sensing_vi2`（SID189）连接浮动组源（SID217）。导出程序以连接和物理 KCL 定义字段，不照抄错误图例。

实际参考在 60 ms：接地 A 电流约 −19.59284 A，等于源 A 相电压除以 3 Ω；浮动 A 电流约 −25.19080 A，中性点约 +16.79386 V，满足 `(va-vn)/3`。原脚本、真实 MAT 和原标签 CSV 留在本地作为核对证据，未修改第三方原件。

负荷电压的原映射正确：接地为 `Sensing_vi1`，浮动为 `Sensing_vi3`。`v_neutral` 由两组同相同幅的源关系重建为 `v_grounded_1-v_floating_1`；这是一条明确的电压恒等式，不是延迟或幅度拟合。

## 冻结验收

[manifest.json](manifest.json) 和 [parameters.json](parameters.json) 在候选实现前固定：13 个信号，三个连续窗口 `[0,0.0498]`、`[0.0502,0.0698]`、`[0.0702,0.1]` s，零时移。每个信号以 100 V 或 100 A 为工程基准，NRMSE ≤ 2e−4 且最大绝对误差 ≤ 0.05 V/A。各事件两侧排除 200 μs（官方本地求解两步），防止只保留右侧量的线性插值跨越跳变；全波形和实际事件时刻仍保存。

内部测试必须另核对分段解析式、星点 KCL、各相源电流、功率和事件右侧，不能仅凭图形相似或参考数据标签判断。已获得的原始参考探测数据不代替这些验收步骤。

冻结提交为 `f685ee76633b6bf78f94f8aee39bc69027516f79`。候选实现后，逐项与该提交核对，所有参数、信号、窗口、基准和阈值未变；仅参考证据状态随实际验收更新。

## 运行与真实验收

先在 MATLAB 中从仓库根目录运行本例导出器；它保留官方电路和默认本地求解器，记录实际版本和来源，修正导出列名，不修改原始第三方工程：

```matlab
addpath('validation/cases/earthing');
export_reference(pwd)
```

若同一 MATLAB 会话中运行了其他案例的同名 `export_reference`，先 `clear export_reference`，再将本例目录置于路径最前。导出后独立运行教学脚本或比较：

```powershell
uv run --locked python examples/21_earthing_neutral.py
uv run --locked python -m validation.cases.earthing.compare
uv run --locked pytest tests/test_earthing_neutral.py
```

本轮实际使用 Windows / Python 3.14.5 的 `.tmp/venv-py3145/Scripts/python.exe`，设置 `MPLBACKEND=Agg`、`PYTHONUTF8=1`。定向 pytest 使用 `--basetemp=.tmp/longterm/pytest-earthing --junitxml=.tmp/longterm/earthing-tests.xml`：**11 passed，1.50 s**；本例和测试及比较入口 Ruff 通过。独立教学脚本正常退出，1001 行、4 条电阻事件，默认未保存输出文件。Matplotlib 用户字体缓存写入权限提示未阻止 Agg 绘图。

真实参考为未修改的官方三网络模型，1001 个时间点。本例两个网络的 13 个信号、全部三个冻结窗口均通过，零时移；独立对比图已查看，单位、组别及窗口正确。各类信号在全部窗口中的最差误差：

| 对比量 | 最大绝对误差 | 最大 NRMSE |
|---|---|---|
| 六个负荷相电压 | 1.50e−11 V | 9.99e−14 |
| 六个相电流 | 1.45e−11 A | 9.83e−14 |
| 浮动中性点对地电压 | 1.45e−11 V | 9.89e−14 |

小误差来自双方对相同纯电阻代数网络的求解，不能解释为储能积分精度或真实接地装置准确度。PyCy 采样星点峰值为 28.867260 V，接地回流峰值 66.666667 A，浮动三相电流和最大绝对值 2.842e−14 A。

内部测试覆盖两积分配置、rebuild/reuse、全部时刻的独立加权星点方程、源电流正方向、各组瞬时功率、整步及非整步事件唯一右侧行，以及非法电阻事件求解前拒绝。纯电阻网络不做无意义的储能能量或步长阶次测试。

原始/标准化参考、候选 CSV/JSON/NPZ、对比 PNG、指标 JSON 和输入快照均留在 `local_reference/earthing/`。报告包含实际 Git HEAD/工作区、包源码、比较代码、原始与标准化数据及输入文件 SHA-256；最新报告路径由主任务在验证状态记录中登记。该目录默认不入 Git，仓库保存完整复现脚本和本摘要。参考与内部验证已通过，最终提交及阶段状态由主任务收口。
