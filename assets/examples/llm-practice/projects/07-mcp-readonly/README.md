# 第七篇：MCP 只读资料练习

这是供使用的固定最小服务，不是完整 MCP 开发教程。资料与产品为教学模拟；服务和 probe 客户端进行真实 stdio MCP 通信，固定请求由程序发出，不请求模型或 OpenAI API。

## 文件与来源

- `source_server.py`：三个只读工具，固定 `input/sources.txt`，不接受路径或写入请求。
- `probe_client.py`：初始化、发现、成功/失败请求与检查；输出新 JSON 文件，不覆盖已有记录。
- `requirements.txt`：官方 `mcp==1.26.0`，使用 v1 接口，不与 v2 或独立 fastmcp 包混用。
- `input/sources.txt`：第五篇 sources.txt 的原块，另接第四篇 S6 完整干扰块；S1、S2、S3、S5、P5、E5 原文与标签不改。D5 虽存在于原件中，服务策略明确拒绝读取。
- `input/contract.json`：第五篇 D5-v1 字段与 12 条标识契约，逐字节副本。启动前供操作者核对，不作为服务工具。
- `tasks/`：三阶段提示词的副本；正常流程与故障练习分开。
- `run-record.md`：空白记录表；包中没有参考答案、模型响应、虚拟环境或凭据。

## 独立环境

下载配套 `07-mcp-readonly.zip`，解压至新的练习目录。不要在博客源码根运行、安装或注册工具。Python 3.10+；本文程序实测 Python 3.11.9，依赖的安装需要网络。本地服务运行无需网络或 API 密钥。

PowerShell 7，在已解压项目根执行：

```powershell
python -m venv .venv
& ./.venv/Scripts/python.exe -m pip install -r requirements.txt
New-Item -ItemType Directory -Path runs -ErrorAction Stop
& ./.venv/Scripts/python.exe probe_client.py --case all --output runs/probe-01.json
```

不必激活虚拟环境。若 runs 已存在，复用目录并为每次输出选择新文件名。Bash 对应：

```bash
python3 -m venv .venv
./.venv/bin/python -m pip install -r requirements.txt
mkdir runs
./.venv/bin/python probe_client.py --case all --output runs/probe-01.json
```

成功退出码为 0，JSON status=passed，含初始化信息、三个工具的 schema、实际来源清单、九种案例调用及输入未变检查。`--case list` 只初始化、发现工具并列出来源；`--case read` 等另发送一种案例请求。失败文件 status=failed、退出码 1，不等于空查询。

独立无连接实验使用一个确认不存在的文件名：

```powershell
Test-Path ./missing-server.py  # 须为 False
& ./.venv/Scripts/python.exe probe_client.py --server ./missing-server.py --output runs/no-connection-01.json
```

预期初始化失败、退出码 1，不能出现伪造的工具结果。重复指定旧输出文件须报 FileExistsError；已有文件保持原样。

## 工具范围

| 工具 | 输入 | 返回与限制 |
| --- | --- | --- |
| list_sources | 无 | 七个开放来源 ID、标题、行数及输入文件 SHA-256 |
| search_sources | query，1—80 字符 | 字面查询，完整匹配行；正常零命中返回 count=0、hits=[] |
| read_source | source_id、start_line、end_line | 两端包含、从 1 开始、最多 8 行；真实标签在 position 中 |

所有成功返回均标记 material_type=teaching_simulation。失败 `isError=true`：未知 S99 为 NOT_FOUND，D5 为服务策略 FORBIDDEN，倒置范围为 INVALID_ARGUMENT，错误类型由 SDK 校验。probe 的未知工具请求用于检验服务拒绝，不向模型增加写入能力。

readOnlyHint 是声明，不是操作系统沙箱。本服务代码仅读取固定文件；进程仍应按宿主和操作系统权限限制。不要将真实敏感数据放入本练习，不将它注册为公共远程服务。

## Codex 项目接入

先完成程序检查，再在此独立项目的 `.codex/config.toml` 加入本章正文给出的配置。将解释器和服务路径替换为本机绝对路径；只对该练习项目确认信任。`enabled_tools` 仅包含三个工具，默认审批行为由宿主决定，不配置自动跳过审批。

启动一个新 Codex CLI 会话，以 `/mcp` 核对连接，再依次提交 tasks/07-01-discover.txt 和 tasks/07-02-collect.txt；每阶段核对后推进。tasks/07-03-failures.txt 是独立后续实验。模型只用本 MCP 工具，不读取 contract、参考答案或通过 Shell 绕过来源范围。没有 Codex 时仍可完成 probe，但不填写模型调用或干扰防御通过。

无原生 MCP 功能时可以在普通对话中提供明确标注的 probe 返回样例，练习解释证据；这条分支不算真实连接验收。参考答案与实际材料验证记录在系列 expected/ 目录，完成后再读取。
