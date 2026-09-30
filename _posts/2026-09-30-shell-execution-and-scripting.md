---
layout: post
title: "Shell 执行与脚本基础"
date: 2026-09-30 00:01:00 +0800
categories: [学习]
tags: [Shell, Bash, PowerShell, 脚本, 终端实验系列]
excerpt: "通过确定性演示程序，解释参数、变量、管道、输出与退出状态，并建立能保存失败证据的 Bash 和 PowerShell 运行脚本。"
series: terminal-lab
series_order: 2
---

把同一条命令执行多次并不困难，困难的是确认每次收到正确参数、保存了所需输出，而且失败没有被后续日志命令掩盖。脚本的价值是明确这些约定，让执行过程可检查。

本文是系列第二篇，前置知识见[终端环境与文件操作]({% post_url 2026-09-01-linux-terminal-common-commands %})。Windows 使用 PowerShell 7，Linux 使用 Bash。演示程序依赖 Python 3，只处理确定性文本，不需要编译器、服务器或 GPU；日志统计交给[第五篇]({% post_url 2026-09-30-log-analysis-and-result-processing %})。

## 1. 最小项目与演示程序

沿用 `terminal-lab`，独立阅读时先在个人目录创建空项目及 `scripts/`、`logs/`。以下步骤都从项目根目录执行。Windows 核对 `Get-Command python`、`python --version`；Linux 核对 `command -v python3`、`python3 --version`，不要把别名指向的其他解释器当作同一个环境。

用编辑器将完整代码保存为 `scripts/demo.py`，UTF-8 编码；也可获取[配套源码]({{ '/assets/examples/terminal-lab/scripts/demo.py' | relative_url }})。

```python
import argparse
import sys

parser = argparse.ArgumentParser()
parser.add_argument("--label", required=True)
parser.add_argument("--fail", action="store_true")
args = parser.parse_args()
# 固定值仅用于演示日志与退出码，绝不能作为性能测量样本。
print("# label: " + args.label)
print("input_id=demo-v1\nn=3\nvariant=demo\nrepeat=1\nthreads=1\nseed=0")
print("correctness=" + ("fail" if args.fail else "pass"))
print("metric=demo_value\nvalue=1.25\nunit=ms\nscope=synthetic")
print("# diagnostic: deterministic demo", file=sys.stderr)
sys.exit(7 if args.fail else 0)
```

它把约定字段写入标准输出，把诊断文字写入标准错误；正常结束返回 0，加入 `--fail` 返回 7。`value=1.25` 是虚构教学字段，不能作为程序耗时。诊断行以 `#` 开头，后续解析器保留原始日志但忽略这些注释行。

## 2. 参数、引号与展开

### 单个参数与参数数组

两种 Shell 中，`'...'` 通常作为不展开变量的字符串，`"..."` 可展开变量，但转义细节不同。Bash 中双引号内反斜杠有特定规则，PowerShell 常用反引号转义，不能直接互换。

```powershell
# Windows 本地 · PowerShell 7，terminal-lab 根目录
$label = 'trial with spaces'
& python scripts/demo.py --label $label
$demoArgs = @('scripts/demo.py', '--label', $label, '--fail')
& python @demoArgs
$programRc = $LASTEXITCODE
"program exit=$programRc"
```

```bash
# Linux · Bash，terminal-lab 根目录
label='trial with spaces'
python3 scripts/demo.py --label "$label"
demo_args=(scripts/demo.py --label "$label" --fail)
python3 "${demo_args[@]}"
program_rc=$?
printf 'program exit=%s\n' "$program_rc"
```

第一条标签应完整包含空格，第二条退出码为 7。数组把参数保持为独立元素，优于拼接一大段字符串再交给 `eval` 或 `Invoke-Expression`；后者会重新解释字符串，其中的引号、分号和替换表达式都可能改变含义。

### 通配符与预览

Bash 常在调用工具前展开未引用的 `*.log`；PowerShell 中许多 cmdlet 自行解释 `-Path` 通配符，外部程序是否支持通配符取决于程序本身。

```bash
# 没有匹配时默认 Bash 可能原样保留 *.log，逐项检查避免误解。
for file in logs/*.log; do
  test -f "$file" || continue
  printf '%s\n' "$file"
done
```

PowerShell 先用 `Get-ChildItem -LiteralPath logs -File -Filter '*.log'` 列出目标，再逐个操作对象。给模式加引号不意味着两端执行同样的匹配，需要明确由 Shell、cmdlet 还是工具负责匹配。

## 3. 变量与环境

