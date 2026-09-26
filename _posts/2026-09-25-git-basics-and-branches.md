---
layout: post
title: "Git 基础操作与分支管理"
date: 2026-09-25 00:01:00 +0800
categories: [学习]
tags: [Git, 版本控制, 分支管理, 冲突处理, Git系列]
excerpt: "围绕学习任务清单，理解文件状态与暂存差异，组织清晰的提交，并通过可复现案例完成分支合并与冲突处理。"
series: git
series_order: 1
---

一次清晰的开发记录，需要同时做好内容选择和历史组织：先确认哪些修改应该进入提交，再决定它们属于哪条开发线。本文从文件状态出发，逐步完成一次功能开发与冲突处理。

本文是 Git 系列第二篇。建议先阅读[基本原理与学习路径]({% post_url 2026-09-16-git-learning-roadmap %})，并准备其中的 `git-practice` 仓库。案例继续使用 README 和任务清单，文件修改均通过编辑器完成；代码块内的 Git 命令可以在 PowerShell 或 Bash 中执行。不同方案会明确标注，不应把所有代码块不加区分地连续运行。

## 1. 仓库结构与基础配置

### 配置范围

开始前确认当前位置、分支和配置来源：

```bash
git rev-parse --show-toplevel
git branch --show-current
git config --show-origin --get user.name
git config --show-origin --get user.email
```

`rev-parse` 输出仓库根目录。如果提示不在仓库中，应先核对目录，而不是立即初始化。`--show-origin` 能解释配置来自哪个文件；工作与个人仓库使用不同身份时尤其有用。

常见配置范围包括系统、用户和仓库。仓库级配置通常覆盖用户级同名配置；还存在 worktree、命令行等配置来源，因此定位问题时应查看实际来源，不只查看全局文件。

```bash
git config --local user.name "Practice User"
git config --local user.email "practice@example.com"
git config --global core.editor "code --wait"
```

最后一条仅适用于已经安装且能从终端调用 VS Code 的环境。编辑器需要等待窗口完成编辑后再返回，Git 才能读取最终说明；也可以保留已有编辑器设置。

### 仓库来源

已有远程项目通常使用 `git clone <url>`；新的本地项目才使用 `git init -b main`。尖括号表示需要替换的占位符，不应原样输入。克隆会建立本地仓库与工作区，并配置默认远程；初始化不会自动关联托管平台。

## 2. 文件状态与差异分析

### 暂存前后状态

假设 README 已在上篇提交。在末尾增加 `Status: drafting`，然后运行：

```bash
git status --short
git diff -- README.md
git add README.md
```

添加前应看到 ` M README.md`。再把这一行改成 `Status: ready`，运行：

```bash
git status --short
git diff -- README.md
git diff --cached -- README.md
git diff HEAD -- README.md
```

现在状态应是 `MM README.md`：左列表示索引相对 HEAD 的变化，右列表示工作区相对索引的变化。暂存区保存 `drafting`，工作区保存 `ready`；直接提交会记录 `drafting`。

| 比较方式 | 比较对象 | 本例重点 |
| --- | --- | --- |
| `git diff` | 索引 → 工作区 | `drafting` 改为 `ready` |
| `git diff --cached` | HEAD → 索引 | 增加 `drafting` |
| `git diff HEAD` | HEAD → 工作区 | 增加 `ready` |

`--` 用来分隔修订参数和文件路径，文件名可能与分支名重名时尤其有用。想把最终的 `ready` 提交进去，需要再次添加：

```bash
git add README.md
git diff --cached
git commit -m "docs: mark project ready"
```

### 补丁结构

差异中的 `---` 与 `+++` 标记旧、新文件，`@@` 标记修改块的行号范围；正文以 `-` 开头的行被删除，以 `+` 开头的行被加入，空格开头的行提供上下文。例如：

```diff
@@ -1 +1 @@
-Status: drafting
+Status: ready
```

阅读补丁时应同时检查上下文，确认改变的是预期位置。大范围修改可以先用 `git diff --stat` 看规模，再逐文件阅读。`git diff --check` 能检查部分空白错误，但不能判断功能逻辑是否正确。

## 3. 暂存管理与提交规范

### 暂存范围

