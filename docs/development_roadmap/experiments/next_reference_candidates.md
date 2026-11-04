# 下一项参考候选：只读调查

核查日期：2026-11-04。本记录只检查本机R2025a目录、官方网页、已下载原SLX及已安装组件源代码；未启动MATLAB、未仿真、未修改模型或冻结的02/catalog。目录中的支持文件名不代表文件已下载，网页当前显示R2026b也不作为本机模型版本证据。

## 优先项：纯线性T形梯级线路

推荐下一次先获取`simscape/TransmissionLineExample`。本机`help/docCatalog/exampleapi/simscape.zip`列明主文件`TransmissionLine.slx`和`TransmissionLinePlotV.m`；目录说明为50个0.1 m段组成5 m同轴线路。[官方说明](https://www.mathworks.com/help/simscape/ug/transmission-line.html)与本机目录一致。

本机已有配套原件：

- `C:/Program Files/MATLAB/R2025a/toolbox/physmod/simscape/supporting_files/example_libraries/TransmissionLine_lib.slx`，原件metadata为R2025a，SHA256=`c9de97cb0b86024c03fe16ec4f1ba979be896b4a0ccda8fac066fdb84c899444`。
- 同目录`+TransmissionLine/t_section.ssc`，SHA256=`e6bae69228f1b4c2d568097ca973ff2b13e8ab2cccdb07cfbaeae7b22492ae73`。

源代码直接给出拓扑：两端各串联`Rℓ/2`和`Lℓ/2`，中点对参考端并联电导`Gℓ`及电容`Cℓ`；电容ESR显式为0。没有自动二极管、器件枚举、磁饱和或控制器。现有`Resistor`、`Inductor`、`Capacitor`可构成同一T形梯级，泄漏电导用电阻表示，无需新增生产元件。

源码声明的**组件默认值**为ℓ=50 m、R=0.3 Ω/m、G=5 µS/m、L=220 µH/m、C=90 pF/m，不能直接作为主模型实例值。

调查后续，根代理已安排MATLAB代理实际取得原主模型`local_reference/transmission_line/simulink/TransmissionLine.slx`。本代理仍未调用MATLAB，只读SLX确认metadata为R2025a，SHA256=`844a8501b9e25a4fe881ecfc7ea14d7d1b0e9bdba38986572ba1a910551d86fe`。模型PreLoadFcn显式设总长5 m、50段、R=0.0067 Ω/m、C=100 pF/m、Z=50 Ω、G=5 µS/m；每段参数引用`segmentLength=0.1 m`和`L=C*Z^2=250 nH/m`。五个子系统各10个T段，实际共50段。各半段电阻0.000335 Ω、各半段电感12.5 nH，中点电容10 pF、电导0.5 µS。根网络为10 V峰值、200 MHz、0相位正弦理想电压源和50 Ω终端，所有T段参考端接同一地。没有依据静态枚举猜测任何器件。

本记录截点状态：**配套库、组件和新取得主SLX已inspected**。尚未在本记录中证明原生编译、运行、实际初值和真实结果，不能据此标runnable/reference_ready；原生运行由MATLAB代理另行负责。许可沿用本机已授权MathWorks软件的本地使用条件，未声称允许再分发原件。

下一最小操作：`openExample('simscape/TransmissionLineExample','workDir', targetDirectory)`获取及原件静态核对已完成；由MATLAB代理核实实际初值、求解器和日志信号，默认真实运行后保存原始数据及provenance。进入PyCy候选前，以相同T梯级为唯一拓扑依据，预设输入/中点/输出电压、首段电流、传播时延及能量/损耗检查。现有π形分段线和Bergeron线具有不同离散拓扑或方程，不能仅因线路总参数相同就宣称等价。

## 其余候选与边界

| 优先级 | 官方精确ID / 文件 | 已核实事实 | 下一最小操作及未决点 |
|---|---|---|---|
| 2 | `simscape/ElectricalTransformerExample` / `ElectricalTransformer.slx` | 本机目录列明50 W、60 Hz、120/12 V，线性B-H、无铁损、绕组损耗和漏磁；0.5 s接额定负载。[官方说明](https://www.mathworks.com/help/simscape/ug/electrical-transformer.html)一致。主文件未取得。 | `openExample`取得后检查磁路到电气等效参数、励磁/漏感、绕组电阻、受控负载开关。线性B-H不意味着可以忽略有限励磁支路；不能直接把50 W/电压比替换进现有09后视为对齐。 |
| 3 | `simscape/ComparisonOfMutualInductorAndIdealTransformerExample` / `CompareCircuits.slx`、`ElectricalEquivalentCircuitTransformer.slx`等6个支持模型 | 本机目录明确用于比较互感与理想变压器简化假设，具有纯电气等效支路候选。主文件未取得。 | 获取支持模型后找最小独立电气网络，完整保留其励磁/漏感边界。尚无接线和参数，不认定任何一个已可直接对标。 |
| 后置 | `simscapeelectrical/LCLineTestBridgeExample` / `LCLineTestBridge.slx`及3个辅助脚本 | 目录和[官方说明](https://www.mathworks.com/help/simscape-electrical/ug/lc-transmission-line-and-test-bridge.html)表明是非对称线路加双向测试桥；页面引用Band-Limited Op-Amp。 | 先取得原SLX，检查运放和测试桥是否位于必须保留的激励/测量路径。尚不能把整个模型叫作纯被动线路，优先级低于TransmissionLine。 |
| 待核 | `simscapeelectricalsps/SynchronousBuckConverterExample` / `SynchronousBuckConverter.slx` | 精确ID、标题、文件名在本机`sps.zip`目录中存在。未取得SLX。 | 获取后先核实选用器件、自动二极管、死区与电感反向电流。同步命名不能证明是双向受控电阻开关；不得根据静态TypeOptions推断枚举，也不通过删除二极管改造原拓扑来凑等价。 |
| 暂无可推荐原件 | 半桥/全桥、同步Boost | 当前已下载模型中未找到独立且已确认没有自动续流依赖的官方原件。Infineon半桥导入示例目录明确涉及IGBT/二极管器件数据，不能据此认定在现有开关能力内。 | 保持来源发现状态，先取得原SLX与原生枚举/参数证据。不会用当前B1三相桥拆出半桥后冒称未改结构的官方参考。 |

## 已下载RLC原件可补现有算例验证

`local_reference/mathworks_dc_analysis/RLCCircuit.slx`来自已取得的MathWorks教学仓库v2.2.2，SLX metadata为R2024a，SHA256=`26b7204cbea99d2835c3c53faeaee3c293ac29f2ec144ef1a9db999287d8b3bd`；同tag的BSD三条款许可证已保存于该目录。只读XML确认12 V直流源，经SPDT在源与地之间选择，接串联R、L、C，C下端回地；电压测量接电容两端。R/L/C分别由固定常数10 Ω、1 µH、1 µF驱动可变元件，当前参数未见时间变化。原件开关`ee.switches.spdt_ps`保存R_closed=0.01 Ω、G_open=1 µS、Threshold=0.5 V；电容ESR=1 µΩ，电感并联电导=1 nS。原件存在Dashboard人工切换，不能把默认常值门极当作已安排阶跃。

该原件没有独立半导体二极管块，可作为既有04/RLC的补充参考调查；其知识点与现有算例重叠，不建议仅为数量另新增。最小操作是原生读取SPDT实际端口/控制定义和可变储能元件参数化，使用SimulationInput安排可复现切换、保持SLX原件不变，随后才制定误差预算及真实导出。这里没有从数值枚举猜测开关类型，也未把XML静态检查提升为原生运行成功。

目录证据SHA256：`simscape.zip`=`999114437031cfc219803cd85176750a2c26017ee3e36eef03899ba7a9e0e0eb`；`sps.zip`=`66b2721ae0d938f1a2d1caaebf18cb1dfb74d7186d96fe3e0518fe4c908c7bc5`。目录JSON的本次提取位于忽略目录`.tmp/longterm/simscape_example_catalog.json`和`sps_example_catalog.json`。未复制或提交任何MathWorks原模型、组件代码或参考数值数据。
