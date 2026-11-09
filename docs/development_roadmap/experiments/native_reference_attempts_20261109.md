# 2026-11-09：商业参考的实际运行与恢复入口

本记录区分真实参考、自检、候选比较与建模失败。正式新增19–26共8项；26数值/独立审查、完整回归与Git交付均已完成。所有第三方模型、原始波形及运行脚本留在忽略的`local_reference/`。短探针没有替代正式验收。

## B2：参考、候选数值与正式交付通过

原100/50ns参考的500周期duty/派生源流FAIL保留在[原失败报告](../../../validation/cases/synchronous_buck/initial_reference_failure.json)。先行固定的25/12.5ns补充随后完成两次真实10ms运行，406263/809567点；两连续窗及全部500周期均通过原十分之一预算。周期duty最大差0.000901717<0.0015，派生源流0.00681914A<0.01A。[合格参考报告](../../../validation/cases/synchronous_buck/qualified_reference_report.json)明确其条件精度边界，不能当作绝对全局误差证明。

真实run位于`local_reference/b2_protocol_research/native_refinement_identity_v2/20261109T0842314439381Z/runs/`：`20261109T085422260Z-baseline`和`20261109T085726994Z-refined`。完整参考审计`local_reference/b2_protocol_research/20261109T085912755Z-refinement-25-12p5ns-audit/report.json` SHA`973dcb1874ae5afae6f97e601d7f36dc563a116ebf517fa075c77b13d955e947`；独立复核库存`local_reference/b2_protocol_research/postrun_pair_review/20261109T0856259740829Z/evidence_inventory.json` SHA`ae5790722b0aa9ce13b10e1f931b3ffe2e184916c560e69ee3846300b77bb797`。

50ns候选首次商业比较`local_reference/synchronous_buck/comparison_results/20261109T092300Z-first-candidate/report.json`输出PASS，SHA`d70e717a10b762b8e5dc8dc822907c04b5fdc2173cccf55fff8eb93b99def948`。独立原始数据/输入身份复核通过：全部500周期独立重算最大差4.97e-14、两窗指标最大差3.55e-15，审计`local_reference/synchronous_buck/comparison_audits/20261109T1054201484912Z_independent/report.json` SHA`2962a893dff0636bd452b349dfbadd5a0126a37f1fe230e75a9921ae3866f552`。精简[商业报告](../../../validation/cases/synchronous_buck/validation_report.json)已保存。13项比较工具测试、锁定27包、Ruff/mypy及恢复后完整pytest **1236 passed、478.786s、零失败/错误/跳过（含slow）**通过，XML`.tmp/longterm/buck-final-20261109Tresume01.xml` SHA`08923f2470d57988738efccd3fbd5ac39e432e2ea585ccb2ba794f143971b188`。先前暂停中断不算通过；新结果另立身份。独立Agg200001点/4事件的旧运行与当前候选源hash一致，经主审核定复用。26已以`9269350887a867aee2740fed04155ade8f8757be`独立提交，完成数8；本次比较时HEAD4e43及未提交工具快照身份仍保留，不能改写运行历史。结论仅覆盖冻结的同步控制/负荷事件和核定二极管不活动域；不推广为自动二极管/普通自换流Buck框架，也不认证其余半/全桥、Boost或滤波候选。

## A3：有限R建模已实际尝试，尚未保存或编译

以下目录均相对`local_reference/a3_followup/native_reference_design/20261109T074056761817Z/native_probe/`。

| run | 实际停止点 | 结果边界 |
| --- | --- | --- |
| `20261109T083756913536Z` | 原top77与native85库存守卫不等；native还返回4个OverlayGraph和4个Curve | 删除前停止，无build/sim |
| `20261109T084804578106Z` | 未限定库名的`defn_name`与预期身份守卫不符 | build前停止；保留原始失败 |
| `20261109T092018312571Z` | `builder_final_10_parameters`：`ValueError: Component has no parameters` | 原库/线路定义身份与14次接线调用已过；未保存修改工程，无build/sim |
| `20261109T105927241384Z` | v5已过全部Wire库存，原生SrvcCbl编辑前/后RowDefn一致性守卫拒绝 | 仅根CRC差异，含义未证；未保存修改工程，无build/sim |
| `20261109T111545271892Z` | 最小CRC诊断在删除其余76个Main顶层对象后首次观察根CRC变0，按设计停止 | snapshot0–34（35项）无差异；未编辑线路位置/Length，无save/build/run |

