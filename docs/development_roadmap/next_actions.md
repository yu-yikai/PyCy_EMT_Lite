# 恢复与下一步

2026-11-12。目标active；恢复先读五状态，核分支/HEAD/工作区/实际远端。
checkpoint为本记录前的fb9aaa8，须与Git历史核对；开发分支常规提交/里程碑推送已授权。
C1仍in_progress，新增9项本地/商业验收保持，跨OS另列F1。

1. 先读[本轮构建记录](experiments/c1_output_intent_build_only_20261112.json)。唯一run231950255510Z/会话4225已闭场exit1；build0但worker1受控异常、quit返回，guarded/native completion均false。DC ownPGB在MainDyn451，负ownBA读取在MainOut854，同刻测量不合格；无Run/OUT，不恢复旧会话。
2. runtime的CBR空格解析局限、上述真实时序拒绝、独立helper的PGBList分隔线异常分别保留。独立helper仅193完成检查PASS，未达完整元数据/4I+15Vm/37维度与STOF深门；另101描述符复核不补成准入。冻结旧包/脚本/收据，不修后重跑它们。
3. 另冻且独审一个标准master:force_dsout（Real/Dim1）置于源fresh内部别名与标准DC PGB之间的最小方案。官方v5.02页面及本机5.0安装定义只支持该原语，未来调度待实测。
   先固定不同输入/输出别名、精确观察组件/ports/wires/nets与存储预期；19电气分支、源方程/CUR、32通道、时钟、ideal flags和17预算及Vs/token门保持。新helper只针对合法CBR空格及精确已知PGBList注释分隔线修解析，其他未知记录仍拒绝。
   新独立build-only必须build0、完整Map32/DATAStruct34及全11参数/ports/实例身份，4I和15Vm同MainOut fresh→ownPGB无覆盖；DC明确负ownBA→标准identity copy→ownPGB顺序且无Dyn writer/历史CUR。37维度/STOF、原物理和环境守卫保留；不改生成文件/手填索引/重构电流/放宽预算。build-only通过仍不允许Run。
4. 结构合格后，另冻短探针执行/数值合同与分析器再Run；随后完整开环参数、双步长参考、最小候选。旧数值/时序FAIL保持，删除的A压降/秩2门为NA而非PASS。
   复用CaseDefinition链、现有12/18与controls/vsc.py，沿开环→已知角dq电流→PLL→P前馈/Vac→真实DC电容Vdc及扰动推进。固定DC不认证Vdc，刚性电网不认证Vac；合闸/扰动/故障和D1仍待。
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
