# 2026-11-09：商业参考的实际运行与恢复入口

本记录区分真实参考、自检、候选比较与建模失败。正式新增19–27共9项；27已独立验收提交ae9fe362，A3completed，当前B1。26的9269350交付和旧失败均保留历史。所有第三方模型、原始波形及运行脚本留在忽略的`local_reference/`。短探针没有替代正式验收。

## B2：参考、候选数值与正式交付通过

原100/50ns参考的500周期duty/派生源流FAIL保留在[原失败报告](../../../validation/cases/synchronous_buck/initial_reference_failure.json)。先行固定的25/12.5ns补充随后完成两次真实10ms运行，406263/809567点；两连续窗及全部500周期均通过原十分之一预算。周期duty最大差0.000901717<0.0015，派生源流0.00681914A<0.01A。[合格参考报告](../../../validation/cases/synchronous_buck/qualified_reference_report.json)明确其条件精度边界，不能当作绝对全局误差证明。

真实run位于`local_reference/b2_protocol_research/native_refinement_identity_v2/20261109T0842314439381Z/runs/`：`20261109T085422260Z-baseline`和`20261109T085726994Z-refined`。完整参考审计`local_reference/b2_protocol_research/20261109T085912755Z-refinement-25-12p5ns-audit/report.json` SHA`973dcb1874ae5afae6f97e601d7f36dc563a116ebf517fa075c77b13d955e947`；独立复核库存`local_reference/b2_protocol_research/postrun_pair_review/20261109T0856259740829Z/evidence_inventory.json` SHA`ae5790722b0aa9ce13b10e1f931b3ffe2e184916c560e69ee3846300b77bb797`。

50ns候选首次商业比较`local_reference/synchronous_buck/comparison_results/20261109T092300Z-first-candidate/report.json`输出PASS，SHA`d70e717a10b762b8e5dc8dc822907c04b5fdc2173cccf55fff8eb93b99def948`。独立原始数据/输入身份复核通过：全部500周期独立重算最大差4.97e-14、两窗指标最大差3.55e-15，审计`local_reference/synchronous_buck/comparison_audits/20261109T1054201484912Z_independent/report.json` SHA`2962a893dff0636bd452b349dfbadd5a0126a37f1fe230e75a9921ae3866f552`。精简[商业报告](../../../validation/cases/synchronous_buck/validation_report.json)已保存。13项比较工具测试、锁定27包、Ruff/mypy及恢复后完整pytest **1236 passed、478.786s、零失败/错误/跳过（含slow）**通过，XML`.tmp/longterm/buck-final-20261109Tresume01.xml` SHA`08923f2470d57988738efccd3fbd5ac39e432e2ea585ccb2ba794f143971b188`。先前暂停中断不算通过；新结果另立身份。独立Agg200001点/4事件的旧运行与当前候选源hash一致，经主审核定复用。26已以`9269350887a867aee2740fed04155ade8f8757be`独立提交，完成数8；本次比较时HEAD4e43及未提交工具快照身份仍保留，不能改写运行历史。结论仅覆盖冻结的同步控制/负荷事件和核定二极管不活动域；不推广为自动二极管/普通自换流Buck框架，也不认证其余半/全桥、Boost或滤波候选。

## A3：派生SrvcCbl参考自细化与27首次商业比较通过

以下目录均相对`local_reference/a3_followup/native_reference_design/20261109T074056761817Z/native_probe/`。

| run | 实际停止点 | 结果边界 |
| --- | --- | --- |
| `20261109T083756913536Z` | 原top77与native85库存守卫不等；native还返回4个OverlayGraph和4个Curve | 删除前停止，无build/sim |
| `20261109T084804578106Z` | 未限定库名的`defn_name`与预期身份守卫不符 | build前停止；保留原始失败 |
| `20261109T092018312571Z` | `builder_final_10_parameters`：`ValueError: Component has no parameters` | 原库/线路定义身份与14次接线调用已过；未保存修改工程，无build/sim |
| `20261109T105927241384Z` | v5已过全部Wire库存，原生SrvcCbl编辑前/后RowDefn一致性守卫拒绝 | 仅根CRC差异，含义未证；未保存修改工程，无build/sim |
| `20261109T111545271892Z` | 最小CRC诊断在删除其余76个Main顶层对象后首次观察根CRC变0，按设计停止 | snapshot0–34（35项）无差异；未编辑线路位置/Length，无save/build/run |
| `20261109T113500721502Z` | v6保存成功后，原生/磁盘定义恢复原CRC，严格CRC0编辑基线拒绝 | worker1/36.6893s；无build/run，旧拒绝保留 |
| `20261109T114121456591Z` | v7分阶段严格核定义后真实build/run | worker0/35.5044s；完整6ms，6001×6原生数据 |
| `20261109T115004933156Z` | 仅求解/输出步长改0.5µs副本真实build/run | worker0/50.2884s；完整6ms，12001×6原生数据 |

