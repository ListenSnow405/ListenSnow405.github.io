---
layout: post
title: "性能实验与诊断工具"
date: 2026-09-30 00:04:00 +0800
categories: [学习]
tags: [性能实验, 基准测试, Nsight, 可复现性, 终端实验系列]
excerpt: "以同一向量计算任务组织 CPU 对照实验，记录环境、预热、A/A 与平衡顺序，检查原始样本和离散程度，再按问题选择诊断工具。"
series: terminal-lab
series_order: 6
---

一次运行更快，可能来自代码变化，也可能来自缓存、频率、后台负载或测量范围变化。可靠的性能实验要先明确比较对象和正确性，再组织原始样本，最后用诊断证据解释变化。

本文是系列第六篇，需要能[构建并验证程序]({% post_url 2026-09-01-linux-command-line-development %})，并理解[日志整理]({% post_url 2026-09-30-log-analysis-and-result-processing %})。CPU 实验是主线，Windows PowerShell 7 与 Linux Bash 共享 Python 3 驱动；GPU 工具属于需要设备与权限的扩展，不要求读者有 GPU 才能完成本文。

## 1. 测量范围与正确性

### 总耗时与阶段耗时

第三篇程序计算 `3*a+2*b`，A 为两个循环，B 为融合循环。两者同输入、同参考规则、同输出要求。错误程序即使更快也没有比较价值，正式测量前必须通过 CTest 和逐元素检查。

| 指标 | 包含内容 | 本例用途 |
| --- | --- | --- |
| 进程总耗时 | 启动、分配、初始化、计算、校验、输出及退出 | 观察用户等待或任务总成本 |
| `compute_ms` | 单次 compute 调用，多次调用耗时的平均 | 比较本例 CPU 计算阶段 |
| GPU kernel 时间 | 设备上指定核函数区间，需正确同步 | GPU 扩展实验，不能用 Shell 时间替代 |
| 端到端耗时 | 明确定义的输入准备、传输、计算与结果获取 | 必须按任务边界记录 |

Linux 的 Bash `time` 可以计整个命令或管道；GNU 外部 `/usr/bin/time` 另有资源报告，选项不是 Bash 关键字的同一接口：

```bash
# Linux · Bash，项目根目录；/usr/bin/time 需已安装 GNU time
/usr/bin/time -f 'elapsed_s=%e max_rss_kib=%M' \
  ./build-release/vector_lab 1000000 B 10
```

```powershell
# Windows 本地 · PowerShell 7，MSVC Release 程序
$elapsed = Measure-Command {
    & ./build-release/vector_lab.exe 1000000 B 10 | Out-Null
    $script:measuredRc = $LASTEXITCODE
}
$elapsed.TotalMilliseconds
$measuredRc
```

这两者范围不完全相同：PowerShell 示例包含脚本块和管道开销，并丢弃显示输出，但程序仍执行输出动作。它们用于明确总成本，不进入 compute-only 的加速比。GNU time 的峰值 RSS 单位应按实际实现核对，也不能直接与另一平台的不同内存指标同列比较。

## 2. 环境与资源控制

### Release 构建与来源

独立阅读时先按第三篇创建完整源码和 CMake 文件，再创建 Release 构建目录。本文 Windows 路线使用已初始化 MSVC 的 Developer PowerShell：

```powershell
cmake -S . -B build-release -G 'NMake Makefiles' -DCMAKE_BUILD_TYPE=Release
cmake --build build-release
ctest --test-dir build-release --output-on-failure
Get-FileHash -LiteralPath 'build-release/vector_lab.exe' -Algorithm SHA256
```

```bash
# Linux · Bash，独立的本机 Release 目录
cmake -S . -B build-release -G 'Unix Makefiles' -DCMAKE_BUILD_TYPE=Release
cmake --build build-release --parallel 2
ctest --test-dir build-release --output-on-failure
sha256sum build-release/vector_lab
```

每一步检查成功后继续；多配置生成器须改用 `--config Release` 与 `ctest -C Release`，并调整程序路径。Debug、Sanitizer、Profiler 产物与普通 Release 计时分组保存，不能混为同一构建配置。

