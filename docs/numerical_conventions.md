# 数值约定

[English](numerical_conventions.en.md) · [运行入口](../README.zh-CN.md) · [模型与验证](models_and_validation.md)

本文集中说明当前程序的方程、时间、初值、事件和指标约定。各模型的专用方程及验证证据见模型文档。
需要逐项理解公式来源、局部矩阵和状态更新时，阅读[元件推导](component_derivations.md)：第 1–5 节给出基础盖章与 RLC 手算例子，第 13–15 节展开一致初值、事件循环和离散能量。

按问题阅读：不清楚调用顺序时从第 1 节开始；结果时刻与预期不同时看[时间网格](#time-grid)；
第一行结果有疑问时看[一致初值](#initialization)；故障切换前后有疑问时看[事件](#events)。

<a id="source-route"></a>

## 1. 从元件到结果

`CaseDefinition` 保存元件、仿真配置、事件和输出选项；`run_case()` 创建 `Circuit` 和 `Simulator`。
小电路可直接使用这两个对象。电路内部准备节点及额外支路未知量，各元件把自己的方程写入同一个
`A x = b`，求解后更新历史量并记录 `SimulationResult`。这种局部写入称为 stamp。
没有另一个编译入口、仿真会话或检查点恢复流程。

每次运行都应重新创建元件、电路和仿真器。一个 `Simulator` 只能运行一次，已经归属某个仿真器的电路
不能转交另一个仿真器；失败后也应重新构建。这样可避免旧电感、电容和事件状态污染新计算。
`SimulationResult` 是数据，不是可继续积分的状态快照。

| 阅读顺序 | 在文件中搜索 | 需要弄清的问题 |
|---|---|---|
| [cases.py](../pycy_emt_lite/cases.py) | `CaseDefinition`、`run_case()` | 示例的元件和配置怎样交给仿真器，结果怎样交给摘要、绘图和保存？ |
| [circuit.py](../pycy_emt_lite/core/circuit.py) | `Circuit._prepare()` | 节点电压和额外支路电流怎样编号？ |
| [basic.py](../pycy_emt_lite/components/basic.py) | `Capacitor._companion()`、`stamp()`、`update_state()` | 电容公式怎样变为本步方程，何时保存历史电压和电流？ |
| [stamping.py](../pycy_emt_lite/core/stamping.py) | `add_conductance()`、`add_current_source()` | 两端元件对矩阵和右端项的正负号如何写入？初值时再读 `_InitialConditions`。 |
| [simulation.py](../pycy_emt_lite/core/simulation.py) | `Simulator.run()`、`_solve_step()`、`_assemble()` | 谁依次调用元件盖章、求解和状态更新？初值及事件点有何不同？ |
| [solvers.py](../pycy_emt_lite/core/solvers.py) | `DenseLinearSolver.solve()` | 怎样解 `A x = b`，并检查非有限量与残差？ |
| [results.py](../pycy_emt_lite/io/results.py) | `SimulationResult.series()`、`to_json()` | 怎样用字段名读取数组、将结果保存到文件？ |

表中带下划线的函数是内部实现，供阅读；编写算例仍使用 README 中的公开接口。
想逐行对照电容，可按[元件推导的 RC 阅读路线](component_derivations.md#reading-map)连接示例、公式和测试。

## 2. 单位、方向与最小 MNA

电路采用 SI 单位：时间 s、电压 V、电流 A、电阻 Ω、电感 H、电容 F；频率通常用 Hz，角度用 rad。
同步机标幺量和 PLL 的 rad/s 单位在模型文档中单独说明。
`0`、`gnd`、`ground` 是参考节点别名，地名不区分大小写；普通节点名仍区分大小写。
三相母线接地时三相端点都连接参考地，不生成一个同名普通节点。滤波器、分段线和电机生成的内部节点
不得与该模型的外部端点或参考地重名；修改接线或名称以消除冲突，不能靠重名旁路实际阻抗。
这里的冲突检查只针对生成该节点的模型自身，不保留全局私有命名空间。同名普通节点始终连线：
例如另一元件显式连接 `LINE:internal:1`，就是接入分段线 `LINE` 的第一个内部节点，可用于有意抽头或诊断。
自动名称在结果中可见；编写外部接线时应避免无意复用这些名称，重命名模型后也需同步修改有意抽头。
未知向量由非参考节点电压及电压源、电感等所需的支路电流组成。
元件名称必须唯一，所有结果字段也必须唯一。记录结果行时发现重名字段会立即报错，并给出元件、时刻和修复方法。
例如节点 a=10 V、b=5 V，跨接 a/b 的电容若也叫 a，其端电压会与节点字段 `v:a` 冲突；
将电容重命名为 C 后，`v:a=10 V` 与 `v:C=5 V` 各自保留。复合元件展开后的字段同样不能与其他元件重名。

两端元件 `p → n` 定义 `v=Vp−Vn`，电流也由 p 流向 n。电压源供电时，记录的源支路电流通常为负；
不能直接把 `v*i` 当成向外送出的功率。三相节点通常为 `bus:a/b/c`，输出用 `v:节点`、`i:元件`；
复合元件可能另有支路/绕组字段，应按对应模型说明解释。

电导 G 在节点子矩阵写入 `A[p,p]+=G`、`A[n,n]+=G`、`A[p,n]-=G`、`A[n,p]-=G`。
从 p 流向 n 的独立电流 I 写入 `b[p]-=I`、`b[n]+=I`。涉及参考节点的行列省略。
理想电压源引入电流未知量 k，在节点 KCL 中写入 `+ik/−ik`，另加一行 `Vp−Vn=Vsource`。
因此 MNA 能直接容纳电压约束，不需要将理想电压源替换为很大的电导。

对长度为 h>0 的积分区间，令下标 0 表示区间左端：

| 元件与方程 | 梯形法 `trapezoidal` | 后向欧拉 `backward_euler` |
|---|---|---|
| R：`i=Gv` | `G=1/R` | 相同 |
| C：`i=Gv+Ihist` | `G=2C/h`；`Ihist=−i0−Gv0` | `G=C/h`；`Ihist=−Gv0` |
| L：`v−Req i=Vhist` | `Req=2L/h`；`Vhist=−Req i0−v0` | `Req=L/h`；`Vhist=−Req i0` |

串联 R–L 的支路方程为 `v−(R+Req)i=Vhist`。电容用并联电导与历史电流表示，电感保留支路电流未知量。
求解后才保存这一步的端电压和电流；不能在 stamp 时提前覆盖历史量。
同步机机电/控制状态采用单独声明的显式推进顺序，不能由全局 `method` 推断其积分阶次。

<a id="time-grid"></a>

## 3. 时间网格和参数

`SimulationConfig(time_step, stop_time, start_time=0, method="trapezoidal", event_time_policy="insert", record_every=1, linear_solver_mode="rebuild")`：

- `time_step` 必须是有限正实数；`stop_time` 必须是有限非负实数；布尔值不作为数值接受。
- 当前只支持 `start_time=0`。`stop_time=0` 合法，只记录一致初值一行。
- **停止时间必须是基本步长的整数倍。** 例如步长 100 μs、停止时间 250 μs 在计算前报错；
  改成 200/300 μs，或选择能整除 250 μs 的步长。程序不缩短最后一步来迁就终点。
- 只吸收浮点表示造成的微小舍入差异：正时间比较使用成对 8 ULP 容差，并统一到标准网格值；
  零时刻只与零相等。这不允许任意近似对齐。
- `method` 只接受表中的两种方法。普通 R/L/C 参数必须为有限正实数；复合模型是否允许零阻抗由模型说明决定。
- `linear_solver_mode` 接受 `"rebuild"`（默认，每次重新 LU 分解）、`"reuse"`（实际 A 完全相同时复用上一份 LU）或 `"precompute"`（小型网络启动预分解）；不改变积分方法或时间网格。含大量开关器件的网络选择前两种，第三种的限定范围见[预计算规则](#network-precompute)。

元件参数按 `numbers.Real` 接受 Python/NumPy 实数，转换为有限浮点数后检查范围；布尔值、可转换字符串和复数不接受。
`time_step` 不支持非正规浮点数（小于 `numpy.finfo(float).tiny`）。在分配前限制基础步数和基础步数加事件数
均不超过 5,000,000，分段线不超过 1,000 段，`SampleDelay` 不超过 1,000,000 点。超过限制需缩短算例或修正输入；
这些是避免意外大分配的上限，不代表接近上限时必然有足够内存。

`Circuit` 准备后不得直接增删/替换元件、改元件名或端点；PLL 构造后不得改其增益、额定频率、初始角及频率限幅，
采样延时不得改长度。发现配置与已创建对象失配时明确报错，需重建对象。合法开关事件、门极及控制状态更新保持支持。
`IdealSwitch` 的关断电导不得大于导通电导，允许 `Goff=0` 和两者相等；启用饱和时 `Lsat≤Lm`，相等时退化为线性。

`insert` 允许显式事件在基本网格之间插点，因此实际区间 h 可不相等。所有储能历史与统计指标必须使用实际时间。
终点整步要求与事件插点是两个独立约定。Bergeron 历史另要求固定网格和整步传播时延。

`record_every` 必须为正整数，默认保存每个求解点。设为 N 时按求解点序号每 N 点保存一次，
初始点、显式事件点和终点始终保留；插入事件会参与序号计数，因此输出不一定等间隔。
它仅减少结果行，网络、状态更新和控制回调仍在每个求解点执行。
`result.time_step` 仍是基础 EMT 步长；绘图和统计读取实际 `time` 列。

### 可选步后控制回调

`CaseDefinition(..., on_step=callback)` 或 `Simulator(..., on_step=callback)` 连接显式控制。
回调接收当前只读测量行，返回新增字段的映射（无字段时返回 `{}`）；键须为非空字符串且不得与已有字段重名，值须为有限实数，布尔值不接受。
执行顺序为求解和状态更新、事件右侧一致求解、一次回调、选择保存结果；同刻事件不重复推进控制器。
回调在 t=0 也执行，此时只观察/初始化，不能给要求正间隔的 PI/PLL 传零步长。
控制器保留的命令通过元件 callable 作用于下一网络步；没有同一步代数闭环。
回调需从相邻 `row["time"]` 计算实际间隔，并随新算例重新创建状态。
示例见 [三端 VSC-HVDC](three_terminal_vsc_hvdc.md)，默认 `on_step=None` 保持原流程。

<a id="initialization"></a>

## 4. 一致初值

当高压储能与近零电压约束并存时，LU 消减误差可能使一致解未通过逐行约束检查。
此时只补求一次残差方程 `A δx=b−Ax`，再使用原初值阈值复查；不放松约束或允许冲激。

`t=0` 先应用零时刻事件，再解初始网络并记录；不会先积分一个正步长，也不会把 h=0 代入上表。
电容保持 `initial_voltage`，电感保持 `initial_current`，默认均为零；同时从网络约束求出配套的电容电流、
电感电压与源电流，建立第一步所需历史。复合元件沿用内部储能支路的约定。

已有回归包括以下可核对的初值：

| 电路 | t=0 的一致状态与输出 |
|---|---|
| 1 V 电源、1 Ω、1 F 串联，`vC(0)=0.25 V` | `iC(0)=0.75 A` |
| 1 V 电源、1 Ω、1 H 串联，`iL(0)=0.2 A` | `vL(0)=0.8 V` |
| 3 A 注入并联 1 F、2 F，电容初始电压相同 | 电流分别为 1 A、2 A |
| 相同电感接浮置星点，外端电压为 400/0/0 V，电流初值为零 | 星点初始电压为 `400/3 V` |
| `1+3t V` 理想电压源并联 2 F，`vC(0)=1 V` | `iC(0)=6 A` |

最后一个例子需要电源导数来确定电容电流，可以直接运行：

```python
from pycy_emt_lite import Capacitor, Circuit, SimulationConfig, Simulator, VoltageSource

components = [
    VoltageSource("V", "n", "0", lambda t: 1 + 3 * t, derivative=lambda t: 3.0),
    Capacitor("C", "n", "0", 2.0, initial_voltage=1.0),
]
result = Simulator(Circuit.from_components("consistent_initial_state", components),
                   SimulationConfig(time_step=0.01, stop_time=0.02)).run()
assert abs(result.rows[0]["i:C"] - 6.0) < 1e-12
```

常量源的导数为零，三相正弦源提供解析导数。只有网络约束确实需要时，才要求 callable 独立源提供
`derivative`；不能一律用差分猜测或假定为零。理想电压约束与电容初值冲突、电流约束与电感初值冲突、
冗余理想源造成电流不唯一等情况应修正初值或实际接线。程序不自动加微小泄漏电阻，也不支持所有高阶代数约束拓扑。

<a id="events"></a>

## 5. 显式事件的左右侧

`FaultApplyEvent/FaultClearEvent` 修改 `Fault.enabled`，`BreakerOpenEvent/BreakerCloseEvent` 修改 `Breaker.closed`。
`time` 是要求执行的时刻，`target` 是电路中元件的 `name`。事件时间和标准事件目标在首次求解前检查。
晚于停止时间的事件不执行，也不为其延长仿真。
标准故障事件只接受 `Fault`，标准断路器事件只接受 `Breaker`；不能把它们指向 `IdealSwitch` 来替换其门极函数。
其他操作需按现有 `SimulationEvent` 接口定义事件。

| `event_time_policy` | 非对齐事件的处理 |
|---|---|
| `insert`（默认） | 在所要求时刻插入结果时间点 |
| `quantize_up` | 延后到下一基本网格点；日志保留要求时间与实际时间 |
| `require_aligned` | 计算前报错，提示对齐时间或选择其他策略 |

每个正时间事件点依次执行：

1. 用事件前拓扑积分到该时刻的左侧。
2. 按事件要求时间排序执行；要求时间相同的事件保持加入顺序。
3. 固定动态状态，用新拓扑求同一时刻的右侧网络。
4. 更新配套历史量，不再次推进时间或动态状态。
5. 只保存一行右侧结果；事件日志保留各次操作。

电容电压、电感电流在受支持的有限切换中连续；电阻电流、节点电压等代数量可以跳变。
若新拓扑要求储能状态瞬间改变或冲量，程序应报错，需修正接线、初值或采用有物理依据的有限阻抗。
零时刻及停止时刻事件也遵守一行右侧记录。普通 callable 电源和 PWM 门极边沿不自动转成显式事件，
所以本节机制不保证自动定位这些不连续点。

## 6. 指标使用真实时间

[analysis/metrics.py](../pycy_emt_lite/analysis/metrics.py) 把相邻结果点间的信号视为线性函数。
统计窗口边界落在区间内部时先线性插值裁剪；不能按样本数平均来处理事件插点后的非均匀网格。
对区间 h、端值 a/b：`∫x dt=h(a+b)/2`，`∫x² dt=h(a²+ab+b²)/3`。
两个信号相乘的积分为 `∫vi dt=h(2v0i0+v0i1+v1i0+2v1i1)/6`。
因此 RMS 是 `sqrt(∫x²dt/T)`，平均有功是 `∫vidt/T`；它们不是直接对采样平方值做梯形积分。

积分窗口必须具有正时长，时间必须有限且递增。窗口涉及显式事件跳变所在区间时，积分型指标拒绝计算，
因为只有右侧记录不足以恢复左侧极限；应选择不跨切换的窗口。该检查依赖 `event_log`，CSV 等缺少日志的数据需由调用者保证窗口不跨事件。
`peak_abs` 是采样点峰值，允许单点，
不声称找到连续波形真实极值。`voltage_sag_summary` 比较指定窗口 RMS 与额定值，不跟踪暂降持续时间。

三相瞬时有功为 `va ia+vb ib+vc ic`，包含零序贡献；无功采用幅值不变 Clarke 约定
`q=1.5(vβ iα−vα iβ)`。`sqrt(P²+Q²)` 与相应功率因数的常规解释限于平衡正弦情况，不能当作一般不平衡系统容量定义。
比较离散波形时应明确公共物理时间点、窗口、方向、单位和参考；细步长结果只能作为数值对照。

## 7. 报错后的修复

| 问题 | 修复方法 |
|---|---|
| 非整步停止时间、非法步长或起点 | 按第 3 节修正配置；不要容忍错误终点 |
| 输出字段冲突 | 根据报错重命名对应节点或元件，不能覆盖已有电压、时间或其他支路字段 |
| 控制/PWM 输入或门极非法 | 数值参数、采样和重置值使用有限实数；门极只用布尔值或数值 0/1 |
| 重复元件名、事件目标不存在或类型不匹配 | 使用唯一名称；把事件指向相应 Fault/Breaker |
| 重复运行或复用已占用电路 | 重新创建元件、Circuit 和 Simulator |
| 非法 R/L/C、变比、时间常数或控制限幅 | 按错误中的参数名和允许范围修正，核对 SI/标幺单位 |
| 初值冲突、需要电源导数 | 核对储能初值与理想约束；必要时提供解析 `derivative` |
| 矩阵奇异 | 检查浮置节点、重复理想约束及未确定的环流；不应把所有奇异性都归因于缺少接地 |
| 源值/矩阵/解非有限或残差异常 | 按错误中的时刻、元件或求解上下文定位，再检查参数尺度和步长 |
| 事件窗口统计不成立 | 选择切换前后各自不跨事件的物理窗口 |

错误检查不能证明模型物理正确。数值验证仍需初值、解析/独立参考、KCL、能量和步长收敛；
梯形法能量账使用区间平均电压/电流，后向欧拉还含数值耗散。具体已有证据与未验证项只在模型文档维护。

## 8. 求解保护、结果文件与输出预检

`Simulator` 在三种网络策略中都按原顺序每次装配 A/b，再求解最新 b。`reuse` 用完整矩阵精确相等判断失效，
不使用近似阈值，也不只看开关状态：参数、实际 h、饱和档位和 Park 电角度均可能改变 A。
缓存只属于一个 Simulator，最多保存上一份 LU；A1→A2→A1 要重新分解三次，不保留多拓扑历史。
初值/事件右侧增广矩阵也参与相同判断，现有一次修正使用该矩阵的 LU，不减少源/门极/状态/回调执行。
显式 `solver=` 的现有自定义后端在 `rebuild` 保持原行为；`reuse/precompute` 当前只接受 DenseLinearSolver 实例，否则在占用电路前报错。
`factorization_count` 为实际分解次数，`solve_count` 为实际求解次数；Simulator 每次新分解的 `reused_factorization=False`，
命中上一份分解（包括一致修正）时为 True。precompute 的准备分解也计入次数，循环内每次求解的该标志均为 True。
分解减少不代表全流程必然加速；三策略的准备/循环/总时间和进程峰值内存测量留到后续阶段。

<a id="network-precompute"></a>

预计算仅用于开关少、完整状态集合小且满足预算的网络。含大量开关器件的网络使用 rebuild/reuse，不能为使用预计算而缩减可达状态、改步长或扩大预算。
通用 Simulator 保留状态数和字节预算检查；不新增任意的开关个数阈值或自动选型。HVDC 示例入口另行明确拒绝 precompute。

`linear_solver_mode="precompute"` 当前核定固定参数 Resistor、Capacitor、Inductor、CurrentSource、VoltageSource、Fault、Breaker、IdealSwitch，
以及 ThreePhaseSource、ThreePhaseLine、不含饱和的 ThreePhaseTransformer 的精确类型。
自定义子类、其他组合线路/变压器、电机及带饱和的三相变压器仍在占用电路前报错，可选 reuse。
它用独立数值副本，保留参数与变量编号，将源值/导数及储能历史置零以形成系数矩阵；准备阶段不调用真实源/门极、事件、控制回调或状态更新。
真实求解仍读取最新源/历史量，并执行源导数要求、初值冲突和所有原有数值检查。
三相源副本先按合法原参数构造，再仅将私有副本幅值置零以消除 RHS/导数；原源的幅值检查和真实正弦/解析导数保持。
三相 RL 和线性变压器的内部历史/支路字典由构造器重新创建，不共享原组件的可变状态。

默认 `precompute_states=None` 枚举全部 Fault.enabled、Breaker.closed、IdealSwitch 导通状态的二值组合，包括当前固定的布尔门极。
`precompute_max_states=1024` 必须为正整数；状态数超限在枚举和分解前拒绝。
显式 `precompute_states` 是非空列表或元组，每个字典必须恰好覆盖电路中所有这些元件的名称，值为 True/False；不能遗漏名称或重复状态。
Simulator 接收时复制为内部不可变快照；之后修改外部列表/字典不改变声明。
显式集合可排除确定不会出现的奇异组合，调用者须保证覆盖实际状态；自动集合中任一矩阵奇异/欠定都会在时间推进前报错。

下面的小电路显式声明 S 的关断与导通两种状态，无需另设求解器或控制接口：

```python
from pycy_emt_lite import Capacitor, Circuit, CurrentSource, IdealSwitch, Resistor, SimulationConfig, Simulator

components = [
    CurrentSource("I", "0", "n", 1.0), Resistor("R", "n", "0", 2.0),
    Capacitor("C", "n", "0", 1.0),
    IdealSwitch("S", "n", "0", lambda t: 0.1 <= t < 0.2,
                closed_resistance=1.0, open_conductance=0.0),
]
config = SimulationConfig(time_step=0.1, stop_time=0.2, linear_solver_mode="precompute",
                          precompute_states=({"S": False}, {"S": True}))
simulator = Simulator(Circuit.from_components("finite_switch_states", components), config)
result = simulator.run()
assert result.series("state:S").tolist() == [0.0, 1.0, 0.0]
assert simulator.solver.factorization_count == 4
```

查表键包含实际 h、积分/一致求解类别和状态，积分方法固定属于本次 Simulator；矩阵族覆盖既有网格的全部正 h 及初值/事件一致增广矩阵。
相同完整 A 仅预分解一次，即使不同状态/求解类别可共用；运行时核对实际 A 精确相等，并复用同一 LU 做一致修正。
未知状态/h 或新系数在求解前拒绝，不能在循环中补分解或静默换成 reuse。查表读取 stamp 已保存的门极状态，不额外调用门极函数。
每步组装及一致约束的 QR/秩检查仍保留；此策略只减少网络 LU，不省略其他计算或数值保护。

私有数值预算为 1 GiB：先按状态数、全部 h、普通/增广尺寸估计 A、LU、主元、准备期去重键、查表键及临时数组空间，再创建；创建时累计实际数组/字节键 nbytes 复核。
这是数值存储与估计工作空间的限制，不是进程 RSS 保证；Python 对象及底层库实际峰值须按算例测量。
N4已测两个既有小网络的三策略及HVDC两策略；记录包含准备成本和进程生命周期峰值工作集，不能当作全部支持网络的内存保证，见[成本验收](audit_20261005/项目问题与改进计划.md#network-solver-n4)。
超过预算时应缩小仍完整的状态集合或选 reuse，不能为通过检查遗漏可达状态；提高 `precompute_max_states` 也不会解除字节预算。
此前 HVDC 核定发现 1024 状态及 15 种实际正 h 需要 16384 个不同矩阵，仅原 A/LU/主元就约 4.29 GiB。
目前按大量开关网络的使用限制，HVDC 入口在创建控制器和网络前直接拒绝 precompute，不再生成该状态族；缩短时间或关闭故障也不开放，见[HVDC范围](three_terminal_vsc_hvdc.md#network-solver-scope)。

`DenseLinearSolver.solve()` 与已有 `factorize().solve()` 都检查解有限性、缩放残差和求解诊断；后者保留多右端项能力。
残差阈值须为有限非负实数。残差反映后向误差，不能保证病态方程的前向误差或派生电流精度。
求解器可返回只读数组或复用缓冲；仿真器先复制，再做一致初值修正，不改写求解器持有的数组。
`last_diagnostics` 对应最近一次线性调用；若触发修正，它记录 `A δx=b−Ax` 的诊断。
修正后的初值另按原始网络约束验收，不能把修正方程的残差当作最终原方程残差。
按 `G(Vp−Vn)+Ihist` 求电流的支路另检查浮点表示分辨率：估计不确定度超过 `1e-7 A + 1e-3*abs(i)` 时明确拒绝。
这只针对电压差/历史项相消，不是完整误差界；约 1 pA 的电容误差低于该绝对尺度，不能据此承诺其相对精度。
程序不会静默改变电阻、加泄漏或增加网络未知量。状态更新、输出和回调执行失败会附元件/回调名、时刻、阶段并保留原异常链。

缺失信号在 `series()` 与 NPZ 中为 NaN，CSV 写为空字段，JSON 写为 `null`，读回统一为 NaN；分析指标拒绝非有限信号。
模型参数中无穷仍可表示缺省支路：JSON 写为字符串 `"Infinity"` / `"-Infinity"`，不写非标准数值常量；读回恢复浮点值，
合法旧 JSON 的裸 Infinity/NaN 仍可读。CSV 不能恢复完整配置和事件日志。JSON/NPZ 导入验证列名、形状、等长、实际时间与已有元数据；
时间须有限、非负且严格递增。损坏数据按文件、行/字段定位，不能截断长列或补齐短列后静默继续。
NPZ 业务字段不得使用 `__meta__`、`__columns__`、`file`、`allow_pickle`。无 `.npz` 后缀时 NumPy 自动追加，方法仍不返回路径。

`run_case()` 在仿真前验证图片种类、列数、保存文件名和输出路径；案例名须为单段相对目录名，图片可用案例目录内的相对层级。
检查路径归属、已有文件/目录冲突和图片格式；实际信号字段（含回调生成字段）仍在绘图时核对。绘图失败也关闭 Figure。
报告的 `figure_paths` 从调用时工作目录解释，再换算为相对报告目录的链接；标题、字段等显示文本做 Markdown 转义。
