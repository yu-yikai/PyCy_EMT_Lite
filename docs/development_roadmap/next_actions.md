# 恢复与下一步

2026-11-16：同物理Simscape短探针已完成建模/编译及完整结构准入；尚未Run。新增完成9、C1进行中、目标active。入口：[本轮建模记录](experiments/c1_simscape_short_build_20261116.json)。checkpoint为本次提交前fbfc278，恢复先交叉核实际Git/远端与结束检查点。

1. 先读五状态并核分支/HEAD/工作区/远端。63496已exit0终态；87656编译通过但metadata不完整，26757配置失败，首包预检启动0，全部保持。不要轮询/重启旧句柄、driver或已消耗包；76308及旧PSCAD会话也已终态。
2. 最终v5实际80模块/SID/参数与端口、19支路/14非地节点、控制图、8编译采样率、29日志端口通过。113源码快照仍为tasks.current_source_snapshot（fa156）；27号c3fdf79摘要小改已另验收，其余112及依赖不变。不要让新执行绕过旧参考包固定HEAD/hash守卫。
3. 下一步另冻单Run协议及新独立包。复用最终建模证据和原参数，先固定精确81点、每个原生量各自时间轴、Clock/tout对齐准入、实际DC源i/v及六可变电阻R/i/v叶子、统一输出精度及完整原始MAT保存。任何缺叶子/缺点/时间错位均失败，不重算代替或插值补齐。
4. Run前绑定实际Fcn/Constant/连接/日志来源与原控制公式，不移用PSCAD FormCodec说明。单独冻结导出/分析入口和独审，随后才有界运行；保留0..400µs全部81点/80区间、原TR5µV/共模2µV及其余全部门。BE只能诊断，不预断实际首步或换相公式，不删点/放宽阈值。
5. 短探针不能代替原0.2s双h参考。原PSCAD共模FAIL保持，完整参考合格前不实施教学候选。研究脚本和第三方原件继续留忽略目录，不增加公共框架、重复算例或依赖。
6. F1没有新观察：精确c3fdf79的CI43825501731因账单锁未获得runner、steps空，已终态；不要反复触发，外部解除后再补跨OS。本轮未改正式源码，无新全量测试；既有1300含slow结果保留其实际范围。

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
