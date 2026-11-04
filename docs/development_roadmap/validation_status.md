# 验证状态

| 对象 | 内部证据 | 外部参考 | 正式状态 |
|---|---|---|---|
| 基线a03a450 | 1118测试含slow、14原有例通过 | 旧文档不等于本次商业对标 | 能力重评完成 |
| 级联RC探针 | 独立expm、KCL、TR/BE收敛通过 | 不冒称商业参考 | 研究探针完成 |
| 新增19级联RC | 分段矩阵指数、KCL/能量、TR/BE细化；独立执行通过 | 官方R2025a，真实10052样本；16个窗×信号均通过 | 已完成290a8ea |
| 既有02 RC | 原解析测试保留 | 官方参数适配、真实5013样本，电压/电流双限值均通过 | 补验证完成68f2f8a；不计新增 |
| 新增20七电阻双源 | Fraction精确解、逐节点KCL、功率；独立执行通过 | 官方v2.2.2/R2025a，101样本14信号全过；禁用未接万用表，主网不变 | 已完成d481c57 |
| 新增21接地/浮动中性点 | 解析星点/KCL/功率、两求解/积分配置、事件/非法输入11项 | 官方真实1001样本；39窗×信号均过；原错标签证据保留 | 已完成5c595e2 |
| 既有12 SPWM | 已有PWM/RL内部测试 | TwoLevel官方真实40001点；特征通过，波形NRMSE 2.66%–2.72%超2% | 首次对标FAIL；未完成，保留原判据 |
| PSCAD cookbook | 工程XML已检查 | v4.6.0，无实跑数值 | inspected |

到20的本地稳定Python3.14.5完整回归：1133 passed，154.47 s；Ruff/mypy通过。原14例及新增19/20均单独执行通过。

到21的最新本地完整回归：**1144 passed，158.14 s**（含slow）；Ruff/mypy通过。21独立Agg运行也通过，当前共有17个教学脚本。

`68f2f8a` 的 [GitHub Actions](https://github.com/yu-yikai/PyCy_EMT_Lite/actions/runs/41799220935) 已实际success，Ubuntu/Windows两job全部成功，含全量/slow/coverage、全部例、构建、安装wheel与生成文件检查。该旧HEAD证据不覆盖20/21。

`5c595e2` 的 [GitHub Actions](https://github.com/yu-yikai/PyCy_EMT_Lite/actions/runs/41801829262) 已实际success，Ubuntu/Windows的全部步骤成功，覆盖新增19/20/21和既有02补验证的代码。可提交的精简证据为 `experiments/ci_5c595e2.json`；原始run/jobs JSON在 `.tmp/longterm/ci/`。job日志下载实际返回403，未从元数据推测远端测试数量；1144是本地实测数量。

各例完整数值报告在 `validation/cases/*/validation_report.json`；商业模型、波形与图/日志在local_reference，默认不提交。报告包含来源/软件、原模型/raw/normalized/候选hash、固定阈值、绝对时间和输入快照。网络已用系统现有代理恢复正常push；后续HEAD需单独记录CI，不能把本次证据扩大到未测试代码。
