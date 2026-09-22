---
layout: post
title: "Git 学习路线：从第一次提交到团队协作"
date: 2026-09-16 10:00:00 +0800
categories: [学习]
tags: [Git, GitHub, 版本控制, 学习路线, 团队协作]
---

Git 的命令并不算少，但真正让初学者感到困难的，往往不是记不住命令，而是不清楚“当前修改究竟在哪里”“下一步为什么要这样做”。如果一开始就背诵大量参数，很容易在遇到冲突、推送失败或误操作时失去判断依据。

本文提供一条循序渐进的学习路线：先在本地建立完整的版本管理闭环，再学习分支、远程仓库和团队协作，最后接触历史整理与故障恢复。每个阶段都给出明确目标和练习，不要求一次掌握 Git 的全部功能。

如果你还不熟悉终端、目录和路径，可以先阅读[《Linux 终端入门：常用命令与实用技巧》]({% post_url 2026-09-01-linux-terminal-common-commands %})；如果已经能在命令行中完成编译和调试，也可以结合[《Linux 命令行开发：编译、构建与调试》]({% post_url 2026-09-01-linux-command-line-development %})一起练习。

## 1. Git、GitHub 与版本控制

假设一份课程项目经历了多次修改，我们可能会得到下面这些文件：

```text
课程设计-初版.zip
课程设计-修改版.zip
课程设计-最终版.zip
课程设计-最终版2.zip
课程设计-真的最终版.zip
```

这种方式能够暂时保留副本，却很难回答几个重要问题：某次修改具体改了什么、哪一版可以运行、一个错误从什么时候出现，以及两个人的修改应该如何合并。

Git 是一个分布式版本控制系统。它可以记录文件变化、比较不同版本、创建独立分支，并让多人围绕同一份历史进行协作。GitHub、Gitee 和 GitLab 则是托管 Git 仓库并提供代码审查、问题跟踪等功能的平台。

可以先记住这个区别：

- Git 是运行在本机上的版本控制工具；
- GitHub 是一种远程托管与协作平台；
- 没有 GitHub，也可以只在本地使用 Git；
- 配置 Git 的用户名和邮箱，不等于登录了 GitHub。

这一阶段不需要背命令，只需要理解 Git 记录的不是一串“最终文件”，而是一段可以检查和追溯的修改历史。

## 2. 先建立四个区域的心智模型

日常使用 Git 时，可以把项目理解为四个区域：

```text
工作区  →  暂存区  →  本地仓库  →  远程仓库
 修改       选择        提交          分享
```

### 工作区

工作区就是正在编辑的项目目录。保存文件后，修改首先只存在于工作区中。

### 暂存区

暂存区保存“准备放进下一次提交的内容”。`git add` 不是上传文件，而是在选择下一次提交要包含哪些变化。

### 本地仓库

执行 `git commit` 后，暂存区中的内容会成为一个本地提交。提交包含作者、时间、说明以及指向前一个提交的关系，由此形成历史。

### 远程仓库

远程仓库是 GitHub 等平台上的仓库。执行 `git push` 才会把本地提交发送到远程；执行 `git fetch` 或 `git pull` 才会获取远程变化。

初学阶段最重要的动作不是“立刻推送”，而是经常执行 `git status`，观察文件如何在这些区域之间移动。

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

用户名和邮箱会进入提交记录。它们用于标识提交作者，不是 GitHub 密码，也不代表当前终端已经获得远程仓库权限。

接下来创建练习目录。执行 `git init` 前应先用 `pwd` 或 PowerShell 的 `Get-Location` 确认当前位置，避免在错误目录中初始化仓库。

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

这几个命令构成最小闭环：

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

对 README 连续进行三次小修改，每次只完成一件事，例如添加项目目标、目录结构和运行方法。每次修改后都走完上面的闭环，最后用 `git log --oneline` 检查是否得到三条容易理解的记录。

## 4. 第二阶段：养成可靠的提交习惯

Git 可以保存历史，但只有清晰的历史才真正有价值。相比一次性提交大量文件，更推荐把修改拆成几个可以独立解释的提交。

### 一次提交只表达一个意图

