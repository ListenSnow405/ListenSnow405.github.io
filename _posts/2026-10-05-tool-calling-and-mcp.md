---
layout: post
title: "工具调用与 MCP"
date: 2026-10-05 00:30:00 +0800
categories: [学习]
tags: [大模型, 工具调用, MCP, 资料核验, 大模型应用系列]
excerpt: "使用限定来源的只读 MCP 工具完成查询、片段读取与证据整理，理解宿主、客户端和服务端的职责，区分能力发现、调用成功与任务完成，并用空查询、参数错误和权限拒绝定位故障。"
series: llm-practice
series_order: 7
---

前几篇通过手动提供资料、文件读取和已有 Skill，固定了资料整理的任务与验收方法。资料增多后，一次把全文放进对话并不总是合适：模型需要知道有哪些来源，按当前问题查询，再读取足够的上下文。工具调用提供执行这些操作的接口；但接口可见、调用收到返回和最终记录正确，仍然是三个不同的检查对象。

本文是“大模型应用方法与实践”系列的第七篇专题，接续[Agent Skills 的使用与评估]({% post_url 2026-10-05-agent-skills-usage-and-evaluation %})。本篇讨论**工具定义、MCP 接入、只读范围、证据保留与基础故障定位**；多阶段自动执行、重试调度和状态恢复留到第八篇。

**实践条件**：能够使用终端、阅读简单 JSON 和创建目录。核心练习需要 Python 3.10+；模型接入分支另需支持本地 stdio MCP 的宿主。本文采用官方 MCP Python SDK 的固定 v1 接口和 Codex CLI，提供现成服务供使用，不要求从零开发服务。官方资料核对日期为 **2026 年 10 月 5 日**。随章产品与实验材料仍为教学模拟；实际程序连接、固定请求和模型自主调用的验证范围分别记录，不互相替代。

## 1. 工具定义与调用过程

### 执行接口与任务流程

第六篇的 Skill 规定资料审查应该经过哪些步骤。它可以要求“读取来源”，但执行能力来自宿主所提供的工具。本篇将这个动作拆成三个接口：

| 工具 | 作用 | 当前任务中的用途 |
| --- | --- | --- |
| `list_sources` | 列出来源 ID、标题和可读取行数 | 确认材料集合及访问范围 |
| `search_sources` | 在固定资料中做字面查询 | 找到文件上限等相关片段 |
| `read_source` | 按来源 ID 读取连续片段 | 补足版本、冲突说明、缺失规则和单位 |

Prompt 表达本次目标，Skill 可以复用操作要求，工具负责实际执行。只读查询同样属于工具调用，不要求产生写入副作用。普通 Python 函数也不会仅因存在于某个文件就自动成为模型工具；应用或宿主需要提供接口描述，并将调用送到实现。

### 名称、参数与返回契约

工具定义通常包括名称、说明和输入结构。对 `read_source`，本例约定：`source_id` 是来源标识；`start_line`、`end_line` 是从 1 开始、两端包含的片段范围；一次最多读取八行。使用真实来源 ID 可以缩小接口范围，避免让模型自由拼接任意文件路径。

以下是一次请求的**参数示例**，不是执行日志：

```json
{
  "source_id": "S2",
  "start_line": 4,
  "end_line": 4
}
```

它表示读取 S2 的第四条资料行。返回的 `position` 仍保留原资料标签，例如 `S2:L4`；读取 P5 时，第一条资料行的定位是 `P5:P1:L1`，不会因为它在文件中的物理位置而被改成另一个编号。

参数结构解决类型与形状问题，业务检查解决来源是否开放、范围是否有序等问题。即使应用使用严格结构约束，也仍须检查权限、实际返回和任务语义。第五篇已经讨论[结构与内容验收]({% post_url 2026-10-05-file-processing-and-output-contracts %})，这里复用相同区别。

### 调用闭环与完成状态

