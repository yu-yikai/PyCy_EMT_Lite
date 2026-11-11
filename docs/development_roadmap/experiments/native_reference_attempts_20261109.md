# 商业参考的实际运行与恢复入口（2026-11-09起）

本记录区分真实参考、自检、候选比较与建模失败。正式新增19–27共9项；27已独立验收提交ae9fe362，A3completed，当前B1。26的9269350交付和旧失败均保留历史。所有第三方模型、原始波形及运行脚本留在忽略的`local_reference/`。短探针没有替代正式验收。

当前更新至2026-11-11：B1完整1ms保持桥双步长诊断通过；完整0.2s协议/参考/候选仍待，详见文末。

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

## 2026-11-10三相保持v3：编译前重载端口拒绝

D仍为上述B1研究根。保存XML库存审查的两处缺口（重复ID/参数名和额外Frame被过滤）均保留原失败，
中断132011稿又拒绝了合法Main无ID元数据，未冻结/未原生运行。v3仅允许原件完整相同的paramlist和空grouping，
其余全部孩子逐一检查；双正常、24反例拒绝通过。源包D/held_bridge_research/20261110T012542208437Z_inventory_fix_v3，
75项manifest SHA `7383d7be87ba0382c09b1828af7eff9575e48e3f8513624253a628ec9b10c68f`；
独审 `local_reference/native_static_reviews/b1_held_bridge_v3_20261110T012725578000Z/report.json`
SHA `999e414f13c8b4c787a02d4d3e35594f940c294829a40317616f30a951f1ca60`。
这些是静态和隔离副本保存守卫结果，不能认证原生连通性。

实际粗步run `D/n/20261110T012944216380Z` 在读取第36个组件Ts_s时拒绝，worker1/14.8018653 s；
没有到setter、改接、新增元件、save、build或run，复制工程仍与00c3输入逐字相同。
Ts_s定义/参数/codec/端口类型不变，唯OUT.x由原创建记录70变为原生重载69；原输出标签仍在70且无连线，
不能假定偏移无害。已抓36个组件中只有该端口差异，不能据此推断剩余284个端口或完整图。
库名义端口仍在x+2；同类h_s未移，具体原生重载/图形原因尚未证明。

| 实际归档 | SHA256 |
|---|---|
| terminal.json | `67dddc9505b9771a17b67e31ba39cd01b71e69ec1f919f72c8593107cd55000c` |
| manifest.json（33项全部核同） | `eed419bf054ecffab97c96fbde3e5ac4ea4f008a3b3ddbd54cca5d6483b3ffca` |
| before_components.json（36项） | `0112baa1f8dfe4ab4fe3848c7b83b5926042569ea54dc4244c15a80141914c98` |
| worker.stderr.txt | `6edc2387c4806791c36fbabd125d174c486cede9475e9eb9a70d9a6ef101e135` |

自有进程空、monitor/cleanup错误空，源/profile/父环境未变；native_run_returned=false，build_errors=null。
这不是科学比较FAIL，亦不改变此前20 µs原语资格。v3细步长不启动；下一步准备独审的只读全320组件/163线
抓取入口，先核所有重载差异及实际网络，在所有setter/save/build/run前硬停。原12和原MathWorks2% FAIL保持。
先前分析器130950及其绑定v3的派生版012748均支持5/2.5 µs配对分析；后者9ccb37ef…不能用于这个无波形失败run；
协议340cf3a6…和阈值不变，后续来源包变化必须另建绑定版本。

## 2026-11-10完整只读重载抓取与单线修正依据

捕获包 `D/load_geometry_capture/20261110T013730Z_capture_only_v1`，19项manifest
`6f558354bbb4f77235307fd521f3b3046b64c6a95c28d71b3a5838787ee279d7`；
builder `dd189cae923b97ffbca81d79958b4140b0e3df2bc70b9ca8dc5418a586687b11`，
driver `da430d882d6d6a14f1079eaf4e1338565e0c7f2aacb3571a9bd85ae5536a7b40`。
已检查不存在原生setter/save/project.build/run路径，保留原420 s资源/身份/清理守卫。

实际 `D/n/20261110T014409445520Z` 终态为READ_ONLY_CAPTURE_COMPLETE_NO_MUTATION_OR_SOLVE，
162.0826488 s，预定CaptureComplete异常/worker1，diagnostic_capture_completed=true，
guarded_driver_completed=false；不称仿真PASS。自有进程空，原件/profile/父环境未变。
全部320组件定义/参数/codec、163条线顶点逐项相同，唯Ts_s OUT70→69；其原生location67与源XML68不同，
其他319个location均同原件。主库OUT相对原生location仍+2，所以不再把现象猜成主库端口偏移。
具体加载/实例位置变化的原因仍未证；Ts_s和h_s末次端口重读均稳定，磁盘副本仍为00c3。

