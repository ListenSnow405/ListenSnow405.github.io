---
layout: post
title: "Linux 终端入门：常用命令与实用技巧"
date: 2026-09-01 09:00:00 +0800
categories: [学习]
tags: [Linux, 命令行, Shell]
---

对于刚接触 Linux 的人来说，终端里闪烁的光标多少有些陌生。但终端并不神秘：我们只是在用文字告诉计算机“要做什么”。熟悉命令行之后，管理文件、搜索代码和查看系统状态都会变得更加直接。

这篇文章从最常见的操作出发，整理一套可以边读边练的 Linux 终端入门路线。文中的命令默认在 Bash 或相近的 Shell 中执行。

## 1. 先认识终端、Shell 和命令

终端是我们输入和查看文字的窗口，Shell 则负责解释输入的命令。Linux 中常见的 Shell 有 Bash、Zsh 等。

一条命令通常由三部分组成：

```text
命令 [选项] [参数]
```

例如：

```bash
ls -l /home
```

这里 `ls` 是命令，`-l` 是选项，`/home` 是要查看的目录。方括号只表示内容可以省略，实际输入时不需要写出来。

遇到不熟悉的命令，可以先查看帮助：

```bash
man ls
ls --help
```

在 `man` 页面中可以按 `/` 搜索，按 `q` 退出。

> 本文示例中的 `$` 表示普通用户的命令提示符，不需要输入。以 `#` 开头的行表示注释，而不是管理员提示符。

## 2. 浏览目录

### 查看当前位置：`pwd`

```bash
pwd
```

它会输出当前工作目录的绝对路径，例如 `/home/snow/projects`。

### 列出目录内容：`ls`

```bash
ls
ls -l
ls -a
ls -lah
```

- `-l`：显示权限、大小、修改时间等详细信息；
- `-a`：显示以 `.` 开头的隐藏文件；
- `-h`：以 KB、MB、GB 等易读单位显示文件大小。

短选项通常可以合并，因此 `ls -lah` 等价于 `ls -l -a -h`。

### 切换目录：`cd`

```bash
cd /home/snow/projects  # 进入指定目录
cd ..                   # 返回上一级目录
cd ~                    # 回到当前用户的主目录
cd -                    # 回到上一次所在的目录
```

Linux 路径中有几个常见符号：

- `/`：根目录，也是绝对路径的起点；
- `~`：当前用户的主目录；
- `.`：当前目录；
- `..`：上一级目录。

以 `/` 开头的是绝对路径；从当前目录出发的则是相对路径。例如，`/home/snow/a.txt` 是绝对路径，`notes/a.txt` 是相对路径。

## 3. 创建、复制、移动和删除

### 创建目录与文件

```bash
mkdir notes
mkdir -p projects/demo/src
touch notes/linux.md
```

`mkdir -p` 可以一次创建多层目录；`touch` 会创建空文件，如果文件已经存在，则只更新其时间戳。

### 复制文件与目录

```bash
cp notes/linux.md notes/linux-backup.md
cp -r projects/demo projects/demo-backup
```

复制目录时需要使用 `-r`，表示递归处理目录中的内容。需要保留权限和时间等属性时，可以使用 `cp -a`。

### 移动与重命名

```bash
mv notes/linux.md notes/terminal.md
mv notes/terminal.md projects/demo/
```

`mv` 既可以移动文件，也可以给文件或目录重命名。

### 删除文件与目录

```bash
rm notes/linux-backup.md
rmdir notes
rm -r projects/demo-backup
```

`rmdir` 只能删除空目录，`rm -r` 会递归删除整个目录。

> `rm` 删除的内容通常不会进入回收站。执行 `rm -r` 前，先用 `pwd` 和 `ls` 确认当前位置与目标；初学时可以使用 `rm -i`，让命令在删除前逐项询问。

如果文件名以 `-` 开头，可以用 `--` 表示选项已经结束：

```bash
rm -- -example.txt
```

## 4. 查看和编辑文本

### 查看较短的文件

```bash
cat README.md
```

`cat` 会一次输出全部内容，适合短文件。面对较长的文件，使用 `less` 更方便：

```bash
less README.md
```

在 `less` 中可以滚动浏览，按 `/` 搜索，按 `q` 退出。

### 查看开头、结尾和日志

```bash
head -n 10 app.log
tail -n 20 app.log
tail -f app.log
```

`tail -f` 会持续等待并显示新增内容，常用于观察正在更新的日志；按 `Ctrl+C` 可以结束。

### 编辑文本

不少 Linux 环境提供 `nano` 或 `vim`：

```bash
nano notes.md
vim notes.md
```

`nano` 对初学者更直观。第一次使用 Vim 时，只需要先记住：按 `i` 进入编辑模式，按 `Esc` 回到普通模式，输入 `:wq` 保存退出，输入 `:q!` 放弃修改。

## 5. 搜索文件与文本

### 使用 `find` 查找文件

```bash
find . -type f -name "*.cpp"
find . -type d -name "build"
```

第一个 `.` 表示从当前目录开始查找，`-type f` 只匹配文件，`-type d` 只匹配目录。给通配模式加引号，可以避免它提前被 Shell 展开。

### 使用 `grep` 搜索文本

```bash
grep "main" hello.cpp
grep -Rni "TODO" src/
```

- `-R`：递归搜索子目录；
- `-n`：显示行号；
- `-i`：忽略大小写。

