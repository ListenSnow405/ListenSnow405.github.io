---
layout: post
title: "Git 常用命令手册：从日常操作到历史恢复"
date: 2026-09-16 10:10:00 +0800
categories: [学习]
tags: [Git, GitHub, 命令速查, 版本控制, 开发工具]
---

Git 的操作横跨工作区、暂存区、提交历史、分支、远程同步和故障恢复等多个场景。真正遇到问题时，只记得命令名称往往不够；更重要的是知道它会读取什么、修改什么，以及是否会影响共享历史。

这份手册按实际场景组织，适合已经掌握基本提交与分支操作、需要快速查找命令的读者。如果你还没有建立“工作区—暂存区—本地仓库—远程仓库”的完整认识，建议先阅读[《Git 学习路线：从第一次提交到团队协作》]({% post_url 2026-09-16-git-learning-roadmap %})。

## 1. 阅读约定与风险等级

示例中的占位符需要替换为实际内容：

```text
<file>       文件路径
<branch>     分支名
<commit>     提交哈希、标签或其他提交引用
<remote>     远程名，通常是 origin
<url>        远程仓库地址
```

命令按照影响范围分为三类：

| 标记 | 含义 |
| --- | --- |
| 安全 | 主要用于查看，或产生容易撤销的新记录 |
| 谨慎 | 会修改工作区、暂存区或本地历史，执行前应检查状态 |
| 高风险 | 可能丢弃文件、改写共享历史或覆盖远程分支 |

风险取决于具体参数和使用场景。例如，`git reset` 并非总是危险，但 `git reset --hard` 会覆盖已跟踪文件在工作区中的修改。执行任何会改变仓库状态的命令前，都建议先查看：

```text
git status
git diff
git diff --cached
```

## 2. 帮助、版本与基础配置

### 查看版本和帮助

```text
git --version
git help <command>
git <command> --help
git <command> -h
```

`--help` 通常打开完整手册，`-h` 则在终端中显示简短选项列表。

### 查看配置

```text
git config --list
git config --show-origin --list
git config --global --list
git config --local --list
```

Git 配置主要分为三个层级：

- `--system`：整台计算机；
- `--global`：当前用户；
- `--local`：当前仓库，默认优先级最高。

`--show-origin` 会同时显示每条配置来自哪个文件，适合排查“配置明明改过，却没有生效”的问题。

### 常用初始化配置

```text
git config --global user.name "Your Name"
git config --global user.email "you@example.com"
git config --global init.defaultBranch main
git config --global core.editor "code --wait"
```

读取或删除单项配置：

```text
git config --get user.email
git config --unset --local <key>
git config --unset --global <key>
```

配置别名示例：

```text
git config --global alias.st status
git config --global alias.last "log -1 --stat"
git config --global alias.graph "log --graph --oneline --decorate --all"
```

## 3. 创建、克隆与定位仓库

### 初始化仓库

```text
git init
git init -b main
git init <directory>
```

在现有目录执行前先确认路径：

```text
pwd                         # Bash、Zsh
Get-Location                # PowerShell
git rev-parse --show-toplevel
```

最后一条命令只有在 Git 仓库内部才能成功执行，并会输出仓库根目录。

### 克隆仓库

```text
git clone <url>
git clone <url> <directory>
git clone --branch <branch> <url>
git clone --depth 1 <url>
git clone --recurse-submodules <url>
```

`--depth 1` 会创建浅克隆，只获取有限的提交历史，适合临时构建或体积较大的仓库。后续如果需要补全历史，可以执行：

```text
git fetch --unshallow
```

### 判断当前是否在仓库中

```text
git rev-parse --is-inside-work-tree
git rev-parse --is-bare-repository
git rev-parse --git-dir
```

## 4. 查看工作区状态

```text
git status
git status --short
git status --branch --short
git branch --show-current
```

`git status --short` 使用两列字符分别表示暂存区和工作区的状态。例如：

```text
 M README.md     工作区已修改，尚未暂存
M  app.cpp       修改已经暂存
MM config.yml    暂存后又继续修改
?? notes.txt     未跟踪文件
A  new.cpp       新文件已经暂存
D  old.cpp       删除已经暂存
UU conflict.cpp  存在未解决冲突
```

列出已跟踪和未跟踪文件：

```text
git ls-files
git ls-files --others --exclude-standard
git ls-files --deleted
git ls-files --modified
```