v4 run实际核对两个master线路定义/XML身份，原生RowDefn编辑前与原件一致；6ms/1µs求解/采样回读仅为配置证据。终态worker1、28.148s，观察到异常后正常quit，`remaining_owned=[]`、monitor错误null、cleanup错误空，原件/profile/父环境不变。manifest SHA`6393b32c33fce16cc63e8274c9ffa2c0dd718a887c7ec25c9b55a0b6950b08d5`；terminal SHA`4d035a963eb185df4e1ebfd63a6aac5490dac494140cce70a560dff3beb882ef`。

该次入口为`local_reference/a3_followup/finite_r_native_probe_owned_guard_v4.py` SHA`362fa0b54dd719ffc96db41e2cc780668f7556ad131a67e60ce326c9af3887ad`，builder为`.../native_reference_design/20261109T074056761817Z/builder_checked_v4.py` SHA`5182eec41ec459b8f418aa480b9d8abd3387e2d85df6f8bc2e7c4c1b543ec0e0`。它们保留为该次失败身份。

v5仅对本轮create_wire返回的精确Wire/已知iid省略不支持的parameters读取，最终集合严格相等；其他对象仍强读native参数，逐步保存身份。新driver`local_reference/a3_followup/finite_r_native_probe_owned_guard_v5.py` SHA`6beca649559638c15221dd16ebeca1717adbd7939d9dc81b85447afe3a3cd457`，builder`.../builder_checked_v5.py` SHA`ce894fec7178107cb51189b6a2c7007aea4cb026620dabd8195619ceb172bb4d`；独立AST审查确认控制/物理/接线/solver/保护不变。实际run`20261109T105927241384Z`已过Wire库存，但`Native SrvcCbl definition changed during Main-only editing`守卫停止，未保存修改工程/build/run。worker1、30.2399s，异常后正常quit、自有进程清空，源/profile/父环境不变；manifest SHA`47d246343b0458709fe78a77b4af307374425b3539a0739526e31ed12d73b439`，terminal SHA`575ad53b6572faa9ab35f913047537e50df90eb64606a65904a9063d5fec8005`。

独立核v5当时40项库存为1TLine+25UserCmp正常参数回读、14plainWire成功；31项manifest的hash/size全部相符。编辑前与原source一致；前/后唯一XML差异为根`Definition/@crc`从36752239变0，64参数、全部ID、内部paramlist CRC、布局/属性/拓扑均相同。原生CRC变0的原因尚未证明，不能直接称为普通序列化或已知物理变更。当时须先核CRC边界，未直接重跑或删除守卫；该次没有波形。后续严格分阶段保存与真实结果见下。

独立只读CRC研究位于`local_reference/a3_followup/integrity_review/20261109_crc_semantics_research_a9e612/`：`report.json` SHA`ea17d3c4bff90ae234fe3cd93c52cda94079254de28bbb93cbf1b5ddb71d1848`，`diagnostic_plan.json` SHA`c1523076af312eb8c041646bd91ef7db1c6b11d459a66ba50f77fe3caf5fcb4b`，manifest SHA`f3de89f4c117a7fa8b85d001b34b6f83304bc44615c6092338ad8d9aa1607931`。安装公共Definition.xml接口将返回字符串解析为新的客户端Element；7项内存检查通过，未运行native。XSD仅规定crc为required long，wizard的初始值为0；已读官方文档没有赋予“0即失效缓存”或“可忽略元数据”的语义，不能扩大解释。
已独立审查并实际执行最小分阶段CRC诊断：builder SHA`2fc58602f7614188b70e9c11970657a08350a054c3675274712a000f576f6590`、driver SHA`fd542bcb9d78dfb72d10bca7ae518390ce64b4b3c0d932a6826044a7d7f78ed8`。run`20261109T111545271892Z`的snapshot35紧接`delete_other_main_objects`（76个顶层对象批量删除）后首次观察根CRC 36752239→0，snapshot0–34及重复XML读取/dirty getter/库身份均未变，确认读取相同；其余定义内容仍无差异。该定位不确定是哪个删除对象或官方CRC语义，不能据此放松守卫。按设计DiagnosticStop，worker1/14.1266s，正常异常后quit、自有进程清空/monitor null/cleanup空，源/profile/父环境不变；未编辑line vertices/Length，无save/build/run。manifest SHA`089a2fa6cbfd5f1613d2f3fb4de9356632a74be6a5aeb2547e524f1920bdf7ff`，terminal SHA`578cd728916fc2e7374333395be0ac01b064b0b832b0055b8468d846eade0c5f`，诊断结果 SHA`3cb9e0e72a37a7cdf71a49eeebc85f2d3138f1f6c1332e1f0ef9655c853c5ba9`。 独立审计核66项manifest及37份XML（编号0–35加1份确认），0–34逐字节相同，35/确认恰为唯一根CRC字符串替换；报告`local_reference/a3_followup/integrity_review/20261109_actual_crc_diag_111545_08cd72/report.json` SHA`2a2dcc4a61d6d376741822f2f4c8cb007b5f9f7d094ec46adac3141b267d2caf`，审计manifest SHA`af0cc96e890d97b2f4b40c6202cca0dee0b8020137fe7d196f4089467f917eed`。

