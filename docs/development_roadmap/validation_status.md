# 验证状态

2026-11-23。独立 PSCAD 冷启动共 240,002 个采样点，80,001 个共同时间点。电路守恒、负荷切换、功率滤波、频率和相位递推均通过。正式新增仍为 18 项。
[单站孤网下垂 PSCAD 实测](experiments/d1_gfm_island_native_20261123.json)

2026-11-23。双档解析预检复核了负荷事件、逐拍梯形积分、滤波与相位关系，以及预测稳态约 359.4→717.4 W、60.001→59.643 Hz。原生验收待执行，正式新增仍为 18 项。
[单站孤网下垂原生协议](experiments/d1_gfm_island_protocol_20261123.json)

2026-11-23。36 号对标覆盖 600,003 个原生正时间点。Windows 1,616 项含慢测，WSL2 默认入口和四项专项均通过。正式新增 18 项。
[36 号验收报告](../../validation/cases/grid_connected_pv/acceptance_report.json)

2026-11-23。两档初值、光伏仿射范围和原生参考已封存。试算点数和偏差已复核，正式算例待实现，新增完成数为 17。
[36 号光伏并网候选协议](../../validation/cases/grid_connected_pv/candidate_protocol.json)

2026-11-23。两档同档短窗公共前缀、照度阶跃前后物理及跨档窗都通过。正式新增仍为 17 个，PyCy 教学候选待验证。
[光伏并网原生照度阶跃复核](experiments/d1_pv_grid_irradiance_native_20261123.json)

2026-11-23。两档短窗各有 10,001 和 20,002 个原始正时间点。支路物理、控制采样、实际门极和公共前缀通过。正式新增仍为 17 个。
[光伏并网原生启控复核](experiments/d1_pv_grid_activation_native_20261123.json)

2026-11-23。已固定短窗投入、长窗出力和物理能量判据。原生并网运行待完成。650 串原生参考以及 1 s PyCy 技术试算均已绑定。
[光伏单站并网原生协议](experiments/d1_pv_grid_protocol_20261123.json)

2026-11-23。原生串联工程共 60,005 个采样点。原始启动、逐区间电荷和能量、同档缩放、两档稳态和共同时间复核均通过。正式新增仍为 17 个。
[650 串光伏双档原生参考](experiments/d1_pv_string_native_20261123.json)

2026-11-23。串联缩放固定同档逐点和跨档门限。两档单电池补充报告作为原始参考，保留其零行判定。原生串联执行待完成。
[光伏串联原生缩放协议](experiments/d1_pv_string_protocol_20261123.json)

2026-11-23。原始数据双档共 60,005 行、8 路输出。全部区间的电荷、能量、独立稳态和跨步长通过。物理冷启动满足补充协议，原始 0 s 电压门失败单列。
[光伏 R–C 双档原生参考](experiments/d1_pv_rc_transient_native_20261123.json)

2026-11-23。5 µs 原协议失败项为零行电压，约 0.312 mV，高于 0.10 mV 门限。原始回执和审计均保留，逐区间电荷和能量通过。补充复核待完成。
[光伏暂态启动补充协议](experiments/d1_pv_rc_startup_protocol_20261123.json)

2026-11-23。光伏暂态双档各预定 20,002、40,003 个原生采样点。冻结了控制边沿、支路物理、逐区间能量、稳态和跨档判据，待原生运行复核。
[光伏 R–C 原生暂态协议](experiments/d1_pv_rc_transient_protocol_20261123.json)

2026-11-23。5 µs 和 2.5 µs 各保留 2,002、4,003 个原生时刻及 28 路输出。通过电流方向、电压一致性、欧姆定律、功率、稳态窗口和跨步长复核。
[单电池双档原生测量](experiments/d1_pv_static_native_20261123.json)

2026-11-23。光伏静态协议有 28 路信号，以原生光伏端口和独立电表核对方向与欧姆定律。原生编译与实测尚待完成。
[单电池原生静态协议](experiments/d1_pv_static_protocol_20261123.json)

2026-11-23。35 号与 PSCAD 两档对标覆盖 180,003 个原始正时间点，六路开关逐点一致。34 号两档全列逐位相同。Windows 1,612 项含慢测及 Ubuntu WSL2 独立入口和 11 项专项均通过。
[35 号验收报告](../../validation/cases/grid_connected_storage/acceptance_report.json)

2026-11-23。35 号实现前的诊断覆盖 180,003 个原生正时间点。六路开关与离散控制字逐点一致，最大电压差约 0.664 nV，最大电流差约 3.87 nA。独立公开入口尚待验证。
[35 号候选协议](../../validation/cases/grid_connected_storage/candidate_protocol.json)

2026-11-23。原生长窗核对 60,001 和 120,002 个恢复正时间点、41 路输出和 43 列控制日志。每档均通过旧短窗与新种子、旧短窗与新恢复以及同档种子尾段共三组前缀复核。功率窗、梯形关系和细档门极保持均通过。
[单站储能双档原生长窗](experiments/d1_storage_grid_long_native_20261123.json)

2026-11-23。长窗两档预计分别记录 60,001 和 120,002 个恢复正时间点。既有短窗判据沿用，另加入正负功率窗、逐外环给定和跨档门限。原生长窗待执行。
[单站储能原生反转长窗协议](experiments/d1_storage_grid_long_protocol_20261123.json)

2026-11-23。单站储能两档种子和恢复分别核对 510,005 行、30,003 行及 41 路输出。两档参考均完成 100 µs 首次采样和 105 µs 门极生效，末充电窗平均母线 400.419 V 和 400.420 V。
[单站储能双档原生短窗](experiments/d1_storage_grid_short_native_20261123.json)

2026-11-23。并网储能独立 PyCy 两个长窗共 180,005 行，最大实际相电流约 2.48 A。5 µs 短窗与粗档长窗前 10,002 行逐点一致。带桥漏流的独立预充计算得到峰值约 4.000 A，0.800 s 母线约 399.99968 V。两组证据用于原生构建前的核对。
[单站并网储能短窗协议](experiments/d1_storage_grid_short_protocol_20261123.json)

2026-11-23。储能端口两档共核对 1,205 行、10 路原生输出及四个电流边沿。同档极化与端口电压最大偏差低于 5.50 pV，逐区间能量残差约 1.10 pJ，公共时刻最大极化差约 25.403 µV。两档静置均向零极化恢复。
[储能端口原生双档证据](experiments/d1_storage_rc_short_native_20261123.json)

2026-11-23。短窗 5 µs 和 2.5 µs 的预期行数含零点分别为 402 和 803。第一条充电行的极化电压计算值约为 50.0 µV 和 25.0 µV。实际原生求解与复核待执行。
[一阶 RC 储能端口短窗协议](experiments/d1_storage_rc_short_protocol_20261123.json)

2026-11-23。34 号正式对标覆盖 5 µs、2.5 µs 共 330,003 个原生正时间点，并独立核准两个起点。12 路开关状态每点相同，最大电压差约 15.8 nV，最大相电流差约 1.01 nA，物理守恒和功率窗全部通过。Windows 1,609 项含慢测、Ubuntu WSL2 默认入口及 8 项专测通过。
[34 号验收报告](../../validation/cases/two_terminal_vsc_hvdc/acceptance_report.json)

