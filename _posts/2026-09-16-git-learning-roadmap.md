---
layout: post
title: "Git 学习路线：从第一次提交到团队协作"
date: 2026-09-16 10:00:00 +0800
categories: [学习]
tags: [Git, GitHub, 版本控制, 学习路线, 团队协作]
---

Git 的命令并不少，但初学者真正容易卡住的，通常不是“记不住命令”，而是说不清“当前修改究竟在哪里”“下一步为什么要这样做”。如果一开始只顾着背参数，遇到冲突、推送失败或误操作时，往往还是不知道该从哪里检查。

本文给出一条循序渐进的学习路线：先在本地建立完整的版本管理闭环，再学习分支、远程仓库和团队协作，最后接触历史整理与故障恢复。每个阶段都有明确的目标和练习，不要求你一次掌握 Git 的全部功能。

如果你还不熟悉终端、目录和路径，可以先阅读[《Linux 终端入门：常用命令与实用技巧》]({% post_url 2026-09-01-linux-terminal-common-commands %})；如果已经能在命令行中完成编译和调试，也可以结合[《Linux 命令行开发：编译、构建与调试》]({% post_url 2026-09-01-linux-command-line-development %})一起练习。

## 1. Git、GitHub 与版本控制

假设一份课程项目反复修改了几轮，目录里可能会出现下面这些文件：

```text
课程设计-初版.zip
课程设计-修改版.zip
课程设计-最终版.zip
课程设计-最终版2.zip
课程设计-真的最终版.zip
```

这种方式虽然保留了副本，却很难回答几个关键问题：某一版究竟改了什么、哪一版可以正常运行、错误从什么时候开始出现，以及两个人的修改应该如何合并。

Git 是一个分布式版本控制系统。它能够记录文件变化、比较不同版本、创建独立分支，也能让多人围绕同一段历史协作。GitHub、Gitee 和 GitLab 则是托管 Git 仓库，并提供代码审查、问题跟踪等功能的平台。

先记住下面几个区别：

- Git 是运行在本机上的版本控制工具；
- GitHub 是一种远程托管与协作平台；
- 没有 GitHub，也可以只在本地使用 Git；
- 配置 Git 的用户名和邮箱，不等于登录了 GitHub。

此时不必急着背命令。先理解一件事：Git 记录的不是一串名为“最终版”的文件，而是一段可以检查、比较和追溯的修改历史。

## 2. 先建立四个区域的心智模型

日常使用 Git 时，可以把一次修改的流转过程理解为四个区域：

```text
工作区  →  暂存区  →  本地仓库  →  远程仓库
 修改       选择        提交          分享
```

### 工作区

工作区就是正在编辑的项目目录。保存文件后，改动最先出现在这里。

### 暂存区

暂存区保存“准备放进下一次提交的内容”。因此，`git add` 不是上传文件，而是在挑选下一次提交要包含哪些变化。

### 本地仓库

执行 `git commit` 后，暂存区中的内容会成为一个本地提交。每个提交都记录作者、时间、说明，并与前面的提交相连，逐步形成项目历史。

### 远程仓库

远程仓库通常托管在 GitHub 等平台上。执行 `git push`，本地提交才会发送到远程；执行 `git fetch` 或 `git pull`，远程变化才会来到本地。

初学阶段，比“赶快推送到 GitHub”更重要的是经常执行 `git status`，观察文件如何在这些区域之间流转。

## 3. 第一阶段：完成本地版本管理闭环

先确认 Git 已经安装：

```text
git --version
```

第一次使用时配置提交身份：

```text
git config --global user.name "Your Name"
git config --global user.email "you@example.com"
git config --global init.defaultBranch main
```

用户名和邮箱会写入提交记录，用来标识作者。它们既不是 GitHub 密码，也不能说明当前终端已经获得远程仓库权限。

接下来创建练习目录。执行 `git init` 前，先用 `pwd` 或 PowerShell 的 `Get-Location` 确认当前位置，以免在错误目录中初始化仓库。

```text
mkdir git-practice
cd git-practice
git init
git status
```

创建一个 `README.md`，写入项目名称和用途，然后依次执行：

```text
git status
git diff
git add README.md
git diff --cached
git commit -m "docs: add project introduction"
git log --oneline
```

