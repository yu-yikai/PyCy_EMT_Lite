# 恢复与下一步

2026-11-12目标active。恢复先读五状态文件，核实际分支、HEAD、工作区与远端。
checkpoint为本次记录前的4aff99c3；按实际Git历史交叉核对，不自称包含自身提交。
开发分支codex/emt-examples-longterm常规提交/里程碑推送已授权；不改main、不强推、不覆盖用户文件。
C1仍in_progress，正式新增9项；本轮仅构建已终态，不恢复或重复旧run。

1. 先读[源电流只构建记录](experiments/c1_source_current_build_only_20261112.json)和[参考设计](experiments/c1_openloop_reference_design.md)。
   真实PSCAD编译0错误，原驱动因构建阶段无INF而非零停止；独立实际审查另证DC负BA读在MainOut、其PGB仅在MainDyn，输出链未获准入。原生会话受控退出，自有进程清空。
   本轮无Run/OUT数值，NOT_OBSERVED；新身份是三相A表与负源BA，原CUR历史不能替代同刻计量。
2. 下一步另冻Map/实际PGB绑定、仅DC本地PGB的Fortran→Dsout调度及已观察的−(CBR...)精确模板，再做独立build-only；不得只补INF重跑或直接Run。
   任何后续运行都须另冻执行/数值合同，不能把编译或MainOut计量准入当商业波形验收。
   旧[理想支路结果](experiments/c1_ideal_branch_diagnostic_20261112.json)和[测量诊断](experiments/c1_dc_measurement_diagnostic_20261112.json)全部FAIL保持。
   去表后B=S为rank1，旧A压降/秩2门不适用；不放宽原源、桥、KCL/功率/能量预算或引入接地/电阻追认失败。
3. 合格后再冻结完整开环协议、参考细化及最小候选；实际正弦约定仍为sin(ωt+Ph)、正abc，cos-Park角ωt−π/2。
   复用CaseDefinition链、现有12/18与controls/vsc.py，沿开环→已知角dq电流→PLL→P前馈/Vac→真实DC电容Vdc及扰动推进。
   固定DC不认证Vdc，刚性电网端不认证Vac调节；D1planned，控制/合闸/扰动/故障范围未完成。
4. F1旧CI43060348386在runner前因账单锁失败；外部恢复后补双OS，不轮询同终态或空提交绕锁。

113源码/依赖未改，复用前次1300含slow/锁定/Ruff/mypy39，不称本轮重新测试。
原件、派生定义、原生文件和研究脚本留在忽略目录；结束前同步证据、提交及下一步。

## 本机命令

稳定Python3.14.5：`.tmp/venv-py3145/Scripts/python.exe`。下列离线缓存仅适用于本机，其他机器正常`uv sync --locked`。

~~~powershell
$env:UV_CACHE_DIR="$PWD/.uv-cache"
$env:UV_PYTHON_INSTALL_DIR="$PWD/.uv-python"
$env:UV_PROJECT_ENVIRONMENT="$PWD/.tmp/venv-py3145"
$env:UV_PYTHON_DOWNLOADS='never'
$env:PYTHONUTF8='1'
$env:MPLBACKEND='Agg'
$env:MPLCONFIGDIR="$PWD/.tmp/longterm/mpl"
$env:OPENBLAS_NUM_THREADS='1'
uv sync --locked --offline --python .uv-python/cpython-3.14.5-windows-x86_64-none/python.exe
uv run --locked --offline ruff check pycy_emt_lite examples tests validation
uv run --locked --offline mypy
uv run --locked --offline pytest
~~~

pytest指定新仓库内`--basetemp=.tmp/longterm/pytest-<唯一ID>`，先核路径位于仓库且不存在，可加`-p no:cacheprovider`。
保留slow；仅有新代码/失败/未解疑点才运行对应检查和必要完整回归，日志/XML不覆盖旧结果。
默认教学执行不读商业归档；`finite_r_bergeron`比较只读已核本地PSCAD归档，不启动native。
商业比较入口为`uv run --locked python -m validation.cases.<case>.compare`；26/27的特殊参考范围见各case README，
不套用其他case的MATLAB导出命令。第三方原件、波形和研究脚本保留忽略的`local_reference/`。

Git ownership仅用单命令`-c safe.directory=D:/VibeCoding/PyCy_EMT_Lite`；子进程仅当前进程设置
GIT_CONFIG_COUNT/KEY_0/VALUE_0，不改全局配置。已有系统代理helper
`.tmp/longterm/git_with_system_proxy.py`可传git参数；仅本命令读取系统现有代理并脱敏，不持久改网络设置。
结束当前执行前同步任务/证据/提交/下一步；不声称无环境时会后台继续。

## 历史证据边界

旧暂停中断全量不作通过；最新1244来自后续独立完成的运行。08:22UTC低于3 GiB时只准备/未启动，
后来资源满足后才顺序实跑；旧资源中止、A3 CRC/v6 save、B1端口等失败全保留，不再列为当前阻塞。
A3 v7严格允许单次观察CRC转0、保存后完整源定义恢复，不忽略CRC或推广一般语义。
B2 callback/load_system研究没有证明语义等价或内存收益，不以未测替换重跑合格参考。
