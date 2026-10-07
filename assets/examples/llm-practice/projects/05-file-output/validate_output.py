"""D5-v1 固定练习的结构与文件一致性检查；不判断原文是否支持数值。"""
import argparse
import csv
import json
import re
from pathlib import Path

BASE = Path(__file__).resolve().parent
FIELDS = ["record_id", "tool", "version", "field", "value", "unit", "state",
          "source_refs", "note"]


def require(condition, message):
    if not condition:
        raise ValueError(message)


def unique_object(pairs):
    """默认 JSON 解码会保留重复键的最后一个值，此处显式拒绝重复键。"""
    result = {}
    for key, value in pairs:
        require(key not in result, f"JSON 重复键：{key}")
        result[key] = value
    return result


def reject_constant(value):
    raise ValueError(f"JSON 非标准数值：{value}")


def read_json(path):
    # utf-8 不吞掉 BOM；该练习要求无 BOM。NaN/Infinity 不作为合法值接受。
    return json.loads(path.read_text(encoding="utf-8"),
                      object_pairs_hook=unique_object, parse_constant=reject_constant)


def clean_string(value):
    # 固定单行字段：允许普通标点和双引号，禁止控制字符，避免隐藏的列/行边界。
    return (type(value) is str and bool(value.strip())
            and not any(ord(char) < 32 or ord(char) == 127 for char in value))


def source_positions():
    """只索引资料中真实出现的标签，不根据行数猜测；D5 是指令，不作事实证据。"""
    result, source = set(), None
    for line in (BASE / "sources.txt").read_text(encoding="utf-8").splitlines():
        header = re.match(r"\[(S[1235]|P5|E5)\]", line)
        if header:
            source = header.group(1)
        elif line.startswith("["):
            source = None
        label = re.match(r"((?:P[0-9]+:)?L[0-9]+)：", line)
        if source and label:
            result.add(f"{source}:{label.group(1)}")
    return result


def checked_json(path):
    """固定键、记录集合与字段类型来自 contract.json，而不是参考答案。"""
    data = read_json(path)
    contract = read_json(BASE / "contract.json")
    require(type(data) is dict and set(data) == {"schema_version", "demand_id", "records"},
            "JSON 顶层键必须为 schema_version、demand_id、records")
    for key in ("schema_version", "demand_id"):
        require(data[key] == contract[key], f"JSON {key} 不匹配")
    records = data["records"]
    require(type(records) is list, "records 必须为数组")
    specs = contract["records"]
    require(len(records) == len(specs), f"记录数量必须为 {len(specs)}")
    ids = []
    for index, record in enumerate(records, 1):
        require(type(record) is dict and set(record) == set(FIELDS),
                f"第 {index} 条记录的键不匹配")
        require(clean_string(record["record_id"]), f"第 {index} 条 record_id 不合法")
        ids.append(record["record_id"])
    require(len(ids) == len(set(ids)), "record_id 重复")
    require(ids == [item["record_id"] for item in specs], "记录集合或顺序不匹配契约")
    positions = source_positions()
    for record, spec in zip(records, specs):
        rid = record["record_id"]
        for key in ("tool", "version", "field", "unit"):
            require(record[key] == spec[key], f"{rid}: {key} 不匹配契约")
        state, value = record["state"], record["value"]
        require(type(state) is str and state in ("known", "missing", "conflict"),
                f"{rid}: state 不合法")
        if state == "known":
            # Python bool 是 int 的子类；使用精确类型，防止 true 冒充文件数量 1。
            expected_type = {"integer": int, "boolean": bool, "string": str}[spec["value_type"]]
            require(type(value) is expected_type, f"{rid}: value 类型错误")
            if expected_type is int:
                require(value >= spec["minimum"], f"{rid}: value 低于允许下限")
            elif expected_type is str:
                require(clean_string(value), f"{rid}: value 必须是非空单行字符串")
        else:
            require(value is None, f"{rid}: missing/conflict 的 value 必须为 null")
        refs = record["source_refs"]
        require(type(refs) is list and bool(refs), f"{rid}: source_refs 必须为非空数组")
        require(all(type(ref) is str and ref in positions for ref in refs),
                f"{rid}: 来源定位不存在")
        require(len(refs) == len(set(refs)), f"{rid}: 来源定位重复")
        require(clean_string(record["note"]), f"{rid}: note 必须是非空单行字符串")
    return data