## 5. 比较文件与提交

### 工作区和暂存区

```text
git diff
git diff -- <file>
```

这些命令显示工作区中尚未进入暂存区的修改。

### 暂存区和当前提交

```text
git diff --cached
git diff --staged
git diff --cached -- <file>
```

`--cached` 与 `--staged` 含义相同，适合在提交前复查即将提交的内容。

### 工作区和当前提交

```text
git diff HEAD
git diff HEAD -- <file>
```

它会同时显示已经暂存和尚未暂存的变化。

### 比较提交或分支

```text
git diff <commit1> <commit2>
git diff <branch1>..<branch2>
git diff <branch1>...<branch2>
```

对于 `git diff A...B`，Git 会从 `A` 与 `B` 的合并基点比较到 `B`，常用于查看功能分支相对主分支引入的变化。双点在 `git diff` 中通常等价于直接写两个端点，不要把它与 `git log A..B` 的提交集合语义混淆。

### 控制输出范围

```text
git diff --stat
git diff --name-only
git diff --name-status
git diff --word-diff
git diff --check
```

`git diff --check` 会检查空白错误，适合在提交或发布前运行。

## 6. 暂存、移动与删除文件

### 暂存修改

```text
git add <file>
git add <directory>
git add -A
git add -u
git add -p
```

区别如下：

| 命令 | 新文件 | 已修改文件 | 已删除文件 |
| --- | --- | --- | --- |
| `git add <path>` | 路径范围内 | 路径范围内 | 路径范围内 |
| `git add -A` | 是 | 是 | 是 |
| `git add -u` | 否 | 是 | 是 |
| `git add -p` | 默认否 | 交互选择 | 交互选择 |

`git add -p` 可以按修改块选择要暂存的内容，是拆分提交时非常实用的命令。未跟踪的新文件默认不会出现在补丁选择中；可以先用 `git add -N <file>` 建立“意向添加”记录，再进行分块暂存。

### 取消暂存

```text
git restore --staged <file>
git restore --staged .
```

这些命令只调整暂存区，不会丢弃工作区中的修改。

### 移动和删除已跟踪文件

```text
git mv <old> <new>
git rm <file>
git rm --cached <file>
```

`git rm --cached` 会停止跟踪文件，但保留工作区副本。它常用于处理已经纳入版本控制、后来才加入 `.gitignore` 的本地配置；执行后仍需提交这次索引变化。

## 7. 创建、检查与修改提交

### 创建提交

```text
git commit
git commit -m "message"
git commit -v
git commit -am "message"
```

`-a` 只自动暂存已跟踪文件的修改和删除，不包括新文件。

### 修改最近一次提交

```text
git commit --amend
git commit --amend --no-edit
```

`--amend` 会创建一个新提交来替换当前提交，因此提交哈希也会改变。对已经共享的提交使用时必须谨慎。

### 为交互式变基准备修正提交

```text
git commit --fixup=<commit>
git commit --squash=<commit>
git rebase -i --autosquash <base>
```

`fixup` 和 `squash` 可以把后续修正标记为属于某个已有提交，再通过交互式变基统一整理。

### 查看单个提交

```text
git show
git show <commit>
git show --stat <commit>
git show --name-status <commit>
git show <commit>:<path>
```

最后一条命令会直接显示某次提交中的文件内容，不会切换分支，也不会修改工作区。

## 8. 浏览和搜索提交历史

### 常用日志视图

```text
git log
git log --oneline
git log --graph --oneline --decorate --all
git log --stat
git log -p
git log -n 10
```

### 按范围查看

```text
git log <branch1>..<branch2>
git log <branch1>...<branch2>
git log --left-right <branch1>...<branch2>
```

`A..B` 表示可以从 `B` 到达、但不能从 `A` 到达的提交；`A...B` 表示两边各自独有的提交。

### 按条件过滤

```text
git log --author="name"
git log --since="2026-09-01"
git log --until="2026-09-30"
git log --grep="keyword"
git log -- <path>
git log --follow -- <file>
```

`--follow` 适合追踪单个文件跨越重命名的历史，但不适合用作通用的多文件重命名分析工具。

### 汇总贡献

```text
git shortlog -sn
git shortlog -sne --all
```

它统计的是提交数量，不能直接代表代码质量、实际工作量或贡献价值。

