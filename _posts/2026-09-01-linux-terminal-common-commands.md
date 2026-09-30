---
layout: post
title: "终端环境与文件操作"
date: 2026-09-01 09:00:00 +0800
categories: [学习]
tags: [终端, PowerShell, Linux, 文件操作, 终端实验系列]
excerpt: "识别 Windows 与 Linux 的执行环境，通过同一个练习目录掌握路径、文件操作、文本检索、权限、编码与换行。"
series: terminal-lab
series_order: 1
---

在本地整理数据、在服务器运行程序之前，首先需要回答两个问题：命令在哪台机器上执行，输入与输出文件位于哪个目录。许多错误并非命令拼写错误，而是环境和位置判断错误。

本文是“命令行开发与实验实践”系列第一篇，不要求编程经验。Windows 路线使用 **PowerShell 7**，Linux 路线使用 **Bash 与 GNU 工具**；两组命令是替代路线，不应连续混用。练习只在个人练习目录执行，不在已有代码仓库、共享数据目录或系统目录中执行。

阅读顺序：**环境与文件 → Shell 脚本 → 构建调试 → 远程任务 → 日志整理 → 性能实验**。下一篇为[Shell 执行与脚本基础]({% post_url 2026-09-30-shell-execution-and-scripting %})；完整入口见[系列导读]({{ '/series/' | relative_url }}#terminal-lab)。本文由原 Linux 终端入门文章重构，发布地址保持不变。

<span id="1-先认识终端shell-和命令"></span>

## 1. 终端与执行环境

终端负责接受输入和显示文字，Shell 负责解释命令，工具程序负责完成具体任务。Windows Terminal 可以承载 PowerShell、cmd 和 WSL 等环境；窗口相同，不意味着语法和可用命令相同。

| 环境 | 路径与执行边界 | 核对入口 |
| --- | --- | --- |
| Windows PowerShell | Windows 文件系统；管道主要传递对象 | `$PSVersionTable`、`Get-Location` |
| Linux Bash | 当前 Linux 主机的文件系统；常规管道传递字节流 | `$BASH_VERSION`、`hostname`、`pwd` |
| Git Bash | Windows 上的类 Unix 工具环境，盘符路径常见如 `/c/` | 工具路径及 Windows 程序的路径转换 |
| WSL | Linux 子系统，Windows C 盘常见挂载点为 `/mnt/c/` | 发行版、挂载位置及程序所属环境 |
| SSH 会话 | 命令在连接的远端主机执行 | 主机名、用户名和远端目录 |

PowerShell 中的 `ls`、`cp`、`rm` 可能是 cmdlet 的别名，不接受一整套 GNU 参数。本文使用 `Get-ChildItem` 等全名。在 Linux 中，`$SHELL` 常表示登录 Shell 配置，不足以证明当前解释器一定是 Bash，应结合版本和进程判断。

**Windows 本地 · PowerShell 7**：

```powershell
$PSVersionTable.PSVersion
Get-Location
Get-Command Get-ChildItem
Get-Help Copy-Item -Examples
```

**Linux 本地或远端 · Bash**：

```bash
printf '%s\n' "$BASH_VERSION"
hostname
whoami
pwd
type -a ls
man cp
```

`man` 中按 `/` 搜索、按 `q` 退出。Windows 帮助未完整安装时，可查阅 Microsoft Learn。代码块不包含提示符，出现的 `#` 是注释；不要复制提示符中的用户名、机器名或 `$`。

<span id="2-浏览目录"></span>
<span id="查看当前位置pwd"></span>
<span id="列出目录内容ls"></span>
<span id="切换目录cd"></span>

## 2. 路径与目录

### 工作目录与路径解析

相对路径以当前工作目录为起点。`data/input.txt` 并不固定指向某一文件；切换目录后，它可能指向另一文件或不存在。绝对路径携带完整位置，但 Windows 的 `C:\...` 不能直接作为 Linux 服务器路径。

`.` 表示当前目录，`..` 表示父目录。Bash 的 `~` 在适当位置展开为主目录；PowerShell 可通过 `$HOME` 得到个人主目录。含空格的路径应作为一个参数传入，使用引号保护。

练习使用个人主目录下的 `terminal-lab`，初次执行前确认该目录不存在。若有同名项目，选择另一个空目录，并在后续步骤始终使用同一路径。

**Windows 本地 · PowerShell 7**：

```powershell
$labRoot = Join-Path $HOME 'terminal-lab'
if (Test-Path -LiteralPath $labRoot) { throw '练习目录已存在，请另选空目录' }
New-Item -ItemType Directory -Path $labRoot
Set-Location -LiteralPath $labRoot
New-Item -ItemType Directory -Path data, logs, backup, 'notes with spaces'
Get-Location
Get-ChildItem -Force
```

**Linux · Bash**：

```bash
lab_root="$HOME/terminal-lab"
if test -e "$lab_root"; then printf '练习目录已存在\n' >&2; exit 1; fi
mkdir -- "$lab_root"
cd -- "$lab_root"
mkdir data logs backup 'notes with spaces'
pwd
ls -la
```

Bash 的 `exit` 会结束当前 Shell，因此也可把检查部分保存成脚本执行。目录建立后，所有连续步骤均在项目根目录运行。进入空格目录分别用 `Set-Location -LiteralPath 'notes with spaces'` 与 `cd -- 'notes with spaces'`，再用对应切换命令返回 `..`。

### 输入文件与字节约定

创建三行 ASCII 文本，UTF-8 编码、无 BOM，每行以 LF 结束。特意约定字节格式，是为了使两端校验和可直接比较；它不是所有文本文件的通用要求。

```powershell
# Windows 本地 · PowerShell 7，terminal-lab 根目录
$text = "sample_id,value`ns01,10`ns02,20`n"
$path = Join-Path (Get-Location).Path 'data/input.txt'
[IO.File]::WriteAllText($path, $text, [Text.UTF8Encoding]::new($false))
Get-Content -LiteralPath $path -Encoding utf8
```

```bash
# Linux · Bash，terminal-lab 根目录
printf 'sample_id,value\ns01,10\ns02,20\n' > data/input.txt
cat data/input.txt
```

两端应看到表头和两条记录，共三行。写入已有同名文件会覆盖原内容；这里的前提是新建空目录。真实实验中，应先确定文件是否已经存在。

<span id="3-创建复制移动和删除"></span>
<span id="创建目录与文件"></span>
<span id="复制文件与目录"></span>
<span id="移动与重命名"></span>
<span id="删除文件与目录"></span>

## 3. 文件操作与影响范围

### 副本与完整性检查

复制生成副本，移动改变位置，重命名改变名称。复制成功并不自动证明字节完整，应核对目标文件，再比较校验和。

```powershell
# Windows 本地 · PowerShell 7
Copy-Item -LiteralPath 'data/input.txt' -Destination 'backup/input.txt'
Get-FileHash -LiteralPath 'data/input.txt', 'backup/input.txt' -Algorithm SHA256
Copy-Item -LiteralPath 'backup/input.txt' -Destination 'backup/input-renamed.txt'
Move-Item -LiteralPath 'backup/input-renamed.txt' -Destination 'backup/archived.txt'
Get-ChildItem -LiteralPath backup
```

```bash
# Linux · Bash
cp -i -- data/input.txt backup/input.txt
sha256sum data/input.txt backup/input.txt
cp -i -- backup/input.txt backup/input-renamed.txt
mv -i -- backup/input-renamed.txt backup/archived.txt
ls -l backup
```

第一次复制后，两个哈希应相同；最后应存在 `backup/input.txt` 和 `backup/archived.txt`。`cp -i`、`mv -i` 在目标已存在时询问覆盖。目录复制与属性保留需另查 `cp -r`、`cp -a`，不能认为普通复制保留了全部访问控制信息。

### 删除目标与预览

删除实验只处理刚生成的 `backup/archived.txt`，原始输入和备份保留。

```powershell
# Windows 本地 · PowerShell 7，仍在项目根目录
$deleteTarget = (Resolve-Path -LiteralPath 'backup/archived.txt').Path
Get-Item -LiteralPath $deleteTarget
Remove-Item -LiteralPath $deleteTarget -WhatIf
Remove-Item -LiteralPath $deleteTarget
Test-Path -LiteralPath $deleteTarget
```

```bash
# Linux · Bash，仍在项目根目录
pwd
ls -l -- backup/archived.txt
rm -i -- backup/archived.txt
test ! -e backup/archived.txt && printf '已删除练习副本\n'
```

PowerShell 最后应输出 `False`。`-WhatIf` 是支持该机制的 cmdlet 的预览，并不锁定文件系统；预览后目标仍可能变化。Bash 中 `--` 结束选项解析，可保护以连字符开头的文件名。

递归删除还会影响全部后代文件。清理整个练习目录时，应先解析完整目标，核对它位于预期练习父目录中并列出内容，再执行明确的删除命令。空变量检查只能避免部分错误，不能证明路径正确。终端删除通常不进入回收站，覆盖也没有普遍适用的撤销功能；唯一副本不应参与清理练习。

<span id="4-查看和编辑文本"></span>
<span id="查看较短的文件"></span>
<span id="查看开头结尾和日志"></span>
<span id="编辑文本"></span>
<span id="5-搜索文件与文本"></span>
<span id="使用-find-查找文件"></span>
<span id="使用-grep-搜索文本"></span>
<span id="排序去重与统计"></span>

## 4. 文本查看与检索

### 文件长度与读取方式

短文件可直接读取，长文件应分页或查看局部。Linux 的 `less data/input.txt` 可以滚动与搜索；`head -n 5`、`tail -n 5` 查看开头和结尾。日志追踪用 `tail -f logs/run.log`，按 `Ctrl+C` 停止查看；停止查看不等于停止写日志的程序。

```powershell
# Windows 本地 · PowerShell 7
Get-Content -LiteralPath 'data/input.txt' -Encoding utf8 -TotalCount 5
Get-Content -LiteralPath 'data/input.txt' -Encoding utf8 -Tail 5
# 仅在日志存在且正在增长时使用：
# Get-Content -LiteralPath 'logs/run.log' -Encoding utf8 -Wait
```

编辑可使用已有编辑器。Linux 的 `nano` 通常更容易入门；Vim 中 `i` 进入插入模式，`Esc` 返回普通模式，`:wq` 保存退出，`:q!` 放弃当前未保存修改。不要为了查看内容误进入编辑并覆盖文件。

### 名称查找与内容查找

按名称找文件回答文件在哪里，按内容找文本回答哪一行含有目标。

```powershell
# Windows 本地 · PowerShell 7
Get-ChildItem -LiteralPath data -File -Recurse -Filter '*.txt'
Select-String -LiteralPath 'data/input.txt' -Pattern 's02,20' -SimpleMatch
```

```bash
# Linux · Bash
find data -type f -name '*.txt'
grep -nF -- 's02,20' data/input.txt
```

匹配应位于第 3 行。`find` 的模式加引号，避免 Shell 提前展开；`-F`、`-SimpleMatch` 表示字面匹配。

安装 ripgrep 后，两端均可用 `rg -n -F 's02,20' data` 与 `rg --files data`。`rg` 默认跳过隐藏文件和被忽略文件，结果为空也可能是范围问题；必要时针对性使用 `--hidden` 或 `--no-ignore`。它不是系统必然自带的工具，“找不到 rg”不能证明文件不存在。

<span id="7-权限与用户"></span>

## 5. 用户、权限与访问

Linux 的 `r`、`w`、`x` 对文件分别表示读取、写入和执行；对目录则关系到列出、增删目录项和路径遍历。删除文件还受父目录权限、粘滞位和 ACL 等影响，不由文件自身写权限单独决定。

```bash
whoami
id
ls -ld . data
ls -l data/input.txt
```

普通文本不需要执行权限。对于可信且可读的 Bash 脚本，`bash scripts/run.sh` 由解释器读取文件；`./scripts/run.sh` 还需要执行权限、合适的 shebang 和挂载条件。必要时仅对该脚本使用 `chmod u+x scripts/run.sh`，不要用 `chmod -R 777` 清除权限边界。

Windows 用 `whoami` 与 `Get-Acl -LiteralPath 'data/input.txt'` 核对账户和访问控制。`.ps1` 执行还涉及执行策略，与文件 ACL 不同。拒绝访问时先确认目标路径、所有者、权限与组织策略，不把管理员模式作为第一步。

## 6. 编码与换行

编码决定字节如何解释为字符，换行决定行尾字节，终端显示又受终端与程序输出设置影响。三者应分开检查。两个文件看起来一样，仍可能因 BOM 或 LF/CRLF 不同而哈希不同。

PowerShell 7 文本输出通常采用 UTF-8 无 BOM；Windows PowerShell 5.1 的 `Out-File`、`>` 常产生 UTF-16LE，`-Encoding UTF8` 通常带 BOM。本文的显式 .NET 写入避免默认编码差异。外部程序输出编码仍需单独核对，改变控制台代码页不等于转换已有文件。

查看字节可用 `Format-Hex -LiteralPath 'data/input.txt'`；Linux 用 `od -An -tx1 data/input.txt`。本例行尾应是 `0a`，不含 `0d 0a`；UTF-8 BOM 是 `ef bb bf`。`file data/input.txt` 提供检测线索，推断编码不是严格证明。

下面是独立的脚本换行实验，需已安装 Python 3。先创建 `scripts/`，保存为 `scripts/fix_newlines.py`；Windows 用 `python`、Linux 用 `python3` 从项目根目录执行。它只产生练习文件，不改真实源码。

```python
from pathlib import Path
source = Path("logs/crlf-demo.sh")
source.write_bytes(b"#!/usr/bin/env bash\r\nprintf 'hello\\n'\r\n")
# 保留原件，明确移除 CRLF 中的 CR；这里已知输入仅为 ASCII。
target = Path("logs/lf-demo.sh")
target.write_bytes(source.read_bytes().replace(b"\r\n", b"\n"))
print(source.read_bytes())
print(target.read_bytes())
```

Linux 运行 `bash logs/lf-demo.sh` 应输出 `hello`。CRLF 原件可能出现 `$'\r'`、解释器路径含 `\r` 等错误，症状取决于调用方式。未知编码文件应先按正确编码解码，再写出目标编码，不能用删字节的方法修复所有乱码。

## 7. 常见问题

| 症状 | 检查与判断依据 | 处理 |
| --- | --- | --- |
| 找不到输入 | 当前目录、完整路径和文件名 | 用绝对路径确认，再修正相对路径 |
| 空格路径被拆开 | 是否作为单个参数传入 | 完整路径加引号，文件 cmdlet 优先用 `-LiteralPath` |
| PowerShell 的 `ls -lah` 报错 | `Get-Command ls` 是否为别名 | 改用原生参数 |
| 哈希不同但内容相似 | BOM、行尾、编码和末尾换行 | 区分字节一致与文本等价 |
| 权限不足 | 路径、账户、目录权限和执行方式 | 针对具体限制处理 |
| 中文显示错误 | 文件字节、解码与输出编码 | 保留原件，再修复对应环节 |

<span id="12-常用命令速查"></span>

## 8. 命令速查

| 目标 | Windows PowerShell | Linux Bash / 工具 |
| --- | --- | --- |
| 定位 | `Get-Location`、`Set-Location` | `pwd`、`cd` |
| 列出 | `Get-ChildItem -Force` | `ls -la` |
| 创建目录 | `New-Item -ItemType Directory` | `mkdir` |
| 文件操作 | `Copy-Item`、`Move-Item`、`Remove-Item` | `cp`、`mv`、`rm` |
| 查看 | `Get-Content` | `cat`、`less`、`head`、`tail` |
| 检索 | `Select-String -SimpleMatch` | `grep -nF`、`rg -nF` |
| 字节校验 | `Get-FileHash -Algorithm SHA256` | `sha256sum` |
| 帮助 | `Get-Help`、`Get-Command` | `man`、`type`、`--help` |

两列对应目标，不承诺参数、权限保留或递归行为完全相同。

<span id="11-一个小练习"></span>

## 9. 实践练习

1. 建立目录并写出三行输入。验收：当前位置为练习根目录，原件与副本 SHA-256 相同。
2. 检索 `s02,20`。验收：来源为 `data/input.txt`、行号为 3；搜索副本时明确改变范围。
3. 新建 CRLF 副本。验收：解释为何它与 LF 原件哈希不同，但解码后可文本等价。
4. 删除指定副本。验收：执行前能指出完整目标，执行后原件与 `backup/input.txt` 仍存在。

Windows 文件操作在 PowerShell 7 中实测；Linux 原生命令和权限实验未在 Linux 主机执行。跨平台流程不以 Windows 成功代替 Linux 验证。

<span id="6-管道与重定向"></span>
<span id="8-进程与系统信息"></span>
<span id="查看和结束进程"></span>
<span id="查看磁盘内存和系统信息"></span>
<span id="9-网络与软件安装"></span>
<span id="10-提高效率的小技巧"></span>

## 10. 旧章节入口

旧文管道、条件执行迁入[第二篇]({% post_url 2026-09-30-shell-execution-and-scripting %})，进程、资源和 SSH 迁入[第四篇]({% post_url 2026-09-30-remote-development-and-task-management %})，排序与统计迁入[第五篇]({% post_url 2026-09-30-log-analysis-and-result-processing %})。旧章节链接保留为定位入口，完整流程以对应专题为准。

## 11. 参考资料

- [Windows Terminal 常见问题](https://learn.microsoft.com/en-us/windows/terminal/faq)。
- [PowerShell 字符编码](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_character_encoding)。
- [GNU Coreutils 手册](https://www.gnu.org/software/coreutils/manual/coreutils.html)。
- [ripgrep 使用指南](https://github.com/BurntSushi/ripgrep/blob/master/GUIDE.md)。

下一篇：[Shell 执行与脚本基础]({% post_url 2026-09-30-shell-execution-and-scripting %})。