| 命令 | 范围 | 新文件 |
| --- | --- | --- |
| `git add README.md` | 指定路径的变化 | 包含 |
| `git add -A` | 整个工作树的新增、修改、删除 | 包含 |
| `git add -u` | 已跟踪文件的修改、删除 | 不包含 |
| `git add -p` | 交互选择修改块 | 默认不包含未跟踪文件 |

按文件暂存适合修改范围清晰的情况。一个文件混入两项任务时，`add -p` 可以按修改块选择；交互中的 `y` 接受当前块，`n` 跳过，支持拆分时可用 `s` 拆成更小的块。相邻修改无法自动拆开时，可以先整理工作内容，不必强行编辑复杂补丁。

若希望对新文件分块暂存，可先用 `git add -N <file>` 建立意向添加记录，再执行 `add -p`。但初学阶段通常更容易先把新文件整理到单一用途，再整体加入。

### 提交检查

一次提交应能用一句具体说明解释。把任务功能和不相关的格式调整分开，有利于审查、定位回归和单独撤销。

```bash
git status
git diff
git add -p
git diff --cached
git diff --cached --check
git commit -m "docs: clarify task completion rules"
git show --stat HEAD
```

`feat:`、`fix:`、`docs:` 是说明格式约定，并非 Git 的要求。说明应与实际补丁相符。`commit -am` 会自动暂存已跟踪文件的修改与删除，却不会加入新文件；因此它不能替代状态检查。

误暂存文件时可执行 `git restore --staged <file>`，工作区修改会保留。已经形成的提交如何修正，见[历史重写与撤销恢复]({% post_url 2026-09-25-git-history-and-recovery %})，本篇只讨论提交前的组织。

## 4. 文件管理与忽略规则

### 忽略规则

为练习仓库创建 `.gitignore`：

```gitignore
/build/
*.log
.env
```

`/build/` 限定仓库根目录的构建目录，`*.log` 匹配日志文件，`.env` 排除该名称的本地环境文件。规则应围绕项目实际产物制定；适合共享的编辑器配置不必一概排除。

创建 `build/output.txt` 后，可以检查匹配来源：

```bash
git check-ignore -v build/output.txt
git status --ignored
```

输出会给出规则文件、行号和命中规则。团队共享规则放在 `.gitignore`；只属于本机的例外可放在 `.git/info/exclude`。忽略规则不阻止文件已经被跟踪后的变更。

### 跟踪关系

若此前已经提交 `.env`，应先确认该文件是否含敏感信息，再将其加入忽略规则并停止跟踪：

```bash
git rm --cached .env
git add .gitignore
git diff --cached
git commit -m "chore: stop tracking local environment"
```

此操作保留当前工作区副本，但会在新提交中删除该路径；协作者更新时也会受到版本删除的影响，应提前沟通各自的本地配置。旧提交仍包含旧文件，若其中出现真实密钥，需要先轮换密钥，再单独处理历史。

移动和删除已跟踪文件可分别使用 `git mv <old> <new>` 与 `git rm <file>`。它们也需要后续提交才能进入历史。Git 通常根据内容相似性识别重命名，而不是存储一个永久的“重命名标志”。

## 5. 分支操作与合并机制

### 功能分支

下面进入独立的功能案例。先提交前面的有效修改，确认 `git status` 干净，在 `main` 上创建 `tasks.txt`：

```text
Read Git basics: pending
Practice branching: pending
```

```bash
git switch main
git add tasks.txt
git commit -m "feat: add learning tasks"
git switch -c feature/statistics
```

创建 `stats.txt`，写入 `Total tasks: 2`，提交后回到主分支：

```bash
git add stats.txt
git commit -m "feat: add task statistics"
git switch main
git merge --ff-only feature/statistics
```

由于主分支在功能开发期间没有新提交，它可以直接移动到功能分支的提交上，这就是快进。合并完成后 `stats.txt` 应出现在主分支，日志中没有额外的合并提交。

```text
合并前：A ── B(main) ── C(feature/statistics)
合并后：A ── B ── C(main, feature/statistics)
```

### 合并方式

| 方式 | 结果 | 适用考虑 |
| --- | --- | --- |
| 默认 `merge` | 能快进时快进，否则通常建立合并提交 | 保留两条历史的连接 |
| `merge --no-ff` | 即使能快进也建立合并提交 | 明确记录一次分支整合 |
| `merge --squash` | 准备合并结果，需另行提交 | 主分支只记录一个整合提交 |

