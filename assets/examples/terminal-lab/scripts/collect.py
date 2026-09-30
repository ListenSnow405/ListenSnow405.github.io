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
