# 分阶段实施记录

开始日期：2026-11-03（Asia/Shanghai）。输入计划：[improvement_plan.md](improvement_plan.md)。

起点：`main@6b5d206fced1cec48d8f2298f794942b24d108cd`，版本 0.1.1。
开始时 `git status --short` 仅有 `?? docs/reviews/`；六份用户提供的审查文档原样保留并纳入版本控制，生产代码无既有工作区差异。

执行范围为 T1–T9，包括教学文档 T2/T3/T4/T7；每个实际任务独立提交。
T10 是有性能需求和稳定总流程收益证据才启动的可选候选，本轮没有新的性能需求，不引入读取优化。默认 rebuild、PLL 80/1000、FAST 用途及 HVDC 拒绝 precompute 的边界保持。

## 验收记录

各项完成后在此追加实际命令、结果、兼容影响及未验证范围。历史审查文档描述的是整改前快照，不能代替本轮验收结果。

### 第一期 T1 / AUD-001：严格二值状态

- 修改 `components/base.py`、`switching.py`、`power_electronics.py` 和 `tests/test_events.py`（源码位于 `pycy_emt_lite/`）。三种开关共用 `_binary_state` 规则；Fault/Breaker 构造、stamp、更新和输出均拒绝非法值。允许 bool/np.bool_ 及实数 0/1；Fault/Breaker 不接受可调用门极。
- 独立预期：10 V/1 Ω 导通为 10 A，断开为 0 A；回调中的合法改值在下一求解区间生效。旧实现的构造反例先运行得到 28 failed（均未抛错），修复后通过。
- `.venv/Scripts/python.exe -m pytest tests/test_events.py tests/test_power_electronics.py tests/test_step_callback.py --basetemp=.tmp/pytest-t1-green --junitxml=.tmp/t1-tests.xml`：335 passed；覆盖标准事件和三种求解模式下回调非法值在下一次求解前失败，且无新采样输出。
- 同解释器快速回归 `-m 'not slow' --basetemp=.tmp/pytest-t1-fast --junitxml=.tmp/t1-fast.xml`：1088 passed、9 deselected；组件及新测试 Ruff 通过。此处解释器为既有 3.14.0rc3，稳定版另见 T9。
- 兼容影响仅为此前未声明的 truthy 状态输入改为抛错；合法状态的电导、事件时刻、输出名及积分方程不变。

### 第二期 T2 / AUD-006：内部节点契约

- 在中英数值约定和元件推导说明局部冲突拒绝、生成名可见、跨元件同名显式抽头允许及改名同步要求，无源码更改。
- 独立分压：10 V 源、总 2 Ω 两段线、8 Ω 负载得到 8 V；在中点并接 1 Ω 后，`10×0.9/1.9×8/9=4.21052631578947 V`。实际探针与公式相符，两者节点列表均为 `['in', 'out', 'LINE:internal:1']`。
- 既有 `internal_node_collision` 三个参数例通过，`git diff --check` 通过。保留 I02 局部防冲突范围，不增加节点或改变命名/数值行为。

### 第三期 T3 / AUD-005：例 12 学习目标

- 仅修正例 12 开头说明，使学习目标对应实际三相 RL 电流图及开关纹波；选用计划中的最小文字方案，不增图或改 PWM/网络参数。
- `MPLBACKEND=Agg OPENBLAS_NUM_THREADS=1 .venv/Scripts/python.exe examples/12_two_level_pwm_generator.py` 默认运行通过，40001 样本，三相基波 RMS 为 105.609214/105.538711/105.605329 A；默认不保存。字体缓存权限提示不影响此次运行，T9 使用仓库内缓存目录。

### 第四期 T5 / AUD-002：PI 抗饱和双语推导

- 中英元件推导改按 `Δxi=Ki·e·h` 方向判定上下限冻结，解释负 Ki、Ki=0 及候选输出与保存积分的时间层，不改源码。
- 指定手算 `Kp=0, Ki=-1, xi=2, e=1, h=0.5, upper=1` 得输出 1、保存 xi=1.5。稳定 Python 3.14.5 定向 PI 测试 6 passed；11 个独立正/负/零 Ki、上下限及候选输出/保存状态差异探针通过；`git diff --check` 通过。
