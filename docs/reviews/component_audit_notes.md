# 元件、组合网络与电机审查证据

审查日期：2026-11-03（Asia/Shanghai）。绑定生产基线：`6b5d206fced1cec48d8f2298f794942b24d108cd`。
本附录供本轮总报告引用；未修改生产源码、现有测试或用户文档。总报告的问题编号及统计为最终口径。

## 1. 实际覆盖

逐文件阅读并核对的实现：

| 文件 | 检查内容 |
|---|---|
| `pycy_emt_lite/components/__init__.py` | 全部导出与实现归属 |
| `pycy_emt_lite/components/base.py` | 抽象接口、默认空实现、有限实数输入校验、所有权声明 |
| `pycy_emt_lite/components/basic.py` | R/C/L、独立电压/电流源，全部构造、注册、stamp、更新、输出及导数路径 |
| `pycy_emt_lite/components/switching.py` | Fault/Breaker 的有限电阻、拓扑状态、输出 |
| `pycy_emt_lite/components/power_electronics.py` | IdealSwitch 门极二值验证、导通/泄漏电导、同次采样与测量 |
| `pycy_emt_lite/components/three_phase.py` | 相序、地别名、源、串联RL线路/负荷、并联RLC功率换算及各相状态 |
| `pycy_emt_lite/components/lines.py` | π型、三相π型、分段线、单相/三相Bergeron，全文件 |
| `pycy_emt_lite/components/transformers.py` | 单相/三相绕组约束、漏感、励磁/铁耗、四种Y/D接线、滞后饱和，全文件 |
| `pycy_emt_lite/converters/__init__.py`、`filters.py` | L/LC/LCL展开接线、内部节点、参数及每次新建元件 |
| `pycy_emt_lite/machines/__init__.py`、`synchronous.py`、`park_generator.py` | 经典机与六状态Park教学模型的全文件 |

逐文件阅读的测试：`test_basic_components.py`、`test_three_phase.py`、`test_line_models.py`、`test_transformers.py`、`test_power_electronics.py`、`test_synchronous_machine.py`、`test_park_synchronous_generator.py`。包括参数化的非法输入、独立ODE、解析解、能量/功率、共同网格收敛、初值/事件、PWM细网格对照。

理论文档核对：`component_derivations.md` 第1–11.3节与12.1节逐节对照实现；`models_and_validation.md` 第1–10节逐节阅读。英文对应基础、三相/线路、变压器、电机及滤波段作对应核对；中英数学块的一致性检查由文档审查分工统一记录。综合算例高通/DC网络及控制部分由综合算例分工核对，本文不冒充独自验证。

历史记录针对性阅读：原I01/I02、I20、I37/I39、R0–R5修复范围与7.4/7.5验收，以及模型边界第6章。特别区分已经修好的局部内部节点碰撞、磁链积分和Park模型问题；不把旧问题原样重新计数。

## 2. 物理方程、离散式和代码的对应

令关联向量a在正端为+1、负端为−1，省略地分量，u=aᵀv，i从正端指向负端。MNA节点行以流出为正，因此已知电流源写b−=aI。

