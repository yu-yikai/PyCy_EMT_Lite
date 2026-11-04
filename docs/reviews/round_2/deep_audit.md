# 第二轮深度复审

日期：2026-11-04（Asia/Shanghai）。基线 `main@f0bf847655d6b158918b549bf4085d37749bc805`，版本 0.1.1，开始时工作区干净。
本轮审查按最初要求完成独立复核及第一批小范围整改后暂停，验收前未提交或推送。用户后续已明确授权提交并推送本批，交付操作见 [实施记录](implementation_log.md)。第一轮报告作为历史快照保留，实际完成状态以其实施日志为准。

## 结论与继承

确认两项 P1（合法 VSC 输入的计算错误，均已修复）及一项 P2（非法状态输入/事件日志路径，留待下一批）。未确认新的核心 MNA、RLC 积分或其他已检元件方程缺陷；这不是任意参数、拓扑或设备准确性的证明。
本轮只改一个生产文件中的两处局部逻辑、现有控制测试和本目录四份报告。未改网络方程、积分/事件推进、控制增益、输出列、保存协议、依赖或公开签名。

从第一轮原始基线 6b5d206 到当前的 12 次提交已按实际 diff 核对：T1 的共享二值规则确实覆盖构造/stamp/update/outputs，T8 确实新增下游回滚/恢复与方向断言，T2/T3/T4/T5/T6/T7 的中英正文与当前行为一致。第一轮 T9 的稳定 Windows/Linux 结果属于历史已完成证据，不再称未执行，也不冒充本轮修改后的 CI。本轮重新运行的基线/最终结果见 [实施记录](implementation_log.md)。

第一轮没有把 VSC 电压矢量测试下探到亚伏，T8 的 current_limit 使用普通 float，因而未识别以下两个独立反例。不是旧修复回退，也不是 FAST 精度边界的新包装。

## 第一批：VSC 数值尺度与配置标量

### R2-001 / P1 / 已确认合法输入的控制计算错误

- 位置：`pycy_emt_lite/controls/vsc.py`，`sample()` 的 dq 电压矢量限幅，基线 154 行。
- 复现：零电流、t=0、Vdc=1 V、dq 电压 (0.2,0) V、调制上界 0.98。独立桥关系 `mabc=2*vabc/Vdc` 应为 (0.4,-0.2,-0.2)，幅值 0.4，未达到限制；旧源码实际为 (0.196,-0.098,-0.098)。把所有电压同乘 100 后才得到正确结果。
- 原因：`min(1, available/max(norm,1 V))` 以带量纲 1 V 下限替代实际范数；available<1 V 时会错误缩小尚未饱和的矢量，并可能错误回滚电流积分。
- 最小方案：仅当 `norm>available` 时取 `available/norm`，否则 scale=1。零向量属于后一分支，不需虚构电压下限。保留现有低 Vdc 保护分母、矢量方向及调制上界。
- 兼容影响：修正受影响低压数值；不调增益、不改参考算法/采样层、网络物理方程或公开 API。高压既有分支应逐值等价，须实际验证。
- 验证：正式测试先在旧实现失败；覆盖零/未饱和/边界/饱和、非零方向、亚伏至 HVDC 尺度、dt>0 积分保存和 m/m_next。
- 状态：已修复。最终位置 154–156 行；正式测试 `tests/test_controls.py:148,166`。旧实现六个低压向量例和一个错误冻结积分例失败；修复后全部通过。隔离恢复旧分母再次触发 7 failed。证据 `.tmp/round2-controls/minimal_scale.py`、`red.log`、`mutations/`。

### R2-002 / P1 / 已确认合法 NumPy 实数配置的溢出

- 位置：同文件 `VSCControlConfig.__post_init__()`，基线 41–42 行，以及 q 裕量 `current_limit**2`。
- 复现：合法 `current_limit=np.int8(20)` 通过有限正实数校验，但 20 的 NumPy int8 平方溢出为负；Id=0、Vac 误差 0.1、ac_kp=10、ac_ki=1、积分初值 0、dt=.001 s 的正常 q 候选 1.0001 A 被截成 0，使用 float 20 的对照正确。
- 原因：校验器返回 float，但 frozen 配置没有保存返回值，后续仍在窄整数 dtype 上计算；输入不变性与物理限流圆被破坏。
- 最小方案：按既有 float 字段注解，在构造期以 `object.__setattr__` 保存 `_finite_real` 的返回值；保持原合法范围和所有限制值。
- 兼容影响：接受的 NumPy 实数配置以 Python float 保存，避免窄 dtype 运算；不改变参数含义、默认值、公开签名或依赖。验证常规 float 配置轨迹保持。
- 验证：先建立独立电流参考与 float 对照的失败测试，再修复；覆盖小整数和浮点标量，不以实现类型断言替代物理预期。
- 状态：已修复。最终位置 41–42 行；正式测试 `tests/test_controls.py:195`。旧实现 np.int8 例失败，float/np.int64/np.float32 对照通过；修复后通过，隔离去掉规范化再次触发 1 failed。没有因该窄整数溢出改变当前限制值或扩大非法参数范围。