## 9. 分支操作

### 查看分支

```text
git branch
git branch -a
git branch -r
git branch -vv
git branch --merged
git branch --no-merged
```

`-vv` 会显示上游分支以及领先、落后信息。

### 创建与切换

```text
git switch <branch>
git switch -c <new-branch>
git switch -c <new-branch> <start-point>
git switch -
```

`git switch -` 快速返回上一次所在分支。

### 重命名和删除

```text
git branch -m <new-name>
git branch -m <old-name> <new-name>
git branch -d <branch>
git branch -D <branch>
```

`-d` 会拒绝删除尚未合并的分支；`-D` 则会强制删除分支引用。使用后者前，应确认重要提交仍可从其他引用到达，或至少能够通过 `reflog` 找回。

### Detached HEAD

```text
git switch --detach <commit>
```

这种方式适合临时查看旧版本。如果在 detached HEAD 状态下创建了需要保留的提交，应在离开前为它建立分支：

```text
git switch -c recovery/my-work
```

## 10. 合并与冲突处理

### 合并分支

```text
git merge <branch>
git merge --no-ff <branch>
git merge --squash <branch>
```

- 默认合并可能直接快进，也可能创建合并提交；
- `--no-ff` 即使能够快进，也会保留一个合并提交；
- `--squash` 会把对方分支的整体差异放入工作区和暂存区，但不会建立真实的合并关系，之后还需要手工提交。

### 查看冲突

```text
git status
git diff --name-only --diff-filter=U
git diff
```

整理好最终内容、删除冲突标记并完成必要测试后：

```text
git add <resolved-file>
git commit
```

放弃本次合并：

```text
git merge --abort
```

### 选择冲突一侧的内容

```text
git restore --ours <file>
git restore --theirs <file>
git add <file>
```

这会为整份文件选择其中一侧的版本，不适合双方修改都需要保留的情况。尤其在变基过程中，`ours` 与 `theirs` 的视角可能和直觉相反；使用前应查看实际差异，不能只凭名称判断。

## 11. Rebase 与历史整理

### 把当前分支变基到新起点

```text
git rebase <upstream>
git rebase <upstream> <branch>
```

rebase 会复制并重新应用一组提交，因此提交哈希会发生变化。它适合整理尚未共享的功能分支，不应随意改写其他人已经在其上继续工作的公共历史。

### 冲突控制

```text
git rebase --continue
git rebase --skip
git rebase --abort
git rebase --quit
```

- `--continue`：解决冲突并暂存后继续；
- `--skip`：跳过当前补丁，可能丢失该提交的变化；
- `--abort`：返回变基开始前；
- `--quit`：停止变基，但不主动恢复开始前的 `HEAD` 和工作区。

### 交互式整理

```text
git rebase -i HEAD~5
git rebase -i --autosquash <base>
```

常见动作包括：

| 动作 | 作用 |
| --- | --- |
| `pick` | 保留提交 |
| `reword` | 修改提交信息 |
| `edit` | 暂停以修改提交 |
| `squash` | 合并提交并编辑说明 |
| `fixup` | 合并提交并通常丢弃当前说明 |
| `drop` | 删除提交 |

## 12. 远程仓库管理

### 查看远程信息

```text
git remote
git remote -v
git remote show <remote>
```

### 添加、修改和删除远程

```text
git remote add <remote> <url>
git remote set-url <remote> <url>
git remote rename <old> <new>
git remote remove <remote>
```

### 获取远程引用

```text
git fetch
git fetch <remote>
git fetch <remote> <branch>
git fetch --all --prune
```

`fetch` 只更新远程跟踪引用，不会自动把远程分支合并到当前分支。`--prune` 会清理远程已经删除的远程跟踪引用，但不会直接删除同名的本地分支。

### 拉取并整合

```text
git pull
git pull --ff-only
git pull --rebase
```

- `--ff-only` 只接受快进，一旦历史分叉就停止；
- `--rebase` 会在获取后把本地提交重放到远程分支之上；
- 不带参数的 `pull` 如何整合历史取决于 Git 配置，团队应提前统一约定。

如果想先查看远程变化再决定如何整合，可以把操作拆开：

```text
git fetch origin
git log --oneline HEAD..origin/main
git merge --ff-only origin/main
```

### 推送

