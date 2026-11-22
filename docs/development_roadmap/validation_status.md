# 验证状态

2026-11-22。PLL 两档原生长窗通过原 19 项电气判据，各 2,000 次采样和门极应用，细档保持 40,001 个中点。验收窗最大相角误差 0.6298°、频率误差 0.01949 Hz、周期平均跟踪误差 0.06665 A。原生跨步长最大周期均值差 0.04845 A、最大分窗 RMS 差 0.07194 A。
[PLL 双步长原生长窗](../../validation/cases/grid_connected_vsc_pll/full_reference_report.json)

2026-11-22。PLL 粗档 40,002 点通过原 19 项电气判据、2,000 次反馈和随后的门极施加。稳态验收窗相角误差峰值 0.630°、频率误差峰值 0.01949 Hz，最大周期平均电流误差 0.06497 A。三周期功率方向通过。
[PLL 长窗记录](../../validation/cases/grid_connected_vsc_pll/full_reference_report.json)

2026-11-22。PLL 细档 243 点通过原 19 项电气、六次反馈和门极顺序及 121 个实际中点保持。两档短窗范围为 0–605 µs，长窗锁定与电流跟踪待验。
[PLL 双步长短窗结果](../../validation/cases/grid_connected_vsc_pll/short_reference_report.json)

2026-11-22。PLL 粗档真实运行 122 点，19 项电气判据全部通过，共模残差峰值含末位精度上界约为 0.223 nV。六次采样和下一门极拍均通过，首个样本因初始超前产生负的频率修正，第二个样本切换到实测电压归一化。
[PLL 短窗记录](../../validation/cases/grid_connected_vsc_pll/short_reference_report.json)

2026-11-22。并网 PLL 协议的 29 号电路与 11 号离散定义哈希、短窗行数和末次生效时刻已核。耦合 PLL 的原生短窗待运行。
[接入参考协议](../../validation/cases/grid_connected_vsc_pll/reference_protocol.json)

2026-11-22。公开 29 号入口四次运行共 240,010 点，原电气及控制检查均通过。32 个同档窗口通过 736 项连续量和 416 项离散量核对，最大周期平均跟踪误差为 0.06269 A。两平台跨档及两工况成组比较通过。Windows 1581 项含 slow 回归通过，WSL2 Ubuntu 完成 29 号默认独立运行及 28、29 号的 27 项专项测试。共用接线后的 28 号两档原波形和比较结果与正式验收时逐字节一致。
[29 号验收报告](../../validation/cases/grid_connected_vsc_closed_loop/validation_report.json)

2026-11-22。四份 PSCAD 长窗全点电气、时钟、控制与跟踪判据均通过。PyCy 原型同档比较在 32 个窗口内通过 736 项连续量及 416 项离散量检查。跨档最大周期 dq 均值差 0.04355 A，最大分窗 dq RMS 差 0.08142 A。两档共同前段均通过，去除 q 阶跃后确认该阶跃的 q 轴均值贡献为 1.530–1.567 A。正式教学入口尚待独立运行及验收。
[完整参考报告](../../validation/cases/grid_connected_vsc_closed_loop/qualified_reference_report.json)

2026-11-22。5 µs 主工况 40,002 点全部通过原电气、控制和跟踪判据。两档各九窗 PSCAD 对 PyCy 共通过 414 项连续量检查及 234 项门极、电阻和饱和状态检查。主工况跨档最大周期均值差 0.04355 A，最大分窗 dq RMS 差 0.08142 A，分别低于 0.10 A 和 0.20 A。
[主工况两档结果](experiments/c1_pscad_main_both_steps_20261122.json)

2026-11-22。PSCAD 细档主工况完成一次原生构建和一次长窗运行。全部 2,000 次控制更新、2,000 次门极施加和 40,001 个细步长半步保持通过。配置角复算得到电网 q 轴电压最大误差 0.05954 pV，原限值为 1 pV。原 19 项电气判据和同档 PyCy 对标通过，范围为细档主工况。
[数值报告索引](experiments/c1_pscad_angle_arithmetic_trial_20261122.json)

2026-11-22。直流负端作求解零点的 2.5 µs PSCAD 主工况完整输出 80,003 点，原 19 项电气判据全部通过。共模约束残差上界为 0.027515 µV，上限为 2 µV。三周期跟踪误差最大 0.0627 A，功率方向通过。独立高精度配置角复算确认 2,000 个采样中有 67 个 (e_q) 值超过原 1 pV 上限，峰值 1.588 pV。整体资格仍未通过。
[实测和复算](experiments/c1_pscad_reference_point_trial_20261122.json)

