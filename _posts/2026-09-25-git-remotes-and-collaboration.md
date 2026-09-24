---
layout: post
title: "Git 远程协作与版本管理"
date: 2026-09-25 00:02:00 +0800
categories: [学习]
tags: [Git, GitHub, 团队协作, 版本管理, Git系列]
excerpt: "区分本地分支、远程跟踪分支与上游关系，用双目录案例演练同步和分叉，并学习 stash、worktree 与版本标记。"
---

远程协作的难点，是本地看到的远程信息可能已经过时，而不同开发者又会同时推进历史。理解引用之间的关系，才能解释为什么拉取需要整合、推送可能被拒绝，以及临时任务应该放在哪里完成。

本文是 Git 系列第三篇，默认已经掌握[本地提交与分支合并]({% post_url 2026-09-25-git-basics-and-branches %})。案例使用两个克隆目录模拟两名开发者，远程同步部分还提供本地裸仓库方案，无须向真实平台发布练习内容。各处的 `<url>`、`<branch>` 均应替换为实际值。

## 1. 远程仓库与分支关系

### 引用层次

常见的三个名字分别指向不同对象：

| 名称 | 所在位置 | 含义 |
| --- | --- | --- |
| `main` | 本地仓库 | 当前开发者可以提交到的分支 |
| `origin/main` | 本地仓库 | 最近获取到的远程分支位置 |
| 远程的 `main` | 服务器或另一仓库 | 协作者推送时更新的分支 |

`origin` 只是远程配置名称，可以重命名，也可以同时配置多个远程。`origin/main` 是本地的远程跟踪引用，并非每次查看时都实时请求服务器。因此，`status` 中的领先、落后信息通常只反映最近获取的状态。

```text
本地 main ── push ──> 远程 main
本地 origin/main <── fetch ── 远程 main
```

fetch 获取对象并更新相关引用，不会自动把远程改动合并到当前开发分支。pull 则先获取，再按参数或配置整合。

### 上游关系

上游配置让 Git 知道当前分支通常与哪条分支比较和同步：

```bash
git branch -vv
git status --short --branch
```

`push -u origin feature/tasks` 会在成功推送时建立相应上游关系。已有远程跟踪分支时，也可以通过 `git branch --set-upstream-to=origin/main main` 配置本地 `main` 的上游。无参数 push 的行为还受 `push.default` 等设置影响；不确定时明确写出远程和分支。

## 2. 远程连接与上游配置

### 托管仓库连接

对已有平台仓库，通常直接克隆。对已有本地仓库，则先在平台建立空仓库，再添加远程：

```bash
git remote add origin <url>
git remote -v
git push -u origin main
```

两种路径是替代关系。平台仓库若已经包含独立初始化的 README，本地又有自己的初始提交，可能出现两段无共同祖先的历史；初学练习使用空远程能避免这一额外问题。

提交用户名和邮箱只标识作者。HTTPS 凭据与 SSH 密钥用于认证，仓库权限属于授权。使用 SSH 时，测试成功只能说明平台识别了密钥，不能证明账号有权访问某个私有仓库。不要把令牌、密码或私钥写入远程 URL 或项目文件。

### 本地双目录实验

下面的方案与上面的托管方案独立。在新的空目录中执行，所有路径均为练习目录：

```bash
mkdir git-collaboration-lab
cd git-collaboration-lab
git init --bare --initial-branch=main central.git
git clone central.git alice
cd alice
git config user.name "Alice Practice"
git config user.email "alice@example.com"
```

空仓库克隆警告在此处属于预期。创建 `README.md`，写入 `Learning task collaboration`，然后：

```bash
git add README.md
git commit -m "docs: initialize collaboration practice"
git push -u origin main
cd ..
git clone central.git bob
cd bob
git config user.name "Bob Practice"
git config user.email "bob@example.com"
```

`central.git` 是无普通工作区的裸仓库，用来接收推送；日常编辑只在 `alice` 与 `bob` 目录进行。初始化 `main` 后再克隆 Bob，可确保其初始分支有可检出的提交。本地路径不涉及网络认证，适合专注观察提交关系。

## 3. 远程同步与分叉处理

### 领先与落后

在 Bob 的 README 末尾增加 `Contributor: Bob` 并提交、推送：

```bash
git add README.md
git commit -m "docs: record Bob contribution"
git push origin main
cd ../alice
git fetch origin
git log --oneline HEAD..origin/main
git rev-list --left-right --count HEAD...origin/main
```

Alice 没有新提交时，最后一条应输出左右计数 `0 1`：当前分支没有独有提交，远程跟踪分支有一个。此时可快进：