Shell 变量存在于当前解释器，环境变量可由子进程继承；子进程通常不能反向修改父 Shell 环境。Bash 用 `name=value` 建立变量，`export name` 使其进入环境；PowerShell 的 `$name` 与 `$env:NAME` 也属于不同范围。

Linux 中 `LAB_MODE=demo python3 scripts/demo.py --label test` 只对该次进程及其子进程设置环境。`LAB_MODE=demo command1 && command2` 不会自动给第二条设置同一环境。PowerShell 可用 `try/finally` 临时改变并恢复：

```powershell
$hadMode = Test-Path Env:LAB_MODE
$savedMode = $env:LAB_MODE
try {
    $env:LAB_MODE = 'demo'
    & python scripts/demo.py --label test
    $programRc = $LASTEXITCODE
} finally {
    if ($hadMode) { $env:LAB_MODE = $savedMode }
    else { Remove-Item Env:LAB_MODE -ErrorAction SilentlyContinue }
}
```

已有值应恢复，无原值时才删除。`PATH` 决定通过名字查找程序的位置，核对用 `Get-Command python -All` 或 `type -a python3`。同名工具可能有多份，版本正确也不能证明来自期望目录。仅为一次运行改变环境时，不必修改系统 PATH 或启动文件。

## 4. 管道与输入输出

### 字节流与对象流

Bash 常规管道连接前一进程标准输出与后一进程标准输入。`grep -nF 'value=' logs/run.log | head -n 5` 传递文本字节。PowerShell cmdlet 管道主要传递对象，可在格式化前选择属性：

```powershell
Get-ChildItem -LiteralPath logs -File |
    Select-Object Name, Length |
    Sort-Object Length
```

`Format-Table` 面向显示，不应放在需要保存对象属性的中间阶段。外部程序接入 PowerShell 管道还有文本与字节转换问题，因此本文只处理可解码文本；二进制复制使用文件工具，不依赖文本管道保真。

### 覆盖、追加与流合并

以下是独立实验，每条可单独执行；`>` 会覆盖同名输出。

```bash
python3 scripts/demo.py --label test > logs/stdout.log 2> logs/stderr.log
python3 scripts/demo.py --label test > logs/combined.log 2>&1
python3 scripts/demo.py --label test >> logs/appended.log 2>&1
```

Bash 重定向从左到右生效：`> file 2>&1` 先把输出送入文件，再让错误流指向同一位置；`2>&1 > file` 可能把错误留在原终端。`< input.txt` 把文件交给程序读取，不等于把路径作为参数。

```powershell
# Windows 本地 · PowerShell 7，明确保存文本编码
& python scripts/demo.py --label test 2>&1 |
    Out-File -LiteralPath 'logs/combined.log' -Encoding utf8
$programRc = $LASTEXITCODE
```

PowerShell 不提供 Bash 同样的 `<` 语法，需要查看程序的文件参数或使用明确进程接口。7.4 起部分原生命令重定向保留字节流，但合并错误流、经过 cmdlet 和旧版本时仍有差异，不能笼统视为同一二进制通道。

## 5. 退出状态与条件执行

### 外部程序与 Shell 状态

退出码是外部程序约定，0 常表示成功，非零意义由程序定义。Bash 的 `$?` 是上一条管道或命令状态；PowerShell 的 `$LASTEXITCODE` 是最近外部程序或相关脚本退出码，`$?` 是上一项操作成功状态。读取之前先运行其他命令，可能已失去所需状态。

PowerShell 的 `$ErrorActionPreference='Stop'` 能把许多 cmdlet 非终止错误转为异常，不能跨版本保证所有原生程序非零退出都抛异常。本文保存并检查退出码，不依赖该推断。

```powershell
& python scripts/demo.py --label test --fail
$programRc = $LASTEXITCODE
if ($programRc -ne 0) { "实验失败，exit=$programRc" }
```

```bash
python3 scripts/demo.py --label test --fail
program_rc=$?
if (( program_rc != 0 )); then printf '实验失败，exit=%s\n' "$program_rc"; fi
```

`&&`、`||` 在 Bash 中根据前面状态决定后续执行；PowerShell 从 7 起支持管道链运算符，5.1 需条件语句。`a && b || c` 不是完整 if/else：a 成功但 b 失败，也会执行 c。

### 管道中的失败

默认 Bash 管道状态通常来自最后一项，`tee` 成功可能掩盖实验失败。直接保存各段状态，不在管道后插入其他命令：

```bash
set -o pipefail
python3 scripts/demo.py --label test --fail 2>&1 | tee logs/tee-failed.log
codes=("${PIPESTATUS[@]}")
printf 'program=%s tee=%s\n' "${codes[0]}" "${codes[1]}"
```