squash 不记录原分支作为合并父线，因此后续合并判断、重复使用该分支与分支删除检查都会有所不同。三种方式是选择关系，不要在同一案例中依次执行。

检查完成后删除已合并的练习分支：

```bash
git log --graph --oneline --decorate -n 8
git branch -d feature/statistics
```

`-d` 会进行合并状态检查：有上游时参照上游，否则参照 HEAD。若拒绝删除，应查看原因，尤其是经过 squash 的分支，不要直接把命令改成 `-D`。

### 游离状态

`git switch --detach <commit>` 可以查看旧提交。若在这一状态完成了新工作，应先执行 `git switch -c recovery/experiment` 为当前提交建立分支，再离开。回到主分支不等于把实验提交合并进去，保留与整合是两个不同动作。

## 6. 合并冲突处理

### 冲突构造

保持工作区干净，从当前主分支创建新分支：

```bash
git switch -c feature/task-status
```

将 `tasks.txt` 第一行改为 `Read Git basics: completed` 并提交：

```bash
git add tasks.txt
git commit -m "feat: record completed reading"
git switch main
```

此时主分支第一行仍为 `pending`。把它改成 `Read Git basics: in progress`，提交并合并：

```bash
git add tasks.txt
git commit -m "docs: record reading progress"
git merge feature/task-status
```

双方从共同祖先出发改动同一行，Git 无法决定最终状态。终端会报告内容冲突，`git status --short` 中通常出现 `UU tasks.txt`。

### 内容决策

在默认冲突样式下，文件会出现类似内容：

```text
<<<<<<< HEAD
Read Git basics: in progress
=======
Read Git basics: completed
>>>>>>> feature/task-status
Practice branching: pending
```

这里当前分支是 `main`，另一侧是功能分支。假设实际阅读已经完成，应将文件整理为两行：第一行采用 `completed`，第二行保留。需要删除冲突标记，不能把两种互相矛盾的状态一起留下。

```bash
git diff --check
git add tasks.txt
git diff --cached
git commit -m "merge: reconcile task completion status"
git status
git log --graph --oneline --decorate -n 8
```

状态干净、最终文件内容正确、日志出现连接两条历史的合并提交，才算完成。软件项目还应运行相应测试，Git 解决了文本合并并不保证功能正确。

### 中止与替代方案

若尚未完成合并且暂时无法判断，可以执行 `git merge --abort`。它尝试恢复合并前状态；带着已有未提交修改开始合并时可能无法完整重建，因此本例要求先保持工作区干净。

`git restore --ours <file>` 或 `--theirs` 会为整个冲突文件选择一侧内容，不能替代逐段判断。变基时两侧的含义还会变化，应先阅读实际差异。

## 命令速查

| 任务 | 命令 |
| --- | --- |
| 简短状态 | `git status --short --branch` |
| 分块暂存 | `git add -p` |
| 取消暂存 | `git restore --staged <file>` |
| 忽略来源 | `git check-ignore -v <file>` |
| 创建分支 | `git switch -c <branch>` |
| 返回上一分支 | `git switch -` |
| 合并分支 | `git merge <branch>` |
| 放弃合并 | `git merge --abort` |

## 实践练习

在新分支增加一项学习任务，同时修改 README 的使用说明。把两项变化组织为两次提交，再合并到主分支。验收时检查每次提交是否只表达一个意图、任务总数是否同步更新，并解释为什么“没有文本冲突”仍可能留下统计错误。

## 参考资料

- [git-status](https://git-scm.com/docs/git-status)、[git-diff](https://git-scm.com/docs/git-diff)
- [git-add](https://git-scm.com/docs/git-add)、[gitignore](https://git-scm.com/docs/gitignore)
- [git-branch](https://git-scm.com/docs/git-branch)、[git-merge](https://git-scm.com/docs/git-merge)

**系列导航**：第二篇 / 共五篇 · [上一篇：基本原理与学习路径]({% post_url 2026-09-16-git-learning-roadmap %}) · [下一篇：远程协作与版本管理]({% post_url 2026-09-25-git-remotes-and-collaboration %}) · [命令速查]({% post_url 2026-09-16-git-command-reference %})
