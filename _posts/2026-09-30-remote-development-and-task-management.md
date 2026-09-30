---
layout: post
title: "远程开发与任务管理"
date: 2026-09-30 00:02:00 +0800
categories: [学习]
tags: [SSH, Linux, tmux, 任务管理, 终端实验系列]
excerpt: "区分本地客户端与远端执行位置，完成项目同步、环境预检和长任务运行，并用进程、日志与资源证据判断任务状态。"
series: terminal-lab
series_order: 4
---

服务器任务需要同时管理三种状态：本地项目是否已经同步，远端进程是否仍在运行，运行结果是否有效。SSH 连接正常不能证明任务会在断线后继续，进程消失也不能证明计算成功。

本文是系列第四篇，需要有权使用的 Linux 账户，并掌握[脚本与退出状态]({% post_url 2026-09-30-shell-execution-and-scripting %})。计算项目来自[第三篇]({% post_url 2026-09-01-linux-command-line-development %})。本地客户端可以是 Windows PowerShell 7 或 Linux Bash，远端命令统一在 Linux Bash 执行。没有服务器时可阅读流程，本篇不声称完成远端实测。

## 1. 连接与主机识别

### 客户端与远端边界

先核对本地 OpenSSH 客户端：Windows 使用 `Get-Command ssh, scp`，Linux 使用 `command -v ssh`、`command -v scp`。`ssh -V` 查看客户端版本，不能代表服务器版本。

以下是需替换的配置模板：把 `server.example.org`、`student`、端口与密钥文件改为账户管理员提供的真实值。配置保存到本地个人目录的 `.ssh/config`，Windows 常见为 `$HOME/.ssh/config`，Linux 为 `~/.ssh/config`；不要覆盖已有配置，添加一个独立 Host 段。

```text
Host lab-server
    HostName server.example.org
    User student
    Port 22
    IdentityFile ~/.ssh/id_ed25519
    ServerAliveInterval 30
    ServerAliveCountMax 3
```

若有跳板机，可按实际网络配置 `ProxyJump jump-alias`，并另定义该别名。首次连接应通过可信渠道核对主机密钥指纹；指纹变化需要查明原因，不直接关闭主机校验。登录密钥的公钥可交给服务器管理者配置，私钥不上传、不写入实验日志。

**本地 PowerShell 或 Bash**：

```bash
ssh lab-server
```

**连接后 · 远端 Linux Bash**：

```bash
hostname
whoami
pwd
printf '%s\n' "$BASH_VERSION"
```

确认主机和用户后才继续。`ServerAliveInterval` 用于连接存活检测，既不是任务调度，也不能使计算进程抵御机器重启。`exit` 退出远端会话，后续命令又在本地执行；文章中明确标注执行位置正是为了防止操作错机器。

## 2. 代码与数据同步

### Git 提交路线

代码仓库适合按提交同步。先在本地核对 `git status --short`、`git rev-parse HEAD`，有意选择、提交和推送需要的源文件；再在远端克隆或更新。未提交内容不会因 `git push` 自动传到服务器，未跟踪输入也不包含在提交中。

远端克隆模板中的 URL 必须换成自己有权访问的练习仓库：

```bash
# 远端 Linux Bash：先确认 ~/work 下尚无同名项目
mkdir -p ~/work
cd ~/work
git clone <YOUR_REPOSITORY_URL> terminal-lab
cd terminal-lab
git rev-parse HEAD
git status --short
```

占位符不能原样执行。已有项目不要重新克隆覆盖；先核对远端改动，再按项目协作约定更新。`.gitignore` 只影响特定 Git 跟踪行为，已经跟踪的文件不会因此自动消失，也不决定 scp、rsync 是否复制某个文件。

### 文件复制路线

没有练习仓库时可用 scp。先在远端创建 `~/work/terminal-lab/src`，然后退出回本地，在本地项目根目录执行：