| 实际run归档 | SHA256 |
|---|---|
| manifest.json（42项主审/独审全核） | `b89a771447cc7602246f0bedda04276b2d2849bc37ce8a4d62f4a6cd6fdf62f7` |
| terminal.json | `e688b537c1b5e657303d78388e77952381381750a68c9734aad866ec8952bf24` |
| capture_result.json | `27981f4464882d72779cefd6746dc37dc8fd4a40d78d6e64e92d79c99d817fde` |
| loaded_components.json | `a7e05122c1ad2fc2d9e2ac2e6fb941eeac75990c12ebaa21a50a055995afe0af` |
| loaded_wires.json | `85911836d6b5675d49166772e3be4f538642314106ccd163ec5b92e652e4d927` |
| loaded_graph.json | `b2b50338cd63760a3a441d67900f8f15906c1727ae4e9c2481c1102b9bab8405` |

422端口/102预期网只有signal:Ts_s分为两段，零short/X交叉/overlap。
独审 `local_reference/native_static_reviews/b1_complete_load_geometry_20261110T014556040427Z/report.json`
SHA `7c19d8e6557b716cc61ceb8e60d0068c69a1fff7ff634947eff298ee2588a431`；
其one_wire_repair_proof/report.json SHA `c95a46739a5462489a25aaf54c96ae80eb99267b7315c82016a43423c63ecd23`
以连续线段/端口独立算法证明只加(69,60)→(70,60)线可恢复422端口/102网全连通，且段上仅两个目标端口。
all_location_crosscheck/report.json SHA `8324706dbe18054409bfbed92860fa4c1f08384ec1a0550500221a0711e733ef`。
这是最小几何修正的依据，不认证后续save或运行；旧XML位置守卫保持，保存结果尚未实测。

新 `D/held_bridge_analysis/20261110T015018895673Z_geometry_addendum/protocol.json`
SHA `6e9bd7764a2e32a3e73a5697a2f48fe88fdba13fa77dadacadfef614450c8493`，仅线数184→185；
数值预算/物理方程与340cf3原协议完全相同，尚无新波形。后续单线版本见下一节；
原12、原MathWorks FAIL和正式完成9项不变。
全部109项目Python文件集合/hash与1244全量前一致，核心/依赖相对起点main不变；本轮未机械重跑旧全量。


## 2026-11-10单线修复 v4：冻结与运行入口

源包为 `D/held_bridge_research/20261110T015230Z_Ts_one_wire_v4`。24 文件清单全部核同，
manifest SHA `2cec5b4405083ccc0e91f61be66eb9f14374839c52e75fdb1ac649a8b7c6a679`。
只据完整原生捕获把 Ts_s.OUT 预期坐标改为 (69,60)，增加一段到原标签 (70,60) 的导线。
不主动移动原组件；69 个控制数学对象、31 个电气对象和原导线保持。
总数为 356 组件、185 线、471 端口、110 网络，保存库存为 541 对象及原两项元数据。

两步长离线接线通过；30 项 XML 反例、4 项接线故障和两项过期证据均被拒绝。
原保存 XML 的组件坐标守卫保持严格，未预先允许 Ts_s 保存到新坐标。
独审 `local_reference/native_static_reviews/b1_one_wire_v4_20261110T015420439121Z/report.json`
SHA `85675153792e6f001ef1b91f65597159f398bf146bf868d98f2abff8a1000367`，
最终绑定 `final_package_binding/report.json`
SHA `47346ed4fcb769388350408205b1ba41e1eab65e21eb05ed1eadb75491048a8d`。

| 冻结入口 | SHA256 |
|---|---|
| builder_held_bridge_5us.py | `7ea821ee2cc3b857d40a78a9a59d8d4134dbe5d55402fb6e67582cbc183ce4ef` |
| builder_held_bridge_2p5us.py | `27579e2474fe1c64cc1b9de735483d7987bfee49f00f592a3cf70a7a6c83dd63` |
| b1_native_held_bridge_5us.py | `badf51a5f2499c5ed1aff53376fbcf4ee67825633e6220afc8303d2644211975` |
| b1_native_held_bridge_2p5us.py | `449be6f37f72f79cc5d8c058d2d163f0a907d5c2c5dcffdde1acac7a7da1ee00` |

