# 恢复与下一步

2026-11-12目标active。恢复先读五状态文件，核分支、实际HEAD、工作区与真实远端。
checkpoint为本次记录前的42c9c7a8；后续提交须按实际Git历史交叉核对，不自称包含自身。
开发分支codex/emt-examples-longterm常规提交/里程碑推送已授权；不改main、不强推、不覆盖用户文件。
C1仍in_progress；既有11已验收、正式新增9项。本轮原生/分析已终态，无已知待恢复运行。

1. 先读[理想支路结果](experiments/c1_ideal_branch_diagnostic_20261112.json)、[前次测量诊断](experiments/c1_dc_measurement_diagnostic_20261112.json)及[参考设计](experiments/c1_openloop_reference_design.md)。
   最新选项已在after/XML/Map三处核实生效，但新旧全部INF/OUT字节相同；原DC端口与电流表门仍同五行FAIL。
   本轮native、mapper和两套数值审计均终态，自有进程清空；不重复启动该run或试调阈值。
2. 调查直接读取电源支路同刻CBR的最小原生计量，避免独立DC零阻A支路；先核安装source_1定义及生成顺序。
   原source CUR虽有Dsout表达式，旧PGB仍可能位于Dyn；只增加输出声明不能代替实际MainOut新鲜读取证明。
   已有只读提案和独立理想方程等价审查，收据见本次记录；尚无新计量包或原生验证。
   最小派生源只加Text输出与`−CBR:BA`，原物理/Branch/Dyn/CUR保持。优先build-only，Run前硬核freshCBR→同次MainOut PGB；scalar0声明本身不保证时序。
   新身份为三相A表＋DC源支路；去表合并节点后电压关系rank1，旧A压降独立观察与门不适用于新拓扑，不能以结构零追认旧FAIL。
   新计量身份须另冻且原生验证；不加电阻/接地DC、使用历史CUR或放宽原门追认旧数据。
   所有失败包保留；继续worker -B、精确库存及资源/时间/归属守卫，实际映射准入先于任何OUT哈希或解释。
3. 合格后再冻结完整开环协议、参考细化与最小候选；实际源唯一sin(ωt+Ph)、正abc，cos-Park角为ωt−π/2。
   复用12/18、controls/vsc.py及CaseDefinition链，保持开环→已知角dq电流→PLL→P前馈/Vac→真实DC电容Vdc及扰动。
   完整草案已有独立电流包络/基波功率估计，仍未冻参数/预算，不把近似当商业参考。
   固定理想DC不能验证Vdc，刚性电网端不能验证Vac调节；合闸/功率阶跃/电压扰动/故障范围保持，不新增通用框架或重复算例。
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