```powershell
# Windows 本地 · PowerShell，OpenSSH scp 已安装
scp ./CMakeLists.txt lab-server:work/terminal-lab/
scp ./src/vector_lab.cpp lab-server:work/terminal-lab/src/
```

Linux 本地同样可以用这两条 scp 命令。远端相对路径 `work/...` 是相对于远端用户主目录的约定，若组织有指定工作盘，应替换为实际获准目录。只复制源码，在远端重新编译；本地 `.exe` 不会因为复制到 Linux 就变为可执行的 Linux 程序。

Linux 本地如已安装 rsync，且服务器也提供 rsync，可用独立同步路线：

```bash
# 本地 Linux Bash，terminal-lab 根目录；先预览
rsync -av --dry-run --exclude='.git/' --exclude='build*/' \
  --exclude='logs/' --exclude='results/' --exclude='metadata/' \
  ./ lab-server:work/terminal-lab/
```

检查预览后再去掉 `--dry-run`。源路径尾部 `/` 表示复制目录内容，省略时可能在目标下多出一层目录。这里未使用 `--delete`，同名目标仍可能被更新，因此不能把预览当作备份。Windows 的 scp 不等于自带 rsync；使用 WSL 或额外工具时必须说明环境和本地路径，不把 Bash 命令直接放到 PowerShell。

数据与结果应独立同步，输入哈希在两端一致；Linux 用 `sha256sum`，Windows 用 `Get-FileHash -Algorithm SHA256`。哈希匹配证明该文件字节相同，不证明它对应了正确实验参数。

## 3. 环境预检与远端构建

在远端项目根目录执行，先核对机器、工具与空间，再复用第三篇流程：

```bash
hostname
uname -a
command -v g++ cmake
g++ --version
cmake --version
df -h .
df -i .
cmake -S . -B build-linux -G 'Unix Makefiles' -DCMAKE_BUILD_TYPE=Release
cmake --build build-linux --parallel 2
ctest --test-dir build-linux --output-on-failure
./build-linux/vector_lab 1003 B 2
```

每一步失败都先处理原因。远端工具版本可能不同，工作目录可能在容量配额或共享文件系统下。`df -h` 有空间但 inode 或用户配额耗尽，仍可能写入失败；并行构建线程数也要遵守服务器资源约定。

核对真实程序路径和代码状态后，先做小规模正确性运行。性能实验需要资源条件，第六篇另行讨论；“服务器能运行”不代表已具备可比较计时条件。

## 4. 长任务与会话

### tmux 主线

tmux 是远端终端复用器，需要服务器已安装且允许使用。在获准交互运行任务的机器上，它可以让会话暂离后重新接入；若组织要求通过调度器运行，应在资源分配流程内使用，不能在登录节点直接发起计算。

**远端 Linux Bash**：

```bash
tmux new -s terminal-lab
```

进入 tmux 后确认当前位置为项目根目录，再运行以下独立教学任务：

```bash
mkdir -p logs
run_id="remote-$(date -u +%Y%m%dT%H%M%S)-$$"
log="logs/$run_id.log"
(set -C; : > "$log") || exit 1
printf 'run_id=%s\nstarted_at=%s\n' "$run_id" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$log"
./build-linux/vector_lab 1000000 B 100 >> "$log" 2>&1 &
task_pid=$!
printf '%s\n' "$task_pid" > "logs/$run_id.pid"
printf 'task pid=%s log=%s\n' "$task_pid" "$log"
wait "$task_pid"
task_rc=$?
printf 'exit_code=%s\n' "$task_rc" >> "$log"
```

这是任务管理日志，不包含第五篇完整字段；正式性能记录使用第六篇驱动。100 次计算是有限任务，机器快时可能很快结束，不承诺演示固定时长。

