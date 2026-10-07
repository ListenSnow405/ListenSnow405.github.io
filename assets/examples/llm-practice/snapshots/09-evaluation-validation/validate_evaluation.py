"""在独立临时项目中验收 D9 评分、计价与失败保护，不调用模型。"""
import copy
import hashlib
import importlib.util
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


def main():
    checks = []
    with tempfile.TemporaryDirectory(prefix="llm-eval-09-") as temporary:
        lab = Path(temporary) / "lab"
        shutil.copytree(ROOT / "projects/09-evaluation", lab)
        shutil.copy2(ROOT / "expected/09-gold.json", lab / "reference.json")
        shutil.copy2(HERE / "teaching-runs.json", lab / "teaching-runs.json")
        spec = importlib.util.spec_from_file_location("d9_eval", lab / "evaluate.py")
        evaluator = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(evaluator)
        runs = evaluator.read_json(lab / "teaching-runs.json")
        gold = evaluator.read_json(lab / "reference.json")
        prices = evaluator.read_json(lab / "prices.json")
        plan = evaluator.read_json(lab / "plan.json")

        def check(name, condition):
            if not condition:
                raise AssertionError(name)
            checks.append({"name": name, "passed": True})

        def rejected(name, action):
            try:
                action()
            except ValueError:
                check(name, True)
            else:
                check(name, False)

        def report(trials):
            return evaluator.summarize(trials, gold, prices, plan)

        result = report(runs["trials"])
        check("36 task decisions", len(result["details"]) == 36)
        check("first/final pass counts", [(r["first_pass"], r["final_pass"]) for r in result["summary"]] == [(6, 6), (10, 10), (10, 12)])
        check("calls and correct stops", [r["model_calls"] for r in result["summary"]] == [10, 10, 12] and all(r["correct_blocks"] == 2 for r in result["summary"]))
        check("teaching token totals", [round(r["token_estimate"], 5) for r in result["summary"]] == [0.04430, 0.05230, 0.05726])
        check("human review remains pending", all(r["human_review"] == "pending" for r in result["details"]))
        cost = evaluator.token_cost({"input_tokens": 2000, "cached_input_tokens": 1000,
                                    "cache_write_input_tokens": 500, "output_tokens": 300}, prices["per_million"])
        check("exclusive cache read/write formula", str(cost) == "0.00515")
        rejected("invalid cache accounting", lambda: evaluator.token_cost({"input_tokens": 10,
                 "cached_input_tokens": 8, "cache_write_input_tokens": 5, "output_tokens": 0}, prices["per_million"]))
        bad = copy.deepcopy(gold["C01"])
        bad["records"][0]["value"] = True
        check("boolean does not equal integer", not evaluator.score(json.dumps(bad), gold["C01"])["automatic_pass"])
        check("duplicate JSON keys rejected", "json_parse" in evaluator.score('{"case_id":"C01","case_id":"C01"}', gold["C01"])["errors"])
        bad = copy.deepcopy(gold["C01"])
        bad["records"].append(copy.deepcopy(bad["records"][0]))
        check("duplicate record rejected", "coverage" in evaluator.score(json.dumps(bad), gold["C01"])["errors"])
        bad = copy.deepcopy(gold["C03"])
        bad["records"][0]["source_refs"] = ["S5:L2"]
        check("both conflict sources required", "evidence" in evaluator.score(json.dumps(bad), gold["C03"])["errors"])
        modified = copy.deepcopy(runs["trials"])
        modified[0]["attempts"][0]["input_tokens"] = None
        unknown = report(modified)["summary"][0]
        check("unknown tokens propagate", unknown["token_estimate"] is None and unknown["total_estimate"] is None and unknown["token_cost_per_correct_task"] is None)
        modified = copy.deepcopy(runs["trials"])
        modified[0]["attempts"][0]["tool_cost"] = None
        unknown = report(modified)["summary"][0]
        check("unknown tool cost preserves token estimate", unknown["token_estimate"] is not None and unknown["total_estimate"] is None)
        modified = copy.deepcopy(runs["trials"])
        for trial in modified:
            for attempt in trial["attempts"]:
                attempt["raw_output"] = "invalid JSON"
        check("zero correct tasks has no unit cost", all(r["token_cost_per_correct_task"] is None for r in report(modified)["summary"]))
        rejected("missing trial rejected", lambda: report(runs["trials"][:-1]))
        rejected("duplicate trial rejected", lambda: report(runs["trials"] + [runs["trials"][0]]))
        modified = copy.deepcopy(runs["trials"])
        modified[10]["attempts"][0]["stage"] = "model"
        check("read failure cannot call model", "process" in report(modified)["details"][10]["errors"])
        modified = copy.deepcopy(runs["trials"])
        modified[0]["attempts"].append(copy.deepcopy(modified[0]["attempts"][0]))
        check("W0 call limit checked", "process" in report(modified)["details"][0]["errors"])
        modified = copy.deepcopy(runs["trials"])
        modified[0]["wall_seconds"] = 121
        check("time limit checked", "process" in report(modified)["details"][0]["errors"])
        before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (lab / "reference.json", lab / "teaching-runs.json")}
        command = [sys.executable, "evaluate.py", "--runs", "teaching-runs.json", "--reference", "reference.json", "--out", "runs/demo-01"]
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONIOENCODING="utf-8")
        first = subprocess.run(command, cwd=lab, env=env, capture_output=True, text=True, encoding="utf-8")
        check("actual CLI completed", first.returncode == 0 and (lab / "runs/demo-01/report.json").exists())
        output_hash = hashlib.sha256((lab / "runs/demo-01/report.json").read_bytes()).hexdigest()
        second = subprocess.run(command, cwd=lab, env=env, capture_output=True, text=True, encoding="utf-8")
        check("existing output protected", second.returncode != 0 and output_hash == hashlib.sha256((lab / "runs/demo-01/report.json").read_bytes()).hexdigest())
        check("logs and reference unchanged", before == {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (lab / "reference.json", lab / "teaching-runs.json")})
        saved = json.loads((lab / "runs/demo-01/report.json").read_text(encoding="utf-8"))
        (HERE / "recalculated-report.json").write_text(json.dumps(saved, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    record = {"date": "2026-10-05", "os": platform.system(), "python": platform.python_version(),
              "scope": "actual isolated program validation on human authored fixtures; no model or API calls",
              "checks": checks, "passed": len(checks)}
    (HERE / "program-validation.json").write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(record, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