```bash
git merge --ff-only origin/main
```

检查 README 应能看到 Bob 的新增内容。此例把获取和整合分开，便于在修改当前分支前先阅读远程变化。

### 双向分叉

在 Alice 创建 `alice-notes.txt`，写入 `Alice task notes`，提交但暂不推送，然后切换目录：

```bash
git add alice-notes.txt
git commit -m "docs: add Alice notes"
cd ../bob
```

在 Bob 目录创建 `bob-notes.txt`，写入 `Bob task notes`，再提交并推送：

```bash
git add bob-notes.txt
git commit -m "docs: add Bob notes"
git push origin main
cd ../alice
git fetch origin
git rev-list --left-right --count HEAD...origin/main
```

回到 Alice 并获取远程后，应得到 `1 1`。两边各有一个独有提交，单纯移动分支指针已无法同时保留两条历史。

```text
      B  ← Alice main
     /
A ──
     \
      C  ← origin/main
```

`git merge --ff-only origin/main` 会拒绝这种分叉。拒绝并不意味着内容冲突，只表示无法快进。练习采用合并保留两边提交：

```bash
git merge -m "merge: integrate collaborator notes" origin/main
git log --graph --oneline --decorate -n 8
git push origin main
```

两个新增文件互不冲突，通常可以自动合并。完成后，Alice 和远程都包含双方记录，Bob 则需要再次获取并整合。

### 整合策略

`pull --ff-only` 适合只允许快进的更新；`pull --rebase` 会在获取后重放本地提交，适用于团队允许整理的个人历史；普通 pull 的行为受配置和 Git 版本影响，建议明确约定策略。

重放会改变提交标识，具体操作见[历史重写与撤销恢复]({% post_url 2026-09-25-git-history-and-recovery %})。共享分支分叉时不能只为了让 push 成功就覆盖远程，应该先检查双方独有提交。

## 4. 功能分支协作流程

### 开发与审查

真实项目通常在功能分支工作，再通过平台提交 Pull Request。开始前保存当前工作，并更新主分支：

```bash
git switch main
git fetch origin
git merge --ff-only origin/main
git switch -c feature/task-filter
```

在功能分支中修改、复查并提交，再执行：

```bash
git push -u origin feature/task-filter
```

平台上选择目标分支 `main` 和来源分支 `feature/task-filter`，检查差异、说明修改目的、等待测试与审查。Pull Request 保存的是讨论和审查过程，本地 Git 命令并不会自动创建它。本地裸仓库实验也不提供这个界面。

### 开发期间更新

主分支产生新变化时，可以在当前功能分支获取并合并：

```bash
git fetch origin
git merge origin/main
```

冲突处理沿用第二篇的流程。个人分支是否采用 rebase，应遵循团队规则；已经有其他人基于其工作的分支不应随意重写。

### 合并后清理

确认平台完成合并后，更新主分支，再检查分支是否可以删除：

```bash
git switch main
git fetch --prune origin
git merge --ff-only origin/main
git branch -d feature/task-filter
```

若采用 squash，Git 可能因原提交未成为主分支祖先而拒绝 `-d`。需要确认内容已合入、没有未交付工作后再决定处理，不能把拒绝一律视为错误。远程分支删除可由平台完成，也可明确执行 `git push origin --delete feature/task-filter`；`fetch --prune` 只清理对应的过期跟踪引用，不直接删除同名本地分支。

## 5. 任务切换与多工作区管理

### 方案选择

| 方案 | 适用情形 | 工作现场 |
| --- | --- | --- |
| 临时提交 | 工作可以形成可理解的阶段记录 | 内容保存在当前分支历史中 |
| stash | 短时间切走，仍使用同一目录 | 修改收起，稍后恢复 |
| worktree | 需要同时查看或运行两个版本 | 原目录保持，新目录独立工作 |

### 暂存工作

假设正在功能分支修改 README，临时需要切回主分支：

```bash
git status
git stash push -u -m "task filter in progress"
git stash list
git switch main
```

默认 stash 保存已跟踪文件的工作区和索引状态；`-u` 还包含未跟踪文件，不包含被忽略文件。`-a` 会包含被忽略文件，应先核对体积和范围。stash 是本地记录，不会随着普通 push 自动分享。

回到原功能分支后，先检查再恢复：

```bash
git stash show -p "stash@{0}"
git stash apply "stash@{0}"
git status
```

引用加引号可避免 PowerShell 对花括号等字符的解释。`apply` 保留条目，确认恢复正确后再 `git stash drop "stash@{0}"`；默认 apply 不保证还原原先的暂存分组，需要恢复索引时可考虑 `--index`，但也可能因冲突失败。`pop` 则在成功应用后删除条目，发生冲突时会保留它。