| 模型 | 方程/离散关系 | 实现位置与判断 |
|---|---|---|
| R | i=u/R；ΔY=aaᵀ/R | `basic.py:66`、`:75`，正确；派生电流经过消减误差检查，避免只凭网络残差宣称精度 |
| 独立I源 | i=I(t)，Δb=−aI | `basic.py:106`，方向正确；需要一致求解导数时才读取di/dt。没有自动`i:<源名>`输出，推导2.2已明确，属于现有API |
| 独立V源 | ai进入KCL，aᵀv=E(t) | `basic.py:163`；支路电流流入源正端，发电时负，正确 |
| C梯形 | i₁=(2C/h)u₁−(2C/h)u₀−i₀ | `basic.py:262`；电导与历史源符号正确，`:239`在旧历史被覆盖前计算i₁ |
| C后向欧拉 | i₁=(C/h)(u₁−u₀) | 同上；G随实际h重算 |
| L梯形 | u₁−(2L/h)i₁=−(2L/h)i₀−u₀ | `basic.py:319`、`:366`；额外支路未知量及KCL/KVL符号正确 |
| L后向欧拉 | u₁−(L/h)i₁=−(L/h)i₀ | 同上；更新保存电流与电压 |
| 串联RL | u₁−(R+R_eq)i₁=H；历史保留uL=u−Ri | `three_phase.py:219`、`:247`、`:482`、`:510`；`lines.py:100`、`:161`；无重复计入R压降 |
| 三相源 | √2 Urms sin(ωt+φa/b/c)，φ=(0,−120°,120°) | `three_phase.py:93`；相电压RMS和相序正确，一致求解解析导数匹配 |
| 并联RLC额定换算 | G=P/Ull²，L=Ull²/(ωQL)，C=QC/(ωUll²) | `three_phase.py:311`起各属性；固定阻抗而非恒PQ，独立各相L/C历史；P=0输出inf表示缺省R而非发散，已有文档和IO契约 |
| π线 | 串联RL，两端各C/2 | `lines.py:242`；串联电流与端部电容电流分别输出，无遗漏端口储能 |
| 分段线 | 每段R/N、L/N、C/N；内节点总C/N，端部C/(2N) | `lines.py:435`、`:459`；`sending/receiving`输出为首/末段串联电流，文档明确不能当总端口电流 |
| Bergeron | is=vs/Z+η(−vr(t−τ)/Z−ir(t−τ))，另一端对称 | `lines.py:550`、`:566`、`:596`；两端电流均流入线，负号正确；整数历史索引与同刻替换相配 |
| 变压器传能支路 | up−n us−Rσ ip−Lσ dip/dt=0，is+n ip=0 | `transformers.py:155`，一次支路行放电压约束、二次支路行放安匝约束，非对称MNA合理 |
| 励磁/铁耗 | im为一次外端并联L；铁耗up/Rfe；λ̇=up | `transformers.py:207`、`:237`；TR/BE磁链与电感积分一致，事件h=0不推进λ；一次传能电流输出不含并联支路，已有明确说明 |
| Y/D接线 | Y:相→中性点；D:a→b、b→c、c→a | `transformers.py:380`，相移由接线自然得到；二次D零漏阻抗的非唯一环流被明确拒绝 |
| 饱和近似 | 按上一时刻\|λ\|选择Lm/Lsat，再积分di/dt=up/Leff | `transformers.py:138`、`:210`；与声明的显式滞后近似相符，跨拐点一阶误差不应包装成梯形全局二阶或完整铁芯模型 |
| 经典机 | e−v=Rs i+Ls di/dt；2Hw ẇ=(Pm−Pem)/Sb−D(w−1)，δ̇=ωb(w−1) | `synchronous.py:169`、`:230`；Pem=Σei含铜损和RL储能交换，与声明教学模型一致；机电显式欧拉，电气TR/BE |
| Park机 | Vd=Ed′−RsId+Xq′Iq，Vq=Eq′−RsIq−Xd′Id；两轴暂态电势+AVR+调速器 | `park_generator.py:153`、`:251`；d=−cosθ、q=sinθ，幅值不变变换与基值匹配；代数电流不被错误固定为电感状态 |
| Park功率 | Pem=Pterminal+Pcopper=Sb[Ed′Id+Eq′Iq+(Xq′−Xd′)IdIq] | `park_generator.py:196`起更新，与端口式相符，凸极项未丢失 |
| L/LC/LCL | LCL: ic=i1−i2，vm=vc+Rd ic；L1 i̇1=vconv−R1i1−vm，L2 i̇2=vm−R2i2−vgrid | `filters.py:121`起展开接线；Rd与C串联；组合不再维护重复积分状态，合理 |

初值/显式事件通过`context._initial`登记储能约束，而不是极小步推进。对标准合法输入，未发现新的RLC、变比、相序、行波符号或机组状态重复积分错误。此判断仅限上述实现和证据，不能视为任意参数条件下的数学认证。

### 单位、初值、输出和证据边界补表

以下测试位置均位于`tests/`，列出的文件在本分工已全文审查；执行结果由总报告统一给出。

