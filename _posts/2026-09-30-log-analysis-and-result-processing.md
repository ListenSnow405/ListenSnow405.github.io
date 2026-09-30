---
layout: post
title: "日志分析与结果整理"
date: 2026-09-30 00:03:00 +0800
categories: [学习]
tags: [日志分析, Python, PowerShell, 数据校验, 终端实验系列]
excerpt: "从完整异常日志素材出发，建立明确字段与标识，校验缺失和重复记录，按唯一键关联 A/B 结果，并生成可复查的 TSV 与 JSON。"
series: terminal-lab
series_order: 5
---

几十次运行的日志里找到一个耗时很容易，确认这个耗时属于哪次输入、哪个版本和哪个阶段却更重要。如果失败记录被删除、缺失值被补成零，汇总表即使整齐，也可能给出错误结论。

本文是系列第五篇，需要理解文本查看和基本管道，不要求服务器、编译器或 GPU。日志生成机制见[第二篇]({% post_url 2026-09-30-shell-execution-and-scripting %})，测量设计放在[第六篇]({% post_url 2026-09-30-performance-experiments-and-diagnostics %})。Windows PowerShell 7 与 Linux Bash 共享同一份 Python 3 标准库解析器，分别用原生工具检索和浏览结果。

## 1. 日志格式与记录标识

### 原始证据与派生数据

原始日志保存程序输出、诊断和包装脚本记录，结构化表把这些内容按字段组织，汇总表再对有效记录计算摘要。派生文件可以重建，原始日志应保留，不能为了让解析成功而修改掉异常行。

本例每个 `.log` 对应一次运行。`run_id` 唯一标识运行，`case_id` 标识同一输入与配置；A/B 配对另用 `pair`，实际先后顺序用 `order`。文件行号可用于指出错误位置，不能用于关联不同运行。

| 字段 | 约定 |
| --- | --- |
| `run_id`、`case_id` | 使用字母、数字、下划线、点和连字符；不能用文件行号代替 |
| `started_at` | ISO 8601 时间，包含时区或 Z |
| `input_id`、`n`、`repeat` | 输入公式版本、规模、进程内计算次数 |
| `variant`、`threads`、`seed` | 实现名称、线程数、随机种子；无随机输入时固定记录 0 |
| `phase`、`pair`、`order` | warmup / aa / sample、配对轮次、全局执行顺序 |
| `correctness`、`exit_code` | 参考检查 pass/fail，包装脚本保存的真实退出码 |
| `metric`、`value`、`unit`、`scope` | 指标、数值、单位和计时范围，缺失值不可填成零 |

这里规定日志行是 `key=value`，只按第一个 `=` 分隔，空行和 `#` 注释行忽略，同一键不得重复。未知扩展键可保留在原始日志中；必填字段必须有值。程序的 `checksum` 是辅助核对字段，不是耗时。

机器、工具链、代码与资源状态保存在同一实验会话的 `metadata/`，由会话标识关联。日志字段齐全仍不等于环境记录完整，应一起保存源码、配置与资源说明。

## 2. 完整素材与独立准备

独立阅读时创建空 `terminal-lab` 与 `scripts/`。将下列生成器保存为 `scripts/make_fixtures.py`，在项目根目录运行；Windows 用 `python`，Linux 用 `python3`。它重新生成七份固定教学日志，已存在的同名素材会被覆盖，因此只在练习目录执行。

```python
from pathlib import Path

root = Path(__file__).resolve().parents[1] / "fixtures"
root.mkdir(exist_ok=True)
base = """run_id={run}
case_id=vector-small
started_at=2026-09-30T00:00:00+00:00
input_id=formula-v1
n=1003
repeat=2
threads=1
seed=0
variant={variant}
phase=sample
pair={pair}
order=1
correctness=pass
metric=compute_ms
value=1.25e-1
unit=ms
scope=compute-only
exit_code=0
"""
cases = {
    "01-A": base.format(run="r01", variant="A", pair=1),
    "02-B": base.format(run="r02", variant="B", pair=1).replace("1.25e-1", "0.10"),
    "03-failed": base.format(run="r03", variant="A", pair=2).replace("exit_code=0", "exit_code=7"),
    "04-missing": base.format(run="r04", variant="B", pair=2).replace("value=1.25e-1\n", ""),
    "05-duplicate": base.format(run="r05", variant="A", pair=3) + "value=0.2\n",
    "06-invalid": base.format(run="r06", variant="B", pair=3).replace("1.25e-1", "NaN"),
    "07-unmatched": base.format(run="r07", variant="A", pair=4),
}
for name, content in cases.items():
    # 只写本脚本约定的七份教学素材，重复执行会重建这些文件。
    (root / (name + ".log")).write_text(content, encoding="utf-8", newline="\n")
print(f"created {len(cases)} fixtures in {root}")
```

