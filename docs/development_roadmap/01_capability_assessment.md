# 当前能力与算例覆盖重新评估

评估日期：2026-11-04（Asia/Shanghai）。生产基线 `a03a450340797771099fceb5ec77137bc7f681c2`，版本 0.1.1；工作分支 `codex/emt-examples-longterm`。开始时工作区干净，origin/main 与本地 main 均指向上述提交。未发现仓库或父目录 AGENTS.md。本次工作在独立分支进行，保留既有编号、API、积分方程与默认参数。

## 1. 结论及证据分层

现有模型足以支持近期基础电路、线路、受控桥及单站变流器教学，当前主要缺口是可追溯的外部数值参考和独立对比流程。无需先重构 MNA，也无需重新实现已有 SPWM、PLL、dq 控制或 LCL 元件组合。

本报告把以下证据分开使用：源码中真实的方程与状态；正式测试的解析、独立 ODE、KCL/KVL、能量及细化判据；本轮实际运行结果；历史记录；真实 Simulink/PSCAD 对标。前四项均不能代替第五项。A 类表示在声明的模型范围有充分内部验证，**不表示商业平台对标完成**。

本轮按目录阅读了 core、components、controls、converters、machines、events、analysis、io、visualization 与 cases 的实现，并逐个核对全部 14 个现有算例；测试按其真实断言核对数值能力，未将“文件中存在测试”直接视作已证明。历史线索包括 [第一轮审查](../reviews/full_project_audit.md)、[实施记录](../reviews/implementation_log.md)、[第二轮审查](../reviews/round_2/deep_audit.md)、[第二轮独立验证](../reviews/round_2/numerical_validation.md)、[第二轮实施记录](../reviews/round_2/implementation_log.md)。历史修复状态以当前源码及测试为准，旧问题清单不自动转为新待办。

## 2. 本轮基线执行

基线由主执行进程运行，原始日志在忽略目录 `.tmp/longterm/`。首次运行使用原 `.venv` 的 Python 3.14.0rc3；依赖版本为 NumPy 2.5.2、SciPy 1.18.0、Matplotlib 3.11.1、pytest 9.1.1、mypy 2.4.0、Ruff 0.16.10。以下均为本轮实际结果。

| 检查 | 当前实际证据 |
|---|---|
| Ruff：`ruff check pycy_emt_lite examples tests` | 通过，0.286 s；`.tmp/longterm/baseline-ruff.log` 为 `All checks passed!` |
| mypy：`mypy` | 39 个源文件通过，2.066 s；`.tmp/longterm/baseline-mypy.log` |
| pytest（含 slow） | **1118 passed，175.68 s**；`.tmp/longterm/baseline-pytest.log`、`baseline-tests.xml` |
| 默认算例 | `.tmp/longterm/examples.json`：现有 14/14 进程退出 0，Agg；01–17 各约 1.56–9.06 s，18 FAST 约 87.82 s |
| 参考软件/许可 | 单独探测并在参考目录登记；发现安装路径不等于实际可运行 |

随后将验证环境切换为本机已安装的稳定 Python 3.14.5，在以下项目内目录离线按锁文件安装 27 个包：

```powershell
$env:UV_CACHE_DIR = '.uv-cache'
$env:UV_PYTHON_INSTALL_DIR = '.uv-python'
$env:UV_PROJECT_ENVIRONMENT = '.tmp/venv-py3145'
$env:UV_PYTHON_DOWNLOADS = 'never'
uv sync --locked --offline --python .uv-python/cpython-3.14.5-windows-x86_64-none/python.exe
```

稳定环境的全量 pytest（含 slow）已实际完成：**1128 passed，160.97 s**，证据 `.tmp/longterm/stable-tests.xml`。该次包含原有 1118 项及本批公共比较工具新增的 10 项测试；当时尚未改变正式包源码。此结果属于本批开发后的稳定环境复验，不能倒写成初始提交本身包含 1128 项。后续新增算例及工具仍需按其最终文件状态重新检查。

本轮算例运行仅证明脚本可执行；FAST 严格控制精度诊断仍应保留。单次墙钟受并发任务影响，不作为性能基准。Linux/Windows CI 的历史成功也不代替当前工作分支的新一轮 CI。

## 3. 能力矩阵

分类：A 已支持且有充分内部测试；B 已支持但相关物理范围验证不足；C 可用已有元件组合；D 少量局部扩展；E 重要数值算法扩展；F 超出当前近期/中期范围。同一模型的不同工况可以分属不同类别。

