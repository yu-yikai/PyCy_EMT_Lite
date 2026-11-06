# D0：完整线性网络参考调查

日期：2026-11-06。当前是参考调查，尚无候选实现或正式验收协议；正式新增仍为6项。

## 优先原网

本机合法安装的 `power_gui.slx` 对应 MathWorks R2025a 的
[Analyze a Simple Circuit](https://www.mathworks.com/help/releases/R2025a/sps/powersys/ug/analyzing-a-simple-circuit.html)。
原网顺序为 **电源→150 km、两π段线路→单相线性变压器→固定阻抗负荷**，
另有固定补偿和等值阻抗支路。保留实际顺序及全部支路，不为任务标题移动元件或删减网络。

原件来自安装目录 `toolbox/physmod/powersys/supporting_files/documentation_models/power_gui.slx`，
SHA256为 `a46b7c34658c65ce58c6e51a6d167244c06f4e839063c00bd1ff75c78bdc5a08`。
文件内元数据为 R2025a Prerelease Update 2；本机运行软件为 R2025a Update 1。
文件保存版本和实际运行版本分开记录，不把安装目录中的旧保存版本改称新版本原件。

| 原网部分 | 复用方案与待核事项 |
| --- | --- |
| 60 Hz电源、2 Ω源电阻 | 现有 `VoltageSource`、`Resistor`；核实际幅值、相位及源电流方向 |
| 150 km、两π段线路 | 现有基础R/L/C或线路类；核展开后的实际参数、端口电流及初值 |
| 两端110 Mvar支路 | 原件为有损串联RL，不能改成纯电感 |
| 两绕组线性T | 优先外置绕组阻抗、励磁并联支路和理想变比；核励磁接点及两侧pu基准 |
| 等值阻抗与末端负荷 | 保留原有串/并联支路；负荷是固定阻抗R∥C，不是单个电阻 |

初步判断无需新核心类、依赖、网络构建器或求解框架。是否实施仍取决于下面的原生核验。

## 核验要点

1. **线路修正。** [R2025a PI Section Line](https://www.mathworks.com/help/releases/R2025a/sps/powersys/ref/pisectionline.html)
   对各段按指定频率施加双曲修正，不能直接把每公里R/L/C乘75 km当作实际支路参数。
   最终以原生展开的R/L/C/G为准，不额外加入推导中出现、原件却未实现的支路。
2. **初始化。** [Series RLC Load](https://www.mathworks.com/help/releases/R2025a/sps/powersys/ref/seriesrlcload.html)
   和 [Parallel RLC Load](https://www.mathworks.com/help/releases/R2025a/sps/powersys/ref/parallelrlcload.html)
   在未指定初值时可能计算稳态初值。保存的零字段不证明活动初值为零；必须读取真实t=0状态。
   若需要非零初值，优先使用基础电感、电容的公开初值参数，不写线路类私有状态。
3. **T等效与测量。** 按[原生线性T定义](https://www.mathworks.com/help/releases/R2025a/sps/powersys/ref/lineartransformer.html)
   核绕组和励磁位置。线路串联电流不等于含端部电容的端口总流，T绕组电流也不自动包含励磁总流。
4. **可观测性。** 原网已有Ub1、Ub2、i_eq、i_Load接Scope。本次通过SimulationInput开启时间和状态捕获后，
   输出仅含tout/xout，没有Scope波形；原件本来未开启SaveState。原生12维状态和厂商C/D矩阵已保存，可核对物理映射；
   后续如从状态重建测量，应明确标为线性投影，不称为直接Scope日志。不修改未标记信号属性来补测量。

默认配置为50 ms、ode23tb、RelTol=1e-4，AbsTol/MaxStep/InitialStep为auto；
powergui为Continuous、`x0status=blocks`。

## 本次实际运行

原网默认探针 `20261106T044524416Z` 已在MATLAB R2025a Update 1真实完成：
0–50 ms、219点、12个动态状态，sim耗时7.2005767 s；监测器终态exit0。
只通过SimulationInput捕获时间和状态，没有修改物理、默认求解器、初值或信号属性。
运行及分析后Dirty均为off，原SLX的SHA保持不变。

- 12个实际初值全部非零，且与原生分析的x0完全相同；原生x0等于厂商analysis返回xss的虚部。
  后续教学定义拟从物理相量计算这些初值，保留原网稳态初始化。
- 原生netlist在两端及中点明确包含约202 MΩ、101 MΩ、202 MΩ的线路并联电阻，
  与双曲公式复数导纳的实部相符。`SpecifyConductance=off` 不能推断实际G为零。
  现有线路类不含此G，非零初值也需显式指定，因此优先用基础R/L/C逐段表达。
- 已保存完整SimulationOutput MAT、原生状态CSV、状态名、A/B/C/D、x0、实际对话参数及netlist。
  默认结果只证明 **runnable**；尚未做参考自身精化或候选比较。

输入快照和全部原始结果归档在忽略的
`local_reference/d0_research/default_runs/20261106T044524416Z/`，第三方原件和波形不提交。

随后只读 `power_analyze('detailed')` 获得了满精度17支路表；没有再次sim。
每75 km段的R为0.8224445766062685 Ω、L为0.06495433715369778 H，
总C为1.0065300911250024 µF；两端Rshunt为201979312.5281228 Ω，中点为100989656.2640614 Ω。
独立双曲公式、pu换算及复阻抗节点递推与原生参数/相量交叉核验：
12状态相量最大相对差3.839e-13，六输出最大相对差1.097e-13。
独立计算只用原参数和拓扑，没有用厂商A/B求解或拟合波形。
T的原生导数行也与漏阻抗后、理想变比前的励磁接点相符。

四测量的原生C/D映射为Ub1=线路首端电容电压、Ub2=线路末端电容电压，
i_eq=(源电压−Ub1)/2 Ω，i_Load=Il_Z1+Il_Zs（两个诊断电流输入均为0）。
它们可由商业仿真状态和原生输入做线性投影；仍须在正式导出中保留此来源说明。

最终固定入口为 `local_reference/d0_research/evidence_inventory_final.json`，
74项文件hash由主审逐项复核通过；其SHA256为
`9297e7ef3f59aed86f9791c9e4ee7c98f15f0a09dc467481947d6e2e2a8c6e4f`。
原库存也保留：并行收尾时独立脚本格式整理及其JSON来源hash更新了两项，最终库存明确记录前后身份，
原模型、仿真MAT/CSV和原生分析字节均未改变。机器目录另固定11项关键hash。

## 其他线索与边界

- `power_transformer` 有变压器和负荷但没有线路；`power_piline` 没有变压器，均不充当完整参考。
- PSCAD原装 `simpleac.pscx` 确有线性T、100 km三相耦合Bergeron线和500 Ω负荷，
  另带故障/断路器事件。几何耦合、线路参数及事件使其超出当前最小组合候选，暂作备选，未证明与现有Bergeron相同。
- 本轮确认本机有PSCAD 5.0.0.0可执行文件和现有Python 3.13.5/Automation Library 2.9.7；
  库可发现PSCAD，却未发现Fortran版本。已有编译器文件不证明工具链兼容，许可及原生运行均未核实。
  只读环境记录 `local_reference/d0_research/pscad_environment_20261106.json`，
  SHA256 `edde15178e46dd4851f7406c19bc327fc59072a2e256516c6ac43c978e4d469f`。

下一步在候选实现前冻结全部物理参数、初值计算、方向、比较量、窗口、步长和双误差限，
再进行真实参考自身细化和候选开发。现有相量核验不替代时间域精化和商业比较，原默认运行不需重复。
