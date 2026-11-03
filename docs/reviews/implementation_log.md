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

### 第三期 T4 / AUD-007：中间阅读与调试导航

- 中英 README 增加既有单桥开环→单站 PLL/dq→双站 DC→三站 FAST 测试路线，以及 CaseDefinition、`_assemble` A/b、`_solve_step` x、RLC 历史量和回调时间层的断点导航。
- 稳定 Python 3.14.5 环境执行文中单桥选择命令：1 passed；文件链接、四个测试符号及 `git diff --check` 通过。用 `sys.settrace` 核对 RC 三采样的 assemble→solve→update_state→on_step 顺序及 A/b/x 形状。
- **未验证：真实初学者跟随试用。** 脚本与断点顺序核对不等同于 GUI/IDE 教学体验验收。无新模型、脚本或运行行为变更。

### 第四期 T5 / AUD-002：PI 抗饱和双语推导

- 中英元件推导改按 `Δxi=Ki·e·h` 方向判定上下限冻结，解释负 Ki、Ki=0 及候选输出与保存积分的时间层，不改源码。
- 指定手算 `Kp=0, Ki=-1, xi=2, e=1, h=0.5, upper=1` 得输出 1、保存 xi=1.5。稳定 Python 3.14.5 定向 PI 测试 6 passed；11 个独立正/负/零 Ki、上下限及候选输出/保存状态差异探针通过；`git diff --check` 通过。

### 第四期 T6 / AUD-003：验证与求解策略说明

- 六份中英专题文档同步三相六状态 DOP853 AC/故障参考、并联负荷 KCL/π 线能量、单向分段 λ–i 饱和参考及剩余未认证范围；总表直接指向正式测试函数。
- 教学段落解释参数化而不固定易漂移的数量；主循环说明默认 rebuild 与可选 reuse/precompute，N4 成本测量标为已完成，同时保留未核定通用/稳定全流程加速及 HVDC 拒绝 precompute。
- 稳定 Python 3.14.5 下三个教学入口实际收集 12/8/2，共 22 passed；16 个当前 Python 文档块全部运行通过；396 个本地路径/锚点通过；双语代码块一致，67 组推导显示公式除一处翻译 text 注释外一致；`git diff --check` 通过。复验脚本和结果保存在 `.tmp/t6-doc-checks/`。
- 无源码或可执行文档块更改，未为纯段落变更重复高成本仿真。独立简化模型参考不扩张为设备或商业模型认证。

### 第四期 T7 / AUD-009：同名保存覆盖提示

- 中英 README 保存段明确同一输出根目录/案例名会替换前次同名 result.csv/json/npz 或图片，比较前先复制或改案例名。
- 人工核对 `cases.py` 默认保存关闭、固定文件名及 `plot.figure_name` 路径；`git diff --check` 通过。不改保存行为、格式或默认设置。

### 第五期 T8 / AUD-004：VSC 多级限幅与积分恢复

- 仅 `tests/test_controls.py` 增加五个合成样本。d 优先限流独立计算 `sqrt(10²−Id²)`，Id=0/8 A 的 q 裕量为 10/6 A，对照 Vac PI 候选 ±8.5 A，检查截断与未截断及解除后的 ±0.5 积分恢复。
- 固定 dq 电压 (90,60) V、电流 (3,-4) A，从 t=0 开始以 1 ms 递增。Vdc=100 V 的 45 V 矢量限幅冻结 d/q 积分，升到 400 V 后按 (-0.06,+0.08) 增量恢复；独立相投影核对矢量方向/幅值、逐相调制上界及 m/m_next 时间层。
- `.venv/Scripts/python.exe -m pytest tests/test_controls.py --basetemp=.tmp/t8-controls-all`：157 passed；Ruff 和 diff 检查通过。生产 `controls/vsc.py` 无更改。
- `.tmp/t8-vsc-mutations/` 隔离副本基准 6 passed；删除 q 回滚 2 failed，删除 d/q 回滚 1 failed，逐相削顶代替矢量缩放 1 failed，均被目标状态/方向断言识别。正式工作区未做变异；摘要记录源码/测试 SHA256 和运行命令。变异解释器为 rc3，最终正式测试在稳定版 T9 再验。

### 第五期 T9：工程复验及 Windows CI 编码修复