| 类别 | 单位和合法范围 | 初值、状态和事件 | 输出定义、适用边界及具体测试 |
|---|---|---|---|
| R与独立源 | R>0 Ω；I/V为有限A/V；可给解析A/s、V/s导数 | 无储能；源取当前t值；未声明callable跳变不自动插入事件 | R电流正端→负端；V源电流流入源正端。`test_basic_components.py:201,229,372,393`检验欧姆定律、源方向、约束导数与无约束源；非线性源内部模型不在范围 |
| C/L与RLC网络 | C>0 F、L>0 H；初值为有限V/A | C电压、L电流为指定储能初值；一致网络给配套电流/电压；显式事件保持储能连续；每步重算实际h | C输出v/i、L输出i/v。`test_basic_components.py:289,309,322,333,346,362,415,432,451,482`覆盖初值、导数约束、解析整曲线、守恒/收敛和高低电压混合尺度；梯形振铃与BE耗散属于方法性质 |
| 三相源/RL线/RL负荷 | 正phase_rms V、频率Hz；每相R≥0 Ω、L≥0 H，不能同时零；角度rad | 线路/负荷L电流默认零；三个相独立历史；源附正弦解析导数；地别名统一 | abc瞬时相量不是复相量；每相电流/压降。`test_three_phase.py:111,122,190,205,235,290`验证初值、相序/解析暂态、平衡与故障；没有相间互感 |
| 三相并联RLC | 线电压V；三相总P W、QL/QC非负var，不能全零；f>0 Hz | 额定值转换固定R/L/C；L/C零初值；源直接并联时C须一致预充；各相状态独立 | 输出每相总i、L/C分流、相电压和参数；P=0的r=inf为缺省。`test_three_phase.py:31,122,308,325,350`含独立故障ODE；不能解释为恒功率或任意不平衡模型认证 |
| π线/三相π/分段线 | 每相总R Ω、L H、C F均≥0；R/L不能同零；N为1–1000整数 | 默认L电流与C电压为0；内部状态可在建模前配置但无通用潮流初值；事件遵循网络一致连续性 | π串联i与端部C电流分开；分段sending/receiving是串联i。`test_line_models.py:163,193,239,412,458`及`test_three_phase.py:31`有二端口、ODE、能量/时间或空间收敛；无频变和相间耦合 |
| Bergeron单/三相 | Z>0 Ω、τ>0 s；0<η≤1；τ必须整步且至少一步 | 负时间端口历史0；初始样本不推进；同刻事件替换末样本；实际事件须在固定网格 | 两端i均流入线路。`test_line_models.py:277,287,306,331,341,355,381,397`覆盖整步、反射、脉冲与事件；η<1独立衰减/能量验证仍不足，未承诺任意延迟/频变 |
| 单/三相变压器 | n>0无量纲；Rσ≥0 Ω、Lσ≥0 H；可选Lm/Rfe>0；λ单位V·s；Lsat≤Lm | 默认漏感/励磁电流与磁链0；事件保持电流/磁链；饱和以上一λ选L；二次D须非零漏阻抗 | 一次传能ip不含im/铁耗，二次is=−nip；D绕组i不同线i。`test_transformers.py:67,85,158,175,183,204,273,299,314,366`覆盖线性独立解/功率/初值/收敛及单向饱和曲线；无共同铁芯、磁滞或实际涌流认证 |
| Fault/Breaker/IdealSwitch | 导通R>0 Ω；IdealSwitch 0≤Goff≤Gon S | 无储能；标准事件修改bool；IdealSwitch每次stamp只采样一次并保存门极；Fault/Breaker输入缺口见COMP-01 | 输出i与0/1状态。`test_power_electronics.py:39,72,132,144,160,169,325`核对消减诊断、门极、导通和PWM；不是二极管/器件损耗模型，开路可导致真实拓扑奇异 |
| L/LC/LCL | L>0 H、C>0 F；各R≥0 Ω | 每次`.components()`新建基础元件；默认储能初值0，可replace基本元件初值；不重复保存组合状态 | 沿展开的基础元件名输出；LCL的Rd串联C。`test_power_electronics.py:55,89,107,185,214,264`覆盖独立ODE、KCL、无阻尼/有阻尼、两方法能量及收敛；不自动实现并网闭环 |
| 经典同步机 | E相RMS V、Rs Ω、Ls H；Sb VA、H s；Pm W；f Hz、δ电rad、w pu；阻抗不能全零 | 指定δ/w；Ls>0定子i初值0，Ls=0为代数i；Pm当前采样供下一正区间；h=0不推进机械状态 | i内电势→机端，p为外送W；pem=Σei。`test_synchronous_machine.py:23,37,70,96,106,157,166`有独立耦合ODE、能量与一阶收敛；固定内电势近似，没有完整转子绕组 |
| Park同步机 | Sb VA、相RMS基准V；Rs/X/E/Pm及控制量pu；时间常数/H为s；0≤X′≤X，正w、f | 指定6动态初值；代数定子电流可非零/事件跳变；六状态同一左端显式欧拉；AVR/Pm更新后裁剪 | 同行δ/E′/abc同时间层；`test_park_synchronous_generator.py:91,110,125,167,197,222,262,295,304,309`验证两轴端口、气隙功率、独立ODE、一阶收敛/事件/约束拒绝；仅平衡近工频，无完整dq0、次暂态及不平衡短路 |

