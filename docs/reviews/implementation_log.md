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
