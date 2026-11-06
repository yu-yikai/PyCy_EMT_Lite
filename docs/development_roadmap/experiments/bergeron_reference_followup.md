# A3：有限电阻Bergeron参考与PSCAD环境核验

2026-11-06。已完成安装例调查、独立数学交叉审查和一次原生启动探针。
未加载商业工程、build或sim，未创建PyCy候选；A3在研究中，不计正式完成。

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

## 可恢复证据与下一步

证据均在忽略的`local_reference/a3_followup/`：

| 入口 | SHA-256 |
| --- | --- |
| `analysis_manifest.json`（28调查文件、10关键来源文件） | `9f3f5090a98e9d4ac71484f8423ed9d199d1d15cad15f0f4916e29b9d82205a5` |
| `installed_examples_inventory.json` | `104fd10fea6a32067cd931072828e26e245a6ef2d0ee1b4bdf37c40bf423eb4d` |
| `startup/20261106T061600Z_startup/terminal_summary.json` | `aecb6c82b0755ab6dc6fbae25d7ca4667551cae2f08e91bd113f78380c10891d` |
| `independent_review/physics_audit_review.md` | `eda8af3fd639ba70090f6fba170ffb62e87ae799add44184b0fd919d4725bbea` |

先独立有界读取编译器版本，核公共API的单项设置/工程工具链选择；避开已知挂起的整包settings读取。
确认选择后，独立复制官方简单教程做build/run烟雾验证，只用于环境检查。
在任何A3候选前，先固定有限正R标量参考、与原宿主的明确差异、生效参数/初值/延时规则、事件/方向及比较窗/阈值。
只有真实有限R波形、候选/内部物理/独立运行/图报告/测试/教学/Git验收全部完成才能关闭A3。
不以更简单的无损线路替代有限R要求，也不为它增加损耗线路核心类。