```powershell
# Windows 本地 · PowerShell 7，terminal-lab 根目录
python scripts/make_fixtures.py
Get-ChildItem -LiteralPath fixtures -File
```

```bash
# Linux · Bash，terminal-lab 根目录
python3 scripts/make_fixtures.py
find fixtures -type f -name '*.log'
```

也可逐份下载[素材目录中的配套文件说明]({{ '/assets/examples/terminal-lab/README.md' | relative_url }})。这些耗时是构造数据，专门用于校验解析行为，不能用于声称某实现更快。

| 素材 | 特征 | 预期分类 |
| --- | --- | --- |
| 01-A、02-B | 同一 pair 的正常 A/B | ok |
| 03-failed | 退出码 7，即使存在数值也不进入统计 | failed |
| 04-missing | 缺 value | missing |
| 05-duplicate | value 重复出现 | duplicate |
| 06-invalid | value 为 NaN | invalid |
| 07-unmatched | A 没有对应 B | 运行本身 ok，关联状态 unmatched |

## 3. 检索与上下文

检索用于找到候选证据，不等于格式校验。数值提取若只查找 `time`，可能混入初始化、传输、诊断或其他指标。

```powershell
# Windows 本地 · PowerShell 7
Get-ChildItem -LiteralPath fixtures -File -Filter '*.log' |
    Select-String -Pattern 'exit_code=' -SimpleMatch
Select-String -LiteralPath 'fixtures/05-duplicate.log' -Pattern '^value=' -Context 1,1
```

```bash
# Linux · Bash；rg 需已安装，grep 为另一工具路线
rg -n -F 'exit_code=' fixtures
grep -nE '^value=' fixtures/05-duplicate.log
grep -n -A1 -B1 -E '^value=' fixtures/05-duplicate.log
```

第一条检索应显示所有七个来源，重复素材应显示两条 value。`-F` 是字面匹配，`-E` 是扩展正则；PowerShell `Select-String` 默认使用正则，字面目标应加 `-SimpleMatch`。`grep -P` 是否可用取决于平台和构建，不能假定所有 grep 都支持 PCRE。

查不到时先检查搜索目录、文件编码与忽略规则。`rg` 默认忽略某些文件，不代表实验没有输出；需要扩大范围时应显式说明，而非直接将空结果归为成功。

## 4. 字段校验与状态分类

### 完整解析器

将下列完整代码保存为 `scripts/collect.py`；[配套解析器]({{ '/assets/examples/terminal-lab/scripts/collect.py' | relative_url }})无需第三方依赖。它支持有限的教学字段约定，不是任意应用日志的通用解析器。

