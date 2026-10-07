# F1-v1：事实教学快照

输入：D1 版本 1 与 S1—S3。按固定资料编写并由写作侧核对，不是独立模型运行产物；接收方仍须复核。

R1—R6、U1、U2 在本表中仅映射原始属性，不提前写适用性。LB、BT、RS 各 8 行，共 24 个唯一记录标识。

| 记录标识 | 工具 | 属性 | 资料值 | 依据 |
| --- | --- | --- | --- | --- |
| LB-R1 | LogBrief | 平台 | Windows 11、Ubuntu 24.04 | S1:L3 |
| LB-R2 | LogBrief | 输入类型 | UTF-8 纯文本日志 | S1:L2 |
| LB-R3 | LogBrief | 文件数量及单文件大小 | 最多 2 个，每个不超过 5 MB | S1:L4 |
| LB-R4 | LogBrief | 输出列、单位及缺失规则 | CSV；run_id、status、elapsed_ms；毫秒；缺失留空、不填 0 | S1:L5–L6 |
| LB-R5 | LogBrief | 网络连接 | 不连接网络，本地处理 | S1:L7 |
| LB-R6 | LogBrief | 输入保护 | 不修改输入日志 | S1:L7 |
| LB-U1 | LogBrief | 图形界面 | 不提供 | S1:L8 |
| LB-U2 | LogBrief | 许可证 | 未提供 | S1:L8 |
| BT-R1 | BatchTrace | 平台 | Windows 11、Ubuntu 24.04 | S2:L3 |
| BT-R2 | BatchTrace | 输入类型 | UTF-8 纯文本日志 | S2:L2 |
| BT-R3 | BatchTrace | 文件数量及单文件大小 | 最多 8 个，每个不超过 10 MB | S2:L4 |
| BT-R4 | BatchTrace | 输出列、单位及缺失规则 | CSV；run_id、status、elapsed_ms；毫秒；缺失留空、不填 0 | S2:L5–L6 |
| BT-R5 | BatchTrace | 网络连接 | 不连接网络，本地处理 | S2:L7 |
| BT-R6 | BatchTrace | 输入保护 | 不修改输入日志 | S2:L7 |
| BT-U1 | BatchTrace | 图形界面 | 不提供 | S2:L8 |
| BT-U2 | BatchTrace | 许可证 | MIT | S2:L8 |
| RS-R1 | RunSheet | 平台 | 仅 Windows 11，不支持 Ubuntu 24.04 | S3:L3 |
| RS-R2 | RunSheet | 输入类型 | UTF-8 纯文本日志 | S3:L2 |
| RS-R3 | RunSheet | 文件数量及单文件大小 | 最多 20 个，每个不超过 10 MB | S3:L4 |
| RS-R4 | RunSheet | 输出列、单位及缺失规则 | CSV；run_id、status、elapsed_ms；毫秒；缺失填 0 | S3:L5–L6 |
| RS-R5 | RunSheet | 网络连接 | 不连接网络，本地处理 | S3:L7 |
| RS-R6 | RunSheet | 输入保护 | 是否修改输入日志未提供 | S3:L7 |
| RS-U1 | RunSheet | 图形界面 | 提供 | S3:L8 |
| RS-U2 | RunSheet | 许可证 | 未提供 | S3:L8 |
