# 恢复与下一步

2026-11-09（Asia/Shanghai）。长期目标已恢复active；先读tasks/progress/decisions/validation_status并核实际Git。当前本地HEAD为`9269350887a867aee2740fed04155ade8f8757be`，26验收已单独提交；正常push及真实ls-remote已核相同；精确新CI42606454705已终态billing lock启动前failure，未执行测试。分支`codex/emt-examples-longterm`；不操作main、不强推、不覆盖未提交文件。暂停记录`.tmp/longterm/paused-20261109T0925.json`属于历史，暂停中断的全量不记通过。

## 当前事实

正式新增19–26共8项完成，02补参考另计；26交付提交9269350，12原MathWorks2%波形FAIL保持。核心包/pyproject.toml/uv.lock相对原main未改，教学入口沿用既有元件/控制器。
B2合格参考和首次候选PASS分开：25/12.5ns真实完整10ms自细化已通过；首次50ns候选商业比较及独立原始数据/输入/周期/两窗复核PASS；13项比较工具测试、锁定27包、Ruff/mypy、恢复后完整1236 passed478.786s含slow零失败/错误/跳过通过。26已完成独立验收并提交9269350，前次暂停中断不作通过；新XML见证据索引。
A3/B1已经实际加载/建模，但最新均在build前停止；无有限R或同数学SPWM波形。两最新run终态均正常异常后quit、自有进程清空，原件/profile/父环境不变。旧资源门槛中止和失败均保留，资源不足不再是当前阻塞。完整run与hash只在[本轮证据索引](experiments/native_reference_attempts_20261109.md)集中列出。

## 执行顺序

1. **保存本批研究状态。** 26商业比较/独立原始数据复核、1236全量、图/报告/教学已验收，独立交付提交`9269350887a867aee2740fed04155ade8f8757be`；正式新增8。9269350已正常推送且真实远端一致，精确新CI已一次有界观察终态；单独提交/正常推送本轮路线图研究状态，不重复观察同CI。不重复合格参考、独立执行或完整回归，除非有新改动/失败。
   原100/50ns参考FAIL、原物理/窗/500周期/全部限值保持。26只覆盖已冻结同步控制/事件与二极管不活动域，派生源流和条件精度边界不扩大。核心/pyproject.toml/uv.lock相对原main仍无改动。
2. **A3先核定义前后差异。** [有限R设计](experiments/bergeron_reference_design.md)的v4库存API问题已窄修为仅本轮精确Wire/已知iid省略parameters，完整集合强核。v5实际run`20261109T105927241384Z`已过全部Wire库存，在SrvcCbl编辑前/后RowDefn一致性守卫停止；未保存修改工程/build/sim。已核唯一根CRC 36752239→0，其余定义相同；官方语义未证明。最小分阶段诊断`20261109T111545271892Z`已定位snapshot35紧接删除其余76个Main顶层对象后首次变CRC，其前0–34快照无差异；未编辑线路位置/Length、无save/build/run，按设计停止。单对象原因与一般CRC语义仍未证。下一步仅拟v6：在这一个批量删除边界强核唯一CRC转换/其余完整定义相同，再以删除后完整CRC0 XML严格作基线；此后任何变化含save新CRC仍停止。v6未写代码，须另存独审，不能泛化放松守卫；实际/研究/计划pins见证据索引。
   `finite_r_native_probe_owned_guard_v5.py` SHA6beca649…/`builder_checked_v5.py` SHAce894fec…固定最新失败身份；v4及旧失败保留。实际6ms/1us回读仅为配置，`.tlo`、Vs/Mag时序、方向、零历史/波形仍缺。保持3GiB启动、2GiB动态余量、RPC20s/build180s/run120s/监控总420s。参数/波形核定后才冻正式协议和候选，不扩线路核心类或重跑已成功vdiv教程/整包settings。