### 环境快照与输入身份

记录主机、系统、CPU 型号、线程数、编译器、配置、Shell、Python 和代码状态。Windows 可用 `Get-CimInstance Win32_Processor | Select-Object Name, NumberOfCores, NumberOfLogicalProcessors`；Linux 用 `lscpu`。GPU 扩展还记录 UUID、驱动、Toolkit、可见设备和资源分配，查询入口见[第四篇]({% post_url 2026-09-30-remote-development-and-task-management %})。

本例没有外部数据文件，输入身份由 `formula-v1`、N 和种子 0 描述；使用真实输入时应保存路径、版本与 SHA-256。记录 `git rev-parse HEAD`、`git status --short`、`git diff HEAD --` 和未跟踪文件列表；有修改时必须另存差异及必要未跟踪源码，提交号不能代表全部源码。

CPU 亲和性可以减少部分调度变化，Linux 的 `taskset -c 实际CPU编号 ...`、NUMA 的 `numactl` 是可选入口，需先查看分配的 CPU 集合与内存节点，不能随意选择编号 0。固定亲和性也不能消除频率、温度和内存带宽干扰。本例先记录默认条件，不为了获得一个更小数字随意改变机器全局缓存或频率设置。

## 3. 预热、A/A 与重复实验

### 实验目标

冷启动和稳定重复计算是不同问题。预热可能减少初始化影响，也可能改变缓存和温度；每次新进程中的上下文初始化未必能由另一个进程的预热消除。必须声明要测哪一种行为。

本例的 compute-only 测量排除进程启动，但每次进程内第一轮计算仍包含在平均值中；校验在轮次之间读取数据。驱动的 warmup 只是先运行并保存独立进程样本，不保证之后每个进程完全无冷启动效应。若需要只统计进程内稳定轮次，应修改程序显式区分内部预热并记录新范围，不能偷偷丢掉首轮。

### 实验规则

在查看结果之前确定 N、进程内重复数、预热次数、A/A 和 A/B 配对数、超时以及有效样本规则。示例的 2 次预热、4 对 A/A、10 对 A/B 用于演示流程，不是所有实验的充分样本数。

A/A 让同一 A 连续运行两次，观察环境噪声；A/B 采用奇数轮 AB、偶数轮 BA，保留配对和全局顺序，降低总是后运行某一版本造成的偏差。这是交错且平衡的顺序，不称为拉丁方，也不消除所有长期漂移。若改用随机顺序，应保存随机种子和实际顺序。

失败、错误结果、配置不一致和不可用测量必须排除在性能摘要之外，但原始记录仍保留。资源冲突等额外作废规则应事先定义并有证据；不能在看到慢样本后才决定它“异常”。程序确定性操作次数与硬件计数器也不同，后者可能受调度、复用和共享资源影响。

## 4. 对照运行与结果汇总

### 完整驱动

项目中先保存第五篇的 `scripts/collect.py`，再把下面完整驱动保存为 `scripts/benchmark.py`；[配套文件]({{ '/assets/examples/terminal-lab/scripts/benchmark.py' | relative_url }})依赖 Python 3 和已构建程序。它复用第二篇的参数数组、真实退出码和禁止日志覆盖的原则；正式运行没有使用 demo 的虚构指标。