```python
import argparse
import csv
import json
import math
import re
import statistics
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

FIELDS = "run_id case_id started_at input_id n repeat threads seed variant phase pair order correctness metric value unit scope exit_code".split()
NUMBER = re.compile(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?\Z")
IDENT = re.compile(r"[A-Za-z0-9_.-]+\Z")
SUMMARY_FIELDS = "case_id phase variant input_id n repeat threads seed metric unit scope".split()

def read_log(path):
    data, issues = {}, []
    for line_no, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        if not line or line.startswith("#"):
            continue
        key, separator, value = line.partition("=")
        if not separator or not IDENT.fullmatch(key):
            issues.append(f"malformed_line:{line_no}")
        elif key in data:
            issues.append(f"duplicate_key:{key}")
        else:
            data[key] = value
    issues += ["missing:" + key for key in FIELDS if not data.get(key)]
    for key in ("run_id", "case_id", "input_id", "variant"):
        if data.get(key) and not IDENT.fullmatch(data[key]):
            issues.append("invalid:" + key)
    for key in ("n", "repeat", "threads", "seed", "pair", "order", "exit_code"):
        if data.get(key):
            if not re.fullmatch(r"-?\d+", data[key]):
                issues.append("invalid:" + key)
            else:
                data[key] = int(data[key])
                minimum = 1 if key in ("n", "repeat", "threads", "pair", "order") else 0
                if key != "exit_code" and data[key] < minimum:
                    issues.append("invalid:" + key)
    if data.get("started_at"):
        try:
            if datetime.fromisoformat(data["started_at"].replace("Z", "+00:00")).tzinfo is None:
                raise ValueError("timezone missing")
        except ValueError:
            issues.append("invalid:started_at")
    value = data.get("value", "")
    numeric = None
    if value:
        if NUMBER.fullmatch(value) and math.isfinite(float(value)) and float(value) >= 0:
            numeric = float(value)
        else:
            issues.append("invalid:value")
    for key, choices in (("phase", ("warmup", "aa", "sample")),
                         ("correctness", ("pass", "fail")),
                         ("metric", ("compute_ms", "demo_value")),
                         ("unit", ("ms",)), ("scope", ("compute-only", "synthetic"))):
        if data.get(key) and data[key] not in choices:
            issues.append("invalid:" + key)
    failed = data.get("exit_code") != 0 or data.get("correctness") != "pass"
    if any(x.startswith("duplicate_key:") for x in issues):
        status = "duplicate"
    elif any(x.startswith(("invalid:", "malformed_line:")) for x in issues):
        status = "invalid"
    elif isinstance(data.get("exit_code"), int) and data["exit_code"] != 0:
        status = "failed"
    elif any(x.startswith("missing:") for x in issues):
        status = "missing"
    else:
        status = "failed" if failed else "ok"
    if failed:
        issues.append("run_failed_or_unconfirmed")
    return {**{k: data.get(k) for k in FIELDS}, "value": numeric if status == "ok" else None,
            "status": status, "issues": ";".join(issues), "source": path.name}

def analyze(rows):
    # 同一 run_id 的所有来源均标记重复，不能任意保留第一条或最后一条。
    counts = Counter(r["run_id"] for r in rows if r["run_id"])
    for r in rows:
        if r["run_id"] and counts[r["run_id"]] > 1:
            r.update(status="duplicate", value=None, issues=r["issues"] + ";duplicate_run_id")
    groups, pairs = defaultdict(list), defaultdict(list)
    for r in rows:
        if r["status"] == "ok" and r["phase"] in ("sample", "aa"):
            key = tuple(r[k] for k in SUMMARY_FIELDS)
            groups[key].append(r["value"])
        if r["phase"] == "sample" and r["variant"] in ("A", "B"):
            pairs[(r["case_id"], r["pair"])].append(r)
    summaries = []
    for key, values in sorted(groups.items()):
        center = statistics.median(values)
        summaries.append(dict(zip(SUMMARY_FIELDS, key),
                              count=len(values), median=center, min=min(values), max=max(values),
                              mad=statistics.median(abs(x - center) for x in values)))
    comparisons = []
    comparable = ("input_id", "n", "repeat", "threads", "seed", "metric", "unit", "scope")
    for (case_id, pair), records in sorted(pairs.items(), key=lambda x: str(x[0])):
        sides = {v: [r for r in records if r["variant"] == v] for v in ("A", "B")}
        result = dict(case_id=case_id, pair=pair, speedup_A_over_B=None,
                      sources=[r["source"] for r in records])
        if any(len(side) > 1 for side in sides.values()):
            result["status"] = "duplicate_pair"
        elif any(not side for side in sides.values()):
            result["status"] = "unmatched"
        else:
            a, b = sides["A"][0], sides["B"][0]
            if a["status"] != "ok" or b["status"] != "ok":
                result["status"] = "invalid_pair"
            elif any(a[k] != b[k] for k in comparable):
                result["status"] = "config_mismatch"
            elif a["value"] <= 0 or b["value"] <= 0:
                result["status"] = "nonpositive_time"
            else:
                result.update(status="ok", speedup_A_over_B=a["value"] / b["value"])
        comparisons.append(result)
    return {"counts": dict(Counter(r["status"] for r in rows)), "total": len(rows),
            "records": rows, "summary": summaries, "comparisons": comparisons}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input_dir", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    if not args.input_dir.is_dir():
        parser.error("input directory does not exist")
    report = analyze([read_log(p) for p in sorted(args.input_dir.glob("*.log"))])
    args.output_dir.mkdir(parents=True, exist_ok=True)
    # 派生结果允许覆盖，原始日志不修改；JSON 用 null 表示不可用数值。
    (args.output_dir / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    columns = FIELDS + ["status", "issues", "source"]
    with (args.output_dir / "runs.tsv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns, delimiter="\t")
        writer.writeheader()
        writer.writerows(report["records"])
    print(json.dumps({"total": report["total"], "counts": report["counts"]}))
    return 2 if args.strict and any(r["status"] != "ok" for r in report["records"]) else 0

if __name__ == "__main__":
    raise SystemExit(main())
```

