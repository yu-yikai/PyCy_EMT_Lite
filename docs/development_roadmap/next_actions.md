# 恢复与下一步

2026-11-11（Asia/Shanghai）。长期目标active，分支 `codex/emt-examples-longterm`。
先读tasks/progress/decisions/validation_status，并核实际分支、HEAD、工作区和真实远端。
功能验收checkpoint为 `ae9fe3629ad9617853979b0ef58d4d8319239592`，已正常push；
本轮继续核同HEAD/远端8cc1457，后续文档提交以实际Git历史核对，不把checkpoint当实时HEAD。
不操作main、不强推、不覆盖未提交文件；开发分支常规提交及里程碑推送已获授权。

## 当前事实

正式新增19–27共9项完成，当前B1。27真实PSCAD参考/候选/物理测试和独审已验收。
最新完整实测为1244 passed469.79s（含slow），锁定27包/Ruff/mypy39通过；
本轮109个Python源文件与该全量前hash核同，未重复全量。
核心、依赖和教学入口未改；继续复用既有元件及统一建例流程，参数、接线、观察顺序应直观。

D为[证据索引](experiments/native_reference_attempts_20261109.md)中的B1研究根。
完整v6源 `D/held_bridge_research/20261110T031601744130Z_six_observers_v6`，27文件manifest `ff8a2dd3…`；
分析器 `D/held_bridge_analysis/20261110T032215391716Z_six_observers_v6/analyze.py` 为 `fda6e359…`。
冻结协议 `837a0b76…` 的真实1ms5/2.5µs双步长现已完成，**不要重跑合格诊断代替下一阶段**：

- 粗/细 `D/n/20261111T012359520751Z` / `D/n/20261111T013727404980Z`，84项归档各全核；
  manifest `1e3079dc…` / `5eea30c7…`，两者build0/runtrue/完成标记true，清理和环境守卫通过。
- 384组件/204线/506端口/117网，60通道全201/401行，201共享门极/R相同、200中点保持；
  七Pulse、原69数学/3612门极值、t0/末点/近边界、生成顺序及KCL/TR独审通过。
- 配对结果 `D/held_bridge_analysis/20261110T032215391716Z_six_observers_v6/results/20261111T014327781041Z`，
  summary `525ef21e…`，29项manifest `9e0d6ecc…`，图已查看。
- 独审 `local_reference/native_static_reviews/b1_full60_actual_20261111/pair_20261111T013727404980Z/report.json` 为 `55740490…`；
  范围资格 `D/held_bridge_qualification/20261111T014703278697Z/qualification.json` 为 `8be490f8…`。

资格仅限含观察器的1ms网络，不是完整B1验收。原12、MathWorks2% FAIL及历史v5五Pulse编译失败保留。
上轮暂停run `D/n/20261110T033233257295Z` 未编译/运行，不能分析或配对；暂停注记保留于run外。
所有本轮native和分析已终态，无自有原生进程待恢复。

## 执行顺序

1. **B1完整协议已冻，先完成来源/分析器冻结独审再实跑。**
   `validation/cases/two_level_pwm_pscad/reference_protocol.json` 为 `ed9eec3d…`，独审 `a91f38ee…`；
   采集.200005s（40002/80003行），多5µs仅保证固定[.1,.2]实际覆盖，TIME原样、禁止外推；
   40002共享行/40001中点及全部尾行仍做hard checks。三相自细化max3A，启动NRMSE.02、稳态.01，
   稳态总RMS/基波RMS/电阻耗散2.5%、相位1°；候选原150A/.02/10A/5%/3°不变。
   新建独立来源/分析包，不改旧837a/源/结果；本协议尚无完整原生波形或候选输出。
   固定0.2s、5µs施加门极保持、5/2.5µs电气步长、400V/六R/浮星RL/初值/TR历史、
   全部首末点和近边界、原生TIME/序列/生成顺序、窗/指标/误差预算及所有hash绑定。
   纯电气细化须共享施加门极/R完全相同；若选时钟与电气联合细化，须预先明确常量/时钟/保持边界准入，
   保留全部差异并把准入外差异判失败。不得量化TIME、回放候选门极、移相或事后放宽阈值。
   数学界0.66418A共享/0.66501A PWL仅为sameinput reducedTR推导；旧2ps/libm组合估计没有实现证明，
   不当作商业资格。旧十分之一1A/.3A仅为未冻结提案；本新完整协议预算已在输出前另行固定并独审。
2. **真实完整参考自细化合格后，再比较原12。** 保持稳态窗0.1–0.2s、150A尺度、NRMSE.02、max10A、
   RMS/基波/负荷功率5%和相位3°；不另加用户未要求的候选逐位门极相同门槛。
   优先复用现有metrics/plot/current_features/compare_features，新增验证入口保持短小，不建通用框架。
   日志DSD/DSO支路电流顺序只作有名诊断，不能移相商业比较数据。新候选/协议按既有流程先冻结提交再执行。
   native保持3GiB启动/2GiB动态、RPC20s/build180s/run120s/总420s及原件/profile/父环境守卫。
3. **C1仍后置，先从既有11 PLL补参考。** 可行性见
   `local_reference/c1_pll_reference_research/20261111T013530229954Z/feasibility.md`；未建立或运行模型。
   现成PLL的归一化/相位/次序不同，不能直接套相同增益宣称同数学。
   未来独立标准算术块+显式状态延迟参考先审t0/100/200µs，特别核正弦输入下角度约定、q归一化、
   PI积分先更新、旧omega推进角度与首点不反馈；实际编辑前读building-simulink-models技能。
   不新增同题教学编号/控制类，不引入自动二极管、非线性、复杂机器、稀疏或加速框架。
4. **保留已验收边界。** 27仅常参数集总损耗Bergeron，不推广为宽带电缆或隐藏延迟缓冲直接观测；
   26仅冻结同步控制/负荷事件及二极管不活动域，旧100/50ns参考FAIL保留。
   F1等待外部billing lock解除后补验精确里程碑双OS；[CI42616684547](https://github.com/yu-yikai/PyCy_EMT_Lite/actions/runs/42616684547)
   已终态且未执行测试，不重复轮询或制造空提交。23–27跨OS仍未验证，旧90b2fcd只覆盖22。

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
