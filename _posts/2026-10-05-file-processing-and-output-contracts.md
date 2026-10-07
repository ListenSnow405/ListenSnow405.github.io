---
layout: post
title: "文件处理与输出规范"
date: 2026-10-05 00:10:00 +0800
categories: [学习]
tags: [大模型, 文件处理, 结构化输出, JSON, 大模型应用系列]
excerpt: "从输入解析与字段映射到 JSON、TSV 和 Markdown 交付，通过固定资料和完整脚本核对缺失、冲突、单位、记录集合及文件一致性，并区分结构检查与事实核验。"
series: llm-practice
series_order: 5
---

上一轮资料核验已经留下了工具属性、原文位置和冲突说明。准备交付时，这些内容却被分别整理成报告和表格：报告保留了“未记录”，表格为了方便计算填成了零；JSON 引用了同一条来源，却采用了不同的单位。每份文件单独看都像是完整结果，放在一起则无法确定哪个值可以继续使用。

本文是“大模型应用方法与实践”系列的第五篇专题，接续[资料检索与事实核验]({% post_url 2026-10-05-information-retrieval-and-fact-verification %})。文章讨论**输入怎样映射到稳定、可检查的文件**：先确认实际读取范围，再定义字段与缺失规则，以 JSON 保存主记录，生成语义一致的 TSV 和 Markdown，最后检查实际产物。复杂表格公式、大型文档排版、PPT 设计与完整 OCR 系统留作应用专题。

**实践条件**：能够保存 UTF-8 文本即可完成对话提取；本地导出和检查需要 Python 3.10 或更高版本，仅使用标准库。2026 年 10 月 5 日在 Windows、Python 3.11.9 的独立临时目录中实际运行了配套程序。三种工具、报告摘录与实验记录均为教学模拟。随后实际制作两份 PDF、运行 Windows OCR，并通过现有 Codex 登录对两模型完成 JSON 与文件转写对照；这些实测与主流程的固定文字摘录分开保存。没有运行虚构工具；Platform API 缺少独立密钥，尚未发送请求。

## 1. 文件输入与解析范围

### 原文件与读取结果

把文件交给模型前，需要区分原文件、解析结果和本次实际使用的片段。三者的内容范围可能不同：正文抽取遗漏表格标题，表格读取丢失公式含义，截图只覆盖一页。文件名显示在对话里，也不能证明全部内容已经读取。

| 输入形式 | 可提供的内容 | 核对重点 |
| --- | --- | --- |
| 普通文本 | 原文、行标签、编码说明 | 是否截断；特殊字符是否保留 |
| 带文本层的 PDF | 按页抽取的文字 | 阅读顺序、表格关系、脚注与单位 |
| 扫描页面或图片 | 图片及识别文字 | 数字、负号、小数点、表头与识别遗漏 |
| 表格文件 | 工作表、单元格值、公式或导出表 | 当前读取的是显示值还是公式；隐藏行和合并单元格 |
| 原生文档 | 宿主提供的解析结果 | 正文、批注、修订和附件是否在读取范围内 |

