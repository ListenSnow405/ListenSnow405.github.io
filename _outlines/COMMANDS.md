# 终端常用命令指南（通用速查 + 排错手册）

> **用途**：日常开发与排错的速查页，不绑定任何具体项目。按「遇到什么事」组织，而不是按命令字母表。
> 遇到问题先翻 [§14 排错速查表](#14-排错速查表)，它会指回相应章节。
> 新项目开工时，按 [附录 A](#附录-a新项目开工清单) 把项目自己的路径、脚本、判据填一遍，放进该项目的 README / CLAUDE.md，本页保持通用。

## 目录

0. [读法与约定](#0-读法与约定)
1. [Shell 基础：救命键与必知语法](#1-shell-基础救命键与必知语法)
2. [文件与目录](#2-文件与目录)
3. [文本处理与日志分析](#3-文本处理与日志分析)
4. [二进制、编码与换行符](#4-二进制编码与换行符)
5. [进程、后台与长任务](#5-进程后台与长任务)
6. [系统资源与环境信息](#6-系统资源与环境信息)
7. [远程登录与文件同步](#7-远程登录与文件同步)
8. [Git](#8-git)
9. [构建、链接与调试（C/C++）](#9-构建链接与调试cc)
10. [GPU / CUDA](#10-gpu--cuda)
11. [性能测量方法论（附命令模板）](#11-性能测量方法论附命令模板)
12. [Python 环境](#12-python-环境)
13. [Windows 本地](#13-windows-本地)
14. [排错速查表](#14-排错速查表)
- [附录 A：新项目开工清单](#附录-a新项目开工清单)
- [附录 B：复制即用模板](#附录-b复制即用模板)

---

## 0. 读法与约定

| 记号 | 含义 |
|---|---|
| `<name>` | 占位符，替换成实际值 |
| `[opt]` | 可选部分 |
| 🐧 / 🪟 | 仅 Linux bash / 仅 Windows PowerShell；不标即两边通用（或 Git Bash 可用） |
| ⚠ | 踩过的坑，出事时重点看 |

**上机器之前先判断「这一跑要不要独占资源」**（共享服务器上尤其重要）：

| 档 | 什么时候 | 要求 |
|---|---|---|
| 🔴 严格独占 | 任何**带时间量纲**、要用来做 A/B 或判定优化收益的跑 | 开跑前确认无他人占用，跑后再确认一次；中途被占的数据作废 |
| 🟡 可共享，但要标注 | 只看**计数类**指标（次数、占比、迭代数）或只验正确性 | 可以跑，但时间字段别信 |
| ⚪ 无所谓 | 编译、看日志、列文件等不占计算资源的操作 | —— |

经验：共享机器上的计时噪声常常比待测效应还大（实测 A/A 配对差中位数可到 30%+），而且**越短的阶段被污染得越厉害**；计数类指标基本不受影响。详见 §11。

---

## 1. Shell 基础：救命键与必知语法

### 1.1 快捷键

| 键 | 作用 |
|---|---|
| `Ctrl-C` | 中断前台进程 |
| `Ctrl-Z` → `bg` / `fg` | 挂起前台进程 → 放到后台继续 / 拉回前台 |
| `Ctrl-D` | 输入结束（空行上按 = 退出 shell） |
| `Ctrl-R` | 反向搜索历史命令（再按一次找更早的） |
| `Ctrl-A` / `Ctrl-E` | 光标到行首 / 行尾 |
| `Ctrl-U` / `Ctrl-K` / `Ctrl-W` | 删到行首 / 删到行尾 / 删前一个词 |
| `Ctrl-L` | 清屏 |
| `Ctrl-S` / `Ctrl-Q` | ⚠ 冻结 / 解冻终端输出。终端「卡住不动」先按 `Ctrl-Q` 试试 |

### 1.2 历史

```bash
!!                      # 上一条命令（sudo !! 以 root 重跑）
!$                      # 上一条命令的最后一个参数
history | grep <kw>     # 搜历史
!<n>                    # 执行第 n 条历史
```

### 1.3 引号与变量

```bash
'...'                   # 原样，不展开任何东西
"..."                   # 展开 $VAR、$(cmd)，但不做分词和通配
$'...\t...\r'           # 支持转义字符（grep $'\r' 找 CRLF 时用）
"$var"                  # ⚠ 变量永远加双引号，否则含空格/为空时行为诡异
${VAR:-default}         # 未设置或为空时用默认值
${VAR:?msg}             # 未设置时报错退出
```

### 1.4 环境变量

```bash
VAR=x cmd               # 只对这一条命令生效
export VAR=x            # 对当前 shell 及其子进程生效
env | grep <VAR>        # 查看
unset VAR
```

⚠ `VAR=x cmd1 && cmd2`：`VAR` **只作用于 cmd1**。
⚠ `nohup VAR=x cmd` 不对：要写成 `VAR=x nohup cmd`，或者 `nohup bash -c 'VAR=x cmd'`（变量写在引号内）。

### 1.5 退出码、管道与重定向

```bash
echo $?                         # 上一条命令的退出码（0 = 成功）
echo "${PIPESTATUS[@]}"         # 管道里每一段的退出码
set -euo pipefail               # 脚本开头：出错即停 / 未定义变量报错 / 管道任一段失败即失败
cmd1 && cmd2 || cmd3            # cmd1 成功才跑 cmd2；前面失败才跑 cmd3

cmd > out.log 2>&1              # stdout + stderr 都进文件（顺序不能反）
cmd &> out.log                  # bash 简写，同上
cmd 2>/dev/null                 # 丢掉错误输出
cmd | tee out.log               # 屏幕和文件各一份（-a 追加）
cmd 2>&1 | tee out.log          # 连 stderr 一起
```

### 1.6 命令从哪来

```bash
type -a <cmd>           # 所有同名候选（alias / function / 各个 PATH 位置）
command -v <cmd>        # 脚本里判断命令是否存在
echo "$PATH" | tr ':' '\n'
hash -r                 # 换了 PATH 后清掉 bash 的命令缓存
```

### 1.7 调试脚本

```bash
bash -n script.sh       # 只检查语法，不执行
bash -x script.sh       # 逐行打印展开后的命令（排「脚本瞬间结束」「变量为空」必用）
shellcheck script.sh    # 静态检查：没加引号、未定义变量等（apt install shellcheck）
```

---

## 2. 文件与目录

```bash
ls -lah                              # 含隐藏文件，人类可读大小
ls -lt | head                        # 最近修改的文件在前
tree -L 2                            # 两层目录树
realpath <f>                         # 绝对路径
stat <f>                             # 大小、修改时间、inode
file <f>                             # 文件类型；文本文件会顺带报出 CRLF / BOM / 编码

find . -name '*.log' -mtime -1       # 1 天内改过的 log
find . -type f -size +1G             # 大于 1G 的文件
find src -newer build/app            # ⚠ 比二进制新的源文件（判断「是否需要重编」）
find . -name '*.tmp' -print          # 删之前先 -print 看一眼……
find . -name '*.tmp' -delete         # ……确认无误再删

du -sh * | sort -h                   # 当前目录下各项的大小，从小到大
df -h .                              # 当前所在磁盘的剩余空间
df -i .                              # ⚠ inode 耗尽也会报 No space left
cp -a <src> <dst>                    # 保留权限和时间戳
ln -s <target> <link>                # 软链接
mktemp -d                            # 临时目录
```

**覆盖或删除之前**：先 `ls` / `head` 看一眼目标，重要文件先 `cp <f> <f>.bak`。
⚠ `rm -rf "$DIR/"` 在 `$DIR` 为空时就变成 `rm -rf /`。脚本里加上 `set -u`，或者写成 `"${DIR:?}"`。

---

## 3. 文本处理与日志分析

### 3.1 grep / ripgrep

```bash
grep -n <pat> <f>                    # 带行号
grep -rn --include='*.cu' <pat> .    # 递归，只看某类文件
grep -E 'a|b' / grep -F '[literal]'  # 扩展正则 / 按字面匹配（含 [ ] . 等特殊字符时用 -F）
grep -o 'key=[0-9]*'                 # 只输出匹配到的部分
grep -v / -c / -l / -i               # 取反 / 计数 / 只列文件名 / 忽略大小写
grep -A3 -B2 <pat>                   # 匹配行的后 3 行、前 2 行
grep -H <pat> logs/*.log             # 行首带文件名（多文件时默认就带）
rg <pat>                             # ripgrep：更快，自动跳过 .gitignore 里的文件
```

### 3.2 awk（字段处理）

```bash
awk '{print $1, $3}'                         # 按空白分列
awk -F'\t' '{print $2}' f.tsv                # 按 TAB 分列
awk '{s+=$2} END{print s}'                   # 求和
awk '$3 > 100'                               # 过滤行
awk -F'\t' 'NR==1 || $5=="NO"' f.tsv         # 保留表头 + 满足条件的行
```

⚠ **gawk 和 mawk 不一样**：三参数的 `match($0, /re/, arr)`、`gensub`、`asort` 只有 gawk 有。
Ubuntu 默认装的是 mawk，报错 `syntax error at or near ,`。如果脚本把 stderr 吞了，现象就是**提取出来的字段全空，但程序本身正常跑完**。
检查：`awk --version | head -1`；修复：`sudo apt install gawk`。

### 3.3 sed

```bash
sed -n '100,150p' f                  # 打印第 100~150 行
sed 's/old/new/g' f                  # 替换后输出（不改原文件）
sed -i.bak 's/old/new/g' f           # 原地修改并留备份
sed -i 's/\r$//' f                   # 去掉 CRLF 里的 \r
```

⚠ macOS / BSD 的 `sed -i` 必须带扩展名参数（`sed -i '' ...`），跨平台脚本里尽量避免 `-i`。

### 3.4 排序、统计、对齐

```bash
sort | uniq -c | sort -rn            # 频次统计，从高到低（最常用的组合）
sort -t$'\t' -k3,3n                  # 按第 3 列数值排序
cut -d= -f2                          # 按 = 切开取第 2 段
column -t -s$'\t' f.tsv              # TSV 对齐显示
paste a.txt b.txt                    # 两个文件按行并排
wc -l                                # 行数
head -n 20 / tail -n 20              # 头 / 尾
tail -f run.log                      # 跟踪写入中的日志
tail -F run.log                      # 文件被重建（轮转）后也继续跟踪
less +F run.log                      # 跟踪模式；Ctrl-C 停下来翻页，F 继续跟踪
```

### 3.5 比较

```bash
diff -u a b                          # 统一格式的差异
diff <(sort a) <(sort b)             # 对两条命令的输出做 diff
cmp a b                              # 逐字节比较（二进制、结果文件判等）
cmp -l a b | head                    # 列出前几个不同字节的位置
comm -3 <(sort a) <(sort b)          # 只在 a 有 / 只在 b 有的行
sha256sum a b                        # 大文件判等
```

### 3.6 日志提取模板

```bash
# 多个 log 里提取 key=value，行首带文件名，整理成表
grep -oH 'time_ms=[0-9.]*' logs/*.log | sed 's#^logs/##; s#\.log:time_ms=# #' | column -t

# 同一个指标，按两次运行并排比较（两边都先按键排序）
join <(grep -oE '^\S+ [0-9.]+' runA.txt | sort) <(grep -oE '^\S+ [0-9.]+' runB.txt | sort)

# 一个 log 里挑出关键行（把几类标记拼成一条 -E）
grep -E '^\[run\]|SUMMARY|verdict|_match=' run.log

# 取中位数
sort -n vals.txt | awk '{a[NR]=$1} END{print (NR%2)?a[(NR+1)/2]:(a[NR/2]+a[NR/2+1])/2}'
```

### 3.7 JSON

```bash
jq '.' f.json                        # 格式化
jq -r '.items[] | [.name, .time] | @tsv' f.json
```

---

## 4. 二进制、编码与换行符

### 4.1 看二进制

```bash
xxd f | head                         # 十六进制 + ASCII
head -c 64 f | xxd                   # 只看前 64 字节
od -An -tu4 -N12 f                   # 前 12 字节按 3 个 uint32 显示（读自定义文件头）
od -An -tf8 -N16 f                   # 按 double 显示
```

### 4.2 编码

```bash
file -i f                            # 猜测编码
head -c3 f | xxd                     # 开头是 efbb bf 就是带 BOM 的 UTF-8
iconv -f GBK -t UTF-8 in > out       # 转码
```

### 4.3 换行符（CRLF / LF）

⚠ Windows 上写的 `.sh` 拿到 Linux 执行，报 **`$'\r': command not found`**，或者 `bad interpreter: /bin/bash^M`。

```bash
grep -c $'\r' script.sh              # > 0 说明有 CRLF
dos2unix script.sh                   # 修复（或 sed -i 's/\r$//' script.sh）
git ls-files --eol                   # 看 git 眼中每个文件的换行符（i/ 是仓库里的，w/ 是工作区的）
```

根治办法：仓库里放一份 `.gitattributes`，**并且纳入版本管理**，否则 clone / archive 时不生效：

```
* text=auto
*.sh  text eol=lf
*.ps1 text eol=crlf
```

---

## 5. 进程、后台与长任务

### 5.1 作业控制

```bash
cmd &                    # 后台运行
echo $!                  # 刚放到后台的进程 PID
jobs -l                  # 当前 shell 的后台作业
fg %1 / bg %1            # 拉回前台 / 后台继续
disown %1                # 让作业脱离当前 shell（之后退出 shell 也不会被杀）
wait                     # 等所有后台作业结束
```

### 5.2 断开 SSH 也不停：nohup / tmux

```bash
# nohup：最简单，适合「跑完拿日志」的场景
nohup bash -c 'VAR=1 ./run.sh <args>' > run.log 2>&1 &
echo $! > run.pid
tail -f run.log
```

tmux：适合要交互、要中途回来看的场景

| 操作 | 命令 |
|---|---|
| 新建会话 | `tmux new -s <name>` |
| 暂离（会话继续跑） | `Ctrl-b d` |
| 列出 / 重新接入 | `tmux ls` / `tmux a -t <name>` |
| 往上翻屏 | `Ctrl-b [`，方向键 / PgUp 翻，`q` 退出 |
| 分屏 | `Ctrl-b %`（左右）、`Ctrl-b "`（上下），`Ctrl-b 方向键` 切换 |
| 结束会话 | `tmux kill-session -t <name>` |

### 5.3 查看与结束进程

```bash
pgrep -af <kw>                       # 按命令行查进程（比 ps aux | grep 干净）
ps -o pid,etime,%cpu,%mem,cmd -p <pid>   # 某个进程跑了多久、占多少
top / htop                           # 交互式查看（htop 里 F4 过滤、F5 树状）
top -H -p <pid>                      # 看某个进程里各个线程
kill <pid>                           # 先礼（SIGTERM）
kill -9 <pid>                        # 后兵（SIGKILL，程序来不及清理）
pkill -f <pattern>                   # ⚠ 按模式杀，先用 pgrep -af 确认会匹配到谁
lsof -p <pid>                        # 进程打开了哪些文件
```

### 5.4 计时、限时、等待

```bash
time cmd                             # real / user / sys
/usr/bin/time -v cmd                 # 还给出峰值内存 Maximum resident set size
timeout 3h cmd                       # 超时自动杀（退出码 124）
date '+%F %T'                        # 日志里打时间戳

# 等某个进程结束后再跑下一个
while kill -0 <pid> 2>/dev/null; do sleep 60; done; ./next.sh
# 等某个文件出现
until [ -f done.flag ]; do sleep 30; done
```

### 5.5 CPU 亲和与优先级

```bash
nice -n 10 cmd                       # 降低优先级
taskset -c 0-15 cmd                  # 绑定到 0~15 号核
numactl --hardware                   # NUMA 拓扑
numactl --cpunodebind=0 --membind=0 cmd   # 绑到一个 NUMA 节点（多路 CPU 测性能时用）
```

---

## 6. 系统资源与环境信息

```bash
uname -a; cat /etc/os-release        # 内核与发行版
nproc; lscpu                         # 核数、CPU 型号、NUMA、缓存
free -h                              # 内存（看 available 列，不是 free 列）
uptime                               # 负载（与核数比较）
w / who                              # ⚠ 共享机器上现在还有谁登录着
vmstat 1                             # 每秒一次：CPU / 内存 / swap / IO
iostat -x 1                          # 磁盘繁忙度（sysstat 包）
ulimit -a                            # 进程资源上限（栈、core、打开文件数）
dmesg -T | tail                      # 内核消息（OOM、硬件错误），可能要 sudo
journalctl -k --since '1 hour ago'   # 同上，systemd 系统

dpkg -l | grep <pkg>                 # 某个包装了没有 / 什么版本
ldconfig -p | grep <lib>             # 系统能找到哪些共享库
```

⚠ **page cache**：同一个大文件第二次读会快很多（数据已在内存里）。比较「读文件」耗时时，要固定冷热状态（都是第一次读，或都预热过）。

---

## 7. 远程登录与文件同步

### 7.1 SSH

```bash
ssh-keygen -t ed25519                # 生成密钥
ssh-copy-id <user>@<host>            # 以后免密登录
ssh -L 8888:localhost:8888 <host>    # 把远端 8888 端口映射到本地（Jupyter / TensorBoard）
ssh -J <jump> <host>                 # 经跳板机登录
```

`~/.ssh/config`（Windows：`C:\Users\<you>\.ssh\config`）：

```
Host gpu
    HostName <ip-or-domain>
    User <user>
    ServerAliveInterval 60      # 防止空闲时被断开
    ServerAliveCountMax 5
```

之后 `ssh gpu`、`scp f gpu:~/`、VS Code Remote-SSH 都能直接用这个别名。

### 7.2 传文件

```bash
scp <f> <host>:<dir>/
rsync -avzP --dry-run <src>/ <host>:<dst>/   # 先 dry-run 看会传哪些
rsync -avzP <src>/ <host>:<dst>/             # ⚠ src 末尾有无 / 语义不同：有 / 表示传目录里的内容
```

### 7.3 用 git 同步代码（推荐）

本地 `push` → 服务器 `git pull`。好处：版本可追溯，服务器上的代码永远是某个 commit。

- 服务器上只跟踪、不修改；要改就回本地改。否则 `pull` 会因为本地改动被拒。
- **哪些文件能上服务器完全由 `.gitignore` 决定**：新文件没同步过去，先查 §8.4。
- 拉完核对版本：两边各跑一次 `git log -1 --format='%h %s'`，看是否一致。

---

## 8. Git

### 8.1 只读查看（随时可跑）

```bash
git status [-s]
git diff                             # 工作区相对暂存区
git diff --cached                    # 暂存区相对 HEAD
git diff --stat <a>..<b>             # 两个版本之间改了哪些文件
git log --oneline --graph -n 20
git log -p -- <path>                 # 某个文件的修改历史
git log -S'<text>' --oneline         # 哪些提交增删过这段文本（找「这行是谁、何时加的」）
git blame -L 100,120 <path>
git show <rev>:<path>                # 某个历史版本的文件内容
git branch -vv; git remote -v
git reflog                           # HEAD 的移动记录（救命用）
```

### 8.2 日常

```bash
git add -p                           # 逐块挑选要暂存的改动
git commit -m '<msg>'
git pull --ff-only                   # 只允许快进，避免意外生成合并提交
git push
git stash [push -m '<msg>'] / git stash pop
git switch -c <branch>
```

### 8.3 救急

| 想做的事 | 命令 |
|---|---|
| 丢弃某个文件的未暂存修改 | `git restore <path>` |
| 取消暂存（改动保留） | `git restore --staged <path>` |
| 把文件恢复成某个历史版本 | `git restore --source=<rev> -- <path>` |
| 撤销最近一次提交，改动留在暂存区 | `git reset --soft HEAD~1`（只对未 push 的提交用） |
| 修改最近一次提交 | `git commit --amend`（只对未 push 的提交用） |
| 找回「丢了」的提交 | `git reflog` 找到 hash → `git switch -c rescue <hash>` |
| 找回已删文件 | `git log --diff-filter=D -- <path>` → `git restore --source=<hash>^ -- <path>` |
| 放弃合并 / 变基 | `git merge --abort` / `git rebase --abort` |
| 二分查找引入 bug 的提交 | `git bisect start; git bisect bad; git bisect good <rev>`；可以用 `git bisect run <test.sh>` 自动跑 |

⚠ `reset --hard`、`push --force`、`clean -fd` 都会丢数据：先 `git stash` 或建一个备份分支再做。

### 8.4 忽略与跟踪

```bash
git check-ignore -v <path>           # ⚠ 这个文件为什么被忽略了（给出命中的规则和行号）
git ls-files | grep <kw>             # 仓库实际跟踪了哪些文件
git ls-files --others --exclude-standard   # 未跟踪、也没被忽略的文件
git rm --cached <path>               # 停止跟踪（文件留在本地）
```

白名单写法（默认全部忽略，只放行需要的）：

```gitignore
/*
!/README*
!/src/
src/**
!src/**/
!src/**/*.cpp
```

⚠ `.gitignore` 里**最后一条命中的规则生效**：放行某个例外的规则要写在对应的全局忽略规则之后。

---

## 9. 构建、链接与调试（C/C++）

### 9.1 CMake

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release   # 配置
cmake --build build -j                           # 编译
cmake --build build -j --verbose                 # 显示实际的编译命令（查 flag 有没有生效）
cmake --build build --clean-first                # 全部重编
rm -rf build                                     # 最彻底：缓存有问题时用
cmake -LAH build | grep <VAR>                    # 查缓存变量的当前值
```

⚠ CMake 会缓存变量：命令行上的 `-DXXX=` 改了以后，**旧值可能还留在 `CMakeCache.txt` 里**。行为不对时先 `grep XXX build/CMakeCache.txt`。

### 9.2 确认跑的是新二进制

最常见的「改了没效果」：

```bash
find src -newer build/<app>          # 有输出 = 源码比二进制新，还没重编
ls -l --time-style=full-iso build/<app>
strings build/<app> | grep <新加的字符串>     # 新代码进了二进制没有
```

根治办法：编译时把 git 版本嵌进去，程序启动时打印出来：

```cmake
execute_process(COMMAND git rev-parse --short HEAD OUTPUT_VARIABLE GIT_HASH OUTPUT_STRIP_TRAILING_WHITESPACE)
add_compile_definitions(GIT_HASH="${GIT_HASH}")
```

还有：运行脚本如果有「跳过构建」开关（`-s` 之类），**改了源码之后就不能带它**。

### 9.3 编译器常用 flag

```bash
-O2 -g                               # 带符号的优化版（性能分析、gdb 都能用）
-Wall -Wextra                        # 多开警告
-fsanitize=address,undefined -g      # 越界 / 释放后使用 / 未定义行为（程序会慢 2~3 倍）
-fsanitize=thread -g                 # 数据竞争（不能和 address 同时开）
-E / -S                              # 只预处理 / 只生成汇编
-march=native                        # ⚠ 本机编出来的二进制换一台 CPU 可能 Illegal instruction
```

### 9.4 链接与动态库

```bash
ldd <app>                            # 依赖哪些 .so，各自从哪加载（not found = 找不到）
nm -C <obj> | grep <sym>             # 符号表（U = 未定义，T = 已定义）
readelf -d <app> | grep -E 'RPATH|RUNPATH|NEEDED'
export LD_LIBRARY_PATH=<dir>:$LD_LIBRARY_PATH
```

`undefined reference to X`：没链接到对应的库 / 库的顺序不对（被依赖的库放在后面）/ C 和 C++ 混用却没加 `extern "C"` / 模板或 inline 函数只有声明没有定义。

### 9.5 调试

```bash
gdb --args ./app <args>              # 进入后输入 run
#   bt                 崩溃后看调用栈
#   thread apply all bt 所有线程的栈（排查卡死）
#   frame <n> / p <var> / info locals
gdb -p <pid>                         # 附加到正在运行（卡住）的进程
ulimit -c unlimited                  # 允许生成 core；之后 gdb ./app core
valgrind --leak-check=full ./app     # 内存错误（非常慢，适合小输入）
```

偶发崩溃 / 偶发结果不同，基本就是**竞态或对象生命周期问题**：
- 同一输入循环跑 N 次，统计失败次数（`for i in $(seq 20); do ./app || echo FAIL $i; done`）
- 开 `-fsanitize=thread`
- 重点检查 lambda **按引用捕获**、却在别的线程里异步执行的变量——外层函数返回后它们就析构了

---

## 10. GPU / CUDA

### 10.1 状态与占用

```bash
nvidia-smi                           # 总览
nvidia-smi -L                        # 列出 GPU（顺便验证驱动正常）
nvidia-smi --query-gpu=index,name,utilization.gpu,memory.used,memory.total,clocks.sm,temperature.gpu,power.draw --format=csv -l 5
nvidia-smi --query-compute-apps=gpu_uuid,pid,used_memory,process_name --format=csv   # 谁在用卡
nvidia-smi pmon -c 5                 # 各进程的 SM / 显存利用率
nvidia-smi -q -d PERFORMANCE         # 降频原因（温度 / 功耗 / 空闲）
nvidia-smi topo -m                   # 多卡互联拓扑（NVLink / PCIe）
```

### 10.2 选卡

```bash
CUDA_VISIBLE_DEVICES=1 ./app         # 只让程序看到 1 号卡（程序内部它变成 device 0）
export CUDA_DEVICE_ORDER=PCI_BUS_ID  # 让 CUDA 的编号与 nvidia-smi 的编号一致
```

⚠ `nvidia-smi -i <n>` 用的是物理编号，程序内部用的是被 `CUDA_VISIBLE_DEVICES` 重排之后的编号，别混用。

### 10.3 干净卡检查（🔴 档计时前必做）

```bash
gpu=1
nvidia-smi -i $gpu --query-compute-apps=pid,used_memory --format=csv,noheader   # 应为空
for i in 1 2 3 4 5; do
  nvidia-smi -i $gpu --query-gpu=utilization.gpu,memory.used --format=csv,noheader,nounits
  sleep 2
done                                                                              # util 应一直接近 0

# 等到卡空出来再跑（配合 nohup 挂过夜）
until [ -z "$(nvidia-smi -i $gpu --query-compute-apps=pid --format=csv,noheader)" ]; do sleep 60; done
CUDA_VISIBLE_DEVICES=$gpu ./run.sh
```

⚠ 空闲的 GPU 处在低频，**干净卡上的第一跑会因为时钟爬升偏慢**：先跑一次热身再计时，或者丢弃第一轮。
⚠ 如果计时脚本自带「等待干净卡」开关，要确认它依赖的探针真的可用（先跑 `nvidia-smi -L`）。很多实现在探针不可用时只打一行提示，然后照常开跑。

### 10.4 版本与架构

```bash
nvcc --version                       # 工具链（编译器）版本
nvidia-smi                           # 右上角的 "CUDA Version" = 驱动最高支持的版本，不是装了哪个版本
which nvcc; ls /usr/local/ | grep cuda
```

| 报错 | 原因 |
|---|---|
| `no kernel image is available for execution on the device` | 编译时的 `-arch=sm_XX` 与卡不匹配（A100=80, H100=90, 4090=89, V100=70） |
| `CUDA driver version is insufficient for CUDA runtime version` | 驱动比工具链旧 |
| `out of memory` | 先查 §10.1 有没有别人占着显存，再查自己的峰值 |

### 10.5 编译期检查

```bash
nvcc -Xptxas -v ...                  # 每个 kernel 的寄存器数、spill、共享内存
nvcc --resource-usage ...            # 同上（较新的 nvcc）
cuobjdump -sass <app|obj> | less     # 看 SASS（比较改动前后的指令是否相同）
nvcc -lineinfo ...                   # 让 profiler 能对应到源码行（对性能无影响）
```

### 10.6 调试与性能分析

```bash
CUDA_LAUNCH_BLOCKING=1 ./app         # kernel 同步执行，报错位置变准（很慢）
compute-sanitizer --tool memcheck ./app      # 越界访问（还有 racecheck / initcheck / synccheck）
nsys profile -o prof --stats=true ./app      # 时间线：kernel、拷贝、CPU 之间谁在等谁
ncu --set full -k regex:<kernel> -c 1 -o k ./app   # 单个 kernel 的细粒度指标
```

⚠ `ncu` 报 `ERR_NVGPUCTRPERM`：非 root 用户没有读性能计数器的权限，需要管理员开放，或者用 sudo 运行。

---

## 11. 性能测量方法论（附命令模板）

**原则**

1. **先做 A/A**：同一版本跑两次，看噪声有多大。待测效应小于噪声就没法下结论。
2. **交错跑**：按 ABAB 或拉丁方的顺序跑，不要 AAAA BBBB，否则机器状态随时间漂移会被算成效应。
3. **至少 3 轮，报中位数**，并且丢弃第一轮热身。
4. **计数与计时分开**：计数类指标（次数、迭代数、扫描量）稳定、可以在共享机器上拿；计时只在独占时拿。
5. **诊断探针只用来归因，不用来做 A/B**：探针本身就会改变耗时。
6. **记录环境**：代码版本、驱动、机器负载，跟结果放在一起。
7. **口径写清楚**：计时含不含 I/O、含不含预处理，与对手比较时两边口径要一致。

**环境快照**

```bash
{ date '+%F %T'; hostname; git rev-parse --short HEAD; git status --porcelain | head -5
  nvidia-smi --query-gpu=name,driver_version --format=csv,noheader
  nvcc --version | tail -1; uptime; } > env_snapshot.txt
```

**交错 A/B 模板**

```bash
ORDERS=("A B" "B A" "A B" "B A")          # 每轮的顺序（拉丁方）
for r in "${!ORDERS[@]}"; do
  for arm in ${ORDERS[$r]}; do
    case $arm in
      A) envs="FEATURE=0" ;;
      B) envs="FEATURE=1" ;;
    esac
    env $envs ./run.sh <args> > "ab_${arm}_r${r}.log" 2>&1
  done
done
grep -H 'time_ms=' ab_*.log               # 汇总后按臂取中位数（§3.6）
```

---

## 12. Python 环境

```bash
which python; python --version       # ⚠ 当前用的到底是哪个 python
python -m venv .venv && source .venv/bin/activate   # 🪟 .venv\Scripts\Activate.ps1
python -m pip install <pkg>          # 用 python -m pip，保证装进当前解释器
python -c "import numpy; print(numpy.__version__, numpy.__file__)"
pip list | grep <pkg>
conda env list; conda activate <env>
```

⚠ 大数组处理先估算内存：N 个 int64 ≈ 8N 字节，排序时通常还要再加一份。10 亿元素的数组动辄几十 GB，放不下就改用分块或外存算法。

---

## 13. Windows 本地

### 13.1 PowerShell ↔ bash 对照 🪟

| bash | PowerShell |
|---|---|
| `ls -la` | `Get-ChildItem -Force`（`ls` 可用） |
| `cat f` / `head -n 20` / `tail -n 20` | `Get-Content f` / `-TotalCount 20` / `-Tail 20` |
| `tail -f f` | `Get-Content f -Wait -Tail 50` |
| `grep pat f` | `Select-String pat f` |
| `which cmd` | `Get-Command cmd`，或 `where.exe cmd`（列出所有候选） |
| `export VAR=x` | `$env:VAR = 'x'` |
| `VAR=x cmd` | 没有对应写法：先设 `$env:VAR`，跑完再 `Remove-Item Env:VAR` |
| `rm -rf d` | `Remove-Item -Recurse -Force d` |
| `mkdir -p d` | `New-Item -ItemType Directory -Force d` |
| `touch f` | `if (-not (Test-Path f)) { New-Item f }` |
| `sha256sum f` | `Get-FileHash f` |
| `time cmd` | `Measure-Command { cmd }` |
| `ps` / `kill` | `Get-Process` / `Stop-Process -Id <pid>` |
| `ss -ltnp` | `Get-NetTCPConnection -State Listen` |
| `cmd1 && cmd2` | PowerShell 7 支持；5.1 不支持（用 `; if ($?) { cmd2 }`） |

`$PSVersionTable.PSVersion` 查看版本：5.1 是系统自带的，7+ 是 `pwsh`，两者行为有差别。

### 13.2 编码陷阱（中文环境必读）

中文 Windows 默认代码页是 **GBK (936)**。MSVC 和 PowerShell 5.1 都会把**没有 BOM 的 UTF-8 文件当 GBK 解码**。中文字符的尾字节可能与后面的换行符拼成一个「双字节字符」，结果**下一行代码被吞进注释**。

| 症状 | 办法 |
|---|---|
| MSVC 报莫名其妙的 `C2059` / `C3861`，行号对不上 | `cl /utf-8`（CMake：`add_compile_options($<$<CXX_COMPILER_ID:MSVC>:/utf-8>)`） |
| C/C++ 字符串里，中文紧贴收尾的 `"` 时报 missing closing quote | 中文和 `"` 之间加一个空格 |
| `.ps1` 里注释下一行的赋值「消失」，变量为 `$null`，脚本瞬间跑完却什么也没做 | `.ps1` 存成**带 BOM 的 UTF-8** |
| 控制台输出中文乱码 | `chcp 65001`，或 `[Console]::OutputEncoding = [Text.Encoding]::UTF8` |

检查文件有没有 BOM：`Format-Hex f | Select-Object -First 1`（Git Bash 里用 `head -c3 f | xxd`），开头应为 `EF BB BF`。
用 PowerShell 写带 BOM 的文件：`[IO.File]::WriteAllText($p, $txt, (New-Object Text.UTF8Encoding($true)))`

### 13.3 Git Bash / MSYS2

- 路径写法：`C:\x` 在 Git Bash 里写成 `/c/x`
- 参数里的 `/xxx` 会被自动改写成 Windows 路径：遇到这种情况加 `MSYS_NO_PATHCONV=1`
- ⚠ **DLL 版本冲突**：PATH 里有多套 MinGW（Git 自带一套，自己又装了一套）时，程序可能加载到不匹配的 `libwinpthread-1.dll`、`libstdc++-6.dll`。常见症状是多线程程序**稳定卡死**（condition_variable 丢唤醒），或者启动即崩。
  排查：`where.exe libwinpthread-1.dll`；修复：把编译所用工具链的 `bin` 放到 PATH 最前面（`export PATH=/<drive>/mingw64/bin:$PATH`）。
  Linux 上不会出现，所以症状是「只在本地 Windows 上复现」。

### 13.4 其他

```powershell
git config --global core.longpaths true      # 路径超过 260 字符时
git config --global core.autocrlf input      # 提交时转成 LF、检出时不转（配合 .gitattributes 更稳）
```

- MSVC 命令行（`cl` / `link`）要在「x64 Native Tools Command Prompt」里用，或者先执行 `vcvars64.bat`
- 笔记本上跑出来的耗时与服务器不可比：本地只用来做编译验证和小规模调试

---

## 14. 排错速查表

| 症状 | 可能原因 | 排查 / 修复 | 见 |
|---|---|---|---|
| `command not found` | 没装 / 不在 PATH / PATH 缓存 | `type -a <cmd>`、`echo $PATH`、`hash -r` | §1.6 |
| `$'\r': command not found`、`^M: bad interpreter` | CRLF 换行 | `grep -c $'\r' f`、`dos2unix` | §4.3 |
| `Permission denied`（执行脚本） | 没有 x 权限 / 分区挂载为 noexec | `chmod +x`，或 `bash script.sh` | —— |
| awk 报 `syntax error at or near ,`；字段全空但程序正常结束 | mawk 不支持 gawk 扩展 | `awk --version`，装 gawk | §3.2 |
| 脚本「瞬间完成」却什么也没做 | 变量为空 / glob 没匹配到 / 编码吞行 | `bash -x`、检查 BOM 和编码 | §1.7 §13.2 |
| 改了代码，行为没变 | 没重编 / 带了跳过构建开关 / 服务器没 pull / 跑的是别处的二进制 | `find src -newer <bin>`、`git log -1`、`type -a` | §9.2 §7.3 |
| 新增字段 / 日志行没出现 | 同上：旧二进制 | 同上 | §9.2 |
| 新文件没同步到服务器 | 被 `.gitignore` 忽略 | `git check-ignore -v <f>` | §8.4 |
| `git pull` 被拒 | 服务器上有本地改动 | `git status` → `git stash` 或 `git restore` | §8.3 |
| SSH 空闲一会就断 | 没有心跳 | `ServerAliveInterval 60` | §7.1 |
| 断开 SSH 后任务没了 | 没用 nohup / tmux | 用 nohup 或 tmux 重跑 | §5.2 |
| 进程无声消失，或只打印 `Killed` | 系统 OOM | `dmesg -T \| grep -iE 'killed process\|oom'`、`/usr/bin/time -v` | §6 §5.4 |
| `No space left on device` | 磁盘满 / inode 满 | `df -h .`、`df -i .`、`du -sh * \| sort -h` | §2 |
| Segmentation fault | 越界 / 释放后使用 / 栈溢出 | gdb `bt`、ASan、`ulimit -s` | §9.5 |
| 偶发崩溃 / 偶发结果不同 | 竞态、生命周期问题 | 循环跑 N 次、TSan、查 lambda 按引用捕获 | §9.5 |
| 程序卡住不动 | 死锁 / 丢唤醒 / 等 I/O | `top -H -p`、`gdb -p` → `thread apply all bt` | §9.5 |
| 只在 Windows 本地卡死或崩溃 | DLL 版本冲突 | `where.exe <dll>`，调整 PATH 顺序 | §13.3 |
| MSVC 报错行号莫名其妙 | GBK 解码吞行 | `/utf-8` | §13.2 |
| `undefined reference` | 缺库 / 库顺序 / `extern "C"` | `nm -C`、`--verbose` 看链接命令 | §9.4 |
| `error while loading shared libraries` | 运行时找不到 .so | `ldd <app>`、`LD_LIBRARY_PATH` | §9.4 |
| `Illegal instruction` | `-march=native` 编出的二进制换了机器 | 去掉该 flag 重编 | §9.3 |
| CUDA `out of memory` | 别人占着显存 / 自己峰值太高 | `nvidia-smi --query-compute-apps=...` | §10.1 |
| `no kernel image is available` | `-arch` 与卡不匹配 | 核对 sm 号 | §10.4 |
| `CUDA driver version is insufficient` | 驱动太旧 | 看 `nvidia-smi` 与 `nvcc --version` | §10.4 |
| 计时波动很大，A/B 结论来回翻 | 共享机器 / GPU 时钟爬升 / page cache | `w`、干净卡检查、热身、交错 A/B | §10.3 §11 |
| 第一轮总是明显偏慢 | 时钟爬升 / 冷缓存 | 丢弃第一轮或先热身 | §10.3 §6 |
| 等待干净卡的开关「没效果」 | 探针不可用，被静默跳过 | `nvidia-smi -L`，检查日志里的提示行 | §10.3 |
| 端口被占用 | 另一个进程在监听 | `ss -ltnp \| grep <port>`、`lsof -i :<port>` | —— |
| 终端卡住不响应键盘 | 误按了 `Ctrl-S` | `Ctrl-Q` | §1.1 |
| 控制台中文乱码 | 代码页不是 UTF-8 | `chcp 65001` | §13.2 |

---

## 附录 A：新项目开工清单

在每个项目的 README / CLAUDE.md 里填好下面这些，以后排错时先查这里，再查本页：

| 项 | 要写清楚的内容 |
|---|---|
| 机器 | 开发机、跑分机（主机名、GPU 型号、驱动 / 工具链版本）；哪台机器**不**用来跑分 |
| 路径 | 仓库在服务器上的位置、数据根目录（环境变量名 + 默认值） |
| 同步 | git 同步流程；`.gitignore` 策略（白名单还是黑名单）；谁负责提交 |
| 环境预检 | 一条自检命令，覆盖工具链、awk、依赖库等 |
| 构建 | 构建命令、关键 flag（如 `-arch=sm_XX`）；什么时候可以跳过构建 |
| 运行入口 | 主要脚本及常用开关；环境变量表（名字、默认值、用途） |
| 结果 | 日志、汇总表、最新结果各在哪；结果文件的命名规则 |
| 正确性判据 | 用什么判定结果正确（与基线逐项比对？哪些日志标志？） |
| 计时口径 | 含不含 I/O；与谁比较；加速比怎么算 |
| 跑卡档位 | 哪类运行必须独占资源（§0） |
| 已知坑 | 项目特有的陷阱，每条写成「症状 → 原因 → 命令」 |

## 附录 B：复制即用模板

```bash
# B1. 长任务：挂到后台、落日志、记下 PID
nohup bash -c 'set -x; VAR=1 ./run.sh <args>' > "run_$(date +%m%d_%H%M).log" 2>&1 & echo $! > run.pid

# B2. 等资源空闲后再跑（GPU 版见 §10.3）
while kill -0 "$(cat run.pid)" 2>/dev/null; do sleep 60; done; ./next.sh

# B3. 覆盖前先备份
cp -a <f> "<f>.bak.$(date +%m%d_%H%M)"

# B4. 偶发问题：重复跑 N 次，统计失败次数
fail=0; for i in $(seq 20); do ./app <args> > /dev/null 2>&1 || fail=$((fail+1)); done; echo "fail=$fail/20"

# B5. 多个 log 汇总成表：文件名 + 指标
for f in logs/*.log; do printf '%s\t%s\n' "$(basename "$f" .log)" "$(grep -oP 'time_ms=\K[0-9.]+' "$f" | tail -1)"; done | column -t
```

⚠ `grep -P`（Perl 正则，支持 `\K`）只有 GNU grep 有，macOS 自带的 grep 不支持。