分析器为 `D/held_bridge_analysis/20261110T015936218946Z_Ts_one_wire_v4/analyze.py`，
SHA `d8518e6f74a88171423fe60779e0823bb0427bc15934156f4078b1f591970159`；
7 文件 manifest SHA `1baaafdcee5a972aa4b00772b17090693cb58fe130351206605711ee167bb7ff`。
绑定 SHA `311d11aed064bcc27f0bf1ed17204e77cd9763989a489d11b6ed84d54b7e3cad`，协议仍为 `6e9bd776…`。
分析器仅更新源包绑定、协议身份和导线数，全部方程、预算与其他函数保持。
独审 `analyzer_binding_review/report.json`（同上述独审目录）
SHA `91ca96640782b3ec2982c40dc27c97c946ec3398047c2eb98ca3bab9e37d31ac`。
上述冻结及审查都在新波形之前；资源、原件、profile 和清理保护不变。


### v4 粗步长实际保存结果：尚未编译

实际 run `D/n/20261110T020027875119Z`，256.4880211 s，worker1。
原生新增 36 组件、22 条线（含修复线）并保存；随后完整回读 320 个原组件和 163 条原导线，
全部定义、参数、端口和导线顶点通过原生检查，只有预设的 12 个标签 Name 改接。
保存后全图通过：356 组件、185 线、471 端口、110 网络，开路、短接、交叉和重叠均为空。

保存 XML 检查首先在 `revisor` 处拒绝，因此没有 build/run，也没有新波形。
完整读盘观察到修订信息更新、Ts_s 的 x 从 1224 持久化为 1206（68→67 网格）、
Main 画布 size 从 0 变为 4、12 个改名标签的显示宽度各增加 30 像素，Main CRC 改变；
顶层 Station 的 hierarchy link 从 645246283 变为 1700560261，嵌套 Main link 1978988629 不变。
这些观察用于准备有明确范围的保存检查，不忽略任意坐标、元数据或物理参数变化；
剔除新增 36 组件和 22 线、逐项还原上述七类差异后，整个规范化项目树与原件一致。
新增组件的完整编码参数、全部新增线顶点也与原生回读相同。v4 的细步长入口不运行。
两个顶层 link 值均不是文件中的对象 id；Station 定义及嵌套 Main 的目标对象保持相同。
link 的具体含义未证明，不据此虚构平台语义。

| 实际归档 | SHA256 |
|---|---|
| manifest.json（51 文件全部核同） | `0499fc9dea9dfae80a1c1a721bcfc0233adaa962388af231d943823221c67845` |
| terminal.json | `ac221078e465a4f92b56e24e5c3b0d52d7167340ed45509b7bd065b23f448ec1` |
| after_save_graph.json | `7d365669c069edbbedc7c10245eb57e599262958a4e6e33eac92403777ab1591` |
| project/vdiv.pscx | `754f4584efca82da8a41c458c007be5db702f538a66af984441194b666b8d38d` |

monitor/cleanup 错误为空，自有进程为空，源、依赖、profile 和父环境未变。
这是保存守卫拒绝，不是数值比较 FAIL；B1 仍进行中，完整 0.2 s 未验收，原 MathWorks FAIL 保留。


完整读盘核对记录为 `D/save_metadata_review/20261110T020900Z_v4_actual/report.json`，
SHA `f29fe59406a055949e17f6fc21219f4c2c0851f1a6aafd8e9fa8e369966c8d45`；
其 manifest 为 `2cf3453d9a42ed0180f04efc399e2e0d2342305e08d02572ae027ea3db3a2f91`。
实际修订秒数 1794276148 位于本次 save 调用的 02:02:27.879874–02:02:28.116686 UTC 内。
新版本将检查同一修订者及本次 save 的整数秒范围，只允许已实测的单个坐标和画布尺寸变化；
原组件改用完整属性比较，并只允许上述 12 个标签的宽度增量，其余属性保持严格。


## 2026-11-10限定保存检查 v5

独立完整核对：`local_reference/native_static_reviews/b1_v4_saved_XML_20261110T021128309961Z/report.json`，
SHA `087a27d9785e4a38f5ada4ff62683b188b40f931ab536deef8c654006743a33b`。
其独立连通图和七类差异的全树还原均通过；只还原三个拦截字段后，原 v4 保存守卫通过。

新源包 `D/held_bridge_research/20261110T021300Z_save_exact_v5` 的 25 文件 manifest 为
`72a3b74bc09440fe1ad4a05a19a2ef033e7db5e08c701c21e824eb877f8e004d`。
v5 只限定已观察到的保存变化：同一修订者、本次 save 调用前后整数秒范围、单个 Ts_s 的 x=1206、
Main.size=4。其余 Main 元数据保持；原组件改为完整属性比较，只允许上述 Ts_s 坐标和 12 个标签宽度各 +30。
没有新增模型 setter、数学控制、导线或物理判据，原 420 s 与进程清理保护保持。