PDF 中存在可复制文字，并不保证抽出的文本能保持表格结构；扫描文件也可能带有识别生成的文字层。`pypdf` 可提取文字，但不提供 OCR。使用它读取图像页面时，需要另行处理识别，并回看原页核对。[pypdf 文本提取说明](https://pypdf.readthedocs.io/en/stable/user/extract-text.html)

本例选择配套文字摘录作为可在普通对话中使用的输入，不假定读者具备文件上传或 PDF 工具。P5 的 `P1:L1` 是**教学页码与行标签**；没有 PDF 原件，因此读取它只能确认摘录内容，不能确认原页布局、抽取准确率或扫描识别质量。

### 输入清单与遗漏记录

第五篇使用新的任务版本 **D5-v1**，提取范围比第四篇的完整条件矩阵更小。S1、S2、S3 和 S5 沿用原文；旧版本 S4 与干扰资料 S6 不进入本次输入，不能据此改写上一轮的核验结论。

| 来源 | 当前用途 | 边界 |
| --- | --- | --- |
| S1、S2、S3 | 三种工具的说明 | 对应 LogBrief 1.2、BatchTrace 0.9、RunSheet 2.0 |
| S5 | BatchTrace 0.9 快速卡片 | 与 S2 的文件上限冲突，缺少更正或取代说明 |
| P5 | 耗时单位与缺失符号说明 | 只有教学文字摘录，没有 PDF 原件 |
| E5 | 三条教学模拟实验记录 | 不是实际工具测试，不用于速度排名 |

完整来源在[练习项目的 sources.txt]({{ '/assets/examples/llm-practice/projects/05-file-output/sources.txt' | relative_url }})。输入检查至少记录：读取了哪些来源和版本，实际读取哪些页或标签，哪些内容缺失，以及这些缺口是否影响本次字段。若真实任务中的单位页无法读取，应把换算标为待确认，不能根据文件名猜测单位。

### PDF 与 OCR 补充实测

为检验读取差异，另行按 P5/E5 内容制作了[文本 PDF]({{ '/assets/examples/llm-practice/snapshots/05-live-validation/pdf/digital-report.pdf' | relative_url }})与[栅格 PDF]({{ '/assets/examples/llm-practice/snapshots/05-live-validation/pdf/raster-report.pdf' | relative_url }})；它们是实际生成的教学文件，不是此前未提供的 P5 原件。两者均为一页，保存后实际渲染并目视检查。pypdf 从文本版抽取 260 字符，从无文字层的栅格版抽取 0 字符。

随后用本机 Windows.Media.Ocr 的 zh-Hans-CN 识别栅格版的 150 dpi 渲染图。原始结果有 21 行、372 字符，却没有保留完整表格关系：标识、数值和状态按列返回，`1.25` 拆成 `1. 25`，破折号漏识别，`sim-02` 的连字符被识别成长横线。

回看实际页面后，另存人工校正记录，恢复三条记录及单位：1250 ms、未记录、0 ms。原始 OCR 保留不改，不能把识别后的空单元格直接判为缺失。这只验证了清晰单页教学资料，未覆盖歪斜拍照、扫描噪声或复杂跨页表格；原始文件、错误和复现步骤见[补充实测记录]({{ '/assets/examples/llm-practice/expected/05-live-validation.md' | relative_url }})。

## 2. 字段契约与信息映射

### 记录标识与固定字段

字段契约说明一个值是什么、用哪种类型保存、怎样处理未知，以及它与哪条记录关联。“整理成表格”没有给出这些规则，模型可能把平台名称当作标识，把不同版本合并，或用“无”同时表示不存在和未提供。

本次交付 `records.json`、`records.tsv`、`report.md`。主记录固定为 **12 条**：三个工具各有三条属性，另有三条模拟耗时。标识与顺序由[contract.json]({{ '/assets/examples/llm-practice/projects/05-file-output/contract.json' | relative_url }})确定。

```text
LB-FILES, LB-PROTECT, LB-LICENSE
BT-FILES, BT-PROTECT, BT-LICENSE
RS-FILES, RS-PROTECT, RS-LICENSE
RUN-01, RUN-02, RUN-03
```

前九条分别记录 `max_input_files`、`input_unchanged`、`license`；后三条记录 `elapsed_ms`。它们保留第四篇的属性含义，但不重新生成全部必要条件判定，也不开展候选排名。

| 键 | 含义与约束 |
| --- | --- |
| `record_id` | 本次契约内唯一标识，不因显示名称改变 |
| `tool`、`version` | 工具名称和版本，不能跨版本合并 |
| `field` | 固定字段名，用于确定值的类型与单位 |
| `value` | 整数、布尔、字符串或 `null`，依字段和状态确定 |
| `unit` | 文件数量为 `files`，耗时为 `ms`，其他为 `none` |
| `state` | `known`、`missing` 或 `conflict` |
| `source_refs` | 非空来源定位数组；冲突和转换保留所需的多处定位 |
| `note` | 单行解释，说明缺失、冲突或必要转换 |

所有记录都保留九个键。JSON 顶层另有 `schema_version: "1.0"`、`demand_id: "D5-v1"` 和 `records` 数组。对象中的键顺序可以变化；记录顺序与 TSV 列顺序固定。标识保证修订时能定位记录，版本保证引用没有跨越范围。

### 缺失、零值与冲突

本例将缺失与冲突的 `value` 统一保存为 `null`，再用 `state` 区分原因。字段存在而值为 `null`，与整个字段被删掉不同；JSON Schema 的必需字段和可空类型也需要分别描述。[JSON Schema 对象说明](https://json-schema.org/understanding-json-schema/reference/object)

| 情况 | `value` | `state` | 解释 |
| --- | --- | --- | --- |
| 明确不修改输入日志 | `true` | `known` | 输入保持不变 |
| 未提供是否修改输入 | `null` | `missing` | 不能推成 `false` |
| 耗时确实记录为零 | `0` | `known` | 已知零值，单位为 ms |
| 耗时未记录 | `null` | `missing` | 不能补零以方便计算 |
| 同版本上限分别为 8 与 4 | `null` | `conflict` | 双方依据保留，尚未裁决 |

如果原文明确会修改输入，`input_unchanged` 才可记录为 `false / known`；当前资料没有这样的事实。RunSheet 的说明未提供输入保护信息，记录应保持缺失。未知许可证也不能沿用 BatchTrace 的 MIT。

BatchTrace 的上限记录示例如下。这是**单条片段**，不能直接当作完整 `records.json` 提交检查：

```json
{
  "record_id": "BT-FILES",
  "tool": "BatchTrace",
  "version": "0.9",
  "field": "max_input_files",
  "value": null,
  "unit": "files",
  "state": "conflict",
  "source_refs": ["S2:L4", "S5:L2", "S5:L3"],
  "note": "S2:L4 为 8，S5:L2 为 4；未说明更正、取代或适用条件。"
}
```

`source_refs` 中的 S5:L3 说明为什么不能直接采用日期较新的卡片。冲突状态的保留不是格式妥协，而是本次可确认事实的边界。

### 单位与转换依据

E5 的三个值为 `1.25`、`—`、`0`，单看这些记录无法确定耗时单位。P5 提供了必要定义：

```text
[P5] 教学模拟报告的配套文字摘录
P1:L1：E5 的 duration 单位为秒（s）；输出 elapsed_ms 时乘以 1000。
P1:L2：破折号“—”表示未记录；数字 0 表示已记录的零值，不能与缺失互换。

[E5] BatchTrace 0.9 教学模拟实验记录
L1：run_id=sim-01；duration=1.25。
L2：run_id=sim-02；duration=—。
L3：run_id=sim-03；duration=0。
```

因此 `RUN-01` 为 `1250 / known / ms`，来源包含 E5:L1 与 P5:P1:L1；`RUN-02` 为 `null / missing / ms`；`RUN-03` 为 `0 / known / ms`。本例转换后都是整数，不需要舍入。换用其他数据时，应先约定精度与舍入规则，再修改契约，不能让模型自行把小数截断。

## 3. 输出形式与表达约定

### 主记录与派生文件

JSON 适合作为本例的主记录，因为它能区分数字、布尔、字符串和空值，并保存来源数组。TSV 便于按列查看，Markdown 便于阅读；后二者从同一主记录生成，减少分别提取造成的漂移。

> 来源与字段契约 → 主 JSON → 原文与单位核验
>
> 核验后的主 JSON → 固定规则导出 → 三格式文件 → 结构与一致性检查

普通聊天中的“请输出 JSON”只是任务要求，输出仍须实际解析。若把代码围栏或解释段落一起保存，文件就不是所需的纯 JSON。能解析也不是完整验收：还需要检查必需键、类型、标识、记录集合和来源。

TSV 的表头与记录字段一致。该文件不保存 JSON 原生类型，因此必须约定转换方法，不能让读者根据单元格外观自行解释。

| JSON 内容 | TSV 表达 | 还原与核对条件 |
| --- | --- | --- |
| `null` | 空单元格 | 同行 `state` 为 missing 或 conflict |
| 布尔值 | 小写 `true`、`false` | `field` 为 input_unchanged |
| 整数 | 十进制规范文本 | 不加千位逗号、单位后缀或前导零 |
| 字符串 | 原文本 | 本例要求非空单行，不含控制字符 |
| 来源数组 | 标签以 `;` 连接 | 本例标签本身不含分号 |

TSV 真正使用 TAB 分隔，而非多个空格。引号和转义交给 `csv` 模块处理；打开文件时设置 `newline=""`，由该模块处理行边界。标准库将 `None` 写成空串的默认行为本身不保存缺失原因，所以本例先显式转换值，再保留状态列。[Python csv 文档](https://docs.python.org/3/library/csv.html)

配套程序的关键序列化步骤如下；完整程序同时处理值、来源数组和固定字段顺序：

```python
# data 已通过本练习的结构检查，tsv_rows 显式转换每个字段。
with output_path.open("w", encoding="utf-8", newline="") as stream:
    writer = csv.writer(stream, delimiter="\t", lineterminator="\n")
    writer.writerows(tsv_rows(data))
```

不能用 `str(value or "")` 处理空值：已知的 `0` 与 `false` 都会丢失。配套代码先用 `value is None` 判断缺失，再单独处理布尔值，最后转换数字与字符串。

### 报告模板与检查范围

Markdown 采用固定模板：需求版本、范围说明、工具属性表、模拟实验表、逐条记录说明与检查边界。表内的值、状态和来源来自同一 JSON；`null` 显示为“未确定”，但状态列仍说明是缺失还是冲突。

本例检查器会用同一模板重新渲染并比较报告。这样可以发现报告单独改写后的漂移，但也意味着标题、列顺序和固定文字必须符合模板。它适合这种稳定交付规范，不能直接用于判断任意自由撰写的报告。后续若允许自由表述，需要另外约定可机器检查的字段区域，并人工检查论述。

## 4. 完整文件整理案例

### 项目准备

下载[第五篇独立练习项目]({{ '/assets/examples/llm-practice/downloads/05-file-output.zip' | relative_url }})，解压到**博客仓库以外的新目录**，进入解压后的 `05-file-output`。压缩包只含以下六份文件，不包含参考答案或运行结果。

```text
05-file-output/
├── README.md
├── sources.txt
├── contract.json
├── records.schema.json
├── export_output.py
└── validate_output.py
```

先阅读 README 和来源，执行 `python --version` 确认 Python 3.10 或更高版本。Windows 若使用 `py -3`，将下列命令中的 `python` 一致替换为它；Bash 环境可用 `python3`，但本篇没有在该环境实际运行。项目不需要安装第三方包。

### 主记录提取与核验

打开[完整提取提示词]({{ '/assets/examples/llm-practice/prompts/05-01-extract.txt' | relative_url }})，在新对话中整份提交。它已包含 D5、全部来源、字段契约与 Schema；无需额外读取参考答案，也不需要沿用前几篇的对话状态。要求只输出完整 JSON，先核验后交付其他格式。

收到结果后，将 JSON 对象保存为练习目录中的 `records-draft.json`，去掉围栏和外围说明，使用 UTF-8 无 BOM。没有文件工具时，由读者实际创建；模型在聊天中展示内容不代表已保存文件。有文件工具时，也要记录实际路径和读取范围。

逐条核验三件事：值和状态是否符合原文，单位是否一致，定位是否支持当前字段。重点检查 BT-FILES 是否仍保留双方冲突、RS-PROTECT 是否保持未知、三条耗时是否区分转换、缺失与零值。核验未通过时先修订主 JSON；不要用不同的答案分别填到三个文件里。

### 确定性导出

以下是**连续执行步骤**，当前目录须为独立的 `05-file-output`。第一条读取已核验的 `records-draft.json`，创建全新输出目录；第二条检查实际文件：

```text
python export_output.py records-draft.json --out output-v1
python validate_output.py output-v1
```

导出程序先检查主记录，再创建 `output-v1`，其中应有 `records.json`、`records.tsv` 和 `report.md`。它不修改输入 JSON，且拒绝已存在的输出目录。修订时另存主记录为 `records-v2.json`，使用 `--out output-v2`，旧版文件可供对照。若中途写入失败，可能留下部分文件，应检查内容并另选新目录，不能把失败记录写成已交付。

本例正确产物的检查输出为：

```text
PASS: 12 records; structure, reference labels and file consistency.
Manual review required: source meaning, unit conversion and factual support.
```

打开三个实际文件，确认标识、值、单位、状态、来源与说明一致。报告中的 RUN-02 应显示“未确定 / missing”，RUN-03 应显示“0 ms / known”；TSV 中前者的值为空单元格，后者为 `0`。文件名称和绝对路径应写入[空白执行记录]({{ '/assets/examples/llm-practice/prompts/05-run-record.md' | relative_url }})，与终端输出及人工核验结论一起保存。

### 对话转写分支

若要观察模型转写多格式的表现，可以在主 JSON 已核验后，于同一对话提交[后续交付提示词]({{ '/assets/examples/llm-practice/prompts/05-02-deliver.txt' | relative_url }})。这是前一阶段之后的**替代方案**：按其中完整模板获得 TSV 和 Markdown，手动保存到另一个新目录，并把主 JSON 复制为该目录的 `records.json`，再运行同一检查器。

保存 TSV 时应保留真实 TAB 和空单元格，不用空格重排；保存报告时保留模板和末尾换行。补充实测把同一份经原文核验的实际模型 JSON 显式加入后续提示词，两模型各独立调用一次；生成的 TSV 与 Markdown 实际保存后，三文件检查均通过。原始回复与保存结果分开保留，没有修复模型字段或文本。这个结果验证了显式提供主记录后的转写，不依赖产品保留前轮状态。比较两个分支时，分别保留原始输出、错误与修订次数，不把参考产物当作模型输入。

## 5. 结构检查与局部修订

### 检查层次

配套[只读检查器]({{ '/assets/examples/llm-practice/projects/05-file-output/validate_output.py' | relative_url }})对本次契约逐项检查，不修改文件，也不依赖外部校验库。

| 检查层次 | 本例实际检查 | 未能证明的内容 |
| --- | --- | --- |
| 解析 | JSON、TSV 可读取；拒绝重复 JSON 键与非标准数值 | 原文事实正确 |
| 结构与类型 | 固定键、值类型、状态、单位和必需说明 | 字符串内容有充分证据 |
| 记录完整性 | 12 条标识唯一，集合和顺序符合契约 | 遗漏了契约以外的业务需求 |
| 来源定位 | 标签在固定原文中实际存在，无重复 | 对应行支持当前数值或推断 |
| 跨文件一致性 | TSV 规范字段与主 JSON 相符；报告符合固定模板 | 三个文件没有共同使用错误事实 |

Python 默认 JSON 解码接受重复键并保留最后一个值，也接受 NaN 和 Infinity。只调用默认 `json.loads` 不能完成本例的严格检查；程序用 `object_pairs_hook` 拒绝重复键，用 `parse_constant` 拒绝这些非标准数值。[Python json 文档](https://docs.python.org/3/library/json.html)

程序还用 `type(value) is int` 区分整数与布尔，避免 Python 中 `bool` 作为 `int` 子类时把 `true` 当成文件数量 1。TSV 则按字段契约比较规范文本：空值、`0`、`false` 必须分别保留。通用[JSON Schema]({{ '/assets/examples/llm-practice/projects/05-file-output/records.schema.json' | relative_url }})描述基本格式；检查器另行实现固定记录集合、状态关系和跨文件规则，不在运行时加载该 Schema。

### 人为故障与修订顺序

[故障目录说明]({{ '/assets/examples/llm-practice/cases/05-faulty-output/README.md' | relative_url }})及其中三个文件由作者手动植入错误，不是实际模型失败。下载该目录的 [JSON]({{ '/assets/examples/llm-practice/cases/05-faulty-output/records.json' | relative_url }})、[TSV]({{ '/assets/examples/llm-practice/cases/05-faulty-output/records.tsv' | relative_url }})与[报告]({{ '/assets/examples/llm-practice/cases/05-faulty-output/report.md' | relative_url }})，保存到独立练习项目的新目录 `faulty-v1`，不要修改博客中的样例原件。

执行 `python validate_output.py faulty-v1`。程序遇到第一个错误即退出；修复后重新检查，后续错误才会继续显现。

| 顺序 | 错误 | 修订与复核 |
| --- | --- | --- |
| 1 | JSON 最后一条重复 RUN-02，缺少 RUN-03 | 根据 sim-03 恢复标识，其他字段不变；复查记录集合 |
| 2 | TSV 的 RUN-02 为 `0 / missing` | 按 E5:L2、P5:P1:L2 恢复空单元格；保留 missing |
| 3 | 报告把 BT-FILES 写成 `8 files / known` | 恢复未确定值与 conflict，保留双方定位和冲突说明 |

面向模型的修订反馈也应指明记录、字段、证据和影响。例如：“只修订 TSV 的 RUN-02：E5:L2 是未记录，P5:P1:L2 要求保留缺失；value 应为空，state 保持 missing。复查 JSON 和报告同一记录，其他记录不变。”要求模型自述“已核验”不足以完成这一步。

若主 JSON 已正确，也可重新导出到新目录，代替逐个修复派生文件。但执行记录须说明重新生成了哪些文件，并保留故障版；最终交付路径指向实际检查过的版本。

### 内容核对与共同错误

再做一个独立边界实验：复制正确主 JSON，将 RUN-01 的 `1250` 改为 `1`，其他字段不变，导出到新目录并检查。三个文件都会使用 `1 ms`，结构和一致性仍可通过；对照 E5:L1 的 `1.25` 与 P5:P1:L1 的秒单位，则能发现错误。

这一结果说明来源标签“存在”和三格式“相同”的证明范围。最终内容核对仍需回到原文，检查单位、版本、缺失解释和冲突依据。配套[程序验证记录]({{ '/assets/examples/llm-practice/expected/05-validation.md' | relative_url }})保存了实际本地检查，包括故障拒绝、输入保留、已有目录保留和上述共同错误实验；在完成自己的结果后，再阅读[独立核对依据]({{ '/assets/examples/llm-practice/expected/05-reference.md' | relative_url }})与参考三文件。

### 模型输出与约束对照

实际测试使用 Codex CLI 0.160.0 和现有 ChatGPT 登录，请求 gpt-6-sol 与 gpt-6-luna，均指定 low。两个模型在同一修订版完整 Prompt 下，普通输出与 CLI Schema 输出各重复两次，共 8 次；全部通过本例契约，12 条事实字段和必要定位均符合核验依据。模型使用独立空目录，没有工具调用；具体后端快照未在 CLI 事件中暴露。

测试前的一次普通输出也保留了真实失败：事实值正确，定位却写成 `S1 L4`，能通过通用 Schema，但被本地来源标签检查拒绝。原 Prompt 未明确分隔符，随后只补充冒号格式与标签示例。受控对照使用修订版，不把初始单次失败与后续结果当成稳定的因果证明。两模型在这组小样本中没有表现出通过率差异，不能据此排名。原始响应与逐次评分见[补充实测记录]({{ '/assets/examples/llm-practice/expected/05-live-validation.md' | relative_url }})。

## 6. API 结构化输出扩展

普通提示词、JSON mode 与 Structured Outputs 的约束不同：JSON mode 关注合法 JSON，Structured Outputs 可在支持的模型与接口中约束 Schema。后者使用受支持的 Schema 子集；对象字段须列入 `required`，设置 `additionalProperties: false`，可空值用包含 `null` 的类型表达。使用前核对具体模型与接口支持。[OpenAI Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs)

以 Responses API 为例，下面只构造 `text.format` 配置，**不发送请求**。在独立练习项目中读取 Schema，配置可随实际请求的 `text` 参数传入；模型、输入与调用代码须按所用 SDK 和接口另行设置。

```python
import json
from pathlib import Path

# 使用本例基本 Schema；固定记录集合与证据语义仍由本地步骤核对。
schema = json.loads(Path("records.schema.json").read_text(encoding="utf-8"))
text_config = {
    "format": {
        "type": "json_schema",
        "name": "d5_records",
        "strict": True,
        "schema": schema,
    }
}
```

消费结果前还要检查拒绝及未完成状态，例如输出长度限制导致的 `incomplete`；不能把这类结果当作完整记录解析。Schema 合规仍不能保证字段事实正确。现有 Codex 登录已用于前述模型对照和 CLI 输出约束测试；运行环境缺少独立 `OPENAI_API_KEY`，不能用这些结果替代官方 Platform 的请求验证。配套[API 实测脚本]({{ '/assets/examples/llm-practice/projects/05-live-tests/run_api_comparison.py' | relative_url }})在缺少密钥时实际退出 2，未发送请求；服务端接受配置、拒绝与未完成分支仍待验证。支持范围以调用时官方文档为准。[响应异常处理](https://developers.openai.com/api/docs/guides/structured-outputs)

## 7. 常见问题

| 问题 | 原因与处理 |
| --- | --- |
| 上传成功却缺少关键字段 | 先确认实际解析内容、页码和遗漏；不能默认全文已读 |
| TSV 在编辑器里列不齐 | TAB 显示宽度不是数据错误；用分隔符解析核对，避免手动加空格 |
| 检查提示记录集合错误 | 检查重复、遗漏与顺序，不仅检查总行数 |
| 未知布尔值被写成 false | 恢复 null / missing；false 需要原文明确支持 |
| 模型生成报告无法通过固定模板 | 对照模板修订，或从核验后的主 JSON 导出新版本 |
| JSON 与报告都通过却与原文不符 | 结构检查没有裁决原文含义；复核单位、版本与证据关系 |
| 程序拒绝 output-v1 | 输出目录已存在；核对现有内容后使用新版本目录 |
| 模型说已保存但找不到文件 | 核对文件工具、实际路径与文件内容；聊天文本不等于文件产物 |

## 8. 操作速查与实践练习

### 操作速查

| 阶段 | 动作 | 验收结果 |
| --- | --- | --- |
| 输入准备 | 核对来源版本、读取范围与遗漏 | 能说明使用了什么，没有读取什么 |
| 字段映射 | 固定标识、类型、单位、状态与定位 | 缺失、零值和冲突不会互换 |
| 主记录核验 | 对照原文检查 JSON | 值与状态有依据，转换过程可复核 |
| 新版本导出 | `python export_output.py records-draft.json --out output-v1` | 新目录含实际三文件，输入未改写 |
| 文件检查 | `python validate_output.py output-v1` | 12 条记录、字段与固定模板一致 |
| 最终交付 | 打开实际产物，记录绝对路径与验证范围 | 区分文本展示、文件生成和人工事实核验 |

### 实践练习

1. **完整交付**：用完整提取提示词生成主 JSON，核验并导出三文件。验收标准：12 条标识与顺序正确，值、状态、单位和来源一致，检查通过；实际路径与人工核验记录完整。
2. **缺失与零值**：将 RUN-02 的 TSV 值误填为 0，再检查和修复。验收标准：检查指出该条与主 JSON 不一致；恢复空值后通过，RUN-03 的已知零值仍保留。
3. **故障修订**：完成 faulty-v1 的连续检查。验收标准：三类人为错误分别定位，修订后记录集合、TSV 和报告一致；未把它们写成模型实测失败。
4. **共同错误**：把 RUN-01 改为 1 后生成新目录。验收标准：如实记录结构检查仍通过，指出秒转毫秒的错误及两处依据；再修正主记录并另存正确版本。
5. **读取范围**：在单独对话中提供 E5 而不提供 P5，要求提取统一单位的耗时。验收标准：指出单位与符号定义缺口，没有猜测毫秒或把破折号补零；不能把该变体冒充原 D5 完整输入。

### 参考资料

以下官方资料用于核对格式与接口行为，核对日期为 2026-10-05；本例模拟资料不代表真实产品证据。

- [Python json](https://docs.python.org/3/library/json.html)：解析行为、重复键与非标准数值。
- [Python csv](https://docs.python.org/3/library/csv.html)：分隔符、引号与换行处理。
- [JSON Schema 对象](https://json-schema.org/understanding-json-schema/reference/object)：必需字段、额外字段和空值。
- [pypdf 文本提取](https://pypdf.readthedocs.io/en/stable/user/extract-text.html)：PDF 抽取与 OCR 边界。
- [OpenAI Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs)：结构化响应与异常处理。
- [本系列配套资料]({{ '/assets/examples/llm-practice/README.md' | relative_url }})：完整提示词、字段契约、程序、故障练习和独立核对依据。

上一篇：[资料检索与事实核验]({% post_url 2026-10-05-information-retrieval-and-fact-verification %})；导读：[大模型应用基础与学习路径]({% post_url 2026-10-04-llm-application-foundations %})；系列入口：[大模型应用方法与实践]({{ '/series/' | relative_url }}#llm-practice)；下一篇：[Agent Skills 的使用与评估]({% post_url 2026-10-05-agent-skills-usage-and-evaluation %})。