```python
import argparse
import hashlib
import json
import platform
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("executable", type=Path)
parser.add_argument("--n", type=int, default=1000000)
parser.add_argument("--repeat", type=int, default=10)
parser.add_argument("--pairs", type=int, default=10)
parser.add_argument("--aa-pairs", type=int, default=4)
parser.add_argument("--warmups", type=int, default=2)
parser.add_argument("--timeout", type=float, default=60)
args = parser.parse_args()
if not (1 <= args.n <= 10000000 and 1 <= args.repeat <= 10000 and
        1 <= args.pairs <= 1000 and 1 <= args.aa_pairs <= 1000 and
        0 <= args.warmups <= 100 and args.timeout > 0):
    parser.error("invalid experiment bounds")
exe = args.executable.resolve(strict=True)
root = Path(__file__).resolve().parents[1]
session = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S") + "-" + uuid.uuid4().hex[:8]
log_dir = root / "logs" / session
log_dir.mkdir(parents=True, exist_ok=False)
meta_dir = root / "metadata" / session
meta_dir.mkdir(parents=True, exist_ok=False)

def git_output(*arguments):
    # 错误也保留，不把不在仓库中的项目伪装成干净提交。
    result = subprocess.run(["git", *arguments], cwd=root, capture_output=True, text=True,
                            encoding="utf-8", errors="replace", check=False)
    return {"exit_code": result.returncode, "output": result.stdout, "error": result.stderr}

try:
    git = {"head": git_output("rev-parse", "HEAD"),
           "status": git_output("status", "--porcelain=v1"),
           "diff": git_output("diff", "HEAD", "--"),
           "untracked": git_output("ls-files", "--others", "--exclude-standard")}
except FileNotFoundError:
    git = {"error": "git executable unavailable"}
metadata = {"session": session, "hostname": platform.node(), "platform": platform.platform(),
            "python": sys.version, "executable": str(exe),
            "binary_sha256": hashlib.sha256(exe.read_bytes()).hexdigest(),
            "arguments": {k: str(v) if isinstance(v, Path) else v for k, v in vars(args).items()},
            "git": git,
            "limits": "补充 CPU 型号、编译器/配置、Shell、资源分配和源码快照；自动记录并不完整。"}
(meta_dir / "environment.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
case_id = f"formula-v1-n{args.n}-r{args.repeat}-t1"
order = 0
failed = False

def run(variant, phase, pair):
    global order, failed
    order += 1
    run_id = session + "-" + f"{order:04d}"
    command = [str(exe), str(args.n), variant, str(args.repeat)]
    header = f"run_id={run_id}\ncase_id={case_id}\nstarted_at={datetime.now(timezone.utc).isoformat()}\nphase={phase}\npair={pair}\norder={order}\n"
    try:
        result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8",
                                errors="strict", timeout=args.timeout, check=False)
        body, code = result.stdout, result.returncode
        body += "".join("# stderr: " + line + "\n" for line in result.stderr.splitlines())
    except subprocess.TimeoutExpired:
        body, code = "# error: timeout; no complete result\n", 124
    with (log_dir / (run_id + ".log")).open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(header + body + f"exit_code={code}\n")
    failed = failed or code != 0
    print(f"{order}: {phase} {variant} exit={code}")

for pair in range(1, args.warmups + 1):
    for variant in ("A", "B"):
        run(variant, "warmup", pair)
for pair in range(1, args.aa_pairs + 1):
    # 两次都是 A，通过 order 保留先后；第五篇只按 sample 做 A/B 关联。
    run("A", "aa", pair)
    run("A", "aa", pair)
for pair in range(1, args.pairs + 1):
    for variant in (("A", "B") if pair % 2 else ("B", "A")):
        run(variant, "sample", pair)
print(f"log_dir={log_dir}\nmetadata_dir={meta_dir}")
raise SystemExit(1 if failed else 0)
```

驱动以参数列表运行程序，不经 Shell 二次解释；每次保存唯一 run_id、phase、pair、order 和真实退出码。超时记录 124，并将未完整结果归为失败。无法启动程序、读取或写入文件等驱动级错误会中止流程，应连同现存日志保留，不能伪造剩余样本。

自动 metadata 包含程序哈希、系统、Python 与 Git 信息，**仍需补充 CPU 型号、Shell、编译器/配置、资源分配与源码快照**。未跟踪列表不是未跟踪文件内容的备份。Git 记录不应包含密钥等敏感文件；提交和清单选择仍由项目维护者负责。

**Windows 本地 · PowerShell 7**：

```powershell
python scripts/benchmark.py build-release/vector_lab.exe --n 1000000 --repeat 10 --pairs 10 --aa-pairs 4 --warmups 2
$batchRc = $LASTEXITCODE
```

**Linux · Bash**：

```bash
python3 scripts/benchmark.py build-release/vector_lab --n 1000000 --repeat 10 --pairs 10 --aa-pairs 4 --warmups 2
batch_rc=$?
```

