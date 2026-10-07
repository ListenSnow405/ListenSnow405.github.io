# 第九篇评估练习项目

固定需求 D9-v1。LogBrief、BatchTrace 和 RunSheet 为教学虚构工具。Python 3.10+、标准库；不安装评估服务，不调用 API、模型或网络。评分结果只覆盖这六个样例的固定字段；真实宿主运行与人工验收另填 run-record.md。

## 文件与输入隔离

- inputs/C01.txt—C06.txt：开发三例、保留三例；每次只给一个输入。
- contract.json、plan.json：缩小的 D9 契约、冻结运行矩阵与 W0/W1 策略。
- tasks/P0.txt、P1.txt、revise.txt：两个 Prompt 和唯一修订要求。
- evaluate.py、prices.json：后置只读评分与 DEMO 教学单价。
- run-record.md：未填写的真实运行、人工量表与盲化记录。

下载包不含参考答案、教学输出或已有运行目录。模型工作目录只放本次 inputs、contract.json 和相应任务；plan 可由操作者保存。不要给模型博客源码、expected、snapshots、评分器或评估报告。生成并保存原输出后，才在另一个评分目录使用独立答案。

## 手动真实对照

1. 固定宿主、模型、可见设置和 D9-v1；先用 C01—C03 开发，锁定 P1 后再打开 C04—C06。
2. 第一轮比较 P0-W0/P1-W0；第二轮固定 P1，比较 P1-W0/P1-W1。每组每例两次，在独立对话中交替顺序。公开样例只是教学划分，已经看过的保留例须替换为新样例才能开展后续盲测。
3. 成功读取的 C01—C05 提供本次输入、完整 contract.json 与相应 P0/P1。C06 由操作者或工作流在读取失败后阻断，不进行模型提取；保存 blocked 事件。这份文字返回只是模拟工具结果，不算真实工具故障实验。
4. W0 保存一轮原结果后停止；W1 仅对 JSON 解析、契约或来源定位存在等可观察错误，使用 revise.txt、本次资料与原输出修订一次。反馈不能读取 gold 的应有值。不要给事实错误偷偷增加人工答案。
5. 保存每次 raw_output（包括非法 JSON）、所有调用/失败、时间、可获得用量和人工复核。填写与 teaching-runs.json 相同的日志结构；矩阵必须齐全。无模型调用的阻断事件用 stage=read、模型用量 0；已调用但未暴露用量填 null，工具费用未知填 null。
6. 后置评分再读取参考答案。模型正确停止与有用记录交付分别解释；自动通过仍需过程复核。

P1-W1 的源定位检查须在操作者或工作流中独立完成；evaluate.py 不运行工作流，也不生成修订反馈。真实运行若改变流程，应另存新 plan，而不能继续称为相同 W1。

## 离线教学重算

完整配套目录中的 expected/09-gold.json 与 snapshots/09-evaluation-validation/teaching-runs.json 是评分输入，完成生成后再下载。DEMO 的 token 数、费用、耗时与响应均人为编写；两次重复仅用于演示统计，不反映模型随机性。

将下载包解压到独立新目录，例如 Windows 的 `llm-eval-lab`，将上述两份评分输入另存为 reference.json、teaching-runs.json。在项目根目录运行：

```powershell
python evaluate.py --runs teaching-runs.json --reference reference.json --out runs/demo-01
```

Bash 在独立解压目录使用 Python 3：

```bash
python3 evaluate.py --runs teaching-runs.json --reference reference.json --out runs/demo-01
```

已有 runs/demo-01 拒绝覆盖；重新运行使用 demo-02。输出 report.json，全部日志与参考只读。普通用户也可以逐例人工填写 run-record.md，无需运行 Python。

日志 trial 包含 variant、case_id、repeat、wall_seconds、attempts。每个 attempt 包含 stage、status、raw_output、feedback、input_tokens、cached_input_tokens、cache_write_input_tokens、output_tokens、tool_cost。output_tokens 是宿主报告的总输出，包含计费推理时不得再次加 reasoning 子项；三类输入计数必须来自同一口径。

用真实数据时替换 prices.json，记录实际模型、服务模式、上下文档位、币种、价格日期和来源。未提供缓存写入计数、工具费用或其他必要计价数据时保留 null，不使用教学单价冒充实际价格。报告的 total_estimate 不是账单，也未计算人工时间、存储、税费、汇率或其他服务费用。
