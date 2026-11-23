# 经证据修订的长期路线图

本路线图随真实参考和验收证据修订。优先正确性、可运行参考和教学价值；当前保持小规模稠密MNA，不引入通用非线性或稀疏求解框架。

## 筛选方法

统一使用 [02参考目录](02_reference_catalog.md) 的0–5分、加权100分方法，详细向量仅保存在 `reference_catalog.json`，不维护第二套评分。维度覆盖教学/代表性/模型和数据可用性/适配/实现和验证难度/知识增量/复用/维护。**正式新增交付必须实际取得真实数据并通过对比**，总分不能替代门槛。

当前正式新增 19–39 共 21 项已完成，既有02补参考另计。A4以23线性T等效、24平衡双T接线链收尾；24没有实际线路，D0的25另交付完整电源、两π线路、变压器与固定负荷原网。B2已交付26（9269350），A3已交付27（ae9fe362）。B1已完成完整PSCAD双向开关参考、同输入电气细化、原12固定比较和独审/独立运行，当时1267全量及教学通过，已以40bef297正式验收提交推送。原MathWorks IGBT参考的2%波形FAIL单列保留。C1 完成既有 11 号 PLL 对标和 28–32 号单站控制教学链。D1 已验收 33 号五母线负荷阶跃、34 号双端 VSC-HVDC、35 号并网储能充放电、36 号光伏并网照度阶跃、37 号单站孤网下垂、38 号双端故障隔离和 39 号双构网源有功分担。其余 Bergeron 变体另行取得物理一致的参考。

## 当前实施顺序与验收门槛

1. **R1 能力与基线**：读当前有效源码/测试/历史，跑全量和算例，记录真实能力矩阵；不重复全项目第三轮审查。
2. **R2 参考目录**：保存合法获取工程、来源/版本/哈希/依赖/许可，区分 discovered/downloaded/inspected/runnable/reference_ready。没有数据的工程只用于研究。
3. **R3 路线与探针**：级联RC独立方程/收敛实验；预先固定正式验收。完成路线图后提交推送并继续开发。
4. **V1 独立验证链路**：固定窗/映射/基值、禁止外推/任意时移、时间加权误差、机器报告与图；加入Windows/Linux分支CI。
5. **A1/A2/A5 基础组**：新增级联RC、补02既有RC参考，再用已实际运行的官方七电阻双源网络展示节点分析、源方向与功率。每例需内部物理检验、独立运行、实际Simscape数据、图/报告、自动测试、教学文档及提交。已有例补对标不增加新增数量。
6. **A3/A4/A6/A7 线路/三相**：不平衡中性点A6、有限50T梯级A7、单相T等效A4a和平衡双T链A4b已验收。A3有限R的两半线+三R方案已获1/0.5µs真实6ms参考和16项自细化PASS，协议44d1436先于候选；27四量两窗八项商业比较、独审和1244全量PASS，A3已完成ae9fe362，见[实际尝试](experiments/native_reference_attempts_20261109.md)；其他接线、零序与磁性非线性不由这些结果认证，不为数量复制接线或参数。
7. **B 电力电子**：B1已补既有12的PSCAD双向开关对标，原MathWorks失败仍单列；B2完成仅指交付26同步Buck，其余半/全桥、Boost和滤波候选未验证，不由26认证。外部受控双向开关与自动二极管严格分开。
8. **C 单站控制**覆盖既有 11 号 PLL 和 28–32 号教学链。由并网开环逐步加入 dq 电流环、PLL、有功前馈、PCC 调压和直流母线调压。32 号在两档 PSCAD 对标中核对了电容初值、负荷投入、支路储能和闭环恢复。 [32 号验收](../../validation/cases/grid_connected_vsc_dc_voltage/acceptance_report.json)
9. **D/E 接口与小网**含 D0 的电源、线路、变压器与固定负荷组合，以及 D1 已验收的平衡 PJM5 五母线负荷扰动、双端 VSC-HVDC、一阶 RC 并网储能和局部等效光伏。单站孤网 P–f 下垂已完成。阶段 E 核对了原厂并联线路故障的实际开断时序。38 号三母线算例已验证受端反送、双端隔离和重合恢复。39 号验证两台构网源的逆斜率分担与共同频率变化。 [33 号验收](../../validation/cases/pjm5_load_step/acceptance_report.json) · [34 号验收](../../validation/cases/two_terminal_vsc_hvdc/acceptance_report.json) · [35 号验收](../../validation/cases/grid_connected_storage/acceptance_report.json) · [36 号验收](../../validation/cases/grid_connected_pv/acceptance_report.json) · [37 号验收](../../validation/cases/islanded_frequency_droop/acceptance_report.json) · [38 号验收报告](../../validation/cases/parallel_line_fault_isolation/acceptance_report.json) · [39 号验收报告](../../validation/cases/dual_grid_forming_power_sharing/acceptance_report.json)
10. **F 工程与教学**：在实际例中调整导航/参数/异常提示，保持既有API；每组结束复审测试、模型边界、参考及提交推送。

## G1 远期研究计划

每项先固定最小物理问题、独立判据和一个真实参考，再决定是否进入实现。当前小规模稠密 MNA 和教学入口继续服务已验收算例。 [现有能力与证据](01_capability_assessment.md)