按 `Ctrl+B`，松开后按 `D` 暂离；从本地重新 SSH 登录后执行 `tmux ls`、`tmux attach -t terminal-lab`。原 Shell 仍负责 `wait` 和退出记录，即使本地断开也能继续。任务仍可能受重启、OOM、用户注销策略或调度回收影响；tmux 不是持久任务服务。

### nohup 与后台边界

`&` 只把任务放入后台，不自动处理全部退出信号；`disown` 改变 Shell 作业管理，也不等于可靠运行服务。没有 tmux 时可在服务器规则允许的前提下，以 nohup 包住负责记录退出码的 Shell：

```bash
# 远端 Linux Bash，独立替代实验；同名文件必须尚不存在
test ! -e logs/nohup-test.log && test ! -e logs/nohup-test.exit || exit 1
nohup bash -c '
  ./build-linux/vector_lab 1000000 B 100
  rc=$?
  printf "%s\n" "$rc" > logs/nohup-test.exit
  exit "$rc"
' > logs/nohup-test.log 2>&1 < /dev/null &
task_pid=$!
printf 'wrapper pid=%s\n' "$task_pid"
```

外层启动状态不是内部计算最终状态，应检查 `.exit` 和日志。进程被强制杀死时退出文件可能根本没有产生，此时记为未确认。nohup 处理挂断信号，不保证重启后继续。

## 5. 进程状态与停止

PID 标识当前进程，之后可能复用；记录时同时保留主机、启动时间和命令行。`jobs -l` 查看当前 Shell 的作业，另一 Shell 通常不能用它找到原作业，`wait` 也只能等待当前 Shell 的相应子进程。

```bash
# 远端 Linux Bash：把 12345 替换为刚记录的实际 PID
ps -p 12345 -o pid,ppid,stat,etime,args
pgrep -af vector_lab
```

`R`、`S`、`D`、`Z` 等状态分别涉及运行/可运行、睡眠、不可中断等待、僵尸；睡眠不自动表示卡死，僵尸也不表示还在计算。结合日志是否增长、资源和调用关系判断。

停止任务前核对目标属于自己且命令正确，先在前台 `Ctrl+C`，或对确切 PID 发送 `kill -TERM 12345`。只有明确无法正常停止时再考虑 KILL，它会跳过应用清理和结果保存；若 PID 是包装 Shell，还要检查计算子进程，不能以父进程消失推断所有子进程已停止。不要用宽泛的进程名批量杀任务。

Windows 本地对照可用 `Start-Process -PassThru` 保存进程对象，并用 `WaitForExit()` 与 `ExitCode` 查看结果；读取标准输出与错误时指定不同文件。`Stop-Process` 会结束进程，不保证程序执行优雅清理，需优先使用应用自身的停止接口。

## 6. 资源与服务检查

### CPU、内存、磁盘与端口

以下均在远端执行，部分工具需额外安装或权限：

```bash
top
free -h
df -h .
df -i .
du -sh logs
uptime
ss -ltn
```

负载包含可运行任务及部分不可中断等待，不等于 CPU 使用百分比；内存中的缓存不应全部理解为被应用占死，应结合 available、swap 和进程 RSS。端口监听只证明有服务占用，不证明服务正常。检查进程归属可用 `ss -ltnp`，权限不足时可能看不到其他用户进程。

任务突然消失且没有退出记录时，核对调度结果、应用错误和有权访问的系统日志；`journalctl -k`、`dmesg` 可能受限。退出 137 常涉及 SIGKILL，但不能单凭这一数值断言 OOM，需对应证据。磁盘满也可能导致日志截断，最后一行成功文字不足以覆盖这些缺口。

### GPU 状态与可见设备

在拥有 NVIDIA GPU 且获准使用的远端上：

```bash
nvidia-smi --query-gpu=index,uuid,name,memory.used,memory.total,utilization.gpu --format=csv
probe_rc=$?
if (( probe_rc != 0 )); then printf 'GPU 查询失败\n' >&2; exit "$probe_rc"; fi
nvidia-smi --query-compute-apps=gpu_uuid,pid,process_name,used_memory --format=csv
```