应得到程序状态 7、tee 状态 0。`pipefail` 使管道返回最右侧非零状态，但不列出所有失败；需查看 `PIPESTATUS`。本实验在未启用 `set -e` 的会话执行。

`set -e` 在条件测试、部分 `&&`/`||` 列表和管道等上下文有例外，不能描述为“任意错误立即停止”。预期失败应显式捕获；PowerShell 也要分别关注退出码和日志 cmdlet 异常，不把 `$?` 当成管道每段的完整报告。

## 6. 运行脚本与重复执行

### Bash 入口

将完整脚本保存为 `scripts/run.sh`，UTF-8 无 BOM、LF 换行；[配套文件]({{ '/assets/examples/terminal-lab/scripts/run.sh' | relative_url }})与此一致。脚本定位自身目录，再进入项目根目录，因此从其他目录调用也能找到演示程序。

```bash
#!/usr/bin/env bash
set -u
# 固定从项目根执行，调用者的当前目录不影响日志位置。
root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd) || exit 1
cd -- "$root" || exit 1
if (( $# < 1 )); then printf 'usage: bash scripts/run.sh LABEL [--fail]\n' >&2; exit 2; fi
command -v python3 >/dev/null || exit 127
mkdir -p logs || exit 1
run_id="demo-$(date -u +%Y%m%dT%H%M%S)-$$-$RANDOM"
log="logs/$run_id.log"
# noclobber 阻止同名覆盖；时间、PID 和随机后缀降低碰撞概率。
(set -C; : > "$log") || exit 1
{
  printf 'run_id=%s\ncase_id=demo-v1\n' "$run_id"
  printf 'started_at=%s\nphase=sample\npair=1\norder=1\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
} >> "$log" || exit 1
python3 scripts/demo.py --label "$1" "${@:2}" >> "$log" 2>&1
program_rc=$?
# 先保存实验退出码；日志写入失败也必须成为脚本失败。
printf 'exit_code=%s\n' "$program_rc" >> "$log" || exit 1
cat -- "$log" || exit 1
exit "$program_rc"
```

运行 `bash scripts/run.sh 'trial with spaces'` 应返回 0；再运行 `bash scripts/run.sh 'failure trial' --fail` 应返回 7。日志名不同且均包含 `exit_code`。程序结束后才显示日志，这个基础模板没有实时显示，也没有假装 `tee` 就能提供全部失败状态。

### PowerShell 入口

保存为 `scripts/run.ps1`；[配套文件]({{ '/assets/examples/terminal-lab/scripts/run.ps1' | relative_url }})如下：

```powershell
#requires -Version 7.0
param([Parameter(Mandatory)][string]$Label, [switch]$Fail)
$ErrorActionPreference = 'Stop'
# PowerShell 的错误偏好不能代替外部程序的退出码检查。
$PSNativeCommandUseErrorActionPreference = $false
$root = Split-Path -Parent $PSScriptRoot
$null = Get-Command python -ErrorAction Stop
Push-Location -LiteralPath $root
try {
    $null = New-Item -ItemType Directory -Path logs -Force
    $runId = 'demo-' + [DateTimeOffset]::UtcNow.ToString('yyyyMMddTHHmmss') + '-' + [guid]::NewGuid().ToString('N')
    $log = Join-Path $root "logs/$runId.log"
    # CreateNew 即使碰撞也不会覆盖既有日志。
    $stream = [IO.File]::Open($log, [IO.FileMode]::CreateNew)
    $stream.Dispose()
    @("run_id=$runId", 'case_id=demo-v1',
      "started_at=$([DateTimeOffset]::UtcNow.ToString('o'))",
      'phase=sample', 'pair=1', 'order=1') | Set-Content -LiteralPath $log -Encoding utf8
    $demoArgs = @('scripts/demo.py', '--label', $Label)
    if ($Fail) { $demoArgs += '--fail' }
    & python @demoArgs 2>&1 | Out-File -LiteralPath $log -Append -Encoding utf8
    $programRc = $LASTEXITCODE
    "exit_code=$programRc" | Add-Content -LiteralPath $log -Encoding utf8
    Get-Content -LiteralPath $log -Encoding utf8
    exit $programRc
} finally {
    Pop-Location
}
```

从项目根目录执行独立进程，避免脚本 `exit` 影响交互会话：

```powershell
pwsh -NoProfile -File scripts/run.ps1 -Label 'trial with spaces'
$normalRc = $LASTEXITCODE
pwsh -NoProfile -File scripts/run.ps1 -Label 'failure trial' -Fail
$failureRc = $LASTEXITCODE
"normal=$normalRc failure=$failureRc"
```

