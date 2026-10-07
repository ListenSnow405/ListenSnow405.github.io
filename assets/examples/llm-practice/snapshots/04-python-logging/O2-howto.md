# O2：Python 3.9 Logging HOWTO 局部摘录

- 发布主体：Python 官方文档。
- 来源：https://docs.python.org/3.9/howto/logging.html#logging-to-a-file
- 适用版本路径：3.9；核对日期：2026-10-05，UTC+08:00。
- 读取状态：实际打开正文；旧版资料用于历史交叉核验。

L1【原文短引，示例紧邻的变更说明】：Changed in version 3.9: The encoding argument was added.

L2【中文转述，示例前置条件】：Logging to a file 一节要求在新启动的解释器中尝试示例，而不是继续之前的会话；示例使用 filename、encoding 与日志级别参数。

L3【中文转述，日志级别说明】：默认级别为 WARNING；是否输出某条消息还与日志级别有关。

L4【核验范围】：本摘录与 O1 的参数历史说明一致；网页示例属于文档证据，不是本文执行该示例的运行记录。
