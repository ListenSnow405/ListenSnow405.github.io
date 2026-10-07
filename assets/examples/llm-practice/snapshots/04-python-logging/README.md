# Python 日志参数核验：官方资料摘录

这是写作侧于 2026-10-05（Asia/Shanghai，UTC+08:00）实际联网搜索、读取官方文档后整理的局部摘录，供离线复核。不是完整网页镜像，不是 Python 多版本运行测试，也不是读者的模型实验记录。行号 L1 等为本摘录内部定位，不能当作原网页物理行号。

问题：`logging.basicConfig` 的 `encoding` 参数何时加入；3.8 与 3.14 是否都适用；参数支持是否等于已有程序实际成功写出日志。

实际搜索词包括 `Python logging basicConfig encoding added 3.9`，搜索范围为 `docs.python.org`。搜索摘要用于找到文档，以下判断依据已打开的正文。

| 编号 | 原始来源与定位 | 读取状态 | 摘录 |
| --- | --- | --- | --- |
| O1 | [Python 3.14 logging：basicConfig](https://docs.python.org/3.14/library/logging.html#logging.basicConfig)，参数表、版本变更与函数前置说明 | 已读正文，核对日期 2026-10-05；版本路径为 3.14 | `O1-basicconfig.md` |
| O2 | [Python 3.9 Logging HOWTO：Logging to a file](https://docs.python.org/3.9/howto/logging.html#logging-to-a-file)，示例及紧邻的变更说明 | 已读正文，核对日期 2026-10-05；旧版页面仅用于历史核验 | `O2-howto.md` |
| O3 | [Python 3.8 logging：basicConfig](https://docs.python.org/3.8/library/logging.html#logging.basicConfig)，完整支持参数表与函数前置说明；[官方中文备用入口](https://docs.python.org/zh-cn/3.8/library/logging.html#logging.basicConfig) | 首次内置读取失败；2026-10-05 通过标准 HTTPS 取得英文正文，HTTP 200，并读取中文对应章节 | `O3-basicconfig.md` |

首次读取失败时，3.8 的判断只依据 O1/O2 的历史说明；恢复后已直接核对 O3 的完整参数表，没有 encoding 或 errors，与“3.9 加入”一致。首次失败、HTTP 响应与替代方式见 `access-recovery.md`。英文入口在原读取工具中仍失败，不声称该服务的内部实现已修复。旧版文档用于历史核验，不构成安装旧版的建议。

摘录分开标记短引、中文转述和结论。复查时打开原文，确认定位与适用条件仍一致；不要只核对 URL 存在。网页之后可能更新，本目录只记录上述核对日期下实际读到的局部内容。