## R2-003 / P2 / 已确认非法输入校验与日志边界，本批未修

位置 `pycy_emt_lite/events/standard.py:49`：`before=bool(getattr(...))`。

```python
from pycy_emt_lite import Circuit, Fault, FaultClearEvent, SimulationConfig, Simulator, VoltageSource

f = Fault("F", "n", 1.0, enabled=False)
f.enabled = "False"  # 构造后写入的非法值
c = Circuit.from_components("zero_event", [VoltageSource("V", "n", "0", 10), f])
r = Simulator(c, SimulationConfig(.1, 0), [FaultClearEvent(0, "F")]).run()
# 基线及本批后均成功：event_log[0]['before']==1.0，state:F==0.0
```

原因是 t=0 事件早于第一次 stamp，先按 Python 真值记录旧值并覆盖，之后的二值校验只能看到合法 False。影响限于非法改值路径的漏拒绝/不实 before，不是合法布尔状态下的错误电路，正时刻回调仍受下一次左侧求解校验保护。
最小后续方案是在设置前复用 `_binary_state`，以四类标准事件验证拒绝先于 setattr/日志/求解；保留类型检查和 bool/np.bool_/0/1。兼容影响为非法改值更早失败，合法事件应逐值不变。独立复现脚本 `.tmp/round2-engineering/probes.py`；下一批实施前仍须先写正式失败测试。本批主动不混入该不相关修改。

## 无新增缺陷的已检范围

| 实际审查范围 | 增量证据及结论 |
|---|---|
| core 下 simulation/stamping/circuit/nodes/variables/context/solvers；basic/base/switching；events | 独立关联矩阵六状态 RLC、相关电容约束、非零初值、三策略、重命名/重排/地别名、事件左/右侧、离散能量共 132 轨迹通过；不重写主循环。 |
| lines/transformers/three_phase、filters、两种 machines | 八类独立公式/ODE、负功率和非平衡适用工况通过；细节见 [数值验证](numerical_validation.md)。 |
| controls 全模块、power_electronics | 除两项已修 VSC 缺陷外，复空间变换、Decimal PI、低通闭式、PLL 相差 ODE、PWM 独立计时、双向开关功率及旋转不变量通过。 |
| io/results、analysis/metrics、cases、plotting/reporting、各包导出及工程配置 | 300 格式往返、Fraction 指标、输出预检/损坏归档等正式测试通过，未发现已检合法输入的新静默数据错误。 |
| README 中英、当前专题、第一轮报告/计划/清单/分项/实施记录及历史计划相关阶段 | 16 个 Python 块、396 个本地路径/锚点通过；保留已修结论和未认证范围，不复制旧清单作为新问题。 |

审查涉及全部包模块职责；对未变化的 __init__ 导出/空标记作接口核对，独立深度试验集中于高风险实现。不是每个函数、所有浮点输入或所有上游源码的穷举证明。

## 架构与学习路径判断

`Simulator.run()` 的积分左侧→事件→冻结状态右侧→更新→一次回调链有物理必要性；precompute 的隔离副本、有限状态与真实 A 核对属于可解释复杂度。没有发现局部抽取能明显减少真实复杂度的证据，不因行数拆文件或增加策略工厂。现有元件状态/网络解/控制状态所有权、A/b/x 断点和中间测试路线保留。
唯一明确类型/实现失配 R2-002 已在当前配置入口解决，无新抽象层；性能 F1 没有新测量或需求，不实施。已有双语推导没有写入错误的 1 V 矢量公式，实际写的是矢量限幅，修复使实现符合该约定，故无需为代码小修扩写教程。

## 残余边界

未进行真实初学者 GUI/IDE 试用、当前远端双平台运行、FULL/BENCHMARK、商业模型或真实设备对标；饱和回程/周期/能量、弱网/负序 PLL、Park 不平衡工程认证仍是明确范围外能力。低残差/覆盖率不证明任意病态矩阵的前向精度。
OutputOptions 的字符串 truthiness 是未声明输入的一致性边界，本轮不据此另造高优先级问题或改保存接口。第一批完成后停止修改，后续只依据新证据选择下一批。
