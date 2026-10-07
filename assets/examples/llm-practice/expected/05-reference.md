# 第五篇独立核对依据

完成自己的提取和检查后再阅读；不要作为被检查模型的输入。三种工具、P5 与 E5 都是教学模拟。参考产物由作者按固定资料整理，再用配套生成器输出，不能称为真实模型返回或工具测试。

| 标识 | value / state | 定位与理由 |
| --- | --- | --- |
| LB-FILES | 2 / known | S1:L4 |
| LB-PROTECT | true / known | S1:L7 明确不修改输入 |
| LB-LICENSE | null / missing | S1:L8 明确未提供许可证 |
| BT-FILES | null / conflict | S2:L4 为 8，S5:L2 为 4，S5:L3 没有更正或取代说明 |
| BT-PROTECT | true / known | S2:L7 |
| BT-LICENSE | MIT / known | S2:L8 |
| RS-FILES | 20 / known | S3:L4 |
| RS-PROTECT | null / missing | S3:L7 明确信息未提供，不能填 false |
| RS-LICENSE | null / missing | S3:L8 |
| RUN-01 | 1250 / known | E5:L1 的 1.25 与 P5:P1:L1 的秒单位；1.25 × 1000 = 1250 ms |
| RUN-02 | null / missing | E5:L2 与 P5:P1:L2 的破折号定义 |
| RUN-03 | 0 / known | E5:L3、P5:P1:L1、P5:P1:L2；已记录零值 |

记录标识、值、状态、单位和来源含义应满足契约；note 可换用准确措辞。若改 note，其他两文件应从相同 JSON 同步生成。`expected/05-output/` 展示一个完整合法版本，不要求独立模型产生逐字相同的 note。

## 实际验证范围

2026-10-05 在 Windows、Python 3.11 的独立临时目录中实际执行配套生成器与只读检查器：正确三文件通过；人为故障分别在标识、TSV 值与报告一致性处被拒绝；重复 JSON 键、NaN、错误字段类型、缺少记录及不存在的定位被拒绝；已有输出目录被保留，输入文件未被修改。参考 JSON 另用本机 JSON Schema 校验库核对过通用结构，读者运行项目无需安装该库。

边界实验把 `RUN-01` 从 1250 改为 1，再从同一 JSON 生成三文件：结构与一致性检查仍可通过；对照 P5 的秒单位和 E5 的 1.25 可发现换算错误。这个结果说明检查器没有事实裁决能力，不是参考答案允许 1 ms。实际执行记录中的模型字段不适用于上述程序检查；这段首次程序验证未开展模型对照、API 请求、PDF/OCR 或虚构工具运行；后续独立补测保存在 `expected/05-live-validation.md`，不改变本节的程序检查边界。

## 故障修订

故障 JSON 最后一条重复 `RUN-02`，应恢复 `RUN-03`。重新检查后，TSV `RUN-02` 的零值与主记录的缺失冲突；改回空单元格。最后，报告的 `BT-FILES` 应恢复未确定值和 conflict，保留双方定位。既可局部修复，也可从正确 JSON 导出新目录；后一方式须如实记录重新生成过程。
