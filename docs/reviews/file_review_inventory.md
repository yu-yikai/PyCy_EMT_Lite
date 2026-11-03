# 本轮逐文件审查清单

日期：2026-11-03；生产基线：6b5d206fced1cec48d8f2298f794942b24d108cd。

本清单覆盖 Git 跟踪的全部88个文件。全文阅读由主审与三个分工交叉完成；历史记录和锁文件的针对性范围见表，不将执行或扫描等同于物理正确性证明。SHA-256对应审查时工作区原文件字节（CRLF可能与Git对象不同）。本轮新增审查文档不计入88文件。表中16个Python块指README与8份专题合计，CHANGELOG无Python块。

| 类别 | 数量 |
|---|---:|
| 工程配置/许可 | 5 |
| 当前文档 | 11 |
| 历史记录 | 1 |
| 算例 | 14 |
| 源码/类型标记 | 40 |
| 测试 | 16 |
| 生成锁文件 | 1 |

| 文件 | 类别 | 行数 | SHA-256 | 实际审查方式 |
|---|---|---:|---|---|
| [.github/workflows/ci.yml](../../.github/workflows/ci.yml) | 工程配置/许可 | 111 | 7f362d282899dd6dd704b5274d2c807f00b2030a6c87376ba1fea6605ab13bf4 | 全文检查 |
| [.gitignore](../../.gitignore) | 工程配置/许可 | 28 | 673192696586bea98c941fc5127fe88050dfa9e3634f82460ed1682eb068091c | 全文检查 |
| [.python-version](../../.python-version) | 工程配置/许可 | 1 | 73880611a18bf211ab229c2a2d93ec11a622693e79532c0b797b91fd056704dc | 全文检查 |
| [CHANGELOG.md](../../CHANGELOG.md) | 当前文档 | 18 | 8bd98a16eb841f14a3f0e629e264a24b8c7510900acf3d0c4ef7f6dad8bf970b | 全文分工核对；16个Python块运行、本地文件/锚点扫描、公式与中英对应 |
| [LICENSE](../../LICENSE) | 工程配置/许可 | 21 | 5885a844188e84f91378e02e7b371c4dadca808da0889dc136fc49e13b4afeec | 全文检查 |
| [README.md](../../README.md) | 当前文档 | 259 | 6c15f02948dcd248ce485c3305ff795c75396718120dcb138c30f202b4262ab6 | 全文分工核对；16个Python块运行、本地文件/锚点扫描、公式与中英对应 |
| [README.zh-CN.md](../../README.zh-CN.md) | 当前文档 | 259 | 07598e777ac373dc58e5e1fcaadd11ffdd02dc59001589bc26d1bcfc24ef24b3 | 全文分工核对；16个Python块运行、本地文件/锚点扫描、公式与中英对应 |
| [docs/audit_20261005/项目问题与改进计划.md](../../docs/audit_20261005/项目问题与改进计划.md) | 历史记录 | 1413 | df537497e4f99e2500375bc81a0977771c47e6c067603aa1c186315ae36cd766 | 针对性：原问题/交付状态/R0–R12/F0–F1/N0–N4/质量门禁；不重演全部历史实验 |
| [docs/component_derivations.en.md](../../docs/component_derivations.en.md) | 当前文档 | 988 | b0370b6d388dc86bbc4460ac9d2b0acf33ea6d6edc33e5bfcfceb93a3ed88f93 | 全文分工核对；16个Python块运行、本地文件/锚点扫描、公式与中英对应 |
| [docs/component_derivations.md](../../docs/component_derivations.md) | 当前文档 | 988 | 2a4be3e08b4175fe57c897a43cf395799465f799fcf55b0a2d819458143170c4 | 全文分工核对；16个Python块运行、本地文件/锚点扫描、公式与中英对应 |
| [docs/models_and_validation.en.md](../../docs/models_and_validation.en.md) | 当前文档 | 564 | 4c298fbc48f73bb46c089b7801494e777fb5514e36d9d8571a457b29af681a52 | 全文分工核对；16个Python块运行、本地文件/锚点扫描、公式与中英对应 |
| [docs/models_and_validation.md](../../docs/models_and_validation.md) | 当前文档 | 632 | 961550e98290319fd3567096de806b3d112e317bc6c877820415fe0fb4edb3d9 | 全文分工核对；16个Python块运行、本地文件/锚点扫描、公式与中英对应 |
| [docs/numerical_conventions.en.md](../../docs/numerical_conventions.en.md) | 当前文档 | 313 | 54abcee9b42ffdf081398ccccdaaaf9e72dd42bfd764729b2890b9669ff936fa | 全文分工核对；16个Python块运行、本地文件/锚点扫描、公式与中英对应 |
| [docs/numerical_conventions.md](../../docs/numerical_conventions.md) | 当前文档 | 293 | 04c93c93b3e85ba557d606de2e1f80bb4d84f1a52712707869c861f041e4bb27 | 全文分工核对；16个Python块运行、本地文件/锚点扫描、公式与中英对应 |
| [docs/three_terminal_vsc_hvdc.en.md](../../docs/three_terminal_vsc_hvdc.en.md) | 当前文档 | 378 | 247e51e8c9e1d293809c41e2f0530b578387b931b078069a0e76ee56e1354149 | 全文分工核对；16个Python块运行、本地文件/锚点扫描、公式与中英对应 |
| [docs/three_terminal_vsc_hvdc.md](../../docs/three_terminal_vsc_hvdc.md) | 当前文档 | 377 | 464665d0e873555572241ceccbe83f376ddfaaca299be0dcda596d258e040bff | 全文分工核对；16个Python块运行、本地文件/锚点扫描、公式与中英对应 |
| [examples/01_r_circuit.py](../../examples/01_r_circuit.py) | 算例 | 92 | a7c3149db2d834b89dc405ceefab8a89c8b2b5c7bbc2033981c76b67ffdad19b | 全文核对；默认模式Agg实际运行 |
| [examples/02_rc_transient.py](../../examples/02_rc_transient.py) | 算例 | 95 | 934694e40f73dcfcfed8c0ac2dbf0aee70249ef16db4be72b7994887a805d14c | 全文核对；默认模式Agg实际运行 |
| [examples/03_rl_transient.py](../../examples/03_rl_transient.py) | 算例 | 96 | 5dfa03b4881808b0340c3dcc22ef9475a3bfe69343b65a8949fd11cd055eb21c | 全文核对；默认模式Agg实际运行 |
| [examples/04_rlc_transient.py](../../examples/04_rlc_transient.py) | 算例 | 115 | 8f5aaa56d9f3e0b6bb38231134cc0cfce92443d617fb6245dc0e43a644644638 | 全文核对；默认模式Agg实际运行 |
| [examples/05_three_phase_steady_state.py](../../examples/05_three_phase_steady_state.py) | 算例 | 100 | 55a3060729a528a75776f2614a0ce2a30c980d972ae5f810b6fcb55d27e93270 | 全文核对；默认模式Agg实际运行 |
| [examples/06_three_phase_short_circuit.py](../../examples/06_three_phase_short_circuit.py) | 算例 | 124 | 32085ee93c5e292ef6b1f2ff8c12cabebfabb298cdf2278229b3433a21307c58 | 全文核对；默认模式Agg实际运行 |
| [examples/07_single_phase_ground_fault.py](../../examples/07_single_phase_ground_fault.py) | 算例 | 89 | 6f8d8cd124fc117d1834360fd5e704253a308c835830e8d70e797aa4af4c420f | 全文核对；默认模式Agg实际运行 |
| [examples/08_pi_line_transient.py](../../examples/08_pi_line_transient.py) | 算例 | 126 | 5efac188ad9113846eaddc5290cd43da78f9835262d72da14da3c71493574664 | 全文核对；默认模式Agg实际运行 |
| [examples/09_single_phase_transformer.py](../../examples/09_single_phase_transformer.py) | 算例 | 145 | a8f16fd1b009c05f4af1c106ae7a6e3048ded1a5f672ab0cdd7874488aa6ff39 | 全文核对；默认模式Agg实际运行 |
| [examples/10_park_generator_avr_governor.py](../../examples/10_park_generator_avr_governor.py) | 算例 | 167 | 5ab016c863961829e56d21312522c75403b9b0be9930f0e387c4f01e3f10ed2d | 全文核对；默认模式Agg实际运行 |
| [examples/11_pll_dynamic_response.py](../../examples/11_pll_dynamic_response.py) | 算例 | 79 | 7d0fd1ccf9d4af6a3123c6208e4607cead19ce38804490ea2d9d7ab98d1b2647 | 全文核对；默认模式Agg实际运行 |
| [examples/12_two_level_pwm_generator.py](../../examples/12_two_level_pwm_generator.py) | 算例 | 171 | 5592d8620d09985c57e67b5a28d55cc2bbfcf9d7ff3f9ec9c8a06713ebe7c917 | 全文核对；默认模式Agg实际运行 |
| [examples/17_single_phase_ac_rlc.py](../../examples/17_single_phase_ac_rlc.py) | 算例 | 106 | 2396190231501645ff2dad0ae2cdf43e4ee547020421b1a3a13912ad2bb3fd0c | 全文核对；默认模式Agg实际运行 |
| [examples/18_three_terminal_vsc_hvdc.py](../../examples/18_three_terminal_vsc_hvdc.py) | 算例 | 297 | 83763aff5ab2a7f4f6ce1086a3c11438a6d0339c5a803dd59d77c77f86ff76a6 | 全文核对；默认模式Agg实际运行 |
| [pycy_emt_lite/__init__.py](../../pycy_emt_lite/__init__.py) | 源码/类型标记 | 65 | 81980a448c4506c4a373d308339c490967a02938c2cb0f0f33a1360dec21d46e | 逐文件全文与相关方程/接口核对（py.typed为空标记） |
| [pycy_emt_lite/analysis/__init__.py](../../pycy_emt_lite/analysis/__init__.py) | 源码/类型标记 | 25 | 20f635eec36432d84d6bf2ed666ecf45230962c7b4aa875838a2b9a65c5aa8a0 | 逐文件全文与相关方程/接口核对（py.typed为空标记） |
| [pycy_emt_lite/analysis/metrics.py](../../pycy_emt_lite/analysis/metrics.py) | 源码/类型标记 | 310 | 14407925b79d9c3ea98c1cf3e4f9208f7820a22a862d70e067632f301aa9b143 | 逐文件全文与相关方程/接口核对（py.typed为空标记） |
| [pycy_emt_lite/cases.py](../../pycy_emt_lite/cases.py) | 源码/类型标记 | 171 | f6c710cbbf2306752bd2345c1f5fc9a8d74b6738f30dd15fcfeb4452a192e986 | 逐文件全文与相关方程/接口核对（py.typed为空标记） |
| [pycy_emt_lite/components/__init__.py](../../pycy_emt_lite/components/__init__.py) | 源码/类型标记 | 54 | 7cdac999206ef73c505ae8f29d9b531355d79bca9dcba02dd6f2c1b332ab4801 | 逐文件全文与相关方程/接口核对（py.typed为空标记） |
| [pycy_emt_lite/components/base.py](../../pycy_emt_lite/components/base.py) | 源码/类型标记 | 93 | 0c005f4f00d5313c04f4be19c4c776ac9893fb50defb066fa6f5819f4b0de463 | 逐文件全文与相关方程/接口核对（py.typed为空标记） |
| [pycy_emt_lite/components/basic.py](../../pycy_emt_lite/components/basic.py) | 源码/类型标记 | 377 | b2a092b07a15a1145cc582c47b1df6f6124d65c972f46b9450faa8c0acb5cc0b | 逐文件全文与相关方程/接口核对（py.typed为空标记） |
| [pycy_emt_lite/components/lines.py](../../pycy_emt_lite/components/lines.py) | 源码/类型标记 | 663 | dd4a0e5d4ee71ef7a655e31064c002536ea994aa185c0e6a47398d1cbac8c74b | 逐文件全文与相关方程/接口核对（py.typed为空标记） |
| [pycy_emt_lite/components/power_electronics.py](../../pycy_emt_lite/components/power_electronics.py) | 源码/类型标记 | 84 | 10cf178bc907259a21d6b52726766c61210329f5f3b4e8539d835ac06ad369bb | 逐文件全文与相关方程/接口核对（py.typed为空标记） |
| [pycy_emt_lite/components/switching.py](../../pycy_emt_lite/components/switching.py) | 源码/类型标记 | 113 | d152666951ea6104eab19f37e5b042744188f1b3f3662535e67188a3467a8658 | 逐文件全文与相关方程/接口核对（py.typed为空标记） |
| [pycy_emt_lite/components/three_phase.py](../../pycy_emt_lite/components/three_phase.py) | 源码/类型标记 | 533 | 9cddd858ba4d27572218dc3a6790b8aa92ac0b71c703c9b7ddec82ddcd60c025 | 逐文件全文与相关方程/接口核对（py.typed为空标记） |
| [pycy_emt_lite/components/transformers.py](../../pycy_emt_lite/components/transformers.py) | 源码/类型标记 | 540 | 632617a185bb69441535bdff552f0b4473566d64f6a78211622962cbb3d66609 | 逐文件全文与相关方程/接口核对（py.typed为空标记） |
| [pycy_emt_lite/controls/__init__.py](../../pycy_emt_lite/controls/__init__.py) | 源码/类型标记 | 48 | f9685f649e794aba54a8cec566390ee8e9a992b7baf41d7a592a74d12980a069 | 逐文件全文与相关方程/接口核对（py.typed为空标记） |
| [pycy_emt_lite/controls/blocks.py](../../pycy_emt_lite/controls/blocks.py) | 源码/类型标记 | 224 | e862509d8dceb31a1151ff710d4f861267e23e9dccd1843f98f774fb07684a7b | 逐文件全文与相关方程/接口核对（py.typed为空标记） |
| [pycy_emt_lite/controls/pll.py](../../pycy_emt_lite/controls/pll.py) | 源码/类型标记 | 135 | 7eca0fb9c6f6464bb36f82d7cad1b27be5bd1b6455b046b5ad3279c075a36efa | 逐文件全文与相关方程/接口核对（py.typed为空标记） |
| [pycy_emt_lite/controls/pwm.py](../../pycy_emt_lite/controls/pwm.py) | 源码/类型标记 | 48 | 6a2469d7957c74ce9ff25e13020541e7c169f38820538e8a71467919ce9391d1 | 逐文件全文与相关方程/接口核对（py.typed为空标记） |
| [pycy_emt_lite/controls/transforms.py](../../pycy_emt_lite/controls/transforms.py) | 源码/类型标记 | 78 | c48dbe02a1cd4b1c12a8fd29439038b76ada81d68f71f7b1183eec2bdc98ab99 | 逐文件全文与相关方程/接口核对（py.typed为空标记） |
| [pycy_emt_lite/controls/vsc.py](../../pycy_emt_lite/controls/vsc.py) | 源码/类型标记 | 174 | a932a3a1061b4200b5ce53d4d8d2cdf9d24f78d590cd78345690b9b738515972 | 逐文件全文与相关方程/接口核对（py.typed为空标记） |
| [pycy_emt_lite/converters/__init__.py](../../pycy_emt_lite/converters/__init__.py) | 源码/类型标记 | 5 | 9f94cc67b26700a8bf1f022c5c806b5e5415ecaf8743d36b2ddceddb6ec70ba6 | 逐文件全文与相关方程/接口核对（py.typed为空标记） |
| [pycy_emt_lite/converters/filters.py](../../pycy_emt_lite/converters/filters.py) | 源码/类型标记 | 143 | 11112e0bc233809fc37c3fcf39cce41dab692a704a711d113bff31aa450a6be2 | 逐文件全文与相关方程/接口核对（py.typed为空标记） |
| [pycy_emt_lite/core/__init__.py](../../pycy_emt_lite/core/__init__.py) | 源码/类型标记 | 5 | 3d0e3034e589c19e37746a909832f2b47780ea9793b011bb2bdf6141dd445ee5 | 逐文件全文与相关方程/接口核对（py.typed为空标记） |
| [pycy_emt_lite/core/circuit.py](../../pycy_emt_lite/core/circuit.py) | 源码/类型标记 | 159 | ee628295a1477c334d66e366ed594f8b824ca66ce36e8c17980972a7f485b0ac | 逐文件全文与相关方程/接口核对（py.typed为空标记） |
| [pycy_emt_lite/core/context.py](../../pycy_emt_lite/core/context.py) | 源码/类型标记 | 35 | 9886feeb12b4c30e115f4ada5594c504cb196ecdb491699a2b7a89fa16902c4e | 逐文件全文与相关方程/接口核对（py.typed为空标记） |
| [pycy_emt_lite/core/nodes.py](../../pycy_emt_lite/core/nodes.py) | 源码/类型标记 | 76 | 71167de688ff341bf99f6fb0beedd05946db4d83eeb9301a387a021ca6f0cffd | 逐文件全文与相关方程/接口核对（py.typed为空标记） |
| [pycy_emt_lite/core/simulation.py](../../pycy_emt_lite/core/simulation.py) | 源码/类型标记 | 634 | b6fdb849172830cff51bfa31af87028524072adabaeeda580ab02c4e4751087d | 逐文件全文与相关方程/接口核对（py.typed为空标记） |
| [pycy_emt_lite/core/solvers.py](../../pycy_emt_lite/core/solvers.py) | 源码/类型标记 | 232 | 031f3d2f118d1d88f34d712bdeeb864ecc13a3fa7d89c7288b984b2b2c31571a | 逐文件全文与相关方程/接口核对（py.typed为空标记） |
| [pycy_emt_lite/core/stamping.py](../../pycy_emt_lite/core/stamping.py) | 源码/类型标记 | 151 | 9f23c65cbaa7d33ea0406bd0d33fe3b5fd007192fd60dbe78399586a35f02f87 | 逐文件全文与相关方程/接口核对（py.typed为空标记） |
| [pycy_emt_lite/core/variables.py](../../pycy_emt_lite/core/variables.py) | 源码/类型标记 | 40 | 6567e110c6b1aedc7faf713ae05d3297b5f70cca98ebf4bc28fcb2f7d05ea0b8 | 逐文件全文与相关方程/接口核对（py.typed为空标记） |
| [pycy_emt_lite/events/__init__.py](../../pycy_emt_lite/events/__init__.py) | 源码/类型标记 | 18 | 5af09c087d751859ff97c6b4a01670312d5618aed864ea042fccf736d660c032 | 逐文件全文与相关方程/接口核对（py.typed为空标记） |
| [pycy_emt_lite/events/base.py](../../pycy_emt_lite/events/base.py) | 源码/类型标记 | 92 | 9cc671d975b5ea60780b29e7a11042f3b39f2bb93454dc2cc72bacfee4bb6663 | 逐文件全文与相关方程/接口核对（py.typed为空标记） |
| [pycy_emt_lite/events/standard.py](../../pycy_emt_lite/events/standard.py) | 源码/类型标记 | 131 | 638e17b7d7601cd901e96cec99c5238c330780e31711c3d5e92e06d56b32d46d | 逐文件全文与相关方程/接口核对（py.typed为空标记） |
| [pycy_emt_lite/io/__init__.py](../../pycy_emt_lite/io/__init__.py) | 源码/类型标记 | 5 | 1eaf1526eecf1d41982a3e2b6685b0a653c233e9b57546d437e1dc4ae582f93e | 逐文件全文与相关方程/接口核对（py.typed为空标记） |
| [pycy_emt_lite/io/results.py](../../pycy_emt_lite/io/results.py) | 源码/类型标记 | 251 | aa02511777508c2f048aae9d459dfd354d0e0d9b539a10af8f0684d66018a915 | 逐文件全文与相关方程/接口核对（py.typed为空标记） |
| [pycy_emt_lite/machines/__init__.py](../../pycy_emt_lite/machines/__init__.py) | 源码/类型标记 | 6 | 9f16d3bf2e00d27f4d8d1bacf35d8ef968f2f79dc5d758af581b04bd9f40232e | 逐文件全文与相关方程/接口核对（py.typed为空标记） |
| [pycy_emt_lite/machines/park_generator.py](../../pycy_emt_lite/machines/park_generator.py) | 源码/类型标记 | 305 | e1f5f5c3b26ab2aaab4db9234954c50913c7890135da4f933b0afc9202e43caa | 逐文件全文与相关方程/接口核对（py.typed为空标记） |
| [pycy_emt_lite/machines/synchronous.py](../../pycy_emt_lite/machines/synchronous.py) | 源码/类型标记 | 275 | a6add8058a9788daba21a1dfac986bef6e4a4c698ec4f8e21fdcb07e1426b06f | 逐文件全文与相关方程/接口核对（py.typed为空标记） |
| [pycy_emt_lite/py.typed](../../pycy_emt_lite/py.typed) | 源码/类型标记 | 0 | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 | 逐文件全文与相关方程/接口核对（py.typed为空标记） |
| [pycy_emt_lite/visualization/__init__.py](../../pycy_emt_lite/visualization/__init__.py) | 源码/类型标记 | 11 | 23a5988f06bd7d833a9d7a0358a55a3d6a57ed96f5e1812c178c0d8ae29267ea | 逐文件全文与相关方程/接口核对（py.typed为空标记） |
| [pycy_emt_lite/visualization/plotting.py](../../pycy_emt_lite/visualization/plotting.py) | 源码/类型标记 | 198 | 6645d31b1c6ae11be45f5652f222a36576dab075c336788d25d15a788c64e346 | 逐文件全文与相关方程/接口核对（py.typed为空标记） |
| [pycy_emt_lite/visualization/reporting.py](../../pycy_emt_lite/visualization/reporting.py) | 源码/类型标记 | 107 | 5ae8a1642303cef26f6c425c36eb49256b318d9773f9bbeb792ca8bcded264d0 | 逐文件全文与相关方程/接口核对（py.typed为空标记） |
| [pyproject.toml](../../pyproject.toml) | 工程配置/许可 | 76 | f32f1496a4e4beb93b9cd3ec318871611b68e1d9765c69b081aed4e9326f5672 | 全文检查 |
| [tests/test_analysis.py](../../tests/test_analysis.py) | 测试 | 297 | 0b48eb7f3805badcc8ea6d09dea1f04b1966d997a4bb49c11d20a049e71e1443 | 全文核对断言、参考来源、参数化与辨识能力；全量执行 |
| [tests/test_basic_components.py](../../tests/test_basic_components.py) | 测试 | 493 | 9e4feb235d53f1079873f2665fb862a95eddb67130b8bd9e4cd9024cbfa3af82 | 全文核对断言、参考来源、参数化与辨识能力；全量执行 |
| [tests/test_controls.py](../../tests/test_controls.py) | 测试 | 384 | 263d2b60a1537d6e3b2fcd09790e39f2be37a9a0f7a21b4bace48ec990e7698d | 全文核对断言、参考来源、参数化与辨识能力；全量执行 |
| [tests/test_events.py](../../tests/test_events.py) | 测试 | 309 | 3bf2326cf18b77e3fad986502d33591553ec0528c1342565e3455a690cbd210f | 全文核对断言、参考来源、参数化与辨识能力；全量执行 |
| [tests/test_line_models.py](../../tests/test_line_models.py) | 测试 | 481 | 36f3136eee6fd59b5cac3351336b62d96676a650d8f1f39126604cbfe73df1f9 | 全文核对断言、参考来源、参数化与辨识能力；全量执行 |
| [tests/test_park_synchronous_generator.py](../../tests/test_park_synchronous_generator.py) | 测试 | 316 | 81b48a814627c9fe320e65e8f3665f9b556b48523b777f3d0f770612f84c5ddc | 全文核对断言、参考来源、参数化与辨识能力；全量执行 |
| [tests/test_power_electronics.py](../../tests/test_power_electronics.py) | 测试 | 378 | c0b2962a41fa3ff060d1ae34cf9931be9c7472a9a3a9a4d0a17dadb1a24a3e7a | 全文核对断言、参考来源、参数化与辨识能力；全量执行 |
| [tests/test_results_io.py](../../tests/test_results_io.py) | 测试 | 172 | 6fd8ad540861642bfb9b82f452633992d9458ad2ade9f473fee521205362b6c3 | 全文核对断言、参考来源、参数化与辨识能力；全量执行 |
| [tests/test_solvers.py](../../tests/test_solvers.py) | 测试 | 740 | b21d925fa2c4bbf4b1e3e41828927eca2e1301a10fe2e78eb30edc0ff1ebf1ef | 全文核对断言、参考来源、参数化与辨识能力；全量执行 |
| [tests/test_step_callback.py](../../tests/test_step_callback.py) | 测试 | 76 | 39adcf9faabeb4820cdb9d95e2831760051f2871ff26070b361cf8f5b53c24fe | 全文核对断言、参考来源、参数化与辨识能力；全量执行 |
| [tests/test_synchronous_machine.py](../../tests/test_synchronous_machine.py) | 测试 | 173 | 2f2498c3c10aa8fb72f6dd6b585c2e6c62a87a4c5355c7d1f65ffd499b8a66cd | 全文核对断言、参考来源、参数化与辨识能力；全量执行 |
| [tests/test_three_phase.py](../../tests/test_three_phase.py) | 测试 | 359 | 861e24e07dcd8710408a33aadc8d0bc5e91baa2f52778a3b4a952a94f795cb8b | 全文核对断言、参考来源、参数化与辨识能力；全量执行 |
| [tests/test_three_terminal_vsc_hvdc.py](../../tests/test_three_terminal_vsc_hvdc.py) | 测试 | 337 | 4a8e3dca989b7104fae0b90ced0a6d34fd26c3a0058e0fbea69a775f5b505998 | 全文核对断言、参考来源、参数化与辨识能力；全量执行 |
| [tests/test_time_grid.py](../../tests/test_time_grid.py) | 测试 | 351 | 633cfb76049f1e3967093a9c576b318cff4c8a32f16dc0ebabcfd2c874bf6052 | 全文核对断言、参考来源、参数化与辨识能力；全量执行 |
| [tests/test_transformers.py](../../tests/test_transformers.py) | 测试 | 387 | 84427f491d86401f0a8d7e980286070dac7d15a9c1f672614f6726bd27c4003f | 全文核对断言、参考来源、参数化与辨识能力；全量执行 |
| [tests/test_visualization_reporting.py](../../tests/test_visualization_reporting.py) | 测试 | 202 | 961d4e2492926879125bb90266c004986cf8c1d871f1c02b554b658155103bda | 全文核对断言、参考来源、参数化与辨识能力；全量执行 |
| [uv.lock](../../uv.lock) | 生成锁文件 | 590 | 79769bb628c8191d5b36db63cff767062e0e5a65b253d41208a3568696e3b5d9 | 针对性：全部27包结构/版本/依赖/源/hash，locked同步；不逐个验证跨平台wheel |
