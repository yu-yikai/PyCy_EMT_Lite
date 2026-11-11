# 恢复与下一步

2026-11-11目标active。先读五状态文件，交叉核分支/实际HEAD/工作区/真实远端；checkpoint为最近记录提交b835e317。
在codex/emt-examples-longterm工作，不修改main、不强推、不覆盖用户未提交文件；常规提交与里程碑推送已授权。
当前C1为in_progress，三点启动资格通过；完整1s PLL仍未验证。19–27正式新增9，B1既有12已完成。
本轮原生与分析都已终态，无已知运行待恢复；不要重新运行已通过的三点探针或1267全量代替审查。

1. 复核启动证据：run为local_reference/c1_pll_reference_research/20261111T151000Z_pll_startup_v5/runs/20261111T1513366278040Z，
   semantic_analysis/20261111T1515333170669Z/report.json为141项PASS；完整SHA及独审见tasks.json与原生记录。
2. 完整1s协议已固定于validation/cases/pll_dynamic_response的manifest/reference_protocol/acceptance_plan，并随本检查点提交。
   原完整草案作为历史保留。先冻结并独审各schedule源、独立分析器及有限合成拒绝样例，再顺序执行100/50µs solver原生参考；参考资格通过后才运行候选。
   固定初值/方向/全窗和阈值，保留t0误差；共同初角锚定unwrap后按真实100µs更新行做PWL，不拟合或移时。
   每行硬核旧omega推进角度、新xi参与PI、状态链和abs(oldomega*Delta)<pi；不能仅靠较宽轨迹误差限。
   原worker/config的FixedStep写为control_step，50µs secondary须先独立定义solver_step并实际回读，控制仍100µs。
   secondary只核同一离散任务的调度/输出不变性；无真实中点记录便不称实测保持或控制步长细化。
3. 完成PLL后依次推进开环并网VSC、已知角度dq电流、合格PLL、P前馈/Vac和带真实DC电容的Vdc链。
   复用现有控制器：P前馈给id_ref、Vac外环给iq_ref；不改称P/Q双PI，不用固定理想直流源证明Vdc动态。
4. 保持精简可读、初学者友好；复用CaseDefinition→Circuit→Simulator→SimulationResult，不加通用框架。
   27限常参数集总损耗Bergeron；26限冻结同步控制/二极管不活动域。F1待外部账单锁解除后补精确HEAD双OS。
   不重查同一CI终态、不制造空提交，不实施自动二极管、非线性、MMC、稀疏或加速框架。

完整回归仍为B1阶段1267 passed494.62s含slow，锁定27包/Ruff/mypy39已通过；本轮111源不变，未重复测试。
结束执行前同步任务/证据/提交/下一步，不声称无运行环境时会后台继续。

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
