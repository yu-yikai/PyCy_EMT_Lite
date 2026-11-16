# 恢复与下一步

2026-11-16当前入口：4c5f423已核实际远端一致，新增9项，C1完整开环协议尚未冻结。见[完整开环准备记录](experiments/c1_full_openloop_preparation_20261116.json)；下方旧记录按各自时间保留。

1. 读取本轮记录及其本地三路设计收据。草案proposal是JSON；细网格oracle的carrier_at_gate_tick仅用于施加门极，原生中点carrier/raw_g另验。
2. 在候选前确定最小验证接口、同h/跨h跳变量比较、能量PWL定义及误差预算，固定参数/方向/初值/全窗/阈值/尾点并提交。13项原生研究观察不进入教学API。
3. 再准备新完整参考包及独立分析器，验证100µs原生采样和同拍执行顺序，运行真实5/2.5µs参考并先过自细化；不重启已闭场短探针。
4. 参考合格后才写最小教学候选和必要验证，随后推进dq电流及其余C1链；D1仍待，F1不重复轮询已终态CI。

113源码/依赖未改，本轮只保存研究与恢复入口，不称新回归或商业验收。

2026-11-16：目标active。C1的400µs人工向量短探针已真实运行并通过双路数值检查：原生编译0错误、Run一次、正常quit，唯一会话63693已闭场，自有进程清空；实际映射551项及118项绑定复核全过。32通道全81点/80区间、原17预算和Vs/完整末位精度门均通过。只取得短探针数值资格，完整SPWM开环VSC、闭环和新候选尚未验收；新增完成数仍9，C1仍in_progress，D1/F1范围保持。113源码与依赖未变，1300含slow为既有回归，本轮未重测。研究工具、原始波形与图留忽略目录，教学继续复用现有元件和CaseDefinition链，保持精简可读。

见[本轮短探针记录](experiments/c1_force_dsout_bounded_numeric_20261116.json)。检查点为本记录前的63e5165；本轮实际提交/远端在结束检查点另核。已保存暂停/恢复历史和全部失败，以下旧状态不覆盖本段。

1. 先读本轮记录、五状态并核实际Git/远端。会话63693已终态，不轮询或重启旧run；冻结v1从未执行。
2. 更新并冻结完整开环协议：400V/120Vrms60Hz/R1Ω/L10mH、m0.85/δ−5°/1kHz草案须独立定稿；明确20ms源斜坡、5µs门极与100µs参考的整数tick、首拍000/111、完整窗/阈值/尾点及双步长自细化预算。删除旧A电流表与秩2描述。
3. 完整真实5/2.5µs参考及资格通过后才做最小候选，再依序推进dq电流、PLL、P前馈/Vac及真实DC电容Vdc。继续现有元件/控制器，不增加公共框架。
4. F1最近记录仍为账单锁导致CI未启动；外部恢复后补验，不重复轮询终态或制造空提交。


2026-11-12：已按用户要求暂停。当前保存到短时数值验证准备阶段：新合同和24文件运行包已固定，分析器与最终独审尚未完成；本轮未启动原生仿真、读取OUT或运行候选。最新已推送提交为63e5165；须待用户明确恢复后再继续。以下为最近已验证结果与后续计划。

2026-11-12。目标paused；恢复先读五状态，核分支/HEAD/工作区/实际远端。
checkpoint为最近已推送的63e5165，须与Git历史核对；开发分支常规提交/里程碑推送已授权。
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