## 3. 新确认问题：Fault/Breaker允许非二值状态静默改变网络

暂用证据编号`COMP-01`，建议总报告定为**P2，已复现的输入契约问题**。不是合法布尔输入下的元件方程缺陷。

- 位置：`components/switching.py:38–41`、`:49`、`:65`，以及`:82–85`、`:93`、`:113`。构造只验证电阻，状态在stamp/output中直接使用Python真值。
- 表现：`Fault("F", "n", 1.0, enabled="False")`、`enabled=2`、`enabled=float("nan")`均被当作投入。10V源加1Ω故障得到`i:F=10A`、`state:F=1`；`False`对照为0A/0。另实际执行`Breaker("B","n","0",closed="False",closed_resistance=1.0)`得到`state:B=1.0`、`i:B=10.0A`。
- 影响：用户从文本配置或交互输入得到字符串时，`"False"`反而投入故障/闭合断路器。与已有`IdealSwitch`严格验证二值状态的行为不一致；数值结果可能有限且完全满足被错误选择的网络，因此求解器残差无法识别。
- 最小复现：见下方内联代码，或本地忽略目录`.tmp/audit_20261103/component_probes.py`。
- 最小修复：明确支持bool/NumPy bool，是否兼容数值0/1参照IdealSwitch约定；构造与实际使用处验证状态，在改写任何状态前拒绝字符串、NaN、2、数组。可共用一个小私有二值校验函数，无须新建元件框架。
- 兼容性：正确bool输入和标准事件不受影响；依赖任意truthy对象的未声明用法将报错，应在变更说明列明。
- 应增验证：Fault/Breaker分别参数化`False/True/0/1`正常对照及`"False"/NaN/2/array/None`负例，核对非法输入首次求解前失败；若支持直接运行期修改状态，也测试失败采样不推进网络/历史。

```python
from pycy_emt_lite import Circuit, Fault, Resistor, SimulationConfig, Simulator, VoltageSource

parts = [VoltageSource("V", "n", "0", 10.0), Resistor("R", "n", "0", 10.0),
         Fault("F", "n", 1.0, enabled="False")]
row = Simulator(Circuit.from_components("flag", parts), SimulationConfig(0.1, 0.0)).run().rows[0]
print(row["state:F"], row["i:F"])  # 当前：1.0 10.0
```

## 4. 核定后不作为新实现Bug的事项

### 跨元件内部节点名称

`core/nodes.py:21`的`_check_internal_nodes()`只查本元件内部名与本元件外端/地，符合历史I02修复明确范围。`SegmentedLine("LINE",...)`生成`LINE:internal:1`；若另一个电阻的用户节点同名，它们会连线。实际探针中，10V源、总2Ω两段线、8Ω负荷原vout=8V；另加1Ω到该生成节点后变为4.210526315789474V，没有报错。