```text
git push
git push -u origin <branch>
git push origin <local-branch>:<remote-branch>
git push origin --delete <branch>
```

如果确实需要更新一条自己负责、允许改写的远程分支，优先使用：

```text
git push --force-with-lease
```

当远程状态与本地预期不一致时，它会拒绝覆盖，因此比 `--force` 多一层保护。不过它仍属于高风险操作，不能替代团队确认。

## 13. 比较本地与远程状态

先更新远程引用：

```text
git fetch origin
```

然后查看当前分支关系：

```text
git status
git branch -vv
git log --oneline HEAD..origin/main
git log --oneline origin/main..HEAD
git diff HEAD...origin/main
git rev-list --left-right --count HEAD...origin/main
```

含义如下：

- `HEAD..origin/main`：远程有、本地当前分支没有的提交；
- `origin/main..HEAD`：本地有、远程没有的提交；
- `rev-list --left-right --count`：分别统计左右两侧独有提交数。

检查远程是否可访问以及有哪些引用：

```text
git ls-remote origin
git ls-remote --heads origin
git ls-remote --tags origin
```

## 14. 撤销、重置与恢复

Git 中，`restore`、`reset` 和 `revert` 最容易被混淆。可以先从影响对象来区分：

- `restore` 主要恢复工作区或暂存区中的文件；
- `reset` 移动分支指针，并可同时重置暂存区、工作区；
- `revert` 创建一个新的反向提交，不删除已有历史。

### 恢复工作区文件

```text
git restore <file>
git restore -p <file>
git restore --source=<commit> -- <file>
```

默认情况下，`git restore <file>` 会用暂存区内容覆盖工作区，因此未暂存修改将会丢失。`-p` 可以让你交互式选择要恢复的修改块。

### 取消暂存

```text
git restore --staged <file>
git restore --staged .
```

默认会从 `HEAD` 恢复暂存区，工作区中的修改仍然保留。

### 用新提交撤销旧提交

```text
git revert <commit>
git revert <oldest>^..<newest>
git revert --no-commit <commit>
```

撤销合并提交时必须指定保留哪条父线：

```text
git revert -m 1 <merge-commit>
```

`-m 1` 的含义取决于该合并提交的父提交顺序，执行前应先用 `git show --summary <merge-commit>` 核对。

### Reset 三种模式

```text
git reset --soft <commit>
git reset --mixed <commit>
git reset --hard <commit>
```

| 模式 | 移动分支 | 重置暂存区 | 覆盖已跟踪文件的工作区 |
| --- | --- | --- | --- |
| `--soft` | 是 | 否 | 否 |
| `--mixed` | 是 | 是 | 否 |
| `--hard` | 是 | 是 | 是 |

`--mixed` 是默认模式。`--hard` 会丢弃已跟踪文件中的本地修改；执行前至少要核对 `git status`、目标提交，以及是否存在可靠的恢复入口。

### 使用 reflog 找回位置

```text
git reflog
git reflog show <branch>
git show HEAD@{2}
git branch recovery/<name> <commit>
```

更稳妥的恢复方式，是先通过 `reflog` 找到目标提交，再创建新分支保护它，而不是立刻进行下一次重置。reflog 通常只存在于本地，其中的记录也会按配置过期。

## 15. 临时保存未完成工作

### 创建 stash

```text
git stash push -m "work in progress"
git stash push -u -m "include untracked files"
git stash push -p
git stash push -- <path>
```

默认情况下，stash 会保存已跟踪文件在工作区和暂存区中的状态；`-u` 还会包含未跟踪文件。若要连被忽略文件一起保存，需要使用 `-a`，此时更应谨慎核对范围。

### 查看和恢复

```text
git stash list
git stash show
git stash show -p stash@{0}
git stash apply stash@{0}
git stash pop
git stash branch <branch> stash@{0}
```

`apply` 会保留 stash 条目；`pop` 则会在成功应用后尝试删除它。发生冲突时，不要假设条目已经消失，应重新查看 `git stash list`。

### 删除 stash

```text
git stash drop stash@{0}
git stash clear
```

`clear` 会删除全部 stash 引用，恢复难度很高，属于高风险操作。

## 16. 移动提交与交换补丁

### Cherry-pick

```text
git cherry-pick <commit>
git cherry-pick <commit1> <commit2>
git cherry-pick --no-commit <commit>
git cherry-pick --continue
git cherry-pick --abort
```

