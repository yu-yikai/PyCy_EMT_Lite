# 恢复与下一步

2026-11-12目标active。先读五状态文件，交叉核分支/实际HEAD/工作区/真实远端；checkpoint为最近记录提交5314486。
开发分支codex/emt-examples-longterm常规提交/推送已授权；不改main、不强推、不覆盖用户文件。
C1仍in_progress：既有11完整离散PLL补验证通过；正式新增19–27共9项，B1已完成。
所有本轮pytest/原生/商业比较/独立默认运行和分析均已终态，无已知待恢复的运行。

1. 恢复时核[PLL结果](../../validation/cases/pll_dynamic_response/validation_report.json)与5314486前置入口提交。
   已通过首次比较run20261111T163858643683Z、独立审计8dc2a994和默认运行164014570020Z，不重跑这些已通过结果代替审查。
2. 进入开环并网VSC参考先行设计。先读examples/12_two_level_pwm_generator.py、examples/18_three_terminal_vsc_hvdc.py的station_components、
   pycy_emt_lite/controls/vsc.py及B1已验证双向开关参考；复用既有六开关/SPWM/RL与CaseDefinition链。
   明确固定DC端、三相电网/中性点及零序回路、RL接线、已知角度/门极采样保持、初值、AC→converter电流方向和参数来源；
   预先冻结拓扑/参数/三相P/Q关系、时间窗和限值，取得真实Simulink或PSCAD输出后再候选，不复制RL负载SPWM题凑数。
3. 再依次已知角度dq电流→已合格PLL→P前馈/Vac外环→真实DC电容Vdc及扰动。
   P前馈给id_ref、Vac给iq_ref；固定理想DC源不能证明Vdc动态。C1全链、D1及F1范围保持。
4. F1精确[CI43060348386](https://github.com/yu-yikai/PyCy_EMT_Lite/actions/runs/43060348386)已终态：账单锁、两OS runner0/steps空，未执行测试。
   外部账户恢复后重跑该精确run，再核两OS完整步骤/产物；不再轮询同终态，不空提交或改代码绕过账户锁。

本轮33专项/1300全量含slow（XML510.444s）、锁定27包/Ruff/mypy39通过；旧111源及依赖未改，总113源hash前后同。
保持精简、可读、初学者友好；第三方原件、波形和研究工具在忽略local_reference。结束前同步任务/证据/提交/下一步，不声称无环境会后台继续。

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
