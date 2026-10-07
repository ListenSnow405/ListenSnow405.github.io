"""D9 离线评分与消耗汇总；不调用模型、不读取密钥，不实施修订。"""
import argparse
import json
import math
import statistics
from collections import Counter
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("JSON 对象包含重复键")
        result[key] = value
    return result


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"), object_pairs_hook=unique_object)


def score(raw, gold):
    """精确类型、标识集合和必要定位分别检查；最终判断仍需人工复核。"""
    errors = []
    try:
        actual = json.loads(raw, object_pairs_hook=unique_object)
    except (ValueError, TypeError):
        return {"automatic_pass": False, "errors": ["json_parse"]}
    if type(actual) is not dict or set(actual) != {"case_id", "outcome", "reason", "records"}:
        return {"automatic_pass": False, "errors": ["schema"]}
    for key in ("case_id", "outcome", "reason"):
        if type(actual[key]) is not type(gold[key]) or actual[key] != gold[key]:
            errors.append("outcome" if key != "case_id" else "schema")
    rows = actual["records"]
    if type(rows) is not list:
        return {"automatic_pass": False, "errors": sorted(set(errors + ["schema"]))}
    expected = {r["record_id"]: r for r in gold["records"]}
    found = {}
    for row in rows:
        if type(row) is not dict or set(row) != {"record_id", "value", "unit", "state", "source_refs"}:
            errors.append("schema")
            continue
        rid = row["record_id"]
        if type(rid) is not str or rid in found or rid not in expected:
            errors.append("coverage")
            continue
        found[rid] = row
        ref = expected[rid]
        for key in ("value", "unit", "state"):
            # bool 是 int 的子类，所以不能只使用 isinstance 或 ==。
            if type(row[key]) is not type(ref[key]) or row[key] != ref[key]:
                errors.append("fact")
        refs = row["source_refs"]
        if (type(refs) is not list or any(type(x) is not str for x in refs)
                or len(refs) != len(set(refs)) or set(refs) != set(ref["source_refs"])):
            errors.append("evidence")
    if set(found) != set(expected):
        errors.append("coverage")
    return {"automatic_pass": not errors, "errors": sorted(set(errors))}


def token_cost(attempt, rates):
    """四类输入/输出互斥计价；缺失用量返回 None，不能当作零。"""
    keys = ("input_tokens", "cached_input_tokens", "cache_write_input_tokens", "output_tokens")
    values = [attempt.get(key) for key in keys]
    if any(x is None for x in values):
        return None
    if any(type(x) is not int or x < 0 for x in values):
        raise ValueError("token 用量须为非负整数或 null")
    total, cached, written, output = values
    if cached + written > total:
        raise ValueError("缓存读取和写入不能超过总输入")
    if any(not Decimal(str(v)).is_finite() or Decimal(str(v)) < 0 for v in rates.values()):
        raise ValueError("单价须为有限非负数")
    ordinary = total - cached - written
    return (Decimal(ordinary) * Decimal(str(rates["input"]))
            + Decimal(cached) * Decimal(str(rates["cached_input"]))
            + Decimal(written) * Decimal(str(rates["cache_write_input"]))
            + Decimal(output) * Decimal(str(rates["output"]))) / Decimal(1000000)


def checked_trials(data, plan):
    """分母来自冻结计划；缺少、重复或额外运行直接报错，避免悄悄删掉失败。"""
    expected = {(v, c["id"], n) for v in plan["variants"] for c in plan["cases"]
                for n in range(1, plan["repeats"] + 1)}
    seen = set()
    for trial in data["trials"]:
        key = (trial["variant"], trial["case_id"], trial["repeat"])
        if key not in expected or key in seen:
            raise ValueError("运行标识重复或不在计划中: " + str(key))
        seen.add(key)
        if not trial["attempts"]:
            raise ValueError("必须保留尝试，未调用的样例也须记录阻断事件")
        seconds = trial["wall_seconds"]
        if type(seconds) not in (int, float) or not math.isfinite(seconds) or seconds < 0:
            raise ValueError("wall_seconds 须为有限非负数")
    if seen != expected:
        raise ValueError("运行矩阵不完整: " + str(sorted(expected - seen)))
    return data["trials"]


