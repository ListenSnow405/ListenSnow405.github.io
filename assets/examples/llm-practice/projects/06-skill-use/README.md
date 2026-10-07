# 第六篇独立练习项目

版本：06-skill-use / 1.0，2026-10-05。本项目包含随章编写的教学 Skill、固定输入和五组任务。沿用第五篇 D5-v1 的 12 条记录，候选 JSON 人为加入三条事实错误；它不是实际模型失败输出。Skill 本身没有脚本、网络目标或凭据需求，只返回审查文本。

本章使用一个已经准备好的 Skill；后续进入第七篇《工具调用与 MCP》。博客内以 `SKILL.md.txt` 保存，不加载到博客开发会话。不要在 J:\Blog 中完成加载练习。

## 文件与完整目录审查

- `skill/source-record-audit/SKILL.md.txt`：待加载的完整指令，安装到隔离项目后改名为 SKILL.md。
- `skill/source-record-audit/references/review-format.json`：输出格式与状态含义，没有答案。
- `input/sources.txt`、`input/contract.json`：完整复制第五篇的当前资料与字段契约。
- `input/candidate.json`：结构合法、事实有错的 12 条候选记录。
- `input/sources-no-units.txt`：独立变体，只删除整个 P5 块，保留其余原文和定位。
- `input/review-format.json`：与 Skill 资源逐字相同，用于保持基线输出契约一致。
- `tasks/T01-explicit.txt` 至 `T05-baseline.txt`：完整可提交任务；不要在同一对话中连续执行。
- `SHA256SUMS.txt`：除本清单以外的项目文件摘要；用于复核所加载副本，不能证明可信来源或正确执行。

先在文本编辑器里检查 Skill 全部两个文件，再检查任务输入及目录清单。解压新包时也要确认没有清单外文件、符号链接或额外脚本。此固定包源自本系列教学材料，不是从第三方商店取得的 Skill，也没有第三方审核背书。

## 隔离目录与本地加载

把下载包解压到博客、个人 Skill 目录和其他项目之外的**新目录**。进入解压后的 `06-skill-use`，先读取全部文件再进行下面的本地复制。若 `.agents/skills` 已存在，停止此组命令，重新选择空练习项目；不要覆盖已有 Skill。命令只在本项目中创建副本，没有修改用户级配置。

PowerShell：

```powershell
Get-Content .\skill\source-record-audit\SKILL.md.txt
Get-Content .\skill\source-record-audit\references\review-format.json
New-Item -ItemType Directory -Path .\.agents\skills -ErrorAction Stop
Copy-Item -LiteralPath .\skill\source-record-audit -Destination .\.agents\skills -Recurse
Rename-Item -LiteralPath .\.agents\skills\source-record-audit\SKILL.md.txt -NewName SKILL.md
git init
codex
```

Bash 替代流程，在另一个新解压目录执行：

```bash
cat skill/source-record-audit/SKILL.md.txt
cat skill/source-record-audit/references/review-format.json
mkdir -p .agents
mkdir .agents/skills
cp -R skill/source-record-audit .agents/skills/
mv .agents/skills/source-record-audit/SKILL.md.txt .agents/skills/source-record-audit/SKILL.md
git init
codex
```

两组命令是替代方案，不能在同一目录先后执行。Bash 命令须逐条检查退出状态，不在失败后继续复制。`git init` 仅为练习项目建立独立仓库边界，不提交文件。`codex` 要求读者已安装 CLI 并完成登录；具体加载位置与调用语法依据本章链接的官方文档，不代表每个产品具有相同目录或 UI。

进入 CLI 后用 `/skills` 查找 source-record-audit，或在新任务中用 `$` 选择它。记下实际显示的名称与路径；同名 Skill 要核对所选副本。若未出现，检查名称、目录、SKILL.md 文件名、禁用设置与当前项目范围，再按官方文档重新启动。用户级或系统 Skill 仍可能可见，隔离项目不等于绝对干净的 Skill 清单。

上述命令没有在博客开发环境中启动 Codex 或修改其配置。发布前只实际验证隔离复制、JSON 解析、材料与格式一致性；原生发现、选择、模型执行和触发率由读者按自己的宿主验证。

## 五组独立任务

每组新建对话，从当前练习项目提交对应任务文件的**完整文本**。每次只允许读取任务所列输入及被选择 Skill 的资源。不把 expected/ 独立答案加入模型上下文。

| 任务 | 条件 | 观察重点 |
| --- | --- | --- |
| T01 | 显式选择，完整来源 | 指定 Skill 是否加载，事实问题是否定位 |
| T02 | 自然语言，完整来源 | 预期匹配是否发生；正确结果不证明原生触发 |
| T03 | 显式选择，缺少 P5 | 是否只审查允许输入，是否留下待确认项 |
| T04 | 自然语言，生日祝福 | 不应选择本 Skill，也不应读资料文件 |
| T05 | 另一个无本 Skill 的项目 | 同材料、同输出契约的普通任务基线 |

T05 在另一处**新目录**进行：只复制 input/ 和 tasks/，不复制 skill/ 或 .agents/，另行 git init，从该目录启动 Codex。使用与 T01 相同产品、模型、设置及可见的其他规则。先检查 Skill 清单；若 source-record-audit 仍来自用户、系统或祖先目录，记录基线受污染，不能声称完成无 Skill 对照。T01 与 T05 的主要任务正文完全相同，T01 只增加显式调用行。

没有原生 Skill 功能时，可使用配套 `prompts/06-01-manual-review.txt`。它完整提供流程、来源、契约、候选和格式，在新对话粘贴即可；这是**人工提供 Skill 内容**，只检验流程与结果，不能填写原生发现、触发成功或加载耗时。

## 结果保存与验收

模型只返回 JSON 文本，不生成文件。读者把原始输出完整保存为 `runs/T01-01/raw.txt`，另把 JSON 对象保存为 `runs/T01-01/review.json`；保存动作由读者完成，不记为模型交付文件。后续另建 T01-02 等目录，保留第一次结果与修订反馈。

可选解析检查（Python 3，仅标准库；不改写输入）：

```text
python -m json.tool runs/T01-01/review.json
```

该命令只检查 JSON 语法，不检查规定键、状态、证据含义或事实。随后按 `prompts/06-run-record.md` 和 `expected/06-reference.md` 进行人工评分。先完成自己的结果，再看独立答案。

记录可见加载/读取证据、流程步骤、错误定位、遗漏与误报，以及越界读写情况。看不到加载日志就填“不可观察”；没有 token 或费用统计就填“不可得”，不能按文件字数猜测。基础任务各重复三次是小型练习建议，不是本章已完成的实验。
