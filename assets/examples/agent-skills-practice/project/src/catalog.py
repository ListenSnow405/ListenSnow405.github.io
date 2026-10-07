"""CSV 的业务入口：保留未知日期，集中处理字段、ID 与分类统计。"""

import csv
from collections import Counter
from datetime import date
from pathlib import Path

FIELDS = ["id", "title", "course", "category", "tags", "updated_at"]


def load_materials(path: Path) -> list[dict]:
    """读取 UTF-8 CSV；返回规范化记录；坏字段或重复 ID 直接报告行号。"""
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != FIELDS:
            raise ValueError(f"字段及顺序必须为 {FIELDS}")
        records, seen = [], set()
        for number, row in enumerate(reader, start=2):
            # 多余列会产生 None 键，缺列会产生 None 值，都不能默默吞掉。
            if None in row or any(value is None for value in row.values()):
                raise ValueError(f"第 {number} 行的列数错误")
            record = {key: value.strip() for key, value in row.items()}
            if any(not record[key] for key in FIELDS[:4]):
                raise ValueError(f"第 {number} 行缺少 ID、标题、课程或分类")
            if record["id"] in seen:
                raise ValueError(f"第 {number} 行的 ID 重复：{record['id']}")
            seen.add(record["id"])
            # 原始空值成为 None；不以运行当天日期代替未提供日期。
            raw_date = record["updated_at"]
            if raw_date:
                if date.fromisoformat(raw_date).isoformat() != raw_date:
                    raise ValueError(f"第 {number} 行日期需要 YYYY-MM-DD 格式")
            record["updated_at"] = raw_date or None
            record["tags"] = [tag.strip() for tag in record["tags"].split(";") if tag.strip()]
            records.append(record)
    if not records:
        raise ValueError("清单没有记录")
    return records


def summarize(records: list[dict]) -> dict:
    """统计完整输入。分类计数与缺失日期是两个独立维度。"""
    return {
        "total": len(records),
        "categories": dict(sorted(Counter(row["category"] for row in records).items())),
        "missing_dates": [row["id"] for row in records if row["updated_at"] is None],
    }