| 功能/候选 | 分类 | 当前真实实现与验证依据 | 适用边界及下一步 |
|---|---|---|---|
| 线性 R/L/C、独立电压/电流源 | A | [basic.py](../../pycy_emt_lite/components/basic.py)；[基础测试](../../tests/test_basic_components.py)核对非零初值、RC/RL 解析曲线、RLC 全暂态、AC 相量、KCL/KVL、无损 LC 能量和共同采样点细化 | SI 单位；R/L/C 为正值，特定复合模型另有允许零值的规则 |
| TR / BE 与稠密 MNA | A | [simulation.py](../../pycy_emt_lite/core/simulation.py)、[solvers.py](../../pycy_emt_lite/core/solvers.py)；[求解器测试](../../tests/test_solvers.py)覆盖 rebuild/reuse/precompute 等价和拒绝路径 | 小网络；残差是后向误差，不能保证病态网络前向精度或派生电流的全部精度 |
| 初值一致性、事件插点及事件右侧 | A | [stamping.py](../../pycy_emt_lite/core/stamping.py)冻结 C 电压/L 电流，相关约束只求导一次；[事件](../../tests/test_events.py)、[时间](../../tests/test_time_grid.py)测试 | 起点仅 0，终点整步；不支持冲量或任意高阶 DAE；约束确需源导数时 callable 必须提供解析 derivative |
| 普通多支路/多电源线性网络 | C | 基础元件可连接任意节点；现有源方向、浮置电感星点、并联电容初值等测试已覆盖非单支路网络 | 仍需每个新拓扑的独立方程与非奇异性试验；无需新增网络基类 |
| 平衡三相电源及串联 RL 负荷/线路 | A | [three_phase.py](../../pycy_emt_lite/components/three_phase.py)；[三相测试](../../tests/test_three_phase.py)核对三相相序、解析启动、电流相量/RMS/P/Q | ThreePhaseSource 为平衡正序；线路各相独立，无互感 |
| 不平衡星形/三角形线性负荷 | C | 可逐相/相间使用基础 RLC；基础节点拓扑允许浮置中性点 | ThreePhaseLoad 本身每相同参数，不应修改它的数学方程来伪装不同相参数；需独立相量/KCL 与外部模型 |
| 接地星形并联 RLC（额定 P/QL/QC 换算） | A | ThreePhaseParallelRLCLoad 实际换算固定 G/L/C；三相测试核对六状态独立分段 DOP853、故障、KCL 和时间细化 | **恒导纳**，不是恒 P/Q 非线性负荷；零有功时参数输出中的 R=Infinity 是明确格式边界 |
| 故障、断路器、三相短路/单相接地 | A | [switching.py](../../pycy_emt_lite/components/switching.py)、标准事件；例 06 由分段 RL 解析式核对，例 07 由电阻分压核对 | 有限故障电阻；开断不自动提供电弧/吸收回路；例 07 无线路储能/相间耦合，不是完整零序故障模型 |
| 单相 π、分段 π、三相 π | A | [lines.py](../../pycy_emt_lite/components/lines.py)；[线路测试](../../tests/test_line_models.py)核对串流/端流、二端口相量、离散能量、空间/时间细化 | 三相 π 各相独立；无频率相关、互感与电晕；分段线发送/接收输出是首/末段串流，非含端电容的总端流 |
| Bergeron 行波及反射 | A | 同上；测试检查到达前无响应、匹配/开路/短路、整步波前、事件右侧历史 | 固定网格且 τ/h 为正整数；负时间历史零，衰减是教学系数；三相无模量变换/相间耦合 |
| 线性单相/三相两绕组变压器 | A | [transformers.py](../../pycy_emt_lite/components/transformers.py)；[变压器测试](../../tests/test_transformers.py)核对理想变比、漏阻抗、四种 Y/D 接线相移、励磁 DC、能量及细化 | 变比为绕组相电压比，漏阻抗一次侧折算；三相为独立铁芯支路；二次 Δ 需要正漏阻抗确定环流 |
| 显式滞后的饱和励磁近似 | B | 按上一时刻磁链选择 Lm/Lsat；现有测试含单向跨拐点分段 λ–i 和步长细化 | 未验证回程/周期/非线性能量/磁滞/真实涌流；本任务不据其类名扩展复杂饱和算例 |
| 外部受控双向开关 | A | [power_electronics.py](../../pycy_emt_lite/components/power_electronics.py)：Ron/Goff 电导模型；[电力电子测试](../../tests/test_power_electronics.py)核对门极、导通及电流消去保护 | 非自动二极管；无正向压降、恢复、电容、损耗曲线和死区；Ron 不能任意趋零而忽略浮点精度 |
| 单相半桥/全桥、同步 Buck/Boost | C | 可用 IdealSwitch、RLC 及独立源组合，SPWM 辅助已存在 | 必须事先确认电感续流路径与互补时序；“同步”不允许替代真正自动二极管；未在本报告中声称已获外部参考 |
| 三相两电平 SPWM + RL | A | **已存在例 12**；测试核对浮置星点、互补门极、导通压降、RL 基波阻抗、5/2.5/1.25 μs 网格敏感性 | callable 门极按网格采样，不自动定位连续载波交点；平均基波只作解析参考，非真实另一平台的开关波形 |
| L、LC、LCL 滤波器 | A/C | [filters.py](../../pycy_emt_lite/converters/filters.py)返回基础元件列表；独立 ODE、KCL、TR/BE 能量与细化测试已有 | 单相组合可按三相复制；尚无独立初级滤波教学脚本，不能将缺少脚本误称缺少元件实现 |
| PI、低通、延时、坐标变换、SRF-PLL | A | [controls](../../pycy_emt_lite/controls/)、[控制测试](../../tests/test_controls.py)：采样时刻、PI 饱和恢复、PLL 独立相差 ODE | Clarke/Park 丢弃零序；PLL 归一化为 max(|vd|,|vq|,1 V)，不外推弱网/负序/失压适应性 |
| VSC 的 PLL、dq 电流、Vdc/P/Vac 外环 | A/B/C | [vsc.py](../../pycy_emt_lite/controls/vsc.py)、[HVDC 测试](../../tests/test_three_terminal_vsc_hvdc.py)已有开环桥、单站、双站与三站；第二轮已补电流圆/电压矢量/亚伏/NumPy 参数测试 | 单站可复用但测量字段约定耦合站名；P 正向 AC→converter；Vac 外环不是独立 Q 指令模式；FAST 严格 RMS 精度未达标 |
| 独立 Q 指令/通用 dq 引用、固定控制采样周期 | D | 当前 VSCController 使用 Vac 外环，on_step 每求解点调用且使用实际 dt；已有保持命令机制 | 仅当具体可验证算例需要时增加小接口；不预先引入调度框架 |
| 简化新能源固定 DC 接口、双端 VSC-HVDC | C | 现有独立源、六开关桥、PLL/dq、双极 RLC 线路和双站测试可复用 | 固定 DC 源不等于 PV 阵列/电池/MPPT；桥为外控双向开关；需明确简化且逐例真实对标 |
| GFM 下垂控制 | D/B | 基础 PI、测量与控制回调可承载；当前没有已验证 GFM 控制器或孤网闭环例 | 先独立方程与外部参考可行性，不把 GFL 的 PLL 改名为 GFM |
| 三/五节点及拓扑简化 IEEE 9 节点 | C/B | 现有 MNA 与线性线路/源可组合，非新增求解算法 | 不自动称为完整标准动态 EMT 模型；要说明被替换的机组/负荷/初始化，先做小网络验证 |
| 两种同步机教学模型 | A/B | [machines](../../pycy_emt_lite/machines/)、[经典机测试](../../tests/test_synchronous_machine.py)、[Park 测试](../../tests/test_park_synchronous_generator.py)与例 10 | 经典机含定子 RL/显式机械；Park 忽略定子快暂态，用平衡代数 dq 端口，不能用于不平衡短路/DC 偏置/次暂态；不扩张为完整磁链 EMT 机 |
| 自动理想二极管换流/分段线性半导体 | E | 无当前实现；状态依赖电压/电流约束需要非光滑求解/状态一致性，门极函数仅依赖时间或保持量 | 远期候选；普通二极管整流桥、非同步 Buck/Boost 不进入近期交付 |
| 通用 Newton/非线性 MNA、完整 MMC/大机组、IEEE 39/118、稀疏/GPU | F | 当前无对应通用求解/模型，实现也不为已有近期例所需 | 独立远期研究，禁止为“预留”重构当前架构 |
| 结果保存/基础分析/绘图/报告 | A | [results.py](../../pycy_emt_lite/io/results.py)、[metrics.py](../../pycy_emt_lite/analysis/metrics.py)、[visualization](../../pycy_emt_lite/visualization/)、对应测试 | CSV 不保存事件/完整元数据；连续指标需正时长且不能跨只有右侧值的事件区间；一般不平衡/畸变容量不由 sqrt(P²+Q²) 完整定义 |
| 跨平台参考数据、映射、误差验收与 provenance | D | 现有 plot_result_comparison 仅同列多结果曲线，未管理来源、单位、信号映射、固定验收窗口与外部运行日志 | 当前最应优先开发的公共验证能力；不放进各教学脚本重复实现 |