2026-11-23。独立 PyCy 研究试算与两档原生续算逐点对照，共 330,003 行。12 路开关状态逐行一致，最大电压差约 15.8 nV，最大相电流差约 1.01 nA。候选复用已核过的初值。
[34 号候选协议](../../validation/cases/two_terminal_vsc_hvdc/candidate_protocol.json)

2026-11-23。粗细两档分别逐点核对 110,001、220,002 个原生长窗点、82 路波形和两站日志。每站验证 5,500 次内环更新及 550 个外环采样点。三组功率窗和跨步长门限通过。5 µs 的 PyCy 试算与原生长窗 12 路开关状态逐点一致。已封存 28–32 号两档共 14 个启动轨迹，供改动后逐位核对。
[双端 PSCAD 长窗报告](experiments/d1_dual_vsc_long_native_20261123.json)

2026-11-23。闭环 PSCAD 5 µs、2.5 µs 分别复核 10,001、20,002 个续算点，覆盖 82 路原生波形及两站各 43 列日志。首次 100 µs 采样在 105 µs 门极拍生效，细档每站 10,001 个中点保持通过。同档重叠最大电压差约 2.01 nV、最大电流差约 0.482 nA。40–50 ms 实测 A 站平均无功约 +27 至 +32 var，B 站约 −50 至 −48 var。
[原生双站闭环报告](experiments/d1_dual_vsc_active_native_20261123.json)

2026-11-23。双档冷启动分别采集 80,601 和 161,201 行。从原生快照续算所得的 200 和 400 行均与相同步长的冷启动尾段对齐，逐点核对 64 路。最大电压差约 0.060 nV，电流差约 0.373 nA。首个恢复区间的全电路储能残差小于 1.08×10⁻¹² J。
[双档原生快照报告](experiments/d1_dual_vsc_snapshot_native_20261123.json)

2026-11-23。双端 VSC 的 PSCAD 5 µs 冷启动核对 80,601 行和 52 路原生测量。0.400 s 断开预充，0.401 s 投入负荷，切换当行电流为 0.999999 A。节点电流残差最大 0.224 nA，逐区间储能残差最大 6.89×10⁻¹¹ J。独立计算全程极电压与线路电流峰值差分别为 0.292 nV、0.171 nA。Ruff、mypy 及现有两个 VSC 算例的 41 项专项测试通过。
[原生试验与输入哈希](experiments/d1_dual_vsc_parked_native_20261123.json)

2026-11-23。33 号在 5 µs、2.5 µs 共核对 360,002 行。母线相电压逐点最大差约 14.6 nV，线路串联电流最大差约 0.283 nA。源端电流原始差约 0.164 A，预定奇偶拍模型的最大残差低于 20 nA。锁定同步、Ruff、mypy、Windows 1,601 项含慢测、Ubuntu 默认入口和 6 项专测均通过。
[33 号执行与对标](../../validation/cases/pjm5_load_step/acceptance_report.json)

2026-11-23。PJM5 原生短窗 401 行，全窗 120,001、240,001 行，每行 95 路。两档都在 0.300 s 读到 10,580 Ω。全窗节点 KCL 残差低于 1.63×10⁻¹¹ A，逐区间储能残差低于 2.28×10⁻⁹ J。跨档瞬态母线电压峰值差约 284 V，距边沿超过 20 ms 的区段峰值差约 0.35 V，稳态窗的 2 号母线有效值最大差 41.6 µV。冻结判据均通过。
[逐步物理检查与跨档证据](experiments/d1_pjm5_pscad_reference_20261123.json)

2026-11-23。PJM5 独立数学计算覆盖 120,001、240,001 行。负荷边沿附近两档母线电压峰值差约 284 V，距边沿超过 20 ms 的峰值差约 0.35 V，50 ms 窗的 2 号母线有效值差低于 0.05 mV。已按这些结果固定瞬态、稳态和储能复核门限。原生 PSCAD 资格待验证。
[冻结判据和数学证据](experiments/d1_pjm5_emt_protocol_20261123.json)

2026-11-23。32 号正式对标通过 5 µs、2.5 µs 两档共 480,005 行，含独立初值。六路门极逐行相同。母线差分与桥臂线电压最大差 4.51 nV，支路电流最大差 0.92 nA。PyCy 电容逐区间储能残差小于 1.16×10⁻¹³ J。锁定同步、Ruff、mypy、Windows 1,595 项含慢测以及 Ubuntu WSL2 默认入口和 5 项专测均通过。
[32 号对标、图和执行记录](../../validation/cases/grid_connected_vsc_dc_voltage/acceptance_report.json)

2026-11-23。直流母线 PSCAD 长窗分别核对 160,001、320,002 个续算点。两档各通过 800 次外环、8,000 次内环及下一门极拍，细档逐一核对 160,001 个中点保持。电容逐区间储能残差均低于 2.01×10⁻¹¹ J。跨步长的母线最低值差 6.96 mV、窗口均值最大差 14.45 mV，功率及 dq 电流窗口均通过预先固定的判据。
[长窗复算及跨步长证据](experiments/c1_dc_live_feedback_long_20261123.json)

2026-11-23。PSCAD 直流闭环短窗的 401、802 个续算区间均通过物理与控制逐行复核。两档各有 2 次外环、20 次内环和 20 次下一门极拍应用。细档的 401 个中点保持全部通过。实测差分电压与控制日志最大差 5.01×10⁻¹² V，电容储能残差最大 1.95×10⁻¹¹ J。长窗负荷恢复待原生验证。
[原生短窗及独立复算](experiments/c1_dc_live_feedback_short_20261123.json)

2026-11-23。5 µs 与 2.5 µs 的带桥 PSCAD 续算分别核对 401、802 个正时间区间。两档均通过原生初值、交流电感、母线 KCL、负荷边沿及储能判据。与 PyCy 的差分母线电压最大差 0.61 nV、支路电流最大差 0.71 nA。对地电压的额外逐点检查仍为 FAIL，两档峰值为 14.16 µV、53.74 µV。闭环控制草案已过合成输入验证，实际原生反馈与门极待核。
[带桥短窗、原始输出和失败诊断](experiments/c1_dc_parked_bridge_20261123.json)

2026-11-23。Ubuntu 24.04.4 WSL2 在独立临时检出中对 a223722 完成 1,590 项全量测试，包含 slow。Python 3.14.5 的锁定同步、Ruff 和 mypy 均通过，369 个归档源文件在测试前后哈希一致。托管 CI 的情况仍按 F1 记录。
[Ubuntu 独立运行证据](experiments/f1_ubuntu_a223722_20261123.json)

2026-11-23。直流母线 PyCy 短窗两档分别 402、803 点，负荷均在 1 ms 投入，首拍约 1.249 A。步长减半后相对连续 RC 解的最大差从 0.625 mV 降至 0.312 mV，符合切换区间的半步误差。两档最大储能残差 2.07×10⁻¹³ J。Windows 115 项专项、锁定同步、Ruff 和 mypy 通过。

