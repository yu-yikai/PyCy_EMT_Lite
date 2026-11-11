# 恢复与下一步

2026-11-11目标active，用户已明确恢复。先核五状态文件及实际分支/HEAD/工作区/真实远端。
恢复时本地与远端均为`3737e663c89646cf76e6cd9f4880d0e579d95731`；12未提交文件及111个
Python源与暂停记录一致。不操作main、不强推、不覆盖未提交文件。常规开发分支提交/里程碑推送已授权。
最新功能验收为`40bef297c431a0981f0dc93279cddf5acbbd6ea6`；最新已核研究提交为`acaec459d0ffe05a56a9951bed3a5544f23c9817`，均已推送。

## 当前事实

B1已completed40bef297；当前C1为in_progress，阶段`existing_11_pll_reference_design`。
B1真实完整参考及300输入资格、原12正式比较、
340快照/独立复算和独立默认Agg40001点均通过，图/报告/精简教学完成。
新1267全量含slow通过494.62s（XML494.618），0失败/错误/跳过；锁定27包/Ruff/mypy39通过。
原109源码、核心、依赖及原12保持，仅新增比较入口/测试；原MathWorks2% FAIL和所有旧失败保留。
正式新增19–27共9项，B1补对标不增加编号。完整pins见[证据索引](experiments/native_reference_attempts_20261109.md)。
本轮仅新执行一次R2026b/SATK接口探针，正常终态/独审通过；无PLL/native/candidate/pytest待恢复。
探针run为`local_reference/c1_pll_reference_research/20261111T135000Z_satk_probe_v2/runs/20261111T1354072589026Z`；
接口结果不替代PLL参考。111个Python源hash不变，既有1267测试不称本轮重跑，暂停原记录不改写。

## 执行顺序

1. 本机真实R2026b/SATK保护函数已验证可用，当前MCP目录无model_*不再是建模接口障碍。
   复用已审的owned进程/快照守卫：新建独立目录、冻结来源，使用model_read→model_edit（显式layout）→read/check；
   仿真用SimulationInput/Output，不绕过接口，不改全局安装/配置。已完成接口探针不重跑。
2. 先设计既有11 PLL的独立商业参考，不将这一步冒称完整单站控制链。可行性记录为
   `local_reference/c1_pll_reference_research/20261111T013530229954Z/feasibility.md`。
   下一步先冻结并运行0/100/200µs语义探针，再做完整参考；五个Unit Delay方案已独审，尚未构造。
   完整角度比较选共同初角锚定unwrap/PWL，先核旧omega×实际Delta小于pi及角增量；50µs保持中点另核，
   不混入100µs更新行的主PWL。旧xi顺序错误可能落在完整预算内，须靠启动及逐行代数硬门拒绝。
   先固定递推/初值/相位/信号方向与窗口/阈值，审t0/100/200µs的显式状态延迟、
   正弦与Park角度约定、q归一化、PI积分先更新和旧omega推进角度；模型未建立或运行。
   现成PLL数学不同，不能只换增益宣称一致；参考和判据固定后再实施、实跑与独立验证。
3. 根据实际参考拆分开环→PLL→dq电流→P/Q/Vdc→扰动，逐项验收并复用现有元件/控制器。
   不新增同题编号或通用框架；教学参数、接线和观察顺序清楚，商业接口/审计留在validation及忽略归档。
4. 保持27仅常参数集总损耗Bergeron、26仅冻结同步控制和二极管不活动域的边界。
   F1等待外部billing lock解除后再补精确里程碑双OS，不重查终态CI或制造空提交。
   不实施自动二极管、通用非线性、复杂机器、MMC、稀疏或加速框架。

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