## 4. 现有算例逐项判断

| 现有脚本 | 当前教学现象及内部依据 | 扩展判断 |
|---|---|---|
| 01 R | Ohm 定律、MNA、电源电流方向 | 保留，作为安装冒烟与验证流程最小测试 |
| 02 RC / 03 RL | 一阶储能、时间常数、零初值、解析指数 | 不再重复造另一套同参数充电例；可先给现有例补真实外部数据 |
| 04 RLC / 17 AC RLC | 二阶阶跃与正弦稳态/启动，整曲线与相位 | 二者激励和学习目标不同，保留；不把稳态相量用于整个启动暂态 |
| 05 平衡三相 RL | 相序、相量分压、滞后与 P/Q | 有意义的后续是非平衡/中性点教学，需先外部参考 |
| 06 三相故障 | 有线路 L，电流连续、故障清除过电压 | 已覆盖施加/清除，不复制；增加复杂度前核对吸收回路和最快时间常数 |
| 07 单相接地 | 三相独立电阻分压，故障相与健全相 | 与 06 的动态模型不同；可在文档明确其最简适用边界 |
| 08 π 线 | 端电容与串流、相位与能量 | 已有分段/Bergeron 元件但无正式独立教学脚本；有参考后补行波/反射比再造 π 稳态更有增量 |
| 09 单相变压器 | 理想变比、漏阻抗、励磁 DC、总输入功率 | 三相 Y/Δ 或“源—变—线—负荷”有增量，但需参数/相位严格映射 |
| 10 Park+AVR+调速器 | 平衡初始化、负荷阶跃、机电和控制分工 | 位于较后学习单元；不把其代数定子替换完整 EMT 同步机 |
| 11 独立 PLL | 无 MNA 的角度/频率/q 电压锁定 | 可以独立真实 Simulink 控制框图对标；不强行套网络案例流程；现有纯控制例无保存开关 |
| 12 两电平 SPWM | 六开关、浮置星 RL、保持延迟、开关纹波/基波 | 已满足候选“三相 SPWM+RL”主题，优先对标或扩展滤波，不能登记为待从零开发 |
| 18 三端 VSC-HVDC | 三站 PLL/dq、双极 DC 网络、故障与功率/储能账 | 复杂度高，先以现有单桥→单站→双站测试拆分学习。参考参数与控制/缓冲有差异，不能直接宣布原商业 benchmark 等价 |

