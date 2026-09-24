---
layout: post
title: "Git 基本原理与学习路径"
date: 2026-09-16 10:00:00 +0800
categories: [学习]
tags: [Git, GitHub, 版本控制, 学习路线, Git系列]
excerpt: "从版本控制、工作区域和提交引用建立 Git 的基本认识，通过首次提交完成最小实践，并规划后续专题的学习顺序。"
---

Git 的学习难点，在于把文件内容、提交历史和协作关系联系起来。能够解释修改保存在哪里、下一次提交包含什么，才能进一步理解合并、同步和恢复操作。

本文是 Git 系列第一篇，也是系列导读。整个系列以“学习任务清单”为练习项目：先保存项目说明，再增加功能、参与协作，最后练习历史整理与问题排查。初次接触 Git 的读者可以顺序阅读；已有使用经验的读者可以通过第五节直接进入所需专题。

<span id="1-gitgithub-与版本控制"></span>

## 1. 版本控制与分布式模型

### 版本记录

用 `project-final.zip`、`project-final-2.zip` 保存项目副本，能够保留文件，却难以说明两个版本的区别。随着修改增多，查找错误来源、合并他人工作和恢复旧内容都会变得困难。

Git 将项目状态记录为一系列提交。每条记录包含文件快照、提交说明、作者等信息，并通过父提交连接到历史。我们既可以比较相邻版本，也可以追踪某个文件的演变。提交说明负责解释修改意图，文件差异负责呈现实际变化，两者共同构成可审查的记录。

### 本地与远程

普通的完整克隆通常包含项目历史，因此查看日志、创建提交和建立分支都可以在断网时完成。远程仓库用于交换对象与引用，让不同开发者能够共享历史；浅克隆、部分克隆则会限制本地已有的数据范围。

Git 是版本控制工具，GitHub 是仓库托管与协作平台。Pull Request、议题和代码审查属于平台提供的协作能力。没有 GitHub 账号也能使用本地 Git，而设置 `user.name` 和 `user.email` 只是在配置提交身份，不会完成远程登录。

<span id="2-先建立四个区域的心智模型"></span><span id="工作区"></span><span id="暂存区"></span><span id="本地仓库"></span><span id="远程仓库"></span>

## 2. 工作区域与文件状态

### 工作区域

一次常见的修改流转如下：

```text
工作区 ── add ──> 暂存区 ── commit ──> 本地仓库
                                           │
                                          push
                                           ↓
                                        远程仓库
```

工作区是正在编辑的文件目录。暂存区又称索引，保存下一次提交准备采用的文件状态。本地仓库存储提交等对象与引用。远程仓库是另一个仓库，并不是每次保存文件后自动同步的文件夹。

例如，先把 README 的标题改好并执行 `add`，然后继续修改正文：暂存区仍保存添加时的版本，工作区则包含后来新增的正文变化。此时提交只包含已暂存内容。因此，暂存更接近“选定下一次快照”，而不是给文件打上一个永久的待提交标签。

### 文件状态

| 状态 | 含义 | 常用检查 |
| --- | --- | --- |
| 未跟踪 | 文件尚未纳入索引或已有提交 | `git status` |
| 已跟踪且未修改 | 工作区、索引与当前提交一致 | `git status` |
| 已修改 | 已跟踪文件的工作区内容发生变化 | `git diff` |
| 已暂存 | 索引相对当前提交发生变化 | `git diff --cached` |

已修改和已暂存并不互斥：同一个文件可以有一部分变化准备提交，另一部分变化仍留在工作区。`status` 用于定位状态，`diff` 用于阅读内容，两者需要配合使用。默认 `git diff` 不展示未跟踪文件的内容，新文件应先检查文件本身，暂存后再检查差异。

<span id="5-第三阶段使用分支隔离修改"></span><span id="什么是合并冲突"></span><span id="本阶段练习-2"></span>

## 3. 提交结构与分支引用

### 提交与快照

从概念上看，一次提交描述的是完整项目快照；底层可以复用未变的对象，并非每次复制整份目录。提交还记录父提交、作者、提交者与说明。修改其中的信息会产生不同的提交对象，因此整理历史时经常会看到提交标识变化。

以下字母只是示意，实际提交使用哈希标识：

```text
A ── B ── C  ← main
          ↑
         HEAD 通过 main 指向 C
```

普通提交通常有一个父提交，初始提交没有父提交，合并提交可以有多个父提交。沿父提交关系可以回溯历史，Git 的许多范围查询都建立在这种可达关系上。

### 分支与 HEAD

分支是指向提交的可移动引用。通常，HEAD 指向当前分支；在该分支创建新提交后，分支引用随之向前移动。

```text
A ── B ── C  ← main
      \
       D     ← feature/statistics ← HEAD
```

此时修改功能分支不会自动让 `main` 指向 D。合并时才会整合两条开发线。切换分支则会按目标版本更新工作区和索引；若操作会覆盖尚未保存的本地修改，Git 通常会拒绝切换。

HEAD 也可以直接指向某个提交，这称为 detached HEAD。它适合临时查看旧版本，但若创建了需要保留的新提交，应及时建立分支，让这些提交拥有明确的引用。

<span id="3-第一阶段完成本地版本管理闭环"></span><span id="本阶段练习"></span>

## 4. 版本管理最小实践

### 环境与仓库

以下命令适用于安装了 Git 的 PowerShell 或 Bash。文件内容通过编辑器填写，避免不同终端的文件写入语法和编码差异。练习应在新的空目录中完成，不要在现有项目中重新初始化。

```bash
git --version
mkdir git-practice
cd git-practice
git init -b main
git config user.name "Practice User"
git config user.email "practice@example.com"
```