v6仅在已观测的批量删除边界强核唯一CRC转换及完整其余定义，再以完整CRC0定义守卫。实际113500保存成功后，native/disk恢复完整原CRC36752239，旧守卫正确拒绝，未build/run。v7编辑期仍严格，保存后要求nativeAfterSave==diskSaved==完整原source（含CRC），并核原生序列化逐字节等编辑前；没有忽略CRC。新builder SHA`1a9a903b8ae0be8b06f04f510aa59cf4f77c719b5a1044ca44f4c10cf2625f79`、driver SHA`2365c86f6ba765d28d5ec8aec01e5f1bcaa956c92a4d9f5e9f438111b696f647`的114121实际build/run成功。

实际TLI/TLO、生成源码和六通道确认R100Ω/Z201Ω/τ300µs，Interp1=1、Inflen=0、BDamp=0、LongLine=0。RTP/TTP单位为Ω/m及s/m，原生kV/kA统一乘1000；Vs/Mag无时移，送/收电流方向由CBR和Rs/RL关系核定。完整6001点独立回执`local_reference/native_static_reviews/20261109T114650Z_a3_actual/report.json` SHA`09a27b0d33b7b2cc0ba31ef5ba79d52eff34b3de0282ebe58e6644908a952ab1`。原生零前史和0.501/0.801ms首次非零支持零历史，隐藏延迟缓冲未直接导出；LCP频域复参数单独保留。

0.5µs run与1µs仅两个步长字段不同，TLO/物理/定义相同。完整资格`local_reference/a3_followup/integrity_review/20261109_a3_refpair_qualification_a8d36e/qualification.json` SHA`638fd6607f703a1799831a274f98088108a28f72a74c0d5b253e9cce25359cd8`，manifest SHA`cb538d8af2ff5d4624bf6acd212db601899e4bcb68a3f5274f98c09108efcdca`。四量两完整窗、共同1µs样本与合并原生网格PWL视图共16项全PASS，maxV9.6634e-12V/maxI5.1514e-14A/maxNR2.7474e-15；全部原始点/输入快照保留。

[协议](../../../validation/cases/finite_r_bergeron/acceptance_plan.md)已在候选前单独提交`44d1436df5714060176998ea1ce94c6d6eaf7d48`。27新源SHA`ab2e3e6cdcd3c799f9ae1952db8c4e2aab711c520443fcf5f529d7a31ba55ee0`独立Agg日志`.tmp/longterm/a3-27-standalone-20261109T1210.log`完成6001点，锁定27包/Ruff/mypy39源及8项物理专项2.89s已过。真实商业比较`local_reference/finite_r_bergeron/comparison_results/20261109T120632310271Z/report.json` SHA`1961582edfe26d9db3497cee3a3b7a884b977ac0596826c63998c433cffaed56`，四量两窗八项PASS、maxV5.9117e-12V/maxI5.1514e-14A/maxNR6.0489e-15，Vs gate1.414e-12V。独立原始数据双重复核和完整1244项回归已通过；27已独立验收提交`ae9fe3629ad9617853979b0ef58d4d8319239592`，正式新增共9项。 全量终态1244 passed469.79s（XML469.778s，零失败/错误/跳过、含slow），全部109个current.py集合与hash和运行前完全相同；独立全量收尾回执`local_reference/native_static_reviews/20261109T122213385907Z_a3_fullsuite_closeout/report.json` SHA`eccac0a01c8ffc046ae268acb7b77bfd90f3fd551fb7ba12248ee4e59d0d4fc6`。精简[正式报告](../../../validation/cases/finite_r_bergeron/validation_report.json) SHA`7768af6062eb7544afd7a4ff382733211fa4a09d0ed8c03f7e12d5c4bfff5a1f`；完整数值报告1961582…未变。 独立全原始数据回执`local_reference/a3_followup/integrity_review/20261109_a3_commercial_independent_bef0ad/report.json` SHA`a38fad05833cbdff7a73e6ea3af42dd1d5efbf94607d6431617f6d0fa3228689`（manifest SHA`fe449f4dd1e291f9b7d2ec78443df5727269f4d61791a60abd7c620b1dbb4f9a`）核153输入快照、12001参考/6001候选全部格式及独立PWL重积分；另一个独立代码/原始数据回执`local_reference/native_static_reviews/20261109T1207201487924Z_a3_public_review/actual_comparison_receipt.json` SHA`a75905ec83e2d92a2a8690f6afc8bfd6566600223f08894b57596a2bffdbc8c9`结果一致。


