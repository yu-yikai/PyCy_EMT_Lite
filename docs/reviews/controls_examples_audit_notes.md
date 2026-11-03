# 控制系统与教学算例审查证据（2026-11-03）

本文件为全仓审查的分项证据，基于 `main@6b5d206fced1cec48d8f2298f794942b24d108cd`。只新增审查材料与忽略目录内的小型只读验证脚本，未修改生产实现、既有测试或算例。全量测试/算例执行由主审统一记录；本分项没有重复运行完整 FAST/FULL/BENCHMARK。

## 1. 实际阅读范围

以下文件已全文阅读，而非只按关键词扫描：

| 分类 | 文件 | 核对重点 |
|---|---|---|
| 控制源码 | `pycy_emt_lite/controls/__init__.py` | 公共导出；VSC 保留在专用模块 |
| 控制源码 | `pycy_emt_lite/controls/blocks.py` | 参数与输入校验、状态提交、负 Ki 抗饱和、BE 低通、按调用次数延迟 |
| 控制源码 | `pycy_emt_lite/controls/pll.py` | 当前采样角度、归一化误差、绝对频率限制、配置变更检查、溢出回滚 |
| 控制源码 | `pycy_emt_lite/controls/transforms.py` | 幅值不变 Clarke/Park；零序舍弃；反变换与功率系数 |
| 控制源码 | `pycy_emt_lite/controls/pwm.py` | 三角载波、比较极性、调制比和有限性边界 |
| 控制源码 | `pycy_emt_lite/controls/vsc.py` | 独立 PLL、测量滤波、外环/内环符号、圆形限流、矢量限幅、步后保持 |
| 算例 | `examples/01_r_circuit.py` | 10 V/5 Ω 与源支路方向 |
| 算例 | `examples/02_rc_transient.py` | RC 阶跃解析式、时间常数和参数练习 |
| 算例 | `examples/03_rl_transient.py` | RL 阶跃解析式、电流状态与正向 |
| 算例 | `examples/04_rlc_transient.py` | 欠阻尼阶跃解、过阻尼时明确跳过比较 |
| 算例 | `examples/05_three_phase_steady_state.py` | RL 负荷相量、RMS 与三相功率 |
| 算例 | `examples/06_three_phase_short_circuit.py` | 带线路 L 的故障/清除、最短时间常数及物理窗口 |
| 算例 | `examples/07_single_phase_ground_fault.py` | 无储能的分相电阻网络、故障相与健全相 |
| 算例 | `examples/08_pi_line_transient.py` | π 线相量解、源导数、串联与电容电流 |
| 算例 | `examples/09_single_phase_transformer.py` | 一次折算漏阻抗、励磁 DC 分量、总输入电流与功率 |
| 算例 | `examples/10_park_generator_avr_governor.py` | 平衡初值推导、三相容量基准、负荷阶跃、机电一阶推进 |
| 算例 | `examples/11_pll_dynamic_response.py` | t=0 观察、采样时间层、rad/s、正弦相位与空间矢量角 |
| 算例 | `examples/12_two_level_pwm_generator.py` | 零阶保持、互补门极、平均基波参考、默认绘图 |
| 算例 | `examples/17_single_phase_ac_rlc.py` | 相量阻抗、完整周期投影与启动状态 |
| 算例 | `examples/18_three_terminal_vsc_hvdc.py` | 所有参数与拓扑、双极线路、功率账、统计、模式和输出 |
| 测试 | `tests/test_controls.py` | 单块、非法输入保持状态、PLL 独立连续 ODE 与一阶收敛 |
| 测试 | `tests/test_power_electronics.py` | 开关电流消去保护、滤波 ODE/KCL/能量、PWM 三档步长 |
| 测试 | `tests/test_synchronous_machine.py` | 铜损、机械能、独立耦合 ODE、RL 离散能量 |
| 测试 | `tests/test_park_synchronous_generator.py` | 独立 dq 端口、分段 ODE、同刻状态、事件保持 |
| 测试 | `tests/test_three_terminal_vsc_hvdc.py` | 单站、双站、完整 FAST、桥/DC 守恒、坏波形辨识 |
| 当前文档 | `docs/three_terminal_vsc_hvdc.md` / `.en.md` | 双语全文；公式、参数、代码映射、历史与当前验证边界 |

另外针对性阅读了 `docs/component_derivations.md` / `.en.md` 第 10、12 节，以及 `docs/models_and_validation.md` / `.en.md` 同步机与控制章节。历史审计记录按问题清单、R5、R7–R12、N1–N4 与当前交付状态定向核对，未声称全文阅读历史逐次日志。机器源码与其全部模型方程另由元件分项审查覆盖。

