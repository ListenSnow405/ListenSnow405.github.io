---
layout: post
title: "Git 历史重写与撤销恢复"
date: 2026-09-25 00:03:00 +0800
categories: [学习]
tags: [Git, Rebase, 版本恢复, 提交管理, Git系列]
excerpt: "根据修改位置和共享状态区分历史整理、文件恢复与提交撤销，通过状态对照理解 reset，并使用 reflog 保护和恢复提交。"
---

历史整理、撤销与恢复都可能改变仓库状态，但它们的目标不同：整理改善记录方式，撤销抵消不需要的变化，恢复重新保护仍有价值的内容。选择命令前，需要明确想保留什么，以及其他人是否已经依赖当前历史。

本文是 Git 系列第四篇，建议先掌握[基础操作]({% post_url 2026-09-25-git-basics-and-branches %})和[远程协作]({% post_url 2026-09-25-git-remotes-and-collaboration %})。所有改写和恢复实验应在独立练习仓库中进行。文中的 A、B、C 是提交图示意，`<commit>` 等占位符必须替换为实际引用；各小节是独立场景，不是一份连续执行的脚本。

## 1. 操作分类与影响范围

### 操作选择

| 目标 | 优先考虑 | 主要影响 |
| --- | --- | --- |
| 取消暂存，保留编辑结果 | `restore --staged` | 索引 |
| 丢弃未暂存的已跟踪文件修改 | `restore` | 工作区文件 |
| 修正最近一次本地提交 | `commit --amend` | 当前分支历史 |
| 整理多次本地提交 | 交互式 rebase | 当前分支历史 |
| 撤回本地提交并重新组织 | reset | HEAD、索引或工作区 |
| 抵消已共享的修改 | revert | 新增反向提交 |
| 找回旧提交位置 | reflog 与新分支 | 本地引用 |

“是否推送”是判断共享状态的线索，但不是唯一条件：同事可能通过其他远程或 bundle 取得提交。关键在于是否有人基于旧历史继续工作。

### 现场保护

```bash
git status
git diff
git diff --cached
git log --graph --oneline --decorate -n 10
git branch backup/before-history-edit
```

备份分支只保存当前提交位置，不保存未提交内容。未提交修改应先形成可保留的提交、使用合适范围的 stash，或复制到仓库外的可靠位置。被忽略文件、未跟踪文件与子模块中的修改也要分别考虑，不能只看到一个备份分支就认为整个目录已被保护。

## 2. 最近提交修正

### 说明与内容

假设刚提交任务功能，但说明不准确：

```bash
git commit --amend -m "feat: add task completion summary"
```

如果遗漏了 README 更新，先编辑文件，再暂存并修正：

```bash
git add README.md
git diff --cached
git commit --amend --no-edit
git show --stat HEAD
```

`--no-edit` 保留原说明，但提交内容和标识仍可能变化。amend 会把当前索引用于替换最近提交，因此暂存区里若还混入其他修改，也会一起进入新提交。修正前的复查不能省略。

```text
修正前：A ── B
修正后：A ── B'  ← 当前分支
```

旧 B 不再是当前分支顶端。尚未共享时，替换最近记录通常容易理解；已共享时，新增一个修正提交往往更适合协作者继续工作。

## 3. 提交重组与迁移

### 变基机制

假设功能分支从 A 创建，主分支后来新增 B、C，功能分支产生 D、E：

```text
A ── B ── C  ← main
 \
  D ── E     ← feature/summary
```

在功能分支且工作区干净时执行 `git rebase main`，Git 会尝试把功能分支的提交重放到新起点：

```text
A ── B ── C ── D' ── E'  ← feature/summary
          ↑
         main
```

图示采用普通线性提交。重放可能遇到冲突、已存在的补丁或空提交，不能理解成无条件复制每个原提交。新历史需要重新检查内容与测试；提交图看起来更整齐不等于整合一定正确。

### 交互式整理

在练习分支保留至少四个提交，用最近三条记录演示：

```bash
git log --oneline -n 4
git rebase -i HEAD~3
```

编辑器中的提交通常从旧到新排列，例如：

```text
pick a1b2c3d add summary
pick b2c3d4e fix summary wording
pick c3d4e5f explain summary usage
```

这些哈希只作展示，应修改 Git 实际打开的列表。把第二行 `pick` 改为 `fixup`，第三行改为 `reword`，保存后 Git 会把第二条合入前一条，再要求编辑第三条说明。