逐行校验避免“提取到了一个数字”就认为运行有效。数字规则接受科学计数法，拒绝 NaN、Inf、非法尾随内容和负耗时；整数配置、时区与枚举字段也检查。格式异常全部写入 `issues`，失败样本的数值在派生结果中置为 null，原始日志仍保存。

状态分类按重复、非法、明确非零退出、缺失、其余失败或正常的顺序决定主状态，多种问题并存时通过 issues 保留。跨文件重复 `run_id` 的所有记录均标记重复，不任意选择第一条或最后一条。没有完整成功判据时不会作为有效样本。

### 运行与计数验收

```powershell
# Windows 本地 · PowerShell 7
python scripts/collect.py fixtures results/fixtures
$collectRc = $LASTEXITCODE
$report = Get-Content -LiteralPath 'results/fixtures/report.json' -Raw -Encoding utf8 | ConvertFrom-Json
$report.counts
```

```bash
# Linux · Bash
python3 scripts/collect.py fixtures results/fixtures
cat results/fixtures/runs.tsv
```

预期 `total=7`，ok 3、failed 1、missing 1、duplicate 1、invalid 1。普通模式退出 0 表示整理成功，不表示所有实验成功；加入 `--strict` 时，任何异常记录使解析器返回 2，便于批处理阻止继续发布摘要。

目录为空时输出总数 0 和空摘要，不调用空数组中位数；缺少输入目录则直接报参数错误。数量对账必须同时看输入运行数、状态计数与最终总数，不能只数有效行。

## 5. 排序、分组与关联

### 文本数值与对象属性

字符串排序会把 `100` 排在 `20` 前。PowerShell 从 JSON 读取的有效 value 为数值，可直接排序；TSV 导入字段通常是字符串，需先检查状态再转换：

```powershell
$rows = Import-Csv -LiteralPath 'results/fixtures/runs.tsv' -Delimiter "`t" -Encoding utf8
$valid = $rows | Where-Object { $_.status -eq 'ok' }
$valid | Sort-Object { [double]::Parse($_.value, [Globalization.CultureInfo]::InvariantCulture) } |
    Select-Object run_id, variant, value
$rows | Group-Object status | Select-Object Name, Count
```

InvariantCulture 避免本地小数符号约定改变解析。Linux 的简单 TSV 查看可用：

```bash
# 本例 TSV 没有字段内 Tab 或换行；列号来自本篇固定表头
head -n 1 results/fixtures/runs.tsv
awk -F '\t' 'NR > 1 && $19 == "ok" {print $1, $15}' results/fixtures/runs.tsv
```

`awk` 三参数 `match`、`gensub`、`asort` 等可能是 gawk 扩展，不能直接承诺其他实现可用。`awk --version` 也不是所有实现的通用探测方式；需要扩展时明确调用并核对 `gawk`。上述最小例子不使用这些扩展。

### 唯一键与完整关联

不能用 `paste` 按行拼接 A/B：失败缺行或排序变化会将不同运行并排。解析器按 `(case_id, pair)` 关联正式样本，先检查每侧唯一性，再核对输入、规模、重复数、线程数、种子、指标、单位和计时范围。摘要也将这些配置作为分组条件，即使误用了相同 case_id，不同配置也不会被合成一个中位数。

本例四个 pair 的预期结果为：1 正常，2 invalid_pair，3 invalid_pair，4 unmatched。重复配对键标为 duplicate_pair；配置不同标为 config_mismatch；计时为零不能作为加速比除数。未匹配和异常记录全部出现在 comparisons，不能用只保留交集的关联掩盖缺失。

正常配对的 `speedup_A_over_B = time_A / time_B`，大于 1 表示 B 用时较少。素材中的 1.25 只是构造数据的计算结果，不能扩展成真实优化结论。中位数和 MAD 属于描述性摘要，因果结论需要第六篇的实验设计。

## 6. JSON、TSV 与比较范围

JSON 保留数字和 null，TSV 用空字段表示不可用数值。两者都可再次读取，而 `Format-Table`、`column -t` 只是人类浏览方式，不是数据保存格式。

```powershell
# Windows 本地 · PowerShell 7：导出可再次读取的 CSV
$report.records | Export-Csv -LiteralPath 'results/fixtures/runs.csv' -NoTypeInformation -Encoding utf8
Import-Csv -LiteralPath 'results/fixtures/runs.csv' -Encoding utf8 |
    Group-Object status | Select-Object Name, Count
