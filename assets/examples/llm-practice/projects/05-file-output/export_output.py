"""从经过结构检查的 JSON 导出三个文件；仅创建全新的输出目录。"""
import argparse
import csv
import json
from pathlib import Path

from validate_output import checked_json, render_report, tsv_rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("json_file", type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    try:
        # 检查先于任何写入。结构合规不代替读者的事实核验。
        data = checked_json(args.json_file)
        # exist_ok=False 保留已存在的目录和文件；不会覆盖上一版本。
        # 中途写入失败可能留下部分文件，应检查后另选新目录，不在原目录重试覆盖。
        args.out.mkdir(parents=True, exist_ok=False)
        (args.out / "records.json").write_text(
            json.dumps(data, ensure_ascii=False, allow_nan=False, indent=2) + "\n",
            encoding="utf-8", newline="\n")
        with (args.out / "records.tsv").open("w", encoding="utf-8", newline="") as stream:
            writer = csv.writer(stream, delimiter="\t", lineterminator="\n")
            writer.writerows(tsv_rows(data))
        (args.out / "report.md").write_text(render_report(data), encoding="utf-8", newline="\n")
    except (ValueError, OSError, csv.Error) as error:
        parser.exit(1, f"FAIL: {error}\n")
    print(f"WROTE: {args.out.resolve()}; records.json, records.tsv, report.md")
    print("Run validate_output.py on this directory, then review the sources manually.")


if __name__ == "__main__":
    main()
