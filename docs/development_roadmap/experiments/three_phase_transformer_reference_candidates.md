# A4后续：三相接线与双变压器小网参考调查

2026-11-06。本轮先查本机R2025a目录和官方来源，再取得原件、静态核对并运行一次原完整模型。没有编写PyCy候选、冻结新比较阈值或修改核心。本文状态是 **runnable：默认探索运行成功**；尚无参考自身精化和候选验收，不能记为reference_ready或新增完成。

## 优先候选：Y–Δ–Y双变压器链

本机 `C:/Program Files/MATLAB/R2025a/help/docCatalog/exampleapi/sps.zip` 明确列出 `simscapeelectrical/TransmissionDeltaReferenceExample`，支持件为 `ee_delta_transmission.slx` 和 `ee_delta_transmission_plot.m`。[官方示例说明](https://www.mathworks.com/help/simscape-electrical/ug/transmission-system-with-delta-reference.html)用于解释两个变压器之间的三角形参考点。网页当前显示R2026b；本轮版本证据来自实际下载SLX的R2025a Update 1元数据，不用网页版本代替原件版本。

通过安装版 `copyFromWeb.m` 已核定的exampledata路径规则，实际HTTP 200取得官方R2025a文件：

| 文件 | 来源与SHA-256 |
|---|---|
| `ee_delta_transmission.slx`，54871字节 | [版本固定原件](https://www.mathworks.com/help/releases/R2025a/exampledata/simscapeelectrical/main/ee_delta_transmission.slx)；`02be3b7168ed504a6a585c3aa29aba3369b294d6bed2a517d6408a1931abe4ca` |
| `ee_delta_transmission_plot.m`，572字节 | [版本固定脚本](https://www.mathworks.com/help/releases/R2025a/exampledata/simscapeelectrical/main/ee_delta_transmission_plot.m)；`7deef91850394ae29c5151280759c3fc7b8c1d2a2a3ec86b2d0e90cdd2c88ad9` |

原件保存在忽略的 `local_reference/three_phase_transformer/simulink/`，取得日志为同目录上级的 `acquisition_attempts.json`。未提交第三方原件、未推断再分发授权。沙箱首次HTTP访问失败的记录也保留；获准的正常网络执行随后成功，没有关闭TLS验证或读取凭据。

原SLX只有8个顶层块，接线已由XML和原生日志核定：三相源→Y–Δ升压变压器→直接相连的三相母线（接Delta Reference）→Δ–Y降压变压器→接地星形电阻负荷，另有源中性点参考和Solver Configuration。模型名虽含transmission，**原件没有线路段**，不能把它叫作已验证的输电线路模型。

| 原件SID | 核定配置 |
|---|---|
| 26，Voltage Source | 60 Hz、相移0；`vline_rms=sqrt(3)*13e3/sqrt(2)`，即线RMS约15.922 kV、内电势相峰值13 kV，不能直接当作13 kV线RMS。`impedance_option='1'`，详见未决点。 |
| 27，Wye-Delta Transformer | 100 MVA、60 Hz；线额定电压13/115 kV；`Winding1Connection=ee.enum.windingconnection.Y`、`Winding2Connection=ee.enum.windingconnection.delta1`，前者为浮动星点。 |
| 28，Delta-Wye Transformer | 100 MVA、60 Hz；115/13 kV；`delta1`→`Y`，输出绕组星点同样浮动，不能与负荷接地星点混同。 |
| 两个变压器 | 各绕组电阻0.01 pu；`leakage_reactance_option`、`magnetizing_resistance_option`、`magnetizing_reactance_option`及`saturation_option`均为明确的`exclude`符号值。保存的0.05 pu漏抗、500 pu励磁及饱和表不是活动支路。 |
| 29，Load | `parameterization=ratedpower`、`component_structure_PQ=R`，13 kV、1 kW；负荷中性点接地。保存的L/C/Q及24 kV初始电压字段不表示本例启用了储能负荷。 |
| 32，Delta Reference | 连接两个Δ侧的公共母线，提供电压参考。它不是额外接地电阻或负载；原生日志中的参考电流约为零。 |

当前原件没有显式半导体、自动二极管、PWM、死区、分接控制或活动磁饱和。变压器的磁性效应被明确排除，适合优先研究线/绕组电压比、钟点方向、浮动中性点及功率；源内部仍有活动动态阻抗，不能据变压器无电感便称整个原网为无储能网络。

## 原完整网络默认运行证据

使用MATLAB `25.1.0.2973910 (R2025a) Update 1`、Simulink和Simscape Electrical执行一次。沿用 `simulating-simulink-models` 工作流，用 `SimulationInput` 只打开现有Simscape全量日志及工作区输出捕获，未改原件拓扑、物理参数、初值或求解设置。模型由`sim`自动加载；执行前后核对同名解析/已加载路径、Dirty和原件hash，结束关闭模型不保存。偏好、缓存和代码生成目录独立保存在工作区内。

默认实际求解器为daessc，可变步、最大步长1 ms、停止0.05 s；得到449个原生样本，本次仿真耗时9.807136 s。记录为 `local_reference/three_phase_transformer/native_probe_batch.log`，探针实现为 `run_native_probe.m`。原件hash运行后未变。

`default_probe/simulink_output.mat` 保存完整原生 `SimulationOutput`，SHA-256为 `1fc0ffec236473e919b7ace9b15965dd81274257274671bce3db44606830e18f`；`default_probe/provenance.json` 为 `edf3e31ab768b11a9b452287304039fd5016922772f9bd31bd7d361e117d529f`，含实际求解器、运行时间、SID对应路径/原生对话框参数、模型路径/Dirty/hash及改动范围。

在同一MAT上只读提取18份原生CSV，未重跑仿真；完整字段路径、单位、样本数、初值和峰值见 `default_probe/native_signal_inventory.json`：

- 源：`Voltage_Source.V`、`.I`、`.IL`、`.V_impedance`、`.N.V`。
- 两个变压器：各自`.N1.V`、`.N2.V`、`.i1`、`.i2`、`.power_dissipated`。
- 负荷：`Load.N.V`；输出绕组原生电流另存为`Delta_Wye_Transformer.i2`，它的正方向流入变压器，负荷吸收电流须取反。
- 参考点：`Delta_Reference.I`、`.V`。

首次缓存提取曾访问不存在的`Load.N.I`，原失败日志 `extract_cached_probe.log` 保留。读取实际日志结构后去掉该无效路径，同一MAT的第二次提取exit 0，日志 `extract_cached_probe_complete.log`；未添加测量块、未伪造字段或绕过结构编辑工具。

只读数值审计 `default_probe/native_physics_audit.json` 另外确认：

- 源三相初始电流和端口电压均为0，但内电势的b/c相在0时刻非零；`Voltage_Source.V-Voltage_Source.V_impedance`与13 kV相峰值、0/−120/+120°、60 Hz正弦一致，最大差2.47e-10 V。
- 原生`.I`与`.IL`逐点相同，`.IL`非零；阻抗电压在初始b/c相约±11258.33 V。源明确存在活动动态阻抗，不能当理想源，也不能把端口`.V`冒充内电势。
- 零初值冷启动的最早非零原生时刻为5.76234962644974e-9 s，`IL=[−2.42192022464711e-10,9.65517803481053e-5,−9.65515381560828e-5] A`；下一时刻为1.15246992528995e-8 s。原始CSV保留了这些点。负荷仅1 kW而两个变压器各为100 MVA，后续不能按1 ms最大步长直接为PyCy选步长；实际源R/L尚未核定，不从这些点拟合时间常数或假定活动参数。
- 按额定电压/总功率独立计算每相负荷R=13000²/1000=169000 Ω，`Load.N.V+169000*Delta_Wye_Transformer.i2`最大残差5.64e-11 V，确认原生输出绕组电流的符号。
- Delta Reference三相电流最大2.61e-18 A；它保留中间母线的参考作用，不是额外负载。

上述原生CSV没有归一化、时间移动或候选幅值拟合。全部脚本、取得日志、静态审计、18份CSV、MAT和原件的hash集中在本地 `evidence_inventory.json`；完整日志保留，未因一次字段错误否认已成功的原生仿真，也未把默认探索输出提升为正式参考。

## 相容性判断与最小下一步

本候选的知识点与23的单相直流阶跃不同，优先级高于复杂铁芯或分接控制模型。PyCy现有 `ThreePhaseTransformer` 支持Y/Y、Y/D、D/Y、D/D，变比是**每相绕组电压比**；在没有励磁支路时，两侧绕组串阻可按变比折算合并，但必须先核定原件的pu基准、Δ支路次序和电流定义。现有类在副边Δ且漏阻抗为零时主动拒绝未定环流，本例有正绕组电阻，不应人为添加零阻理想环路。

当前仍有三个需要直接证据的问题，未写PyCy候选或验收阈值：

1. 原生`DialogParameters.impedance_option`是string，`Enum={}`，读取值仍为`'1'`，没有直接给出显示标签。它不是已核定的枚举名；不能按静态TypeOptions顺序猜`1`，也不能把保存的R=0.01 Ω/L=3.97e-4 H或Ssc/XR同时当作活动值。下一步只读原生Mask动态字段、R2025a对应参数描述/内部参数树，核实该值的实际分支及计算参数；不要对波形拟合R/L来充当参数来源，不必重跑本次默认sim。
2. 核定`delta1`绕组端子顺序及`.i1/.i2`究竟是各绕组电流还是外部线电流，保留明确的线电流KCL转换；不能把额定线电压比直接传作绕组变比。使用已有原生日志作方向和端口恒等式核对，然后再建立独立相量/状态方程。
3. Delta Reference固定绝对电势规范点。候选需要在现有接口内保留相同物理约束或明确只比较线电压与电流；不能用随意接地或额外泄漏电阻凑出可解系统。若必须增加真正缺失的约束能力，先单独评估最小改动与教学必要性。原默认Y–Δ–Y链不自动验证Yy/Dd及不平衡零序情形。

完成这些原生解释后，才决定是否进入协议冻结、参考自身细化和实现。正式验证对象应先保持这个无实际线路段的双变压器链，不将它包装成完整配电网或复制多个仅改接法的算例凑数量。

## 本机已取得但当前不选的原件

从安装版 `toolbox/physmod/powersys/supporting_files/documentation_models/` 原样复制两份文件至忽略的 `installed_documentation_models/`，只读XML、未运行：

| 原件 | 实际证据与筛选结论 |
|---|---|
| `power_transfo3ph.slx`，SHA `015e8b0f2d57b361ef4e103add21d0d22bb78546f5aa4c457e06f842dce251be` | 三相500/230 kV、450 MVA、Yg/Yg，但`SetSaturation=on`、`SetInitialFlux=on`，残磁[0.8,−0.4,0.4]，三个断路器50 ms合闸。不能因文件名把它认作线性三相参考；本轮不关闭饱和后冒称原模型等价。 |
| `power_transformer.slx`，SHA `1c69d015bfc14a6c3aa87dc2d8f201a623cac62f35f5c159dabc7631c9546427` | 75 kVA、14.4 kV/120 V/120 V，`ThreeWindings=on`，是单相三绕组分配负荷例，不是三相Yd/Dy接线教学。可另行研究现有元件组合，当前优先级低于上面的纯线性双三相链。 |

这两份旧安装示例的自身metadata是R2025a Prerelease Update 2，不能写成本轮已用Update 1原生运行通过。另查到的三柱/五柱、磁滞、自动分接示例具有明确额外物理或控制边界，未因它们“可找到”就记作兼容、runnable或reference_ready。
