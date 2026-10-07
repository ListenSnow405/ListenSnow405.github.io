# O1：Python 3.14 logging.basicConfig 局部摘录

- 发布主体：Python 官方文档。
- 来源：https://docs.python.org/3.14/library/logging.html#logging.basicConfig
- 适用版本路径：3.14；核对日期：2026-10-05，UTC+08:00。
- 读取状态：实际打开正文；本文件为手动整理的局部摘录。

L1【原文短引，版本变更说明】：Changed in version 3.9: The encoding and errors arguments were added.

L2【中文转述，encoding 参数表项】：encoding 与 filename 一起指定时，其值用于创建 FileHandler，并用于打开输出文件。

L3【中文转述，函数前置说明】：根记录器已有处理器时，该函数不进行配置；force=True 是文档列出的例外。

L4【核验范围】：上述说明支持参数加入版本及其配置条件。本文没有运行 Python 3.8 或 3.14；没有检查某个读者程序的处理器、日志级别、输出路径或文件内容。