预期共 32 份日志：4 份 warmup、8 份 aa、20 份 sample。末尾输出实际日志目录和 metadata 目录。使用这次输出的目录整理，不从所有历史会话中任意混合样本：

```powershell
# Windows：将下面路径替换成驱动实际输出的会话目录
$sessionLogs = 'logs/实际会话标识'
python scripts/collect.py $sessionLogs results/bench --strict
$report = Get-Content -LiteralPath 'results/bench/report.json' -Raw -Encoding utf8 | ConvertFrom-Json
$report.summary | Format-Table
$report.comparisons | Format-Table
```

Linux 对应 `python3 scripts/collect.py logs/实际会话标识 results/bench --strict`，这是必须替换路径的模板。摘要展示 count、median、min、max、MAD；warmup 不进入摘要，A/A 与 sample 分开，只有 sample 做 A/B 关联。

### A/A 噪声与加速比

以下保存为独立 `scripts/inspect_noise.py`，从项目根目录读取上述整理结果。它处理空样本、失败样本和偶数样本：

```python
import json
import statistics
from collections import defaultdict
from pathlib import Path

report = json.loads(Path("results/bench/report.json").read_text(encoding="utf-8"))
pairs = defaultdict(list)
for row in report["records"]:
    if row["phase"] == "aa":
        pairs[(row["case_id"], row["pair"])].append(row)
deltas = []
for key, rows in pairs.items():
    rows.sort(key=lambda r: r["order"])
    if len(rows) != 2 or any(r["status"] != "ok" for r in rows):
        print("invalid A/A pair", key)
        continue
    first, second = (r["value"] for r in rows)
    if first <= 0:
        print("nonpositive A/A time", key)
        continue
    deltas.append((second - first) / first)
print("A/A signed relative differences:", deltas)
print("A/A median absolute difference:",
      statistics.median(abs(x) for x in deltas) if deltas else None)
ratios = [r["speedup_A_over_B"] for r in report["comparisons"] if r["status"] == "ok"]
print("paired A/B speedups:", ratios)
print("median paired speedup:", statistics.median(ratios) if ratios else None)
```

加速比定义为 A 时间除以 B 时间，大于 1 表示 B 更快；配对比值中位数与“两个独立中位数相除”不是同一个统计量。MAD 是样本对中位数绝对偏差的中位数，不是置信区间。若 A/B 差异与 A/A 波动相近，应增加证据或报告结果不确定，不引用无出处的固定噪声百分比。

## 5. 诊断工具与性能证据

### CPU 最小入口

问题是运行时间长，先看阶段与资源；问题是崩溃，先做调试和正确性检查。Linux 可使用 `perf stat -- ./build-release/vector_lab 1000000 B 10` 查看可用计数器；权限或事件不支持时保留错误，不默认 sudo。`perf record` 则用于热点采样，需要匹配符号和报告解释，不能仅以一次计数断言瓶颈。

Windows 可用系统性能监视器或 Windows Performance Recorder 做采集，工具安装、配置与权限不同；不制造与 perf 完全等价的命令。本篇不声称完成这两端的硬件计数器分析。

### GPU 扩展入口

GPU 程序采用既有[开发环境与第一个核函数]({% post_url 2026-09-27-gpu-development-first-kernel %})中的向量加法案例，完整源码和构建前提见该篇；本系列 CPU 程序不能直接拿给 CUDA 工具产生核函数报告。计时同步与传输范围见[性能测量与瓶颈分析]({% post_url 2026-09-28-gpu-performance-measurement-and-bottleneck-analysis %})。

先在独立 GPU 练习目录编译并通过参考结果，再核对工具版本：

```bash
# Linux GPU 扩展 · Bash；以下程序路径需按 GPU 教程实际产物替换
compute-sanitizer --version
nsys --version
ncu --version
```

依次按问题选工具，下面是 **占位命令模板**，`./vector_add` 换成实际验证通过的程序；在 Windows PowerShell 中使用对应 `.exe` 路径。

```bash
compute-sanitizer --tool memcheck ./vector_add
nsys profile --trace=cuda,nvtx --sample=none -o results/vector-timeline ./vector_add
ncu --set basic --launch-count 1 -o results/vector-kernel ./vector_add
```

