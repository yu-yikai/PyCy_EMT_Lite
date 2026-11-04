# 恢复与下一步

日期2026-11-04（Asia/Shanghai）。自动恢复首先读tasks/progress/decisions/validation_status，并执行git status、branch、rev-parse HEAD、log及远端检查，保留用户工作。

## 已完成检查点

工作分支codex/emt-examples-longterm。8d5d15d能力评估，08096f0参考目录，f462cde路线/初始验收，207dea7/dbe9b13比较工具，290a8ea级联RC，68f2f8a既有RC真实验证，4c78c38多源验收，d481c57多源网络。f685ee7为21候选前冻结验收；be90111为比较图物理量缩放修正；5c595e2为21完整验收。当前正式新增3，既有02补参考另计。JSON checkpoint是记录时的已知HEAD，不是自引用当前提交。

首组68f2f8a的Ubuntu/Windows CI成功：run41799220935。5c595e2代码的双平台全部步骤也已成功：run41801829262，证据experiments/ci_5c595e2.json。GitHub直连443曾超时，已用系统既有代理正常push至5c595e2。恢复仍先核对远端。诊断见.tmp/longterm/ci，本机.tmp/longterm/git_with_system_proxy.py仅运行时读取系统配置，不修改remote/持久配置，不打印代理或凭据。

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

## 当前执行与具体命令

1. B1首次真实比较已失败，不能标完成：TwoLevel三相NRMSE为2.66%–2.72%，超过冻结2%；RMS/基波/相位/电阻功率特征通过。读取case失败报告及experiments/spwm_feasibility.md（落盘后）；保持146a279的判据及12原件。原生门极与12在稳态约1%样本不同，器件压降也不同，尚未隔离各项贡献。下一次若研究物理适配，必须先明确新的控制协议，不能拟合时移或为当前失败放宽标准。
2. 21已完整验收提交5c595e2，13信号/3窗通过。重现用uv run python -m validation.cases.earthing.compare；相关测试test_earthing_neutral.py。无需为重新规划重复改动已完成算例。
3. 最新完整回归到21：1144 passed158.14s，Ruff/mypy通过；5c595e2双平台CI成功。无新代码不重复全量；B1新增比较代码后按其影响运行必要检查并记录新HEAD的CI。
4. 比较复现命令：uv run python -m validation.cases.cascaded_rc.compare；同路径换rc_charging/nodal_analysis。没有真实参考时应失败，不能回退合成数据。每次运行保存独立UTC目录，原报告的inputs快照可核对旧字节。
5. MATLAB从仓库根addpath('validation/cases/<case>'); export_reference(pwd)。需要正常许可服务权限。不得上传local_reference原件；参考默认R2025a。
6. B2先调查独立可行参考：半/全桥、明确同步DC/DC，或A4现有线性变压器/线路组合；在真实参考/拓扑/参数确认和候选前验收冻结之前，不实现新教学例。B1的默认参考不通过仅阻止依赖该对齐的控制链，不阻止独立候选研究。Bergeron暂无数学一致商业结果，保持待验证。

长期任务尚未全部完成。后续先复核B1失败证据，再从B2参考调查或其他独立候选继续；不声称无实际执行环境时会后台继续。