它会把指定提交引入的变化应用到当前分支，并创建一个新提交。新提交通常拥有不同的哈希，也不表示两个分支之间建立了合并关系。

### 生成和应用邮件补丁

```text
git format-patch -1 <commit>
git format-patch <base>..<branch>
git am <patch-file>
git am --continue
git am --abort
```

只需要应用普通差异、不保留原提交元数据时，可以使用：

```text
git diff <base>..<branch> > changes.patch
git apply --check changes.patch
git apply changes.patch
```

`git apply --check` 只验证补丁能否应用，不会修改文件。

## 17. 标签与版本发布

### 查看和创建标签

```text
git tag
git tag --list "v1.*"
git tag <name>
git tag -a <name> -m "release message"
git tag -a <name> <commit> -m "release message"
git show <tag>
```

轻量标签只是一个引用；附注标签还包含创建者、时间和说明等对象信息，通常更适合正式发布。

### 推送和删除标签

```text
git push origin <tag>
git push origin --tags
git push --follow-tags
git tag -d <tag>
git push origin --delete <tag>
```

普通的 `git push` 默认不会自动推送所有本地标签。删除或移动已经发布的标签可能影响构建流程和使用者，因此应先经过团队确认。

### 从标签描述版本

```text
git describe --tags
git describe --tags --always --dirty
```

它常用于生成开发版本号或构建标识。

## 18. 查找修改来源与定位回归

### Blame

```text
git blame <file>
git blame -L 20,40 <file>
git blame -w <file>
```

`blame` 会显示每一行最后由哪个提交修改。它适合用来寻找上下文和相关提交，不应被简单地当作评价个人的工具。

### 搜索内容

```text
git grep "keyword"
git grep -n "keyword"
git grep "keyword" <commit>
```

### 搜索历史中的变化

```text
git log -S"exact text" --oneline
git log -G"regular expression" --oneline
git log -p -S"function_name" -- <path>
```

- `-S` 查找某个字符串出现次数发生变化的提交；
- `-G` 查找补丁文本匹配正则表达式的提交。

### 使用 bisect 二分定位

```text
git bisect start
git bisect bad
git bisect good <known-good-commit>
```

Git 会切换到中间提交。测试后重复标记：

```text
git bisect good
git bisect bad
```

结束并回到原分支：

```text
git bisect reset
```

如果测试可以通过脚本返回成功或失败状态，还可以自动执行：

```text
git bisect run <test-command>
```

## 19. 使用 worktree 并行处理分支

一个仓库可以关联多个工作区，从而同时检出并处理不同分支：

```text
git worktree list
git worktree add ../project-hotfix -b hotfix/login main
git worktree add ../project-review <existing-branch>
```

处理完成后：

```text
git worktree remove ../project-hotfix
git worktree prune --dry-run
git worktree prune
```

`worktree` 很适合“正在重构，却要立即处理线上修复”这类场景。各工作区共享对象数据库和多数引用，但分别拥有独立的 `HEAD`、暂存区与工作目录。同一个普通分支通常不能同时在两个工作区中检出。

需要移除工作区时，应优先使用 `git worktree remove`，避免直接删除目录后遗留管理记录。

## 20. 忽略规则与跟踪状态

Git 的忽略来源包括：

- 仓库中的 `.gitignore`，适合团队共享；
- `.git/info/exclude`，只作用于当前本地仓库；
- `core.excludesFile` 指定的全局忽略文件。

检查某个文件为什么被忽略：

```text
git check-ignore -v <file>
git check-ignore -v --no-index <file>
```

列出被忽略文件：

```text
git status --ignored
git ls-files --others --ignored --exclude-standard
```

停止跟踪已经提交的本地文件：

```text
git rm --cached <file>
git commit -m "chore: stop tracking local configuration"
```

注意：从当前版本停止跟踪，并不会清除文件在旧提交中的内容。如果密钥已经进入历史，应立即吊销或轮换，再按照团队流程清理历史。

## 21. 子模块、稀疏检出与大型文件

### Submodule

添加子模块：

```text
git submodule add <url> <path>
git submodule status
```

克隆包含子模块的仓库：

```text
git clone --recurse-submodules <url>
git submodule update --init --recursive
```

更新子模块记录：

```text
git submodule update --remote --merge
git status
```