v4 run实际核对两个master线路定义/XML身份，原生RowDefn编辑前与原件一致；6ms/1µs求解/采样回读仅为配置证据。终态worker1、28.148s，观察到异常后正常quit，`remaining_owned=[]`、monitor错误null、cleanup错误空，原件/profile/父环境不变。manifest SHA`6393b32c33fce16cc63e8274c9ffa2c0dd718a887c7ec25c9b55a0b6950b08d5`；terminal SHA`4d035a963eb185df4e1ebfd63a6aac5490dac494140cce70a560dff3beb882ef`。

该次入口为`local_reference/a3_followup/finite_r_native_probe_owned_guard_v4.py` SHA`362fa0b54dd719ffc96db41e2cc780668f7556ad131a67e60ce326c9af3887ad`，builder为`.../native_reference_design/20261109T074056761817Z/builder_checked_v4.py` SHA`5182eec41ec459b8f418aa480b9d8abd3387e2d85df6f8bc2e7c4c1b543ec0e0`。它们保留为该次失败身份。

v5仅对本轮create_wire返回的精确Wire/已知iid省略不支持的parameters读取，最终集合严格相等；其他对象仍强读native参数，逐步保存身份。新driver`local_reference/a3_followup/finite_r_native_probe_owned_guard_v5.py` SHA`6beca649559638c15221dd16ebeca1717adbd7939d9dc81b85447afe3a3cd457`，builder`.../builder_checked_v5.py` SHA`ce894fec7178107cb51189b6a2c7007aea4cb026620dabd8195619ceb172bb4d`；独立AST审查确认控制/物理/接线/solver/保护不变。实际run`20261109T105927241384Z`已过Wire库存，但`Native SrvcCbl definition changed during Main-only editing`守卫停止，未保存修改工程/build/run。worker1、30.2399s，异常后正常quit、自有进程清空，源/profile/父环境不变；manifest SHA`47d246343b0458709fe78a77b4af307374425b3539a0739526e31ed12d73b439`，terminal SHA`575ad53b6572faa9ab35f913047537e50df90eb64606a65904a9063d5fec8005`。

独立核最新40项库存为1TLine+25UserCmp正常参数回读、14plainWire成功；31项manifest的hash/size全部相符。编辑前与原source一致；前/后唯一XML差异为根`Definition/@crc`从36752239变0，64参数、全部ID、内部paramlist CRC、布局/属性/拓扑均相同。原生CRC变0的原因尚未证明，不能直接称为普通序列化或已知物理变更。当前须先说明CRC元数据与有效定义的核验边界，再独立审查任何窄修订，不直接重跑或删除守卫。实际`.tlo`、源时序/单位/方向、零历史与波形仍缺，正式协议/候选未建立。

