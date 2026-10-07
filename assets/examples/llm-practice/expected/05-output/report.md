# 文件整理报告

需求版本：D5-v1

范围：三种虚构工具的九条属性及三条教学模拟实验记录；不作性能排名。

## 工具属性

| 标识 | 工具与版本 | 字段 | 值与单位 | 状态 | 来源 |
| --- | --- | --- | --- | --- | --- |
| LB-FILES | LogBrief 1.2 | max_input_files | 2 files | known | S1:L4 |
| LB-PROTECT | LogBrief 1.2 | input_unchanged | true | known | S1:L7 |
| LB-LICENSE | LogBrief 1.2 | license | 未确定 | missing | S1:L8 |
| BT-FILES | BatchTrace 0.9 | max_input_files | 未确定 | conflict | S2:L4;S5:L2;S5:L3 |
| BT-PROTECT | BatchTrace 0.9 | input_unchanged | true | known | S2:L7 |
| BT-LICENSE | BatchTrace 0.9 | license | MIT | known | S2:L8 |
| RS-FILES | RunSheet 2.0 | max_input_files | 20 files | known | S3:L4 |
| RS-PROTECT | RunSheet 2.0 | input_unchanged | 未确定 | missing | S3:L7 |
| RS-LICENSE | RunSheet 2.0 | license | 未确定 | missing | S3:L8 |

## 模拟实验记录

| 标识 | 工具与版本 | 字段 | 值与单位 | 状态 | 来源 |
| --- | --- | --- | --- | --- | --- |
| RUN-01 | BatchTrace 0.9 | elapsed_ms | 1250 ms | known | E5:L1;P5:P1:L1 |
| RUN-02 | BatchTrace 0.9 | elapsed_ms | 未确定 | missing | E5:L2;P5:P1:L2 |
| RUN-03 | BatchTrace 0.9 | elapsed_ms | 0 ms | known | E5:L3;P5:P1:L1;P5:P1:L2 |

## 记录说明

- LB-FILES：一次任务最多 2 个文件。
- LB-PROTECT：原文明确不修改输入日志。
- LB-LICENSE：该行明确未提供许可证；保持未知。
- BT-FILES：S2:L4 为 8，S5:L2 为 4；未说明更正、取代或适用条件。
- BT-PROTECT：原文明确不修改输入日志。
- BT-LICENSE：原文明确许可证为 MIT。
- RS-FILES：一次任务最多 20 个文件。
- RS-PROTECT：该行明确未提供是否修改输入日志的信息。
- RS-LICENSE：该行明确未提供许可证。
- RUN-01：教学模拟记录 sim-01：1.25 s × 1000 = 1250 ms。
- RUN-02：教学模拟记录 sim-02：标记为“未记录”, 保留缺失。
- RUN-03：教学模拟记录 sim-03：0 s 转为 0 ms，是已记录的零值。

检查边界：来源标签存在与文件一致性不代表事实已核验；须回到原文检查含义与单位。