父仓库记录的是子模块仓库中的某个特定提交，并不会自动跟随其最新分支。提交父仓库前，应确认这个目标提交已经推送到协作者可访问的远程。

### Sparse checkout

只检出大型单仓库中的部分目录：

```text
git sparse-checkout init --cone
git sparse-checkout set src docs
git sparse-checkout add tests
git sparse-checkout list
git sparse-checkout disable
```

结合部分克隆：

```text
git clone --filter=blob:none --sparse <url>
```

### Git LFS

Git LFS 是一项独立扩展，适合管理需要纳入版本控制的大型二进制文件。常用入口如下：

```text
git lfs install
git lfs track "*.psd"
git lfs ls-files
```

`.gitattributes` 需要随仓库一同提交。启用 LFS 前，应确认托管平台的额度，以及所有协作者的环境都已准备就绪。

## 22. 仓库清理、维护与打包

### 预览和删除未跟踪文件

```text
git clean -n
git clean -nd
git clean -ni
git clean -fd
```

- `-n`：只预览；
- `-d`：包含未跟踪目录；
- `-i`：交互式选择；
- `-f`：真正删除。

`git clean -fd` 删除的未跟踪文件无法通过普通撤销找回，因此必须先用 `-n` 或 `-i` 核对范围。`git clean -fdx` 还会删除被忽略的文件，风险更高。

### 检查和维护对象数据库

```text
git count-objects -vH
git fsck
git gc
```

Git 通常会自动维护仓库，不必频繁手工执行 `gc`。`fsck` 用于检查对象的连接性和有效性，也可能报告悬空对象；后者并不一定意味着仓库已经损坏。

### 导出源码快照

```text
git archive --format=zip --output=source.zip HEAD
git archive --format=tar.gz --output=source.tar.gz <tag>
```

`archive` 只导出指定提交中的已跟踪文件，不包含 `.git` 历史，也不包含未提交修改。

### 创建可传输的 Git bundle

```text
git bundle create project.bundle --all
git bundle verify project.bundle
git clone project.bundle project-copy
```

bundle 适合离线传输仓库对象和引用，但不能作为工作区未提交内容的备份。

## 23. 认证和远程故障排查

远程操作失败时，建议按照“地址—网络—认证—授权—分支状态”的顺序逐层检查，而不是反复执行 `push`。

### 检查远程地址

```text
git remote -v
git remote get-url origin
git ls-remote origin
```

### 检查 SSH 身份

```text
ssh -T git@github.com
ssh -vT git@github.com
```

SSH 测试成功，只能证明平台识别了当前密钥。要访问私有仓库，还必须确保远程 URL 正确、仓库确实存在，并且该账号已经获得权限。

### 常见错误

#### `fatal: not a git repository`

这表示当前路径不在 Git 仓库内。可以检查：

```text
pwd
git rev-parse --show-toplevel
```

在没有确认目录用途之前，不要直接执行 `git init`。

#### `Author identity unknown`

配置提交身份：

```text
git config --global user.name "Your Name"
git config --global user.email "you@example.com"
```

#### `remote origin already exists`

先检查现有地址，再决定修改还是重命名：

```text
git remote -v
git remote set-url origin <url>
```

#### `Repository not found`

常见原因包括 URL 拼写错误、仓库已经改名、账号无权访问私有仓库，或协作者邀请尚未接受。即使 SSH 认证成功，也不能排除这些问题。

#### `non-fast-forward`

这表示远程分支包含本地尚未拥有的提交。先获取并检查：

```text
git fetch origin
git log --graph --oneline --decorate HEAD...origin/<branch>
```

确认差异后，再根据团队约定选择 merge 或 rebase，不要直接强制推送。

#### `refusing to merge unrelated histories`

这表示两个分支没有共同祖先，常见于本地与远程分别独立初始化的情况。先确认是否选错了仓库或分支；只有确实需要合并两段独立历史时，才考虑使用 `--allow-unrelated-histories`。

#### `detected dubious ownership`

Git 检测到仓库目录的所有者与当前用户不一致。应先检查路径、用户和目录权限，不要只为消除提示，就把范围宽泛的目录加入 `safe.directory`。

## 24. 高频工作流模板

### 开始一个新功能

```text
git switch main
git fetch origin
git merge --ff-only origin/main
git switch -c feature/<name>
```

### 提交当前功能

