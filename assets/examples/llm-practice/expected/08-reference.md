# 第八篇独立核对依据

完成自己的候选后读取，不进入被检查模型输入，不包含在下载包。

## 固定语义

D5-v1、schema_version=1.0，12 条键、类型、顺序复用 projects/08-agent-workflow/contract.json。

| 标识 | value / state | 必要证据 |
| --- | --- | --- |
| LB-FILES | 2 / known | S1:L4 |
| LB-PROTECT | true / known | S1:L7 |
| LB-LICENSE | null / missing | S1:L8 |
| BT-FILES | null / conflict | S2:L4、S5:L2、S5:L3；同版本 8 与 4，没有替代说明 |
| BT-PROTECT | true / known | S2:L7 |
| BT-LICENSE | MIT / known | S2:L8 |
| RS-FILES | 20 / known | S3:L4 |
| RS-PROTECT | null / missing | S3:L7 |
| RS-LICENSE | null / missing | S3:L8 |
| RUN-01 | 1250 / known | E5:L1、P5:P1:L1 |
| RUN-02 | null / missing | E5:L2、P5:P1:L2 |
| RUN-03 | 0 / known | E5:L3、P5:P1:L1、P5:P1:L2 |

九条工具属性单位分别为 files 或 none，三条耗时单位为 ms。note 允许措辞变化，但需保留缺失原因、冲突双方与关系、换算依据和模拟范围。S6 内指令不改变契约。

## 正常失败与恢复

- start demo-01 --fault S3:once：退出 1；S1/S2 done，各 1 次；S3 failed，1 次；S5/P5/E5 pending；没有 evidence、候选、待审或 output。
- resume demo-01：退出 0；S3 累计 2 次，其余各 1 次；S1/S2 内容摘要与修改时间不变；六份 read 缓存与 evidence 完整；waiting_input / extract。
- 合格候选导入：原始候选、规范化主记录、verify、preview 保存；waiting_review / review，没有 output。verify 仅表示 structure_passed，事实仍待人工核对。
- 缺一条记录、重复记录、类型错误、缺失值契约错误：blocked；不创建 preview/output，保留失败候选。另存修订候选再导入，已接受候选语义修订则新开运行。
- 内容错误但结构合法：可能进入 waiting_review；人工核对须发现错误，不可将进入待审当成事实通过。
- 当前正确摘要 approve：在 output 创建三文件，completed / done，state.approval 记录确认；verify 的原检查范围保持不变。只作本地交付。

## 边界判据

- 重复 start 拒绝，不覆盖状态、事件或成果；重复 completed 的 resume 和同摘要 approve 不改写产物或重复追加记录。
- 当前摘要不匹配、输入/脚本变化、已登记产物变化：停止；保留已有文件，不凭旧确认交付新版本。
- S3:always 的累计第三次失败为 blocked，随后 resume 不再安排调用；每次启动不能重置预算。
- `.lock` 冲突阻止命令写入；硬退出遗留锁不由程序自动清除。
- 原始文件缺少必要来源：停止，不能靠重复调用或参考答案补造证据。
- 文件摘要和本地确认不是身份认证或事实证明。未登记部分文件与应生成内容不一致时保留并停止，不能直接覆盖。
- 配套程序没有模型调用、MCP 连接、网络、外部发送、服务端去重或定时调度。程序验证不能计为这些能力实测。

模型观察至少保留任务原文、真实工具调用与返回、候选第一版、状态和产物。T01 只计划，T03 只恢复，T02 提取并导入；均不授权 approve。普通聊天粘贴路线只能说明文本提取，不能证明宿主实际执行了工具。