3. **B1先修实际端口布线。** [短探针设计](experiments/spwm_matched_reference_design.md)为0–1ms/5µs、native TIME直接驱动、网格仅观察。`D/n/20261109T091917405572Z`的170字符路径已加载，创建组件后实际端口坐标守卫拒绝；未build/run。补充端口抓取`D/n/20261109T111717200520Z`已保存31组件/53项检查、23坐标不符，按设计在所有wire/save/build/run前停止。source NA/NB实际(6,4)/(10,4)、ground仍(11,4)，旧重合假设失效；R/L/varrlc/电流表跨度2格。逐个按实际端口另存重连稿，核图/正交性/源probe与ground并独立审查，不统一缩放或略过守卫。D的完整路径见证据索引。
   六双向外控R/浮星RL、69/31/46规格和原控制数学不变；实测时基、全部g/有效R、源/单位/TR历史后才另冻完整0.2s及控制网格细化协议。默认12、原MathWorksFAIL和原全部限值保持，C1后置，不引入自动二极管框架。
4. **F1仍是外部账单锁。** 精确验收9269350的[CI42606454705](https://github.com/yu-yikai/PyCy_EMT_Lite/actions/runs/42606454705)终态failure，Ubuntu129123587852/Windows129123588150均runner0/steps空，注释确认billing lock、未执行测试，test_count=null。证据[ci_9269350.json](experiments/ci_9269350.json)，7份raw/hash已核。不轮询同终态；账户恢复后补验精确HEAD双OS全部步骤，旧90b2fcd仅覆盖22。D0不重复已成功参考。

## 本机命令

稳定Python3.14.5：.tmp/venv-py3145/Scripts/python.exe。下列离线缓存仅适用于本机，其他机器正常uv sync --locked。

~~~powershell
$env:UV_CACHE_DIR="$PWD/.uv-cache"
$env:UV_PYTHON_INSTALL_DIR="$PWD/.uv-python"
$env:UV_PROJECT_ENVIRONMENT="$PWD/.tmp/venv-py3145"
$env:UV_PYTHON_DOWNLOADS='never'
uv sync --locked --offline --python .uv-python/cpython-3.14.5-windows-x86_64-none/python.exe
$env:PYTHONUTF8='1'
$env:MPLBACKEND='Agg'
$env:MPLCONFIGDIR="$PWD/.tmp/longterm/mpl"
$env:OPENBLAS_NUM_THREADS='1'
uv run ruff check pycy_emt_lite examples tests validation
uv run mypy
uv run pytest
~~~

pytest指定新仓库内--basetemp=.tmp/longterm/pytest-<唯一ID>，先核路径位于仓库且不存在，可加-p no:cacheprovider。
保留slow；新代码/失败才触发对应范围与必要完整回归。日志/XML放.tmp/longterm/，不覆盖旧失败。
Git ownership用单命令-c safe.directory=D:/VibeCoding/PyCy_EMT_Lite；子进程仅当前进程GIT_CONFIG_COUNT/KEY_0/VALUE_0，不改全局配置。
网络按实际结果判断：早先direct成功、后续direct低速/443失败；最终已有系统代理的子进程helper在提升权限后正常push并核远端5f1a96b。可用.tmp/longterm/git_with_system_proxy.py传git参数，读取现有系统代理并脱敏，不持久改网络设置。
正式case比较入口：uv run python -m validation.cases.<case>.compare，case包括cascaded_rc/rc_charging/nodal_analysis/earthing/transmission_line/transformer_t_equivalent/three_phase_transformer_chain/source_line_transformer。
Buck尚未正式交付，不套用其他case的单参数MATLAB命令。所有第三方原件、波形/图片/缓存保留忽略的local_reference。
长期目标仍active；结束当前执行前同步证据/任务/提交/下一步，不宣称离线后台继续。

## 历史证据边界

08:22UTC约2.282GiB<3GiB时只准备/未启动；08:36:59UTC实测约10.28GiB后才顺序运行。首个B2更细启动资源保护中止、旧参考自身FAIL，以及A3/B1的全部失败目录保持，不恢复旧worker、不覆盖旧输出。
B2的callback/load_system研究没有证明与open_system语义等价或减少内存；当前不需要通过未测替换重跑合格参考。所有第三方原件/波形/脚本仅保留忽略目录。