| 动作 | 作用 |
| --- | --- |
| `pick` | 保留并应用提交 |
| `reword` | 修改说明 |
| `edit` | 暂停以调整内容 |
| `squash` | 合入前一条并整理说明 |
| `fixup` | 合入前一条，通常丢弃当前说明 |
| `drop` | 不再应用该提交 |

需要拆分某个提交时可以选择 `edit`，暂停后重新组织索引和提交；初次练习不必同时学习全部动作。整理后用 `log` 查看记录数，再将最终文件树与备份分支比较，确认没有意外丢失功能。

后续修正也可先建立 fixup 提交，再统一整理：

```bash
git add README.md
git commit --fixup=<target-commit>
git rebase -i --autosquash <base>
```

`<base>` 应位于待整理目标之前；如果目标是根提交，应另行使用适当的 `--root` 范围。autosquash 帮助安排修正的位置，最终仍需检查编辑列表。

### 冲突控制

rebase 暂停后，阅读 `status`，编辑冲突文件并暂存，再继续：

```bash
git status
git add <resolved-file>
git rebase --continue
```

`--abort` 返回变基前状态；`--skip` 跳过当前补丁，可能丢失它的变化；`--quit` 停止变基流程，却不主动恢复原 HEAD、索引和工作区。它们不是等价的“退出”。变基过程中 `ours` 通常指已重建的一侧，`theirs` 指正在重放的提交，不能沿用普通合并时对分支名称的直觉。

### 提交迁移

若一个修复提交需要进入另一条分支，可切换到目标分支并应用：

```bash
git switch release/task-list
git cherry-pick <fix-commit>
```

目标分支必须已经存在，且应先确认工作区干净。cherry-pick 将变化应用到目标并通常创建新提交，不会自动删除来源分支上的原记录，也不建立两条分支之间的合并父子关系。

遇到冲突时解决后 `git add`，再 `git cherry-pick --continue`；放弃则使用 `--abort`。若修复依赖前置改动，仅选择一条提交可能无法工作，应检查依赖并测试目标版本。

### 远程更新边界

