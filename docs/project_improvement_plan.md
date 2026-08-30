# PyCy_EMT_Lite 精简改进计划

## 1. 改进目标与原则

项目改进聚焦四项工作：

1. 收缩公开 API、模型、示例和文档。
2. 修正时间、状态、事件、错误和指标等可信性问题。
3. 保留少量有物理验证的 EMT 与新型电力系统课程。
4. 建立一个最低必要 CI 和安装包检查。

项目只保留一条公开流程：
`CaseDefinition -> Circuit -> Simulator -> SimulationResult`。
不为兼容旧内容保留第二套流程。

### 新增内容的硬门槛

创建任何文件、公开类、脚本、文档或依赖前，必须同时回答：

- 为什么不能修改或合并现有内容？
- 哪个已经确认的教学目标或缺陷会直接使用它？
- 怎样用现有测试或一个最小测试验证它？
- 它替代或删掉了什么旧内容？

任一项没有明确答案，就不创建。无当前用途的实现直接删除，由 Git 保存历史，不设
“实验代码仓库”。

## 2. 项目边界与最小结构

### 教学边界

项目应当展示小规模 EMT 电路的 MNA、离散化、逐步求解、事件和基础控制，并让学习者
用解析解、KCL/KVL、能量、收敛性或独立参考检查结果。

项目不宣称具备厂站级模型精度、大电网仿真、实时/HIL、完整器件非线性、工程级
MMC/HVDC、并行计算或生产研究能力。模型层级和限制必须直接写明，不能把平均值或代理
模型称为详细 EMT 模型。

### 最小目标结构

```text
README.md                        # 简短英文入口
README.zh-CN.md                  # 完整中文入口、Quick Start 和学习顺序
LICENSE
pyproject.toml
uv.lock
pycy_emt_lite/                   # 单一对象式 API 和课程实际使用的实现
examples/                        # 约 6–8 个单目标、可验证示例
tests/                           # 数值、物理、示例、文档和安装边界测试
docs/
  numerical_conventions.md       # 全局数值、时间、单位和方向约定
  models_and_validation.md       # 模型层级、限制、证据和未验证项
.github/workflows/ci.yml         # 一个 workflow、一个 job
```

不预建空目录。README 是唯一导航入口；源码细节使用 docstring；文档链接到被测试的
示例，不复制长代码。

## 3. 四阶段执行计划

执行顺序为 A -> B -> C -> D。最低 CI 在 Phase A 建立，用于保护后续修复。

## Phase A：先收缩，再设基线

| 任务 | 最小动作 | 验收 |
|---|---|---|
| A-01 公开范围 | 按“公开物理模型族、内部辅助、删除”检查顶层和子包导出 | 每个公开物理模型族有课程用途和物理测试；辅助 API 有使用者、测试和简短 docstring；其余删除 |
| A-02 示例范围 | 给现有 16 个示例各写一句唯一目标和一种验证方式，结果直接进入中文 README 学习顺序 | 重复、误导或无法验证的示例有明确合并/删除决定；不另写盘点报告 |
| A-03 文档范围 | 将每份现有文档映射到“合并进两个目标文档”或“删除” | 没有归档副本、平行版本或独立审计报告 |
| A-04 项目边界 | 中英文 README 标明教学用途、模型层级和不适用范围 | 不再把 16 个示例和所有模型描述为同等可信 |
| A-05 许可证 | 增加一个与公开方式相符的 `LICENSE`，同步 `pyproject.toml` | 许可明确；不写许可证 ADR 或 NOTICE，除非真正引入第三方材料 |
| A-06 最小 CI | 立即建立 Phase D 所述单 workflow/job | 当前测试、示例和 wheel smoke 有远端基线；许可证决定不阻塞 CI |

### Phase A 退出门

- 顶层没有无课程用途的物理模型；未使用实现已删除而非长期标“实验性”。
- 每个保留示例有唯一目标；没有仅展示图片而没有可复核物理量的核心示例。
- 后续冻结新模型、新示例和新文档，先完成现有正确性修复。
- A-01、A-02、A-03 的结论直接进入代码、README 或两个目标文档，不产生管理文件。

## Phase B：修正可信内核