恢复冲突时编辑文件并暂存，之后正常提交；stash 没有 `--continue` 流程。若不确定如何放弃恢复，应先保存当前现场，不要假设存在 `stash --abort`。底层历史变化较大时，`git stash branch <new-branch> "stash@{0}"` 可从保存时的起点创建分支并尝试恢复。

### 多工作区

在当前仓库执行：

```bash
git fetch origin
git worktree add -b hotfix/task-format ../git-practice-hotfix origin/main
git worktree list
```

新目录检出一个从刚获取的主分支创建的修复分支。原工作区的未完成内容保持原状。各工作区共享对象数据库和多数引用，但拥有各自的 HEAD、索引与文件；同一个普通分支通常不能同时在两个工作区检出。

修复完成后，在新目录提交并按团队流程交付，再回到原目录移除工作区：

```bash
git worktree remove ../git-practice-hotfix
```

移除工作区不等于合并或删除修复分支。若拒绝移除，应检查未提交、未跟踪内容；不要直接强制删除目录。`worktree prune --dry-run` 用于检查失效管理记录，也不是删除有效工作区的替代命令。

## 6. 版本标记与协作故障排查

### 版本标记

当主分支上的某个提交通过验收，可以用附注标签标记版本：

```bash
git tag -a v0.1.0 -m "First verified task release"
git show v0.1.0
git push origin v0.1.0
```

轻量标签只是引用，附注标签还保存标记者、说明等信息。这里显式推送一个标签，避免把本地所有实验标签一起发布。普通 push 通常不会推送全部标签；`--follow-tags` 也只推送符合条件的附注标签。

标签标记的是提交，不包含尚未提交的文件。已发布标签应保持稳定，修复后通常创建新版本标签。托管平台的 Release 页面和附件是另一层发布信息，不会仅凭本地 tag 命令自动生成。

### 故障分类

| 现象 | 优先检查 | 处理方向 |
| --- | --- | --- |
| `not a git repository` | 当前目录、仓库根路径 | 进入正确目录 |
| `remote origin already exists` | `git remote -v` | 确认后修改已有 URL |
| `Repository not found` | 地址、账号、访问权限 | 核对仓库与协作者授权 |
| `non-fast-forward` | 获取后的双方独有提交 | 合并或按约定重放 |
| `unrelated histories` | 是否独立初始化或选错仓库 | 先核对来源，再决定迁移 |
| `dubious ownership` | 目录所有者与当前用户 | 核对权限，不广泛放开信任 |

网络或认证故障可先用 `git ls-remote origin` 测试仓库引用访问。SSH 用户可用 `ssh -T git@github.com` 检查身份，但应阅读输出，GitHub 不提供交互 shell，不能只凭退出状态判断登录测试。分支保护规则、推送策略和配额也可能阻止写入，应结合服务器返回的信息定位。

## 命令速查

| 任务 | 命令 |
| --- | --- |
| 上游检查 | `git branch -vv` |
| 远程更新 | `git fetch origin` |
| 双方计数 | `git rev-list --left-right --count HEAD...origin/main` |
| 快进整合 | `git merge --ff-only origin/main` |
| 首次推送 | `git push -u origin <branch>` |
| 暂存现场 | `git stash push -u -m "message"` |
| 工作区列表 | `git worktree list` |

## 实践练习

完成双目录实验后，让 Bob 获取 Alice 的合并结果，比较两个目录的 `git rev-parse HEAD`。然后在 Alice 保留一项未提交修改，用 worktree 创建独立修复分支。验收时确认：双方主分支提交一致，原目录内容未被带入修复提交，发布标签指向已验收的提交。

## 参考资料

- [git-fetch](https://git-scm.com/docs/git-fetch)、[git-pull](https://git-scm.com/docs/git-pull)、[git-push](https://git-scm.com/docs/git-push)
- [git-stash](https://git-scm.com/docs/git-stash)、[git-worktree](https://git-scm.com/docs/git-worktree)
- [git-tag](https://git-scm.com/docs/git-tag)
- [GitHub：测试 SSH 连接](https://docs.github.com/en/authentication/connecting-to-github-with-ssh/testing-your-ssh-connection)

**系列导航**：第三篇 / 共五篇 · [上一篇：基础操作与分支管理]({% post_url 2026-09-25-git-basics-and-branches %}) · [下一篇：历史重写与撤销恢复]({% post_url 2026-09-25-git-history-and-recovery %}) · [系列导读]({% post_url 2026-09-16-git-learning-roadmap %}) · [命令速查]({% post_url 2026-09-16-git-command-reference %})
