# 恢复与下一步

日期2026-11-06（Asia/Shanghai）。恢复先读tasks/progress/decisions/validation_status，核分支、HEAD、工作区、git log和真实远端。记录中的checkpoint `02044768579ba083d1fb526786922e770cc2e7c6` 是记录时已知提交，远端及后续文档须另核，须与后续历史交叉核对；不覆盖用户工作，不强推，不操作main。

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
本批实现及状态形成正常里程碑推送，精确HEAD的CI须据真实观察另记，不借旧HEAD成功。

## 本轮下一步

1. e51c1f1已正常push，精确run42154476032因账户billing lock启动前失败，真实注释与raw见experiments/ci_e51c1f1.json；两job没有运行任何步骤。F1局部blocked，等待外部账户解锁，不通过改代码、空提交或重复push解决。确认解锁后，在授权Actions界面对同run选择Re-run all jobs（或有相应授权工具时调用POST /repos/yu-yikai/PyCy_EMT_Lite/actions/runs/42154476032/rerun），再按精确head/attempt核对两系统全步骤。当前环境无gh，公开API只读取证据，不擅自操作账单或提取凭据。未来正常必要开发提交仍按里程碑push；账户受限期间其CI也须准确记录，不能借旧HEAD成功。
2. B2已取得并真实运行原SPS同步Buck，先读experiments/synchronous_buck_reference_probe.md。现仅有输出/源电流/占空比，储能初始化、实际门极和体二极管电流未核实；日志override不能新增未标记内部信号。building-simulink-models要求model_edit而当前无此工具，未改信号属性或结构。取得工具后在独立副本补日志，核完物理/控制一致性才考虑冻结协议。原连续PI/外部限幅/Natural PWM也与现离散控制不同，维护成本较高；继续寻找更简单的受控双向开关原参考，禁止用自动换流框架填补。普通MATLAB上下文的prefdir/5201启动失败已由正常许可上下文加独立MATLAB_PREFDIR解决，准确命令见probe，不反复重跑成功的默认结果。
3. 当前下一任务D0：先实读04路线图、tasks.D0及24 README，明确24没有线路。只读本机R2025a示例目录与官方版本化来源，寻找“源—线性变压器—实际线路段—固定负荷”完整可运行网络；先核拓扑、源/线参数、绕组/线量、初值、物理尺度与工具依赖。优先复用当前源/T/Pi或现有分段线，不为数量拼接23/24或改变官方物理后伪称原参考。找到原网后按真实运行/精化/独立推导/实现前协议流程；尚无reference时不写候选或计数。结构编辑须使用building-simulink-models的model_edit，当前无该工具，不绕过。A3仍缺同数学Bergeron商业参考，50T不能代替。A4b已完成，无需重复任何成功sim/全量测试；若要复核其报告用原运行inputs，协议LF规范与原字节hash分开。

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