| 任务 | 最小修改 | 验收 |
|---|---|---|
| B-01 时间与初始化 | 在现有仿真循环和时间测试中固定 `t=0`、首步区间、事件前后和末步语义 | `t=0` 时电容电压、电感电流等存储状态保持声明初值；节点电压和支路电流由一致网络方程求解；短末步有测试 |
| B-02 实例所有权 | `Simulator`、`Circuit` 及有状态 `Component` 实例均只允许参与一次运行 | 任何形式的实例复用都明确报错；不实现 reset、clone 或 session 框架 |
| B-03 续算接口 | 拒绝或移除未正确实现的非零 `start_time` | API 和文档不再暗示 checkpoint/续算；不实现序列化和 schema |
| B-04 事件顺序 | 同一时刻事件按声明顺序处理；固定故障和开关边界 | 相同输入产生相同事件日志和波形；不设计优先级框架 |
| B-05 输入与错误 | 首步前拒绝 NaN/Inf、非法节点、重复名称和错误事件目标；保留求解根因 | 非有限输入、奇异矩阵和错误目标产生不同错误，并包含时间和字段上下文 |
| B-06 结果路径 | 删除 `result_transform`，示例需要时在运行后显式整理结果 | 原始 `SimulationResult` 不被回调修改；不建设防篡改框架 |
| B-07 时间轴与指标 | RMS、均值和平均功率按真实时间加权；`time_step` 明确为标称步长 | 真实时间以结果时间列为准；插入冗余点不改变指标；统计不跨拓扑跳变插值，事件窗排除边界 |
| B-08 基础物理门 | 在现有测试中增加解析、KCL/KVL、求解残差、无源能量和步长减半检查 | R、RC、RL、RLC、事件、三相基础和变压器基础均有物理断言；无源 RLC 总能量不无故增长 |
| B-09 绘图与导出 | 所有示例只要求 headless；另用一个现有或最小测试覆盖绘图/保存 | 不为每个示例重复测试“显示/保存/不保存”组合 |

### Phase B 退出门

- 每个缺陷先由失败测试复现，再修改实现。
- 时间、事件和统计窗口可由测试判断，不依赖人工看宽图。
- 步长减半后结果朝解析解或独立参考收敛。
- 求解错误不被统一误报为拓扑错误。
- 没有新增会话、checkpoint、回调安全、实验 manifest 或通用验证抽象。

## Phase C：保留最小可信模型和课程

### 模型处置

| 模型组 | 决定 | 最低验证 |
|---|---|---|
| R、L、C、独立源 | 保留为可信核心 | 解析解、KCL/KVL、残差和步长收敛 |
| IdealSwitch、故障、断路器 | 保留理想开关和事件语义 | 开合前后方程；同刻事件确定；门极边沿与 `dt` 对齐，非对齐拒绝；切换后使用现有后向欧拉策略 |
| 三相源/负载/故障 | 保留最小集合 | 平衡稳态、三相短路和一个不对称故障 |
| π 型线路、单相变压器 | 保留 | 稳态比值、守恒和暂态趋势 |
| Bergeron | 仅在保留传播课程时留下 | `travel_time`、停止时刻和全部事件时刻均与固定 `dt` 对齐，禁止事件插入短步；验证预响应、到达和反射 |
| PI、坐标变换、PLL、PWM | 只保留最终示例实际调用的模块 | 独立阶跃/变换测试；不增加 chatter 或通用插值框架 |
| 新型电力系统综合案例 | 最多保留一个能进入统一 `Circuit/Simulator` 流程的 GFL 或 GFM 平均值案例 | 功率方向、限幅、DC/储能能量残差、扰动响应和一份独立参考 |
| Diode、反并联 IGBT | 当前删除；只有明确的自然换流课程和独立参考出现后再评估 | 不为保留名称而建设通用 Newton/活动集框架 |
| Park dq0 发电机 | 不能用小修改证明 dq 端口方程时，改用简单同步机代理或删除 | 参数必须进入对应方程，名称不得夸大精度 |
| PV 详细曲线、VSC-HVDC、MMC、多变流器 | 当前删除；Git 保留历史 | 不同时建设整套新能源模型库 |
| 拓扑启发式 | 删除当前可能误报的阻断式诊断 | 奇异性由求解器报告时间、矩阵秩/残差等已有上下文，不另建拓扑边协议 |

现有示例的第一批决定：

1. 示例 07 改用 pre/fault/post 固定窗口指标，不再用有符号全局最小值下结论。
2. 示例 13–15 的手写步进不能形成第二套仿真框架。只选择一个能以小修改接入统一流程
   的 IBR 案例；若都不能，当前版本暂不保留综合案例并在 README 说明缺口。