如果安装了 ripgrep，`rg` 通常更快，也会自动尊重 Git 的忽略规则：

```bash
rg "TODO" src
rg --files
```

### 排序、去重与统计

```bash
sort names.txt
sort names.txt | uniq
wc -l names.txt
```

`sort` 负责排序，`uniq` 合并相邻的重复行，`wc -l` 统计行数。因此在去重前通常要先排序。

## 6. 管道与重定向

管道 `|` 会把前一个命令的输出交给后一个命令：

```bash
ps aux | grep "python"
cat access.log | sort | uniq
```

很多命令也可以直接接收文件名，因此第二条还可以简化为 `sort access.log | uniq`。

重定向可以把输出写入文件：

```bash
echo "Linux notes" > notes.txt
echo "another line" >> notes.txt
```

- `>`：覆盖目标文件；
- `>>`：追加到文件末尾；
- `<`：从文件读取标准输入；
- `2>`：重定向错误信息。

如果想同时在终端查看并保存结果，可以使用 `tee`：

```bash
ls -lah | tee files.txt
```

## 7. 权限与用户

`ls -l` 输出开头的 `r`、`w`、`x` 分别表示读、写、执行权限。例如，可以让脚本对当前用户可执行：

```bash
chmod u+x run.sh
./run.sh
```

也可以使用数字形式，例如 `chmod 755 run.sh`，但对初学者来说，`u+x`、`g-w` 等符号形式更容易看出修改了什么。

查看当前用户及所属用户组：

```bash
whoami
id
```

修改所有者通常需要管理员权限：

```bash
sudo chown user:group file.txt
```

`sudo` 会以更高权限执行命令。使用它之前应确认命令的来源、目标和影响，不要把 `sudo` 当作解决所有权限问题的通用方法。

## 8. 进程与系统信息

### 查看和结束进程

```bash
ps aux
ps aux | less
top
```

找到进程号 PID 后，可以请求进程正常结束：

```bash
kill 12345
```

只有普通结束信号无效时，才考虑 `kill -9 12345`。强制结束会让程序失去清理资源和保存数据的机会。

### 查看磁盘、内存和系统信息

```bash
df -h
du -sh .
free -h
uname -a
```

- `df -h`：查看各文件系统的可用空间；
- `du -sh .`：统计当前目录占用的空间；
- `free -h`：查看内存使用情况；
- `uname -a`：查看内核与系统信息。

## 9. 网络与软件安装

以下命令可以帮助检查网络或获取远程内容：

```bash
ping -c 4 example.com
curl -I https://example.com
ssh user@example.com
```

不同 Linux 发行版使用不同的软件包管理器。Debian、Ubuntu 常用 `apt`：

```bash
sudo apt update
sudo apt install git
```

Fedora 常用 `dnf`，Arch Linux 常用 `pacman`。安装前应先确认自己的发行版，不要直接照搬不匹配的命令。

## 10. 提高效率的小技巧

终端中有一些值得形成习惯的操作：

- 按 `Tab` 自动补全命令、文件名和目录名；
- 按 `↑`、`↓` 浏览历史命令；
- 按 `Ctrl+R` 搜索历史命令；
- 按 `Ctrl+C` 中止当前程序；
- 按 `Ctrl+L` 清理屏幕；
- 使用 `history` 查看命令历史；
- 使用引号保护包含空格的路径，例如 `cd "My Projects"`。

命令还可以根据执行结果进行组合：

```bash
mkdir demo && cd demo
test -f config.txt || touch config.txt
```

`&&` 只在前一条命令成功时继续，`||` 只在前一条命令失败时继续。

Shell 会展开 `*` 等通配符。正式执行批量移动或删除前，可以先用 `printf '%s\n' *.log` 查看将被匹配的文件。

## 11. 一个小练习

尝试完成下面的任务：

```bash
mkdir -p terminal-practice/docs
cd terminal-practice
touch docs/day1.txt docs/day2.txt
echo "learn pwd and ls" > docs/day1.txt
echo "learn grep and find" > docs/day2.txt
cp -r docs docs-backup
find . -type f -name "*.txt"
grep -Rni "learn" .
du -sh .
```

练习结束后，先返回上一级目录并确认目标，再删除整个练习目录：

```bash
cd ..
pwd
ls
rm -ri terminal-practice
```

## 12. 常用命令速查

| 场景 | 命令 |
| --- | --- |
| 查看位置与目录 | `pwd`、`ls`、`cd` |
| 创建文件和目录 | `touch`、`mkdir` |
| 复制、移动、删除 | `cp`、`mv`、`rm` |
| 查看文本 | `cat`、`less`、`head`、`tail` |
| 搜索 | `find`、`grep`、`rg` |
| 文本处理 | `sort`、`uniq`、`wc` |
| 权限 | `chmod`、`chown`、`sudo` |
| 进程与资源 | `ps`、`top`、`kill`、`df`、`du`、`free` |
| 网络 | `ping`、`curl`、`ssh` |

不必一次记住所有选项。先理解“当前目录”和“输入、输出”这两个核心概念，再在真实任务中反复使用，命令会自然地变得熟悉。

掌握文件与文本操作之后，下一步就是在终端中编译、构建和调试代码。可以继续阅读[《Linux 命令行开发：编译、构建与调试》]({% post_url 2026-09-01-linux-command-line-development %})。