```text
git status
git diff
git add -p
git diff --cached
git commit -m "feat: describe the change"
```

### 推送并建立上游

```text
git push -u origin feature/<name>
```

### 更新功能分支

使用合并：

```text
git fetch origin
git merge origin/main
```

或在团队允许整理个人功能分支时使用变基：

```text
git fetch origin
git rebase origin/main
```

### 把做在错误分支上的未提交修改移到新分支

如果修改与目标分支兼容，可以直接创建新分支：

```text
git switch -c feature/correct-branch
```

当前工作区中的修改会被保留，之后可以正常检查并提交。

### 把最近提交移动到新分支

仅限尚未共享的本地提交：

```text
git branch feature/correct-branch
git reset --hard HEAD~1
git switch feature/correct-branch
```

其中，`reset --hard` 会覆盖工作区。执行前应确保状态干净，并通过 `git log` 核对需要移动的提交数量；更稳妥的做法，是先创建备份分支，再移动当前分支。

### 撤销已经进入共享分支的提交

```text
git switch main
git pull --ff-only
git revert <commit>
git push
```

### 找回误删分支

```text
git reflog
git show <candidate-commit>
git branch recovery/<name> <candidate-commit>
```

### 紧急修复但不打断当前工作

```text
git worktree add ../project-hotfix -b hotfix/<name> main
```

在新目录完成修复后，再移除工作区：

```text
git worktree remove ../project-hotfix
```

## 25. 一页速查表

| 场景 | 命令 |
| --- | --- |
| 查看状态 | `git status --short --branch` |
| 查看未暂存修改 | `git diff` |
| 查看已暂存修改 | `git diff --cached` |
| 分块暂存 | `git add -p` |
| 取消暂存 | `git restore --staged <file>` |
| 提交 | `git commit -m "message"` |
| 查看图形历史 | `git log --graph --oneline --decorate --all` |
| 创建并切换分支 | `git switch -c <branch>` |
| 返回上个分支 | `git switch -` |
| 合并分支 | `git merge <branch>` |
| 放弃合并 | `git merge --abort` |
| 获取远程变化 | `git fetch --prune` |
| 只允许快进拉取 | `git pull --ff-only` |
| 首次推送分支 | `git push -u origin <branch>` |
| 撤销共享提交 | `git revert <commit>` |
| 查找本地位置变化 | `git reflog` |
| 临时保存修改 | `git stash push -u -m "message"` |
| 应用指定提交 | `git cherry-pick <commit>` |
| 定位引入问题的提交 | `git bisect start` |
| 检查忽略来源 | `git check-ignore -v <file>` |
| 预览未跟踪文件清理 | `git clean -nd` |
| 检查仓库根目录 | `git rev-parse --show-toplevel` |
| 比较本地与远程提交数 | `git rev-list --left-right --count HEAD...origin/main` |

## 26. 操作前后的检查清单

执行可能改变仓库状态的命令前，先回答：

- [ ] 当前仓库根目录是什么？
- [ ] 当前分支是什么？
- [ ] 工作区和暂存区是否有未提交修改？
- [ ] 命令会影响文件、暂存区、分支指针还是远程历史？
- [ ] 目标提交、分支和远程名称是否已经核对？
- [ ] 其他人是否可能正在依赖这段历史？
- [ ] 如果结果不符合预期，恢复入口是什么？

操作完成后再检查：

```text
git status
git diff
git diff --cached
git log --graph --oneline --decorate -n 15
```

命令手册的价值，不在于鼓励一次使用更多命令，而在于帮助你看清每次操作的输入、影响范围和验证方法。尤其涉及 `reset --hard`、`clean -fd`、交互式 rebase 或强制推送时，先保护现有提交与未提交修改，再处理历史，通常比事后补救更可靠。

## 27. 官方参考资料

- [Git 命令参考](https://git-scm.com/docs)
- [Git 官方速查表](https://git-scm.com/cheat-sheet.pdf)
- [Pro Git：Git 基础](https://git-scm.com/book/zh/v2/Git-基础-获取-Git-仓库)
- [git restore](https://git-scm.com/docs/git-restore)
- [git rebase](https://git-scm.com/docs/git-rebase)
- [git reflog](https://git-scm.com/docs/git-reflog)
- [git worktree](https://git-scm.com/docs/git-worktree)
- [git bisect](https://git-scm.com/docs/git-bisect)
