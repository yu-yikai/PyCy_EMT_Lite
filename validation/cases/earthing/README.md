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

当前阶段先冻结标准，由主任务提交后再编写候选。后续导出/比较命令及真实验收结果会在实现完成后补齐；当前不将候选登记为已完成。