def summarize(trials, reference, prices, plan):
    details, groups = [], []
    split = {c["id"]: c["split"] for c in plan["cases"]}
    for trial in checked_trials({"trials": trials}, plan):
        gold = reference[trial["case_id"]]
        attempts = trial["attempts"]
        first = score(attempts[0]["raw_output"], gold)
        final = score(attempts[-1]["raw_output"], gold)
        model_calls = sum(a["stage"] == "model" for a in attempts)
        # 内容正确不能抵消过程违规；本例的来源失败由工作流阻断。
        process_bad = (any(a["stage"] not in ("model", "read") for a in attempts)
                       or (gold["outcome"] == "blocked" and model_calls != 0)
                       or (gold["outcome"] == "completed" and model_calls == 0)
                       or model_calls > min(plan["budget"]["max_model_calls_per_task"], 2 if trial["variant"].endswith("W1") else 1)
                       or trial["wall_seconds"] > plan["budget"]["max_wall_seconds"]
                       or (model_calls == 2 and not attempts[-1].get("feedback")))
        if process_bad:
            final = {"automatic_pass": False, "errors": sorted(set(final["errors"] + ["process"]))}
        costs = [token_cost(a, prices["per_million"]) for a in attempts]
        tools = [a.get("tool_cost") for a in attempts]
        for value in tools:
            if value is not None and (type(value) not in (int, float) or not math.isfinite(value) or value < 0):
                raise ValueError("tool_cost 须为有限非负数或 null")
        known_cost = sum((c for c in costs if c is not None), Decimal(0))
        token_complete = all(c is not None for c in costs)
        full = token_complete and all(t is not None for t in tools)
        details.append({"variant": trial["variant"], "case_id": trial["case_id"],
                        "repeat": trial["repeat"], "split": split[trial["case_id"]],
                        "first_pass": first["automatic_pass"], **final,
                        "first_errors": first["errors"], "attempts": len(attempts),
                        "model_calls": model_calls,
                        "correct_block": gold["outcome"] == "blocked" and final["automatic_pass"],
                        "wall_seconds": trial["wall_seconds"],
                        "token_estimate": float(known_cost) if token_complete else None,
                        "known_token_subtotal": float(known_cost),
                        "total_estimate": float(known_cost + sum(Decimal(str(t)) for t in tools)) if full else None,
                        "human_review": "pending"})
    for variant in plan["variants"]:
        rows = [r for r in details if r["variant"] == variant]
        passed = sum(r["automatic_pass"] for r in rows)
        token_complete = all(r["token_estimate"] is not None for r in rows)
        token_total = float(sum((Decimal(str(r["token_estimate"])) for r in rows), Decimal(0))) if token_complete else None
        groups.append({"variant": variant, "tasks": len(rows), "first_pass": sum(r["first_pass"] for r in rows),
                       "final_pass": passed, "correct_blocks": sum(r["correct_block"] for r in rows),
                       "model_calls": sum(r["model_calls"] for r in rows),
                       "median_wall_seconds": statistics.median(r["wall_seconds"] for r in rows),
                       "token_estimate": token_total,
                       "token_cost_per_correct_task": token_total / passed if token_total is not None and passed else None,
                       "total_estimate": float(sum((Decimal(str(r["total_estimate"])) for r in rows), Decimal(0))) if all(r["total_estimate"] is not None for r in rows) else None,
                       "by_split": {s: {"passed": sum(r["automatic_pass"] for r in rows if r["split"] == s),
                                         "tasks": sum(r["split"] == s for r in rows)} for s in ("dev", "holdout")},
                       "final_errors": dict(Counter(e for r in rows for e in r["errors"]))})
    return {"notice": "离线自动评分；human_review=pending。首轮/最终通过均包含符合预期的 blocked。",
            "price_basis": prices["basis"], "currency": prices["currency"], "summary": groups, "details": details}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", required=True, type=Path)
    parser.add_argument("--reference", required=True, type=Path)
    parser.add_argument("--prices", type=Path, default=ROOT / "prices.json")
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    # 先检查再创建新目录；已有目录拒绝覆盖，原日志只读。
    result = summarize(read_json(args.runs)["trials"], read_json(args.reference), read_json(args.prices), read_json(ROOT / "plan.json"))
    args.out.mkdir(parents=True, exist_ok=False)
    (args.out / "report.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result["summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, KeyError, TypeError) as error:
        raise SystemExit("评估未完成: " + str(error))