PSCAD 独立续算 401 点，快照起点 400 V、400 J，负荷在恢复后 1 ms 投入。核对全部 401 个区间，最大电荷、储能和节点电流残差分别为 4.95×10⁻¹⁴ C、1.98×10⁻¹¹ J 和 2.17×10⁻¹⁰ A。该结果覆盖无源电路的初值和续算，带桥闭环参考待验证。
[短窗证据与哈希](experiments/c1_dc_bus_startup_20261123.json)

2026-11-23。31 号四组候选共 780,010 点。对 PSCAD 的 36 个同档窗内，468 项离散量完全一致，936 项连续量检查通过，PCC 瞬时相电压最大差 0.85 µV。每组有 650 次外环与 6,500 次内环及后一拍门极应用，细档各核过 130,001 个保持中点。Windows 全量 1,590 项含 slow、WSL2 默认入口和 4 项专测、锁定同步、Ruff 与 mypy 均通过。
[验收、图和原始结果的哈希](../../validation/cases/grid_connected_vsc_power_vac/acceptance_report.json)

2026-11-22。两档四组 8 个相干跨步长窗均通过，基波电压、有功和基波无功最大差为 0.03646 V、1.770 W 和 2.984 var。每个细档工况核过 130,001 个保持中点。Windows 全量 1,586 项含 slow，WSL2 专项 30 项，锁定同步、Ruff 和 mypy 均通过。
[双档结果与软件检查](../../validation/cases/grid_connected_vsc_power_vac/coherent_reference_report.json)

2026-11-22。粗档固定 q 和调节组各 130,002 个原生点。两个相干稳态窗的 PCC 电压分别提高 1.206 V 和 1.221 V，吸收基波无功减少 143.3 var 和 145.6 var。原单周波压降失配在两工况前缀一致复现。
[配对结果与原报告哈希](../../validation/cases/grid_connected_vsc_power_vac/coherent_window_coarse_pair.json)

2026-11-22。5 µs 调节组通过 650 次外环、6,500 次内环及门极应用和 390,003 个馈线相间隔检查。使能前第二周期只跌 0.683 V，基础协议 FAIL。原波形的 50 ms 诊断为使能前 118.787 V、调节后 120.019 V，相干窗的跨步长验证仍待原生运行。
[失败证据和诊断](../../validation/cases/grid_connected_vsc_power_vac/fundamental_window_trial.json)

2026-11-22。外环平均模型的三组响应速度扫描中，稳态 PCC 相电压从基线 118.803 V 恢复至约 119.986 V，桥压所需峰值低于 170.01 V。该筛选供冻结工况，正式判据由独立 PSCAD 开关波形验证。
[已固定的外环参考协议](../../validation/cases/grid_connected_vsc_power_vac/reference_protocol.json)

2026-11-22。PSCAD 5 µs PCC 短窗采集 48 路、122 点，全部按原生编译布局绑定。馈线残差上界峰值 2.01e-10 V，门限 5e-6 V。独立复读 PyCy 同档前 122 点，PCC 电压最大差 9.07e-9 V，电流最大差 1.44e-12 A。P 前馈与 Vac 外环长窗仍待验证。
[原生结果与哈希](experiments/c1_pcc_feeder_native_result_20261122.json)

2026-11-22。PSCAD 短窗第三次试验已编译，生成 17 个非接地物理节点、22 条支路、48 路输出。原准入拒绝后尚无短窗波形，运行须重新按冻结布局逐项核准。
[编译归档及证据身份](experiments/c1_pcc_feeder_native_layout_20261122.json)

2026-11-22。2.5 µs PyCy 复验通过六项预试验判据，PCC 基波从 118.92 V 升至 122.15 V。双档回放以完整 60 Hz 基波估计为参照，逐电气行滤波、每 1 ms 读取的最大偏差为 0.182 V RMS，100 µs 抽样后平均再滤波的最大偏差为 1.570 V RMS。
[两档报告与哈希](experiments/c1_pcc_measurement_replay_20261122.json)

2026-11-22。PCC 有限网阻的 PyCy 预试验通过六项约定检查。正 q 轴基波电流增加 1.490 A 峰值，PCC 基波升高 3.210 V RMS，两工况 PCC 有功均约 500 W，新增支路离散电压残差峰值 2.51e-12 V。PSCAD 短窗预定判据已冻结，待原生执行。
[数据身份与阈值](experiments/c1_pcc_feeder_native_probe_20261122.json)

2026-11-22。30 号新同档比较 18 窗通过 414 项连续量、234 项逐点一致及 72 项 PLL 状态检查。最大相角差 2.665e-15 rad，周期跟踪误差最大 0.06665 A。两平台跨步长通过。最终参考入口切换后复跑 31 项专项及 Ruff 和 mypy，通过的 1,585 项 Windows 全量覆盖相同的教学及测试源码。
[30 号验收报告](../../validation/cases/grid_connected_vsc_pll/acceptance_report.json)

2026-11-22。电源精度两档共 120,005 点。原 19 项物理、18 个同档窗口、严格 PLL 状态及全部中点保持通过。固定候选对照的最大 PLL 相角差 2.665e-15 rad，原生跨档周期均值差 0.04845 A、分窗 RMS 差 0.07194 A。新正式入口对标待执行。
[电源精度双档参考报告](../../validation/cases/grid_connected_vsc_pll/source_precision_reference_report.json)

2026-11-22。PSCAD 粗档电源对照通过原 19 项全点电气判据和全部九个同档窗口。PLL 相角误差峰值 2.665e-15 rad，门限 1e-11 rad。频率、积分与归一化误差均满足冻结门限。
[粗档电源精度结果](../../validation/cases/grid_connected_vsc_pll/source_precision_trial_result.json)

2026-11-22。30 号两档 18 个同档窗通过 414 项连续量和 234 项离散量检查。PLL 相角差峰值 2.594e-10 rad，高于 1e-11 rad 门限。Ruff、mypy、Windows 1,585 项含慢速回归与 WSL2 专项 31 项通过。两系统教学入口可运行，正式验收待完成。
[30 号首轮验证](../../validation/cases/grid_connected_vsc_pll/validation_report.json) · [电源精度对照协议](../../validation/cases/grid_connected_vsc_pll/source_precision_trial.json)

2026-11-22。PLL 两档原生长窗通过原 19 项电气判据，各 2,000 次采样和门极应用，细档保持 40,001 个中点。验收窗最大相角误差 0.6298°、频率误差 0.01949 Hz、周期平均跟踪误差 0.06665 A。原生跨步长最大周期均值差 0.04845 A、最大分窗 RMS 差 0.07194 A。
[PLL 双步长原生长窗](../../validation/cases/grid_connected_vsc_pll/full_reference_report.json)

2026-11-22。PLL 粗档 40,002 点通过原 19 项电气判据、2,000 次反馈和随后的门极施加。稳态验收窗相角误差峰值 0.630°、频率误差峰值 0.01949 Hz，最大周期平均电流误差 0.06497 A。三周期功率方向通过。
[PLL 长窗记录](../../validation/cases/grid_connected_vsc_pll/full_reference_report.json)