01–04 的接线、源码导航和单参数练习已较完整；其逻辑结构可沿用。当前例号 13–16 的空缺是历史明确移除，不应仅为补齐序号恢复。12→18 的知识跨度确实较大，但 README 已有单桥/单站/双站测试阅读路线；新增独立单站脚本必须以真实参考验收为依据。

## 5. 架构及近期决策

1. 复用 `CaseDefinition → Circuit → Simulator → SimulationResult`。新脚本集中参数、创建新实例、定义事件/控制、执行、摘要、PyCy 自身绘图；保持简单，不增加算例基类或插件系统。
2. 独立建立 `validation/`，复用现有结果导出，保存来源/版本/hash/参数/单位/方向/初值/窗口/验收阈值。对比逻辑不污染教学脚本；阈值应先于实现或参考运行冻结。
3. 首个正式新增例由可获得并实际运行的参考决定。已有基础例补对标、已支持模型的教学展开优先于新增算法。对参考状态严格区分 discovered/downloaded/inspected/runnable/reference_ready。
4. 若只有解析关系或 Python 独立 ODE，标记为内部验证；若 MATLAB/PSCAD 不能运行或没有真实数据，算例保持待验证，继续不依赖该软件的开发。
5. 基线 `.github/workflows/ci.yml` 的 push 仅匹配 main。开发分支推送本身不触发该配置，应在正式实现阶段最小开放该分支或提供手工触发，并核验真实远端结果；配置修复与远端执行状态另在进度文件登记。
6. 已知 R2-003 为 t=0 标准事件覆盖非法状态并将 bool() 写入 before 的输入/日志边界；原记录明确尚未修。它不影响合法二值电路方程，也不是扩展示例前必须大改事件系统的依据，可单独任务修复。

本报告没有新增或替换物理方程，没有用测试通过数或模型类名扩张能力。下一阶段以 [参考目录](02_reference_catalog.md) 和 [可行性实测](03_verified_feasibility.md) 决定实际实施顺序。