这里的身份配置只写入练习仓库。正式项目应使用自己的提交身份；希望对所有仓库生效时才使用 `--global`。`git --version` 检查安装状态，`git init -b main` 建立以 `main` 为初始分支名的仓库。

在目录内创建 `README.md`：

```markdown
# Learning Tasks

A repository for tracking learning tasks.
```

### 首次提交

```bash
git status --short
git add README.md
git diff --cached
git commit -m "docs: initialize learning task project"
git log --oneline
git status
```

添加前，简短状态中应出现 `?? README.md`；添加后，它变为 `A  README.md`。`diff --cached` 展示准备写入首次提交的内容。提交成功后，日志出现一条记录，状态应提示工作区干净。哈希、时间和输出语言会随环境变化，不需要与他人的输出逐字一致。

继续在 README 末尾增加一行 `Goal: practice reproducible Git workflows.`，再执行：

```bash
git diff -- README.md
git add README.md
git diff --cached
git commit -m "docs: describe practice goal"
git show --stat HEAD
```

第二次提交只表达“补充目标”这一项意图。此时能够回答三个问题，就完成了最小实践：修改前后有什么不同，提交前索引保存了什么，提交后如何确认结果。

<span id="4-第二阶段养成可靠的提交习惯"></span><span id="一次提交只表达一个意图"></span><span id="暂存前后都检查差异"></span><span id="用-gitignore-排除本地文件"></span><span id="本阶段练习-1"></span><span id="6-第四阶段连接-github-远程仓库"></span><span id="ssh-与-https"></span><span id="本阶段练习-3"></span><span id="7-第五阶段建立团队协作流程"></span><span id="fetch-与-pull-的区别"></span><span id="本阶段练习-4"></span><span id="9-第七阶段选择性学习进阶工具"></span><span id="11-一个完整的练习项目"></span><span id="12-学习完成标准"></span>

## 5. 学习阶段与专题导读

本系列不要求先记住所有参数。每个阶段先完成一个能够验证的任务，再扩展相关命令。

| 顺序 | 专题 | 完成标准 |
| --- | --- | --- |
| 一 | 本文：基本原理与学习路径 | 解释工作区域、提交、分支与 HEAD，完成两次提交 |
| 二 | [基础操作与分支管理]({% post_url 2026-09-25-git-basics-and-branches %}) | 拆分修改，管理文件，完成分支合并与冲突处理 |
| 三 | [远程协作与版本管理]({% post_url 2026-09-25-git-remotes-and-collaboration %}) | 解释上下游关系，处理分叉，完成任务切换与版本标记 |
| 四 | [历史重写与撤销恢复]({% post_url 2026-09-25-git-history-and-recovery %}) | 根据修改状态选择操作，验证整理与恢复结果 |
| 五 | [历史分析与仓库维护]({% post_url 2026-09-25-git-analysis-and-maintenance %}) | 追踪代码变化，定位回归，选择适当的导出与维护工具 |

第二、三篇是日常开发基础。第四篇适合在已经理解分支关系后学习，并在练习仓库中演练。第五篇可以按问题查阅，不必为了完成学习路线而使用所有低频工具。已有经验的读者也可以直接使用[命令速查]({% post_url 2026-09-16-git-command-reference %})定位专题。

<span id="8-第六阶段安全地撤销错误"></span><span id="撤销尚未暂存的文件修改"></span><span id="取消暂存但保留文件修改"></span><span id="修正最近一次本地提交"></span><span id="撤销已经共享的提交"></span><span id="找回移动过的提交位置"></span><span id="本阶段练习-5"></span><span id="10-初学者最常见的误区"></span><span id="把-git-当成自动云盘"></span><span id="每次都执行-git-add-"></span><span id="遇到冲突就删除仓库重来"></span><span id="认为-ssh-成功就一定可以推送"></span><span id="从网上复制高风险命令"></span><span id="只追求命令执行成功"></span><span id="13-进一步阅读"></span>

## 6. 常见误区与操作原则

### 保存、提交与推送

编辑器保存只改变工作区；提交保存本地历史；推送分享提交。推送不会替你收集未提交文件，远程仓库也不会自动保留电脑上所有内容。需要备份的本地配置、未跟踪文件和大文件应有明确的保存方式。

### 检查与验证

常用顺序是检查状态、阅读差异、执行操作、验证结果。命令退出成功说明 Git 完成了请求，不代表改动满足业务需求。提交前需要检查文件范围，合并后需要检查最终内容并运行项目测试。

### 恢复范围

分支备份保护的是提交位置，不包含尚未提交的工作。reflog 保存本地引用变化，也不是永久备份。学习恢复命令时，必须同时理解哪些信息曾经进入 Git、哪些信息仍只存在于文件系统中。

## 命令速查

| 用途 | 命令 |
| --- | --- |
| 安装检查 | `git --version` |
| 状态检查 | `git status` |
| 未暂存差异 | `git diff` |
| 暂存文件 | `git add README.md` |
| 暂存差异 | `git diff --cached` |
| 提交检查 | `git show --stat HEAD` |

## 实践练习

在 README 中分别增加“使用方法”和“后续目标”，各形成一次独立提交。完成后检查日志中是否有四条提交，并尝试解释：若暂存后继续修改文件，立即执行提交会保存哪个版本？先作判断，再用差异命令验证。

## 参考资料

- [Pro Git：起步](https://git-scm.com/book/zh/v2/起步-关于版本控制)
- [Pro Git：Git 基础](https://git-scm.com/book/zh/v2/Git-基础-获取-Git-仓库)
- [Git 术语表](https://git-scm.com/docs/gitglossary)

**系列导航**：第一篇 / 共五篇 · [下一篇：基础操作与分支管理]({% post_url 2026-09-25-git-basics-and-branches %}) · [命令速查]({% post_url 2026-09-16-git-command-reference %})