查询失败要保留错误，空输出不能自动解释为空闲。利用率是采样观察，既不提供预留，也无法保证之后没有其他任务；使用 GPU 前仍需遵守分配规则。

若已获准使用某个 GPU，可用它的实际 UUID 设置单次 CUDA 可见性，例如 `CUDA_VISIBLE_DEVICES=GPU-实际UUID ./your_cuda_program`；这是占位模板，需替换 UUID 与程序。选择后应用内的逻辑 device 0 可能对应主机上原来编号不同的 GPU，记录 UUID 可减少编号歧义。MIG、容器与调度环境还有自己的可见设备规则，不随意覆盖调度器设置。

`nvidia-smi` 的 CUDA Version 表示驱动可支持的 CUDA 版本范围，不等于已安装 Toolkit；工具链用 `nvcc --version` 核对。进程显存占用和瞬时利用率也不能单独解释性能瓶颈。

### 调度系统最小入口

只有确认服务器采用 Slurm 后才使用其命令。已有合法作业可用 `squeue -u "$USER"` 查看队列，`sacct -j 实际作业号 --format=JobID,State,ExitCode,Elapsed` 查询最终记录；提交脚本的分区、账号、GPU 和时间限制必须按本机规则填写，不提供声称通用的资源申请模板。没有 Slurm 的机器无需安装它来完成本篇。

## 7. 常见问题与命令速查

| 症状 | 检查与判断依据 | 处理 |
| --- | --- | --- |
| 本地能运行而服务器失败 | 二进制平台、工具链、输入路径 | 远端重新构建并做小规模验证 |
| 推送后服务器仍是旧代码 | 两端提交与未提交状态 | 同步明确提交，单独处理输入 |
| 断线后任务停止 | 是否只使用 `&`、注销或调度策略 | 按服务器要求使用会话或作业系统 |
| PID 不存在 | 日志、退出记录及调度状态 | 标记未确认，不能直接判成功 |
| GPU 看似空闲但无权使用 | 分配记录、可见性、探针状态 | 按资源规则处理，不用轮询替代申请 |

| 目标 | 入口与位置 |
| --- | --- |
| 连接、复制 | 本地 `ssh`、`scp`；rsync 需两端支持 |
| 会话 | 远端 `tmux new/ls/attach` |
| 状态 | 远端 `ps`、`pgrep`、当前 Shell 的 `jobs` |
| 结果 | 原包装 Shell 的 `wait` 与日志退出记录 |
| 资源 | 远端 `top`、`free`、`df`、`ss`、`nvidia-smi` |

## 8. 实践练习与验证范围

验收：两端代码版本及输入哈希一致；远端 CTest 通过；暂离并重新接入后能找到任务与对应日志；有限任务结束后保留真实退出码；解释“当前空闲”与“获准占用”的区别。没有服务器或调度权限时，记录未执行项目，不模拟一份成功报告。本篇 SSH 同步、tmux、远端资源及 Slurm 流程未实测，作为明确前提的操作流程提供。

## 9. 参考资料

- [OpenSSH 配置手册](https://man.openbsd.org/ssh_config)。
- [rsync 手册](https://download.samba.org/pub/rsync/rsync.1)。
- [tmux 官方手册](https://github.com/tmux/tmux/blob/master/tmux.1)。
- [GNU nohup](https://www.gnu.org/s/coreutils/manual/html_node/nohup-invocation.html)。
- [NVIDIA SMI](https://docs.nvidia.com/deploy/nvidia-smi/)。
- [Slurm sacct](https://slurm.schedmd.com/sacct.html)。

上一篇：[命令行构建与程序调试]({% post_url 2026-09-01-linux-command-line-development %}) · 下一篇：[日志分析与结果整理]({% post_url 2026-09-30-log-analysis-and-result-processing %})。
