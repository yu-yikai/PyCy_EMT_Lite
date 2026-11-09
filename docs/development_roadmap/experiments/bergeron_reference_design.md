# A3：有限电阻线路的参考设计

2026-11-09。已选定来源、完成独立解析和原生API静态核查，探针输入快照已保存。**本次没有启动PSCAD、执行建模脚本或仿真；尚无有限R波形或PyCy候选。**
前次[工具链实跑](pscad_toolchain_smoke.json)只验证了官方电压分压教程，不代替本线路参考。

## 来源和明确的改动

采用本机官方`Lightning/Steep_Front.pscx`中的完整`SrvcCbl`线路定义。原宿主是雷电/避雷器网络，本次参考改用简单电源与电阻负荷，必须称为派生参考，不能称原官方完整算例。

原件90346bytes，SHA-256为`6c59ee7a59e9b356167b3206bd6b27b7a471753b02b3c853753c5f0dc2921a39`。
保留`SrvcCbl` RowDefn及其全部字段；只改原线路实例长度0.01km→10km，保留原Name、100kHz参数频率、单导体、双端局部连接。
画布位置与外部接线也明确改变；删除原Main其他76个顶层对象，未用的定义仍留在本地项目中，不放入教学代码。

| 原活动字段 | 保留值 |
| --- | --- |
| NCond / PU | 1 / 2（手工输入波阻抗和传播时间） |
| RTP / TTP / ZTP | 0.01Ω/m / 3e-8s/m / 201Ω |
| LONGLN | 0；不自行再作长线修正 |
| BDamp / Interp1 / Inflen | 0 / 1 / 0 |

据此得到的**名义值**为R=100Ω、Z0=201Ω、τ=300µs。它们仍需由原生生成的`.tlo`、源码和运行记录确认。
[官方版本记录](https://www.pscad.com/webhelp-pscad-v5.1.0-ol/Log.htm)列有手工YZ/长线修正、损耗频率及插值/无反射选项的后续修复，不能从本机5.0模型字段直接推断运行行为。

## 探针的输入和观察量

```text
e(t) -- Rs=100Ω -- k -- 有限R SrvcCbl -- m -- RL=400Ω -- 地
```

e(t)在0–0.5ms为0，0.5–0.6ms从0连续升至1000V，之后保持1000V；负时间历史为零。探针步长/输出间隔均1µs，终止6ms。
原生用现有time-sig→upramp→source_1（理想、外控DC、Tc=0），不用自写Fortran。连续斜坡保留波前和反射，也便于全窗比较；不能删去斜坡拐点或延时到达点。

保存六路原生通道：控制输入Mag、实际源电压Vs、两端电压Vk/Vm、送入线路Ik、线路流向负荷Im_out。全部Scale=1，原始单位保留kV/kA，后续明确乘1000，接收端流入线路电流另取负号。
实际Vs必须核对控制输入和输出时间轴，不能假设无一拍延迟。电流方向另用`Ik=(Vs−Vk)/100`、`Im_in=−Vm/400`交叉检查；`.inf/.infx`的通道编号不能按名字排序猜测。

独立有理数解析给出以下**条件性设计检查**，不是商业波形：

| 名义区间或极限 | 预期量 |
| --- | --- |
| 0.6–0.8ms首个发送平台 | Vk=693.251533742V；Ik=3.06748466258A |
| 0.9–1.1ms首个接收平台 | Vm=700.780049494V |
| 0.9–1.1ms中间电阻反射后的发送平台 | Vk=735.094495981V；Ik=2.64905504019A |
| 最终DC极限 | Vk=833.333333333V；Vm=666.666666667V；Ik=−Im_in=1.66666666667A |

首个接收波前名义上在0.8ms；中间R的同端反射也在此时返回，负荷反射约1.1ms返回发送端。这说明单一衰减系数不能代替有限R模型。名义误差递推谱半径约0.25488，仅说明所选窗口足以观察收敛，不证明原生精度或最后采样点。

## 已准备的运行及资源状态

只用公开API，在独立副本中保留TLine实例2024913992。删除前核原77个对象ID；保存原/运行时/编辑后RowDefn与实际解析的master资源。保存后与原定义不一致就停止，不能继续build。编译目录必须位于本轮run内。
初版builder及静态记录保留不改；`builder_checked.py`仅增加上述保存一致性硬检查。所有组件参数已用安装版真实表单离线编码，项目枚举映射和Python语法也已核查；这些均不能替代实际建模。

忽略目录`local_reference/a3_followup/native_reference_design/20261109T074056761817Z/native_probe/20261109T075010503354Z/`为**仅准备**记录：5项清单和5个协议文件引用均独立核对。2918506496bytes（2.7181GiB）可用提交量低于3GiB启动门槛；`native_started/builder_executed/sim_called`均false，输入快照未被原生软件消费。没有worker或project目录，不存在可等待的原生任务。

资源恢复后先核脚本与输入hash，再用本机Python3.13运行`local_reference/a3_followup/finite_r_native_probe.py`；无参数才会尝试一次原生探针，`--prepare-only`始终只保存快照。每次新目录，不恢复或覆盖此准备目录。
沿用新会话归属核验、原件/profile/父环境核对、3GiB启动门槛、2GiB动态余量、普通RPC20s、build180s/run120s、总420s和精确自有进程清理，不修改全局PATH/ATS/设置，也不触用户MATLAB。

下一步必须先取得实际参数、完整原生波形、初末时间、零历史及源电压/方向证据，再在候选出现前固定正式窗、误差限、参考自细化和候选步长。两无损半线加三R的数学等价仍见[原调查](bergeron_reference_followup.md)；不创建新线路核心类。

## 证据入口

- 独立物理/来源：`local_reference/a3_followup/reference_design/20261109T073906Z_physics_7ea4ab/final_manifest.json`，15项，SHA`16a7856cadfa48aa8bea03e9b127cc2e695e1ee9d76ac8c80a2eee4d60f2eb54`。
- 原生API、codec及端口静态记录：`local_reference/a3_followup/native_reference_design/20261109T074056761817Z/`。
- 主审独立hash/有理数检查：`local_reference/a3_followup/root_design_audit/20261109T075249916256Z/report.json`，在03a913e版本核15项物理库存、8输入、8 API输入、5准备库存、5协议引用及Buck的11产物/37输入。原版源码、模型和所有探针脚本均仅本地保存。
