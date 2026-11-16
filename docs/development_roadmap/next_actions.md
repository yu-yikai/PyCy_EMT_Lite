# 恢复与下一步

修复57fbc81已提交推送，本地1518全量通过；[新CI](experiments/ci_57fbc81.json)因已确认账单锁未运行两OS测试。新监控正常direct-base/32MiB/2s受控例已闭场，异常路径及完整规模测量仍待补验；具体版本与限制见tasks.offline_analysis_preparation。

2026-11-16：VSC非法输入状态污染已修复，本轮1518项全量含slow通过；仅控制器与测试变化，其余111源码及依赖不变。见[修复记录](experiments/vsc_input_validation_20261116.json)。新增完成9，C1进行中，完整商业参考仍受资源限制。checkpoint为本记录前57fbc81，恢复须核实际Git/远端及闭场记录。

1. 读取五状态，核分支/HEAD/工作区/远端和新的113文件快照。86152全量测试已exit0；旧原生会话及合成分析2790均已终态，不重启。
2. 合成全N分析首次因Windows虚拟环境启动器造成错误资源绑定而人工停止；只终止已严格核对的自有实际计算进程。保留原包和失败。后续先核新监控器直接启动真实解释器及PID握手，用小型受控数据验证，再单独顺序执行完整合成两档。原数学/点数/阈值不变；合成timeproof不是商业原生时间证据。
3. 商业Run原资源门保持300s、private6GiB、pre可用commit3GiB/运行floor2GiB；之前pre5.038GB仍中止。资源明显改善后才另封新HEAD包，建议ROOT额外预留8GiB可用commit，不干预未授权已有MATLAB。已有包/准备器绑定旧457 HEAD，不可直接运行；区分历史构建HEAD、本次执行HEAD与新113源码快照，重新准入未变物理合同和模型。5µs正常闭场后才启动2.5µs。
4. 完整57量Time/Clock/tout位核验、40002/80003点含尾点、原19门及辅助2µV、四窗/六周期/全部pair门须真实通过。先取得正常闭场/raw准入，再运行经实际进程绑定核实的离线分析；合成基准不能授予完整参考资格。原PSCAD FAIL和400µs短探针PASS保留。
5. 完整参考合格前不实施教学候选。F1精确57fbc81的CI43856421332账单锁已终态，外部解除后补验。保持CaseDefinition链与现有元件/控制器，不增加公共框架或重复算例；本轮修复的实际提交/推送由闭场记录核实。

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