真实 v4 保存文件未经修改即可通过 v5 检查；双步长离线图及 28 项针对性拒绝通过。
时间边界在实际 save 调用前后立即采集，先于后续 320 组件回读，不扩大到整个诊断时段。
独审 `local_reference/native_static_reviews/b1_save_exact_v5_20261110T021713155624Z/report.json`
SHA `53280816ccd0e4af33ae51351ef74dc1a1e8366ce36ab695ca9577833b5e8407`；
最终绑定 `final_package_binding/report.json`
SHA `d50a3bbaaeacc55024880bb0b261c3121497dc800fdc4b3e9abe6ccf1a22e508`。

| v5 冻结入口 | SHA256 |
|---|---|
| builder_held_bridge_5us.py | `4ea93fc45c2f4d160fce9241adc800e4ce7790e0904d202f7100f65176395275` |
| builder_held_bridge_2p5us.py | `68ebbc901cffca59d2ce840a77095f7fb1488ba61a74aac593bc051f7b7aa93b` |
| b1_native_held_bridge_5us.py | `7d2c42031f9fadccace363d7a42db859a2151a4428950da1ed84fb7a3f48d168` |
| b1_native_held_bridge_2p5us.py | `e298b0a64e62f39679d2091f67f4e398cb97bb8d4168f41a2f91ca1d73fe260f` |

分析器 `D/held_bridge_analysis/20261110T021727588195Z_save_exact_v5/analyze.py`
SHA `6ba6251a320b82414854fa87d968a43afd752672894bcedf86ee5ee14ceecb66`；
7 文件 manifest 为 `8517deafc91375c57592a623c530f5b8e59983b8a867fecc5bf8f17660412d0d`，
绑定 SHA `cf3819e4ea4fc609d8bb14633ef94fab7d9e4b5c7ff7981603feb601a733605e`。
协议仍为 `6e9bd776…`，仅换来源绑定，14 个函数及全部预算、方程保持。
独审 `analyzer_binding_review/report.json`（同上述 v5 独审目录）
SHA `9e91eb6c6a1c6104a5349dfc86190a924c9a0a56f42fd8159611233cee44ca9a`。
冻结与来源审查均在新波形之前，不将静态检查称为原生运行或数值验收。


### v5 原生编译：保存通过，五个 Pulse 悬空

实际 run `D/n/20261110T022135566419Z`，201.1054258 s。保存后的完整图与限定 XML 检查均通过；
编译器随后报告 5 个 `master:sampler` 的 Pulse 输入悬空，未生成 Main.f、inf 或波形，也没有调用 run。
5 个错误对象 id 为 1576063309、1672543186、1498322375、1778087624、1465072573。
只有 Station.f/Station.dta，不能据此声称完整电气模型已编译。

worker0 和 guarded_driver_completed=true 只表示驱动流程正常清理；
terminal 明确 native_build_errors=5、native_run_returned=false，不能将退出码当作仿真成功。
源、依赖、profile 和父环境未变，monitor/cleanup 错误及自有进程均为空。
下一稿应在清理后也以非零退出码报告编译失败，分析入口须先检查 build/run 语义再读取波形。
本次过早调用旧分析器，在缺少 inf 时返回 FileNotFoundError；没有数值报告或 PASS。
旧分析器及不完整结果保留，不重跑失败输入；修正仅限输入资格检查，不修改任何数值预算。

| v5 实际归档 | SHA256 |
|---|---|
| manifest.json（60 文件全部核同） | `0104d573c901096f07433008373b65615aed4275640797d035e287605ed6f481` |
| terminal.json | `383b7d10d6ee9f9c68918dbfaf42a382bd3f087d6f5751a8ca1b2efad101ea68` |
| build_messages.json | `af66f24eeb00ed1948123ea747a5435c0216bdfc9e885937041e6ceb18d8dad1` |
| saved_xml_guard.json | `7264be61040e08235f2f2c24af760e1418356ecf5429cbd98490fa0a2e397e07` |
| after_save_graph.json | `7d365669c069edbbedc7c10245eb57e599262958a4e6e33eac92403777ab1591` |

保存修订秒数 1794277394 位于本次保存整数边界 1794277393..1794277395。
Ts_s.x=1206、Main.size=4 均按实测持久化；旧数学控制和电气对象检查通过。
几何图把五处分支看作相接，但 PSCAD 编译器没有认可这些 Pulse 连接；
须核对原生分支连接规则，先用小型六路扇出诊断验证最小修正，再改完整模型。
v5 细步长不运行。尚无六路三相 1 ms 波形资格，完整 0.2 s 和原 12 新比较仍待验；正式新增9不变。


### 编译失败的分析准入修正与下一步候选

