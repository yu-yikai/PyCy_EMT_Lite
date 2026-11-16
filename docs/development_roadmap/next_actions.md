# 恢复与下一步

2026-11-16：完整两h模型编译及结构独审通过；5µs完整Run资源中止，细档未启动，尚无完整波形或数值资格。新增9、C1进行中、目标active。入口：[完整模型与资源中止记录](experiments/c1_simscape_full_resource_stop_20261116.json)。checkpoint为提交前457ba4e，恢复先核实际Git/远端和结束检查点。

1. 先读五状态并核分支/HEAD/工作区/远端。43696已终态，native exit-1、owner[]；66960/35474编译会话均exit0。所有旧会话不再轮询或重启；缺report不能把sim调用数记0。
2. 原生门仍300s、private6GiB、pre可用commit3GiB/运行floor2GiB。本次pre5.038GB仍中止，事后约5.098GB且已有MATLAB未动。先在实际用户环境只读观察资源明显改善；建议新ROOT启动前额外留足8GiB可用commit，不放宽原门，不关闭未授权已有进程。
3. coarse包已消耗；fine未消耗但绑定旧457 HEAD，checkpoint后均不可直接运行。旧准备器也硬绑定457。以新HEAD另封准备器/包，区分历史构建HEAD和本次执行HEAD，按未变113源码/原参数重新准入已审SLX，不改旧包/失败。5µs正常闭场后才运行2.5µs。
4. 保持原100µs参考、5µs门极、物理/初值/方向、19门及辅助2µV。完整57量原Time/Clock/tout位证明、40002/80003点含尾点、四窗/六周期/全部pair门均须真实通过。先normal closed/raw准入再用已独审v2离线worker（1800s/private6GiB、available physical3→2GiB）分析；本轮没有运行此worker或测其全N资源。
5. 完整参考合格前不实现教学候选。原PSCAD共模FAIL、400µs Simscape PASS和全部审查/资源失败限域保留。113正式Python与依赖未改，1300含slow属既有结果；F1精确c3fdf79的CI43825501731账单锁已终态，外部解除后补验。继续复用现有链路，不加公共框架或重复算例。

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