2026-11-19。PSCAD 两档主工况均实际运行并正常闭场。5 µs 和 2.5 µs 的共模约束残差峰值分别为 11.463 µV 和 22.469 µV，均超过原 2 µV 上限。三周期跟踪误差最大分别为 0.0574 A 和 0.0627 A，功率方向通过。原复算拒绝和全点诊断均已留档，完整参考待验。用户已暂停。
[长窗记录](experiments/c1_known_angle_dq_pscad_full_20261119.json)

2026-11-19。PSCAD 5.0 的两次 2.5 µs／600 µs 运行均满足 241 行反馈时序、120 个半拍保持和限幅恢复。默认设置有两点共模约束残差超限，峰值 2.088734 µV。稀疏求解门限设为 1 后，原物理判据全过，共模上界 0.558654 µV，限值仍为 2 µV。与使用自身反馈的 Python 同档比较时，23 项数值指标、12 路门极和电阻及饱和状态均通过。Python 长窗已做两工况双步长内部物理检查。
[细档和长窗记录](experiments/c1_known_angle_dq_pscad_feedback_fine_20261119.json)

2026-11-18。固定参考经 `on_step` 连接28号网络，两档121/241点均与固定门极独立驱动逐行一致，初流、电阻关系、KCL、KVL及梯形关系通过。Simulink两版共三次实际启动均未进入函数，无原生控制波形。已验收的开环结果见28号报告。
[设计检查](experiments/c1_known_angle_dq_design_checks_20261118.json) · [启动记录](experiments/c1_known_angle_dq_native_startup_20261118.json)

2026-11-18。PSCAD 5.0完成一次600µs实际闭环运行。121点的原电气门全部通过，共模含精度上界1.446065µV，低于2µV。Python使用自身反馈，121点的门极、电阻、限幅标志逐点一致，23项同档比较通过。范围为5µs短探针。
[短闭环记录](experiments/c1_known_angle_dq_pscad_feedback_20261118.json) · [接入构建记录](experiments/c1_known_angle_dq_pscad_control_20261118.json)

2026-11-18。Windows及WSL2 Ubuntu 24.04.4均完成锁定同步、Ruff、mypy和1573项含slow回归。Ubuntu原1568通过、5失败及新248项专项和完整复验均留档。24号恢复原38项原生对标，28号40002/80003点的输出与已验收结果逐位相同，两路原门全过。
[跨系统验证记录](experiments/f1_ubuntu_a777c00_20261118.json)

2026-11-18。两系统的24个教学入口逐个退出0，sdist/wheel构建及库外安装通过。Ubuntu初次依赖超时和库外索引故障留档，按原锁定依赖恢复后通过。WSL回收了首个成功CLI临时目录，保留原运行及发行包记录。
[CLI与发行包记录](experiments/f1_cli_wheel_cbdc9b1_20261118.json)

2026-11-18当前。正式28号双档全部40002/80003点与真实Simscape对标通过。5µs、2.5µs各通过19项物理门和150组同档比较，跨档132组通过。两路结论一致，原2µV共模阈值保持，实测上界0.310070/0.011836µV。锁定同步、Ruff、mypy、1573项完整回归及默认独立运行通过。发布范围为开环电路。
[28号验收报告](../../validation/cases/grid_connected_vsc_open_loop/validation_report.json)

2026-11-18当前：Decimal80求解精度干预完成完整粗档40002点，实际raw/RHS/Simulator求解次数均40002，初值1次，9份Decimal因子，最大尺度残差2.418e-77。两套原物理核均全19门通过，共模含完整q上界0.3100773µV小于2µV。时间和6门极位与原粗档逐位一致，临时方法已恢复，548输入及8结果文件绑定通过闭场核验。正式候选待精简实现后的双档及全量验收，新增完成9。既有1566项含slow回归保持原源码范围。

2026-11-18当前：全点驱动分解通过原定算术精度门，两份独立复核完成。全部40002点、40001区间、8类矩阵和CSV/NPZ共1480074个binary64值完成核对。KCL分解误差最大4.5931e-74A，TR为1.3815e-75V，累积项为1.3417e-68V。该研究使用既有轨迹，新增求解/轨迹/native均0。候选粗档共模门仍待通过，新增完成9，1566项回归保持原测试范围。见[机器记录](experiments/c1_observed_forcing_ledger_20261118.json)。

2026-11-18：用户已恢复长期任务。已核本地与远端HEAD均为7a10fc9，120个Python文件及2个依赖与既有1566项测试快照一致。当前继续实现全点误差驱动分析器，随后用既有轨迹进行离线分析。新增完成9，C1进行中。以下暂停记录保留为历史。