早拒补丁为 `D/held_bridge_analysis/20261110T022926997877Z_build_run_admission_patch/analyze.py`，
SHA `c311a53e22604acab1ff93f84e7640d14981da44a0399d2a6a07142f0afbb2be`，
6 文件 manifest 为 `d79be13a695939d2a15d255e3470e4717794e606d488a44f3b2b4e593261fd25`。
它先核 run 清单，要求 worker/terminal 的编译错误均为 0、run 已返回并有 EMTDC 完成标记，
再创建本次波形子目录和解析数据。实际 v5 失败输入在解析前被拒绝，六个有限准入检查通过；
13 个其他函数、数值预算和方程保持。旧 6ba 分析器及部分结果 `20261110T022521053709Z` 保留。
该补丁暂保留历史 v5 绑定，仅作下一稿的已审查修正；未来完整模型来源仍须另冻绑定。

两路实际映射确认，五个报错分别是 a_u、a_l、b_u、b_l、c_u，Pulse 高度为 378/392/406/420/434；
末端 c_l 的高度 448 没有报错。干线原生回读及保存均保留全部八个预设顶点，排除了顶点丢失。
官方连接文档描述允许顶点相接，因此不据这一次失败推断通用的“只允许端点”规则。
下一候选只把一条干线分成六条、各段在分支处结束，保留六个原分支；扇出导线由 7 条变 12 条。
先以 20 µs、5/2.5 µs 的小型六路 sampler 诊断确认端点相接的候选原生可用，未证实前不修改完整参考。
若采用此方案，完整模型预期导线数 190、保存对象数 546；这仍是待实测候选，几何协议须提前补充。


v5 原生编译终态独审为
`local_reference/native_static_reviews/b1_v5_native_build_20261110T023147236205Z/report.json`，
SHA `c8393274f9f7090812656718c28a70aa185e4c027c4b6a7b4bcfbf6ce9613f80`；
其 manifest 为 `9e03b5bae1cda9105b370827ee8a5bad1570c85a8deb10e68007798fed38e785`。
60 文件及实际文件集合全核，保存全文仍仅有上述七类差异；独审明确修正了此前连续几何图被当作原生开路证明的不足。
无波形便无 53 通道/201 行资格或独立 TR 波形结论。本轮所有已启动原生进程均已终态，下一诊断尚未原生执行。

早期分析准入补丁的独审为上述 v5 原生独审目录下的 `analyzer_patch_review/report.json`，
SHA `c9b0560da77d2dbb6e913a9a93a48b31f87069379e267537652b0d87693f2383`；
实际失败 run 在波形解析前被拒绝，13 个其他函数及全部数值预算不变，未来来源绑定仍待冻结。

### 六路分段扇出 20 µs：实际双步长资格

新源包 `D/junction_micro_research/20261110T023500Z_endpoint_segments`，19 文件 manifest `754fe2a31c567694845f16851812efb53a2aafc4e86a8be01c172faf52b68238`。
方案 `probe_plan.json` 为 `0c255ecf850220b916f937effe7564a0177ee04f019b6e26825b6b3aa2fc496b`，在实际新波形前冻结。
本模型只有三个同源斜坡 sampler、三个同源二进制门极 sampler、六个 Pulse 观察器及一条双向 varR；不是六路互补完整桥。
30 控制、9 电气、27 通道，完整库存为 143 组件/77 线/184 端口/40 网。
干线分成六段，六个 sampler Pulse、六个 Integer→Real 观察器、时钟及全局观察器共 14 个整数端口以端点相接。
该构造的离线正例和 17 个反例通过；不把端点构造解释为 PSCAD 的通用连接规则。

| 冻结入口 | SHA256 |
|---|---|
| builder_junction_micro_5us.py | `2bca477670624be9717416c983486df63bd22b8e7b82121168a0ba7b25537eb1` |
| builder_junction_micro_2p5us.py | `0810ec04fea28b88df8f4847f1827d4961414eac1ff5aec830b5e3ece25deca6` |
| b1_native_junction_micro_5us.py | `4f9539933ac7dd75878b1161173e9a81d71fbdabd21bfba9cde2baa13b4a3c58` |
| b1_native_junction_micro_2p5us.py | `a158caf516d049b3d2fe08524ecadb75984570f09c3fb9ab7a4c0279367dcda2` |

root 顺序执行实际粗/细 run，清理后明确要求编译错误 0、run 返回和 EMTDC 完成标记均通过，再读取波形。
两次均自有进程清空、无 monitor/cleanup 错误，原件、profile 和父环境未变。每次 48 个归档 SHA/size 全核。