独立只读CRC研究位于`local_reference/a3_followup/integrity_review/20261109_crc_semantics_research_a9e612/`：`report.json` SHA`ea17d3c4bff90ae234fe3cd93c52cda94079254de28bbb93cbf1b5ddb71d1848`，`diagnostic_plan.json` SHA`c1523076af312eb8c041646bd91ef7db1c6b11d459a66ba50f77fe3caf5fcb4b`，manifest SHA`f3de89f4c117a7fa8b85d001b34b6f83304bc44615c6092338ad8d9aa1607931`。安装公共Definition.xml接口将返回字符串解析为新的客户端Element；7项内存检查通过，未运行native。XSD仅规定crc为required long，wizard的初始值为0；已读官方文档没有赋予“0即失效缓存”或“可忽略元数据”的语义，不能扩大解释。
已独立审查并实际执行最小分阶段CRC诊断：builder SHA`2fc58602f7614188b70e9c11970657a08350a054c3675274712a000f576f6590`、driver SHA`fd542bcb9d78dfb72d10bca7ae518390ce64b4b3c0d932a6826044a7d7f78ed8`。run`20261109T111545271892Z`的snapshot35紧接`delete_other_main_objects`（76个顶层对象批量删除）后首次观察根CRC 36752239→0，snapshot0–34及重复XML读取/dirty getter/库身份均未变，确认读取相同；其余定义内容仍无差异。该定位不确定是哪个删除对象或官方CRC语义，不能据此放松守卫。按设计DiagnosticStop，worker1/14.1266s，正常异常后quit、自有进程清空/monitor null/cleanup空，源/profile/父环境不变；未编辑line vertices/Length，无save/build/run。manifest SHA`089a2fa6cbfd5f1613d2f3fb4de9356632a74be6a5aeb2547e524f1920bdf7ff`，terminal SHA`578cd728916fc2e7374333395be0ac01b064b0b832b0055b8468d846eade0c5f`，诊断结果 SHA`3cb9e0e72a37a7cdf71a49eeebc85f2d3138f1f6c1332e1f0ef9655c853c5ba9`。 独立审计核66项manifest及37份XML（编号0–35加1份确认），0–34逐字节相同，35/确认恰为唯一根CRC字符串替换；报告`local_reference/a3_followup/integrity_review/20261109_actual_crc_diag_111545_08cd72/report.json` SHA`2a2dcc4a61d6d376741822f2f4c8cb007b5f9f7d094ec46adac3141b267d2caf`，审计manifest SHA`af0cc96e890d97b2f4b40c6202cca0dee0b8020137fe7d196f4089467f917eed`。

下一步拟定v6，仅在这一个已观测的批量删除边界逐字段严格核完整定义与唯一CRC转换，再将删除后的完整CRC0 XML作为严格基线；此后任何字段变化（包括save后CRC换值）仍须停止。尚未写v6代码，须另存独审，不称一般CRC语义、保存有效或数值等效已证明。


## B1：短路径加载成功，实际端口守卫拒绝

研究根目录D为`local_reference/two_level_pwm/matched_reference_research/20261109T080850088678Z_pscad_static_d5d66d/`。runner包R为`D/owned_runner_research/20261109T084022489231Z/`，公共守卫修订目录G为`R/guard_fix_v3/20261109T085722111717Z/`；D/R/G仅为此文路径缩写。

| run位置 | 实际停止点 | 结果边界 |
| --- | --- | --- |
| `R/native_probe/20261109T085000185753Z` | 创建组件期间原子日志replace遇WinError5；旧清理再因动态`row.Terminate()`调用报TypeError | 无build/run；缺完整terminal，事后独立CIM确认自有进程不存在；不称正常quit |
| `G/native_probe/20261109T091032482166Z` | 262字符工程路径`app.load`报FileNotFoundError，Python侧副本实际存在且hash正确 | 无工程句柄/build/run；修订后日志/清理正常收尾 |
| `D/n/20261109T091917405572Z` | 170字符工程路径已成功加载并创建组件；`Installed native port coordinates differ; re-route before build` | 实际端口与静态坐标假设不符，无build/run |
| `D/n/20261109T111717200520Z` | 仅抓取31个电气组件参数/端口和53项预期检查，23项坐标不符后按设计停止 | 无接线/save/build/run，不据此认证物理拓扑 |

最新run worker1、21.867s，观察到异常后正常quit，`remaining_owned=[]`、monitor错误null、cleanup错误空，源/profile/父环境不变。manifest SHA`ae06fe3bc55b29b653b82639469a2a9fab074aa353a195786ad675bd92f59aea`；terminal SHA`b0422836cb649a7cd330b25836bfcbd3491b8c217f631a346173cd95e918027c`。短路径成功支持旧加载失败与路径长度有关，但旧FileNotFoundError不被改记成功。

该次入口`G/b1_native_probe_short_path_v4.py` SHA`8d596142e44660f3449f3a40d79704155b9b3c521a6490d3606ea2b5b4f6eccc`；builder`G/builder_inventory_v2.py` SHA`a113419df5602b0146e3027fdfa77339b7baaaa58993f3652958b5d23ead0a77`。builder保持原控制/电气/通道69/31/46规格，只严格补齐donor top21+2Graph+2Curve全部25ID/类型，并只删除top21。原静态builder e93e70ab及库存保留不改。当前须按实际端口重新核线、另存修订并独立审查，不能略过守卫或直接重跑。