改写已经推送的个人分支前，需要确认团队允许且无人依赖旧历史。`--force-with-lease` 比无条件强推增加预期引用检查，但后台 fetch 可能更新默认检查依据，因此它不是协作确认的替代品。[Git 推送手册](https://git-scm.com/docs/git-push)说明了这一限制。

明确审查旧远程顶端后，可以指定期望值；以下是语法示意，不应原样执行：

```text
git push --force-with-lease=refs/heads/<branch>:<expected-oid> origin <branch>:<branch>
```

它要求远程目标仍等于已经核对的提交。若被拒绝，应重新检查他人的更新，不能机械地更换期望值后重试。受保护分支也可能完全禁止此类更新。

## 4. 文件恢复与暂存撤销

### 索引恢复

```bash
git restore --staged README.md
```

在已有提交的仓库中，这通常从 HEAD 恢复索引中的该文件，工作区编辑结果保留。新加入的文件取消暂存后，可能重新成为未跟踪文件。

### 工作区恢复

```bash
git diff -- README.md
git restore README.md
```

默认从索引恢复工作区文件，因此丢弃的是未暂存部分。假设 HEAD 内容为 A、索引为 B、工作区为 C，执行后工作区变为 B，并非 A。

指定来源可以恢复历史版本：

```bash
git restore --source=<commit> -- README.md
git diff -- README.md
```

默认只修改工作区；要将结果提交，仍需检查、暂存和提交。`git restore -p` 可以按块选择恢复内容，但被丢弃的未暂存文本未必有 Git 恢复入口。

## 5. 提交重置与反向提交

### 重置模式比较

为隔离实验，新建 `git-reset-lab` 仓库并配置练习身份。在其中创建 `value.txt`，内容为 `one`，提交后打标签 `lab-base`；再改成 `two`，提交并打标签 `lab-tip`。两次提交均只涉及这个文件。

```bash
git init -b main
git config user.name "Practice User"
git config user.email "practice@example.com"
```

第一次填写文件后执行 `git add value.txt`、`git commit -m "test: base value"`、`git tag lab-base`；第二次填写后同样提交，说明为 `test: updated value`，然后 `git tag lab-tip`。确认工作区干净。

从 `lab-tip` 出发重置到 `lab-base`，三种模式分别得到：

| 模式 | HEAD 文件版本 | 索引内容 | 工作区内容 | 简短状态 |
| --- | --- | --- | --- | --- |
| `--soft` | one | two | two | `M  value.txt` |
| `--mixed` | one | one | two | ` M value.txt` |
| `--hard` | one | one | one | 干净 |

以下只在这个独立实验仓库执行。每次测试之间用 `lab-tip` 还原起点；还原命令本身也会覆盖文件，所以不要在中间添加其他有价值的修改。

```bash
git reset --soft lab-base
git status --short
git diff --cached
git reset --hard lab-tip

git reset --mixed lab-base
git status --short
git diff
git reset --hard lab-tip

git reset --hard lab-base
git status --short
git reset --hard lab-tip
```

这里讨论的是不带路径的提交重置形式。带路径的 reset 可以只更新索引，不移动分支。`--hard` 不仅覆盖已跟踪文件，还可能覆盖或移除妨碍检出目标文件的未跟踪路径，因此不能把未跟踪文件视为必然安全。[Git 重置手册](https://git-scm.com/docs/git-reset)区分了这些形式与影响。

### 反向提交

已共享的错误通常通过新提交抵消：

```bash
git revert <bad-commit>
git show HEAD
```

它反向应用目标提交的变化，不把整个仓库简单恢复到目标之前。例如目标之后有其他独立功能，新反向提交可以保留这些功能；若后续修改依赖目标变化，则可能冲突或引入逻辑问题。解决冲突后 `git add` 并 `git revert --continue`，放弃使用 `--abort`。

在上面的实验中，回到 `lab-tip` 后执行 `git revert --no-edit lab-tip`，文件应恢复为 `one`，但日志增加第三条记录，第二条不会消失。这正是与 reset 的核心区别。

### 合并提交撤销

合并提交有多个父提交，撤销时需要指定作为主线的父序号：

```bash
git show --no-patch --format="%H %P" <merge-commit>
git revert -m 1 <merge-commit>
```

只有确认第一父线就是要保留的主线时才使用 `-m 1`。撤销合并不会删除原合并关系，今后再次合并相同祖先不一定重新引入被撤销的变化；可能需要撤销那次 revert 或生成新的修正，应结合提交图判断。

## 6. 引用日志与历史恢复

### 提交定位

误重置、误删分支或离开 detached HEAD 后，应尽量减少继续改写与清理操作，先检查本地引用日志：

```bash
git reflog
git show "HEAD@{2}"
```

序号会随操作变化，`HEAD@{2}` 只是语法示例，不能假设它一定是丢失的提交。应按操作说明、时间和实际内容选择候选哈希，再建立恢复分支：

```bash
git show <candidate-commit>
git branch recovery/task-work <candidate-commit>
git log --oneline recovery/task-work -n 5
```

建立分支不会立即覆盖当前工作区。确认候选正确后，再决定切换、合并或 cherry-pick，通常比直接再次 hard reset 更容易检查。

### 恢复条件与限制

reflog 是本地记录，通常不会随 clone 或 push 传输，且会按配置过期。删除分支后，其专属引用日志可能已不可用，但 HEAD 的日志仍可能保留曾经切换或提交的位置。不可达对象也可能最终被清理，因此不能保证任意旧提交永久可找回。

未提交且未被 Git 保存过的内容、被 clean 删除的普通未跟踪文件，不能依赖 reflog 恢复。编辑器历史、系统备份或其他副本可能有帮助，但属于 Git 之外的恢复来源。

## 命令速查

| 目标 | 命令 |
| --- | --- |
| 最近提交修正 | `git commit --amend` |
| 交互式整理 | `git rebase -i <base>` |
| 取消暂存 | `git restore --staged <file>` |
| 撤销共享修改 | `git revert <commit>` |
| 引用日志 | `git reflog` |
| 保护候选提交 | `git branch recovery/<name> <commit>` |

## 实践练习

在独立实验仓库中先创建一条临时分支和一个提交，记录其文件内容，再切走并删除该练习分支。通过 reflog 找到候选提交并建立恢复分支。验收时检查哈希、文件内容与提交说明，而不是只确认新分支名称存在。

## 参考资料

- [git-commit](https://git-scm.com/docs/git-commit)、[git-rebase](https://git-scm.com/docs/git-rebase)
- [git-cherry-pick](https://git-scm.com/docs/git-cherry-pick)、[git-restore](https://git-scm.com/docs/git-restore)
- [git-revert](https://git-scm.com/docs/git-revert)、[git-reflog](https://git-scm.com/docs/git-reflog)

**系列导航**：第四篇 / 共五篇 · [上一篇：远程协作与版本管理]({% post_url 2026-09-25-git-remotes-and-collaboration %}) · [下一篇：历史分析与仓库维护]({% post_url 2026-09-25-git-analysis-and-maintenance %}) · [系列导读]({% post_url 2026-09-16-git-learning-roadmap %}) · [命令速查]({% post_url 2026-09-16-git-command-reference %})