2026-11-17：已按用户要求暂停。HEAD为7a10fc9；本轮仅恢复核对与账本方案/公式静审，分析器和新纯检查尚未落盘，未启动全点账本、求解或仿真。子任务已停止。暂停记录已保存在忽略目录，五状态仅本地更新、未提交；等待用户明确恢复后再继续。新增完成9，28号候选未验收。

2026-11-16当前：固定h最终120源码与2依赖的锁定同步、全范围Ruff/mypy（39文件）及1566项含slow回归通过（0失败/错误/跳过），默认独立Agg运行40001点通过。真实Simscape参考资格保持。新候选两档40002/80003点的双路独立检查均确认：粗档共模2487点超限，峰值2.533674891µV>原2µV；细档物理门、150/150同h与132跨h门通过，粗档条件预测仅作诊断。63596数值exit1非资源中止，17585测试exit0，均已终态；输入/快照/输出哈希重核一致。候选未验收，新增完成9，C1/跨OS未完成。见[机器报告](../../validation/cases/grid_connected_vsc_open_loop/validation_report.json)。下一项驱动账本仅有未执行计划。

## 已记录里程碑

2026-11-16：完整开环VSC的真实Simscape参考已通过资格验收：[资格报告](../../validation/cases/grid_connected_vsc_open_loop/qualified_reference_report.json)。两档40002/80003点、全部57量原时间位、原19门及辅助门、四窗/六周期和132跨h门通过；最终独审另核6960290次Time/Clock位及69个原始行，未将有限点审查冒称完整数学重跑。

完整MAT重载后29个logsout数值摘要与tout前后一致；不宣称完整simlog树的任意对象元数据逐项相等。细档额外6个R_command日志仍40002点，正式导出57量均保持80003点。科学计数法文件大小仅由冻结窄规则精确核整数，原读取器FAIL保留。见[完整证据与边界](experiments/c1_nojvm_full_reference_20261116.json)。

短MAT-only恢复通过81点原门；原运行FAIL不改称PASS。28号候选未实施、新增完成9、C1进行中。113源码/依赖不变，既有1518含slow未重跑；F1两OS测试仍受已有CI账单锁阻塞。

## 先前检查点

2026-11-16：完整规模内部合成分析正常闭场，40002/80003点、原19门及辅助门、四窗/六周期与132项跨h结果通过。受控会话250.12s（worker247.47s），实际计算PID的采样峰值约110.61MiB；生成的时间编码不是商业原生时间观测。见[分析与守卫证据](experiments/c1_offline_full_n_and_nojvm_guard_20261116.json)。

真实R2025a无JVM守卫探针exit0，9项.NET哈希/固定路径检查通过，全程model0/sim0，自有进程已退出且未强制清理。尚未证明Simulink/Simscape、simlog、MAT保存重载或完整参考，也未证明完整模型内存收益；先前CIM预检超时启动0保持，具体失败查询未记录。

113源码及依赖本轮不变，既有[1518项全量](experiments/vsc_input_validation_20261116.json)保持，未重跑。新增完成9、C1进行中；原短探针PASS、PSCAD FAIL及Simscape完整Run资源中止保留。F1的[CI43856421332](experiments/ci_57fbc81.json)因账单锁未执行测试，本轮无新CI观察。

## 历史记录

2026-11-16：完整两h模型各compile1/sim0、结构独审通过；完整Run仅尝试5µs一档，因可用提交内存低于2GiB资源中止。原模型复制完整，无report/MAT/CSV；是否进入sim及调用数均未观测。见[完整模型与资源中止记录](experiments/c1_simscape_full_resource_stop_20261116.json)。

自有进程清空、清理无错误，已有MATLAB未被干预；前后113/八输入及本机库和exe身份核准。全量波形/原19门/辅助门/四窗及六周期比较均未执行，细档未启动，不授完整参考或候选资格。新增9、C1进行中；1300为旧全量，F1仍为已有账单锁，无新CI。


2026-11-16：真实R2025a库发现exit0、11模块唯一、仅两个只读library、无新用户图。ROOT与独立复核确认113源码快照、15项安装源及输入前后绑定；两包累计启动一次（首次预检超时启动0），63.918s闭场，自有进程清空、无强制清理。该结论仅为接口发现，不授予新模型、逐段TR或数值参考资格。见[接口证据](experiments/c1_simscape_library_discovery_20261116.json)。

三项license test均为1，实际inuse仅MATLAB/Simulink；Simscape新模型许可签出尚未验证。精确c3fdf79的新CI43825501731因账单锁终态失败，两OS未获得runner、steps空，不能算测试失败或通过。可读性小改的本地检查已通过，1300全量仍为此前结果；新增完成9、C1进行中、原2µV FAIL保持。