2026-11-22。PLL 细档 243 点通过原 19 项电气、六次反馈和门极顺序及 121 个实际中点保持。两档短窗范围为 0–605 µs，长窗锁定与电流跟踪待验。
[PLL 双步长短窗结果](../../validation/cases/grid_connected_vsc_pll/short_reference_report.json)

2026-11-22。PLL 粗档真实运行 122 点，19 项电气判据全部通过，共模残差峰值含末位精度上界约为 0.223 nV。六次采样和下一门极拍均通过，首个样本因初始超前产生负的频率修正，第二个样本切换到实测电压归一化。
[PLL 短窗记录](../../validation/cases/grid_connected_vsc_pll/short_reference_report.json)

2026-11-22。并网 PLL 协议的 29 号电路与 11 号离散定义哈希、短窗行数和末次生效时刻已核。耦合 PLL 的原生短窗待运行。
[接入参考协议](../../validation/cases/grid_connected_vsc_pll/reference_protocol.json)

2026-11-22。公开 29 号入口四次运行共 240,010 点，原电气及控制检查均通过。32 个同档窗口通过 736 项连续量和 416 项离散量核对，最大周期平均跟踪误差为 0.06269 A。两平台跨档及两工况成组比较通过。Windows 1581 项含 slow 回归通过，WSL2 Ubuntu 完成 29 号默认独立运行及 28、29 号的 27 项专项测试。共用接线后的 28 号两档原波形和比较结果与正式验收时逐字节一致。
[29 号验收报告](../../validation/cases/grid_connected_vsc_closed_loop/validation_report.json)

2026-11-22。四份 PSCAD 长窗全点电气、时钟、控制与跟踪判据均通过。PyCy 原型同档比较在 32 个窗口内通过 736 项连续量及 416 项离散量检查。跨档最大周期 dq 均值差 0.04355 A，最大分窗 dq RMS 差 0.08142 A。两档共同前段均通过，去除 q 阶跃后确认该阶跃的 q 轴均值贡献为 1.530–1.567 A。正式教学入口尚待独立运行及验收。
[完整参考报告](../../validation/cases/grid_connected_vsc_closed_loop/qualified_reference_report.json)

2026-11-22。5 µs 主工况 40,002 点全部通过原电气、控制和跟踪判据。两档各九窗 PSCAD 对 PyCy 共通过 414 项连续量检查及 234 项门极、电阻和饱和状态检查。主工况跨档最大周期均值差 0.04355 A，最大分窗 dq RMS 差 0.08142 A，分别低于 0.10 A 和 0.20 A。
[主工况两档结果](experiments/c1_pscad_main_both_steps_20261122.json)

2026-11-22。PSCAD 细档主工况完成一次原生构建和一次长窗运行。全部 2,000 次控制更新、2,000 次门极施加和 40,001 个细步长半步保持通过。配置角复算得到电网 q 轴电压最大误差 0.05954 pV，原限值为 1 pV。原 19 项电气判据和同档 PyCy 对标通过，范围为细档主工况。
[数值报告索引](experiments/c1_pscad_angle_arithmetic_trial_20261122.json)

2026-11-22。直流负端作求解零点的 2.5 µs PSCAD 主工况完整输出 80,003 点，原 19 项电气判据全部通过。共模约束残差上界为 0.027515 µV，上限为 2 µV。三周期跟踪误差最大 0.0627 A，功率方向通过。独立高精度配置角复算确认 2,000 个采样中有 67 个 (e_q) 值超过原 1 pV 上限，峰值 1.588 pV。整体资格仍未通过。
[实测和复算](experiments/c1_pscad_reference_point_trial_20261122.json)

2026-11-19。PSCAD 两档主工况均实际运行并正常闭场。5 µs 和 2.5 µs 的共模约束残差峰值分别为 11.463 µV 和 22.469 µV，均超过原 2 µV 上限。三周期跟踪误差最大分别为 0.0574 A 和 0.0627 A，功率方向通过。原复算拒绝和全点诊断均已留档，完整参考待验。用户已暂停。
[长窗记录](experiments/c1_known_angle_dq_pscad_full_20261119.json)

2026-11-19。PSCAD 5.0 的两次 2.5 µs／600 µs 运行均满足 241 行反馈时序、120 个半拍保持和限幅恢复。默认设置有两点共模约束残差超限，峰值 2.088734 µV。稀疏求解门限设为 1 后，原物理判据全过，共模上界 0.558654 µV，限值仍为 2 µV。与使用自身反馈的 Python 同档比较时，23 项数值指标、12 路门极和电阻及饱和状态均通过。Python 长窗已做两工况双步长内部物理检查。
[细档和长窗记录](experiments/c1_known_angle_dq_pscad_feedback_fine_20261119.json)

2026-11-18。固定参考经 `on_step` 连接28号网络，两档121/241点均与固定门极独立驱动逐行一致，初流、电阻关系、KCL、KVL及梯形关系通过。Simulink两版共三次实际启动均未进入函数，无原生控制波形。已验收的开环结果见28号报告。
[设计检查](experiments/c1_known_angle_dq_design_checks_20261118.json) · [启动记录](experiments/c1_known_angle_dq_native_startup_20261118.json)

2026-11-18。PSCAD 5.0完成一次600µs实际闭环运行。121点的原电气门全部通过，共模含精度上界1.446065µV，低于2µV。Python使用自身反馈，121点的门极、电阻、限幅标志逐点一致，23项同档比较通过。范围为5µs短探针。
[短闭环记录](experiments/c1_known_angle_dq_pscad_feedback_20261118.json) · [接入构建记录](experiments/c1_known_angle_dq_pscad_control_20261118.json)

2026-11-18。Windows及WSL2 Ubuntu 24.04.4均完成锁定同步、Ruff、mypy和1573项含slow回归。Ubuntu原1568通过、5失败及新248项专项和完整复验均留档。24号恢复原38项原生对标，28号40002/80003点的输出与已验收结果逐位相同，两路原门全过。
[跨系统验证记录](experiments/f1_ubuntu_a777c00_20261118.json)

2026-11-18。两系统的24个教学入口逐个退出0，sdist/wheel构建及库外安装通过。Ubuntu初次依赖超时和库外索引故障留档，按原锁定依赖恢复后通过。WSL回收了首个成功CLI临时目录，保留原运行及发行包记录。
[CLI与发行包记录](experiments/f1_cli_wheel_cbdc9b1_20261118.json)

2026-11-18当前。正式28号双档全部40002/80003点与真实Simscape对标通过。5µs、2.5µs各通过19项物理门和150组同档比较，跨档132组通过。两路结论一致，原2µV共模阈值保持，实测上界0.310070/0.011836µV。锁定同步、Ruff、mypy、1573项完整回归及默认独立运行通过。发布范围为开环电路。
[28号验收报告](../../validation/cases/grid_connected_vsc_open_loop/validation_report.json)

2026-11-18当前：Decimal80求解精度干预完成完整粗档40002点，实际raw/RHS/Simulator求解次数均40002，初值1次，9份Decimal因子，最大尺度残差2.418e-77。两套原物理核均全19门通过，共模含完整q上界0.3100773µV小于2µV。时间和6门极位与原粗档逐位一致，临时方法已恢复，548输入及8结果文件绑定通过闭场核验。正式候选待精简实现后的双档及全量验收，新增完成9。既有1566项含slow回归保持原源码范围。

