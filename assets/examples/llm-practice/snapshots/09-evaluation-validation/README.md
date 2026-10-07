# D9 教学夹具与程序证据

- make_replay.py：人为构造固定响应、两次重复、token 数、时间和故障，生成 teaching-runs.json 与 ../../expected/09-gold.json；不是模型实验。
- teaching-runs.json：36 个任务及所有尝试，原文保留非法 JSON 与不存在定位；model=none。
- validate_evaluation.py：在独立临时副本实际运行验收，保持原输入；不读取密钥、不调用网络或模型。
- program-validation.json：Windows、Python 3.11.9 的 22 项实际程序验收。
- recalculated-report.json：实际重算的自动结果，人工复核 pending。

参考答案、教学夹具、评分输出及验证脚本均不进入无答案下载包。真实模型只获得本次输入、contract 和相应任务。教学开发/保留划分不构成真实盲测。
