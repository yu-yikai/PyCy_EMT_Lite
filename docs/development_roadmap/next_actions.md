# 恢复与下一步

2026-11-16：C1完整开环真实双步长参考已运行，但共模物理硬门未过；当前为数值误差诊断阶段。新增完成9，C1进行中，目标active。

入口：[完整双步长诊断记录](experiments/c1_full_openloop_dual_h_diagnostic_20261116.json)。checkpoint为本次提交前的fbcfb75，须与实际Git及结束检查点交叉核对。任务与暂停/恢复历史保留在tasks.json和各实验记录。

1. 先读五状态并核分支、HEAD、工作区和实际远端。原生会话98913/25165均已exit0正常闭场，旧69502和报告工具32882也均终态；不轮询或重启旧会话。
2. 读取记录中的两路完整数值receipt、32+1元数据证明、诊断图与原厂手册范围收据。40002/80003全点和尾点保留；共模含q峰值10.838/37.498µV超过2µV，跨h比较通过仅作诊断。C1尚无合格完整参考或教学候选。
3. 下一步先研究S=Σi、T=ΣVL的TR求和约束及初值/舍入/测量证据；不能据V4.6手册断言V5内部根因。三项chatter/interpolation设置仍NO。任何不同算法或half-step试验须先另冻协议、时序、逐步方程与预算，再freshRun；不放宽旧2µV门或覆盖旧FAIL。
4. 旧分析器固定执行HEAD=fbcfb75及clean工作区；本轮提交后不要把在新HEAD直接重跑的拒绝误当新物理结果。后续只读复算先另封历史归档准入，核记录中的原执行HEAD、Git源码和全部immutable输入/波形，不修改旧包或伪造其合同通过。新原生试验另建当前HEAD的新单次包，保留3GiB/2GiB资源与owned/profile/源守卫。
5. 参考真实合格后，最小候选复用16个现有元件、纯时间门极和CaseDefinition链；100µs参考/5µs门极用整数索引，细网格中点保持前一门极。13项原生研究观察留验证层，不增加公共框架。随后继续dq电流、PLL整合、P/Vac、真实DC电容Vdc及扰动；D1待办，F1仅外部恢复后补验。

113个正式Python源和依赖未改；既有1300含slow不称本轮重测。所有原始模型、波形、图和研究脚本在忽略目录；本轮公共改动仅状态与证据记录。

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