## 2. 已证实的问题与明确缺口

### CE-01（P2，静态证实并运行核对）：双语元件推导仍用误差符号描述 PI 冻结

- 位置：`docs/component_derivations.md:725–726`，`docs/component_derivations.en.md:725–726`；对应实现 `pycy_emt_lite/controls/blocks.py:118–127`，现有保护测试 `tests/test_controls.py:43–49`。
- 表现：文档写“超上限且 e>0，或低于下限且 e<0”就不保存积分，并明确称这是源码实际判据。
- 原因：源码已经按 `increment=Ki*e*h` 的方向修复，文档保留了只适用于正 Ki 的旧说法。通用 PI 合法支持负 Ki；不能把 PLL 非负增益约束套到通用 PI。
- 复现：`PIController(0,-1,lower=-1,upper=1); reset(2); step(1,.5)` 返回 1，积分状态从 2 降至 1.5；按文档的 `e>0` 判断则错误预测冻结在 2。
- 影响：学习者照推导重写控制块会重新引入历史 I16 的方向错误；生产源码本身已正确，不能重报为当前 PI 算法 Bug。
- 最小修复：中英同处把 `e>0/e<0` 改为 `Ki*e*h>0/<0`，并说明 Ki=0 时无积分增量；保留候选输出与已保存积分不必一致的准确说明。
- 兼容性：只修文档，无 API 或数值变动。
- 验证：沿用现有正/负/零 Ki 参数化测试和下述反例；人工核对中英公式，避免为这类文本增加脆弱的逐字测试。

### CE-02（P2，测试缺口，未证实生产错误）：VSC 下游限幅的状态恢复没有直接回归

- 位置：`pycy_emt_lite/controls/vsc.py:139–160`，尤其 q 圆形裕量截断时回滚 Vac 积分（142–143），最终电压矢量饱和时回滚两个电流积分（155–157）。现有调用测试集中在 `tests/test_three_terminal_vsc_hvdc.py:174–337`，控制单测对 VSC 只直接检查 `tests/test_controls.py:51–60` 的 PLL 遥测。
- 表现：已有完整 FAST 测试检查门极、调制逐相上界、均值、守恒和故障恢复；没有直接断言电流参考圆内/d 优先、仅 q 截断时的 Vac 积分保持、最终矢量饱和前后电流积分保存/释放。故障工况可能执行相关分支，不能替代行为验收。
- 原因：专用控制器的饱和逻辑叠加在通用 PI 的自身输出限幅之外；通用 PI 的抗饱和测试并不能辨识这里的下游回滚错误。
- 证据：全文核对上述测试；小型合成测量烟雾核对能得到参考幅值 1500 A、逐相下一步调制最大值 0.93429（≤0.98），但该两点烟雾检查不构成恢复过程证明。
- 影响：删除或反转下游回滚时，现有物理守恒仍可通过，均值门槛也未必立即失败；不据此认定当前积分逻辑错误。
- 最小修复：新增几组不跑 EMT 的合成 dq/abc 有限测量序列，分别激发/解除 q 参考截断与电压矢量饱和；以独立公式断言参考向量、积分保存/释放和有限输出。实际故障电流仍可大于参考限制，不能修改网络电流来满足 1500 A。
- 兼容性：只增加定向测试，无需改控制律、默认增益或 FAST 门槛。
- 验证：测试应能识别删除 q 回滚、删除 d/q 回滚、逐相削顶替代矢量缩放等明确变异；解除饱和后按现有数学约定恢复积分，随后保留完整 FAST 物理回归。

### CE-03（P3，静态证实的教学输出不一致）：示例 12 描述的阶梯相电压未绘出

- 位置：`examples/12_two_level_pwm_generator.py:3–4` 与 `:136–144`。
- 表现：文件开头说观察负载端阶梯状相电压和接近正弦的电流，默认 `plots` 只有 `i:La/i:Lb/i:Lc`。
- 原因：绘图配置只有电流；浮置星点负荷相电压需用 `v:phase_a-v:load_n` 等差值，不能直接把桥极点对地电压称为负荷相电压。
- 复现：调用 `define_case()`，`[p.columns for p in case.plots]` 仅为 `[("i:La","i:Lb","i:Lc")]`。
- 影响：初学者运行后找不到说明中承诺观察的电压，也不容易从电流理解开关纹波如何形成。
- 最小修复：若保持当前输出，直接把开头目标改为“观察电流，负荷相电压的提取见测试”；若补图，应选择短窗口绘制实际负荷相电压并明确浮置中性点。不要为一张图引入通用表达式引擎或新公开输出格式。
- 兼容性：修文字无影响；补图会增加交互窗口/保存文件，需同步说明。
- 验证：检查图中电压确为相点减星点，和 `tests/test_power_electronics.py:343–365` 的独立戴维南关系一致；文字方案不需要新自动化测试。

