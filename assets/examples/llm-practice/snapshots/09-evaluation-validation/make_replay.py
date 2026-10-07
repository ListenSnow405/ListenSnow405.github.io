"""构造人为 D9 教学夹具；输出不是模型响应，不模拟实际时钟或账单。"""
import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


def answer(case, rid=None, value=None, unit=None, state=None, refs=None):
    return {"case_id": case, "outcome": "completed" if rid else "blocked",
            "reason": None if rid else "source_read_failed", "records": [] if not rid else [
                {"record_id": rid, "value": value, "unit": unit, "state": state, "source_refs": refs}]}


def make():
    gold = {
        "C01": answer("C01", "LB-FILES", 2, "files", "known", ["S1:L4"]),
        "C02": answer("C02", "LB-LICENSE", None, "none", "missing", ["S1:L8"]),
        "C03": answer("C03", "BT-FILES", None, "files", "conflict", ["S2:L4", "S5:L2", "S5:L3"]),
        "C04": answer("C04", "RUN-03", 0, "ms", "known", ["E5:L3", "P5:P1:L1", "P5:P1:L2"]),
        "C05": answer("C05", "BT-FILES", 8, "files", "known", ["S2:L4"]),
        "C06": answer("C06")
    }
    trials = []
    for variant in ("P0-W0", "P1-W0", "P1-W1"):
        for index, case in enumerate(gold, 1):
            for repeat in (1, 2):
                actual = copy.deepcopy(gold[case])
                row = actual["records"][0] if actual["records"] else None
                if variant == "P0-W0":
                    if case == "C02":
                        row.update(value="MIT", state="known")
                    if case == "C03":
                        row.update(value=4, state="known", source_refs=["S5:L2"])
                    if case == "C04" and repeat == 1:
                        row.update(value=None, state="missing")
                    if case == "C05" and repeat == 1:
                        row.update(value=100, source_refs=["S6:L3"])
                if variant != "P0-W0" and case == "C05" and repeat == 1:
                    row["source_refs"] = ["S2:L99"]
                raw = json.dumps(actual, ensure_ascii=False)
                if variant != "P0-W0" and case == "C04" and repeat == 2:
                    raw = raw[:-1] + ",}"  # 人为尾逗号，保留原文而不自动修复。
                blocked = case == "C06"
                attempt = {"stage": "read" if blocked else "model", "status": "failed" if blocked else "completed",
                           "raw_output": raw, "feedback": None,
                           "input_tokens": 0 if blocked else (1500 if variant == "P0-W0" else 1900),
                           "cached_input_tokens": 0 if blocked else 200,
                           "cache_write_input_tokens": 0 if blocked else 100,
                           "output_tokens": 0 if blocked else 180 + index * 10,
                           "tool_cost": 0}
                attempts = [attempt]
                seconds = 1 if blocked else 10 + index + repeat
                if variant == "P1-W1" and ((case == "C04" and repeat == 2) or (case == "C05" and repeat == 1)):
                    attempts.append({"stage": "model", "status": "completed",
                                     "raw_output": json.dumps(gold[case], ensure_ascii=False),
                                     "feedback": "JSON 解析失败" if case == "C04" else "来源定位 S2:L99 不存在",
                                     "input_tokens": 900, "cached_input_tokens": 400,
                                     "cache_write_input_tokens": 0, "output_tokens": 160, "tool_cost": 0})
                    seconds += 8
                trials.append({"variant": variant, "case_id": case, "repeat": repeat,
                               "wall_seconds": seconds, "attempts": attempts})
    (ROOT / "expected/09-gold.json").write_text(json.dumps(gold, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (HERE / "teaching-runs.json").write_text(json.dumps({"evidence_type": "human_authored_fixture",
        "model": "none", "settings": "not applicable", "usage_basis": "invented_for_arithmetic",
        "time_basis": "invented_for_arithmetic", "trials": trials}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    make()