例如，“增加登录校验”和“调整首页颜色”通常应该是两次提交。这样既方便审查，也便于将来只撤销其中一项修改。

提交信息应说明完成了什么：

```text
feat: add login validation
fix: handle empty configuration file
docs: add local build instructions
refactor: extract database initialization
test: cover invalid user input
```

前缀不是 Git 的硬性要求，但它能帮助团队快速判断提交类型。真正重要的是说明具体、与内容一致。

### 暂存前后都检查差异

```text
git status
git diff
git add src/login.cpp tests/login_test.cpp
git diff --cached
git commit -m "fix: reject empty login credentials"
```

不要把 `git add .` 当成每次提交的固定动作。它确实方便，但也可能把日志、临时文件、调试代码甚至密钥一起暂存。明确列出文件，或在熟悉 Git 后使用 `git add -p` 分块选择，通常更可控。

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

`.gitignore` 只对尚未被 Git 跟踪的文件生效。已经提交过的文件不会因为后来加入忽略规则而自动从历史中消失。

### 本阶段练习

创建一个 `build/` 目录和一个普通源文件，通过 `git status` 观察二者；添加 `.gitignore` 后再次检查，确认构建目录不再出现，而源文件仍然可以被跟踪。

## 5. 第三阶段：使用分支隔离修改

分支允许我们从当前历史上创建一条独立开发线。它不是复制整个项目，而是一个指向提交的轻量引用。

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

如果分支切换会覆盖尚未提交的修改，Git 通常会拒绝切换。这不是故障，而是在保护工作区。遇到这种情况，应先检查修改，选择提交、暂存到 `stash`，或确认后撤销，而不是直接使用强制参数。

### 什么是合并冲突

当两个分支修改同一文件的同一区域，并且 Git 无法自动判断要保留哪一版时，就会产生冲突。冲突区通常由三种标记包围：

- `<<<<<<< HEAD`：当前分支内容的开始；
- `=======`：双方内容的分隔线；
- `>>>>>>> feature/readme-links`：待合并分支内容的结束。

解决冲突的基本过程是：

1. 执行 `git status` 找到冲突文件；
2. 阅读双方修改，手工整理最终内容；
3. 删除冲突标记并运行必要的测试；
4. 使用 `git add` 标记该文件已经解决；
5. 完成合并提交。

冲突不代表仓库损坏，它只表示这个决定需要由了解业务的人完成。

### 本阶段练习

创建两个分支，让它们修改 README 的同一行，然后尝试合并。不要跳过冲突，而是完整经历“发现—理解—修改—验证—提交”的过程。

## 6. 第四阶段：连接 GitHub 远程仓库

在 GitHub 上创建一个空仓库后，可以为本地仓库添加远程地址：

```text
git remote add origin <repository-url>
git remote -v
git push -u origin main
```

`origin` 只是默认使用的远程名称，不是特殊服务器。`-u` 会让本地 `main` 跟踪对应的远程分支，以后通常可以直接执行 `git push` 和 `git pull`。

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

还要区分“认证”和“授权”：`ssh -T git@github.com` 成功，只能证明平台识别了当前 SSH 身份；它不能证明这个账号拥有某个私有仓库的访问权。如果出现 `Repository not found`，应检查远程地址、仓库是否存在、账号权限以及协作者邀请是否已经接受。

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

Pull Request 不只是“申请合并”的按钮。它还提供差异审查、自动测试、讨论和决策记录。团队可以在合并前发现命名、边界条件、测试覆盖或接口兼容问题。

### `fetch` 与 `pull` 的区别

`git fetch` 获取远程引用，但不会立刻改动当前分支；`git pull` 会先获取，再按照配置执行合并或变基。因此，在不确定远程变化时，先 `fetch`、再查看差异，通常更容易控制：

```text
git fetch origin
git log --oneline HEAD..origin/main
git diff HEAD...origin/main
```

### 本阶段练习

与同学共享一个练习仓库，每人使用自己的功能分支和账号完成一次小修改，通过 Pull Request 合并。记录一次审查意见，并在后续提交中修正它。

## 8. 第六阶段：安全地撤销错误