## 3. 关键公式及实现核对

### 通用控制、变换与 PLL

1. PI：候选积分 `xi*=xi+Ki*e*h`，候选输出 `u*=Kp*e+xi*`，先限幅后按积分增量方向决定保存。负 Ki 复现结果与源码及现有测试一致。输出使用候选值，冻结时不能误写成 `Kp*e+saved_xi`。
2. 一阶低通：`y1=(y0+(h/tau)u1)/(1+h/tau)` 是 BE，合法 h/tau 下为有界加权平均。计算溢出明确拒绝，未静默保存非有限量。
3. 延迟按调用次数，不保持固定物理秒数；`SampleDelay` 有合理分配上限，改变 steps 会明确拒绝。
4. 幅值不变变换：`alpha=2/3(a-b/2-c/2)`，`beta=(b-c)/sqrt(3)`；`d=alpha cos+beta sin`、`q=-alpha sin+beta cos`。零序被丢弃，不能对任意 abc 承诺无损往返。无零序时 `P=1.5(vd id+vq iq)`；独立数值核对 abc 功率 1664.9999999999998 W、dq 功率 1665 W，往返 250/-70 的差为浮点舍入。
5. 对真实空间角 `theta_g` 的正序平衡电压，`vq=V sin(theta_g-theta)`，正增益 PLL 的反馈方向正确。源码先 `theta1=wrap(theta0+omega0*h)`，再用同刻电压求误差并更新 `omega1`；不是意外多延迟一步。`omega1` 用于下一角度区间是声明的显式采样规则。
6. 误差归一化是 `vq/max(abs(vd),abs(vq),1 V)`，并非矢量模长归一化。文档和独立连续 ODE 测试均明确对应这一定义。额定/限制单位为 rad/s，VSC 输出遥测转换为 Hz；绝对频率限制换算为 PI 修正量限制正确。
7. 示例 11 的 30° 是正弦源偏移，锁定空间角为 `omega*t+30°-90°`；模型文档已说明，不能误把初始 PLL 当成落后 30°。该算例 t=0 未积分，终点和整步限制也有测试。

### VSC 控制和桥端口

电流正向 AC→converter，`L diabc/dt=vg-vc`。旋转变换求导给出：

```text
L did/dt = vg_d - vc_d + omega L iq
L diq/dt = vg_q - vc_q - omega L id
vc_d* = vg_d + omega L iq - PI(Id*-Id)
vc_q* = vg_q - omega L id - PI(Iq*-Iq)
```

因此 PI 在电压命令中取负号正确。`P=sum(vabc*iabc)` 保留实际零序功率；`Q=1.5(vq id-vd iq)` 与感性吸收正号一致。d 对齐时正 Iq 对应容性支撑，低 Vac 增加 Iq*；低 Vdc 增加从 AC 吸收的 Id*。测量滤波是明确的一阶低通，不是隐藏采样器。

`sample()` 只在网络完成后的回调更新一次，门极 callable 读保持调制，与当前/下一步遥测字段一致。故障一致求解不额外推进控制。上下管互补、无死区，`m>=carrier` 导通。每相两电导对应 `[DC+,phase,DC-]` 的拉普拉斯块，确实进入 MNA。

桥功率独立式 `Pac_bridge=Pdc+sum(Gsw*Vsw**2)` 与 `Pdc` 的符号核对一致。相电抗器交流端 Pac 不能直接用于该桥损耗式，测试正确使用桥交流端。DC 两极储能、站电容负端方向和所有半段线路的 R/L/C 账一致。

BE 离散能量恒等式：

```text
ΔE = h(Pdc_in - ΣR i_k²) - 0.5ΣC(Δv)² - 0.5ΣL(Δi)²
```

测试独立重算能量及数值耗散，未把小 MNA 残差当成物理验证。只存事件右侧量时排除跨事件能量区间有明确原因，同时另查故障电流和状态。

### 机组算例、验证和文档

示例 10 的初值满足 `I=1/Rload_pu`、`Iq=I*A/hypot(A,Xq)`、`Id=I*Xq/hypot(A,Xq)`，其中 `A=Rload_pu+Rs`。代入端口式及暂态电势导数，可得到初始电压 1 pu、速度 1 pu、Pm 覆盖铜损。测试以消去平衡电阻网络后的连续 ODE，核对 200/100/50 μs 的共同时间点一阶收敛。

