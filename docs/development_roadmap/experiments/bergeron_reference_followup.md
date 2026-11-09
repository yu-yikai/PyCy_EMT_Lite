# A3：有限电阻Bergeron参考与PSCAD环境核验

2026-11-09：独立官方vdiv教程已真实完成PSCAD编译、EMTDC链接与运行，工具链验证通过。
有限R标量参考仍停留在调查/解析等价阶段；尚无其商业波形或PyCy候选，不计正式完成。
下文保留2026-11-06启动挂起及裸编译失败，最新受控教程结果见末节。

## 参考调查与可复用的等效网络

扫描本机PSCAD5.0 Examples下全部127个pscx，零XML解析错误，找到53个显式TLine/Cable定义。
其中5个单导体手工参数Bergeron定义来自4个原工程：ENI的Cigre_BM/BM1、Lightning的Steep_Front两线路、LightningCoord的Twr。
这些生效电阻均非零；完整原网还含HVDC或雷电设备，不直接变成简单教学例。
PU=1/2的活动分支已按master.pslx核对，未启用的RTP/TTP/ZTP不能拿来当运行参数。
这不是对任意自定义组件内部的穷尽搜索；simpleac的耦合三相几何线路也不是标量参考。

按[PSCAD官方Bergeron理论](https://www.pscad.com/webhelp-v5-ol/EMTDC/Transmission_Lines/The_Bergeron_Model.htm)图8-33/35和式8-92..94，
有限总电阻会改变端口Norton阻抗，并增加同端历史项；现有单根BergeronLine的衰减系数不能代替它。
以下组成则能复用现有无损BergeronLine和Resistor：

```text
k -- R/4 -- 无损半线(Z0,tau/2) -- R/2 -- 无损半线(Z0,tau/2) -- R/4 -- m
```

取两端电流均流入线路为正，r=R/4、Z=Z0+r、H=(Z0-r)/Z、a=(1+H)/2、b=(1-H)/2。
中间电阻的散射关系消元后得到官方端口式：

```text
ik(t) = vk(t)/Z + Jk(t)
Jk(t) = -a*[vm(t-tau)/Z + H*im(t-tau)]
        -b*[vk(t-tau)/Z + H*ik(t-tau)]
```

独立审查给出了时域解析证明，另有97个复频率点ABCD互核，最大相对差7.35e-13。
后者只是数学交叉检查，既不是PyCy运行，也不是PSCAD波形。
该等价仅覆盖常数标量Z0/tau、集中有限R、关闭额外高频damping的双端模型。
参数频率、LongLine预处理、实际R/Z0/tau仍须由真正的参考导出；反射消除设置、频变与相间耦合不包含其中。
现有离散实现要求`tau/(2*dt)`为正整数，两半线负时间零历史；R=0时直接复用全长无损线，不实例化零欧Resistor。
参考插值、初值、事件和探针方向仍未实测，因此当前只是**待原生验证的等效网络方案**。

## 原生环境探针的实际结果

PSCAD5.0.0、Python3.13.5、mhi.pscad2.9.7及gf46描述文件/编译器/EMTDC库均可发现。
mhi的fortran_versions依赖缺失的ATS ProductList.xml，返回空列表，不能据此断言没有可执行编译器。
未补写ATS、注册表、私有codec或用户设置；安装文件存在也不证明工具链能build。

`startup/20261106T061600Z_startup`新建独立最小化实例，按路径、新PID、父进程和独立端口确认归属，并记录创建时间。
真实API返回version=5.0.0、licensed=true，随后整个settings只读查询未返回；已选编译器仍未知。
launch的连接timeout不能限制已连接后的RPC读取，后续不重复这个整包查询。

有界退出检查发现自有PSCAD已自行消失，原因未知，未发送quit或kill给它，不能声称正常退出。
仅阻塞的自有Python在身份与原生终态核验后被结束；原shell实际exit1，两个PID均确认不存在。
原始部分结果、退出检查和清理记录分别保留。没有触碰用户程序，也没有工程加载/编译/仿真。
这证明一次带许可的原生启动，尚不能证明完整PSCAD运行环境可用。

## 编译器故障定位与独立运行

安装的mhi.pscad 2.9.7公共接口是`settings(settings=None, **kwargs)`：无参数读取整个字典，非空字典或关键字用于写入。
没有核实到`settings(field)`这样的单字段getter，不能按旧恢复说明猜测调用。
`setting_range('fortran_version')`只返回可选范围；本机客户端使用ATS ProductList构建编译器映射，缺文件时范围为空，不能据此知道原生实际选择。
该结论由本机已安装源码核验；未调用不受支持的getter，也未修改ATS、私有映射或设置。

随后按顺序取得以下独立进程证据，每个命令均有30秒期限：

| 条件与操作 | 实际结果 | 能说明的范围 |
| --- | --- | --- |
| 原环境，绝对路径`gfortran.exe --version` | exit 0，GNU Fortran 4.6.2 | 版本命令可执行 |
| 原环境，编译自写10行线性方程程序 | exit 1，stdout/stderr均空，无exe，未尝试运行 | 默认编译失败，原记录保留 |
| 原环境，直接`f951 --version` | `0xC0000135`；同轮as/ld均exit 0 | 前端加载失败；未定位具体缺失DLL |
| 官方批处理对应的子进程环境，前端/编译/运行 | 三项均exit 0；编译0.19771s、运行0.05966s | 独立GF46工具链可用 |

编译器随附的`gf46vars.bat`清空`GCC_EXEC_PREFIX`，并将`%GFORTRAN46%\bin`放到PATH前部。
成功实验只在新子进程内采用该合同：GFORTRAN46指向已核安装根目录，保留原PATH完整后缀及其他环境项；父进程环境核对未变。
没有复制DLL、更改全局PATH、注册表、安装文件或用户配置。
原环境下的PE导入/文件位置检查与前端退出码支持继续检查加载环境，但没有完整加载器跟踪，不能宣称已确定哪个DLL导致失败。

两次编译使用逐字相同的自写程序，求解`[[3,1],[1,2]] * x = [9,8]`；成功输出`x=[2,3]`、最大残差0。
生成exe为x86（PE `0x014c`），SHA-256为`d7580063d5227ecd6b66ff02e2dd669c04ffb9c05cd5166dbdf0b8641658f7c8`。
没有链接EMTDC，也没有新启动PSCAD或加载工程。实际PSCAD编译器选择、EMTDC链接和工程build/run仍未证明。
该成功也不能解释此前无关的settings挂起及原生自行退出原因；原失败日志、结果和输入快照均保留。

## 可恢复证据与下一步

证据均在忽略的`local_reference/a3_followup/`。
本次只读复核五份新增清单的52项文件及其JSON中带路径/hash的61个不同文件引用（两者有重叠），全部相符；下列四个原有证据入口hash也未变。

| 入口 | SHA-256 |
| --- | --- |
| `analysis_manifest.json`（28调查文件、10关键来源文件） | `9f3f5090a98e9d4ac71484f8423ed9d199d1d15cad15f0f4916e29b9d82205a5` |
| `installed_examples_inventory.json` | `104fd10fea6a32067cd931072828e26e245a6ef2d0ee1b4bdf37c40bf423eb4d` |
| `startup/20261106T061600Z_startup/terminal_summary.json` | `aecb6c82b0755ab6dc6fbae25d7ca4667551cae2f08e91bd113f78380c10891d` |
| `independent_review/physics_audit_review.md` | `eda8af3fd639ba70090f6fba170ffb62e87ae799add44184b0fd919d4725bbea` |
| `compiler_readiness/20261106T064800Z/manifest.json`（8项） | `dc3de17a5f0109cae6661ff9fed80d6d33aacb07773b955095c73c33f2fe6eca` |
| `compiler_smoke/20261106T065622Z/manifest.json`（7项） | `efd66274b89e2c32c45203fb66ef11819dadd86f35884c638dd5cf60b9dadffa` |
| `compiler_diagnostics/20261106T070003Z/manifest.json`（15项） | `55c71614e7c831f4653246a6f838ce2a54214ec6cde47f1d178c4f7ac7f92224` |
| `helper_versions/20261106T070301Z/manifest.json`（10项） | `e76b723936c225b125effb69444ccbca6d10430d8dcee7a695bd9e64d320c0e8` |
| `compiler_env_smoke/20261106T070543Z/manifest.json`（12项） | `8edc38e5151541ab227fccba10df0faa2d3f1d96eda866be02a34bb57806438e` |

下一步在自有、限时的原生会话中，通过该版本明确支持的只读接口或界面确认实际编译器选择。
启动子进程可继承已核的官方编译环境；不重复整包settings读取或已知为空的ATS范围查询，不把编译器存在当作选中。
确认选择后，独立复制官方简单教程做build/run烟雾验证，只用于环境检查。
在任何A3候选前，先固定有限正R标量参考、与原宿主的明确差异、生效参数/初值/延时规则、事件/方向及比较窗/阈值。
只有真实有限R波形、候选/内部物理/独立运行/图报告/测试/教学/Git验收全部完成才能关闭A3。
不以更简单的无损线路替代有限R要求，也不为它增加损耗线路核心类。

## 2026-11-09：公开宏与真实EMTDC工具链冒烟

官方V5[资源宏文档](https://www.pscad.com/webhelp-v5-ol/PSCAD/The_Application_Environment/The_Workspace/The_Primary_Window/Projects_Branch/Resources_Branch.htm)定义`$(Compiler)`和`$(EmtPlatform)`；本机2.9.7公开`substitute(str)`直接调用该接口，不经过settings/ATS codec。
先行只读研究另确认profile持久偏好为GF46，但没有把它当活动选择。随后新建独立最小化会话，公开宏实际返回`gf46`/`x86`。

按[官方项目API](https://www.pscad.com/webhelp-v5-al/reference/project.html)复制未改的tutorial/vdiv.pscx到唯一目录，先核输出目录确实在隔离run内，再load→build→messages→run→output→quit。
PSCAD5.0.0/许可true，16条正常build消息、零警告/错误；Station.f和Main.f实际编译，链接vdiv.exe，运行输出EMTDC5.00 R#93051001及`EMTDC run completed.`。
输入和生成map均为原0–0.2s、50µs计算/250µs绘图配置；PlotType=0不请求磁盘波形。本次只验证环境，不能叫有限R数值验收。

继承的编译环境仍只作用于子进程，未修改settings/ATS/注册表/全局PATH。新会话按PID/路径/父进程/创建时间/专属端口核归属，阶段/总期限及2GiB可用提交量保护有效。
13.6482s完整生命周期内，最低观测可用提交量2193596416bytes，未触发保护。quit返回后有界观察退出，cleanup为空；自有worker42340/PSCAD46468已独立核实不存在。
原官方模型、用户profile哈希和父进程环境均未变，没有触碰既有用户MATLAB。

[精简结果与hash](pscad_toolchain_smoke.json)对应忽略目录`local_reference/a3_followup/native_toolchain/20261109T072309048657Z/`，25项库存SHA为`132e558c8da89b6f190a29ae38de01d48a847b29c5a04b2382466c879246324f`；第三方原件、生成源码/二进制及运行配置均只留本地。
先前整包settings挂起/原生自行退出原因仍未知，原记录不覆盖；本轮成功不依赖重复该查询。

下一步先固定最小有限正R标量参考及其与原宿主的差异，核生效参数/零历史/延时插值与端口方向；在A3候选出现前冻结完整比较窗和阈值。教程不含线路，不提升第23项有限R参考的inspected状态。

独立审计逐项核25个文件的hash/size及清单无遗漏，并读取PE确认vdiv.exe为x86（0x014c）；原生、worker及实际运行exe均已退出。生成map只能证明运行配置，不能代替末采样时间或数值精度。审计为`local_reference/a3_followup/native_toolchain_audit/20261109_readonly_e41b7d/audit_result.json`，SHA`9edaac84d2ea930c66f2b545e216deb38e7b388710d5d7cb7bc85346cd3451cb`。
