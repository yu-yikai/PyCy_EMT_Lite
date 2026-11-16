# 恢复与下一步

2026-11-16：真实Simscape完整开环参考已合格，见[证据](experiments/c1_nojvm_full_reference_20261116.json)及[资格报告](../../validation/cases/grid_connected_vsc_open_loop/qualified_reference_report.json)。新增完成9，C1进行中；下一步28号最小教学候选。113源码/依赖未变，1518含slow为此前实测。

1. 读取五状态，核分支、实际HEAD/远端、工作区及f533源码快照。checkpoint为本记录前fadb979，须交叉核实际新提交和闭场记录。36396/15503/57383/36134均已终态，无剩余自有进程，不重跑或复用消耗过的运行目录。
2. 先核资格报告及ROOT资格53ff22f4，固定参数f5041eee/完整协议d87a327e不变。短恢复只证明两次磁盘加载和81点原门，不补记原保存前live快照；原短元数据FAIL、粗档旧读取器FAIL、PSCAD FAIL及普通JVM资源中止保留。
3. 实现examples/28_grid_connected_vsc_open_loop.py：沿CaseDefinition→Circuit→Simulator→SimulationResult，用现有16个元件和6个纯closed(time)。100µs参考保持、5µs门极保持，先验证支持的电气网格再用整数索引。验证实际附着回调、接线、方向、初值、Ron/Goff和state:switch；不回放原生门极，不改用求解后反馈sample，不增加公共采样器框架。
4. 候选两档保持40002/80003点和0.200005s尾点，按原协议完整执行32量同h、原点/物理/控制门、四窗及六周期、跨h比较。两路独立检查、独立Agg运行、图/机器报告、简明教学说明和必要测试齐备后单独提交；正式验收及Git前不计新增完成，不把开环阶段记成C1全链完成。
5. 新候选是正式Python变更，重新运行锁定同步、全Ruff/mypy/pytest含slow。原生参考已合格且数据已封存，源码变更后应重新冻结候选比较的执行HEAD/源码/数据身份；旧分析manifest只适用于fadb979，不能直接在新HEAD重跑。研究工具/原始模型与波形留忽略目录，正式代码保持精简可读。
6. F1精确57fbc81的CI43856421332账单锁已终态，外部解除后补验；不重复触发已有失败。后续dq电流环/外环和D1继续按依赖另立验收。

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
