# Scope日志API勘误

2026-11-06，原协议先行提交`167bb493c1405cd4edd4eaadd1b4cf2e0ad257a0`之后。
首个baseline尝试`20261106T070625609Z`在sim调用前退出1：
`SimulationInput.setBlockParameter(path,name,value)`每次只接受一个块参数，原导出器把Scope点数限制和decimation两对值放在一次调用中。
现拆成两次调用；仍仅配置原有三个Scope的完整数据保存。

原模型、物理/控制/solver、三个协议文件、比较窗及全部限值不变。
新导出器同时保存本勘误，完成记录字段改为`candidate_created_by_exporter=false`，仅描述导出器本身没有创建候选，允许独立开发并行进行。
失败没有执行仿真，也没有in/out MAT；原SLX、脚本和三协议快照、日志、资源/终态记录完整保留，不能算数值FAIL或成功参考。
新baseline必须使用新的独立目录；不覆盖旧失败，不重复任何仍在运行的进程。

证据位于`local_reference/b2_protocol_research/native_refinement/20261106T064932434Z/runs/20261106T070625609Z-baseline/`。
该次11项清单SHA-256为`594a9093fcd68e25b587253832f0b0cb96d217cf6edfb9b97e26cfafaf70ce15`；原SLX仍为`ea8344f62e2a691456363f0391389cd1675bfe246bd71dc8f15a3b838ca6ab42`。