3. 示例 16 在 DC-link、线路损耗和功率平衡可信前退出学习路径。
4. 示例 10 若只是简化代理，不再称为完整 Park dq0 EMT 发电机。
5. 示例 13–16 不再把控制级前向欧拉统一标成梯形 EMT。
6. 所有保留示例只输出带单位的关键观察值；判断阈值只维护在 pytest，除非阈值本身是
   该课的教学目标。

最终保留约 6–8 个单目标示例，覆盖：

- 对象式流程与电阻电路；
- 一阶/二阶动态元件和 MNA；
- 三相与故障事件；
- 线路传播或变压器；
- 课程实际需要的开关、PWM、坐标变换和 PLL；
- 最多一个经过独立对比的新型电力系统综合案例。

### 最小验证形式

- 解析解和物理不变量优先，直接写入现有 pytest。
- 只在没有解析解时加入 1–2 份独立参考；若保留 IBR 综合案例，其中一份必须覆盖它。
- `tests/reference_data/` 只在第一份真实数据加入时创建。
- 小型 Git 跟踪数据的来源、软件版本、参数、单位、信号映射和对应测试统一记录在
  `docs/models_and_validation.md`；不逐目录创建 README 或哈希清单。
- 不创建 `validation/cases/references/manifests/reports`、通用 manifest 或报告生成器。

### Phase C 退出门

- 每个公开物理模型族被至少一个保留示例使用，并有物理测试；辅助 API 有测试和 docstring。
- 没有未进入方程的公开参数、错误精度名称或顶层“实验模型”。
- 不能通过验证门的高级实现、示例和专属文档已删除，不阻塞核心发布。

## Phase D：合并文档并收紧最低工程门

### 最小文档集合

| 文件 | 唯一职责 |
|---|---|
| `README.zh-CN.md` | 唯一完整入口：边界、安装、Quick Start、学习顺序和文档链接 |
| `README.md` | 简短英文摘要，只同步边界、安装、Quick Start 和支持版本 |
| `docs/numerical_conventions.md` | 只写全局 MNA、初值、时间/事件、单位、方向和 2–3 个基础 stamp 推导 |
| `docs/models_and_validation.md` | 一个紧凑模型表、必要方程、限制、当前已有证据和未验证项 |

合并规则：

- `user_guide.md` 和 `new_simulation_workflow.md` 的必要操作并入中文 README。
- `mna.md`、`basic_components.md`、`stamp_principles.md` 和程序指南的可信共同约定并入
  `numerical_conventions.md`；不得把旧长文原样搬迁。
- 三相、控制、电力电子、线路/变压器和新能源理论只保留最终模型需要的内容，并入
  `models_and_validation.md`。
- `visualization_reporting.md` 等重复、过时或可由 docstring 表达的内容直接删除。
- 不创建 `docs/index.md`、归档目录、模型卡目录或一模型一报告。

### 最小文档维护门

| 触发事件 | 同一变更需要检查 |
|---|---|
| 公开 API、结果字段或命令改变 | 中文 README、对应示例；只有四个共享字段受影响时才同步英文 README |
| 方程、参数、单位、方向、时间或事件语义改变 | 两个目标文档中最近的一处和对应测试 |
| 模型被加入、删除或降级 | 中文学习顺序、`models_and_validation.md` |
| Python 或依赖范围改变 | `pyproject.toml`、`uv.lock`、README 和 CI |

当前仓库已经出现旧 API 和路径漂移，因此在合适的现有测试中加入少量断言；确实无处
可放时才新建约 20–30 行的 `tests/test_docs.py`。它只检查保留 Markdown 的本地链接和
已知旧标识（如 `RuntimeResult`、`SimulationSession`、旧包导入），不实现 Markdown
解析器、文档构建器或网站。

过时内容直接修正或删除，由 Git 保存历史。不使用逐页元数据、owner、SLA、双语
parity、文档清单 YAML、版本选择器、追踪矩阵或质量仪表盘。

### 一个最低 CI

`.github/workflows/ci.yml` 只含一个 Ubuntu/Python 3.14 job，并在 Phase A 建立：