| 实际 run | 耗时 | manifest SHA256 | terminal SHA256 |
|---|---|---|---|
| `20261110T025013355273Z` | 100.4808871 s | `8253361711e7d7a969e5cca017e458c7c2cc2790bb207f8265a6259dcca92bd9` | `3268d6d75cdd99dafe4b7393ef2e9d67890846a243fd4b5a3ab9b600119e39b6` |
| `20261110T030456070288Z` | 72.6936051 s | `f99d5bb1c0a2dc18a7efab20d7bde6d52ec12bfc38843c3c478945977f0c025a` | `5dac8051a18eda1ae3866a07d1fa13e449261bb3c260a3e60fed570bac29c57a` |

27 通道保留全部 5/9 行及 t0/20 µs。粗步 Pulse 每行 1，细步为 1/0 交替；六个 Pulse 观察器逐行等于整数时钟。
三组斜坡细步保持值为 1,1,2,2,3,3,4,4,5，三组门极保持值为 1,1,0,0,1,1,0,0,1。
五个共享点的六保持值、六 Pulse 和有效 R 完全一致，四个中间点正确保持；R 只取 .001/1e9 Ω。
同一步 Vload=Vs/(R+1)、Vvar=Vs−Vload、Iload=Vload/1Ω 及 KVL/欧姆关系均过原预算，最大残差 3.91e-16（原始 kV/kA）。
源和 varR 的 MainDyn 电流日志保留原值，不移相主波形；源电流在两个共享点仅有 5.70e-21 kA 打印/舍入差异。
六次 SAMP5 和六个 Pulse REAL 观察器使用同一 IT_1；驱动单 varR 的 g_held 在 R 计算/EXE 前生效。
两个不驱动电气支路的辅助门极 sampler 在 EXE 后执行，不能声称六个 sampler 都驱动了电气元件。
两次保存仅将 g_int 的三个数字拼写 1.0/0.0/1.0 改为 1/0/1，其他参数及全部 77 线严格一致。
实际两 run 的组件参数/端口/线路在排除随机 id 后相同，仅 time_step/sample_step 从 5 改为 2.5 µs。
细步运行有两行源 Branch1/SS1 的零内阻理想化提示，不属于 varR。独审旧一行匹配器在读原始数据前拒绝该格式；
保留原脚本和拒绝事实，另版只识别实际两行格式，继续拒绝任何额外、未解析或非源分支提示。

初版分析器 `5c45704a…` 错将全部 19 个源文件列为缓存，原因是绝对清单路径与相对运行路径直接比较。
旧源和旧结果保留。新版只在 main 中按 resolve 后的文件身份比较，真实 pyc 缓存与其他未列文件分别报告；
8 个其他函数、协议和数值预算不变，4 个路径检查通过。新版的三个额外文件列表均为空，粗步数值产物与原结果字节一致。

新版分析器 `D/junction_micro_analysis/20261110T030215964117Z_cache_paths_v2/analyze.py` SHA `bb3f485c5fc80c02b40f077d23027d08d1363609b8a76c4e0de553c5dc44dc9f`；
12 文件 manifest `366bdb2f20c17539ff4bf0ec0764a4e2a82604a7d5b5390a15a80dd41b27d27f`。
唯一双步长分析结果为该目录下 `results/20261110T030650934205Z`，21 文件 manifest `cb87f7567ec24b2b2f1b020a081b6c0b80d7ccb1ba41baf509d7f40b0820d895`，
summary `7c45ea89be5579aa1921f50b506ef1840da8341f1d7ebe133eda30b5456c9365`，DIAGNOSTIC_PASS，图已查看。
独立终态资格 `local_reference/native_static_reviews/b1_junction_actual_20261110T025715280858Z/pair_final/report.json` SHA `b10ecb6ec9b79355ffbf65313543d10403a45f8275b54d1aeafe4c2aa937be22`，manifest `4c6ec60b0474305650e96cb067f4c5942fb158966b83cbd14380c516c555f50d`。
独立粗/细报告 SHA 分别为 `7d1a329f0ad63e993f01af70dccdd70f31b0d5aa668ee0788daad7af894bc8e6` / `844180e1a9c6f5ba5326f6eafe5d05a68823d4191d8fb0c72ae3d0edaf458155`。
总绑定 `D/junction_micro_qualification/20261110T031249998050Z/qualification.json` SHA `10ca01a7ad54d20a88b89ce2a99bc9df4ca286b2d4fb763a1e6ee9cbd5db53d2`，
2 文件 manifest `43858adad90c5ccb6a20188be96b99ca267ea6898290e55238e7ee423de09d9a`；逐项绑定原始 source、两 run、分析和最终独审。
路径修正独审 `local_reference/native_static_reviews/b1_analyzer_cache_fix_20261110T030523813426Z/report.json`
SHA `e9e1fc713e5735e66bb75f539274e7d4adeaee1e460202a2e9c4f0bb54b38d37`。

