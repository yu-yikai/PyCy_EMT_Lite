# 恢复与下一步

2026-11-12目标active。恢复先读五状态文件，交叉核分支、实际HEAD、工作区及真实远端。
checkpoint为最近记录提交5e27e787；不将其冒充包含本次研究记录的新提交。
开发分支codex/emt-examples-longterm常规提交/里程碑推送已授权；不改main、不强推、不覆盖用户文件。
C1仍in_progress；既有11已验收，正式新增9项。全部本轮原生/分析已终态，无已知待恢复运行。

1. 先读[开环设计](experiments/c1_openloop_reference_design.md)与[证据记录](experiments/c1_openloop_source_research_20261112.json)。
   v1首流FAIL保留，v2仅2 ms单回路观测PASS；不重跑成功探针，不当作三相VSC参考资格。
2. 冻结新的三相短探针：接地AC星点、浮置DC双极、3支R/L、6互补双向开关。
   固定400 V DC，AC幅值从0启动、门极首点为零向量；此激励不同于v2两源同时渐升。
   明确正弦源与Park角度、相序、方向、采样保持及初值；先固定观测分辨率、时间窗和预算，
   再核完整真实接线、同刻三线KCL、共模、首步和积分关系。仅复用B1已合格开关，不继承整桥资格。
3. 先固定完整开环协议，取得合格真实输出后再写最小候选。复用原12/18元件、controls/vsc.py及CaseDefinition链。
   后续保持已知角度dq电流→合格PLL→P前馈/Vac外环→真实DC电容Vdc及扰动；不新增通用框架。
   固定理想DC不能验证Vdc，刚性电网端不能验证Vac调节。
4. F1旧CI43060348386因账单锁在runner前失败，未执行测试；外部恢复后补跑该精确run并核两OS产物。
   不轮询同终态，不空提交或改代码绕过账户锁。

源码113项/依赖未改，上一轮1300全量含slow及锁定/Ruff/mypy通过，本轮未机械重跑。
第三方原件、波形、逐token长审查及研究工具保留在忽略local_reference/.tmp。
结束当前执行前同步任务、证据、提交及下一步，不声称无环境会后台继续。

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