## B1：实际重连后1ms短探针成功，完整控制细化待定

研究根目录D为`local_reference/two_level_pwm/matched_reference_research/20261109T080850088678Z_pscad_static_d5d66d/`。runner包R为`D/owned_runner_research/20261109T084022489231Z/`，公共守卫修订目录G为`R/guard_fix_v3/20261109T085722111717Z/`；D/R/G仅为此文路径缩写。

| run位置 | 实际停止点 | 结果边界 |
| --- | --- | --- |
| `R/native_probe/20261109T085000185753Z` | 创建组件期间原子日志replace遇WinError5；旧清理再因动态`row.Terminate()`调用报TypeError | 无build/run；缺完整terminal，事后独立CIM确认自有进程不存在；不称正常quit |
| `G/native_probe/20261109T091032482166Z` | 262字符工程路径`app.load`报FileNotFoundError，Python侧副本实际存在且hash正确 | 无工程句柄/build/run；修订后日志/清理正常收尾 |
| `D/n/20261109T091917405572Z` | 170字符工程路径已成功加载并创建组件；`Installed native port coordinates differ; re-route before build` | 实际端口与静态坐标假设不符，无build/run |
| `D/n/20261109T111717200520Z` | 仅抓取31个电气组件参数/端口和53项预期检查，23项坐标不符后按设计停止 | 无接线/save/build/run，不据此认证物理拓扑 |
| `D/n/20261109T114236896235Z` | 实际端口重连后严格图审、build/run正常完成 | worker0/209.4687s；全0–1ms，201×46原生数据 |

旧091917 run worker1、21.867s，观察到异常后正常quit，`remaining_owned=[]`、monitor错误null、cleanup错误空，源/profile/父环境不变。manifest SHA`ae06fe3bc55b29b653b82639469a2a9fab074aa353a195786ad675bd92f59aea`；terminal SHA`b0422836cb649a7cd330b25836bfcbd3491b8c217f631a346173cd95e918027c`。短路径成功支持旧加载失败与路径长度有关，但旧FileNotFoundError不被改记成功。

该次入口`G/b1_native_probe_short_path_v4.py` SHA`8d596142e44660f3449f3a40d79704155b9b3c521a6490d3606ea2b5b4f6eccc`；builder`G/builder_inventory_v2.py` SHA`a113419df5602b0146e3027fdfa77339b7baaaa58993f3652958b5d23ead0a77`。builder保持原控制/电气/通道69/31/46规格，只严格补齐donor top21+2Graph+2Curve全部25ID/类型，并只删除top21。原静态builder e93e70ab及库存保留不改。当时须按实际端口重新核线并另存独审，后续重连仍保持全部守卫。

