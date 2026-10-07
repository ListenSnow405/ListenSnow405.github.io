"""只在生成之后评分；参考答案不会进入模型输入。"""
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "d5_validator", ROOT / "projects/05-file-output/validate_output.py")
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)


def evaluate(path, reference_path=None):
    """格式检查与事实字段比较分别评分，格式失败也保留可解析的事实结果。"""
    reference_path = reference_path or ROOT / "expected/05-output/records.json"
    gold = validator.read_json(reference_path)
    result = {"json_parse": False, "contract_pass": False, "contract_error": None,
              "fact_matches": 0, "reference_coverage": 0, "total_records": 12,
              "record_errors": []}
    try:
        actual = validator.read_json(path)
        result["json_parse"] = True
    except (ValueError, OSError) as error:
        result["contract_error"] = str(error)
        return result
    try:
        validator.checked_json(path)
        result["contract_pass"] = True
    except (ValueError, OSError) as error:
        result["contract_error"] = str(error)
    # 七个事实字段按精确类型比较；note 允许准确的独立措辞。
    keys = ("record_id", "tool", "version", "field", "value", "unit", "state")
    rows = actual.get("records", []) if type(actual) is dict else []
    by_id = {}
    for record in rows if type(rows) is list else []:
        if type(record) is dict and type(record.get("record_id")) is str:
            by_id.setdefault(record["record_id"], []).append(record)
    for expected in gold["records"]:
        rid = expected["record_id"]
        matches = by_id.get(rid, [])
        if len(matches) != 1:
            result["record_errors"].append({"record_id": rid, "error": "missing or duplicate"})
            continue
        row = matches[0]
        errors = [key for key in keys if key not in row or type(row[key]) is not type(expected[key])
                  or row[key] != expected[key]]
        if not errors:
            result["fact_matches"] += 1
        else:
            result["record_errors"].append({"record_id": rid, "fields": errors})
        refs = row.get("source_refs")
        if (type(refs) is list and all(type(ref) is str for ref in refs)
                and set(expected["source_refs"]) <= set(refs)):
            result["reference_coverage"] += 1
    return result


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("records", type=Path)
    args = parser.parse_args()
    print(json.dumps(evaluate(args.records), ensure_ascii=False, indent=2))