资格严格限于带观察器的上述 20 µs 标量网络；完整 69 数学块、六互补桥门极、1 ms 或 0.2 s 均不因此认证。
方案 B 的下一步选择保留旧对象/PGB，只将新增 Pulse 观察器设在 x300、新七 PGB 放 x400，避免 x320 支线碰到旧 PGB。
计划 `D/junction_followup_plan/20261110T025800908018Z/report.json` SHA `15576de1e9d360e118e740239700f4b422025fa58f368f7a9c0708a482bc671c`；
选择补记 `selection_addendum.json` SHA `f41e5d8c9698c0c7b747f0fa4797cb4687105ddac32abd2c7a32d3451a6d051d`。
完整预期库存 384/204/506/117、60 通道、588 保存对象。新完整源、协议几何补充、独审和实际 1 ms 双步长仍须分别完成。
本阶段所有已启动原生 run 已终态；项目 109 个 Python 源文件仍与 1244 全量前快照相同，未重复全量测试。

### 用户暂停：完整 v6 来源已冻结，首次粗步未编译

完整来源 `D/held_bridge_research/20261110T031601744130Z_six_observers_v6` 已冻结，27 文件 manifest `ff8a2dd30be7af0d7b5e58dba77820cae5ce73a1ae47a23d63985062f4a6a985`；
协议 `probe_plan.json` `837a0b76bb1b1e7343abe2d614949edbadf3049a7b40fe976fd704654c8fe752`。保持原69数学/31电气，只有预定分段接线、七观察器与60通道补充，预算不变。
来源独审 `local_reference/native_static_reviews/b1_full_v6_20261110T033000Z/report.json` SHA `8c1e1aff55cfe9769e57334c82a6d2181f48625dcd3f75e14f78bf324f8f15e4`。
分析器 `D/held_bridge_analysis/20261110T032215391716Z_six_observers_v6/analyze.py` SHA `fda6e3599a012f77467618200fa7b449053231bba346062e63c3f84e769d5212`，
18 文件 manifest `ae1e1db23573c03fda818e9ce5751107d89783eb44c157304d86b969bfe93a36`，协议字节复用来源；九项有限检查通过，原物理/源公式不变。
分析入口独审 `local_reference/native_static_reviews/b1_full60_analyzer_20261110T033500Z/report.json` SHA `24c3d44a2054e9a7d0fc07284bcb753dc17338964bdca08c68488fc7729288b5`。

root 唯一粗步 `D/n/20261110T033233257295Z` 保存后回读时收到用户暂停指令。
按路径、完整命令、创建时刻、PID及父监控身份核对，仅终止自有worker17644，监控19976保留并完成原有精确清理。
worker1，372.6662254 s，末阶段 `builder_after_save_ports_off_c_l`；native_build_errors=null、run返回false、完成标记false。
尚未编译或仿真，没有数值验收；源/profile/父环境未变，自有进程、monitor和cleanup错误均为空。
52归档SHA/size核同，manifest `e9e326dc2414e7d4a9aeca304fb3de25333ede7363b6ae7653122b707ee9fc12`；terminal `ed7aad3a8459743114067d174618959bb84b04bd297886e5471ac32e5f0678e8`。
原terminal的stop_reason为null，因为外部按用户指令终止worker；不修改原件，另存暂停注记
`D/paused_runs/20261110T033233257295Z/pause.json` SHA `7a0565c5ae8d157d32ce4ab36c4543c252802fb3c496284882c9c329661f66ff`。
这是用户中断，不是数值FAIL/PASS；无粗步分析、细步启动或完整0.2s结果。等待明确恢复后新建run目录重新粗步。
六路20us资格已在2f3846c正常推送；正式新增9及功能checkpoint ae9fe36不变。所有自有原生进程均已结束，无后台继续。


## 2026-11-11：完整保持桥1 ms双步长诊断通过

用户明确恢复后重新核同分支/HEAD/真实远端0796f74、冻结来源/分析器/旧资格，
无PSCAD/compiler进程且资源满足守卫。旧033233暂停run没有被分析或配对。
原v6方案B、837a协议与fda6分析器不变，分别保留384组件/204线/506端口/117网/588保存对象。

| 实际run | 步长/全部行 | 生命周期 | manifest / terminal SHA256 |
|---|---|---|---|
| D/n/20261111T012359520751Z | 5µs / 201 | 250.3283437s、worker0 | 1e3079dc29d7f3a213fdcf14b1860dfc3fe25cefa46817f3049eac72684afdd0 / 6a8b48f8b96ae83c5c70a5519111c3a7983561f9598b4060c585369f6bccf40e |
| D/n/20261111T013727404980Z | 2.5µs / 401 | 305.6036259s、worker0 | 5eea30c7151ea6fddf5c17f6cb2340ca6f64694e035ed430730d909e490206b3 / 2af78bb9e582533f2c3542e746c7661b7350bacfc1de136549e1fafdb7fc8dda |

