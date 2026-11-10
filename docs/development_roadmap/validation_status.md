# 验证状态

2026-11-10当前：27已在`ae9fe36`独立验收并正常推送，正式新增19–27共9项，任务转B1。
最新完整**1244 passed，469.79 s**（XML469.778，含slow），失败/错误/跳过均0；
全部109个Python源文件在全量运行前后集合/hash一致，锁定27包/Ruff/mypy39通过。
日志/XML为`.tmp/longterm/a3-27-full-20261109T1207.*`；27的数值报告、参考资格和本地验收hash见
[validation_report.json](../../validation/cases/finite_r_bergeron/validation_report.json)。
真实PSCAD及内部物理证据分开记，未用解析解替代商业输出。

新精确[CI42616684547](https://github.com/yu-yikai/PyCy_EMT_Lite/actions/runs/42616684547)
实查终态failure；Ubuntu129158174490/Windows129158174768均runner0/steps空，
两个注释确认账户billing lock，未执行测试、test_count=null。
[ci_ae9fe36.json](experiments/ci_ae9fe36.json)及7份raw/hash已核；23–27跨OS仍待验，旧90b2fcd仅覆盖22。
所有本轮执行已终态；历史失败/暂停中断不覆盖或冒充本轮PASS，完整来源见
[证据索引](experiments/native_reference_attempts_20261109.md)。

| 对象 | 内部证据 | 外部参考 | 正式状态 |
|---|---|---|---|
| 基线a03a450 | 1118测试含slow、14原有例通过 | 旧文档不等于本次商业对标 | 能力重评完成 |
| 级联RC探针 | 独立expm、KCL、TR/BE收敛通过 | 不冒称商业参考 | 研究探针完成 |
| 新增19级联RC | 分段矩阵指数、KCL/能量、TR/BE细化；独立执行通过 | 官方R2025a，真实10052样本；16个窗×信号均通过 | 已完成290a8ea |
| 既有02 RC | 原解析测试保留 | 官方参数适配、真实5013样本，电压/电流双限值均通过 | 补验证完成68f2f8a；不计新增 |
| 新增20七电阻双源 | Fraction精确解、逐节点KCL、功率；独立执行通过 | 官方v2.2.2/R2025a，101样本14信号全过；禁用未接万用表，主网不变 | 已完成d481c57 |
| 新增21接地/浮动中性点 | 解析星点/KCL/功率、两求解/积分配置、事件/非法输入11项 | 官方真实1001样本；39窗×信号均过；原错标签证据保留 | 已完成5c595e2 |
| 既有12 SPWM | 原PWM/RL测试；新PSCAD实际拓扑、1206门极及20 µs原语小模型双步长原始行/生成次序独审通过 | 原MathWorks40001点2.66%–2.72%超过2%；同数学1 ms/201点/46通道可运行；小模型5/9行证明t0、连续脉冲、中间保持及同tick电阻 | 原FAIL保留；仅原语资格通过；v3粗步编译前停止；完整只读捕获定位 Ts_s 开路；v4 单线修复后实际保存的 356/185/471/110 全图通过，但保存 XML 的 revisor 守卫拒绝，未编译、无新波形，完整 0.2 s 未验收 |
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
