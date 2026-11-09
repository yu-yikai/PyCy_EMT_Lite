# 恢复与下一步

2026-11-09（Asia/Shanghai）。先读tasks/progress/decisions/validation_status，核实际分支、HEAD、工作区和远端。
记录时checkpoint为03a913ed52bacd6a07083fe4dbc7ae45c7b78fee；后续提交须与Git历史核对。
分支codex/emt-examples-longterm；不操作main、不强推、不覆盖未提交文件。

## 当前事实

正式新增19–25共7项完成，02补参考另计；12商业波形仍FAIL。25完整供电网络交付为9e2513d。
恢复时本地dda8deb、远端4385e2e；本批候选已提交41a6685并正常push，实核远端一致。26仍未商业验收，不计正式完成。
核心包、pyproject.toml和uv.lock相对原main没有改动；教学入口复用既有元件/控制器，不扩框架。
本次最终完整回归1223 passed 475.864s（XML，含slow，零失败/错误/跳过）；锁定27包/Ruff/mypy39及3新入口通过。
26独立Agg200001点、12内部物理及21参考数学/原始点/配对测试通过。商业验收仍未完成，当前候选提交/推送身份须核实际Git。

## 执行顺序

1. **B2参考先解决精度失败。** 原100/50ns两次真实10ms成功，103550/204619点，原生MAT/状态/Scope及各30项库存本次重新全核。
   UC/iL两完整窗自细化通过；500周期duty最大差0.00275472>0.0015、重建源流0.0240559A>0.01A，参考自身FAIL。
   完整[失败报告](../../validation/cases/synchronous_buck/initial_reference_failure.json)保留，候选尚未商业比较。
   独立积分/根贡献分解见local_reference/b2_protocol_research/refinement_diagnosis/；主因是原生控制/根漂移，不能删周期或改阈值。
   [solver补充](../../validation/cases/synchronous_buck/reference_solver_addendum.md)先行固定25/12.5ns及同比收紧Rel/Abs；首个新启动已因系统提交内存不足被保护中止，无sim输出。先读系统资源；先前原生峰值约3.6GiB，须给启动和2GiB余量留空间，再顺序跑两完整10ms。禁止降低保护或反复重启。
   运行用新唯一目录及自有进程监控（6GiB私有/2GiB可用提交量/600s/重复最小步长告警），不触用户MATLAB。
   exporter签名为export_reference(repositoryRoot,runDirectory,stage,protocolFile,protocolHash)；本轮protocolFile为补充md，hash须运行前固定。
   原模型、三份原验收协议、候选50ns、两完整窗、全部500周期及限值均不变。
2. **B2内部与正式交付。** 合格参考就绪后才安装canonical引用并作候选商业比较/图报告。
   教学脚本不读商业数据；LPBE→无内部限幅PI→外Limiter、解后更新及显式负荷事件不变。
   UC/iL在负荷事件连续，可用严格限定的连续状态视图比较；不能任意撤销公共event guard。
   原生稀疏Isrc跳变不能PWL积分成斜坡；派生源流须明确标识，不称直接门极/源流日志。
   条件根预算还依赖原生UC/滤波状态导数相容及无隐藏根，duty epsilon或AbsTol不是绝对误差证明。
   完整内部物理/独立执行/真实比较/图报告/自动测试/教学/常规检查/Git验收齐备才完成26。
3. **A3有限R参考先行。** [Bergeron记录](experiments/bergeron_reference_followup.md)及[工具链结果](experiments/pscad_toolchain_smoke.json)：未改官方vdiv已真实build/EMTDC链接/run，活动宏gf46/x86，正常退出且原件/profile/父环境不变；无磁盘波形，不能算有限R参考。
   新[有限R设计](experiments/bergeron_reference_design.md)：保留SrvcCbl完整定义，仅实例长度.01→10km，名义R100Ω/Z201Ω/tau300us；1kV斜坡.5–.6ms、Rs100Ω/RL400Ω、1us/6ms。来源/解析/codec/端口/公开API已核，未实际建模或仿真。
   仅prepare-only目录20261109T075010503354Z；2918506496bytes可用提交量<3GiB，未启动native、没有可等待的worker/进程。资源恢复再核新脚本/input hash，使用Python313运行local_reference/a3_followup/finite_r_native_probe.py无参数；--prepare-only绝不启动。新唯一目录、2GiB动态保护/普通RPC20s/build180s/run120s/总420s不变，不连续重试、不关用户程序。
   先确认实际.tlo/参数频率/flags、Vs与Mag时序、全时间轴/原生kV-kA及方向、零历史；PSCAD后续版本修过手工线路flags，不能只看XML。再冻正式窗/限值/自细化及候选步长，不创建候选迎合未经核定的参考。不重跑整包settings/空ATS范围或已成功小教程。
4. **F1外部依赖。** 最新实查41a6685的CI run42576654146终态failure，两个job均runner0/steps空，注释明确billing lock，未执行测试。
   不重复轮询该终态；账户真实恢复后补跑覆盖26候选及此前代码的run，核精确HEAD/attempt的双OS全步骤。旧90b2fcd只覆盖22，本地通过不等于跨OS通过。
5. B1先读[独立误差隔离](experiments/spwm_error_isolation.md)：全点回放/16组合/24顺序已审计，门极为主要影响，BE/器件仍有可见影响，1µS很小。观测电压残差闭合只作诊断。后续另冻有明确教学意图的同数学验证协议；不把供应商跨任务调度直接写入12、不拟合时移/放宽2%或扩二极管框架。C1后置；D0不重复成功仿真。

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

最终复现审计在local_reference/b2_protocol_research/20261109T065107846Z-final-reference-audit，两run同协议/版本检查和全部raw重复点检查已启用，周期FAIL逐位不变。恢复不得继续已终态的旧进程；最终测试及审计均应以已保存终态为准。

候选代码41a6685已推送，精确CI已终态billing lock启动前失败；后续03a913e已实核本地/远端一致。本次只保存设计证据，代码/冻结协议/1223测试输入不变。收尾Win32实读可用提交量2444276KiB（约2.331GiB），无PSCAD进程；既有用户MATLAB50448为R2022b，未触碰。A3/B2均须资源恢复，不能直接重启或把prepare-only当活任务等待。

B2启动方式仍仅只读研究：-batch已无desktop，Java路径/hash依赖使-nojvm不可直接用。新callback审计local_reference/b2_protocol_research/callback_audit/20261109T073545Z/report.md（d6ed233c222e19b3f618d67fa8223d20eeee6e0eefa0975a417a92bffbf8165a）：37输入、67源blocks/13链接实例/9直接SPS库、235记录已核；9 masks SelfModifiable支持研究load_system，但OpenFcn/p-code及调用顺序不明，不能证明等价或内存收益。资源足够后才按报告作两个独立进程、各120s且sim(in)前硬返回的加载对照，完整记录配置/拓扑/SID/workspace/日志/SI；仍守6GiB/2GiB/600s。两臂中原open_system峰值约3.6GiB，不在当前不足3GiB余量下尝试。
