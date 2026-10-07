# 第五篇独立练习项目

工具、报告摘录和实验记录均为教学模拟；实际运行下面的程序只验证文件生成与检查，不是工具性能实验或模型评估。项目使用 Python 3.10 或更高版本，仅依赖标准库。发布前实际运行环境为 Windows、Python 3.11。

## 文件职责

| 文件 | 职责 |
| --- | --- |
| `sources.txt` | 完整 D5-v1 和 S1、S2、S3、S5、P5、E5；P5 是文字摘录，没有 PDF 原件 |
| `contract.json` | 固定 12 条记录的标识、顺序、字段类型、单位与整数下限；没有答案数值 |
| `records.schema.json` | JSON 通用结构描述；不能单独检查证据含义、记录集合或跨文件一致性 |
| `export_output.py` | 读取 JSON，创建全新的目录并生成 JSON、TSV、Markdown |
| `validate_output.py` | 只读检查器，逐项检查本练习契约、来源标签与固定报告模板 |
| `README.md` | 准备、连续操作、覆盖边界和验收说明 |

压缩包只包含以上六份文件，不包含参考答案、故障产物或运行输出。把压缩包解压到博客仓库以外的新目录，并进入解压后的 `05-file-output`。先执行 `python --version`，确认版本与命令。Windows 可用 `py -3` 替代以下 `python`；Bash 环境可用 `python3`，但后者未在本篇实际运行。

## 输出契约

主文件顶层只有 `schema_version`、`demand_id`、`records`，前两者为 `1.0`、`D5-v1`。每条记录的九个键与 TSV 表头依次为：

```text
record_id tool version field value unit state source_refs note
```

这里以空格展示键名；真正 TSV 使用 TAB 分隔，不能用空格代替。记录顺序由 `contract.json` 确定。JSON 对象键顺序不影响检查，TSV 列与各格式记录顺序固定。文件用 UTF-8，无 BOM；生成器写 LF，检查器允许读取 CRLF。

- `max_input_files`：正整数，单位 `files`。
- `input_unchanged`：布尔值，单位 `none`；`false` 表示确认会修改输入，不能用于“资料未提供”。
- `license`：非空单行字符串，单位 `none`。
- `elapsed_ms`：非负整数，单位 `ms`；本例输入乘以 1000 后都是整数，不涉及舍入。
- `known` 要求有相应类型的值；`missing`、`conflict` 要求 JSON `null`。两种状态都保留 `source_refs` 和解释，不能用空字符串替代 JSON `null`。
- 来源使用原文标签，如 `S2:L4`、`P5:P1:L1`；数组非空、无重复，标签必须真实存在。缺失可以引用明确说明未提供的行。本例没有“整份文件未提及”的情况。
- 字符串为单行非空文本，不含控制字符；注释允许逗号、普通双引号和管道符。不能在 note 中插入 TAB 或换行。

TSV 的 `value`：null 写空单元格，布尔写小写 `true`/`false`，整数写十进制规范形式，字符串原样保存。`source_refs` 以 `;` 连接；本例来源标签不含分号。使用 `csv` 的 TAB 方言和引号转义。状态列使空值可区分为缺失或冲突，空值不能解读为零。

报告模板由 `validate_output.py` 的 `render_report` 完整定义：固定标题、需求版本、范围说明、工具属性表、模拟实验表、逐条记录说明及检查边界。模型手工生成的报告也须遵守这个模板；该检查器不能评判任意自由格式的报告。单元格中的 `&`、`<`、`>`、反斜线和管道符按函数转义。

## 连续操作

1. 阅读来源与字段契约，使用配套 `05-01-extract.txt` 获取主 JSON。没有文件工具时，将模型展示的 JSON 对象复制到新建的 `records-draft.json`，去掉代码围栏与解释文字。实际创建文件后再记为已保存。不要将 `expected/` 参考答案提供给被检查模型。
2. 按来源核验每条记录的值、状态、单位和定位；先修正主 JSON。文件内容合法仍可能包含错误换算。
3. 从经过核验的主 JSON 生成新版本，随后检查：

```text
python export_output.py records-draft.json --out output-v1
python validate_output.py output-v1
```

这两条按顺序执行。第一条实际写入 `output-v1/records.json`、`records.tsv`、`report.md`；第二条不修改文件。生成器拒绝已存在的输出目录，原输入也不被修改。后续修订另存 `records-v2.json`，再用 `--out output-v2`。如果写入中途失败，可能留下部分文件；检查目录内容并选择一个新目录，不声称已完成交付。

成功检查会显示：

```text
PASS: 12 records; structure, reference labels and file consistency.
Manual review required: source meaning, unit conversion and factual support.
```

`PASS` 只涵盖检查器列出的范围。它不证明真实产品属性，也不证明模型读取了文件。`WROTE` 只是程序报告，交付前还须打开三个实际文件，记录绝对路径，并按原资料复核。

## 检查边界

检查器不依赖第三方 JSON Schema 库，也不在运行时读取 `records.schema.json`；它显式实现固定契约，并增加唯一标识、集合与顺序、字段精确类型、值与状态关系、真实来源标签、TSV 规范序列化和固定报告一致性检查。维护字段时须同步契约、Schema、检查器、提示词、参考产物和文章。

故障样例位于配套资料的 `cases/05-faulty-output/`，应复制到独立练习目录，不能直接修改博客中的原件。修复过程中先检查 JSON，再检查 TSV，最后检查报告。人为植入的故障不是实际模型失败。

把所有文件中的某一数值同时改错，可能仍通过检查。必须核验 E5 的原始数值和 P5 的单位说明，尤其区分未记录与零值。参考产物位于 `expected/05-output/`，在完成自己的结果后读取；不是被检查模型的输入。