运行前创建 `results/`，报告前缀不能与已有结果冲突。Compute Sanitizer 检查访问问题；Nsight Systems 用时间线观察 API、传输、同步和 kernel 的关系；Nsight Compute 深入目标 kernel 指标，`--launch-count 1` 只限制采集次数，不保证第一核函数就是所需对象，实际程序应结合过滤和范围选择。

诊断可能引入探针、重放、串行化与缓存处理，改变原程序运行条件。带 profiler 的耗时不直接进入正常 A/B；`-lineinfo` 与 Sanitizer 对性能的影响也不能给出统一倍数。权限不足、工具缺失或没有报告时，只能记录采集失败，不声称已有时间线验证。

## 6. 实验记录与结论限制

完整交付至少包括：源码和配置快照、输入身份、二进制哈希、环境与资源说明、全部命令参数、运行顺序、原始日志、整理脚本和结果、异常原因及实际诊断报告。自动脚本完成其中一部分，需要人工补全其余信息。

对比时先核对有效样本数和正确性，再看范围和单位，最后解释摘要、配对变化与离散程度。单台 Windows CPU 的结果只说明这台机器和配置下的行为，不能推广到 Linux 服务器或 CUDA。没有完成 GPU 采集，就不把 CPU 正确性测试表述为 GPU Profiler 验证。

## 7. 常见问题与命令速查

| 症状 | 检查与判断依据 | 处理 |
| --- | --- | --- |
| 最快值好看但多数样本不稳定 | 全部样本、顺序与 A/A | 报告离散程度，不只保留最佳值 |
| 第一轮偏慢 | 是否包含启动、初始化或冷缓存 | 先确定目标，再定义预热规则 |
| A/B 配置不同 | 输入、重复数、线程数和范围 | 分组或重新实验，不强行计算比值 |
| profiler 运行变慢 | 探针、重放和诊断选项 | 普通计时与采集分开 |
| 报告为空或权限不足 | 工具状态、输出文件和限制 | 保存失败原因，按环境规则处理 |

| 目标 | 入口 |
| --- | --- |
| CPU 总耗时 | GNU `/usr/bin/time`、PowerShell `Measure-Command` |
| 环境与来源 | `lscpu` / `Get-CimInstance`、Git 状态、SHA-256 |
| 正式样本 | `benchmark.py` 的 phase/pair/order |
| 校验与汇总 | `collect.py --strict`、JSON 原始记录与摘要 |
| CPU 诊断 | Linux `perf`，Windows 系统采集工具 |
| GPU 诊断 | Compute Sanitizer、nsys、ncu |

## 8. 实践练习与验证范围

验收：A/B 均通过参考验证，32 份记录与计划一致，预热、A/A 和正式样本分开；所有正式配对输入、单位和计时范围一致；失败记录不能进入摘要；能够从 run_id 找到原始日志并解释加速比方向。

本文 CPU 驱动与整理流程在 Windows MSVC Release 程序上实测，只验证运行契约与样本组织，不给出跨机器性能排名。Linux CPU 流程、硬件计数器与本篇 GPU 采集未执行，报告须由读者在满足前提的环境中实际生成。

## 9. 参考资料

- [Python subprocess](https://docs.python.org/3/library/subprocess.html)。
- [Python statistics](https://docs.python.org/3/library/statistics.html)。
- [GNU time](https://www.gnu.org/software/time/)。
- [Linux perf 文档](https://www.kernel.org/doc/html/latest/admin-guide/perf-security.html)。
- [Compute Sanitizer](https://docs.nvidia.com/compute-sanitizer/ComputeSanitizer/index.html)。
- [Nsight Systems 用户指南](https://docs.nvidia.com/nsight-systems/UserGuide/)。
- [Nsight Compute 分析指南](https://docs.nvidia.com/nsight-compute/ProfilingGuide/)。

上一篇：[日志分析与结果整理]({% post_url 2026-09-30-log-analysis-and-result-processing %}) · [返回系列导读]({{ '/series/' | relative_url }}#terminal-lab)。