- 新建忽略目录 `.tmp/venv-py3145`，以稳定 CPython 3.14.5 运行；`uv sync --locked --python .uv-python/cpython-3.14.5-windows-x86_64-none/python.exe` 成功，27 包。原有 rc3 `.venv` 保留。平台 Windows 11 build 26300；NumPy 2.5.2、SciPy 1.18.0、Matplotlib 3.11.1、pytest 9.1.1、pytest-cov 7.1.0、Ruff 0.16.10、mypy 2.4.0；Agg、OPENBLAS_NUM_THREADS=1。
- 稳定版 `python -m ruff check pycy_emt_lite examples tests` 通过；`python -m mypy --cache-dir=.tmp/t9-stable/mypy-cache` 通过（39 源码文件）。
- 稳定版 `python -m pytest -p pytest_cov --basetemp=.tmp/t9-stable/pytest --junitxml=.tmp/t9-stable/tests.xml --cov --cov-report=term-missing --cov-report=xml:.tmp/t9-stable/coverage.xml --cov-report=html:.tmp/t9-stable/htmlcov`：**1097 passed**，无跳过，155.97 s；覆盖率 93% 只作覆盖统计，不证明物理正确性。启动 HEAD 为 4e91b06，T8 最终测试当时已在工作区，之后仅提交该相同测试及文档/CI。
- 14 个默认 examples 全部 Agg 通过；无 `outputs` 生成。18 FAST 共 40001 样本、h=2e-5 s、0.8 s，六条故障事件正确，全部有限，DC 平衡残差 0.0270173 W。日志、完整命令及环境在 `.tmp/t9-stable/`；与 pytest 并行的耗时不作为性能基准。
- `uv build --out-dir .tmp/t9-dist-final` 成功，明确由 sdist 构建 wheel；在源码树外临时目录用 `uv run --python <stable-python> --isolated --no-project --with <wheel> python smoke.py` 安装导入，检查版本 0.1.1、`py.typed`、安装路径、10 V/5 Ω=2 A 及二值拒绝修复均通过。pyproject/uv.lock/__version__/py.typed 未改。
- **ENG-001（T9 新确认工程问题）**：起点的 [Windows CI](https://github.com/yu-yikai/PyCy_EMT_Lite/actions/runs/41632731319) 在首例中文摘要输出处因 CP1252 抛 UnicodeEncodeError；Linux 已通过，不能笼统称双平台通过。本地以 `PYTHONIOENCODING=cp1252` 运行例 01 复现同一错误。在 CI job 环境加 `PYTHONUTF8=1`，本地确认 stdout=utf-8 且首例通过。不改生产输出或数值逻辑；新一轮远端双平台也均通过，见下方最终结果。
- 额外最小等价探针在两个隔离副本中比较起点 6b5d206 与当前 T1 三个生产文件：Fault/Breaker × RL/RC × TR/BE × 三种求解模式 × 十种合法状态，共 240 条轨迹（10 V 源、R=2 Ω、L=0.2 H 或 C=0.1 F、开关 1 Ω、h=1 ms、0–6 ms、2/4 ms 标准事件）。15120 个 float64 值逐字节一致，列序、全部行、480 条事件及元数据一致。脚本、轨迹和双方源码 SHA256 留在 `.tmp/t9-equivalence-20261103/`，当前生产文件对应 814f1ed；未重复高成本 FAST。

### 条件任务和未验证边界

- T10 / AUD-008 不启动：没有新增性能需求，也没有交错测量/进程峰值/稳定总流程收益证据，按计划保留 F1 原实现，不能宣称优化收益。
- T4 真实初学者 GUI/IDE 跟随试用未做；FULL/BENCHMARK、商业模型/设备认证、饱和回程/能量等不在本轮扩展范围。

## 最终远端验收

已推送 `main@f7801001af35cf3e0ac1f64474086e5dd311340e`，该提交的 [GitHub Actions 41641078937](https://github.com/yu-yikai/PyCy_EMT_Lite/actions/runs/41641078937) 最终为 **success**。

| 平台 | 实际稳定解释器 | 实际全量测试（含 slow） | 其他门禁 |
|---|---|---|---|
| [Linux](https://github.com/yu-yikai/PyCy_EMT_Lite/actions/runs/41641078937/job/125934454463) | CPython 3.14.7 | 1097 passed，223.76 s | Ruff、mypy（39 文件）、14 默认示例、sdist→wheel、源码树外安装冒烟、工作区清洁均通过 |
| [Windows](https://github.com/yu-yikai/PyCy_EMT_Lite/actions/runs/41641078937/job/125934454803) | CPython 3.14.10 | 1097 passed，298.68 s | 同上全部通过，中文首例输出通过 |

数量和解释器来自本次实际 job 日志，不推用本机或历史结果；原始日志、最终 run JSON 与摘要保存在 `.tmp/t9-ci-monitor/`。
之后仅补交本验收记录，以 `[skip ci]` 避免为记录重跑相同高成本检查；已验证的代码、测试、依赖、示例、双语正文和 CI 配置保持为上述通过版本。

T1/T2/T3/T4/T5/T6/T7/T8 的修改及 T9 工程复验已交付；T4 真实新手试用仍未验证，T10 按启动条件保留。没有未提交的实现修改，也未引入计划排除的物理/架构扩展。