2026-11-16：可读性小改通过锁定同步（27包）、全范围Ruff、mypy（39文件）和27号独立Agg运行（6001点）。修改前后默认stdout逐字相同，除摘要f-string外AST一致。正式Python文件仍113个，27号摘要变更、其余112个及依赖不变；1300项全量仍为此前结果，本轮未重跑。

C1的原完整参考未通过2µV阈值，仍9个新增完成、C1进行中；以下原生记录保持原执行HEAD和证据，不借用当前源码快照。

2026-11-16当前：真实PSCAD编译一次、0错误；19支路、45个计划输出及原完整物理与控制检查通过。有向电路图等价，但节点编号未变化，未满足预设的试验激活条件，最终状态为NODE_ORDERING_NOT_ACTIVATED_NO_RUN。会话8170的exit1来自仿真前准入拒绝；没有调用Run，也没有OUT/INF数值数据。PSCAD正常关闭，自有进程清空；81项非波形文件、33项原绑定、6项控制绑定及完整封包引用均经双路核验。见[节点排序实建记录](experiments/c1_node_ordering_build_attempt_20261116.json)。

原完整双步长参考未通过2µV阈值的结果保留；仍为9个新增完成、C1进行中，没有新的合格参考或教学候选。113个正式Python文件及依赖未改，既有1300项测试（含slow）本轮未重跑。新Simscape路线仅完成静态调查；当前许可、新模型、编译、仿真与全部验收要求均待验证。

2026-11-16当前：原完整开环参考仍未合格。新增历史定向分析session34509已exit0，全40002/80003点及尾点、前后完整metadata/5part hash/shape重绑通过。ROOT以Fraction另核52个保存词元帧的点代数；这些是诊断证据，不授参考资格。见[共模约束复核与单变量协议](experiments/c1_commonmode_constraint_followup_20261116.json)。

已观测初值的无驱动模式、瞬时打印量化不足以单独解释，隐藏内部根因未证。新排序协议仅准备，尚无新native/候选；原FAIL保留，完成仍9。113源码及依赖不变，既有1300含slow本轮未重跑。

2026-11-16当前：完整开环参考双h数值未合格。两次PSCAD均编译0错误、Run一次、正常quit且自有进程清空；45通道完整40002/80003点及尾点双路复核一致。共模硬门峰值10.838/37.498µV超过2µV；其余逐点门和全部跨h比较通过，条件rail因前提失败仅作诊断。见[完整双步长诊断记录](experiments/c1_full_openloop_dual_h_diagnostic_20261116.json)。

原v1元数据准入FAIL与v3报告工具失败均保留；新政策仅精确重构唯一RunTime注释，模型和数值门不变。无教学候选或新增完成数；113源码/依赖未改，1300既有全量本轮未重跑。

2026-11-16当前：完整模型编译0错误，整体Build-only准入FAIL，Run0。独立核45真实通道/19支路和79项非OUT归档；两处PGB分类修正仅取得collector重演证据，新版常量/缓存语法已获范围独审，正式Run准入尚未封定。以上不能作为完整商业数值资格。113源码/依赖未变，既有1300含slow本轮未重跑，新增完成9保持。

见[本轮完整构建记录](experiments/c1_full_openloop_build_attempt_20261116.json)。以下保留各阶段历史。

2026-11-16：完整开环前验协议已固定，见[完整开环协议记录](experiments/c1_full_openloop_protocol_20261116.json)。独立40项协议审查、新kernel48项纯检查、10项定向独审与128个Schur转移对照分别通过；这些范围重叠，不相加为项目测试数量。未执行新完整原生Build/Run或候选，实际新100µs控制链与双h数值资格NOT_OBSERVED。原400µs短探针PASS/新增9/既有1300回归保持；F1无新观察。

2026-11-16：完整开环目前只有研究草案。311项codec及静态接线检查通过；独立内部控制检查覆盖40002/80003点的施加门极，不能当作45通道商业输出。误差预算建议尚未冻结，新100µs原生采样/完整双步长参考/候选均未资格。见[完整开环准备记录](experiments/c1_full_openloop_preparation_20261116.json)。原短探针PASS、新增9项和既有1300项回归保持各自范围，F1无新观察。

2026-11-16：目标active。C1的400µs人工向量短探针已真实运行并通过双路数值检查：原生编译0错误、Run一次、正常quit，唯一会话63693已闭场，自有进程清空；实际映射551项及118项绑定复核全过。32通道全81点/80区间、原17预算和Vs/完整末位精度门均通过。只取得短探针数值资格，完整SPWM开环VSC、闭环和新候选尚未验收；新增完成数仍9，C1仍in_progress，D1/F1范围保持。113源码与依赖未变，1300含slow为既有回归，本轮未重测。研究工具、原始波形与图留忽略目录，教学继续复用现有元件和CaseDefinition链，保持精简可读。