撤销前先判断修改位于哪个区域。不同阶段使用不同命令，不要一看到错误就执行 `reset --hard`。

### 撤销尚未暂存的文件修改

```text
git diff -- README.md
git restore README.md
```

`git restore` 会覆盖工作区中的对应修改。执行前应确认这些修改确实不再需要。

### 取消暂存，但保留文件修改

```text
git restore --staged README.md
```

文件内容仍保留在工作区，只是不再进入下一次提交。

### 修正最近一次本地提交

```text
git add README.md
git commit --amend
```

`--amend` 会用一个新提交替换当前提交。若旧提交已经推送并被其他人基于它继续工作，就不应随意改写。

### 撤销已经共享的提交

```text
git revert <commit>
```

`revert` 不删除原提交，而是创建一个内容相反的新提交，更适合共享分支。

### 找回移动过的提交位置

```text
git reflog
```

引用日志记录本地分支和 `HEAD` 曾经指向的位置，常用于找回误删分支或错误重置前的提交。它是本地恢复线索，不是远程备份，也不会永久保存所有记录。

### 本阶段练习

分别练习“撤销未暂存修改”“取消暂存”和“revert 一个已提交修改”。每一步都先运行 `git status`、`git diff` 或 `git log`，确认命令影响的对象。

## 9. 第七阶段：选择性学习进阶工具

完成前六个阶段后，再根据真实需求学习进阶命令：

- `git stash`：临时收起尚未完成的工作；
- `git rebase`：把一组提交重新应用到新的起点；
- `git cherry-pick`：将指定提交应用到当前分支；
- `git tag`：标记发布版本；
- `git bisect`：用二分搜索定位引入问题的提交；
- `git worktree`：同时检出多个分支，适合并行开发和紧急修复；
- `git submodule`：在仓库中记录另一个仓库的特定提交。

学习这些工具时，应同时理解它们是否会改写历史、影响工作区或产生新的共享状态。会执行命令只是开始，能够预测命令的影响才算真正掌握。

## 10. 初学者最常见的误区

### 把 Git 当成自动云盘

Git 不会自动上传保存的文件。只有提交进入本地历史，推送后才会出现在远程仓库。

### 每次都执行 `git add .`

这样容易混入无关文件。提交前至少检查 `git status` 和 `git diff --cached`。

### 遇到冲突就删除仓库重来

冲突通常只影响少量文件。先阅读 `git status`，必要时使用 `git merge --abort` 或 `git rebase --abort` 返回操作前状态。

### 认为 SSH 成功就一定可以推送

认证成功、远程 URL 正确和拥有仓库权限是三个不同条件，需要分别验证。

### 从网上复制高风险命令

`git reset --hard`、`git clean -fd` 和强制推送都可能造成难以恢复的结果。执行前必须知道将影响哪个分支、哪些文件，以及是否已经有可靠备份。

### 只追求“命令执行成功”

Git 没有报错，不代表提交内容正确。真正的完成标准还包括差异合理、测试通过、没有敏感信息，以及远程分支符合团队约定。

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

练习过程中不要追求命令数量，而要确保自己能回答：当前修改在哪里、下一次提交包含什么、当前分支跟踪哪个远程分支，以及撤销操作会覆盖哪些内容。

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

当这些操作已经形成稳定习惯，就不必继续按顺序学习。下一步更适合以问题为入口：需要整理提交时查 `rebase`，需要定位回归时查 `bisect`，需要并行处理紧急修复时查 `worktree`。

常见操作、进阶组合和风险提示已经整理在[《Git 常用命令手册：从日常操作到历史恢复》]({% post_url 2026-09-16-git-command-reference %})中，可以把它作为日常开发时的检索入口。

## 13. 进一步阅读

- [Git 官方参考手册](https://git-scm.com/docs)
- [Pro Git 在线书籍](https://git-scm.com/book/zh/v2)
- [Git 官方速查表](https://git-scm.com/cheat-sheet.pdf)

Git 最值得训练的不是记忆，而是判断：先观察状态，再理解差异，最后执行范围明确的操作。只要坚持这条顺序，大多数 Git 问题都能被拆解成可以验证的小步骤。