补充端口抓取builder SHA`87e6ea70b68fbd32a7bfc46b177a79d2c7378ac38f483f0ad58e93194977d27e`、driver SHA`994175a18afbded99460e03cbccaf0dadfa6266f1b66018b93699ba3334f9172`只增加实际坐标保存，并在原守卫/所有wire之前无条件停止。实际run`D/n/20261109T111717200520Z`为预期RuntimeError、21.4105s；正常异常后quit、自有进程清空、monitor null/cleanup空、源/profile/父环境不变。`native_port_capture.json` SHA`a3ab6c0197777eec75953bee59527b0ceb2180f7410a04480457988e54f458c8`，manifest SHA`46027d13cac184b7e051a9edbe571a514e68e791e329ceddca8354c0d3fae1b9`，terminal SHA`dacff8ff0d60c08efac859db5cc14c60d8e75755f8636867f86176e1ce5b72ec`。
实际source NA=(6,4)、NB=(10,4)，静态预期分别(5,4)/(11,4)，source ground仍(11,4)，原重合假设不成立；R/L/varrlc/电流表端口跨度2格，差分电压N2为y−2。不能统一缩放；随后重连稿逐端口核电气图/正交性/源probe/ground后才执行。builder SHA`2e83146221683fe5c54398432c48902d212da9b786bcb0a460fa3d8cc273e3f5`、driver SHA`317192dfbc5858a65a52aa9b7f30a9b558179b7211921f8e033414bdf22a6b91`的114236实际成功，正常退出、owned空、源/profile/父环境不变。

实际readback审计`D/readback_audit_research/20261109T114345717986Z/results/20261109T114236896235Z/report.json` SHA`f7113ab57b35077ff9164f66e1720bf58bdaca36d5bda477823c5f1879a75f7d`核48manifest、320组件/163实际wire顶点/422端口/102预期网络，无开短接。波形审计`D/actual_waveform_research/20261109T1149537774717Z/results/report.json` SHA`2dcd7dc01a3970cc08366a28432a8c9a9e034ef3516bfc6d620c9062719e1238`核全201×46原始行：Vs400V、三相零初流、1206门极原公式/rawTIME全同、六R输入0.001/1e9Ω，KCL最大5.01e-12A、TR残差最大1.563e-9V。Branch1理想化为源RE0，六varR为2/3/5/6/8/9。

DSD/DSO使六支路I日志落后一记录；1200对`V[k],R[k],I_record[k+1]`残差最大5.55e-17kV只是生成顺序诊断。保留首/末点、原CSV和同刻不匹配，不平移物理信号或候选。生成相位/omega约12位有效数字和ASCII TIME边界仍保留，不能由1ms推定full0.2s逐位同输入。

下一步设计`D/control_rate_design/20261109T115836954582Z/design.md` SHA`3213e21c93e30e25f46a78d15441271325a2281a952a94e16753bef312707166`仅提出六标准sampler+共享impulse/INT，未native。先做20µs/1ms探针核t0/连续Pulse/同刻顺序与细步中间保持，再冻full0.2s/5与2.5µs电气细化协议。TIME不量化、不回放候选门极；上游69算术仍按电气步执行，不声称冻结整个控制图。复制prepared_input入新unique目录后load，PSCAD5.0.0不使用跨目录save_as；所有actualports/wire/net/profile/source守卫保留。


## 共用运行守卫与未完成项

3GiB启动/2GiB动态提交余量、RPC20s、build180s、run120s、监控总420s保持。每轮新目录、复制原件、真实用户profile双侧存在/hash相同、源和父环境核对，进程每次核PID/父PID/路径/创建时间并排除既有PID。

日志读用显式共享READ/WRITE/DELETE并及时关闭的reader；写端仅对WinError5/32/33作0.2s有界retry。真实短持锁/及时close可完成原子写，持续锁按设计失败；额外“reader始终持开仍能replace”强用例实际FAIL，原样保留，不泛化共享删除保证。清理改用显式WMI`ExecMethod_('Terminate',...)`并取ReturnValue；独立finally保证自有Popen句柄与terminal收尾，未知remaining不能写成空。真实终止测试仅作用于自建短命隐藏Python子进程，没有终止其他程序。

公共守卫最终源SHA`e87584f575584a2dff4a7a8a14a1549603424b5575b5f8e2ff69337e5f15a3be`。独立复核入口`local_reference/a3_followup/integrity_review/20261109_owned_guard_v4_e875_9b13c2/report.json` SHA`2ac1e7bceb1738f8c445b626882c28176a7678b84720c27e93530c8f5e9e3769`；manifest SHA`7fc3b85fa6f8a96b5497923914568fee615fc9510767ee2afb74512d8dd3f57e`。旧脚本、失败和强用例均保留，不以守卫通过认证电路或数值。

08:22UTC约2.282GiB不足门槛是历史；08:36:59UTC实测约10.28GiB后才顺序启动，资源不足已非当前阻塞。A3/B1最新两轮均终态，不能等待旧worker。A3的真实参考/27商业比较/双独审/1244全量均通过，已完成ae9fe362；当前B1已获1ms真实波形，当前待保持5µs控制的细化小探针与完整协议。B1原MathWorks2% FAIL、默认12及全部窗/阈值不变，完整同数学0.2s协议须待实际控制时基、全部门极/有效R/源/单位/TR初始历史核清后再冻。

