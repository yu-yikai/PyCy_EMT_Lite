# 恢复与下一步

2026-11-16：节点排序单变量已实建并按预设NOT_ACTIVATED门停止，Run0；原完整双h仍未过2µV。新增完成9、C1进行中、目标active。

入口：[节点排序实建记录](experiments/c1_node_ordering_build_attempt_20261116.json)。checkpoint为本次提交前61647b6；与实际Git及结束检查点交叉核对。

1. 先读五状态并核分支、HEAD、工作区和实际远端。最新8170已exit1终态、Build1/0errors、Run0、正常quit/owned[]；旧98913/25165/34509等也已终态。不要轮询或重启旧句柄/driver。
2. 读取新记录及ROOT/独立闭场收据。实际45设置仅optimize_nodes True→False，19有向角色图、28 NODE绑定和14非地语义节点保持；未观察到预设重编号，按门阻Run。它不是数值FAIL，也不能证明内部优化器没有效果。全部81非OUT保留，无OUT/INF数值输出；新normal-oneRun闭场/raw/numeric入口从未调用，不应对Run0尝试这些入口。
3. 先做本机R2025a/Simscape同物理参考的最小可行性研究：已有真实B1/25 -batch链和标准双向variable_resistor源码证据。核完整端口/单位/Rmin/热端口/依赖、浮置DC初值与Solver Configuration局部梯形逐步方程，保持16元件物理、100µs/5µs控制、双h完整窗/45量/原预算。新来源/参数/初值/方向/求解器/时序/比较窗/阈值在新native和候选前另固定；安装和旧Run不能代替新模型、当前license或全门。
4. 两处小可读性改进已完成：中英README补同终端恢复图窗方法；27号摘要从现有参数格式化，默认stdout及仿真计算不变。新的113文件快照见tasks.current_source_snapshot；旧快照有且仅有27号摘要hash变化，旧native/分析器不可绕过其固定源码守卫。
5. 原2µV FAIL及旧实验全记录保持。排序包已耗一次Build且Run0，不重试/搜索通过排列。现live context/driver固定05dd455；文档提交后不要在新HEAD直接重跑。后续只读复核先用精确旧Git/快照的归档准入，不改旧包；新native另封当前HEAD/输入/资源/owned/profile守卫。F1账单锁仅既有记录，本轮无新CI观察。

正式Python仍113个，27号仅摘要改动、其余112个及依赖不变；新的源码快照已保存。锁定同步/Ruff/mypy/27号6001点独立运行通过，1300含slow为既有全量，本轮未重跑。所有商业原件/研究脚本在忽略目录。

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
