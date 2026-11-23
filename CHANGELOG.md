# Version notes / 版本记录

These entries describe local package versions; publishing and Git tags are separate actions.
以下记录对应本地包版本；发布与 Git 标签另行执行。

## Unreleased

- Add cascaded RC (19), multi-source nodal analysis (20), grounded/floating neutral loads (21), and finite T-ladder propagation (22), with independent physical tests and real MATLAB R2025a Simscape comparisons. Add a real reference comparison for existing RC example 02.
- Add the linear transformer T equivalent (23), with three external inductors, explicit source event, independent coupled-state/energy checks and a seven-signal comparison against the original Simscape network.
- Add the three-phase Y–delta–Y chain (24), with floating stars, a local center reference, independent startup/interpolation tests and 19 real Simscape signals. Preserve its initial 1 us startup failure; refine to 0.5 us with unchanged error limits.
- Add source–line–transformer steady-state initialization (25), a closed-loop synchronous Buck (26), and a finite-resistance Bergeron line (27).
- Add grid-connected VSC examples covering the open-loop bridge, current control, PLL, power/PCC voltage and DC-link control (28–32), a meshed five-bus load step (33), and two-terminal VSC-HVDC (34).
- Add storage and PV converters (35–36), islanded frequency droop (37), parallel-line fault isolation (38), and dual grid-forming power sharing (39). The [model and validation guide](docs/models_and_validation.en.md) links to the acceptance scope and evidence for these cases.
- Preserve the existing PWM example's failed waveform comparison alongside passing fundamental/power checks, with unchanged predefined limits and no fitted alignment.
- Separate teaching scripts from reference export/comparison tools; preserve fixed acceptance windows, time-weighted metrics, input snapshots and hashes. Third-party models and raw data remain local.
- Use the configured step on nominal intervals and actual intervals on inserted event steps. Improve consistent initialization and apply one residual correction with the existing LU factors.
- Skip same-node MNA branch contributions, preserve storage continuity at delayed Bergeron wavefronts, and re-anchor saturating magnetizing current to the piecewise curve each step. Normalize low-precision scalars at input and resolve output filenames before checking collisions.
- Document how to replay historical comparisons for 11 and 12 and archive shared comparison sources for 38 and 39. Record verified capabilities, reference availability and recovery instructions, and configure Linux/Windows CI for the development branch.

- 新增19级联RC、20多源节点网络、21接地/浮动中性点负荷、22有限T梯级传播，均有独立物理测试与真实R2025a Simscape对比；既有02补真实参考。
- 新增23线性变压器T等效，使用三个外置电感和显式电源事件，独立验证耦合状态/能量，并与原Simscape网络七量对比。
- 新增24三相Y–Δ–Y链：浮动星点、本例中心参考、独立启动/插值物理测试及19量真实Simscape对比；保留初始1 µs启动超限，按原误差限细化到0.5 µs。
- 新增源–线路–变压器稳态初始化（25）、闭环同步 Buck（26）和有限电阻 Bergeron 线路（27）。
- 新增并网 VSC 开环、电流环、锁相、电压与功率控制、直流电压控制（28–32）、五节点网状网络负荷阶跃（33）和两端 VSC-HVDC（34）。
- 新增储能与光伏并网（35–36）、孤岛频率下垂（37）、并联线路故障隔离（38）和双构网源功率分担（39）。各算例的验收范围和证据见[模型与验证](docs/models_and_validation.md)。
- 既有PWM保留波形未通过、基波/功率特征通过的真实结论，保持预设阈值，不拟合对齐。
- 教学与参考导出/对比分离，固定窗口和阈值、时间加权指标、输入快照及hash可追溯；第三方模型与原始数据保留本地。
- 基本时间网格使用配置步长，插入事件时使用实际区间长度。改进一致初值求解，并用现有 LU 分解做一次残差修正。
- 跳过同节点支路盖章，保持 Bergeron 延时波前处的储能状态连续性，按分段磁化曲线重新取励磁电流基准。统一低精度标量的计算类型，并在运行前检查实际输出路径是否冲突。
- 补充 11、12 号历史对标复跑方法，为 38、39 号保存共享比较源码。记录实测能力、参考目录和恢复指令，为开发分支配置 Linux/Windows CI。

## 0.1.1 — 2026-10-14

- Add locked Ruff, package mypy checks, and pytest-cov development dependencies. Clean up imports and existing type annotations without adding a modeling API.
- Configure Linux/Windows CI with job and simulation-step timeouts, all tests, examples, wheel installation checks, and downloadable JUnit/XML/HTML coverage reports.
- Mark the expensive PWM/HVDC tests as `slow`; ordinary pytest still runs them. Quick feedback uses `-m "not slow"`.
- Include `py.typed` in the package and verify that installed wheel metadata matches `__version__`.
- Document the matching local commands in both READMEs. Coverage reports describe exercised code and do not certify physical accuracy.

- 加入锁定的 Ruff、包源码 mypy 和 pytest-cov 开发依赖；整理导入与已有类型标注，保持建模接口精简。
- 配置 Linux/Windows CI 的任务及仿真步骤超时，执行全量测试、示例与独立 wheel 安装检查，并上传 JUnit/XML/HTML 覆盖率报告。
- 将耗时的 PWM/HVDC 测试标为 `slow`；普通 pytest 仍运行全部测试，快速反馈使用 `-m "not slow"`。
- 在包中携带 `py.typed`，并检查安装 wheel 的版本元数据与 `__version__` 一致。
- 在双语 README 中补齐对应本地命令；覆盖率仅说明代码执行情况，不作为物理精度认证。
