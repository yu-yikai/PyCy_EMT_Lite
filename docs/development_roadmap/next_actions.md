# 恢复与下一步

2026-11-12。目标active；恢复先读五状态，核分支/HEAD/工作区/实际远端。
checkpoint为本记录前的b246236，须与Git历史核对；开发分支常规提交/里程碑推送已授权。
C1仍in_progress，新增9项本地/商业验收保持，跨OS另列F1。

1. 读[本轮结构验证记录](experiments/c1_force_dsout_build_only_20261112.json)。唯一run001751572848Z/会话81982已闭场exit0，build0、worker0且正常quit；guarded/build-only completion均true，自有进程清空。DC原始文件855→858→862行在MainOut形成负ownBA读取→标准force恒等传递→ownPGB，独立517深门及108绑定重核全过。
2. 此包只允许build，未Run/OUT，数值NOT_OBSERVED。冻结包、helper、收据及全部旧FAIL，不恢复旧会话或修后重跑。Map32/DATAStruct34、4I/15Vm、全11参数/端口/层级和37维度深审已完成；仅观察STOF45→46，122个非DC传递角色/双射保持，物理STORF44不变。
3. 另冻32通道短探针Run合同、新驱动和两路数值分析器。复用已有17项物理计算；先核来源/新包身份、原生正常完成及actual INF/Map/PGB全绑定，再读OUT。保留全81点含首末、原17预算及Vs/full-token Decimal词元半径门（含零词元）；不删边沿、不用半cell或重构DC电流。新run还须重核完整生成链/元数据/存储/原物理。现有未来数值稿仅草案，未授权其执行。
4. 短探针数值合格后，冻结完整开环参数/指标、双步长真实参考，再做最小候选。删除A压降/秩2门保持NA；旧数值/时序/编译失败保留。复用CaseDefinition→Circuit→Simulator→SimulationResult、现有12/18和controls/vsc.py，沿开环→已知角dq电流→PLL→P前馈/Vac→真实DC电容Vdc及扰动推进；固定DC不认证Vdc，刚性电网不认证Vac。合闸/扰动/故障和D1仍待。
5. F1最近已查CI43060348386在runner前因账单锁失败；外部恢复后补双OS，不重复轮询同终态或空提交绕锁。

113源码/依赖未改，复用既有1300含slow/锁定/Ruff/mypy39，不称本轮重测。
原件和研究脚本留忽略目录；结束前同步证据、Git及下一步，保持教学精简易读。

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
