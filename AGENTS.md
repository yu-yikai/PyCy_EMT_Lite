# 长期EMT开发任务恢复

继续本长期任务时，先读取 `docs/development_roadmap/tasks.json`、`progress.md`、`next_actions.md`、`decisions.md`、`validation_status.md`，并核对分支、HEAD、工作区和远端。不要让用户重新解释规划；状态文件的checkpoint是最近记录的提交，须与实际Git历史交叉核对。

- 在独立分支工作；当前为 `codex/emt-examples-longterm`。不直接修改/推送main，不强推，不丢弃用户未提交文件。用户已授权该开发分支常规提交与里程碑推送。
- 优先复用 `CaseDefinition → Circuit → Simulator → SimulationResult` 及当前元件/控制器；正确性、真实验证、教学可理解性优先。不为扩充数量复制既有SPWM/RLC题目。
- 新算例在候选实现前固定来源、拓扑/参数/初值/方向、比较窗与阈值。只有内部验证、独立运行、真实Simulink/PSCAD对比、图/报告、自动测试、教学说明及Git提交均完成，才能记为completed。
- 内部解析解、矩阵指数和Python ODE不能冒充商业平台输出。缺参考时保留待验证/受阻状态，继续其他独立任务。官方示例也可能有错误标签或未接工具依赖，须以拓扑/方程核验。
- 参考模型、原始波形及本地缓存保留在忽略的 `local_reference/`；不上传许可不明的第三方原件。每次比较保留独立运行目录、输入快照、版本与hash。
- 不实施通用非线性/自动二极管框架、复杂机器/磁滞、MMC、大规模稀疏或加速后端。稀疏求解属于远期独立研究。
- 常规检查：`uv sync --locked`；`uv run ruff check pycy_emt_lite examples tests validation`；`uv run mypy`；`uv run pytest`（含slow）。非交互算例用 `MPLBACKEND=Agg`。本机稳定Python3.14.5/离线缓存命令与现有证据位置见next_actions。
- 每个完整验收任务单独提交，里程碑正常推送；结束当前执行前同步任务/证据/提交/下一步，不声称无环境时会后台继续。