2026-11-18当前：全点驱动分解通过原定算术精度门，两份独立复核完成。全部40002点、40001区间、8类矩阵和CSV/NPZ共1480074个binary64值完成核对。KCL分解误差最大4.5931e-74A，TR为1.3815e-75V，累积项为1.3417e-68V。该研究使用既有轨迹，新增求解/轨迹/native均0。候选粗档共模门仍待通过，新增完成9，1566项回归保持原测试范围。见[机器记录](experiments/c1_observed_forcing_ledger_20261118.json)。

2026-11-18：用户已恢复长期任务。已核本地与远端HEAD均为7a10fc9，120个Python文件及2个依赖与既有1566项测试快照一致。当前继续实现全点误差驱动分析器，随后用既有轨迹进行离线分析。新增完成9，C1进行中。以下暂停记录保留为历史。

2026-11-17：已按用户要求暂停。HEAD为7a10fc9；本轮仅恢复核对与账本方案/公式静审，分析器和新纯检查尚未落盘，未启动全点账本、求解或仿真。子任务已停止。暂停记录已保存在忽略目录，五状态仅本地更新、未提交；等待用户明确恢复后再继续。新增完成9，28号候选未验收。

2026-11-16当前：固定h最终120源码与2依赖的锁定同步、全范围Ruff/mypy（39文件）及1566项含slow回归通过（0失败/错误/跳过），默认独立Agg运行40001点通过。真实Simscape参考资格保持。新候选两档40002/80003点的双路独立检查均确认：粗档共模2487点超限，峰值2.533674891µV>原2µV；细档物理门、150/150同h与132跨h门通过，粗档条件预测仅作诊断。63596数值exit1非资源中止，17585测试exit0，均已终态；输入/快照/输出哈希重核一致。候选未验收，新增完成9，C1/跨OS未完成。见[机器报告](../../validation/cases/grid_connected_vsc_open_loop/validation_report.json)。下一项驱动账本仅有未执行计划。

## 已记录里程碑

2026-11-16：完整开环VSC的真实Simscape参考已通过资格验收：[资格报告](../../validation/cases/grid_connected_vsc_open_loop/qualified_reference_report.json)。两档40002/80003点、全部57量原时间位、原19门及辅助门、四窗/六周期和132跨h门通过；最终独审另核6960290次Time/Clock位及69个原始行，未将有限点审查冒称完整数学重跑。

完整MAT重载后29个logsout数值摘要与tout前后一致；不宣称完整simlog树的任意对象元数据逐项相等。细档额外6个R_command日志仍40002点，正式导出57量均保持80003点。科学计数法文件大小仅由冻结窄规则精确核整数，原读取器FAIL保留。见[完整证据与边界](experiments/c1_nojvm_full_reference_20261116.json)。

短MAT-only恢复通过81点原门；原运行FAIL不改称PASS。28号候选未实施、新增完成9、C1进行中。113源码/依赖不变，既有1518含slow未重跑；F1两OS测试仍受已有CI账单锁阻塞。

## 先前检查点

2026-11-16：完整规模内部合成分析正常闭场，40002/80003点、原19门及辅助门、四窗/六周期与132项跨h结果通过。受控会话250.12s（worker247.47s），实际计算PID的采样峰值约110.61MiB；生成的时间编码不是商业原生时间观测。见[分析与守卫证据](experiments/c1_offline_full_n_and_nojvm_guard_20261116.json)。

真实R2025a无JVM守卫探针exit0，9项.NET哈希/固定路径检查通过，全程model0/sim0，自有进程已退出且未强制清理。尚未证明Simulink/Simscape、simlog、MAT保存重载或完整参考，也未证明完整模型内存收益；先前CIM预检超时启动0保持，具体失败查询未记录。

113源码及依赖本轮不变，既有[1518项全量](experiments/vsc_input_validation_20261116.json)保持，未重跑。新增完成9、C1进行中；原短探针PASS、PSCAD FAIL及Simscape完整Run资源中止保留。F1的[CI43856421332](experiments/ci_57fbc81.json)因账单锁未执行测试，本轮无新CI观察。

## 历史记录

2026-11-16：完整两h模型各compile1/sim0、结构独审通过；完整Run仅尝试5µs一档，因可用提交内存低于2GiB资源中止。原模型复制完整，无report/MAT/CSV；是否进入sim及调用数均未观测。见[完整模型与资源中止记录](experiments/c1_simscape_full_resource_stop_20261116.json)。

自有进程清空、清理无错误，已有MATLAB未被干预；前后113/八输入及本机库和exe身份核准。全量波形/原19门/辅助门/四窗及六周期比较均未执行，细档未启动，不授完整参考或候选资格。新增9、C1进行中；1300为旧全量，F1仍为已有账单锁，无新CI。


2026-11-16：真实R2025a库发现exit0、11模块唯一、仅两个只读library、无新用户图。ROOT与独立复核确认113源码快照、15项安装源及输入前后绑定；两包累计启动一次（首次预检超时启动0），63.918s闭场，自有进程清空、无强制清理。该结论仅为接口发现，不授予新模型、逐段TR或数值参考资格。见[接口证据](experiments/c1_simscape_library_discovery_20261116.json)。

三项license test均为1，实际inuse仅MATLAB/Simulink；Simscape新模型许可签出尚未验证。精确c3fdf79的新CI43825501731因账单锁终态失败，两OS未获得runner、steps空，不能算测试失败或通过。可读性小改的本地检查已通过，1300全量仍为此前结果；新增完成9、C1进行中、原2µV FAIL保持。


2026-11-16：可读性小改通过锁定同步（27包）、全范围Ruff、mypy（39文件）和27号独立Agg运行（6001点）。修改前后默认stdout逐字相同，除摘要f-string外AST一致。正式Python文件仍113个，27号摘要变更、其余112个及依赖不变；1300项全量仍为此前结果，本轮未重跑。

C1的原完整参考未通过2µV阈值，仍9个新增完成、C1进行中；以下原生记录保持原执行HEAD和证据，不借用当前源码快照。

2026-11-16当前：真实PSCAD编译一次、0错误；19支路、45个计划输出及原完整物理与控制检查通过。有向电路图等价，但节点编号未变化，未满足预设的试验激活条件，最终状态为NODE_ORDERING_NOT_ACTIVATED_NO_RUN。会话8170的exit1来自仿真前准入拒绝；没有调用Run，也没有OUT/INF数值数据。PSCAD正常关闭，自有进程清空；81项非波形文件、33项原绑定、6项控制绑定及完整封包引用均经双路核验。见[节点排序实建记录](experiments/c1_node_ordering_build_attempt_20261116.json)。

原完整双步长参考未通过2µV阈值的结果保留；仍为9个新增完成、C1进行中，没有新的合格参考或教学候选。113个正式Python文件及依赖未改，既有1300项测试（含slow）本轮未重跑。新Simscape路线仅完成静态调查；当前许可、新模型、编译、仿真与全部验收要求均待验证。