两者分别84归档SHA/size全核，terminal与worker均build_errors0/run_returnedtrue/完成标记true；
owned、monitor/cleanup错误为空，原件/profile/父环境/依赖未变。保存前后完整XML和原320组件/163线按旧限定守卫核对，
保存图、整数14端点BFS、生成顺序均通过；不推断通用接线规则。

作者配对 `D/held_bridge_analysis/20261110T032215391716Z_six_observers_v6/results/20261111T014327781041Z`：
summary `525ef21e04051ab9b53df6127fa2aafdedde23236a25117b9f3e0b3681628fb6`，
29项manifest `9e0d6eccdb259dc9fe3e1c0db1e0ee1c56ae0c63bc1cbb1c795c2457d8547184`，DIAGNOSTIC_PASS。
60通道全201/401行含t0/末点；201共享六施加门极/R相同、200中点保持及七整数Pulse观察器均通过。
3612原始门极值符合原69数学在原生TIME处的公式，R严格.001/1e9Ω，源400V。
两者均保留phaseA50µs近等号行，margin2.220446049250313e-16、原式/native gate1；
细步88个ASCII观察量半格舍入诊断保留，这些观察量没有驱动控制。t0粗I=0，细I约6.303e-29A，
均在旧1e-12A预算内；pole/neutral约3.999999999996e-10V，没有归零或删点。

独审根 `local_reference/native_static_reviews/b1_full60_actual_20261111`：
粗/细report `bca3e636…` / `69879da8…`；pair `pair_20261111T013727404980Z/report.json`
`5574049047936e6ddd21f1753142b82621d85c515dde47423edc48d98cec0ea3`，manifest `09bb78a5…`。
独立四未知量节点TR解覆盖全部行，细步最大电流差5.671e-12A、neutral差4.302e-11V、KCL5.003e-12A、RL/TR3.459e-9V，
均在冻结837a预算内。全部384组件（除新随机ID）参数/端口/位置及204导线路径两run一致，仅项目h/sample5→2.5µs。
独立全窗PWL电流max A/B/C为0.332501249/0.207000924/0.291821831A，RMS0.200099312/0.123277339/0.135738858A；
仅描述真实电气细化差，不新增验收门槛、不移相。root及作者已查看配对图 `ea337827…`。

独审v1先因小模型snapshot文件名假设拒绝，v2再因公共枚举表示假设拒绝，均在读raw前；
v3 `ea129011…`仅精确检查实际13个输入快照和requested1/2、encoded字符串1/2、公共INTEGER/REAL及端口类型，
旧脚本/拒绝事实保留，物理函数、协议、预算与原生数据不变。
范围资格 `D/held_bridge_qualification/20261111T014703278697Z/qualification.json`
`8be490f84a5d75acada52c46e84b0d5f4d6e5bdcd4345360340309f696201475`；manifest `b1105dd8…`，
绑定源27、分析器18、两run各84、作者29、独审及全部33pair输入。完整hash集中于reference_catalog的B1项。
该资格严格限含观察器的1ms，full0p2s/candidate/formalB1均false；原12和MathWorks2% FAIL保留。

完整输出前另有66行精确有理数数学推导：`D/electrical_refinement_estimate/20261111T013605399749Z`，
report `fa3f9dce…`，独审 `local_reference/native_static_reviews/b1_electrical_bound_20261111T014114157641Z/receipt.json` 为 `9e11b5fe…`。
same5µs保持输入、零初值及指定TR端点更新下，共享界0.664171454A、PWL全时/任意窗RMS界0.665002498A；
这只是reducedTR数学，不证明EMTDC实现、2ps时钟或libm。结合旧68边界的估计仍有条件，没有冻结新预算。
下一步按next_actions先另冻完整0.2s范围/准入/指标/预算，再运行真实参考；不继承旧未冻结1A/.3A提案。

C1只读可行性 `local_reference/c1_pll_reference_research/20261111T013530229954Z/feasibility.md`
`fc38067eda4c14f44de69838a0392ae3db8e8caac2a3bd3ae78b9cd694eef405`，evidence.json
`d92469cdd234477829ca5a5fa75a67648f17235fffadf3d3cbdaa73672375427`。
现成PSCAD master:tvekta和R2022b SPS PLL与11非同数学；独立标准块/UnitDelay方案尚未建立或执行，C1仍planned。
本轮109个Python源文件仍与1244全量前集合/hash一致，未改核心/依赖/教学入口，未重复全量测试。
所有本轮native和分析均终态，无自有原生进程待恢复；CI同账单锁终态不重复轮询。
