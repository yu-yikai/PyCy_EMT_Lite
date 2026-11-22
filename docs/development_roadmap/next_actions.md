# 恢复与下一步

2026-11-22。绑定电源精度双档参考报告、原生回执、原始 INF/OUT/CSV、独立报告和跨档哈希。让 30 号正式比较入口读取这两档参考并新运行两档 PyCy。保持原过门条件及旧 FAIL 记录，整理新图、报告、测试及教学验收。
[电源精度双档参考报告](../../validation/cases/grid_connected_vsc_pll/source_precision_reference_report.json)

2026-11-22。粗档新参考波形和固定 PyCy 粗档已通过所有原判据。按冻结协议在独立目录运行 2.5 µs 对照，保留 80,003 点和全部中点保持。核验细档后重做原生跨档与两档最新 PyCy 同档对标。
[粗档电源精度结果](../../validation/cases/grid_connected_vsc_pll/source_precision_trial_result.json) · [细档对照协议](../../validation/cases/grid_connected_vsc_pll/source_precision_fine_trial.json)

2026-11-22。保留 30 号首轮输入快照和对标 FAIL 证据。粗档单变量对照用原理想源的外部瞬时输入生成同一电压，PLL 仍读取求解后的差分电压。先核本地 `c1_pscad_pll_source_precision_5us_20261122/n/20261122T124522755889Z` 原生运行及终态。闭场后用 `c1_pll_source_precision_numeric_20261122.verify_source_trial` 绑定新回执和已存 PyCy 粗档波形，沿用冻结的全部判据。
[30 号首轮验证](../../validation/cases/grid_connected_vsc_pll/validation_report.json) · [电源精度对照协议](../../validation/cases/grid_connected_vsc_pll/source_precision_trial.json)

2026-11-22。PLL 两档 PSCAD 长窗参考已合格。先核协议、两份原生回执和跨档报告，再以私有共用函数保留 29 号的电流 PI、限幅与门极时序，新教学入口通过既有 SRFPLL 从实测三相电压获得相角。使用两档新 PyCy 轨迹执行原时钟同档比较，检查六路门极、电阻、限幅、锁相及真实电网坐标系的三周期跟踪。复跑受影响的 29 号对标、专项和全量回归并完成图与教学后验收。
[PLL 双步长原生长窗](../../validation/cases/grid_connected_vsc_pll/full_reference_report.json)

2026-11-22。粗档长窗已通过。细档首次启动在建图目录保护处退出，随后用 `c1_pscad_pll_long_2p5us_v2_20261122` 隔离包重试。先核该包 `n/20261122T121136814535Z` 的实际状态和终态，再核验 80,003 点并与粗档比较。
[PLL 长窗记录](../../validation/cases/grid_connected_vsc_pll/full_reference_report.json)

2026-11-22。两档 PLL 短窗已验收。保留已冻结主工况，分别在原生 PSCAD 运行至 0.200005 s。每档通过全点电气、控制复算、110–160 ms 锁相及三周期电流跟踪与功率判据后，再做原生跨档比较。
[PLL 双步长短窗结果](../../validation/cases/grid_connected_vsc_pll/short_reference_report.json)

本机两档长窗包位于 `local_reference/native_static_reviews/` 下的 `c1_pscad_pll_long_5us_20261122` 和 `c1_pscad_pll_long_2p5us_20261122`。先核各自的 `prospective.json` 与任务状态。使用已验证的 PSCAD 自动化 Python，粗档运行 `pll_probe.py --arm validation/cases/grid_connected_vsc_pll/short_reference_report.json`，细档运行 `pll_probe.py --arm`。逐档用各包的 `native_driver.py` 启动，检查前一次运行的终态后再开始下一档。用项目锁定的 Python 执行 `python -B -m local_reference.native_static_reviews.c1_pll_full_oracle_20261122.verify_pll_full`，每档先用 `run` 核验原生回执，再用 `pair` 核验两档报告及各自 SHA-256。

2026-11-22。粗档原始输出及补充运行来源核验通过。用本地细档隔离包启动 2.5 µs 原生短窗，采集 243 点。通过生成准入后运行一次。按同一判据核对六次更新、六次门极生效和 121 个细档中点，再准备两档 0.200005 s 长窗。
[PLL 短窗记录](../../validation/cases/grid_connected_vsc_pll/short_reference_report.json)

2026-11-22。按已冻结协议启动隔离的 PSCAD 5 µs 短窗，原生采集到 605 µs。构建后先核对 19 条支路、差分电压和 MainOut 到 MainDyn 的门极路径，再运行一次。保留原始 INF、五个 OUT 和 32 列 CSV，并独立复算六个 PLL 样本及下一门极拍。粗档通过后再做 2.5 µs 短窗和独立长窗。
[接入参考协议](../../validation/cases/grid_connected_vsc_pll/reference_protocol.json)

