# 原生状态块守卫勘误

2026-11-06，65d89bb之后、首次候选商业数值比较之前。原manifest、parameters和acceptance_plan保持原字节，
本补充只替代其中“生成StateSpace块的AbsoluteTolerance应为auto”的实现类型假设。
物理参数、初值、求解器设置、步长、比较窗、14量映射及所有误差限均不改变。

## 新证据及原失败

正式baseline运行20261106T052652719Z已完成原网50 ms，保存5023个原生时刻、12态和完整SimulationInput/Output。
随后守卫读取不存在的AbsoluteTolerance字段而停止，尚未运行refined或发布正式参考，也没有候选商业比较。
原MAT SHA-256为`15a9a5c9d1acf78415346a549d1964c0c948fd786d1df9699679caa550c039ba`。
原运行目录、输入/脚本快照和错误日志保留；这次是抽取守卫失败，不能改写成仿真数值失败。

只读compile查询发现路径`power_gui/powergui/EquivalentModel1/State-Space`实际为`S-Function`，
函数是`sfun_spid_contc`，没有AbsoluteTolerance块参数。RuntimeObject确认12个连续状态，
CompiledSampleTime=[0,0]；4个函数参数与3个UI字段是不同计数。块路径名不能证明其实现类型。
安装实现身份为：

| 文件 | SHA-256 |
| --- | --- |
| sfun_spid_contc.mexw64 | a87689e01299106db2e40956dcd024f770a309663bf91cd18a94aeb75c6976dd |
| sfun_spid_contc.c | eeddbcc6613837f74a8cbaf238d79d7c8ea6fe0094b8e845ef5f3fc558052074 |

它声明连续状态，安装C源码没有逐态AbsTol设置调用；其中UNDET_ABSTOL用于未定量及状态依赖的一致性检查，
不能当成连续积分误差控制。早先查看的`sfun_spssw_contc`不是本模型实际运行函数，不作为本守卫依据。
[R2025a AbsTol文档](https://www.mathworks.com/help/releases/R2025a/simulink/gui/absolutetolerance.html)说明模型容差与块覆盖的关系。
由安装源码及文档推断它使用模型级容差，但本证据不声称已读取MEX运行时的逐态AbsTol数组。
参考绝对精度仍必须由固定物理相量审计和真实双次细化同时证明，不能只凭这个推断放行。

## 修正后的严格守卫

导出核实际状态块路径、S-Function类型、函数名、无AbsoluteTolerance字段、安装MEX/C身份，
并记录实际参数表达式和12态证据；若身份不同即停止。禁止向原块添加字段或修改块属性。
保存实际SimulationInput及SolverInfo，核ode15s、原RelTol/AbsTol、AutoScaleAbsTol=off、InitialStep和MaxStep。
完整网络分析、所有物理对话参数、初值、原模型字节和依赖身份继续核验，不能仅核函数名。
compile和只读掩码回调可能使内存模型Dirty=on；须如实记录、终止编译并不保存，另核磁盘SLX字节未变。

允许在新的独立导出目录**只读复用上述已完成baseline MAT**，因为本勘误没有改变其任何运行设置。
必须核其原MAT/hash、原输入/脚本快照、实际求解配置、完整50 ms及原初值，再重新抽取和审计；
新provenance同时记录原运行来源及本次抽取脚本/补充协议，不能称为重新仿真。
refined仍需按原冻结设置真实运行完整50 ms；两组全部14量、两完整窗的自身细化和独立sample/PWL预算全过，才发布。
原生重复时间点仅在对应全部归一化信号精确相同时可合并，记录数量并保留原始状态；异值重复点停止处理。

本补充须单独Git提交后才继续正式导出；导出与比较适配器同时核原三文件及本补充的LF文本身份。