见[本轮短探针记录](experiments/c1_force_dsout_bounded_numeric_20261116.json)。检查点为本记录前的63e5165；本轮实际提交/远端在结束检查点另核。已保存暂停/恢复历史和全部失败，以下旧状态不覆盖本段。

2026-11-12：已按用户要求暂停。当前保存到短时数值验证准备阶段：新合同和24文件运行包已固定，分析器与最终独审尚未完成；本轮未启动原生仿真、读取OUT或运行候选。最新已推送提交为63e5165；须待用户明确恢复后再继续。以下为最近已验证结果与后续计划。

2026-11-12。C1仍in_progress；新增19–27共9项本地/商业验收保持，跨OS单列F1。
本轮标准force_dsout直流测量链结构合格：原生build0、worker0正常退出，生成读取→传递→ownPGB均在MainOut；独立517深门及108绑定重核全过。
完整Map32/DATAStruct34、全11参数/端口/实例、4I和15Vm新鲜度、19分支/源物理及存储守卫均通过；STOF45→46，其他36维度不变。
ROOT另核23包件/70归档及3份完整源语义。会话81982已闭场，自有进程清空、环境不变。
本轮无Run/OUT、数值NOT_OBSERVED；短探针数值及完整开环尚未合格。下一步另冻执行合同及两路数值分析器。
113源码/依赖未改，复用既有1300含slow和锁定/Ruff/mypy39，本轮未重测。
C1其余控制链及D1待办，F1外部CI恢复待补。见[本轮构建记录](experiments/c1_force_dsout_build_only_20261112.json)。

| 对象 | 内部证据 | 外部参考 | 正式状态 |
|---|---|---|---|
| 既有11 PLL（C1子步骤） | 原111源不变，33专项/1300全量、独立默认Agg一致 | 完整真实参考/三窗九项/243快照与独立复算通过 | 既有11补验证完成；C1全链仍进行中 |
| 基线a03a450 | 1118测试含slow、14原有例通过 | 旧文档不等于本次商业对标 | 能力重评完成 |
| 级联RC探针 | 独立expm、KCL、TR/BE收敛通过 | 不冒称商业参考 | 研究探针完成 |
| 新增19级联RC | 分段矩阵指数、KCL/能量、TR/BE细化；独立执行通过 | 官方R2025a，真实10052样本；16个窗×信号均通过 | 已完成290a8ea |
| 既有02 RC | 原解析测试保留 | 官方参数适配、真实5013样本，电压/电流双限值均通过 | 补验证完成68f2f8a；不计新增 |
| 新增20七电阻双源 | Fraction精确解、逐节点KCL、功率；独立执行通过 | 官方v2.2.2/R2025a，101样本14信号全过；禁用未接万用表，主网不变 | 已完成d481c57 |
| 新增21接地/浮动中性点 | 解析星点/KCL/功率、两求解/积分配置、事件/非法输入11项 | 官方真实1001样本；39窗×信号均过；原错标签证据保留 | 已完成5c595e2 |
| 既有12补PSCAD参考（B1） | 原12/核心未改；23专项、1267全量及独立Agg40001点通过 | 完整参考/300输入资格、候选固定比较、340快照与独审均PASS | 已完成40bef297；原MathWorks2% FAIL保留 |
| 新增22有限T梯级 | 3761a21先固定判据；101物理状态增广expm/ABCD/KCL/能量/TR/BE共8项通过；独立Agg通过 | 原50T零初值；10/5ps参考细化及六量真实比较均通过，最大8.01mV/0.160mA | 已完成80ba91c |
| 新增23线性T等效 | 0ec7239先固定协议；独立两状态谱指数/KCL/能量/显式事件/TR细化8项通过，独立Agg8001点 | 原完整五网络真实8063/16042点自细化PASS，七量两窗全过，最大0.697mV/0.304mA | 已完成A4a `91dbad6bb77af24d1a548a6d0943930c4bcce40f`；三相/其余组合未推广 |
| 新增24三相Y–Δ–Y链 | 9项精确启动/连续插值/KCL/功率/能量/TR/RMS/相位通过，独立Agg100001点；全量1179 passed490.61s含slow | 原完整58899/76502点自细化38项通过；最终商业两窗19量38项通过，初次1µs绝对FAIL保留 | 已完成02044768579ba083d1fb526786922e770cc2e7c6；不含线路/其他组别/零序/饱和，跨OS CI另待验 |
| 新增25完整供电网络 | 11项独立节点/12初值/14量PWL/KCL/14损耗/双能量/TR/RMS/PQ/相位，Agg5001点；完整1190 passed478.96s含slow | 原完整5023/10023点，28self+56独立精度全过；14量两窗28商业比较全过，maxV0.864127V/maxI0.00623452A/maxNR1.74756e−6 | 已完成9e2513dd98c12ee4f50d94261318ef56fd475aa4；首次守卫失败保留，跨OS CI单列 |
| 新增26同步Buck | 12物理+21参考+13比较工具测试/独立Agg；26验收时全量1236 passed478.786s含slow，锁定/Ruff/mypy通过 | 25/12.5ns真实406263/809567点，两窗及全部500周期自细化PASS；首个50ns候选报告及独立原始数据/输入/周期/两窗复核PASS | 已完成9269350887a867aee2740fed04155ade8f8757be；26阶段正式新增8，限冻结同步控制/事件与二极管不活动域 |
| 新增27有限R Bergeron | 8项独立行波/KCL/KVL/能量/细化测试、独立Agg6001点；完整1244 passed469.79s含slow、109源码hash未变，锁定/Ruff/mypy通过 | 真实PSCAD 6001/12001点参考先过16自细化；四量双完整窗八项全过，maxV5.92e-12V/maxI5.16e-14A；153输入/原始数据/图双独审通过 | 已完成ae9fe3629ad9617853979b0ef58d4d8319239592，正式新增9；限常参数集总损耗近似，隐藏缓冲未直接导出，跨OS另记F1 |
| PSCAD cookbook | 工程XML已检查 | v4.6.0，无实跑数值 | inspected |