这几条命令组成了最小的版本管理闭环：

```text
编辑文件
   ↓
git status        观察当前状态
   ↓
git diff          检查未暂存修改
   ↓
git add           选择本次提交内容
   ↓
git diff --cached 检查已暂存修改
   ↓
git commit        保存一个历史快照
```

### 本阶段练习

连续修改三次 README，每次只完成一件事，例如依次添加项目目标、目录结构和运行方法。每轮都走完上面的闭环，最后用 `git log --oneline` 检查是否留下了三条清楚、易懂的记录。

## 4. 第二阶段：养成可靠的提交习惯

Git 能保存历史，但清晰的历史才真正有价值。与其一次提交大量文件，不如把修改拆成几个能够独立解释的提交。

### 一次提交只表达一个意图

例如，“增加登录校验”和“调整首页颜色”通常应该分成两次提交。这样既方便审查，也便于以后单独撤销其中一项修改。

提交信息应说明完成了什么：

```text
feat: add login validation
fix: handle empty configuration file
docs: add local build instructions
refactor: extract database initialization
test: cover invalid user input
```

这些前缀不是 Git 的硬性要求，但能帮助团队快速判断提交类型。比格式更重要的是：说明要具体，而且必须与实际修改一致。

### 暂存前后都检查差异

```text
git status
git diff
git add src/login.cpp tests/login_test.cpp
git diff --cached
git commit -m "fix: reject empty login credentials"
```

不要把 `git add .` 当成每次提交的固定动作。它虽然方便，却也可能把日志、临时文件、调试代码甚至密钥一并暂存。明确列出文件，或在熟悉 Git 后使用 `git add -p` 分块选择，通常更稳妥。

### 用 `.gitignore` 排除本地文件

常见项目可能需要：

```gitignore
# 构建产物
build/
dist/
*.o

# 日志和缓存
*.log
__pycache__/

# 本地环境和密钥
.env
.env.local

# 编辑器状态
.idea/
.vscode/
```

`.gitignore` 只对尚未被 Git 跟踪的文件生效。一个文件如果已经提交过，不会因为后来加入忽略规则就自动从历史中消失。

### 本阶段练习

创建一个 `build/` 目录和一个普通源文件，用 `git status` 观察二者；添加 `.gitignore` 后再次检查，确认构建目录不再出现，而源文件仍然可以被跟踪。

## 5. 第三阶段：使用分支隔离修改

分支让我们能够从当前历史中分出一条独立的开发线。它并不是项目的完整副本，而是一个指向提交的轻量引用。

```text
git switch -c feature/readme-links
```

完成修改并提交：

```text
git status
git add README.md
git commit -m "docs: add useful project links"
```

回到主分支并合并：

```text
git switch main
git merge feature/readme-links
git branch -d feature/readme-links
```

如果切换分支会覆盖尚未提交的修改，Git 通常会拒绝操作。这不是故障，而是在保护你的工作区。此时应先检查现有修改，再选择提交、用 `stash` 临时保存，或在确认无用后撤销，而不是直接使用强制参数。

### 什么是合并冲突

当两个分支修改了同一文件的同一区域，而 Git 无法替你判断最终内容时，就会产生冲突。冲突区域通常由三种标记包围：

- `<<<<<<< HEAD`：当前分支内容的开始；
- `=======`：双方内容的分隔线；
- `>>>>>>> feature/readme-links`：待合并分支内容的结束。

解决冲突的基本过程是：

1. 执行 `git status` 找到冲突文件；
2. 阅读双方修改，手工整理最终内容；
3. 删除冲突标记并运行必要的测试；
4. 使用 `git add` 标记该文件已经解决；
5. 完成合并提交。

冲突不代表仓库损坏，只是这个决定无法自动完成，必须交给了解上下文的人。

### 本阶段练习

创建两个分支，让它们修改 README 的同一行，然后尝试合并。不要跳过冲突，而是完整经历“发现—理解—修改—验证—提交”的过程。

## 6. 第四阶段：连接 GitHub 远程仓库

在 GitHub 上创建一个空仓库后，可以为本地仓库添加远程地址：

```text
git remote add origin <repository-url>
git remote -v
git push -u origin main
```