2026-11-22。29 号已验收，正式新增共 11 个。PLL 接入沿用 29 号的 19 条支路、三相差分电压、100 µs 求解后采样和下一 5 µs 门极生效。以 11 号的离散更新顺序为依据，先冻结初始角偏差、采样变量、角度与频率的锁定窗口及限值。再取得原生 PSCAD 短窗并扩至两档长窗，同时核对门极和电流跟踪。
[29 号验收报告](../../validation/cases/grid_connected_vsc_closed_loop/validation_report.json) · [既有 PLL 参考](../../validation/cases/pll_dynamic_response/README.md)

2026-11-22。四工况参考、PyCy 原型比较和成组验收均已通过。接下来实现 29 号已知角度 dq 电流环，复用 28 号的物理接线以及既有双 PI、dq 变换和载波。保留 28 号开环门极回调与现有验收行为。在正式入口中演示 100 µs 求解后采样、下一 5 µs 门极生效、细档半步保持、限幅和两轴积分回滚。用新入口重新跑四工况并对照已合格参考，覆盖两档时序、限幅恢复和独立实例状态，补齐中英文入口、图和报告后运行原回归。
[完整参考报告](../../validation/cases/grid_connected_vsc_closed_loop/qualified_reference_report.json) · [控制设计](../specs/algorithms/known-angle-dq-current/known-angle-dq-current-system-architecture.md)

若 Git 直连重置且 Windows 已有本机系统代理，可在仓库根目录借用该代理做单次推送。2026-11-22 已在本机实测成功。

```powershell
$github = [uri]'https://github.com'
$systemProxy = [System.Net.WebRequest]::GetSystemWebProxy().GetProxy($github)
if ($systemProxy -ne $github -and $systemProxy.IsLoopback -and $systemProxy.Scheme -in @('http','https') -and !$systemProxy.UserInfo) {
    git -c safe.directory=D:/VibeCoding/PyCy_EMT_Lite -c "http.proxy=$($systemProxy.AbsoluteUri)" push origin HEAD:refs/heads/codex/emt-examples-longterm
}
```

2026-11-22。细档数值参考点对照已通过原电气判据。沿用已核验的网表，下一项单独冻结角度算术对照。在细档用整数步号 (j) 计算 (r = (3j + 5000) mod 20000 - 10000)，以 (pi r / 10000) 计算正余弦并保留原角度日志。判据以独立高精度配置角复算，继续沿用 1 pV 控制限值和原 19 项全点电气判据。再依长窗协议验证粗档、仅 d 阶跃、成组比较和教学候选。
[数值参考点实测](experiments/c1_pscad_reference_point_trial_20261122.json) · [冻结长窗协议](../../validation/cases/grid_connected_vsc_closed_loop/reference_protocol.json)

2026-11-19。已按用户指令暂停，所有本轮原生仿真均闭场。恢复后先核长窗冻结提交 587cb54、状态文件和两档失败收据。优先准备求解器数值参考点平移的独立 PSCAD 对照。保留以交流中性点为基准的原生差分观测、同一物理网络和全部原判据。原生准入前核对 19 条支路、45 个输出和 8 路差分电压。若 MathWorks 可正常签出许可，也可恢复原 Simscape 路线。
[冻结协议](../../validation/cases/grid_connected_vsc_closed_loop/reference_protocol.json) · [长窗记录](experiments/c1_known_angle_dq_pscad_full_20261119.json)

2026-11-19。5 µs 和 2.5 µs 短闭环已完成真实 PSCAD 与 Python 对标。细档合格运行的稀疏求解门限为 1。准备完整商业参考时先核两档实际生成参数和原电路，逐档取得通过原电气判据的长窗波形。短窗 23 项同档误差和 12 路实际门极、电阻比较可复用。
[粗档对标](experiments/c1_known_angle_dq_pscad_feedback_20261118.json) · [细档和长窗记录](experiments/c1_known_angle_dq_pscad_feedback_fine_20261119.json)

完整参考建模前另封双档协议。主工况在 40 ms 和 80 ms 加入 d、q 指令，于 110–160 ms 取三个 60 Hz 周期。仅 d 阶跃的配对工况在 70–120 ms 取三个周期。各轴周期平均误差目标沿用 0.4 A。两档均以本档测量闭环，核对全部电气点和施加时序，再按各自步长比较跨平台波形。跨步长比较须在原生长窗运行前固定。正式示例沿用28号桥的接线、现有 PI 和 dq 变换，新增内容集中在反馈采样和参考生效时序。

2026-11-18。已知角度dq控制探针已固定121行输入，R2025a与R2026b均在进入脚本前遇到MathWorks登录窗口。先在普通交互式R2025a确认登录及Simulink许可，再从本仓运行修正Sqrt块的入口。入口另建隔离目录并检查实际原生输出。控制探针通过后，再接短Simscape电气网络验证波形和采样次序。
[启动记录](experiments/c1_known_angle_dq_native_startup_20261118.json)

