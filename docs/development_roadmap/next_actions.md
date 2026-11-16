# 恢复与下一步

2026-11-16：历史共模约束复核完成；下一步为已固定的节点排序单变量诊断。原完整双h参考仍未过2µV，新增完成9、C1进行中、目标active。

入口：[共模约束复核与单变量协议](experiments/c1_commonmode_constraint_followup_20261116.json)。checkpoint为本次提交前a495449，须与实际Git历史及结束检查点交叉核对。

1. 先读五状态并核分支、HEAD、工作区和实际远端。分析34509、原生98913/25165及旧失败会话均已终态；不重启或轮询旧句柄。
2. 新记录固定了当前事实与下一研究。已观测初值的无驱动模式/瞬时打印不足解释10.838/37.498µV；运行中有交替增量，累计q界27.061/108.304µV超过实测峰值，因此不能凭打印电流递推唯一归因。原始FAIL、全点和尾点保留。
3. 按next_single_variable_diagnostic创建当前clean HEAD的新单次包：仅optimize_nodes=True→False，其余44项设置、物理/输入/TR/45量/40002点与全部原预算相同。原fullguard与新有向19角色图、14语义节点/NODE槽/实际Map双射合取；未观察到预设的实际Map重编号则记本门NOT_ACTIVATED并在Run前停下，这不证明内部优化无效。新包/外部工具身份、3GiB预检/2GiB监控、owned/profile/源守卫和闭场/raw准入须ROOT另封；本协议本身不授执行。
4. 此次最多一Build、一Run、零重试，只作5µs全窗研究，不挑选通过排列。新输出须完整准入及全部适用原门，再比较基线残差；任何改善不覆盖旧FAIL，也不等于完整双h参考合格。后续如追求资格须另固定完整双h方案；参考合格后才做16既有元件的最小教学候选与后续控制链。
5. 现归档访问工具固定审查HEAD=a495449与clean工作区；文档提交后不要在新HEAD直接重跑并误解其拒绝。必要的历史复算先另封精确原Git/快照/全部原件的只读准入；不修改旧包或旧live guard。D1待办；F1保留账单锁既有受阻记录，本轮无新CI观察。

113个正式Python源和依赖未改；既有1300含slow本轮未重测。研究脚本、原始模型/波形/图均留忽略目录；公共改动仅状态与证据协议。

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
