# 27：有限电阻 Bergeron 线路

运行 `uv run --locked python examples/27_finite_r_bergeron_line.py`。
本例从零历史启动，用一条斜坡电压观察线路传播、反射和最终直流压降。
建议先读08的有限π段线路，再比较本例的明确传播延迟；两种模型的近似对象不同。

## 从参数到接线

```text
Vdc ─ Rs ─ send ─ Rleft ─ B1 ─ Rmiddle ─ B2 ─ Rright ─ recv ─ Rload ─ 0
       100Ω       25Ω    150µs    50Ω    150µs   25Ω             400Ω
                         Z=201Ω        Z=201Ω
```

源负端、负载负端和两个半线的参考端均接地。`send`和`recv`是整条含电阻线路的外端口，
两个半线的内端口叫`line1_send`、`line1_recv`、`line2_send`、`line2_recv`。
每个半线都复用现有`BergeronLine`，负时间电压、电流历史为零，衰减系数为1。
线路电阻由三个现有`Resistor`表示：两端各R/4，中间R/2，总计100 Ω。

| 参数 | 默认值 |
| --- | --- |
| 源电压 | 0.5 ms前为0，0.5–0.6 ms升至1000 V，此后保持 |
| 源电阻 / 负载 | 100 Ω / 400 Ω |
| 线路参数 | Z=201 Ω，总延迟300 µs，总R=100 Ω |
| 半线参数 | Z=201 Ω，延迟150 µs，attenuation=1 |
| 仿真 | 固定步长1 µs，0–6 ms，共6001点，t0正常求解 |

`create_components()`按图从左到右返回元件；`define_case()`配置固定网格和两张图，
`run_case()`沿统一的`CaseDefinition → Circuit → Simulator → SimulationResult`路径执行。
脚本无需商业软件，也不读取商业波形。默认显示图，`SAVE_RESULT_DATA`和
`SAVE_RESULT_FIGURE`均为0；改成1后才在`outputs/finite_r_bergeron/`保存数据或图片。
非交互环境可设置`MPLBACKEND=Agg`运行。

## 先看波前，再看反射

第一张图显示源、完整线路送端和收端电压。源首个非零网格点是0.501 ms，
收端首个非零点是0.801 ms，正好晚300 µs。源虽在0.5 ms开始变化，
该边界点仍为0，不能把首个非零采样晚1 µs解释成额外线路延迟。

波在源阻、中心50 Ω电阻和负载边界散射，多次往返后逐步建立直流分布。
首个发送区间内，完整送端看到25 Ω加201 Ω，所以`Vk=(25+201)Ik`。
负载端电压的首次变化还包含中间电阻的透射，以及负载与右端25 Ω的分压。
不能只把整条线路当成一个300 µs延迟块，再对电压乘一个常数来解释所有反射。

第二张图显示两端电流，方向固定如下：

| 读数 | 字段 | 正方向 |
| --- | --- | --- |
| Vk | `v:send` | 送端对地 |
| Vm | `v:recv` | 收端对地 |
| Ik | `i:Rs` | 源经过Rs进入完整线路 |
| Im_out | `i:Rload` | 完整线路流向负载，再入地 |

暂态中两端电流可以不同，因为行波在两段线内储能。
`i:B1:receiving`和`i:B2:receiving`的正方向是流入各自半线，与图中向右的电流相反。
核对中间电阻时需要保留这个负号。

直流极限中，两半线无传播变化，三个线路电阻仍有压降。
因此`I=1000/(100+100+400)=1.666667 A`，`Vk=833.333333 V`，`Vm=666.666667 V`。
摘要同时显示末点和理论极限，便于发现极性或电阻遗漏；完整启动和反射仍须单独检查。

## 有限R与衰减系数

这里采用[PSCAD官方 Bergeron 模型说明](https://www.pscad.com/webhelp-v5-ol/EMTDC/Transmission_Lines/The_Bergeron_Model.htm)
中的两段无损线和R/4、R/2、R/4集总损耗近似。
电阻产生非负`R*i²`损耗，也改变各边界的反射系数。
半线的`attenuation`保持1，让损耗的来源清楚可见；把它降低会改变模型，不能代替这三个电阻。
此近似使用单频线路参数，适用范围不包括宽带真实电缆的频变损耗精度。

可以把`LOAD_RESISTANCE`改为200 Ω观察反射和最终电压，再恢复400 Ω。
也可把步长改为0.5 µs比较波前；每个半线延迟必须仍是步长的正整数倍。
非整数延迟或不对齐结束点会在求解前拒绝，不能靠短步或四舍五入传播时间解决。
改动参数后的结果应视为另一次实验，原冻结商业验收只覆盖默认参数。

## 参考与验收状态

参考由本机PSCAD 5.0.0安装示例`Lightning/Steep_Front.pscx`中的标量`SrvcCbl`线路派生，
保留完整线路定义并明确替换外围电路。生成的TLI/TLO确认运行Z=201 Ω、总延迟300 µs及总R=100 Ω；
LCP频域复阻抗诊断单独留存。1 µs及0.5 µs的真实原生运行已在候选创建前通过冻结的参考自细化预算。
原件、完整原始波形和hash留在忽略的`local_reference/`，不随代码上传。

四量、完整两窗、固定尺度、误差限值和内部独立验证要求见
[manifest.json](manifest.json)、[parameters.json](parameters.json)及[acceptance_plan.md](acceptance_plan.md)。
四量在0–1.2 ms和1.2–6 ms两窗均通过真实PSCAD比较，未移相或删去启动区间。
最大电压误差5.92×10⁻¹² V、电流误差5.16×10⁻¹⁴ A；这是同一集总损耗模型的一致性结果。
8项独立物理测试覆盖行波递推、KCL/KVL、波前、直流极限、损耗和储能；
独立运行及完整1244项回归测试（含slow）通过。简要结果见
[比较报告](validation_report.json)和[参考自细化报告](qualified_reference_report.json)。
原生STANDARD、无快照及可观测的零前史支持零历史解释；原生隐藏延迟缓冲没有直接导出，
商业结论保留这一证据边界。

## 复核商业比较

持有已核定的本地参考归档时，从仓库根目录运行：

```text
uv run --locked python -m validation.cases.finite_r_bergeron.compare
```

该命令读取`local_reference/finite_r_bergeron/`的参考和来源记录，核对hash后运行本例；
不启动PSCAD。缺少归档或身份不符会报错。每次比较在独立目录保存输入快照、数据、图和报告。

重新生成参考需要本地PSCAD许可及编译器。先复制上述安装示例，保留完整`SrvcCbl`定义，
将线路长度设为10 km，外围按本页源、100 Ω源阻及400 Ω负载重接；
保持常参数Bergeron、插值开启、无限长/高频修正/长线修正关闭。
用STANDARD无快照分别以1 µs和0.5 µs步长及同样输出间隔运行完整6 ms，
记录源指令、源电压、两端电压和两端电流，并从TLI/TLO核对实际R、Z和延迟。
原生kV/kA输出按1000换算为V/A，保留全部时间点及本页电流方向；
先按冻结预算通过参考自身细化，再比较候选。原生运行及归档证据入口见
[本轮证据索引](../../../docs/development_roadmap/experiments/native_reference_attempts_20261109.md)。
