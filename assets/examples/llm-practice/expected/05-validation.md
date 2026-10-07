# 第五篇程序验证记录

本文件保留第五篇首次纯程序验证的历史状态；后续 PDF/OCR 与模型实测另见 `expected/05-live-validation.md`，不覆盖原始日志。

日期：2026-10-05；系统：Windows；Python：3.11.9。

来源均为教学模拟，JSON 为作者整理的参考主记录。以下命令实际在独立临时目录执行，退出码 0 表示程序通过，1 表示按预期拒绝。路径以 TEMP 替代临时目录，便于复核；不是模型运行记录。

```text
export_output.py records-draft.json --out output-v1 => 0: WROTE: TEMP\output-v1; records.json, records.tsv, report.md / Run validate_output.py on this directory, then review the sources manually.
validate_output.py output-v1 => 0: PASS: 12 records; structure, reference labels and file consistency. / Manual review required: source meaning, unit conversion and factual support.
export_output.py records-draft.json --out output-v1 => 1: FAIL: [WinError 183] 当文件已存在时，无法创建该文件。: 'C:\\Users\\17334\\AppData\\Local\\Temp\\llm-ch05-9oycm3cc\\output-v1'
validate_output.py faulty-v1 => 1: FAIL: record_id 重复
validate_output.py faulty-v1 => 1: FAIL: TSV RUN-02 与 JSON 不一致
validate_output.py faulty-v1 => 1: FAIL: Markdown 与 JSON 的固定模板不一致
validate_output.py faulty-v1 => 0: PASS: 12 records; structure, reference labels and file consistency. / Manual review required: source meaning, unit conversion and factual support.
export_output.py bool-as-int.json --out bool-as-int => 1: FAIL: LB-FILES: value 类型错误
export_output.py missing-row.json --out missing-row => 1: FAIL: 记录数量必须为 12
export_output.py bad-ref.json --out bad-ref => 1: FAIL: LB-FILES: 来源定位不存在
export_output.py missing-to-zero.json --out missing-to-zero => 1: FAIL: RUN-02: missing/conflict 的 value 必须为 null
export_output.py extra-key.json --out extra-key => 1: FAIL: 第 1 条记录的键不匹配
export_output.py duplicate-key.json --out duplicate-key => 1: FAIL: JSON 重复键：schema_version
export_output.py nan.json --out nan => 1: FAIL: JSON 非标准数值：NaN
export_output.py coherent-wrong-unit.json --out wrong-unit => 0: WROTE: TEMP\wrong-unit; records.json, records.tsv, report.md / Run validate_output.py on this directory, then review the sources manually.
validate_output.py wrong-unit => 0: PASS: 12 records; structure, reference labels and file consistency. / Manual review required: source meaning, unit conversion and factual support.
export_output.py serialization-boundary.json --out serialization => 0: WROTE: TEMP\serialization; records.json, records.tsv, report.md / Run validate_output.py on this directory, then review the sources manually.
validate_output.py serialization => 0: PASS: 12 records; structure, reference labels and file consistency. / Manual review required: source meaning, unit conversion and factual support.
```

正确输出与发布参考文件逐字节一致；主 JSON 未被修改；已有输出目录的三文件哈希未变化。通用 Schema 另经本机 jsonschema 校验，读者程序仅需标准库。

`wrong-unit` 与 `serialization` 是边界测试输入，不是参考事实。三格式一致的错误换算仍通过，已知 false 可以正确序列化，但不能用于来源未提供的属性。未执行 API、PDF/OCR、真实工具或模型对照测试。
