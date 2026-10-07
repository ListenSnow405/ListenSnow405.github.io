# 第七篇实际程序验证快照

日期：2026-10-05。Windows / Python 3.11.9 / 官方 MCP SDK 1.26.0，协商协议 2025-11-25。请求由固定客户端发出，未请求模型。

- `probe-final.json`、`probe-final.stderr.txt`：初始化、工具列表、来源调用与九类固定请求的原始返回及 stderr。
- `discovery-final.json`、`discovery-final.stderr.txt`：独立初始化、工具发现和来源清单。
- `no-connection-final.json`、`no-connection-final.stderr.txt`：不存在服务脚本，初始化失败与真实底层原因。
- `initial-restricted.json`：首次受限环境的 WinError 5；不记为服务返回或正常零命中。
- `protection.json`、`no-overwrite.stderr.txt`：旧记录拒绝覆盖、非零退出码和摘要未变。
- `dependencies.txt`：此次安装得到的完整依赖版本快照，不表示最新推荐版本。
- `manifest.json`：被测文件与记录摘要、包版本与运行范围。
- `historical/`：先前运行的原始日志与当时摘要；当前项目编号更新后已重新执行程序检查，旧日志中的路径保留实际执行时的值。

stderr 保留 SDK 依赖组合的非致命警告和服务请求日志；stdout 仍由 MCP SDK 专用于协议。本快照不含模型生成的 12 条结果，不用于测量模型工具选择或干扰防御。文件路径记录本次隔离环境，读者运行时使用自己的项目路径。
