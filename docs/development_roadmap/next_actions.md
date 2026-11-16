# 恢复与下一步

2026-11-16：完整规模合成分析与无JVM守卫能力验证已完成，见[分析与守卫证据](experiments/c1_offline_full_n_and_nojvm_guard_20261116.json)。C1仍进行中，新增完成9；完整商业参考和教学候选尚未验收。113源码与依赖不变，1518全量是此前实测结果。

1. 读取五状态，核分支、实际HEAD、工作区、远端及f533源码快照。checkpoint为本记录前8c68b175；实际新提交与远端看闭场记录。86152测试、2790失败合成、47342成功合成、旧原生及51054守卫均已终态，不重启。
2. 下一步另冻400µs无JVM Simscape兼容包：沿用原短模型、5µs/81点、57量、物理/求解器/全部预算；仅把Java路径与哈希叶函数替换成已证明的有限.NET守卫，并绑定本次新执行HEAD与113源码，历史构建HEAD单列。实际sim后保存完整MAT，清除内存对象再重载，证明原生simlog可读并按原守卫导出。先核新包与独审再单次运行，不能由守卫PASS跳过模型资格。
3. 短链合格后才准备新HEAD的完整两档包。原300s、private6GiB、pre可用commit3GiB/运行floor2GiB保持；之前pre5.038GB仍中止，普通完整Run建议额外预留8GiB可用commit。仅守卫启动的内存峰值不能证明完整模型省内存；不干预已有MATLAB，不复用消耗过或旧HEAD包。
4. 完整57量Time/Clock/tout位核验、40002/80003点含尾点、原19门及辅助2µV、四窗/六周期与全部pair门须真实通过。正常闭场/raw准入后，另封真实归档分析器与当前监控绑定；旧实际波形worker引用旧监控，不能直接执行。合成PASS不授参考资格，原PSCAD FAIL保留。
5. 完整参考合格前不实施新教学候选。F1精确57fbc81的CI43856421332账单锁已终态，外部解除后补验。继续复用现有链和元件，保持精简、可读、初学者友好。

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