以下保留各阶段历史；较早“资源不足/未比较/未启动”不覆盖上述当前状态。

到20的本地稳定Python3.14.5完整回归：1133 passed，154.47 s；Ruff/mypy通过。原14例及新增19/20均单独执行通过。

到21的最新本地完整回归：**1144 passed，158.14 s**（含slow）；Ruff/mypy通过。21独立Agg运行也通过，当前共有17个教学脚本。

B1工具加入10项数学/失败测试后的完整回归：**1154 passed，144.24 s**（含slow），Ruff/mypy通过。此前默认沙箱Temp权限导致46项fixture建立目录失败；使用新的仓库内basetemp全量重跑全部通过。该结果属于软件测试，不把12的真实波形FAIL改为通过。`8a65b6e` 的 [独立CI](https://github.com/yu-yikai/PyCy_EMT_Lite/actions/runs/41805586718) 已在Ubuntu/Windows全部成功；精简证据见experiments/ci_8a65b6e.json。该HEAD不覆盖之后新增的22代码。

到22的最终本地全量（含slow）：**1162 passed，412.17 s**；Ruff/mypy通过。18个教学脚本均已独立运行；22专项8项耗时339.16s。`80ba91c`代码已正常推送，尚未观察到其CI run，不借用8a结果。必要阶段文档将正常push以对同一代码的新HEAD做完整双平台验证。

`68f2f8a` 的 [GitHub Actions](https://github.com/yu-yikai/PyCy_EMT_Lite/actions/runs/41799220935) 已实际success，Ubuntu/Windows两job全部成功，含全量/slow/coverage、全部例、构建、安装wheel与生成文件检查。该旧HEAD证据不覆盖20/21。

`5c595e2` 的 [GitHub Actions](https://github.com/yu-yikai/PyCy_EMT_Lite/actions/runs/41801829262) 已实际success，Ubuntu/Windows的全部步骤成功，覆盖新增19/20/21和既有02补验证的代码。可提交的精简证据为 `experiments/ci_5c595e2.json`；原始run/jobs JSON在 `.tmp/longterm/ci/`。job日志下载实际返回403，未从元数据推测远端测试数量；1144是本地实测数量。

各例完整数值报告在 `validation/cases/*/validation_report.json`；商业模型、波形与图/日志在local_reference，默认不提交。报告包含来源/软件、原模型/raw/normalized/候选hash、固定阈值、绝对时间和输入快照。网络已用系统现有代理恢复正常push；后续HEAD需单独记录CI，不能把本次证据扩大到未测试代码。

2026-11-06到23的本地最终全量：**1170 passed，384.08 s**（含slow），锁定离线同步27包、Ruff全范围、mypy39源码文件通过。日志`.tmp/longterm/a4-closeout-pytest.log`/`a4-closeout-tests.xml`；23独立执行日志`a4-closeout-standalone.log`。正式报告run20261106T025650374531Z，两窗×七量全部通过，SHA a64c0677349799eb0f3b7874b6cbedba071fd07c3e0498cc6933bc48ee71c0bc。

`90b2fcd`的[真实CI](https://github.com/yu-yikai/PyCy_EMT_Lite/actions/runs/41809969999)两系统全步骤success，在线复核日期2026-11-06；与80ba91c同代码，因此补齐22的跨操作系统验收。证据experiments/ci_90b2fcd.json，公开job日志403，远端测试数量未知。该旧HEAD不覆盖23；23在正常push后的精确HEAD另行等待CI，不把本地通过改称远端通过。

2026-11-06最新远端e51c1f1的[CI run42154476032](https://github.com/yu-yikai/PyCy_EMT_Lite/actions/runs/42154476032)实际终态failure，但两job均未获runner、steps为空，check-run注释明确“The job was not started because your account is locked due to a billing issue.”，没有运行软件测试。证据experiments/ci_e51c1f1.json及归档annotations；远端测试数null。23商业平台数值比较和本地回归通过保持原结论，23跨OS CI仍待账户解锁后补验；不能以旧90b2fcd替代。

2026-11-06 A4b候选：8项独立物理测试、Agg50001点、锁定同步/Ruff/mypy通过；新增后完整1178 passed474.63 s（含slow）。严格原ode15s资源中止，极小AbsTol的daessc短探针也出现最小步长停滞；两Abs1e-8短probe和自细化通过。参考配置补充926138d在正式full/候选商业比较前提交，固定19量/两窗/双限值及参考十分之一误差预算不变。正式50ms参考与候选商业验收仍待完成，正式新增仍5。

2026-11-06到24最终：1179 passed490.61s（XML490.603，含slow），日志.tmp/longterm/a4b-final-full-pytest.log、a4b-final-full-tests.xml。锁定同步27包、Ruff全范围、mypy39通过，九专项76.926s、独立Agg100001点。最终真实比较run20261106T041603177270Z全部38项PASS，maxLV20.17655V/HV205.91860V/源电流119.38782µA/maxNR.000246239，图/输入/hash独立审计均完成，提交0204476。原始资源中止/最小步长/guard/1µs商业FAIL均保留，未降低窗口/限值。正式新增6；A4当前23/24范围完成，真实线路组合后置D0，F1新HEAD跨OS状态单独记录。

2026-11-06本批已正常push到1423c7d6dfbca10547cf856dc20faa5dadf935dc。一次有界公开API观察确认最新CI run42162705728终态failure：Windows127711904930/Ubuntu127711905228均runner_id=0、steps=[]，各自注释明确账户billing lock，未执行任何测试，远端test_count=null。证据experiments/ci_1423c7d.json，7份raw响应/hash全核；网络观察及所有本轮监控已终态。23/24跨OS仍未验证，F1局部受阻不改变本地1179/商业数值PASS。继续D0参考先行，不通过代码或空提交绕账单锁。

2026-11-06 D0默认参考探针run20261106T044524416Z：真实R2025a Update1运行原power_gui50ms，219点/12动态状态，ode23tb、7.2005767s；监测exit0、Dirty off、原SLX SHA不变。12实际初值与native analysis x0完全相同且全非零；原始MAT、CSV、状态名/A/B/C/D与netlist保留。没有Scope输出；目前仅runnable，尚无精化、候选、商业比较或第7项正式交付。本轮仅研究与文档，1179全量结果仍属于此前已通过且未改变的代码，不记作重新执行。

D0独立物理核验：17支路参数最大相对差6.994e-14，12状态相量3.839e-13、6输出1.097e-13；T接点/方向与原生导数行一致。最终74项库存hash由主审全核，入口evidence_inventory_final.json（9297e7ef…）；旧库存保留其并行收尾前两项身份。相量一致性不代替尚未完成的时间域精化与候选验证。

2026-11-06 D0研究检查点已提交54374d5d9caf480d765b18faacea763054304f27。主审复核catalog22项中的86个SHA及最终库存74项全部通过，旧21项资源记录未改；任务依赖/JSON/19处本地文档链接和Git whitespace检查通过。仅文档/研究证据，无候选和代码/依赖变动，未重复1179全量。所有本轮native/提取/审查已终态，无后台任务；下一步冻结D0实现前协议，再细化参考并开发。正常推送及实际远端HEAD在执行末核对，23/24跨OS仍按最近一次真实CI账单锁失败记录，不以本次文档提交声称补验。


2026-11-06最新到25：1190 passed478.96s（XML478.948，含slow，1190/0fail/0error/0skip），锁定27包、全Ruff、mypy39及两个新入口通过。11专项6.63s，真实run20261106T054356596388Z的28项双限值通过；完整报告/图/hash及guard436c266的缓存说明见[25指南](../../validation/cases/source_line_transformer/README.md)。正式完成新增共7项。9e2513d已正常推送且实际远端一致，新CI正在有界观察；最近已实查1423c7d仍为billing lock启动前失败，不能把本地/商业PASS称作跨OS通过。


2026-11-06最新9e2513d代码里程碑已正常推送；[CI run42170878293](https://github.com/yu-yikai/PyCy_EMT_Lite/actions/runs/42170878293)已实查终态failure，Ubuntu127738145863/Windows127738146164均runner0、steps空，各注释确认GitHub账户billing lock，未执行测试/test_count=null。证据experiments/ci_9e2513d.json，7份raw响应/hash全核。F1局部受阻，23/24/25跨OS仍待账户外部恢复，不扩大本地/商业PASS结论；同终态不继续轮询。当前只做文档同步，代码/依赖与9e2513d一致，所有本轮监测已终态。

2026-11-09：参考自身失败完整报告见[initial_reference_failure.json](../../validation/cases/synchronous_buck/initial_reference_failure.json)；更细配置见[补充协议](../../validation/cases/synchronous_buck/reference_solver_addendum.md)。恢复后的13项参考数学测试、锁定/Ruff/mypy和独立Agg已实际执行；1190全量仍是25阶段结果，不称本轮已重跑。

2026-11-09最终本地全量：**1223 passed，475.864s（XML，含slow）**，零失败/错误/跳过；日志/XML .tmp/longterm/b2-final-20261109.*。原始点/配对两项校验修复后已完整重跑，锁定/Ruff/mypy及独立Agg通过。这是内部软件证据，Buck真实参考自身FAIL保持，PSCAD未build，跨OS尚待新HEAD实查。

2026-11-09远端精确候选41a6685：[run42576654146](https://github.com/yu-yikai/PyCy_EMT_Lite/actions/runs/42576654146)已核终态failure；Ubuntu129025769158/Windows129025769665均未获runner/steps空，注释仍为账户billing lock，远端test_count=null。软件代码没有在CI执行，不能推断测试失败或跨OS通过；7份raw/hash及精简JSON已保存。1223是本地实测。

B1原2%波形FAIL保持；本轮结构重建六路真实门极全40001点一致，±0.8V/实际二极管/1uS+BE差异已获得新代数证据，但默认12未改、未跑候选或新商业比较，仍未验收。见[时序补充](experiments/spwm_timing_followup.md)。

2026-11-09后续研究：PSCAD官方vdiv原参数0.2s/50µs实跑完成，16正常build消息/零警错，实际EMTDC链接/运行；PlotType0无磁盘波形，有限R仍未验收，详见experiments/pscad_toolchain_smoke.json。B1独立四因素16组合及24顺序审计确认门极为主影响，原12/2% FAIL不变；观测器件残差不算预测器件模型。本轮无生产源码/测试/依赖变化，1223是前次最终代码实测，不机械重跑。

2026-11-09 A3设计检查：15项物理库存、8输入、8 API输入、所有组件codec/端口、精确首个平台/DC及名义稳定性已独立复核。prepared目录5项库存与5引用全核，2.7181GiB<3GiB，native/builder/sim均未执行，有限R参考仍inspected/无数值验收；详见[设计](experiments/bergeron_reference_design.md)。B2 callback审计11产物/37输入和235记录保存，但无语义等价/内存增益实测。本轮仅研究文档，无生产/test/依赖修改，沿用前次1223实测而不称新回归。

2026-11-09 B1[同数学短探针设计](experiments/spwm_matched_reference_design.md)完成静态来源/控制/codec审查；独立核三库存26/39/29文件及全部输入，审计manifest SHA105b1a9dba0e14f042d97aa12797b937a055d0e7648732def247a962a77bd1d5。没有原生建模、波形、新商业比较或完整协议，原MathWorks2%波形FAIL和完成数7保持。A3 profile_guard_v2的9种exists/hash守卫用例通过，其他运行/物理逻辑不变；08:22UTC资源约2.282GiB<3GiB，driver未调用。本轮只新增研究说明与证据索引，没有生产/教学/测试/依赖改动；1223仍是41a6685代码的既有全量实测，不宣称重跑或新跨OS通过。

B1最终未执行builder SHAe93e70ab…，69/31/46图已独立核；40001原固定网格ref/carrier/门极及R值、保持/观察步号零差，仅为条件算术。新增builder/独立审阅库存5/7项主审全核，manifest分别9f101941…/00c212fb…；真实原生拓扑、时间、源、有效R和TR初始化仍待，无B1运行器。上述脚本均忽略且不进入教学执行路径。
