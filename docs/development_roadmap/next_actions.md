# 恢复与下一步

日期2026-11-04（Asia/Shanghai）。自动恢复首先读tasks/progress/decisions/validation_status，并执行git status、branch、rev-parse HEAD、log及远端检查，保留用户工作。

## 已完成检查点

工作分支codex/emt-examples-longterm。8d5d15d能力评估，08096f0参考目录，f462cde路线/初始验收，207dea7/dbe9b13比较工具，290a8ea级联RC，68f2f8a既有RC真实验证，4c78c38多源验收，d481c57多源网络。f685ee7为21候选前冻结验收；be90111为比较图物理量缩放修正；5c595e2为21完整验收。当前正式新增4（19/20/21/22），既有02补参考另计。JSON checkpoint是记录时的已知HEAD，不是自引用当前提交。

8a65b6e为B1工具/真实失败报告；3761a21为A7候选前验收冻结；4217cdb为原生枚举与资源状态修订；c0f9fa2为有界CI超时调整；80ba91c为A7完整验收，均已正常推送。读取后续git log核对新增提交，不以此历史检查点替代真实HEAD。

首组68f2f8a的Ubuntu/Windows CI成功：run41799220935。5c595e2和8a65b6e代码的双平台全部步骤也已成功：run41801829262和41805586718，证据见experiments/ci_5c595e2.json及ci_8a65b6e.json。后者不覆盖之后22代码。80ba91c已到origin，但09:43UTC仍未发现其run；同次push有旧文档skip指令，不能据旧CI宣布完成。正常提交必要阶段文档后，以新HEAD独立确认同一代码的CI。GitHub直连443曾超时，系统既有代理可正常push；首次500已核对远端后重试成功。诊断见.tmp/longterm/ci，本机.tmp/longterm/git_with_system_proxy.py仅运行时读取系统配置，不修改remote/持久配置，不打印代理或凭据。

## 本机稳定环境

PowerShell设置UV_CACHE_DIR=$PWD/.uv-cache、UV_PYTHON_INSTALL_DIR=$PWD/.uv-python、UV_PROJECT_ENVIRONMENT=$PWD/.tmp/venv-py3145、UV_PYTHON_DOWNLOADS=never，执行：

```powershell
uv sync --locked --offline --python .uv-python/cpython-3.14.5-windows-x86_64-none/python.exe
$env:PYTHONUTF8 = '1'
$env:MPLBACKEND = 'Agg'
$env:MPLCONFIGDIR = "$PWD/.tmp/longterm/mpl"
$env:OPENBLAS_NUM_THREADS = '1'
```

其他机器正常uv sync --locked，不依赖本机忽略目录。上述UV_PROJECT_ENVIRONMENT有效时uv run使用稳定环境；也可直接用.tmp/venv-py3145/Scripts/python.exe。

本机沙箱默认Temp曾使pytest无法建立编号目录（46项fixture setup错误，其余1108通过，并非数值断言失败）。本地回归显式指定仓库内新的 `--basetemp=.tmp/longterm/pytest-<run-id>`；先确认目标绝对路径在仓库内且该目录不存在，避免pytest清理已有内容。原失败日志保留 `.tmp/longterm/b1-pytest.log`；更正后全量1154 passed/144.24s，日志b1-retry-pytest.log和b1-retry-tests.xml。

## 当前执行与具体命令

1. 当前F1：最新代码80ba91c已完成A7全部验收，但其push未观察到CI。阶段文档不带skip指令正常push后，读取最新remote HEAD的GitHub API run/jobs并等待Ubuntu/Windows全部结束；目标SHA必须对应本次HEAD。没有新代码不重复1162本地全量，不将8a结果套到22。
2. 21已完整验收提交5c595e2，13信号/3窗通过。重现用uv run python -m validation.cases.earthing.compare；相关测试test_earthing_neutral.py。无需为重新规划重复改动已完成算例。
3. 最新完整回归到22：1162 passed412.17s，Ruff/mypy通过，日志a7-pytest.log和a7-tests.xml。22专项8 passed339.16s，独立Agg通过；六量真实参考全窗通过（max8.0124mV/.160248mA）。重现uv run python -m validation.cases.transmission_line.compare；参考/独立推导、原错标签与全部hash均已保存。
4. 比较复现命令：uv run python -m validation.cases.cascaded_rc.compare；同路径换rc_charging/nodal_analysis。没有真实参考时应失败，不能回退合成数据。每次运行保存独立UTC目录，原报告的inputs快照可核对旧字节。
5. MATLAB从仓库根clear export_reference；addpath('validation/cases/<case>')；export_reference(pwd)。需要正常许可服务权限。不得上传local_reference原件；参考默认R2025a。A7采用经hash核对的TransmissionLine.slx及本机配套SSC/library，路径/未保存状态不符时导出应拒绝。
6. A4正只读调查simscape/ComparisonOfMutualInductorAndIdealTransformerExample，已取得CompareCircuits及五个支持SLX。支持件是四电气端口Subsystem Reference，不能独立当sim顶层；PostLoad默认tStep=100s大于stop8s，官方MLX另用2s，不能把默认全零结果当有效变压器暂态参考。先读experiments/transformer_reference_probe.md（写好后）及原始MLX/端子，核定实际活动参数/初值/激励与能否用现有元件构成同T等效；未冻结新验收前不写候选。B2同步DC/DC调查可独立进行。Bergeron暂无数学一致商业结果，保持待验证。
7. B1保留总体FAIL：ThreePhase TwoLevel波形NRMSE2.66%–2.72%超过冻结2%，features通过。8a65b6e保存failed validation_report和spwm_feasibility.md；保持146a279判据与12原件。后续如研究适配，先明确新的物理控制协议，隔离保持/门极、器件压降及积分差别；不能拟合时移或为当前失败放宽标准。

长期任务尚未全部完成。后续先完成F1当前精确HEAD双平台验收，再从A4/B2参考先行继续；不声称无实际执行环境时会后台继续。