`origin` 只是约定俗成的远程名称，并不代表某台特殊服务器。`-u` 会让本地 `main` 跟踪对应的远程分支，此后通常可以直接执行 `git push` 和 `git pull`。

如果项目已经存在于远程，则通常直接克隆：

```text
git clone <repository-url>
cd <repository-directory>
git status
```

### SSH 与 HTTPS

- HTTPS 通常通过凭据管理器或个人访问令牌认证；
- SSH 使用本机私钥和上传到平台的公钥完成认证；
- 密码、令牌和私钥都不应写入仓库、脚本或远程 URL。

这里还要区分“认证”和“授权”：`ssh -T git@github.com` 成功，只能说明平台识别了当前 SSH 身份，并不代表这个账号有权访问某个私有仓库。如果出现 `Repository not found`，应依次检查远程地址、仓库是否存在、账号权限，以及协作者邀请是否已经接受。

### 本阶段练习

把练习仓库推送到一个新建的远程仓库，再在另一个临时目录中克隆它。比较两个目录的 `git log --oneline`，确认提交历史一致。

## 7. 第五阶段：建立团队协作流程

一个简单而可靠的功能开发流程是：

```text
更新远程信息
    ↓
从 main 创建功能分支
    ↓
开发、检查、分批提交
    ↓
推送功能分支
    ↓
创建 Pull Request
    ↓
审查、测试并合并
```

开始工作前先更新远程信息：

```text
git switch main
git fetch origin
git status
git pull --ff-only
git switch -c feature/search
```

完成后推送功能分支：

```text
git push -u origin feature/search
```

Pull Request 不只是一个“申请合并”的按钮，它还是差异审查、自动测试、讨论和决策记录的集中入口。团队可以借此在合并前发现命名、边界条件、测试覆盖和接口兼容等问题。

### `fetch` 与 `pull` 的区别

`git fetch` 只更新远程引用，不会立刻改动当前分支；`git pull` 则会先获取远程变化，再按配置执行合并或变基。因此，当你还不确定远程发生了什么时，先 `fetch`、查看差异，再决定如何整合，过程通常更可控：

```text
git fetch origin
git log --oneline HEAD..origin/main
git diff HEAD...origin/main
```

### 本阶段练习

与同学共享一个练习仓库，每人使用自己的功能分支和账号完成一次小修改，通过 Pull Request 合并。记录一次审查意见，并在后续提交中修正它。

## 8. 第六阶段：安全地撤销错误

撤销之前，先判断修改处于工作区、暂存区还是提交历史。不同阶段对应不同工具，不要一看到错误就执行 `reset --hard`。

### 撤销尚未暂存的文件修改

```text
git diff -- README.md
git restore README.md
```

`git restore` 会用暂存区中的版本覆盖工作区修改。执行前要确认这些内容确实不再需要。

### 取消暂存，但保留文件修改

```text
git restore --staged README.md
```

文件内容仍然保留在工作区，只是不再包含在下一次提交中。

### 修正最近一次本地提交

```text
git add README.md
git commit --amend
```

`--amend` 会创建一个新提交来替换当前提交。如果旧提交已经推送，而且其他人可能基于它继续工作，就不应随意改写。

### 撤销已经共享的提交

```text
git revert <commit>
```

`revert` 不会删除原提交，而是新增一个反向提交来抵消它的变化，因此更适合共享分支。

### 找回移动过的提交位置

```text
git reflog
```

引用日志记录了本地分支和 `HEAD` 曾经指向的位置，常用于找回被误删的分支，或定位错误重置前的提交。它只是本地恢复线索，不是远程备份，也不会永久保留所有记录。

### 本阶段练习

分别练习“撤销未暂存修改”“取消暂存”和“revert 一个已提交修改”。每一步都先运行 `git status`、`git diff` 或 `git log`，确认命令影响的对象。

## 9. 第七阶段：选择性学习进阶工具

完成前六个阶段后，不必急着把所有进阶命令学完；更合适的方式是根据真实需求逐步补充：