def value_text(value):
    if value is None:
        return ""
    if type(value) is bool:
        return "true" if value else "false"
    return str(value)


def tsv_rows(data):
    """缺失/冲突的值为空单元格，状态单独保留；来源数组以分号连接。"""
    yield FIELDS
    for record in data["records"]:
        yield [value_text(record[key]) if key == "value"
               else ";".join(record[key]) if key == "source_refs"
               else record[key] for key in FIELDS]


def md_cell(value):
    # 固定模板的表格单元格先转义 HTML，再转义 Markdown 的反斜线与管道符。
    return (str(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace("\\", "\\\\").replace("|", "\\|"))


def render_report(data):
    """此练习采用固定报告模板，逐字比较；不适用于任意自由撰写的 Markdown。"""
    lines = ["# 文件整理报告", "", f"需求版本：{data['demand_id']}", "",
             "范围：三种虚构工具的九条属性及三条教学模拟实验记录；不作性能排名。", ""]
    for title, is_run in (("工具属性", False), ("模拟实验记录", True)):
        lines += [f"## {title}", "", "| 标识 | 工具与版本 | 字段 | 值与单位 | 状态 | 来源 |",
                  "| --- | --- | --- | --- | --- | --- |"]
        for record in data["records"]:
            if (record["field"] == "elapsed_ms") != is_run:
                continue
            value = value_text(record["value"]) or "未确定"
            if record["value"] is not None and record["unit"] != "none":
                value += " " + record["unit"]
            cells = [record["record_id"], f"{record['tool']} {record['version']}",
                     record["field"], value, record["state"], ";".join(record["source_refs"])]
            lines.append("| " + " | ".join(md_cell(cell) for cell in cells) + " |")
        lines.append("")
    lines += ["## 记录说明", ""]
    for record in data["records"]:
        lines.append(f"- {record['record_id']}：{md_cell(record['note'])}")
    lines += ["", "检查边界：来源标签存在与文件一致性不代表事实已核验；须回到原文检查含义与单位。", ""]
    return "\n".join(lines)


def check_bundle(folder):
    data = checked_json(folder / "records.json")
    # csv 模块负责引号与分隔符；不用 split，也不让默认 None -> 空串隐式决定语义。
    with (folder / "records.tsv").open(encoding="utf-8", newline="") as stream:
        rows = list(csv.reader(stream, delimiter="\t", strict=True))
    expected = list(tsv_rows(data))
    require(bool(rows) and rows[0] == FIELDS, "TSV 表头不匹配")
    require(len(rows) == len(expected), "TSV 记录数量不匹配")
    for index, (actual, target) in enumerate(zip(rows[1:], expected[1:]), 1):
        require(len(actual) == len(FIELDS), f"TSV 第 {index} 条列数错误")
        require(actual == target, f"TSV {target[0]} 与 JSON 不一致")
    actual_report = (folder / "report.md").read_text(encoding="utf-8")
    require(actual_report == render_report(data), "Markdown 与 JSON 的固定模板不一致")
    return len(data["records"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()
    try:
        count = check_bundle(args.output_dir)
    except (ValueError, OSError, csv.Error) as error:
        parser.exit(1, f"FAIL: {error}\n")
    print(f"PASS: {count} records; structure, reference labels and file consistency.")
    print("Manual review required: source meaning, unit conversion and factual support.")


if __name__ == "__main__":
    main()