```

Linux 如安装 jq，可用 `jq '.counts, .comparisons' results/fixtures/report.json` 查看结构。一般 CSV 含有引号、逗号和字段内换行，应使用 CSV 解析库；`cut -d,`、简单 `split(',')` 不足以解析这些格式。

文件比较有三个层级：字节相同可比较 SHA-256 或用 `cmp`；文本等价可按明确编码解码并约定换行处理；数值正确应使用算法需要的容差。PowerShell `Compare-Object` 比较对象内容，不是通用二进制逐字节比较。JSON 对象属性顺序、BOM 和换行不同，不必导致结构化数据不等价。

二进制诊断只需最小入口：Linux `file`、`od -An -tx1`，Windows `Format-Hex`，查看文件头是否与期望格式一致。不要把可执行文件中的字符串当作完整版本来源证明。

## 7. 规模与内存限制

解析器逐文件读取，但最终仍把全部记录、分组数值和报告放在内存中，适合教学与中小实验集合。对象和字符串占用往往大于文件字节数，不能仅根据日志大小推断内存需求。

规模增大时可逐行读取原始日志、输出 JSON Lines 或批量写入 SQLite；精确中位数仍需保留相关样本或采用外部排序。分块不能随意把各块中位数再求中位数当作总体中位数。切换近似算法应记录误差与方法，而不是默默改变统计含义。

## 8. 常见问题与命令速查

| 症状 | 检查与判断依据 | 处理 |
| --- | --- | --- |
| 数值为空 | 字段是否缺失、格式规则是否匹配 | 保留 missing/invalid，不补零 |
| 日志有两条相同键 | 重复键与原始来源 | 标记 duplicate，核对产生原因 |
| A/B 数量不等 | 唯一键、失败和未匹配项 | 完整关联，保留未匹配 |
| 科学计数法排序错误 | 数据是否仍为字符串 | 校验后按数值排序 |
| 表格很整齐却无法读取 | 是否保存了显示结果 | 使用 CSV/TSV/JSON 序列化 |

| 阶段 | 入口 |
| --- | --- |
| 检索 | `rg -nF`、`grep -nE`、`Select-String` |
| 字段查看 | 简单 TSV 的 `awk`、`cut`；PowerShell 对象属性 |
| 校验 | `collect.py`、`--strict`、状态计数 |
| 排序与分组 | `Sort-Object`、`Group-Object`、明确数值规则 |
| 输出与查看 | `Export-Csv`、`ConvertFrom-Json`、`jq` |
| 比较 | SHA-256、`cmp`、解码后的文本或数值容差 |

## 9. 实践练习与验证范围

验收：七份日志得到约定计数，原件未修改；四个配对保留正常、异常和未匹配状态；复制一份日志后所有相同 run_id 均标记重复；空目录输出空摘要；将某个 B 的单位改为不支持单位时标为非法，不进入比较。偶数样本中位数取中间两值平均，不能任意取其中一个。

Python 3 解析、异常素材、空样本、重复标识与关联检查在 Windows 实测，PowerShell 结果读取也已验证。Linux Shell 检索未实测；共享解析器的语义结果可比较，不要求两端 BOM、换行和文件字节完全一致。

## 10. 参考资料

- [Python CSV](https://docs.python.org/3/library/csv.html)。
- [Python statistics](https://docs.python.org/3/library/statistics.html)。
- [GNU awk 手册](https://www.gnu.org/software/gawk/manual/gawk.html)。
- [GNU grep 手册](https://www.gnu.org/software/grep/manual/grep.html)。
- [jq 手册](https://jqlang.org/manual/)。

上一篇：[远程开发与任务管理]({% post_url 2026-09-30-remote-development-and-task-management %}) · 下一篇：[性能实验与诊断工具]({% post_url 2026-09-30-performance-experiments-and-diagnostics %})。