| 方向 | 首个试验与进入条件 |
|---|---|
| 分段线性自动换流 | 用单二极管 R/L 支路验证导通和关断判据，再验证半桥的换流瞬间。用明确的电压、电流方向、零点附近行为与能量守恒核对真实器件参考。 |
| 通用非线性 MNA | 先选一条有解析导数的非线性支路，核对残差、雅可比、迭代收敛及失败报告。利用小步长和真实参考识别误差来自器件方程、迭代还是离散。 |
| 复杂电机与变压器 | 先分开研究电机机械功率平衡与变压器磁化曲线。用可核的磁链数据、空载和暂态波形验证。磁滞另检查往返轨迹和单周期损耗。 [圆转子同步机](https://www.mathworks.com/help/simscape-electrical/ref/synchronousmachineroundrotor.html) · [非线性变压器](https://www.mathworks.com/help/simscape-electrical/ref/nonlineartransformer.html) |
| 完整 EMT 初始化 | 从现有瞬时 RLC 一致性扩到单电源周期稳态，再接闭环控制及拓扑事件。检查首步状态连续性、周期残差和不一致条件拒绝，用已知稳态与原生冷启动分别复核。 |
| 39/118 节点网络 | 先完成小网物理及初始化对标，随后固定可溯源的节点、支路和潮流数据。另取得动态元件、控制、扰动和原生波形，按实际物理范围命名。 [39 节点数据](https://matpower.org/docs/ref/matpower6.0/case39.html) · [118 节点数据](https://matpower.org/docs/ref/matpower4.0/case118.html) |
| MMC 与高保真新能源场站 | 单站和简化双端验收后，用一个可独立对标的物理子系统起步。MMC 先核桥臂能量和子模块电压。新能源场站先核单机直流侧能量、限幅和并网扰动，再组合多机。 |

**稀疏求解与矩阵结构复用单列为独立研究。** 用同一 `A,b` 和变量编号，对照已验证的稠密 LU 与 CSC 稀疏 LU。试验从解析可核的 RLC 和已有真实对标的小例开始，再扩到逐级增大的固定拓扑、参数变化及开关网络。分别记录装配、格式转换、排序与分解、每次求解耗时、填充量和峰值内存。相同稀疏结构可用于研究排序和符号分析复用。数值分解复用仍须确认矩阵系数相同。先按原物理门限核对波形、初值、事件和奇异矩阵报告，再用同硬件、单线程、多次测量确定适用规模。成果为独立对照报告和接口取舍，届时决定是否改核心。 [SciPy 稀疏 LU 接口](https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.linalg.splu.html)

恢复入口是 [next_actions.md](next_actions.md)，状态以 [tasks.json](tasks.json) 和实际Git历史为准。外部阻塞仅影响依赖它的任务；尚未完成真实对标的例不能记入正式完成数。

2026-11-06状态：到25的本地最终1190 passed478.96s（含slow），核心源码及依赖相对原main未改。到22的双系统CI已通过；23/24/25的精确CI因GitHub账户账单锁在runner启动前失败，F1局部受阻，不能借旧CI扩大结论。12仍按146a279固定标准保留波形FAIL；24原1µs startupFAIL也保留，0.5µs在原限值下重验通过。

D0已交付25完整 `power_gui` 线性网络：源→两π段线路→T→固定阻抗负荷，保留所有补偿/修正G和非零初值；真实双run精化、28项商业比较及1190全量回归通过，无核心或依赖改动。见[教学与验证指南](../../validation/cases/source_line_transformer/README.md)及[前置调查](experiments/source_line_transformer_reference_probe.md)。

2026-11-09交付次序：B2先行25/12.5ns完整10ms参考自细化已通过两连续窗及全部500周期；原100/50ns FAIL和首次资源保护中止保留。50ns候选首次商业报告PASS，独立原始数据复核与完整1236 passed478.786s含slow通过，已交付9269350，当时正式新增8；随后27通过双独审及1244全量，以ae9fe362交付，现正式新增9。暂停中断的全量仍不记通过，目标已恢复；当前资源不足已非阻塞。
A3的CRC守卫已按实际编辑/保存阶段分别严格核完整定义；v6保存后拒绝保留，v7及0.5µs副本真实build/run成功。派生SrvcCbl参考限定R100Ω/Z201Ω/τ300µs、零可观测前史与完整6ms，不推广到原宿主或其他四定义。27商业比较、双独审和1244全量通过，已独立交付ae9fe362，正式新增9。B1重连后1ms真实201×46短探针通过图/输入/门极与TR诊断，完整0.2s及保持5µs控制的电气细化协议仍未冻结。完整证据/失败与恢复入口见[本轮索引](experiments/native_reference_attempts_20261109.md)，状态及后续正式提交以tasks与Git为准。

27验收提交ae9fe362已正常推送并核真实远端相同；精确[CI42616684547](https://github.com/yu-yikai/PyCy_EMT_Lite/actions/runs/42616684547)终态failure，Ubuntu129158174490/Windows129158174768均runner0/steps空，注释确认billing lock、未执行测试/test_count=null。F1外部依赖保持，不重查终态；本地1244/商业PASS不替代跨OS结果。证据[ci_ae9fe36.json](experiments/ci_ae9fe36.json)；此前9269350的独立CI证据仍保留。