1. `uv sync --locked`；
2. `uv run pytest`；
3. 原样运行 README 的 Quick Start 命令；
4. 以 `MPLBACKEND=Agg` 直接循环运行全部保留示例；
5. `uv build --out-dir .tmp/dist`；
6. 在系统临时目录安装该 wheel，以临时目录为工作目录，断言
   `importlib.metadata.version("pycy-emt-lite") == pycy_emt_lite.__version__`；
7. 检查 `git status --porcelain` 为空，防止示例污染仓库。

不创建 `scripts/dev.py`。只有仓库启用分支保护时，才将这个 job 设为 required。

### 发布实际发生时才补充

明确决定发布 PyPI 后，才补齐包 URL、分类器和发布说明；若宣称 Python 3.12–3.14，
才加 Linux 版本矩阵；若宣称 Windows 支持，才加一个 Windows smoke。构建一次
wheel+sdist，安装测试其中的 wheel，再发布同一批未重建产物；届时才使用 PyPI
trusted publishing/OIDC。

当前不创建 CHANGELOG、CITATION、CODEOWNERS、Issue/PR 模板、Dependabot、SBOM、
attestation、Nightly、三平台矩阵、mypy/`py.typed` 或覆盖率门。

### Phase D 退出门

- 冷环境按 README 安装并运行第一个示例。
- 全部保留示例 headless 通过且不产生未跟踪文件。
- wheel 从仓库外导入成功，安装元数据版本与 `__version__` 一致。
- 产品文档仅剩上述最小集合，内部链接有效，旧 API 名称清除。

## 4. 范围外能力与重新评估条件

| 当前不建设 | 只有出现以下证据才重新评估 |
|---|---|
| YAML、CaseSpec、第二套 API、教学 CLI/Catalog/JSON schema | Lite 不再能用单一对象流程满足已确认课程；优先另立项目而非污染 Lite |
| 通用非线性框架、完整器件库 | 已确认自然换流课程，并有独立参考和维护者 |
| 完整 Park、PV 详细曲线、HVDC/MMC、多变流器、宽频线路 | 一个新模型能替代现有课程，且已有参数、参考和物理测试 |
| checkpoint、流式结果、稀疏 stamp、LU 缓存 | 默认课程经 profiler 证明现有实现造成真实时间或内存问题 |
| 文档站、版本选择器、全文双语 | 学习者反复无法导航，且必要产品文档已超过约 8–10 份 |
| 多 Python/操作系统矩阵 | 准备声明相应支持范围，或用户已复现平台差异 |
| CONTRIBUTING、社区模板和行为准则 | 明确开始接受外部贡献 |
| 发布、安全和供应链工具 | 明确发布 PyPI；或已知安全公告影响锁定依赖，此时审查 `uv.lock` 并运行完整 CI |

不使用固定周/月/季度维护任务。模型、API、依赖、发布或用户问题发生实际变化时，才触发
对应检查。

## 5. 统一完成定义

一个任务只有同时满足以下条件才能关闭：

1. 缺陷由测试复现；删除/文档任务有可检查的前后清单。
2. 修改只覆盖当前问题，没有顺手增加框架或无关重构。
3. 数值任务明确时间窗、单位、方向、步长和容差。
4. 物理模型至少检查解析值、不变量或独立参考。
5. 公开行为改变时，只更新最近的一份必要文档。
6. 最低 CI 和全部保留示例通过。
7. 没有新增未使用文件、公开符号或依赖。

失败时保留真实错误和输出，不通过裁剪波形、放宽坐标轴或只看最终值掩盖问题。

## 6. 仍需查阅的最少外部依据

- [NERC：IBR EMT 模型要求与验证实践](https://www.nerc.com/comm/RSTC_Reliability_Guidelines/Reliability_Guideline-EMT_Modeling_and_Simulations.pdf)：借鉴模型边界、验证和限制说明；本教学项目不宣称达到厂站模型要求。
- [PSCAD：Interpolation and Switching](https://www.pscad.com/webhelp-v5-ol/EMTDC/Advanced_Features/interpolation_and_switching.htm)：核对开关事件和时间步语义。
- [uv：GitHub Actions 集成](https://docs.astral.sh/uv/guides/integration/github/)：建立锁定依赖的最小 CI。
- [pytest：Good Integration Practices](https://docs.pytest.org/en/stable/explanation/goodpractices.html)：核对测试与安装包导入边界。

外部资料只用于定义验证问题，不能替代项目自己的解析、守恒、收敛和参考对比。
