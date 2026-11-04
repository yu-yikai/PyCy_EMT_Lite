# Version notes / 版本记录

These entries describe local package versions; publishing and Git tags are separate actions.
以下记录对应本地包版本；发布与 Git 标签另行执行。

## Unreleased — 2026-11-04

- Add cascaded RC (19), multi-source nodal analysis (20), and grounded/floating neutral loads (21), with independent physical tests and real MATLAB R2025a Simscape comparisons. Add a real reference comparison for existing RC example 02.
- Separate teaching scripts from reference export/comparison tools; preserve fixed acceptance windows, time-weighted metrics, input snapshots and hashes. Third-party models and raw data remain local.
- Record verified capabilities, reference availability, task dependencies and recovery instructions; enable this development branch's Linux/Windows CI without changing package APIs or solver equations.

- 新增19级联RC、20多源节点网络、21接地/浮动中性点负荷，均有独立物理测试与真实R2025a Simscape对比；既有02补真实参考。
- 教学与参考导出/对比分离，固定窗口和阈值、时间加权指标、输入快照及hash可追溯；第三方模型与原始数据保留本地。
- 建立实测能力/参考目录、依赖任务与恢复指令，开放本分支Linux/Windows CI，保持包API与核心方程。

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
