# 恢复与下一步

日期2026-11-06（Asia/Shanghai）。恢复先读tasks/progress/decisions/validation_status，核分支、HEAD、工作区、git log和真实远端。
checkpoint `72e255c41c332d944054330ea672a82fade593cb` 是记录时最近已知提交，须与实际后续历史交叉核对；不覆盖用户工作、不强推、不操作main。

## 当前事实

分支codex/emt-examples-longterm。正式新增19/20/21/22/23/24/25共7项完成，既有02补参考另计，既有12商业波形FAIL保持。
最新完整交付25是9e2513d；原完整源→两π线路→T→固定阻抗负荷/补偿网络已交付D0，24无实际线路的范围不扩大。
25仅224行、28现有元件，公开初值由本例复阻抗递推计算；核心、pyproject.toml和uv.lock相对原main均无差异。

本轮完整1190 passed478.96s（XML478.948，含slow，零失败/错误/跳过），日志.tmp/longterm/d0-final-full-pytest.log和d0-final-full-tests.xml。
锁定27包、全范围Ruff、mypy39及两个新Python入口通过；25专项11passed6.63s，独立Agg5001点。
协议65d89bb在候选/tests不存在时固定14量双窗；守卫勘误436c266只纠正真实SFunction身份，全部物理/求解设置/限值不变。
正式reference run20261106T054135322Z，5023/10023点，28self及56独立精度PASS；baseline从首次守卫失败的完整MAT只读复用，refined真实新跑。
candidate compare20261106T054356596388Z，TR10µs/5001点、28项PASS；maxV.864127V/maxI.00623452A/maxNR1.74756e−6，图已查看。
详见validation/cases/source_line_transformer/README.md及机器报告；独立236项身份/28self/56PWL界审计见.tmp/longterm/d0-native-independent-audit.json。
本轮数值/导出/测试进程均终态；用户原MATLAB PID9980未触碰。
9e2513d已正常push并核真实远端；精确该HEAD的新CI也已终态核验，本轮仅文档收尾，代码与该CI源相同。

## 下一步

1. F1局部blocked：精确9e2513d的run42170878293已真实终态failure，Ubuntu127738145863/Windows127738146164均runner0、steps空、billing lock注释，未执行测试/test_count=null。
   证据experiments/ci_9e2513d.json及7份raw/hash已全核；不再轮询该终态。外部账户真实解锁后，优先对这个覆盖25的run选择Re-run all jobs，再核精确head/attempt的Windows/Ubuntu全步骤。
   不改代码制造空提交、不操作账户账单。90b2fcd成功仅覆盖22；本地/商业结果不代替23/24/25跨OS验证。
2. B2先读experiments/synchronous_buck_state_followup.md。新state-save运行与缓存提取已完成，原四Scope逐字不变；L/C非零初值、互补selector和固定PI坐标已核，原生状态误差/控制离散化仍待验证。
   在26候选不存在时先固定完整参数/初值/方向、控制调用顺序、PWM与负荷事件、原生精化预算、比较窗/限值；再运行真实精化及内部步长分析。无内部限幅PI配外部Limiter，避免增加抗饱和；LP/PI动态误差不能由代数坐标残差替代。
   根附近全点/不同浮点布尔结果保留，不用guard删点。保持现有Switch/控制器，禁止自动二极管/非线性扩展；教学入口只解释电路与运行。
3. A3仍缺同数学Bergeron商业参考。PSCAD5.0及mhi.pscad可发现，但许可/编译/真实运行未证；simpleac为耦合/带事件原网，不能冒充相容参考。
4. B1既有12固定2%波形限仍FAIL（2.66%–2.72%），不放宽标准/拟合时移；C1控制教学链保持后置。
5. D0无需重复成功仿真/全量测试。以后仅真实新代码或失败触发必要验证；运行身份/许可环境迁移须重新审计，不绕过SFunction/MEX/source守卫。

## 本机命令与环境

稳定Python3.14.5位于`.tmp/venv-py3145/Scripts/python.exe`。PowerShell先设置：

```powershell
$env:UV_CACHE_DIR="$PWD/.uv-cache"
$env:UV_PYTHON_INSTALL_DIR="$PWD/.uv-python"
$env:UV_PROJECT_ENVIRONMENT="$PWD/.tmp/venv-py3145"
$env:UV_PYTHON_DOWNLOADS='never'
uv sync --locked --offline --python .uv-python/cpython-3.14.5-windows-x86_64-none/python.exe
$env:PYTHONUTF8='1'
$env:MPLBACKEND='Agg'
$env:MPLCONFIGDIR="$PWD/.tmp/longterm/mpl"
$env:OPENBLAS_NUM_THREADS='1'
```

其他机器正常`uv sync --locked`，不依赖忽略缓存。默认沙箱Temp有权限问题，全量pytest使用新的仓库内`--basetemp=.tmp/longterm/pytest-<唯一ID>`，先验证目标绝对路径位于仓库且不存在，避免pytest清理旧内容；可加`-p no:cacheprovider`避免旧cache权限warning。常规检查Ruff包括pycy_emt_lite/examples/tests/validation，mypy检查包，pytest保留slow。新代码/失败才重跑必要范围，已经通过后不机械重复全量。

如Git因当前身份拒绝ownership，读写命令可加`-c safe.directory=D:/VibeCoding/PyCy_EMT_Lite`，子进程则仅当前进程环境设置：

```powershell
$env:GIT_CONFIG_COUNT='1'
$env:GIT_CONFIG_KEY_0='safe.directory'
$env:GIT_CONFIG_VALUE_0='D:/VibeCoding/PyCy_EMT_Lite'
```

必须正斜杠，不写全局配置。GitHub直连曾超时，已有系统代理可用；忽略helper`.tmp/longterm/git_with_system_proxy.py`只读取系统配置、允许本分支普通push/ls-remote、不打印凭据、不更改remote/持久配置。按执行权限机制审批网络写操作。

各case重现：`uv run python -m validation.cases.<case>.compare`，case名cascaded_rc/rc_charging/nodal_analysis/earthing/transmission_line/transformer_t_equivalent/three_phase_transformer_chain/source_line_transformer；缺真实参考应报错，不生成伪数据。MATLAB从根目录`clear export_reference; addpath('validation/cases/<case>'); export_reference(pwd)`，需合法许可；同名函数切换须clear。原件/原始日志/波形/缓存保留local_reference。

长期目标尚未完成，D0已交付；继续B2参考相容性、A3独立研究及F1外部恢复；不声称无实际执行环境时后台继续。
