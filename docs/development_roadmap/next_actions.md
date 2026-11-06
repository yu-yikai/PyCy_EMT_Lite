# 恢复与下一步

日期2026-11-06（Asia/Shanghai）。恢复先读tasks/progress/decisions/validation_status，核分支、HEAD、工作区、git log和真实远端。记录中的checkpoint `e51c1f1881edcc4f4d53c5f9b166814c9dd8e3f8` 是本次已知推送提交，须与后续历史交叉核对；不覆盖用户工作，不强推，不操作main。

## 当前事实

工作分支`codex/emt-examples-longterm`。新增19/20/21/22/23共5项完成；既有02补真实参考另计；既有12整体波形FAIL保留，不能因features或软件测试通过改写。23协议预提交0ec7239，完整实现`91dbad6bb77af24d1a548a6d0943930c4bcce40f`。A4a只覆盖线性T等效，A4剩余三相接法/组合仍需独立可运行参考。

到23本地完整**1170 passed，384.08 s**（含slow），日志`.tmp/longterm/a4-closeout-pytest.log`、`a4-closeout-tests.xml`。锁定同步、Ruff全范围、mypy39文件通过。原18教学脚本已有独立执行证据，本次23独立Agg通过，共19脚本。23新真实比较run20261106T025650374531Z，报告和图在local_reference/transformer_t_equivalent/comparison_results；两窗×七量通过，maxV0.697mV/maxI0.304mA/maxNRMSE7.29216e-6。报告及来源详见case README。原模型与原始波形忽略，不上传。

90b2fcd真实run41809969999的Ubuntu/Windows全步骤均success，2026-11-06在线复核；与80ba91c同代码，覆盖22。旧CI不覆盖23。旧80ba91c因同批历史skip指令未观察到CI，保留历史，已由90b2fcd补足，不再重复调查。

## 本轮下一步

1. e51c1f1已正常push，精确run42154476032因账户billing lock启动前失败，真实注释与raw见experiments/ci_e51c1f1.json；两job没有运行任何步骤。F1局部blocked，等待外部账户解锁，不通过改代码、空提交或重复push解决。确认解锁后，在授权Actions界面对同run选择Re-run all jobs（或有相应授权工具时调用POST /repos/yu-yikai/PyCy_EMT_Lite/actions/runs/42154476032/rerun），再按精确head/attempt核对两系统全步骤。当前环境无gh，公开API只读取证据，不擅自操作账单或提取凭据。未来正常必要开发提交仍按里程碑push；账户受限期间其CI也须准确记录，不能借旧HEAD成功。
2. B2已取得并真实运行原SPS同步Buck，先读experiments/synchronous_buck_reference_probe.md。现仅有输出/源电流/占空比，储能初始化、实际门极和体二极管电流未核实；日志override不能新增未标记内部信号。building-simulink-models要求model_edit而当前无此工具，未改信号属性或结构。取得工具后在独立副本补日志，核完物理/控制一致性才考虑冻结协议。原连续PI/外部限幅/Natural PWM也与现离散控制不同，维护成本较高；继续寻找更简单的受控双向开关原参考，禁止用自动换流框架填补。普通MATLAB上下文的prefdir/5201启动失败已由正常许可上下文加独立MATLAB_PREFDIR解决，准确命令见probe，不反复重跑成功的默认结果。
3. A4a已验收，不为重规划重复修改它；A4其余三相/组合与A3 Bergeron须先取得同数学方程的商业参考。50T通过不能代替Bergeron。
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

各case重现：`uv run python -m validation.cases.<case>.compare`，case名cascaded_rc/rc_charging/nodal_analysis/earthing/transmission_line/transformer_t_equivalent；缺真实参考应报错，不生成伪数据。MATLAB从根目录`clear export_reference; addpath('validation/cases/<case>'); export_reference(pwd)`，需合法许可；同名函数切换须clear。原件/原始日志/波形/缓存保留local_reference。

长期目标尚未完成，继续F1本批与B2/后续独立参考任务；不声称无实际执行环境时后台继续。
