# 第二轮实施记录

日期：2026-11-04（Asia/Shanghai）。开始 HEAD `f0bf847655d6b158918b549bf4085d37749bc805`，分支 main，工作区干净，0.1.1。
当前与第一轮数值验收提交 f780100 的差别仅为验收记录；从最初 6b5d206 到当前共 12 次提交，实际源码只改二值保护，另有控制定向测试、双语说明和 Windows CI UTF-8 配置。
审查初始要求优先于历史提交指令：完成验收前不提交、不推送、不合并。之后用户明确授权提交并推送本批，见末节。

## 基线检查

使用既有隔离稳定解释器 `.tmp/venv-py3145/Scripts/python.exe`（CPython 3.14.5，Windows 11 build 26300），NumPy 2.5.2、SciPy 1.18.0、Matplotlib 3.11.1、pytest 9.1.1、Ruff 0.16.10、mypy 2.4.0。Agg、OPENBLAS_NUM_THREADS=1、PYTHONUTF8=1；不改依赖及锁文件。

- `python -m ruff check pycy_emt_lite examples tests`：通过。
- `python -m mypy --cache-dir=.tmp/round2-baseline/mypy`：通过，39 源码文件。
- `python -m pytest -m 'not slow' --basetemp=.tmp/round2-baseline/pytest --junitxml=.tmp/round2-baseline/tests.xml`：1088 passed、9 deselected，45.51 s，与第一轮相同数量。
- 本轮暂不重复全部默认示例/文档/包安装或远端 CI；对新增数值改动在本批结束后安排一次全量含 slow，不能用昨日 CI 代替本轮代码验收。

日志 `.tmp/round2-baseline/`；各代理的独立探针与未通过试探另存 `.tmp/round2-core/`、`.tmp/round2-controls/`、`.tmp/round2-models/`、`.tmp/round2-engineering/`。

## 先证据后修改

R2-001/R2-002 的独立反例、最小方案与兼容风险已先写入 [deep_audit.md](deep_audit.md)，再安排正式失败测试和两处局部整改。后续追加真实执行结果，不预填通过。

## 第一批整改与验收

仅改 `pycy_emt_lite/controls/vsc.py`：配置入口保存已验证 float，最终电压只在真实矢量幅值超过 available 时缩放；合计 6 行 diff。正式测试在既有 `tests/test_controls.py` 增加 62 行、21 参数样本，没有新增依赖或第二套正式模型。

| 执行 | 真实结果 |
|---|---|
| `python -m pytest tests/test_controls.py -k 'every_scale or subvolt or numpy_scalar_configuration' --basetemp=.tmp/round2-controls/pytest-red --junitxml=.tmp/round2-controls/red.xml`（旧源码） | 8 failed、13 passed、157 deselected；R2-001 六个低压向量+一个错误冻结积分，R2-002 一个 np.int8 限流错误。 |
| `python -m pytest tests/test_controls.py --basetemp=.tmp/round2-controls/pytest-green --junitxml=.tmp/round2-controls/green.xml`（修复后） | 178 passed。 |
| 隔离临时副本 21 个新增样本 | 正常 21 passed；恢复旧 1 V 分母 7 failed；丢弃 float 规范化 1 failed。证据 `mutations/`，正式源码未作破坏性变异。 |
| 基线/候选正常 HVDC 合成序列 | 42 样本、882 trace、全部 PI/PLL/滤波/保持状态、756 门极值及 float.hex 完全一致。双方 source SHA256、配置及全部样本在 `.tmp/round2-controls/hvdc_equivalence/`。不以此推定全部网络事件元数据等价。 |
| `python -m ruff check pycy_emt_lite examples tests` | 通过，`.tmp/round2-final/ruff.log`。 |
| `python -m mypy --cache-dir=.tmp/round2-final/mypy` | 通过，39 源码文件，`.tmp/round2-final/mypy.log`。 |
| `python -m pytest -p pytest_cov --basetemp=.tmp/round2-final/pytest --junitxml=.tmp/round2-final/tests.xml --cov --cov-report=term-missing --cov-report=xml:.tmp/round2-final/coverage.xml` | **1118 passed，152.39 s**，含全部 9 slow，无跳过。包含真实 FAST 故障、门极、桥功率/DC 能量、采样和结果格式回归。覆盖率仍显示 93%，不据此证明物理正确性。 |

所有上述 python 指向稳定 `.tmp/venv-py3145/Scripts/python.exe`；环境与基线相同。完整回归只执行这一遍，未为报告文字再跑高成本模式，也未单独再运行默认例 18。
从基线全量 1097 项到本轮 1118 项，增加量恰为 21 个新参数样本；基线快速 1088/9 deselected 与上一轮一致。

## 行为差异、文档及剩余事项

- 预期改变：亚伏 VSC 命令不再被任意 1 V 下限缩小或错误冻结积分；合法 NumPy 窄整数配置不再在限流平方中溢出。配置字段的具体存储类型统一为其注解声明的 Python float。
- 正常 HVDC 合成默认配置的输出和内部状态逐值不变；真实系统的现有物理断言全过。没有输出列/事件格式/元数据/schema/API 改动，也没有放宽原精度、残差或 FAST 断言。
- 已核对双语推导/系统说明，原文声明真实矢量限幅，没有写入错误的 1 V 分母；本次使实现符合该数学约定，不额外扩写双语教程。
- R2-003（非法值被 t=0 事件覆盖）已复现但留待后续独立批次。没有把它说成合法状态方程错误或假称第一轮 T1 已穷尽所有输入路径。
- 本轮不重新进行远端 CI、构建/包安装、全部默认例或 GUI 新手试用；明确保留其历史完成/未验证范围。独立探针和 oracle 假设修正详见 [数值验证](numerical_validation.md)。
- 已对照 diff 复核本批实现，保持版本/锁文件/CI/默认模型参数；阶段验收完成后暂停。截至审查验收结束未运行 Git add/commit/push/merge，变更先留在工作区供审阅；其后授权另记如下。

## 用户后续授权交付（2026-11-04）

用户明确要求“将本次修改进行Git提交并进行推送”。重新核对工作区仅含本批 vsc.py、test_controls.py 与四份复审报告；六文件在补记授权前的 SHA256 与已验收 manifest 全部一致，无验收后源码改动，未重复高成本仿真。
远端 fetch 确认 main 与 origin/main 均为 f0bf847，无分叉；交付仅包含两项 VSC 修复、21 个测试样本及四份报告，R2-003 不在本次代码修改中。
按该授权补记文档并提交，采用非强制推送到 origin/main；不启动下一批整改。既有 CI 会由该推送触发，不能在运行结束前将其记为通过。
