# 第五篇补充实测

这是独立于六文件主练习项目的补测工具。PDF 内容仍为教学模拟，文件解析和模型响应是实际执行结果。参考答案只在模型输出之后由评分程序读取，没有进入模型输入。原始输入、原始响应、评分及人工 OCR 校正分别保存于 `snapshots/05-live-validation/`。

## 实际范围

- PDF：同内容的一页文本版与一页无文字层栅格版，实际生成、抽取并用 Poppler 渲染；逐页目视检查。
- OCR：Windows 自带 `Windows.Media.Ocr`，已安装的 `zh-Hans-CN`，输入为 150 dpi 渲染图。没有安装 OCR 工具或语言包；存在真实识别错误。
- JSON 模型对照：Codex CLI 0.160.0，现有 ChatGPT 登录；请求 `gpt-6-sol` 和 `gpt-6-luna`，均为 low；每模型普通输出与 `--output-schema` 输出各两次。使用相同完整 Prompt、独立空目录和新调用，忽略用户配置，没有工具调用。后端具体模型快照未在 CLI 事件中暴露。
- TSV/Markdown：两个模型各一次，输入为同一份经核验的实际模型 JSON 与同一份后续提示词。代码块内容保存为文件后通过固定检查器；未修复模型内容。
- Platform API：缺少 `OPENAI_API_KEY`，脚本退出 2，未发送请求。Codex 登录与 CLI Schema 测试不能作为 `api.openai.com/v1/responses` 的验证。

少量固定样本不用于性能排名、稳定性推断或产品能力比较。PDF 是清晰页面的人工栅格化，不涵盖真实扫描噪声、歪斜拍照、多页复杂表格或全部 OCR 工具。

## 文件与依赖

| 文件 | 职责 |
| --- | --- |
| `make_pdf_fixtures.py` | 用 reportlab、PyMuPDF、pypdf 与 Poppler 生成、渲染和抽取实际 PDF |
| `run_windows_ocr.ps1` | Windows PowerShell 5.1 的 WinRT OCR；保存原始文字与词坐标，不自动改错 |
| `evaluate_records.py` | 后置核验格式、七个事实字段及必要定位，note 的准确性另行人工复核 |
| `run_codex_comparison.py` | 独立调用两模型、两模式、两次重复；保留原响应、事件、用量与评分 |
| `run_delivery_comparison.py` | 使用同一份核验后主 JSON，测试模型转写 TSV/Markdown |
| `run_api_comparison.py` | 标准库调用官方 Platform Responses API，显式检查完成、拒绝、HTTP 错误与未完成状态 |

Python 3.10 或更高版本。PDF 脚本实际依赖版本见保存的 `pdf-result.json`；程序不会安装依赖。Windows 默认使用本机宋体，字体文件不随配套分发。其他环境须指定可用字体与 Poppler；没有完成该环境实测。

`run_windows_ocr.ps1` 用 UTF-8 BOM 保存，供 Windows PowerShell 5.1 正确读取含中文的源码；输出 JSON 与其他数据仍为 UTF-8 无 BOM。不能用“所有文件无 BOM”的要求替代这项脚本环境差异。

## PDF 与 OCR 复现

复制完整配套目录到博客以外的练习目录，保留 `projects/`、`prompts/`、`expected/` 的相对关系，再进入 `projects/05-live-tests`。选择全新输出目录，以下为连续步骤；替换示例绝对路径为自己的练习路径：

```text
python make_pdf_fixtures.py --out C:/llm-lab/pdf-test
powershell.exe -NoProfile -File run_windows_ocr.ps1 -ImagePath C:/llm-lab/pdf-test/raster-report-render.png -OutputPath C:/llm-lab/pdf-test/raster-ocr.json
```

第一条拒绝已有输出目录。第二条会写指定 JSON 路径，应使用新文件名；只读取图片。执行后回看真实 PDF 或渲染图，另存人工校正记录，不覆盖原始 OCR，也不能把 OCR 漏识别形成的空字符串直接判为缺失。

## 模型与文件转写复现

以下独立测试会通过当前 Codex 登录发出真实模型调用并消耗相应用量。更换模型时确认自己的访问权限；需要比较推理设置时另设实验，不混入本轮。

```text
python run_codex_comparison.py --models gpt-6-sol gpt-6-luna --repeats 2 --effort low --out C:/llm-lab/codex-test
```

参考答案只由父级评分程序读取。模型工作目录为空，输入来自 `prompts/05-01-extract.txt`；普通模式的 Prompt 中也包含完整 Schema，Schema 模式另加 CLI 输出约束。这是调用约束的对照，不能宣称测试了不带字段说明的自由聊天。

核验一份实际模型 JSON 后，再测试文件转写；两个模型收到完全相同的主记录：

```text
python run_delivery_comparison.py --models gpt-6-sol gpt-6-luna --input C:/llm-lab/codex-test/model-1-plain-01/records.json --out C:/llm-lab/delivery-test
```

转写程序只拆出提示词约定的两个代码块，保留真实 TAB、空值与文本，恢复围栏行前的换行，不改字段、数值或报告文字。模型与程序执行仍分别记录。

## Platform API 复现条件

在自己的运行环境配置 `OPENAI_API_KEY`，不要写入源码、Prompt、命令行参数或公开记录。使用账户实际可访问、支持本例 Schema 与 low 推理设置的两个模型，替换占位模型名后运行：

```text
python run_api_comparison.py --models YOUR_API_MODEL_A YOUR_API_MODEL_B --out C:/llm-lab/platform-api-test
```

该脚本固定使用官方 HTTPS 目的地与默认 TLS 验证，保存无鉴权头的请求体和结果；遇到鉴权、权限或限流错误停止，不将失败当作 Schema 合规。拒绝及未完成结果不进入普通记录评分。当前仅验证缺少密钥的本地退出分支，尚未验证成功的远端调用、拒绝、截断或限流分支。

官方行为参考 [Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs)、[Codex 评估示例](https://developers.openai.com/blog/eval-skills)和 [Windows OCR](https://learn.microsoft.com/en-us/uwp/api/windows.media.ocr.ocrengine.recognizeasync?view=winrt-20348)。实际结果以本地保存的响应和验证记录为准。