预期为 0、7。第三种状态是参数错误：Linux 可运行 `bash scripts/run.sh 'invalid arguments' --unknown`，Python 会拒绝未知参数并返回 2，包装脚本仍保存独立日志。PowerShell 的入口只暴露已定义参数，因此对演示程序直接做独立参数故障实验：

```powershell
# Windows 本地 · PowerShell 7，项目根目录；每次生成不同日志名
$argumentLog = Join-Path 'logs' ('arguments-' + [guid]::NewGuid().ToString('N') + '.log')
& python scripts/demo.py --label test --unknown 2>&1 |
    Out-File -LiteralPath $argumentLog -Encoding utf8
$argumentRc = $LASTEXITCODE
"exit_code=$argumentRc" | Add-Content -LiteralPath $argumentLog -Encoding utf8
```

预期 `argumentRc` 为 2。这个故障日志只有参数诊断和退出码，不是完整实验记录，第五篇解析时不能补出缺失的成功字段。Shell 参数绑定失败也可能发生在脚本主体开始之前，因此没有日志文件不代表成功。

执行策略阻止可信本地脚本时，先用 `Get-ExecutionPolicy -List` 核对限制和组织要求，不直接修改整台机器策略。有限重复可用 Bash 的 `for trial in 1 2 3` 或 PowerShell 的 `foreach ($trial in 1..3)`；每次都检查状态，不因最后一轮成功便判定全批成功。

## 7. 脚本检查与故障定位

`bash -n scripts/run.sh` 只检查语法；`bash -x ...` 打印展开命令，可能泄露参数或密钥，调试前应去除敏感内容。ShellCheck 是额外静态工具，提供引号等线索，不能替代实际运行。

PowerShell 解析器可只检查语法：

```powershell
$parseTokens = $null
$parseErrors = $null
$scriptPath = (Resolve-Path -LiteralPath 'scripts/run.ps1').Path
$null = [Management.Automation.Language.Parser]::ParseFile(
    $scriptPath, [ref]$parseTokens, [ref]$parseErrors)
$parseErrors
```

无输出表示没有发现语法错误，文件权限和依赖尚未验证。

| 症状 | 检查与判断依据 | 处理 |
| --- | --- | --- |
| 失败运行却显示成功 | 状态是否在日志命令后读取 | 立即保存退出码，分别处理日志失败 |
| 标签或路径被拆开 | 参数元素数与引号 | 使用数组，不二次解释字符串 |
| 不同目录调用失败 | 是否依赖调用者目录 | 从脚本位置解析项目根目录 |
| 每轮日志覆盖 | 是否复用固定文件名 | 唯一标识加创建时禁止覆盖 |
| 程序找不到 | 实际解释器路径和依赖 | 核对来源，再安装匹配环境依赖 |

## 8. 命令速查与实践练习

| 目标 | Bash | PowerShell 7 |
| --- | --- | --- |
| 定位工具 | `command -v`、`type -a` | `Get-Command -All` |
| 参数数组 | `"${args[@]}"` | `@argumentArray` |
| 原生退出码 | `$?` | `$LASTEXITCODE` |
| 环境变量 | `export NAME=value` | `$env:NAME='value'` |
| 语法检查 | `bash -n` | `Parser::ParseFile` |
| 入口 | `bash scripts/run.sh` | `pwsh -NoProfile -File scripts/run.ps1` |

验收：正常、故意失败和参数错误各执行一次，产生三份不同日志、标签空格完整、状态分别为 0、7、2；从父目录调用仍写入项目 `logs/`；环境变量临时修改后恢复；日志写入失败时脚本不报告成功。

Windows PowerShell 7 入口、空格参数与正常/失败状态已实测；Bash 入口未在 Linux 主机执行。第三篇提供 C++ 计算程序，第六篇用独立跨平台驱动组织正式实验，不把本篇虚构数值混入性能样本。

## 9. 参考资料

- [Bash 管道](https://www.gnu.org/software/bash/manual/html_node/Pipelines)。
- [Bash 严格选项](https://www.gnu.org/software/bash/manual/html_node/The-Set-Builtin.html)。
- [PowerShell 自动变量](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_automatic_variables)。
- [PowerShell 管道](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_pipelines)。
- [PowerShell 重定向](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_redirection)。

上一篇：[终端环境与文件操作]({% post_url 2026-09-01-linux-terminal-common-commands %}) · 下一篇：[命令行构建与程序调试]({% post_url 2026-09-01-linux-command-line-development %})。