这证明全局没有保留内部命名空间；**它本身不证明程序误解了现有“同名节点即连线”契约**。现有测试还明确访问内部节点作物理验证、对Park内部源加约束以测试诊断。不能直接把它称为原I02未修复，或一律禁止外部访问。
建议作为低优先级API/文档约定：解释自动节点的命名、是否允许有意引出，提醒避免意外复用。只有在确定“内部节点必须不可外接”的新契约之后，再比较加轻量元数据和保留节点检查的成本；本轮不建议为它引入全局组件注册框架。

### 机组事件时序

补充独立探针使用非平衡初值，避免只验证平衡点造成假通过：经典机初速1.01、机械功率2000W；Park初速1.01、Eq′=0.8。在0.012/0.0123/0.03s分别触发改变网络的单相故障，捕获event.apply前的动态状态，并与事件右侧输出比较。经典2状态、Park6状态的最大跳变量均为**0.0**，且速度已经离开初值。事件右侧只重新求代数量，未重复推进动态状态。证据脚本`.tmp/audit_20261103/machine_event_probe.py`，运行命令`.venv/Scripts/python.exe .tmp/audit_20261103/machine_event_probe.py`，6个组合均通过。

### 文档证据覆盖过期

`models_and_validation.md:29–31`及英文总表，仍把三相π/并联RLC列为局部检查、饱和列为仅线性回归；正文三相部分及`test_three_phase.py:31`已有分段独立六状态DOP853参考。`test_transformers.py:67`已有单方向跨拐点的分段λ–i独立参考、TR/BE与rebuild/reuse及减h验证。
应更新双语表及饱和正文以准确写出**已验证单调分段曲线，未验证独立饱和能量、反向回程/周期累积、磁滞或实际涌流**，保留模型范围，不能因测试多了就删除剩余限制。该项由文档审查统一合并编号。
同一文档“怎样读一个基础测试”中三条命令的`12/4/1 passed`也落后于新增求解策略参数化（静态组合为12/8/2）。不影响算法，但影响新手对运行结果的核对。

## 5. 测试辨识能力与保留设计

- RC/RL不仅看终值，还看一致初值、首步和全曲线；共同物理网格上TR约4、BE约2的误差比，能识别时间层或系数错误。
- 三相源/线路/负荷不仅比较RMS，还核对全相位暂态、各相KCL、故障连续电流、健康相分压和分段解析解。
- 分段线以级联ABCD矩阵、连续均匀线矩阵指数和内部端口能量独立核对；空间误差和时间误差分开，值得保留。
- 线性变压器覆盖四种Y/D接线、相移、绕组/线电流、安匝与输入总电流、TR/BE储能和收敛。主支路和励磁分支职责清楚，不建议改成隐含混合电流输出。
- LC/LCL使用不调用生产stamp的DOP853参考和离散能量账；BE额外耗散被单列，未把它当真实电阻。无需增加另一个滤波器仿真器。
- Park独立ODE仍共享声明模型的近似假设，不能证明商业模型或设备数据等价；但对双轴电抗、符号、气隙功率与一阶推进具有真实辨识度。
- `Component`保留少数必要抽象及默认无状态方法，`StampContext`隔离编号/时间上下文，滤波器只展开基本元件。此结构符合教学定位；不建议仅为减行数合并所有元件，或因文件长而拆出大量中间类。
- 多模块中几行相同的RLC companion公式属小规模显式重复；现有独立测试已能核对。没有已复现维护失配时，不建议引入通用动态元件层。

未验证/可选补强：饱和反向过零和周期累积误差、独立非线性能量、衰减Bergeron的解析幅值/能量、机组更广工况及外部实验数据。它们是证据边界，不是已经发现的错误；应按明确教学需求选最小试验，不扩大现有模型承诺。

## 6. 本分工执行范围

执行了两份本地只读探针（各约2秒内），没有重复运行父任务负责的全量测试。首次文件探针记录非法Fault状态及生成节点连线结果；第二份核对机组非平衡事件状态。脚本及缓存仅在忽略的`.tmp/audit_20261103/`；可追溯的核心复现代码和输出已写入本附录，不要求读者取得本机临时目录。

全仓基线测试、平台、版本、构建与覆盖率以总报告为准。本分工没有执行FULL/BENCHMARK长模式、Linux远端CI、设备实验或商业EMT对标，也没有据历史记录推定当前通过。
