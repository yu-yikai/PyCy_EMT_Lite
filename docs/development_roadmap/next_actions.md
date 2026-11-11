# 恢复与下一步

2026-11-12目标active。恢复先读五状态文件，核分支、实际HEAD、工作区与真实远端。
checkpoint为本次记录前的e73c0b3b；后续提交须按实际Git历史交叉核对，不自称包含自身。
开发分支codex/emt-examples-longterm常规提交/里程碑推送已授权；不改main、不强推、不覆盖用户文件。
C1仍in_progress；既有11已验收、正式新增9项。本轮原生/分析已终态，无已知待恢复运行。

1. 先读[测量诊断](experiments/c1_dc_measurement_diagnostic_20261112.json)、[原三相记录](experiments/c1_three_phase_probe_20261112.json)及[参考设计](experiments/c1_openloop_reference_design.md)。
   最新33通道包真实运行及两套数值审计已终态。原DC端口和新电流表压降各五行超1e−8 V门，整体FAIL。
   源端电压/闭合过门，只定位了记录中的端电压差；条件预测仍仅诊断，不推断内部EMF或浮置数值成因。
2. 安装电流表及实际生成分支已只读核实。下一包只改`use_ideal_branch=False→True`，
   保持`branch_threshold=0.0005 Ω`、33通道、元件/参数/门极/时钟和全部原门；先独立冻结再运行。
   这是算法选项假设，可能影响其他零阻抗支路；不能称只改DC表内部或保证修复。核实际选项与生成`SHORT_CIRCUIT`后再读波形。
   新设计须保留同刻独立电流观测、端口方向和全部原失败；不能用源CUR历史或改门追认旧数据。
   33通道v1编译失败、v2成功运行但数值FAIL均完整保留，不修改冻结包或重启已完成的run。
   新包继续显式worker -B、精确无缓存库存与资源/时间/归属守卫；节点从实际生成文件核定，映射收据先于原始波形。
3. 合格后再冻结完整开环协议、参考细化与最小候选；实际源唯一sin(ωt+Ph)、正abc，cos-Park角为ωt−π/2。
   复用12/18、controls/vsc.py及CaseDefinition链，保持开环→已知角dq电流→PLL→P前馈/Vac→真实DC电容Vdc及扰动。
   固定理想DC不能验证Vdc，刚性电网端不能验证Vac调节；不新增通用框架或重复算例。
4. F1旧CI43060348386因账单锁在runner前失败，未执行测试；外部恢复后补该run并核两OS产物。
   不轮询同终态，不空提交或改代码绕账户锁。

113源码/依赖未改，上一轮1300全量含slow/锁定/Ruff/mypy通过，本轮未机械重跑。
原生波形、原件与研究脚本留在忽略的local_reference/.tmp；结束执行前同步证据、提交及下一步。

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
