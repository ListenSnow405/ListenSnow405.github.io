# 第八篇：可恢复的资料整理工作流

版本：`08-workflow/1.0`。输入为 D5-v1、S1/S2/S3/S5/P5/E5，语义与第五至七篇相同。三种工具、报告文字摘录和实验记录均为教学模拟资料。sources.txt 还保留 D5 与 S6，程序只缓存六份必要来源；S6 的指令干扰不进入正常证据包。

## 环境与范围

Python 3.10+，只有标准库；无需安装依赖、连接 MCP、配置 API 密钥或调度任务。在博客、真实资料目录和其他练习之外新建目录，解压 `08-agent-workflow.zip`，进入其中的 `08-agent-workflow/`。运行只读取本目录固定文件，只创建/更新本目录 `runs/<run_id>/`。输入、已登记产物和其他运行不覆盖。不要在博客源码副本运行。

| 文件 | 职责 |
| --- | --- |
| sources.txt、contract.json | 完整原资料、12 条字段契约 |
| workflow.py | 来源检查点、故障注入、有限重试、候选导入、待审和本地交付 |
| validate_output.py | 沿用第五篇的只读结构与文件一致性检查器 |
| tasks/08-01-plan.txt | 核对现有运行后只形成计划 |
| tasks/08-02-extract.txt | 单 Agent 提取候选，或返回文本由读者保存 |
| tasks/08-03-recover.txt | 有限授权下恢复读取，不进入确认交付 |
| run-record.md | 空白程序/模型/人工检查记录 |
| SHA256SUMS.txt | 固定文件摘要；检查复制是否变化，不证明来源安全 |

下载包不含候选、答案、已运行目录或已经完成的验收记录。程序不生成提取答案；模型或读者提供候选。它是固定工作流辅助程序，不是独立自主 Agent。

## 主流程：PowerShell

初始状态：当前目录为新解压的 `08-agent-workflow/`，没有 `runs/demo-01/`。

```powershell
python workflow.py start demo-01 --fault S3:once
```

预期退出 1、status=failed、stage=read；S1/S2 已缓存，S3 第一次调用被注入超时，后续未执行。此故障发生在程序中的来源读取接口，不是实际磁盘、MCP 或网络故障。

```powershell
python workflow.py resume demo-01
python workflow.py status demo-01
```

预期 status=waiting_input、stage=extract；S3 累计 2 次，其余来源 1 次。已有 S1/S2 不重新调用或改写。`evidence.txt` 包含六份原文及原定位。结构、引用与事实契约以 contract.json 为准，不使用大纲早期抽象字段。

提交 tasks/08-02-extract.txt。具备文件与终端能力的宿主可以创建 `runs/demo-01/inbox/candidate-v1.json` 并导入；普通聊天读者把 JSON 文本保存到这个新文件，UTF-8 无 BOM，无 Markdown 围栏。任务只允许保存一个候选文件和执行导入，不允许修改状态或自行批准。

```powershell
python workflow.py resume demo-01 --candidate inbox/candidate-v1.json
```

合格结构得到 waiting_review。查看 `preview/records.json`、`preview/records.tsv`、`preview/report.md` 和 evidence.txt，逐条核对来源支持、冲突、缺失、零值与单位。程序不替代这一语义审查。格式不合格则 blocked，在 inbox 另存新候选版本再导入；已经通过导入的候选保持不变，事实修订使用新 run_id。

**以下命令只由读者完成事实核对后执行**。确认的是这个运行中具体待审稿的摘要，不是其他模型输出或未来的版本：

```powershell
$reviewDigest = (Get-Content -LiteralPath .\runs\demo-01\state.json -Raw | ConvertFrom-Json).review_digest
python workflow.py approve demo-01 --digest $reviewDigest
python validate_output.py .\runs\demo-01\output
```

completed 表示本次本地 output 三文件已创建并记录显式确认；不表示对外发送、发布或独立事实证明。`verify.json` 永远保留程序实际检查范围 `structure_passed / pending_human_review`，批准另存 state.approval。输入或待审稿之后变化会被摘要复核拒绝，不能拿旧确认交付新内容。

## Bash 的等价路径

在另一个新解压目录执行同一 Python 流程；相对路径使用 `/`。主命令和运行标识与 PowerShell 相同，不能在同一目录重复执行 start。

```bash
python3 workflow.py start demo-01 --fault S3:once
python3 workflow.py resume demo-01
python3 workflow.py status demo-01
# 提交提取任务并把结果保存在新候选文件后：
python3 workflow.py resume demo-01 --candidate inbox/candidate-v1.json
```

人工核对完成后才读取当前摘要并交付：

```bash
review_digest=$(python3 -c 'import json; print(json.load(open("runs/demo-01/state.json", encoding="utf-8"))["review_digest"])')
python3 workflow.py approve demo-01 --digest "$review_digest"
python3 validate_output.py runs/demo-01/output
```

Windows 为本次实际程序验证环境，Bash 为等价命令说明，未进行 Linux 原生运行。

## 检查点与故障实验

状态文件可以更新，事件日志只追加；来源缓存、accepted 候选、verify、preview 和 output 只创建。恢复首先核对固定输入与脚本摘要，再检查所有已登记文件摘要。再次 resume 已完成运行不会重复生成；再次以同摘要 approve 不改写输出。源码变更、候选语义修订与不同输入都应新建运行。

`--read-attempts` 设置一次命令为每份尚未完成来源安排的最多调用数，默认 1；各来源跨命令累计上限固定为 3。重试等待为 0.2、0.4 秒，属于便于练习的退避值，不是线上服务策略。`start retry-01 --fault S3:once --read-attempts 2` 会在一个命令内完成读取；`start stop-01 --fault S3:always --read-attempts 3` 会在第三次失败后 blocked，后续 resume 不再调用 S3。失败时也要查看状态，而非只凭退出码判断。

JSON 结构错误、来源缺失、权限/文件错误、摘要变化和累计耗尽不做盲目重试。已有未登记文件若与重建内容完全一致可登记为检查点，部分写入或不同内容会停止并保留现场；不能强行覆盖。硬退出可能留下 .lock，先人工确认没有运行进程并检查现场，再决定是否移走锁；程序不会自行解除。这只是单机串行练习，不能作为多机并发、断电事务、对抗性文件篡改或外部动作恰好执行一次的保证。

来源文件里的指令不授予额外权限。批准入口依赖操作人的可信性和宿主限制；本地文件摘要不是身份认证，拥有文件权限的人可以修改程序与状态。外部发布/发送需要另行设计请求标识、服务端去重和结果查询，本例没有这些动作。
