# 恢复与下一步

2026-11-12目标active。先读五状态文件，交叉核分支/实际HEAD/工作区/真实远端；checkpoint为最近记录提交da18a433。
在codex/emt-examples-longterm工作；常规提交/里程碑推送已授权，不改main、不强推、不覆盖用户文件。
当前C1为in_progress：既有11完整1s参考资格已通过，候选比较尚未执行。新增19–27共9项，B1已完成。
本轮原生和分析均已终态；不重跑已通过的参考、分析器或1267全量代替复核。

1. 复核[公开参考资格报告](../../validation/cases/pll_dynamic_response/qualified_reference_report.json)，再核其qualification/provenance/198项绑定及两份后置独审。
   原生23列各10001行，solver时钟10001/20001行；50µs只核相同100µs控制的调度，不证明中点保持。
2. 精简case比较入口、33合成检查及完整1300项含slow已通过；入口与代码独审已完成。
   先核本检查点的实际Git提交/推送，再设置MPLBACKEND=Agg首次运行uv run --locked python -m validation.cases.pll_dynamic_response.compare。
   原main/三次plot保持；任何缺失/篡改/非有限/非法时间/角度门或输入前后变化均须FAIL，不能重建候选递推。
   三窗九指标和硬门按8048ce4已冻结协议，不拟合、不移时、不放宽。候选后补独审、图报告、独立默认Agg运行和简短教学说明。
3. PLL正式验收后依次做开环并网VSC、已知角度dq电流、合格PLL、P前馈/Vac及真实DC电容Vdc链。
   P前馈给id_ref、Vac外环给iq_ref；固定理想DC源不能证明Vdc动态。D1及F1也仍属于长期范围。
4. 保持精简、可读和初学者友好，复用CaseDefinition→Circuit→Simulator→SimulationResult；不增通用框架。
   F1待外部账单锁解除后补精确HEAD双OS，不轮询同一CI终态或造空提交；27/26既有限定保持。

本轮1300 passed510.44s含slow、锁定27包/Ruff/mypy39通过；旧111源未改，新2文件，总113源前后不变。
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