补充端口抓取builder SHA`87e6ea70b68fbd32a7bfc46b177a79d2c7378ac38f483f0ad58e93194977d27e`、driver SHA`994175a18afbded99460e03cbccaf0dadfa6266f1b66018b93699ba3334f9172`只增加实际坐标保存，并在原守卫/所有wire之前无条件停止。实际run`D/n/20261109T111717200520Z`为预期RuntimeError、21.4105s；正常异常后quit、自有进程清空、monitor null/cleanup空、源/profile/父环境不变。`native_port_capture.json` SHA`a3ab6c0197777eec75953bee59527b0ceb2180f7410a04480457988e54f458c8`，manifest SHA`46027d13cac184b7e051a9edbe571a514e68e791e329ceddca8354c0d3fae1b9`，terminal SHA`dacff8ff0d60c08efac859db5cc14c60d8e75755f8636867f86176e1ce5b72ec`。
实际source NA=(6,4)、NB=(10,4)，静态预期分别(5,4)/(11,4)，source ground仍(11,4)，原重合假设不成立；R/L/varrlc/电流表端口跨度2格，差分电压N2为y−2。不能统一缩放；下一修订须逐个原生端口布线并核电气图、正交性、源电压探针和ground实际连接，尚未创建/执行重连稿。


## 共用运行守卫与未完成项

3GiB启动/2GiB动态提交余量、RPC20s、build180s、run120s、监控总420s保持。每轮新目录、复制原件、真实用户profile双侧存在/hash相同、源和父环境核对，进程每次核PID/父PID/路径/创建时间并排除既有PID。

日志读用显式共享READ/WRITE/DELETE并及时关闭的reader；写端仅对WinError5/32/33作0.2s有界retry。真实短持锁/及时close可完成原子写，持续锁按设计失败；额外“reader始终持开仍能replace”强用例实际FAIL，原样保留，不泛化共享删除保证。清理改用显式WMI`ExecMethod_('Terminate',...)`并取ReturnValue；独立finally保证自有Popen句柄与terminal收尾，未知remaining不能写成空。真实终止测试仅作用于自建短命隐藏Python子进程，没有终止其他程序。

公共守卫最终源SHA`e87584f575584a2dff4a7a8a14a1549603424b5575b5f8e2ff69337e5f15a3be`。独立复核入口`local_reference/a3_followup/integrity_review/20261109_owned_guard_v4_e875_9b13c2/report.json` SHA`2ac1e7bceb1738f8c445b626882c28176a7678b84720c27e93530c8f5e9e3769`；manifest SHA`7fc3b85fa6f8a96b5497923914568fee615fc9510767ee2afb74512d8dd3f57e`。旧脚本、失败和强用例均保留，不以守卫通过认证电路或数值。

08:22UTC约2.282GiB不足门槛是历史；08:36:59UTC实测约10.28GiB后才顺序启动，资源不足已非当前阻塞。A3/B1最新两轮均终态，不能等待旧worker。当前分别卡在RowDefn一致性守卫与原生端口假设；未取得原生波形。B1原MathWorks2% FAIL、默认12及全部窗/阈值不变，完整同数学0.2s协议须待实际控制时基、全部门极/有效R/源/单位/TR初始历史核清后再冻。

## 交付与跨操作系统边界

26交付`9269350887a867aee2740fed04155ade8f8757be`已正常push，真实ls-remote相同。精确[CI42606454705](https://github.com/yu-yikai/PyCy_EMT_Lite/actions/runs/42606454705)终态failure，Ubuntu129123587852/Windows129123588150均runner_id0、steps空；各check注释确认账户billing lock，未执行任何测试/test_count=null。精简[CI证据](ci_9269350.json) SHA`f84ac79906b409131616b71c0ab52dab6f31967b3e583dc014e4d138b0426a85`，7份原始API响应hash均核。F1局部受阻，不机械轮询该终态或借本地1236/商业PASS称跨OS通过。
