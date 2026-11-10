# 恢复与下一步

2026-11-10（Asia/Shanghai）。长期目标active，分支`codex/emt-examples-longterm`。
先读tasks/progress/decisions/validation_status，并核实际分支、HEAD、工作区和远端。
任务检查点为最新功能验收`ae9fe3629ad9617853979b0ef58d4d8319239592`；已正常push且真实远端核同。
后续文档提交在其后，以实际Git历史交叉核对，不把checkpoint当成实时HEAD。
不操作main、不强推、不覆盖未提交文件；开发分支常规提交及里程碑推送已获授权。

## 当前事实

正式新增19–27共9项完成，02补参考另计，当前任务B1。26提交`9269350`、27提交`ae9fe36`均已验收。
核心包、pyproject.toml和uv.lock相对起点main没有变化；教学入口继续复用现有元件和统一建例流程。
27只有8个元件：源、源阻、两半线、三只线路电阻和负载；先看参数/接线，再看波前、反射和直流极限。

27真实PSCAD参考1/0.5 µs先过16项自细化，`44d1436`先冻结协议再创建候选。
四量双完整窗八项比较、8项独立物理测试、Agg独立6001点和两路原始数据审查均通过。
完整1244 passed469.79s（XML469.778，含slow），零失败/错误/跳过；109个Python文件集合/hash与运行前一致。
锁定27包、Ruff全范围和mypy39通过；证据`.tmp/longterm/a3-27-full-20261109T1207.*`。
所有本轮native、仿真、测试和CI观察已终态，不恢复旧worker或无故重跑已合格参考/回归。

B1按真实端口重连后已真实build/run：完整1 ms、201点、46通道，400V源及1206门极值经独审。
当前参考仍为`runnable`。20 µs标准sampler/impulse小模型的5/2.5 µs两次真实运行、完整原始行和独审已通过；
已证t0、连续高Pulse更新、中间点保持及同tick有效R，范围仅两个sampler/一条varR。
六路三相1 ms保持和完整0.2 s尚未验收。11-10的v3粗步在编译前拒绝Ts_s重载端口偏移。
后续只读完整320组件/163线抓取已完成：仅Ts_s一处开路，其他参数/线/端口一致，位置与端口左移一格。
单线 v4 已实际保存，356/185/471/110 全图通过；保存 XML 守卫因修订信息更新而拒绝，尚未编译、无新波形。
完整文件差异正逐项核对，限定保存检查后再继续。资格、全部 run 和 hash 见证据索引。
原12及MathWorks2%波形FAIL保持，不以新短探针覆盖原失败。
全部run、脚本身份与完整hash集中在[本轮证据索引](experiments/native_reference_attempts_20261109.md)。

## 执行顺序

1. **B1 先完成保存检查，再实跑三相 1 ms。** 见[同数学参考设计](experiments/spwm_matched_reference_design.md)和[本轮证据索引](experiments/native_reference_attempts_20261109.md)。
   D 为证据索引中的 B1 研究根；本轮所有已启动进程均已终态，无后台仿真。
   v3 在重载端口检查处停止；完整只读捕获 `014409445520Z` 定位到唯一的 Ts_s 开路。
   v4 源为 `D/held_bridge_research/20261110T015230Z_Ts_one_wire_v4`，24 文件 manifest 为 `2cec5b44…`。
   只增加一段 (69,60)→(70,60) 导线；实际 run `020027875119Z` 保存后的完整原生图通过，
   共 356 组件、185 线、471 端口、110 网络。51 文件 hash 全核；256.4880211 s 干净退出。
   保存 XML 首先因 revisor 更新被拒绝，没有 build/run 或波形，不能启动 v4 细步长。
   完整文件核对还观察到单个 Ts_s 的 x 持久化、Main.size、12 个标签宽度、Main CRC 和顶层层级 link 变化；
   只记录已观察的变化，不推断未证实的 CRC/link 含义。
   下一版仅限定已实测的保存变化，保留其余组件参数、坐标、元数据和导线检查。
   原 69 个数学控制、31 个电气对象与旧导线不改；只允许原定 12 个标签改接及 6 个 sampler/公共 impulse/INT。
   分析器 v4 位于 `D/held_bridge_analysis/20261110T015936218946Z_Ts_one_wire_v4`；
   协议 `6e9bd776…` 只将线数 184 改为 185，数值预算及物理方程不变。来源再变时另冻绑定。
   完成新源及绑定独审后，由 root 顺序跑 5/2.5 µs：核完整 201/401 行、53 通道、t0/末点、
   六路门极互补、有效 R、同刻次序、全部共享点与中间点保持，再核 KCL/TR 和独立电气解。
   不量化时钟、拟合相位、删点或回放候选门极。已合格的 20 µs 原语探针不重跑，不能代替三相验收。
   从 00c3 成功工程先 copy 再 load；不重试已知跨目录 save_as 挂起路径。旧包与失败全部保留。
2. **B1通过短探针后再冻完整协议。** 先固定0.2 s、控制周期与细化方式、初值、有效R、源单位、
   TR历史、比较窗和误差预算，再准备参考自细化及商业候选；C1仍后置。
   DSD/DSO支路电流日志次序只作单独诊断，不能给候选比较移相。
   保持3 GiB启动/2 GiB动态余量、RPC20 s/build180 s/run120 s/总420 s及原件/profile/父环境守卫。
   不引入自动二极管、非线性、复杂机器、稀疏或加速框架。
3. **A3和B2保持已验收范围。** 27只覆盖冻结常参数集总损耗Bergeron，不推广为宽带电缆；
   STANDARD/无快照、零可观测前史与因果到达不等于直接导出隐藏缓冲。
   26只覆盖冻结同步控制/负荷事件及二极管不活动域；原100/50 ns参考FAIL保留。
   不为换参或凑数量复制SPWM/RLC算例。新候选须有独立教学价值和真实相容参考。
4. **F1等待外部账单锁解除。** 精确验收ae9fe36的
   [CI42616684547](https://github.com/yu-yikai/PyCy_EMT_Lite/actions/runs/42616684547)
   已实查终态failure；Ubuntu129158174490/Windows129158174768均runner0/steps空，两注释确认billing lock。
   [ci_ae9fe36.json](experiments/ci_ae9fe36.json)及7份raw/hash已核，未执行测试/test_count=null。
   不轮询同终态、不制造空提交或修改代码绕过；外部账户恢复后再补验精确里程碑双OS全部步骤。
   旧90b2fcd只覆盖22，23–27跨OS仍未验证。

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
