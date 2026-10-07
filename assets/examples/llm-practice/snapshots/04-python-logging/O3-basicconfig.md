# O3：Python 3.8 logging.basicConfig 局部摘录

- 发布主体：Python 官方文档。
- 英文原始来源：https://docs.python.org/3.8/library/logging.html#logging.basicConfig
- 官方中文备用入口：https://docs.python.org/zh-cn/3.8/library/logging.html#logging.basicConfig
- 页面版本：Python 3.8.20；版本路径：3.8。
- 核对日期：2026-10-05，UTC+08:00。
- 读取状态：首次内置网页读取失败；随后通过启用证书校验的标准 HTTPS 请求取得英文正文，HTTP 200，147822 字节，并定位完整 basicConfig 章节。内置网页读取工具也成功读取官方中文对应章节。
- 状态变化与诊断范围见 `access-recovery.md`。本文件为局部阅读记录，不是运行测试。

L1【参数表整理，英文原文已读】：该节列出的支持参数为 filename、filemode、format、datefmt、style、level、stream、handlers、force，共九项；其中没有 encoding 或 errors。官方中文对应表的参数集合相同。

L2【中文转述，函数前置说明】：根记录器已有处理器时，basicConfig 不进行配置；force=True 是文档列出的例外。

L3【中文转述，版本变更说明】：该节记录 force 参数在 3.8 加入。encoding 的“3.9 加入”由 O1/O2 的历史说明交叉核验，不将其他版本的文字冒充本页原文。

L4【核验结论与限制】：O3 的完整支持参数表与 O1/O2 的加入版本说明共同支持“3.8 不适用同一 encoding 参数写法”的文档判断；没有运行 Python 3.8，也没有证明整个 Python 3.8 无法通过其他方式写出 UTF-8 文件。