2026-11-16当前：原完整开环参考仍未合格。新增历史定向分析session34509已exit0，全40002/80003点及尾点、前后完整metadata/5part hash/shape重绑通过。ROOT以Fraction另核52个保存词元帧的点代数；这些是诊断证据，不授参考资格。见[共模约束复核与单变量协议](experiments/c1_commonmode_constraint_followup_20261116.json)。

已观测初值的无驱动模式、瞬时打印量化不足以单独解释，隐藏内部根因未证。新排序协议仅准备，尚无新native/候选；原FAIL保留，完成仍9。113源码及依赖不变，既有1300含slow本轮未重跑。

2026-11-16当前：完整开环参考双h数值未合格。两次PSCAD均编译0错误、Run一次、正常quit且自有进程清空；45通道完整40002/80003点及尾点双路复核一致。共模硬门峰值10.838/37.498µV超过2µV；其余逐点门和全部跨h比较通过，条件rail因前提失败仅作诊断。见[完整双步长诊断记录](experiments/c1_full_openloop_dual_h_diagnostic_20261116.json)。

原v1元数据准入FAIL与v3报告工具失败均保留；新政策仅精确重构唯一RunTime注释，模型和数值门不变。无教学候选或新增完成数；113源码/依赖未改，1300既有全量本轮未重跑。

2026-11-16当前：完整模型编译0错误，整体Build-only准入FAIL，Run0。独立核45真实通道/19支路和79项非OUT归档；两处PGB分类修正仅取得collector重演证据，新版常量/缓存语法已获范围独审，正式Run准入尚未封定。以上不能作为完整商业数值资格。113源码/依赖未变，既有1300含slow本轮未重跑，新增完成9保持。

见[本轮完整构建记录](experiments/c1_full_openloop_build_attempt_20261116.json)。以下保留各阶段历史。

2026-11-16：完整开环前验协议已固定，见[完整开环协议记录](experiments/c1_full_openloop_protocol_20261116.json)。独立40项协议审查、新kernel48项纯检查、10项定向独审与128个Schur转移对照分别通过；这些范围重叠，不相加为项目测试数量。未执行新完整原生Build/Run或候选，实际新100µs控制链与双h数值资格NOT_OBSERVED。原400µs短探针PASS/新增9/既有1300回归保持；F1无新观察。

2026-11-16：完整开环目前只有研究草案。311项codec及静态接线检查通过；独立内部控制检查覆盖40002/80003点的施加门极，不能当作45通道商业输出。误差预算建议尚未冻结，新100µs原生采样/完整双步长参考/候选均未资格。见[完整开环准备记录](experiments/c1_full_openloop_preparation_20261116.json)。原短探针PASS、新增9项和既有1300项回归保持各自范围，F1无新观察。

2026-11-16：目标active。C1的400µs人工向量短探针已真实运行并通过双路数值检查：原生编译0错误、Run一次、正常quit，唯一会话63693已闭场，自有进程清空；实际映射551项及118项绑定复核全过。32通道全81点/80区间、原17预算和Vs/完整末位精度门均通过。只取得短探针数值资格，完整SPWM开环VSC、闭环和新候选尚未验收；新增完成数仍9，C1仍in_progress，D1/F1范围保持。113源码与依赖未变，1300含slow为既有回归，本轮未重测。研究工具、原始波形与图留忽略目录，教学继续复用现有元件和CaseDefinition链，保持精简可读。

见[本轮短探针记录](experiments/c1_force_dsout_bounded_numeric_20261116.json)。检查点为本记录前的63e5165；本轮实际提交/远端在结束检查点另核。已保存暂停/恢复历史和全部失败，以下旧状态不覆盖本段。

2026-11-12：已按用户要求暂停。当前保存到短时数值验证准备阶段：新合同和24文件运行包已固定，分析器与最终独审尚未完成；本轮未启动原生仿真、读取OUT或运行候选。最新已推送提交为63e5165；须待用户明确恢复后再继续。以下为最近已验证结果与后续计划。

2026-11-12。C1仍in_progress；新增19–27共9项本地/商业验收保持，跨OS单列F1。
本轮标准force_dsout直流测量链结构合格：原生build0、worker0正常退出，生成读取→传递→ownPGB均在MainOut；独立517深门及108绑定重核全过。
完整Map32/DATAStruct34、全11参数/端口/实例、4I和15Vm新鲜度、19分支/源物理及存储守卫均通过；STOF45→46，其他36维度不变。
ROOT另核23包件/70归档及3份完整源语义。会话81982已闭场，自有进程清空、环境不变。
本轮无Run/OUT、数值NOT_OBSERVED；短探针数值及完整开环尚未合格。下一步另冻执行合同及两路数值分析器。
113源码/依赖未改，复用既有1300含slow和锁定/Ruff/mypy39，本轮未重测。
C1其余控制链及D1待办，F1外部CI恢复待补。见[本轮构建记录](experiments/c1_force_dsout_build_only_20261112.json)。

| 对象 | 内部证据 | 外部参考 | 正式状态 |
|---|---|---|---|
| 既有11 PLL（C1子步骤） | 原111源不变，33专项/1300全量、独立默认Agg一致 | 完整真实参考/三窗九项/243快照与独立复算通过 | 既有11补验证完成；C1全链仍进行中 |
| 基线a03a450 | 1118测试含slow、14原有例通过 | 旧文档不等于本次商业对标 | 能力重评完成 |
| 级联RC探针 | 独立expm、KCL、TR/BE收敛通过 | 不冒称商业参考 | 研究探针完成 |
| 新增19级联RC | 分段矩阵指数、KCL/能量、TR/BE细化；独立执行通过 | 官方R2025a，真实10052样本；16个窗×信号均通过 | 已完成290a8ea |
| 既有02 RC | 原解析测试保留 | 官方参数适配、真实5013样本，电压/电流双限值均通过 | 补验证完成68f2f8a；不计新增 |
| 新增20七电阻双源 | Fraction精确解、逐节点KCL、功率；独立执行通过 | 官方v2.2.2/R2025a，101样本14信号全过；禁用未接万用表，主网不变 | 已完成d481c57 |
| 新增21接地/浮动中性点 | 解析星点/KCL/功率、两求解/积分配置、事件/非法输入11项 | 官方真实1001样本；39窗×信号均过；原错标签证据保留 | 已完成5c595e2 |
| 既有12补PSCAD参考（B1） | 原12/核心未改；23专项、1267全量及独立Agg40001点通过 | 完整参考/300输入资格、候选固定比较、340快照与独审均PASS | 已完成40bef297；原MathWorks2% FAIL保留 |
| 新增22有限T梯级 | 3761a21先固定判据；101物理状态增广expm/ABCD/KCL/能量/TR/BE共8项通过；独立Agg通过 | 原50T零初值；10/5ps参考细化及六量真实比较均通过，最大8.01mV/0.160mA | 已完成80ba91c |
| 新增23线性T等效 | 0ec7239先固定协议；独立两状态谱指数/KCL/能量/显式事件/TR细化8项通过，独立Agg8001点 | 原完整五网络真实8063/16042点自细化PASS，七量两窗全过，最大0.697mV/0.304mA | 已完成A4a `91dbad6bb77af24d1a548a6d0943930c4bcce40f`；三相/其余组合未推广 |
| 新增24三相Y–Δ–Y链 | 9项精确启动/连续插值/KCL/功率/能量/TR/RMS/相位通过，独立Agg100001点；全量1179 passed490.61s含slow | 原完整58899/76502点自细化38项通过；最终商业两窗19量38项通过，初次1µs绝对FAIL保留 | 已完成02044768579ba083d1fb526786922e770cc2e7c6；不含线路/其他组别/零序/饱和，跨OS CI另待验 |
| 新增25完整供电网络 | 11项独立节点/12初值/14量PWL/KCL/14损耗/双能量/TR/RMS/PQ/相位，Agg5001点；完整1190 passed478.96s含slow | 原完整5023/10023点，28self+56独立精度全过；14量两窗28商业比较全过，maxV0.864127V/maxI0.00623452A/maxNR1.74756e−6 | 已完成9e2513dd98c12ee4f50d94261318ef56fd475aa4；首次守卫失败保留，跨OS CI单列 |
| 新增26同步Buck | 12物理+21参考+13比较工具测试/独立Agg；26验收时全量1236 passed478.786s含slow，锁定/Ruff/mypy通过 | 25/12.5ns真实406263/809567点，两窗及全部500周期自细化PASS；首个50ns候选报告及独立原始数据/输入/周期/两窗复核PASS | 已完成9269350887a867aee2740fed04155ade8f8757be；26阶段正式新增8，限冻结同步控制/事件与二极管不活动域 |
| 新增27有限R Bergeron | 8项独立行波/KCL/KVL/能量/细化测试、独立Agg6001点；完整1244 passed469.79s含slow、109源码hash未变，锁定/Ruff/mypy通过 | 真实PSCAD 6001/12001点参考先过16自细化；四量双完整窗八项全过，maxV5.92e-12V/maxI5.16e-14A；153输入/原始数据/图双独审通过 | 已完成ae9fe3629ad9617853979b0ef58d4d8319239592，正式新增9；限常参数集总损耗近似，隐藏缓冲未直接导出，跨OS另记F1 |
| PSCAD cookbook | 工程XML已检查 | v4.6.0，无实跑数值 | inspected |

