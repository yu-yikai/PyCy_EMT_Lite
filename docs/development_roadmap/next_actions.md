# 恢复与下一步

2026-11-16：同物理Simscape400µs短探针真实sim1、双路数值通过且闭场。新增完成9、C1进行中、目标active。入口：[短探针数值记录](experiments/c1_simscape_short_run_20261116.json)。checkpoint为提交前1a9a5bd，恢复先核实际Git/远端和结束检查点。

1. 先读五状态并核分支/HEAD/工作区/远端。45940已exit0，58747已exit1且sim0；所有旧MATLAB/PSCAD会话均终态，不轮询或重启已消耗包。当前113源码快照仍fa156，其余历史范围不扩大。
2. 原5µs/100µs控制、浮动DC/接地AC、19支路参数和原全部数值门保持。新57量原Time及Clock与tout逐位相同，各81点，原始MAT可恢复；不要用理想时间替换CSV中心或用控制命令替代实际R/i/v。
3. 下一步先另冻完整0.2s双h的构建/执行/导出与时间协议。回读两h求解、5µs门极/100µs参考和采集末点，再分别有界Run；沿用原完整窗口/全部预算及独立复算，禁止从本短探针推断完整资格。
4. 原PSCAD完整共模FAIL保持。完整参考合格前不实现教学候选，不删首末点/换相点或改阈值；BE仅诊断。首次Decimation类型读取失败及0B序列化报告均留存，修复仅本地研究工具。
5. 正式代码和依赖本轮未改，无新全量测试；1300含slow为既有结果。F1精确c3fdf79的CI43825501731账单锁/runner0已终态，外部解除后才补跨OS，不重复触发。教学继续复用CaseDefinition链，不加公共框架或重复算例。

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