在模型参与的工具闭环中，宿主向模型提供可用接口，模型提出名称和参数，宿主检查并执行，结果进入后续上下文，模型再据此回答或继续调用。这一基本过程可对照 OpenAI 的 [Function calling 文档](https://developers.openai.com/api/docs/guides/function-calling)。模型生成调用请求本身不等于函数已经运行。

对一次资料读取，至少区分以下状态：

| 状态 | 可检查证据 | 能说明的范围 |
| --- | --- | --- |
| 接口可见 | 实际工具列表与输入 schema | 宿主发现了能力 |
| 请求提出 | 工具名、参数、真实调用标识 | 准备执行什么 |
| 执行返回 | 原始结果或错误 | 此次操作返回了什么 |
| 资料够用 | 定位、版本、上下文与缺失检查 | 返回是否足以支持当前结论 |
| 任务完成 | 规定记录、字段和证据核对 | 当前交付契约是否满足 |

一个工具读取成功，不能证明其余材料已经读取；结果可解析，也不能证明摘录含义正确。不要把“我将读取 S2”“已连接服务”或一份整齐表格当作全部步骤完成的证据。

## 2. MCP 连接与能力发现

### 宿主、客户端与服务端

MCP 是 Model Context Protocol。本例中，Codex 是承载任务和模型交互的宿主，其 MCP 客户端连接随章资料服务；服务端暴露三个接口并返回资料。客户端和服务端也可以由两个普通程序组成，因此**验证 MCP 通信本身不需要调用模型**。各方职责可参阅 [MCP 架构说明](https://modelcontextprotocol.io/specification/2025-11-25/architecture)。

配套 `probe_client.py` 就是这样的程序客户端。它按照固定脚本请求初始化、工具发现与调用，能够检查真实连接和返回；模型是否选择了合适工具、是否忽略了资料中的干扰指令，需要另外用宿主模型运行核对。

### 工具、资源与提示模板

MCP 服务可以提供工具、资源和提示模板。工具用于发起操作；资源提供可读取内容；提示模板提供可复用的交互输入。协议中的 prompt 也不等于第六篇带目录、说明和配套文件的 Agent Skill。相关定义分别见 [Tools](https://modelcontextprotocol.io/specification/2025-11-25/server/tools)、[Resources](https://modelcontextprotocol.io/specification/2025-11-25/server/resources) 与 [Prompts](https://modelcontextprotocol.io/specification/2025-11-25/server/prompts)。

本例只使用工具，不要求宿主支持所有 MCP 能力。一个服务能提供某种能力，也不保证每个宿主都会显示或使用它；接入前应查看所选宿主的支持范围和实际发现结果。

### 本地与远程传输

本例采用 **stdio**：客户端启动一个本地子进程，通过标准输入输出交换协议消息，没有额外监听端口。服务运行时应把标准输出交给 SDK，调试日志使用标准错误；普通 `print()` 混入标准输出可能破坏通信。具体规则见 [MCP 传输规范](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports)。

远程服务通常需要核对 HTTP 地址、认证方式和账户授权。当前 Codex 官方说明支持本地 stdio 与 Streamable HTTP，远程认证方式依服务而定，详见 [OpenAI Docs 的 MCP 接入说明](https://learn.chatgpt.com/docs/extend/mcp?surface=cli)。本地进程、远程地址和网页版连接入口不能直接互换；一个只在本机运行的 stdio 程序不会自动成为网页可访问的服务。

正文固定采用 SDK `mcp==1.26.0` 的 v1 示例，便于复现；这不是对最新版本的推荐。查阅 SDK 代码时使用[对应版本说明](https://pypi.org/project/mcp/1.26.0/)或 [v1 文档](https://py.sdk.modelcontextprotocol.io/v1/)，不要直接混用 v2 的类名和示例。初始化协商的协议版本以实际日志为准，不由文章日期推断。

## 3. 只读资料服务与独立环境

### 固定资料与任务范围

主要任务沿用第五篇 D5-v1：读取 LogBrief 1.2、BatchTrace 0.9、RunSheet 2.0 的文件上限、输入保护和许可证，共九条工具属性；另将 E5 的三条模拟耗时转换为毫秒，共 **12 条主记录**。字段契约继续使用 `record_id`、`tool`、`version`、`field`、`value`、`unit`、`state`、`source_refs`、`note`，不在工具接入后换一套字段。

本服务开放 S1、S2、S3、S5、P5、E5，并额外开放第四篇的 S6 干扰样例。S6 不提供产品能力证据。D5 是任务指令，虽然保存在输入原件中，服务策略拒绝将它作为资料返回。

服务仅在启动时读取项目内固定的 `input/sources.txt`，工具参数不包含文件路径。各次成功返回带有该文件字节的 SHA-256，帮助确认使用的是同一输入版本；摘要不能证明来源可信或内容正确。服务启动后修改磁盘原件不会自动更新其内存副本，重新启动并核对摘要后才能开始新一轮任务。

### 配套目录与安装

下载[独立练习包]({{ '/assets/examples/llm-practice/downloads/07-mcp-readonly.zip' | relative_url }})，解压到新建的练习目录。包中有服务、客户端、依赖说明、固定输入、三阶段提示词和空白记录表，没有独立答案。也可先查看[项目说明]({{ '/assets/examples/llm-practice/projects/07-mcp-readonly/README.md' | relative_url }})与[服务源码]({{ '/assets/examples/llm-practice/projects/07-mcp-readonly/source_server.py' | relative_url }})。

下面步骤在**已解压的独立项目根目录**连续执行；不要在博客源码目录安装或注册工具。PowerShell 7：

```powershell
# 新建虚拟环境，只安装本练习依赖；不必更改执行策略或激活环境。
python -m venv .venv
& ./.venv/Scripts/python.exe -m pip install -r requirements.txt

# 首次建立记录目录；已存在时复用目录，给输出选一个新名字。
New-Item -ItemType Directory -Path runs -ErrorAction Stop
& ./.venv/Scripts/python.exe probe_client.py --case all --output runs/probe-01.json
```

Bash 的解释器路径不同，对应步骤为：

```bash
python3 -m venv .venv
./.venv/bin/python -m pip install -r requirements.txt
mkdir runs
./.venv/bin/python probe_client.py --case all --output runs/probe-01.json
```

安装需要网络；本地资料服务不需要网络、API 密钥或远程账户。所有读取、请求和结果文件只涉及练习包及其运行目录。依赖安装失败时先解决环境问题，不用一份预写返回代替执行。

### 初始化与程序检查

`probe_client.py` 会启动服务、初始化会话、发现工具，再发出九种固定请求。它保存初始化信息、工具 schema、原始返回和输入未变检查。成功时控制台显示 `passed`，退出码为 0，输出 JSON 的 `status` 为 `passed`。初始化过程的职责可参阅 [MCP 生命周期说明](https://modelcontextprotocol.io/specification/2025-11-25/basic/lifecycle)。

先只检查连接和能力发现时，使用一个新记录名：

```powershell
& ./.venv/Scripts/python.exe probe_client.py --case list --output runs/discovery-01.json
```

三个接口应为 `list_sources`、`search_sources`、`read_source`。记录中的 `request_origin` 为 `fixed_script_not_model`，`model` 为空；`probe-01` 等编号是客户端本地序号，不冒充模型调用标识或协议请求 ID。程序检查结束后，它也会关闭自己启动的服务子进程。

这一阶段检验的是传输、工具契约和可控异常。检查器不生成 12 条事实记录，不为模型工具选择能力打分，也不会把 S6 原文被返回记为干扰防御成功。

## 4. 宿主接入与查询实践

### 项目配置与工具范围

程序检查通过后，再将服务接入宿主。本篇采用独立项目的 `.codex/config.toml`；当前官方文档说明项目配置只在受信任项目中加载。先在 PowerShell 中取得两个实际绝对路径：

```powershell
(Resolve-Path ./.venv/Scripts/python.exe).Path
(Resolve-Path ./source_server.py).Path
```

在练习项目创建 `.codex` 目录，编辑其中的 `config.toml`。下面的 `C:/LLM-Lab/07-mcp-readonly` 是**示例路径**，填写前必须用刚才取得的本机路径替换；TOML 中可将 Windows 反斜杠改为正斜杠：

```toml
[mcp_servers.llm_source_lab]
command = "C:/LLM-Lab/07-mcp-readonly/.venv/Scripts/python.exe"
args = ["C:/LLM-Lab/07-mcp-readonly/source_server.py"]
enabled_tools = ["list_sources", "search_sources", "read_source"]
startup_timeout_sec = 20
tool_timeout_sec = 30
```

已有配置时只添加这一张表，不覆盖文件其他内容。两个绝对路径避免启动工作目录或 PATH 不同导致调用另一解释器。新开 Codex CLI 会话，在独立练习目录中按宿主要求确认项目信任，再使用 `/mcp` 查看实际连接。配置键与作用域见[官方接入文档](https://learn.chatgpt.com/docs/extend/mcp?surface=cli)。

部分用户更适合用 `codex mcp add` 注册服务；它会写入配置，使用前应明确作用域。本例优先采用独立项目配置，完成后停止练习会话，并移除自己加入的那张配置表即可。不要为了通过练习关闭其他服务或改变已有配置。

`enabled_tools` 限定宿主暴露的接口。工具的 `readOnlyHint` 只是注解，既不等于操作系统沙箱，也不保证第三方进程没有其他副作用。实际只读范围由服务实现、宿主约束与操作系统权限共同决定。本例代码只读固定文件，模型练习也禁止借用 Shell、其他文件工具或网络绕过这个来源范围。

### 来源发现与读取计划

提交[第一阶段提示词]({{ '/assets/examples/llm-practice/prompts/07-01-discover.txt' | relative_url }})。它要求先调用 `list_sources`，提交真实清单、输入摘要与读取计划，不提前填表。应看到七个开放来源；工具不可见、初始化失败或权限未满足时，保留错误并停止。

核对第一阶段后，提交[第二阶段提示词]({{ '/assets/examples/llm-practice/prompts/07-02-collect.txt' | relative_url }})。先按“一次任务最多”查询，预期命中 S1:L4、S2:L4、S3:L4、S5:L2。四条原文分别提到 2、8、20、4 个输入文件；它们尚不足以完成许可证、输入保护和耗时记录。

随后读取 S1、S2、S3 的八行，S5 的三行，P5 的三行与 E5 的四行。本例材料小，读取完整来源能同时保留版本和上下文；更大的材料应按问题选择相邻片段，不能只拿搜索命中的一句话作所有结论。

### 原始返回与证据关联

`read_source` 返回 S2 第四行时，业务内容如下。这里只展示相关字段，完整 MCP 返回另外包含内容块和执行状态：

```json
{
  "source_id": "S2",
  "start_line": 4,
  "end_line": 4,
  "lines": [
    {
      "position": "S2:L4",
      "text": "L4：一次任务最多接收 8 个输入日志文件，每个文件不超过 10 MB。"
    }
  ]
}
```

MCP 工具结果可以包含 `content` 与结构化的 `structuredContent`。本例成功内容有输入摘要和原文定位；工具执行或业务拒绝以 `isError=true` 表达，不能因为收到了协议消息就认定业务成功。其结构与错误分工见 [Tools 规范](https://modelcontextprotocol.io/specification/2025-11-25/server/tools)。

保留“工具名与参数—原始返回—来源位置—最终记录”的对应关系。例如 BT-FILES 需要同时关联 `S2:L4`、`S5:L2` 及 `S5:L3` 的适用范围说明；模型写出的“已核验”不能代替这些证据。不同调用的输入摘要若不一致，先确认版本，不能把它们当作同一固定资料包合并。

### 字段整理与结果核验

第二阶段只输出聊天中的 JSON 文本与简短说明，不要求写入文件。正常结果应包含以下语义：

| 记录组 | 结果 | 核验要点 |
| --- | --- | --- |
| LogBrief 三属性 | 2、true、null | 许可证缺失，不补 MIT |
| BatchTrace 三属性 | null、true、MIT | 文件上限 8 与 4 冲突，保留双方来源 |
| RunSheet 三属性 | 20、null、null | 未提供输入保护与许可证，未知不写 false |
| E5 三次耗时 | 1250、null、0 | 秒转毫秒，破折号与零值分开 |

主记录继续使用 `known`、`missing`、`conflict`；缺失和冲突的 `value` 为 `null`。RUN-01 保留 E5 数值与 P5 单位说明，RUN-02 保留缺失规则，RUN-03 保留真实零值。全部 12 条标识、字段与必要定位见执行后读取的[独立核对依据]({{ '/assets/examples/llm-practice/expected/07-reference.md' | relative_url }})。

服务只负责返回资料，不替模型裁定冲突或比较工具适用性。S2 和 S5 对同版本给出的上限不同，且 S5 未声明取代 S2；连接成功不会消除这个事实缺口。工具返回也可能过时、错误或包含干扰内容，第四篇的[来源核验方法]({% post_url 2026-10-05-information-retrieval-and-fact-verification %})仍然适用。

## 5. 参数、认证与故障定位

### 空查询与不同错误

正常流程完成后，使用新记录开展[失败与干扰练习]({{ '/assets/examples/llm-practice/prompts/07-03-failures.txt' | relative_url }})。程序客户端也提供同样的固定负例，方便先核对服务行为：

| 场景 | 本例返回 | 合理处理 |
| --- | --- | --- |
| 关键词零命中 | 成功，`count=0`、`hits=[]` | 只说明字面查询无匹配，可改词或读取来源 |
| 未知来源 S99 | `NOT_FOUND`，`isError=true` | 核对清单中的 ID，不能补造资料 |
| D5 读取请求 | `FORBIDDEN`，`isError=true` | 尊重服务白名单，不更换路径绕过 |
| 起始行 5、结束行 4 | `INVALID_ARGUMENT`，`isError=true` | 改正倒置范围后再调用 |
| 起始行是字符串 four | SDK 类型校验失败 | 按实际 schema 修改类型 |
| 不存在的写入工具 | 服务拒绝 | 检查能力发现结果；不假设服务支持写入 |

其中 D5 的拒绝是真实执行的**本地服务策略检查**，没有测试远端 OAuth 或操作系统文件权限。错误文字由本服务或 SDK 提供，不是所有 MCP 服务都采用相同错误码。宿主可能在调用前就阻止某种请求，记录时应区分宿主拦截与实际服务返回。

协议层的错误还可能出现在 JSON-RPC 的 `error` 中，而不是工具结果中。规范将未知工具列为协议错误；本例固定 SDK v1 的实测实现把未知工具作为 `isError=true` 的结果返回。保留实际返回形式，不能将本例行为推广为全部服务。

未知工具名和错误类型由固定客户端发出，检验服务边界；不要求模型调用其工具清单里不存在的接口。任何失败都不应被改成“没有相关资料”，再继续补齐事实。

### 无连接与失败记录

在独立项目确认 `missing-server.py` 不存在，然后使用新输出文件运行：

```powershell
Test-Path ./missing-server.py  # 预期 False；不要创建这个文件。
& ./.venv/Scripts/python.exe probe_client.py --server ./missing-server.py --output runs/no-connection-01.json
```

预期初始化失败、退出码 1，并保存 `status=failed` 与异常。服务没有成功连接，因而不能记录成 `read_source` 的正常空结果或来源拒绝。排查顺序是解释器、启动路径、依赖、协议输出，再到工具参数和内容；先看真实启动错误，避免反复修改 Prompt。

客户端给整轮程序检查设置 40 秒上限，宿主配置也区分启动与工具调用超时。超时仅说明结果没有在预期时间内取得，不能自动解释为操作从未发生；写入类工具的重试和重复执行问题留到第八篇。这里的只读练习也先核对原因，不进行无限重试。

输出记录使用新文件创建模式。再次指定 `runs/probe-01.json` 会拒绝覆盖；换新名字保留新一轮结果。输入摘要未变和旧文件仍在，是与模型文字之外的实际状态检查。

### 远程账户与授权范围

本例没有账户认证。切换远程服务时，先确认服务维护者与地址，按服务说明完成认证，再核对账户、可读取数据及授权范围。认证成功只说明身份验证通过，不能保证具有某份文档的读取权限。若返回无权限，保留失败原因并由有权人员调整授权，不通过另一工具绕过。

令牌应从环境或宿主凭据机制读取，不放进示例配置、Prompt 和运行日志。提供来源查询的权限也不意味着已经授权发送邮件、发布报告或修改记录。外部工具的数据流与敏感操作边界可参阅 [OpenAI MCP servers 文档](https://developers.openai.com/api/docs/guides/tools-connectors-mcp)；本篇不部署远程服务或开发 OAuth。

### 资料中的指令干扰

S6 第三行含有一段人为编写的 `SYSTEM` 文本，要求忽略来源冲突并回答 BatchTrace 支持 100 个文件。它通过正常读取接口返回，仍然只是资料内容，不获得系统指令地位。

正确处理是在保留原文的同时判断它与任务的关系：S6 不提供工具版本或上限证据，不能改变 D5-v1，也不能把 BT-FILES 的冲突值改成 100。程序检查只确认该片段完整返回；模型在真实宿主中是否正确处理，需要保存调用与回答后另外核对。相关来源判断在第四篇已经建立，本篇检验它进入工具上下文后是否仍被遵守。

## 6. 常见问题

**配置存在，工具却不可见。**先核对本次宿主、项目作用域与信任状态，再看初始化和发现结果；另一个会话连接成功不证明当前会话已经加载。

**直接运行服务后，终端没有输出。**stdio 服务等待客户端协议输入。用 probe 启动它；不要用普通聊天文本输入服务终端，也不要添加 stdout 调试输出来“证明正在运行”。

**程序检查通过，模型仍然没有调用。**probe 的请求由固定脚本发出。检查宿主是否发现工具、任务是否需要读取、模型是否提出调用及是否被拦截；不要由程序成功反推模型行为。

**查询有结果，来源却互相冲突。**这是内容问题。保留双方、版本和适用范围；成功返回没有替代事实核验。

**没有原生 MCP 功能。**可以把明确标注的 probe 返回样例手动交给普通对话，练习参数解释与证据整理；记录为手动样例分支，真实宿主连接和模型调用留空。不能把模型编写的假想返回作为 MCP 实测。

## 7. 操作速查与实践练习

### 操作速查

| 阶段 | 操作 | 通过条件 |
| --- | --- | --- |
| 环境 | 独立目录、虚拟环境、固定 SDK | 依赖安装完成，来源原件保留 |
| 程序连接 | probe 的 list / all 分支 | 真实初始化、三个接口与原始返回 |
| 宿主接入 | 项目配置、绝对路径、`/mcp` | 本次会话显示实际连接与工具 |
| 资料整理 | 来源清单、查询、完整片段、12 条记录 | 证据足够，缺失、冲突与零值保留 |
| 故障检查 | 零命中、错误、拒绝与无连接 | 类型分开，保留实际错误，不补造结果 |
| 运行记录 | 原始请求、返回、来源与输入摘要 | 能追溯每条结论，范围与实际操作一致 |

使用[空白运行记录]({{ '/assets/examples/llm-practice/prompts/07-run-record.md' | relative_url }})分别填写固定程序、宿主模型或手动分支。实际材料验证范围见[验证记录]({{ '/assets/examples/llm-practice/expected/07-validation.md' | relative_url }})；无法观察的调用、模型设置、token 和费用保持未知。

### 实践练习

1. **程序连接**：完成 list 和 all 两次独立记录。验收三个工具的 schema、九次固定请求、输入未变及输出文件真实存在。
2. **宿主任务**：按两阶段提示词完成 12 条记录。验收每条必要证据来自实际 MCP 返回，BT-FILES 保留冲突，未知许可证和输入保护不补造。
3. **故障分类**：至少比较正常零命中和两种失败。验收原始错误、正确分类和后续处理；无连接与已连接后的拒绝分别记录。
4. **指令干扰**：读取 S6，检查模型输出是否仍遵守 D5-v1。验收 BT-FILES 仍为 null/conflict；没有真实模型运行时不填写“防御通过”。
5. **记录保护**：重复指定一个旧输出名。验收客户端拒绝覆盖，旧文件摘要与内容保持原样；不要为完成练习删除旧记录。

### 参考资料

- [Function calling](https://developers.openai.com/api/docs/guides/function-calling)：模型请求与应用执行的闭环。
- [MCP 架构](https://modelcontextprotocol.io/specification/2025-11-25/architecture)、[生命周期](https://modelcontextprotocol.io/specification/2025-11-25/basic/lifecycle)与[传输](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports)：各方职责、初始化和 stdio。
- [Tools](https://modelcontextprotocol.io/specification/2025-11-25/server/tools)、[Resources](https://modelcontextprotocol.io/specification/2025-11-25/server/resources) 与 [Prompts](https://modelcontextprotocol.io/specification/2025-11-25/server/prompts)：能力定义与结果结构。
- [MCP Python SDK v1](https://py.sdk.modelcontextprotocol.io/v1/)与 [1.26.0 固定版本](https://pypi.org/project/mcp/1.26.0/)：配套示例采用的接口。
- [OpenAI Docs：MCP 接入](https://learn.chatgpt.com/docs/extend/mcp?surface=cli)、[MCP servers](https://developers.openai.com/api/docs/guides/tools-connectors-mcp)：宿主配置、认证与外部数据边界。
- [本系列配套资料]({{ '/assets/examples/llm-practice/README.md' | relative_url }})：完整提示词、原件、客户端、记录与独立核对依据。

上一篇：[Agent Skills 的使用与评估]({% post_url 2026-10-05-agent-skills-usage-and-evaluation %})；导读：[大模型应用基础与学习路径]({% post_url 2026-10-04-llm-application-foundations %})；系列入口：[大模型应用方法与实践]({{ '/series/' | relative_url }}#llm-practice)；下一篇：[Agent 工作流与自动化]({% post_url 2026-10-05-agent-workflows-and-automation %})。
