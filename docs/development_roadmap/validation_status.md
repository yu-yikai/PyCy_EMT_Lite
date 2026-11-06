# 验证状态

| 对象 | 内部证据 | 外部参考 | 正式状态 |
|---|---|---|---|
| 基线a03a450 | 1118测试含slow、14原有例通过 | 旧文档不等于本次商业对标 | 能力重评完成 |
| 级联RC探针 | 独立expm、KCL、TR/BE收敛通过 | 不冒称商业参考 | 研究探针完成 |
| 新增19级联RC | 分段矩阵指数、KCL/能量、TR/BE细化；独立执行通过 | 官方R2025a，真实10052样本；16个窗×信号均通过 | 已完成290a8ea |
| 既有02 RC | 原解析测试保留 | 官方参数适配、真实5013样本，电压/电流双限值均通过 | 补验证完成68f2f8a；不计新增 |
| 新增20七电阻双源 | Fraction精确解、逐节点KCL、功率；独立执行通过 | 官方v2.2.2/R2025a，101样本14信号全过；禁用未接万用表，主网不变 | 已完成d481c57 |
| 新增21接地/浮动中性点 | 解析星点/KCL/功率、两求解/积分配置、事件/非法输入11项 | 官方真实1001样本；39窗×信号均过；原错标签证据保留 | 已完成5c595e2 |
| 既有12 SPWM | 已有PWM/RL内部测试 | TwoLevel官方真实40001点；特征通过，波形NRMSE 2.66%–2.72%超2% | 首次对标FAIL；未完成，保留原判据 |
| 新增22有限T梯级 | 3761a21先固定判据；101物理状态增广expm/ABCD/KCL/能量/TR/BE共8项通过；独立Agg通过 | 原50T零初值；10/5ps参考细化及六量真实比较均通过，最大8.01mV/0.160mA | 已完成80ba91c |
| 新增23线性T等效 | 0ec7239先固定协议；独立两状态谱指数/KCL/能量/显式事件/TR细化8项通过，独立Agg8001点 | 原完整五网络真实8063/16042点自细化PASS，七量两窗全过，最大0.697mV/0.304mA | 已完成A4a `91dbad6bb77af24d1a548a6d0943930c4bcce40f`；三相/其余组合未推广 |
| 新增24三相Y–Δ–Y链 | 9项精确启动/连续插值/KCL/功率/能量/TR/RMS/相位通过，独立Agg100001点；全量1179 passed490.61s含slow | 原完整58899/76502点自细化38项通过；最终商业两窗19量38项通过，初次1µs绝对FAIL保留 | 已完成02044768579ba083d1fb526786922e770cc2e7c6；不含线路/其他组别/零序/饱和，跨OS CI另待验 |
| PSCAD cookbook | 工程XML已检查 | v4.6.0，无实跑数值 | inspected |

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