- `git stash`：临时收起尚未完成的工作；
- `git rebase`：把一组提交重新应用到新的起点；
- `git cherry-pick`：将指定提交应用到当前分支；
- `git tag`：标记发布版本；
- `git bisect`：用二分搜索定位引入问题的提交；
- `git worktree`：同时检出多个分支，适合并行开发和紧急修复；
- `git submodule`：在仓库中记录另一个仓库的特定提交。

学习这些工具时，还要同时弄清它们是否会改写历史、影响工作区，或产生新的共享状态。会执行命令只是起点，能够预判结果、解释影响，才算真正掌握。

## 10. 初学者最常见的误区

### 把 Git 当成自动云盘

Git 不会在保存文件时自动上传内容。修改只有先提交到本地历史，再完成推送，才会出现在远程仓库中。

### 每次都执行 `git add .`

这样很容易把无关文件混进提交。提交前至少要检查 `git status` 和 `git diff --cached`。

### 遇到冲突就删除仓库重来

冲突通常只涉及少量文件。先阅读 `git status`，如果暂时不准备继续处理，可以使用 `git merge --abort` 或 `git rebase --abort` 返回操作前的状态。

### 认为 SSH 成功就一定可以推送

平台识别身份、远程 URL 正确、账号拥有仓库权限，是三个彼此独立的条件，需要分别验证。

### 从网上复制高风险命令

`git reset --hard`、`git clean -fd` 和强制推送都可能造成难以恢复的结果。执行前必须弄清它们会影响哪个分支、哪些文件，以及是否已有可靠的恢复入口。

### 只追求“命令执行成功”

Git 没有报错，并不代表提交内容一定正确。真正的完成标准还包括差异符合预期、测试通过、没有敏感信息，以及远程分支符合团队约定。

## 11. 一个完整的练习项目

可以用一个纯文本“学习任务清单”完成整条路线：

1. 创建 `git-practice` 目录并初始化仓库；
2. 添加 README，写明项目目标；
3. 用三次提交增加任务、完成状态和使用说明；
4. 添加 `.gitignore`，排除日志和本地配置；
5. 创建 `feature/statistics` 分支并增加统计文件；
6. 在两个分支修改同一行，制造并解决一次冲突；
7. 创建 GitHub 仓库并推送 `main`；
8. 推送功能分支并创建 Pull Request；
9. 合并后在另一个目录重新克隆；
10. 使用 `git log --graph --oneline --decorate --all` 回顾整个历史。

练习时不必追求使用了多少命令，更重要的是随时能够回答：当前修改在哪里、下一次提交包含什么、当前分支跟踪哪个远程分支，以及撤销操作会覆盖哪些内容。

## 12. 学习完成标准

完成这条路线后，可以用下面的清单自测：

- [ ] 能解释工作区、暂存区、本地仓库和远程仓库；
- [ ] 能独立完成“检查—暂存—复查—提交”；
- [ ] 能编写范围清晰的提交并使用 `.gitignore`；
- [ ] 能创建、切换和合并功能分支；
- [ ] 能通过 `fetch` 查看远程变化并安全同步；
- [ ] 能参与一次基于 Pull Request 的协作；
- [ ] 能解决简单的文本冲突；
- [ ] 能根据修改所处阶段选择撤销方式；
- [ ] 能区分远程地址、身份认证和仓库授权问题；
- [ ] 面对不熟悉的命令时，会先查看帮助和影响范围。

当这些操作已经形成稳定习惯，就不必再按固定顺序学习。此后的进阶更适合从问题出发：需要整理提交时查 `rebase`，需要定位回归时查 `bisect`，需要并行处理紧急修复时查 `worktree`。

常见操作、进阶组合和风险提示已经整理在[《Git 常用命令手册：从日常操作到历史恢复》]({% post_url 2026-09-16-git-command-reference %})中，可以把它作为日常开发时的检索入口。

## 13. 进一步阅读

- [Git 官方参考手册](https://git-scm.com/docs)
- [Pro Git 在线书籍](https://git-scm.com/book/zh/v2)
- [Git 官方速查表](https://git-scm.com/cheat-sheet.pdf)

学习 Git，最值得训练的不是记忆命令，而是判断操作边界：先观察状态，再理解差异，最后执行范围明确的操作。只要坚持这个顺序，大多数问题都能被拆解为一组可以验证的小步骤。