## 交付与跨操作系统边界

26交付`9269350887a867aee2740fed04155ade8f8757be`已正常push，真实ls-remote相同。精确[CI42606454705](https://github.com/yu-yikai/PyCy_EMT_Lite/actions/runs/42606454705)终态failure，Ubuntu129123587852/Windows129123588150均runner_id0、steps空；各check注释确认账户billing lock，未执行任何测试/test_count=null。精简[CI证据](ci_9269350.json) SHA`f84ac79906b409131616b71c0ab52dab6f31967b3e583dc014e4d138b0426a85`，7份原始API响应hash均核。F1局部受阻，不机械轮询该终态或借本地1236/商业PASS称跨OS通过。

27验收提交`ae9fe3629ad9617853979b0ef58d4d8319239592`已正常push且真实ls-remote相同；精确[CI42616684547](https://github.com/yu-yikai/PyCy_EMT_Lite/actions/runs/42616684547)实查终态failure，Ubuntu129158174490/Windows129158174768均runner0/steps空，两组annotations明确billing lock、未执行测试/test_count=null。新[CI证据](ci_ae9fe36.json) SHA`33523e8e411aa2a5d62670f52b4b33e6a34c2119f10d19efe28733fbf6ec9f57`，7份raw/hash已核。本地1244/商业PASS不代表跨OS执行；旧9269350证据独立保留，不重查任一终态。

## B1采样保持小模型双步长实测（13:07 UTC检查点）

以下D仍为`local_reference/two_level_pwm/matched_reference_research/20261109T080850088678Z_pscad_static_d5d66d`。
新小模型包为`D/hold_microprobe_research/20261109T123808872837Z`，plan在原生运行前冻结。

| 入口 | SHA256或终态 |
|---|---|
| 小模型包manifest.json（94项） | `209092793a35838fec9e7959d071f6565b4fd53363f82d72a6bf5d982f43b184` |
| probe_plan.json | `54b25beceb7d94d010d9447f4f0a39f2c1820317aef2a3676a24b4f16d89dc84` |
| 原生5 µs：D/n/20261109T125632879377Z | worker0，62.7550735 s，5行/17通道 |
| 该run manifest.json（46项） | `fa9d32ebe777eef2604fb4efdb068a8a6e08a073b03f33ce616abb9d42e5c514` |
| 原生2.5 µs：D/n/20261109T125858632549Z | worker0，62.5221623 s，9行/17通道 |
| 该run manifest.json（46项） | `f8a4daa4c4fa9a6b0fba7dcea4c7ab7085063d930933ee550d02fddd443f79e1` |
| 资格：D/microprobe_analysis/20261109T125739637402Z/primitive_qualification/20261109T130659559817Z/qualification.json | `5859c0fee101ba1942ecc2c0e7ac8fa1a3ca5ef4fcc111df984e282829089ae2` |
| 资格目录manifest.json | `5fe89702c127ec3a5f4aa62b66a2c67d69b13f1454f514d9969d46eb6b8d711f` |
| 独审：local_reference/native_static_reviews/b1_micro_pair_actual_20261109T130532536138Z/report.json | `47309dc912e9f5e78ba844168e9de843cd0d9d8e04f1aceba0bd39953c158496` |
| 该独审manifest.json | `2054135013d4f9813158571ea2c2f88c286b9062ccf6261d30ac99c082682ecc` |

两run原件/profile/父环境未变、自有进程空，清理/监控错误均空。
原生全部5/9行、t0/末点和四个半步均保留；初次分析profile字段schema错误的FAIL也保留，
修正仅影响解析，不改原生输入/数据。首次导入产生的一个__pycache__单独列为运行缓存，94个冻结输入均未变。
主审另独立核两份46项run manifest、全部原始值、共享点/中间保持和资格关联65个文件hash，并实看配对图。
资格只认证20 µs的两个标量sampler/单varR：连续高Pulse每次采样、中间保持、t0及同tick电阻生效，
电压方程残差≤3.91e-16 kV。DSD/DSO支路I记录次序不作波形移相。
六路三相1 ms、完整0.2 s和默认12新商业比较仍未验收；原MathWorks2% FAIL保持。
本轮没有项目Python源码/依赖变化，109个源码hash与已通过1244全量前一致，不把旧全量称为本轮重跑。
