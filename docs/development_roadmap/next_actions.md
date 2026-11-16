# 恢复与下一步

2026-11-16：同电路Simscape参考的真实库接口发现已完成；新短探针尚未固定、建立或运行。新增完成9、C1进行中、目标active。

入口：[接口发现记录](experiments/c1_simscape_library_discovery_20261116.json)。checkpoint为本次提交前c3fdf79；实际Git、远端与结束检查点交叉核对。

1. 先读五状态并核Git。76308已exit0终态，唯一MATLAB启动已闭场；只加载fl_lib/nesl_utility，11接口唯一，无新模型或仿真。不要轮询或重启旧句柄、driver或已消耗的包。旧8170/98913/25165/34509等也已终态。
2. 下一步先固定并建立从0开始的400µs同物理SPWM短探针。复用原参数/16电气元件/19原生支路/方向；明确L=.01H、r=0、g=0、i_L=0/high且i_L_specify=on，六R=.001/1e9，AC公共星点接地、DC浮置，不加Floating Reference电容或DC接地支路。实例化后核实际端口域/连接和初值，不把库端口计数当编译资格。
3. 根据真实discovery和95a477参数建议另固定solver/converter/时序：局部TR、LocalSolverSampleTime、DoDCoff、正则化/滤波关闭；LOCAL容差枚举已核，数值建议仍须前验固定。连续AC使用V/provide input-only，缺导数则显式失败并另立版本，不静默滤波；真保持R使用Ohm/zero。完整回读实际PS R、100µs参考/5µs门极、首步与换相方程。保留原逐段TR5µV/共模2µV、原点和全部首末点，不预断BE作用于哪个实际采样段。
4. 新建模/编译/仿真须新HEAD独立封包、资源与输入守卫；当前发现包只授予库读取，不能直接改function或复用为仿真包。模型运行许可、直接DC源电流日志、全部控制/物理/输出绑定均待实测。短探针不代替原完整双h参考；完整参考合格前不实施教学候选。原PSCAD2µV FAIL及全部失败原件保持。
5. 源码当前113文件快照见tasks.current_source_snapshot；c3fdf79仅27号摘要改动，其余112个及依赖不变。两处可读性小改已验收提交。旧113全部不变只适用于其历史执行，不绕过旧准入的固定HEAD/hash。
6. 新CI43825501731精确针对c3fdf79，已终态：账单锁、两OS runner0/steps空。原始API与公开记录ci_c3fdf79.json已保存，不重复轮询/触发；外部解除后再补跨OS。首次CIM超时/启动0及后续库发现的启动1均保留，观察边界见ROOT/独立闭场收据。

本轮小改的锁定同步/Ruff/mypy/27号6001点独立运行通过；1300含slow为此前全量，未重跑。所有商业原件、研究脚本和接口原始数据留忽略目录；不增加公共框架。

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
