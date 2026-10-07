# 第五篇 API、PDF/OCR 与模型补测

日期：2026-10-05。系统 Windows，Python 3.11.9，Codex CLI 0.160.0。原资料为教学模拟，以下文件操作、OCR 和模型调用实际执行。主 JSON 参考答案只由后置评分程序读取；模型输入不含参考答案。原始响应未修复，结果不能扩大为模型排名或总体稳定性结论。

## 结果概览

| 分支 | 实际结果 | 范围 |
| --- | --- | --- |
| 文本 PDF | 一页，pypdf 抽取 260 字符，关键标识、1.25、破折号、0 和单位说明保留 | 实际生成的清晰教学 PDF |
| 栅格 PDF | 一页，pypdf 抽取 0 字符 | 同内容整页图像，没有隐藏文字层 |
| Windows OCR | zh-Hans-CN，150 dpi，1241 × 1754，21 行、372 字符 | 原始结果存在错误，不能直接作为完成记录 |
| JSON 模型对照 | 两模型 × 两模式 × 两次，共 8 次，全部通过固定契约、12 条事实字段与必要定位检查 | 修订后相同 Prompt，low；没有工具调用 |
| TSV/Markdown 转写 | 两模型各一次，三文件一致性均通过 | 相同核验后模型 JSON；实际保存代码块，未改模型内容 |
| Platform API | 缺少 OPENAI_API_KEY，脚本本地退出 2；远端请求 0 次 | 未验证 Responses API 成功、拒绝或未完成响应 |

API 未完成的原因是运行环境缺少独立密钥。现有 Codex 使用 ChatGPT 登录，真实模型对照与 CLI Schema 输出已执行，但不能据此宣称官方 Platform 的 `text.format` 请求已验证。

## PDF 与 OCR 证据

独立制作了 `digital-report.pdf` 和 `raster-report.pdf`，使用 P5/E5 的单位与三条记录内容，另加“独立实测夹具”说明；它们不是此前未提供的 P5 原件，也不是外部产品的实测报告。文本 PDF 字体已嵌入；栅格版只含整页图像。两份保存后的 PDF 均用 Poppler 渲染，并实际目视检查，无缺字、重叠或表格裁切。

原始 OCR 文字按列返回：先列出三个 run_id，再给数值和状态；`duration` 表头与破折号漏识别。可观察错误包括：

- `1.25` 被拆成 `1. 25`。
- `sim-02`、`sim-03` 分别写成 `sim—02`、`sim—03`。
- `P1:L1` 变成 `PI：LI`，说明不能直接用识别结果建立可靠行标签。
- `已记录` 中部分“已”被认作“己”。

回看实际渲染页后，另存 `reviewed-rows.json` 与 TSV：sim-01 为 1250 ms，sim-02 为 null / missing，sim-03 为 0 ms / known。校正依赖原页，不把 OCR 空单元格自动解释为缺失；原始 `raster-ocr.json` 与 `raster-ocr-raw.txt` 保留不改。

本例是人工制作的清晰一页栅格资料，不覆盖歪斜、拍照、噪声、跨页表格或其他 OCR 引擎。没有安装新工具、修改语言包或调用联网 OCR。

## 模型输入与评分

初始普通输出调用使用原版 05-01 Prompt：JSON 能解析，并通过通用 Schema；12 条事实字段均正确，但定位写成 `S1 L4` 等空格形式。本地检查器以“来源定位不存在”拒绝。此失败与原始 Prompt 一起保存，不改成作者植入错误，也不丢弃失败结果。

原 Prompt 没有明确给出定位分隔符，随后补充“英文冒号”和 `S1:L4`、`P5:P1:L1` 的格式示例，未加入事实答案。正式受控对照使用这一修订版，不能把初始单次调用与后续结果视作稳定的 Prompt 因果实验。

| 请求模型 | 输出约束 | 重复 | 契约通过 | 事实字段 | 必要定位 |
| --- | --- | --- | --- | --- | --- |
| gpt-6-sol | 普通输出 | 2 | 2/2 | 每次 12/12 | 每次 12/12 |
| gpt-6-sol | CLI Schema | 2 | 2/2 | 每次 12/12 | 每次 12/12 |
| gpt-6-luna | 普通输出 | 2 | 2/2 | 每次 12/12 | 每次 12/12 |
| gpt-6-luna | CLI Schema | 2 | 2/2 | 每次 12/12 | 每次 12/12 |

CLI 请求指定相同 low 设置；每次使用新调用、独立空目录、忽略用户配置，没有工具调用。普通模式的完整 Prompt 也包含 Schema，Schema 模式额外使用 `--output-schema`。这里记录的是请求模型别名，CLI 事件未暴露后端具体快照；没有把 ChatGPT 网页产品、其他推理设置或 API 账户混为同一环境。

格式评分包含固定键、精确类型、状态、单位、标识集合、顺序和真实定位标签。事实评分单独比较 record_id、tool、version、field、value、unit、state，note 允许准确措辞；必要定位按预先核验的参考集合检查是否覆盖。首次两模型的 note 另经人工对照，没有将模型自检作为证据。

转写分支将 gpt-6-sol 第一次普通输出的完整主 JSON 对照来源核验后，显式加入同一份 05-02 后续提示词。两模型各独立调用一次；不是依赖原会话记忆。仅分离约定代码块并保存真实 TAB 与换行，原始响应不修复；两组三文件均通过固定检查器。

这组小样本未观察到两模型或两输出约束的通过率差异。不能据此推断谁更强，不能用通用 Schema 通过证明定位语义或事实正确。

## 原始文件与复现入口

- `snapshots/05-live-validation/pdf/`：实际两份 PDF、渲染图、文字抽取、OCR 原始结果、人工校正及依赖版本。
- `snapshots/05-live-validation/initial-call/`：原版 Prompt、初始模型响应、CLI 事件和失败评分。
- `snapshots/05-live-validation/codex-json/`：受控 Prompt、Schema、八次原始响应与逐次评分。
- `snapshots/05-live-validation/codex-delivery/`：共同输入、两次原始回复和保存后的三文件。
- `snapshots/05-live-validation/platform-api-status.json`：缺少密钥、未发请求的状态。
- `snapshots/05-live-validation/manifest.json`：验证范围与原始文件 SHA-256。
- `projects/05-live-tests/README.md`：完整复现命令、脚本、依赖及 Platform API 的后续条件。

首次纯程序验证保留在 `expected/05-validation.md`，不以本次补测覆盖其历史状态。配置独立 API Key 后，应另存一轮 Platform 原始请求、响应和评分，再更新尚未验证的服务端分支。
