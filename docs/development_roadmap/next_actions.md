# 恢复与下一步

日期2026-11-06（Asia/Shanghai）。恢复先读tasks/progress/decisions/validation_status，核分支、HEAD、工作区、git log和真实远端。记录中的checkpoint `54374d5d9caf480d765b18faacea763054304f27` 是记录时已知提交，远端及后续文档须另核，须与后续历史交叉核对；不覆盖用户工作，不强推，不操作main。

## 当前事实

工作分支codex/emt-examples-longterm；正式新增19/20/21/22/23/24共6项完成，既有02补参考另计，既有12波形FAIL保持。
24完整实现提交02044768579ba083d1fb526786922e770cc2e7c6，A4本阶段23/24范围完成。
原源—变压器—线路—负荷整链尚未交付，明确转入D0，不能把24无线路网络当作该目标完成。

最终本地1179 passed490.61s（XML490.603，含slow），日志.tmp/longterm/a4b-final-full-pytest.log和a4b-final-full-tests.xml。
锁定同步27包、Ruff全范围、mypy39文件通过；24九专项76.926s、独立Agg100001点完成。
正式reference run20261106T041347000Z，58899/76502点自身38项PASS；最终candidate compare run20261106T041603177270Z，
0.5µs两窗19量38项PASS，maxLV20.17655V/HV205.91860V/maxNR.000246239。案例README保存复现及全部hash。
原1µs商业startupFAIL、资源/最小步长/guard失败保留。所有本轮Python/MATLAB/monitor进程均终态，无后台运行。
核心pycy_emt_lite相对原main无改动；没有新依赖、通用约束或自动二极管框架。

90b2fcd真实双OS全步骤成功只覆盖22；23/24跨OS尚未验证。
已确认e51c1f1与后续旧run因GitHub账户账单锁而在runner启动前失败，不能改称代码断言失败。
本批已正常推送到1423c7d；精确run42162705728两个job均runner0/steps空，实际billing lock启动前失败。
证据experiments/ci_1423c7d.json，远端test_count=null；不是本地测试或数值断言失败。

## 本轮下一步

1. F1局部blocked：最新1423c7d精确run42162705728已真实终态failure，两job因账户billing lock未启动任何步骤，原始7份响应/hash及注释见experiments/ci_1423c7d.json。无后台CI监控，不继续轮询相同终态，不通过代码/空提交/重复push解决。外部账户确认解锁后，优先对这个覆盖24的run在授权Actions界面选择Re-run all jobs（或有相应授权工具时POST /repos/yu-yikai/PyCy_EMT_Lite/actions/runs/42162705728/rerun），再按精确head/attempt核两系统全步骤。旧e51c1f1记录保留但只覆盖到23；当前环境无gh，不擅自操作账单或提取凭据。正常必要开发里程碑仍可push，CI状态须真实分开记录。

2. B2已取得并真实运行原SPS同步Buck，先读experiments/synchronous_buck_reference_probe.md。现仅有输出/源电流/占空比，储能初始化、实际门极和体二极管电流未核实；日志override不能新增未标记内部信号。building-simulink-models要求model_edit而当前无此工具，未改信号属性或结构。取得工具后在独立副本补日志，核完物理/控制一致性才考虑冻结协议。原连续PI/外部限幅/Natural PWM也与现离散控制不同，维护成本较高；继续寻找更简单的受控双向开关原参考，禁止用自动换流框架填补。普通MATLAB上下文的prefdir/5201启动失败已由正常许可上下文加独立MATLAB_PREFDIR解决，准确命令见probe，不反复重跑成功的默认结果。
3. D0研究已提交54374d5，当前已找到并真实运行本机官方power_gui完整网，先读[专项调查](experiments/source_line_transformer_reference_probe.md)。实际顺序是源→150km/两π段线路→线性T→固定阻抗负荷，另保留全部RL补偿/等值支路。默认run20261106T044524416Z：50ms/219点/12状态，ode23tb、7.2005767s、exit0、Dirty off，原件hash不变；只记runnable，不计第7例。原始MAT/CSV/analysis/net及输入快照保留local_reference/d0_research/default_runs/20261106T044524416Z，不重跑默认sim。

   精确detailed支路表及独立物理相量/初值已核：12态相量最大相对差3.839e-13；线路双曲修正实际生成三条约202M/101M/202MΩ shunt，不能按SpecifyConductance=off省略。优先基础R/L/C与理想T，保持励磁接点/所有支路及公开初值参数。原网Scope无保存波形，本次仅开启tout/xout捕获；C/D明确了Ub1/Ub2/i_eq/i_Load映射，后续状态线性投影须如实标注。接下来在候选前冻结协议，再做参考自身精化和实现；相量核验不替代时间域商业比较，当前没有候选。A3同数学Bergeron参考仍缺，PSCAD simpleac为耦合/带事件原网，不能凭取得原件替代相容性。A4b已完成，无需重复成功sim或全量测试。

