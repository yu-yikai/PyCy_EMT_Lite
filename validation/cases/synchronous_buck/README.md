# 26：同步 Buck 电压闭环候选

**未验收候选：内部物理测试通过，真实参考自身精化失败，尚未进行候选商业比较；正式新增算例仍为7项。**
本例可用于学习与运行，当前结果不能称为已通过 Simulink 对标。默认电路、初值、更新顺序和误差限见
[参数](parameters.json)、[实现前协议](acceptance_plan.md)及[验收清单](manifest.json)。

## 电路与初值

用10个已有元件搭建30V降压回路，建议先熟悉02的储能初值和12的载波比较：

```text
30V(dc) -- [Supper || 100k] -- mid -- [L=1mH || 10k] -- out
                              |                       |
                       [Slower || 100k]       C=22uF || R=3.75 || Ipulse
                              |                       |
                              0                       0
```

两开关导通电阻均0.1Ω。每管的100kΩ电阻提供关断小电流路径，开关自身关断电导设为0；
电感并联的10kΩ支路也保留。`i:L`方向为mid→out，`v:out`为输出对地电压，负荷电流方向为out→0。

t=0两管关断，电感按直流短路、电容按开路计算初值。令
`Rdown=100kΩ || 3.75Ω`，则`UC0=30*Rdown/(100k+Rdown)`、`iL0=UC0/3.75`，
得到约1.124916mV和0.299978mA。它们由电路计算，不从商业文件读取；滤波和PI积分初值均为0，占空比初值0.01。

## 控制与观察

从15V参考减去输出电压，经1µs一阶低通、`Kp=0.5, Ki=200`的PI，再由外部Limiter限制至0.01–0.95。
PI内部不限幅，饱和时仍积分，因此启动时会出现过冲。限幅使duty合法，并不消除积分累积。

每个50ns步先用上一次duty和当前50kHz三角载波求电路，再用已求出的输出电压推进低通后退欧拉、PI新积分和限幅。
更新后的duty作用于下一次求解；t=0只观察初值。载波固定偏移5µs，t>0下管指令为上管指令的反相，提供同步续流路径。

额外2A负荷在2.5–5ms及7.5–10ms吸收电流。显式事件先用旧负荷积分到边沿，再切换负荷并保持电感电流、电容电压连续；
边沿行记录右侧代数量，电容电流可跳变。负荷阶跃不能用跨边沿斜坡代替。

双向受控开关仅用于已核定的体二极管不活动域：`|iL|≤7.99A`、`|UC|≤40V`，
还须检查中点电压和互补模式。运行回调在超域时拒绝继续。本例没有自动二极管换流、死区或通用非线性器件框架。

从仓库根目录运行：

```powershell
uv sync --locked
uv run --locked python examples/26_synchronous_buck.py
```

默认展示输出电压、电感电流和duty，不保存结果。脚本顶部的`SAVE_RESULT_DATA`、`SAVE_RESULT_FIGURE`可设为1保存；
非交互运行先设`$env:MPLBACKEND='Agg'`。观察启动过冲、2.5ms负荷投入后的电压下降与恢复，以及饱和期间仍变化的积分项。
保存CSV后可比较`duty`、`filtered_error`、`integral_term`三列，检查限幅与积分的区别。

练习时每次只改一项，并恢复默认值：将`TIME_STEP`减至25ns，比较启动和阶跃附近的曲线；
或减小`INTEGRAL_GAIN`，观察恢复速度与过冲的变化。参数变化须重新检查有效域、收敛和商业对齐，默认报告不覆盖练习结果。

## 当前验证证据

来源为MathWorks原模型[SynchronousBuckConverter.slx](https://www.mathworks.com/help/releases/R2025a/exampledata/simscapeelectricalsps/main/SynchronousBuckConverter.slx)，
实际平台为MATLAB R2025a Update1 / Simulink / Simscape Electrical Specialized Power Systems。
原件、完整MAT、原始Scope/状态轴及独立运行库存保留在忽略的`local_reference/`，不随本指南分发第三方模型。

内部12项测试覆盖精确DC初值、独立两状态方程与单模式矩阵指数、梯形法二阶收敛、事件连续性、
完整10ms的KCL/瞬时功率/有效域/控制时序、含开关协方差的离散能量，以及包含首负荷阶跃的50→25ns细化。
[参考归一化测试](../../../tests/test_synchronous_buck_reference.py)另用解析数据检查积分和非法输入，不把内部解析解称为商业输出。

```powershell
uv run --locked pytest tests/test_synchronous_buck.py tests/test_synchronous_buck_reference.py
```

原100/50ns两次真实10ms运行成功，分别103550/204619点；UC/iL两个完整窗自细化通过。
全部500周期中，duty最大均值差0.00275472超过0.0015，派生源流0.0240559A超过0.01A，
故[首次参考自身精化报告](initial_reference_failure.json)为FAIL。没有删周期、移时或放宽限值。
[求解配置补充](reference_solver_addendum.md)先行固定25/12.5ns并收紧容差；新尝试因系统可用提交内存不足2GiB在仿真启动前中止，
两次新完整运行和精化核验尚未完成，没有新的商业波形。

`audit_reference`只审计两组真实参考，不导入或运行候选。以下命令重放原100/50ns证据，预期保留FAIL；输出目录须为新目录：

```powershell
$runs = 'local_reference/b2_protocol_research/native_refinement/20261106T064932434Z/runs'
$audit = 'local_reference/b2_protocol_research/audit-' + (Get-Date -Format 'yyyyMMddTHHmmss')
uv run --locked python -m validation.cases.synchronous_buck.audit_reference `
  --baseline "$runs/20261106T070956629Z-baseline" `
  --refined "$runs/20261106T071447577Z-refined" `
  --output $audit --duty-error-assumption 1e-6
```

参考源流周期均值由原生iL/UC/duty、解析载波交点及KCL分段重建，明确属于派生量；原始测量样本完整保留，
不能将稀疏源流跳变PWL插值后积分。`1e-6`是显式条件敏感性假设，还依赖状态锚点导数相容和无隐藏根，不能由AbsTol推定绝对精度。
真实参考自身合格后，仍须完成候选商业比较、图/报告、教学与全部常规检查、Git提交，才能验收26。
