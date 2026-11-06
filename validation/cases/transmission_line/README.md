# 22：有限50T线路、启动瞬态与色散

运行 `uv run --locked python examples/22_t_section_transmission_line.py`，建议先学02的储能初值与08的集中参数线路。本例直接使用现有R/L/C和稠密LU复用，保留50个对称T段、100个生产电感；没有新增线路核心类。

## 接线、参数与观察

第k段按全局向右方向排列为：

```text
n(k-1) -- Rk_left -- Lk_left -- ck -- Lk_right -- Rk_right -- nk
                                |
                             Ck // Rk_shunt
                                |
                                0
```

每段0.1 m，总长5 m；单位长度R=0.0067 Ω/m、L=250 nH/m、C=100 pF/m、G=5 μS/m。因此各串臂为0.000335 Ω和12.5 nH，中点为10 pF并联2 MΩ，电容ESR为0。左端n0接10 V峰值、200 MHz、零相位理想正弦源，无串阻；n50以50 Ω接地。全部100个电感电流和50个电容电压初值0。默认TR步长10 ps、总时长50 ns；`linear_solver_mode='reuse'`只复用现有线性分解。

n15/n25/n50是相应T段的**右端口**，不是电容中点c15/c25/c50。串臂电流均向右，`i:L1_left`从源进入线路，`i:Rload`从n50流向地。启动前线路没有储能，观察波形逐段建立、端口电流与负载吸收。输入端允许瞬时回馈，不能要求每个时刻源功率都为正。

`长度*sqrt(L_per_m*C_per_m)=25 ns`只是连续线路名义尺度。有限50T的每段相移在200 MHz下约0.63914 rad，存在色散；忽略小R/G时，相位延时约25.431 ns、群延时约26.333 ns，Bloch阻抗约47.469 Ω，50 Ω终端仍有小反射。50 ns启动记录不自动成为稳态记录，也不是Bergeron的严格纯延时模型。练习可保持50段，降低源频率，观察离散色散的变化；当前绘图固定使用n15/n25/n50。修改频率后原真实参考验收不再适用。

## 真实来源与原图标签问题

来源为 MathWorks [Transmission Line](https://www.mathworks.com/help/simscape/ug/transmission-line.html)，`simscape/TransmissionLineExample`，实际模型 `TransmissionLine.slx`。本机MATLAB R2025a Update 1、Simulink和Simscape已真实执行；实例覆盖参数与上文一致，不能用SSC组件默认值替代。第三方模型、原始MAT/CSV、日志和对比图保留在忽略的 `local_reference/transmission_line/`，不主张再分发许可。

原模型S1至S5各含10段。官方绘图把 `S2.T_5.p2.v` 标成Segment25，它实际上是第15段右端；真正第25段是 `S3.T_5.p2.v`。标准化参考按真实接线使用 `v_boundary_15`、`v_boundary_25`，原脚本和误标签证据仍保留。源为 `v_source`，负载为 `v_load`。

原SSC右臂正方向是p2朝中点，故 `l2.i` 与全局右行电流反号。参考输入 `i_source_to_line` 取第一左臂正向，`i_load` 使用已核定的最后右臂反向。原生100L/50C的t=0状态已实际逐一检查，均严格为0；源正弦及终端Ohm关系也独立核对。

## 独立物理与数值验收

候选前提交 `3761a21` 固定 [manifest.json](manifest.json) 和 [parameters.json](parameters.json)。六个正式信号为n0/n15/n25/n50电压及输入/负载电流，完整窗口0–50 ns，工程基值10 V和0.2 A。各信号同时要求NRMSE≤0.003、最大电压误差≤0.05 V或最大电流误差≤0.001 A；不拟合时间、相位、幅值或传播延迟。

内部独立oracle将相邻无分支的半臂精确合并为51个RL电流状态，加50个中点电容电压，共101状态；再用已知200 MHz正弦/余弦两状态作103维矩阵指数。生产候选保留100个电感。oracle从零物理状态、sin0=0/cos0=1求完整瞬态，既不调用MNA stamp，也不以稳态传递函数代替启动响应。另以独立对称T的ABCD矩阵检查三个频点的状态频响。推导见 [独立验收方案](../../../docs/development_roadmap/experiments/transmission_line_validation_plan.md)。这些数学结果不能冒充商业平台数据。

`tests/test_t_section_transmission_line.py` 检查全部储能状态、半臂方向、源/负载电流、所有中点及相邻段KCL（1e-8 A）、正耗散、储能加损耗相对于源工作平衡（相对0.005），并单独核对TR离散能量恒等式。TR按20/10/5 ps对同一精确瞬态细化，两次误差比均须≥3；BE用相同步长演示一阶收敛与数值耗散。能量分母取正的工作/损耗/储能尺度，避免用接近零的净功归一化。

## 导出与比较

MATLAB在仓库根目录执行：

```matlab
addpath('validation/cases/transmission_line');
export_reference(pwd);
```

参考独立采用ode15s、RelTol=1e-8、AbsTol=1e-10，分别以10 ps和5 ps最大步长输出原生样本，自身六信号差异须小于正式绝对误差限值的1/10。求解器精化不改变原物理模型、驱动或初值。最终导出脚本还校验实际模型字节与加载路径/未保存状态，provenance记录所用实例、初值与软件。

具备真实导出数据后运行：

```powershell
$env:MPLBACKEND='Agg'
uv run --locked python -m validation.cases.transmission_line.compare
```

无真实数据时命令失败，不回退合成参考。每次在独立UTC目录保存候选CSV/JSON/NPZ、完整波形叠图、逐量指标、模型/参考/参数/manifest/候选/导出及比较脚本输入快照、Git状态和SHA-256。所有比较保持绝对时间。

## 当前执行状态

独立教学脚本已实际Agg运行成功，5001个时间点。本地稳定Python3.14.5的8项内部测试全部通过，339.16 s；物理/能量与两个细化测试标为slow，快速集合保留接线及三个频点检查。耗时为本次执行记录，不作性能基准。

真实参考10 ps最大步长5066个原生不等步样本、5 ps最大步长10041点；两次的全部100L/50C零初值已核验。六信号自身细化最大差约2.272e-4 V和9.982e-6 A，均小于正式绝对限值的1/10。

最终导出固定后的首次正式比较，六信号完整0–50 ns窗口全部通过；未作时间、相位、幅值或传播延迟拟合。完整 [validation_report.json](validation_report.json) 与本地UTC运行目录的报告逐字节一致，叠图已实际查看，端口、单位、方向和全窗均正确：

| 信号 | 最大绝对误差 | NRMSE（固定基值） |
|---|---:|---:|
| 源n0 | 1.972e-4 V | 3.469e-6 |
| 第15段右端口 | 2.929e-3 V | 1.118e-4 |
| 第25段右端口 | 4.130e-3 V | 1.696e-4 |
| 负载n50 | 8.012e-3 V | 2.723e-4 |
| 源至线路电流 | 1.054e-4 A | 2.615e-4 |
| 负载电流 | 1.602e-4 A | 2.723e-4 |

源在各自原生采样时刻都遵循同一正弦；比较器按双方不等采样点的分段线性重建计算误差，因此源列仍有小的插值误差。这些数值是本配置和步长的证据，不是任意线路离散或连续分布电缆的精度承诺。正式提交及跨平台回归由主任务收口。