以下保留各阶段历史；较早“资源不足/未比较/未启动”不覆盖上述当前状态。

到20的本地稳定Python3.14.5完整回归：1133 passed，154.47 s；Ruff/mypy通过。原14例及新增19/20均单独执行通过。

到21的最新本地完整回归：**1144 passed，158.14 s**（含slow）；Ruff/mypy通过。21独立Agg运行也通过，当前共有17个教学脚本。

B1工具加入10项数学/失败测试后的完整回归：**1154 passed，144.24 s**（含slow），Ruff/mypy通过。此前默认沙箱Temp权限导致46项fixture建立目录失败；使用新的仓库内basetemp全量重跑全部通过。该结果属于软件测试，不把12的真实波形FAIL改为通过。`8a65b6e` 的 [独立CI](https://github.com/yu-yikai/PyCy_EMT_Lite/actions/runs/41805586718) 已在Ubuntu/Windows全部成功；精简证据见experiments/ci_8a65b6e.json。该HEAD不覆盖之后新增的22代码。

到22的最终本地全量（含slow）：**1162 passed，412.17 s**；Ruff/mypy通过。18个教学脚本均已独立运行；22专项8项耗时339.16s。`80ba91c`代码已正常推送，尚未观察到其CI run，不借用8a结果。必要阶段文档将正常push以对同一代码的新HEAD做完整双平台验证。

`68f2f8a` 的 [GitHub Actions](https://github.com/yu-yikai/PyCy_EMT_Lite/actions/runs/41799220935) 已实际success，Ubuntu/Windows两job全部成功，含全量/slow/coverage、全部例、构建、安装wheel与生成文件检查。该旧HEAD证据不覆盖20/21。

`5c595e2` 的 [GitHub Actions](https://github.com/yu-yikai/PyCy_EMT_Lite/actions/runs/41801829262) 已实际success，Ubuntu/Windows的全部步骤成功，覆盖新增19/20/21和既有02补验证的代码。可提交的精简证据为 `experiments/ci_5c595e2.json`；原始run/jobs JSON在 `.tmp/longterm/ci/`。job日志下载实际返回403，未从元数据推测远端测试数量；1144是本地实测数量。

各例完整数值报告在 `validation/cases/*/validation_report.json`；商业模型、波形与图/日志在local_reference，默认不提交。报告包含来源/软件、原模型/raw/normalized/候选hash、固定阈值、绝对时间和输入快照。网络已用系统现有代理恢复正常push；后续HEAD需单独记录CI，不能把本次证据扩大到未测试代码。

2026-11-06到23的本地最终全量：**1170 passed，384.08 s**（含slow），锁定离线同步27包、Ruff全范围、mypy39源码文件通过。日志`.tmp/longterm/a4-closeout-pytest.log`/`a4-closeout-tests.xml`；23独立执行日志`a4-closeout-standalone.log`。正式报告run20261106T025650374531Z，两窗×七量全部通过，SHA a64c0677349799eb0f3b7874b6cbedba071fd07c3e0498cc6933bc48ee71c0bc。

`90b2fcd`的[真实CI](https://github.com/yu-yikai/PyCy_EMT_Lite/actions/runs/41809969999)两系统全步骤success，在线复核日期2026-11-06；与80ba91c同代码，因此补齐22的跨操作系统验收。证据experiments/ci_90b2fcd.json，公开job日志403，远端测试数量未知。该旧HEAD不覆盖23；23在正常push后的精确HEAD另行等待CI，不把本地通过改称远端通过。

2026-11-06最新远端e51c1f1的[CI run42154476032](https://github.com/yu-yikai/PyCy_EMT_Lite/actions/runs/42154476032)实际终态failure，但两job均未获runner、steps为空，check-run注释明确“The job was not started because your account is locked due to a billing issue.”，没有运行软件测试。证据experiments/ci_e51c1f1.json及归档annotations；远端测试数null。23商业平台数值比较和本地回归通过保持原结论，23跨OS CI仍待账户解锁后补验；不能以旧90b2fcd替代。

2026-11-06 A4b候选：8项独立物理测试、Agg50001点、锁定同步/Ruff/mypy通过；新增后完整1178 passed474.63 s（含slow）。严格原ode15s资源中止，极小AbsTol的daessc短探针也出现最小步长停滞；两Abs1e-8短probe和自细化通过。参考配置补充926138d在正式full/候选商业比较前提交，固定19量/两窗/双限值及参考十分之一误差预算不变。正式50ms参考与候选商业验收仍待完成，正式新增仍5。

2026-11-06到24最终：1179 passed490.61s（XML490.603，含slow），日志.tmp/longterm/a4b-final-full-pytest.log、a4b-final-full-tests.xml。锁定同步27包、Ruff全范围、mypy39通过，九专项76.926s、独立Agg100001点。最终真实比较run20261106T041603177270Z全部38项PASS，maxLV20.17655V/HV205.91860V/源电流119.38782µA/maxNR.000246239，图/输入/hash独立审计均完成，提交0204476。原始资源中止/最小步长/guard/1µs商业FAIL均保留，未降低窗口/限值。正式新增6；A4当前23/24范围完成，真实线路组合后置D0，F1新HEAD跨OS状态单独记录。

2026-11-06本批已正常push到1423c7d6dfbca10547cf856dc20faa5dadf935dc。一次有界公开API观察确认最新CI run42162705728终态failure：Windows127711904930/Ubuntu127711905228均runner_id=0、steps=[]，各自注释明确账户billing lock，未执行任何测试，远端test_count=null。证据experiments/ci_1423c7d.json，7份raw响应/hash全核；网络观察及所有本轮监控已终态。23/24跨OS仍未验证，F1局部受阻不改变本地1179/商业数值PASS。继续D0参考先行，不通过代码或空提交绕账单锁。

2026-11-06 D0默认参考探针run20261106T044524416Z：真实R2025a Update1运行原power_gui50ms，219点/12动态状态，ode23tb、7.2005767s；监测exit0、Dirty off、原SLX SHA不变。12实际初值与native analysis x0完全相同且全非零；原始MAT、CSV、状态名/A/B/C/D与netlist保留。没有Scope输出；目前仅runnable，尚无精化、候选、商业比较或第7项正式交付。本轮仅研究与文档，1179全量结果仍属于此前已通过且未改变的代码，不记作重新执行。

D0独立物理核验：17支路参数最大相对差6.994e-14，12状态相量3.839e-13、6输出1.097e-13；T接点/方向与原生导数行一致。最终74项库存hash由主审全核，入口evidence_inventory_final.json（9297e7ef…）；旧库存保留其并行收尾前两项身份。相量一致性不代替尚未完成的时间域精化与候选验证。

2026-11-06 D0研究检查点已提交54374d5d9caf480d765b18faacea763054304f27。主审复核catalog22项中的86个SHA及最终库存74项全部通过，旧21项资源记录未改；任务依赖/JSON/19处本地文档链接和Git whitespace检查通过。仅文档/研究证据，无候选和代码/依赖变动，未重复1179全量。所有本轮native/提取/审查已终态，无后台任务；下一步冻结D0实现前协议，再细化参考并开发。正常推送及实际远端HEAD在执行末核对，23/24跨OS仍按最近一次真实CI账单锁失败记录，不以本次文档提交声称补验。


2026-11-06最新到25：1190 passed478.96s（XML478.948，含slow，1190/0fail/0error/0skip），锁定27包、全Ruff、mypy39及两个新入口通过。11专项6.63s，真实run20261106T054356596388Z的28项双限值通过；完整报告/图/hash及guard436c266的缓存说明见[25指南](../../validation/cases/source_line_transformer/README.md)。正式完成新增共7项。9e2513d已正常推送且实际远端一致，新CI正在有界观察；最近已实查1423c7d仍为billing lock启动前失败，不能把本地/商业PASS称作跨OS通过。


2026-11-06最新9e2513d代码里程碑已正常推送；[CI run42170878293](https://github.com/yu-yikai/PyCy_EMT_Lite/actions/runs/42170878293)已实查终态failure，Ubuntu127738145863/Windows127738146164均runner0、steps空，各注释确认GitHub账户billing lock，未执行测试/test_count=null。证据experiments/ci_9e2513d.json，7份raw响应/hash全核。F1局部受阻，23/24/25跨OS仍待账户外部恢复，不扩大本地/商业PASS结论；同终态不继续轮询。当前只做文档同步，代码/依赖与9e2513d一致，所有本轮监测已终态。

2026-11-09：参考自身失败完整报告见[initial_reference_failure.json](../../validation/cases/synchronous_buck/initial_reference_failure.json)；更细配置见[补充协议](../../validation/cases/synchronous_buck/reference_solver_addendum.md)。恢复后的13项参考数学测试、锁定/Ruff/mypy和独立Agg已实际执行；1190全量仍是25阶段结果，不称本轮已重跑。

2026-11-09最终本地全量：**1223 passed，475.864s（XML，含slow）**，零失败/错误/跳过；日志/XML .tmp/longterm/b2-final-20261109.*。原始点/配对两项校验修复后已完整重跑，锁定/Ruff/mypy及独立Agg通过。这是内部软件证据，Buck真实参考自身FAIL保持，PSCAD未build，跨OS尚待新HEAD实查。

2026-11-09远端精确候选41a6685：[run42576654146](https://github.com/yu-yikai/PyCy_EMT_Lite/actions/runs/42576654146)已核终态failure；Ubuntu129025769158/Windows129025769665均未获runner/steps空，注释仍为账户billing lock，远端test_count=null。软件代码没有在CI执行，不能推断测试失败或跨OS通过；7份raw/hash及精简JSON已保存。1223是本地实测。

B1原2%波形FAIL保持；本轮结构重建六路真实门极全40001点一致，±0.8V/实际二极管/1uS+BE差异已获得新代数证据，但默认12未改、未跑候选或新商业比较，仍未验收。见[时序补充](experiments/spwm_timing_followup.md)。

2026-11-09后续研究：PSCAD官方vdiv原参数0.2s/50µs实跑完成，16正常build消息/零警错，实际EMTDC链接/运行；PlotType0无磁盘波形，有限R仍未验收，详见experiments/pscad_toolchain_smoke.json。B1独立四因素16组合及24顺序审计确认门极为主影响，原12/2% FAIL不变；观测器件残差不算预测器件模型。本轮无生产源码/测试/依赖变化，1223是前次最终代码实测，不机械重跑。

2026-11-09 A3设计检查：15项物理库存、8输入、8 API输入、所有组件codec/端口、精确首个平台/DC及名义稳定性已独立复核。prepared目录5项库存与5引用全核，2.7181GiB<3GiB，native/builder/sim均未执行，有限R参考仍inspected/无数值验收；详见[设计](experiments/bergeron_reference_design.md)。B2 callback审计11产物/37输入和235记录保存，但无语义等价/内存增益实测。本轮仅研究文档，无生产/test/依赖修改，沿用前次1223实测而不称新回归。

2026-11-09 B1[同数学短探针设计](experiments/spwm_matched_reference_design.md)完成静态来源/控制/codec审查；独立核三库存26/39/29文件及全部输入，审计manifest SHA105b1a9dba0e14f042d97aa12797b937a055d0e7648732def247a962a77bd1d5。没有原生建模、波形、新商业比较或完整协议，原MathWorks2%波形FAIL和完成数7保持。A3 profile_guard_v2的9种exists/hash守卫用例通过，其他运行/物理逻辑不变；08:22UTC资源约2.282GiB<3GiB，driver未调用。本轮只新增研究说明与证据索引，没有生产/教学/测试/依赖改动；1223仍是41a6685代码的既有全量实测，不宣称重跑或新跨OS通过。

B1最终未执行builder SHAe93e70ab…，69/31/46图已独立核；40001原固定网格ref/carrier/门极及R值、保持/观察步号零差，仅为条件算术。新增builder/独立审阅库存5/7项主审全核，manifest分别9f101941…/00c212fb…；真实原生拓扑、时间、源、有效R和TR初始化仍待，无B1运行器。上述脚本均忽略且不进入教学执行路径。