两个电机模型文档正确区分经典机定子 L 的电流状态与 Park 代数电流；Park 不能拿 X'/omega 当三只独立动态电感。机械能 `H*Sbase*w²` 给出带 w 分母的功率形式摆动方程，标幺与三相总容量基准一致。AVR/调速器为一阶状态裁剪，并非通用冻结式 PI。其饱和恢复等更广工况不由当前平衡负荷 ODE 自动保证。

## 4. 已确认优势和应保留的边界

- 六个控制源码文件（其中 `__init__` 为导出入口，其余五个为实现/接口文件）职责自然；控制块不继承电气 Component，VSC 不另建网络求解层。
- 14 个例子中的 01–04 已有接线、预期、单参数练习、源码入口；其教学性明显高于逐行解释 Python。
- 示例 05 的 RL 相量、08 的 π 线端电流、09 的励磁直流分量、17 的工频相位投影说明与算法一致，应保留。
- 测试包含独立 ODE、能量、共同时间点收敛、错误相位和零均值振荡负例；高通过率不只来自重复实现比较。
- 三端示例明确区分原 benchmark 参数、PyCy 调整、有限 RC 缓冲、理想双向电导开关与完整 IGBT；默认 FAST 不冒充商业等价平台。
- FAST 严格 RMS 不达标是已记录的模型/控制精度边界，历史 I34 假通过已由汇总指标和合成负例修复。按历史 R12 明确授权的用途，不能再把观察性 `control_accuracy_met=0` 称为当前必须修复的程序缺陷，也不能偷偷调参/降阈值。
- 预计算在 HVDC 入口提前拒绝；小网络有限状态能力仍保留。rebuild 默认与 reuse 选择是合理、可解释的折中。
- 控制代码按物理链条线性展开，即使 `VSCController.sample()` 较长，也没有证据要求拆成多层策略/工厂。可用少量段落注释解释测量→外环→参考限幅→内环→电压限幅→保持，无需重构公开接口。

## 5. 未验证事项及后续最小方案

1. 未运行 FULL/BENCHMARK，不以历史记录代替当前复验；未重新运行商业 Simulink/PSCAD 或核定所有参考文件 hash。
2. 未证明弱网/负序/失压锁定、闭锁整流、保护或设备开断电压能力；现有文档已排除，不作为缺失功能 Bug。
3. 未对三站闭环做小信号或全运行点稳定性证明；单标量环推导、均值通过与守恒不足以证明它。
4. FAST 20 μs/1000 Hz 每载波 50 步，FULL/BENCHMARK 在 PWM 与时序也改变；不能把跨 MODE 差异视为纯步长收敛。现有单站固定 PWM 的 20/10 μs 和 PWM 例 5/2.5/1.25 μs 对照更有辨识度，应保留。
5. 1500 A 是参考矢量上界，不能限制已储能网络的实际故障电流。RC 清除缓冲改变物理模型；3 MV 级峰值是声明电路的结果，非设备预测。
6. 如需缩小基础控制到三端系统的学习跨度，优先在 HVDC 文档中增加一段“沿已有单站/双站测试读源码”的导航，对应 `test_single_bridge_open_loop_power_identity`、`test_single_station_pll_and_dq_tracking_with_step_refinement`、`test_two_station_intermediate_dc_exchange`。没有必要为补编号恢复 13–16 或先新增框架。

## 6. 本分项执行证据与外部核对

执行命令（项目根目录，已有锁定环境）：

```powershell
$env:PYTHONPATH = (Get-Location).Path
.venv/Scripts/python.exe .tmp/audit_20261103/controls_reproduce.py
```

脚本和日志在 `.tmp/audit_20261103/controls_reproduce.py` / `controls_reproduce.log`，未纳入发布文件。它只构造对象并计算少量有限合成输入，不运行全网。输出包括负 Ki 积分 1.5、示例 12 只有电流图、dq 功率恒等式舍入级差以及 VSC 1500 A 参考限幅烟雾结果。

2026-11-03 读取了 [DIgSILENT 官方 benchmark 发布页](https://www.digsilent.de/index.php/en/faq-reader-powerfactory/benchmark-of-a-three-terminal-vsc-hvdc-system-in-powerfactory.html)，确认其提供白皮书和 PSCAD/Simulink 模型下载；没有据此重新认证仓库历史商业模型对标数值。另核对了 [MathWorks 官方二阶高通滤波器说明](https://www.mathworks.com/help/simscape-electrical/ref/passiveharmonicfilterthreephase.html)，其二阶高通的 C/L/R 参数关系与例 18 的换算形式一致。仓库旧链接会重定向到此当前页面；此核对不等于逐项验证原 R2022b SPS 掩膜实现。