```powershell
& .\.tmp\longterm\resume_c1_native_controller_probe_releases_20261118.ps1 -Release R2025a
```

2026-11-18。Windows和WSL2 Ubuntu全量、24个教学入口、发行包与库外安装均已实测。分支上次托管CI为43856421332，两套runner均因账单锁未启动。账户恢复后在开发分支运行一次 `gh workflow run ci.yml --ref codex/emt-examples-longterm`，保存对应提交、两套runner实际步骤和测试产物。
[测试记录](experiments/f1_ubuntu_a777c00_20261118.json) · [CLI与发行包记录](experiments/f1_cli_wheel_cbdc9b1_20261118.json)

2026-11-18当前。28号开环已验收，C1下一项为已知角度dq电流环。先从已合格的本地Simscape物理网络建立真实PI控制参考，固定前馈测量点、dq相角和符号、初始积分状态、限幅、采样顺序及一拍生效约定。先核t=0、独立d/q阶跃和限幅释放，再冻结完整双步长验收方案。复用既有PI、dq变换、门极和CaseDefinition流程。
[28号验收报告](../../validation/cases/grid_connected_vsc_open_loop/validation_report.json)

2026-11-18当前：82923已exit0，完整粗档精度干预通过两套原19门，127.072s，峰值约290.8MiB，自有进程已退出。见[研究记录](experiments/c1_decimal80_precision_intervention_20261118.json)。下一项在忽略目录临时替换raw求解为普通LU加一次准确残差修正，先固定合同再跑完整粗档。math.sumprod输入需显式Python float，并把b与乘积放入同一次累加。当前局部probe在3个历史18维系统接近D80解，但极端输入仍有NaN/下溢边界，正式core修改前须确定范围处理、原始坏解拒绝和初始化补解行为。probe路径及hash在本记录。正式源码120及2依赖仍匹配1566项既有回归快照。

2026-11-18当前：全点驱动分解已完成，见[记录](experiments/c1_observed_forcing_ledger_20261118.json)。14180已exit0，11.261s，峰值约50.8MiB，自有进程已退出。下一步把每个重放步由原float stamp和当前float历史生成的A/b交给Decimal80求解，再回float进入既有状态更新。合同、脚本、源快照和输出目录另行冻结后，运行完整40002点及双路原19物理门。当前处于单因素对照准备阶段，正式候选仍待验收。

2026-11-18：用户已恢复长期任务。已核本地与远端HEAD均为7a10fc9，120个Python文件及2个依赖与既有1566项测试快照一致。当前继续实现全点误差驱动分析器，随后用既有轨迹进行离线分析。新增完成9，C1进行中。以下暂停记录保留为历史。

2026-11-17：已按用户要求暂停。HEAD为7a10fc9；本轮仅恢复核对与账本方案/公式静审，分析器和新纯检查尚未落盘，未启动全点账本、求解或仿真。子任务已停止。暂停记录已保存在忽略目录，五状态仅本地更新、未提交；等待用户明确恢复后再继续。新增完成9，28号候选未验收。

2026-11-16当前：先核五状态、实际Git与[候选FAIL报告](../../validation/cases/grid_connected_vsc_open_loop/validation_report.json)。checkpoint为已推送的研究快照8386c4e，其父提交bbb1e2d为独立步长修复；恢复时交叉核实际后续提交。1566项含slow通过覆盖source_snapshot3950a1cd的120源码及2依赖；后续仅文档/状态更新。63596和17585均终态，无剩余运行，不复用已消耗manifest。

1. 下一项仅做已存40002点的驱动账本：读取忽略目录c1_fixed_h_zero_solve_ledger_plan_20261116T154539272172Z/plan.json，execution_authorized=false。先独审公式、初值与实际state/h，写分析器并定向验证，再按新HEAD另封ROOT执行包；当前没有分析器或新求解器改动。
2. 账本区分组装系数、求解残差、历史构造和输出相减对交替模态的累积作用；零新solve/trajectory/native，不删点、不投影、不换积分法、不改原2µV门。观测分解不能冒充干预因果。必要的后续单因素轨迹须另封协议，不直接改公共求解器。
3. 28号仍未验收，新增完成9/C1进行中。已完成默认独立运行、两路完整比较、图和项目回归；后续修复必须重新冻结并完整重验，物理门及Git验收全部齐备才计完成。教学保持161行、现有16元件与CaseDefinition链，无新依赖/框架。
4. 早先远端直连查询连接重置，随后常规推送成功，8386c4e及父提交已在开发分支；下次按实际HEAD和远端交叉核对。F1保留旧精确HEAD账单锁证据，本轮没有新CI观察。

## 已记录里程碑

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