4. B1仍失败：146a279固定NRMSE2%限值，实际2.66%–2.72%，features通过。研究适配须先明确新的控制/器件协议，隔离时序、压降与积分差别，不拟合时移/幅值、不为现有失败放宽标准。C1依赖的控制链保持后置。

## 本机命令与环境

稳定Python3.14.5位于`.tmp/venv-py3145/Scripts/python.exe`。PowerShell先设置：

```powershell
$env:UV_CACHE_DIR="$PWD/.uv-cache"
$env:UV_PYTHON_INSTALL_DIR="$PWD/.uv-python"
$env:UV_PROJECT_ENVIRONMENT="$PWD/.tmp/venv-py3145"
$env:UV_PYTHON_DOWNLOADS='never'
uv sync --locked --offline --python .uv-python/cpython-3.14.5-windows-x86_64-none/python.exe
$env:PYTHONUTF8='1'
$env:MPLBACKEND='Agg'
$env:MPLCONFIGDIR="$PWD/.tmp/longterm/mpl"
$env:OPENBLAS_NUM_THREADS='1'
```

其他机器正常`uv sync --locked`，不依赖忽略缓存。默认沙箱Temp有权限问题，全量pytest使用新的仓库内`--basetemp=.tmp/longterm/pytest-<唯一ID>`，先验证目标绝对路径位于仓库且不存在，避免pytest清理旧内容；可加`-p no:cacheprovider`避免旧cache权限warning。常规检查Ruff包括pycy_emt_lite/examples/tests/validation，mypy检查包，pytest保留slow。新代码/失败才重跑必要范围，已经通过后不机械重复全量。

如Git因当前身份拒绝ownership，读写命令可加`-c safe.directory=D:/VibeCoding/PyCy_EMT_Lite`，子进程则仅当前进程环境设置：

```powershell
$env:GIT_CONFIG_COUNT='1'
$env:GIT_CONFIG_KEY_0='safe.directory'
$env:GIT_CONFIG_VALUE_0='D:/VibeCoding/PyCy_EMT_Lite'
```

必须正斜杠，不写全局配置。GitHub直连曾超时，已有系统代理可用；忽略helper`.tmp/longterm/git_with_system_proxy.py`只读取系统配置、允许本分支普通push/ls-remote、不打印凭据、不更改remote/持久配置。按执行权限机制审批网络写操作。

各case重现：`uv run python -m validation.cases.<case>.compare`，case名cascaded_rc/rc_charging/nodal_analysis/earthing/transmission_line/transformer_t_equivalent/three_phase_transformer_chain；缺真实参考应报错，不生成伪数据。MATLAB从根目录`clear export_reference; addpath('validation/cases/<case>'); export_reference(pwd)`，需合法许可；同名函数切换须clear。原件/原始日志/波形/缓存保留local_reference。

长期目标尚未完成，继续D0参考先行、F1外部恢复及B2备选独立研究；不声称无实际执行环境时后台继续。
