# 恢复与下一步

1. 读取 tasks.json、progress.md、validation_status.md、decisions.md，并核对 `git status --short`、分支、HEAD、远端，保留用户工作。
2. 在 `codex/emt-examples-longterm` 恢复。用 `git log --oneline` 与tasks的commit交叉核对；JSON的checkpoint是最近已提交检查点，不可能自引用当前提交hash。
3. 稳定环境：PowerShell设 `UV_CACHE_DIR=$PWD/.uv-cache`、`UV_PYTHON_INSTALL_DIR=$PWD/.uv-python`、`UV_PROJECT_ENVIRONMENT=$PWD/.tmp/venv-py3145`、`UV_PYTHON_DOWNLOADS=never`，执行 `uv sync --locked --offline --python .uv-python/cpython-3.14.5-windows-x86_64-none/python.exe`。跨机器改用正常 `uv sync --locked`。
4. 先完成规划提交与推送，再提交独立比较工具。实现19级联RC、运行已有官方数据对比，保存报告/图与自动测试；没有真实通过结果不得改completed。
5. 参考复现：MATLAB `addpath('validation/cases/cascaded_rc'); export_reference(pwd)`。受限环境需正常许可服务权限；不要上传第三方.slx或原始波形。
6. 补既有RC验证，随后按04优先寻找Bergeron/不平衡负荷可运行参考；12/SPWM先研究模型差异。继续所有不依赖受阻软件的任务。

本文件将在当前批次结束前更新为具体最新命令与未完成事项；不会在无执行环境时声称后台继续。
