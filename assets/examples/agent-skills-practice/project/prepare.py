"""从模拟 CSV 生成可浏览目录和报告。只写新目录，不安装软件或调用模型。"""

import argparse
import csv
import hashlib
import html
import json
import shutil
import sys
from io import StringIO
from pathlib import Path

from src.catalog import load_materials, summarize


def escape(value) -> str:
    """输入显示在 HTML 文本和属性中，统一转义引号及尖括号。"""
    return html.escape(str(value), quote=True)


def page(title: str, body: str, script: bool = False) -> str:
    """生成独立页面；普通浏览不加载外部资源。"""
    return ("<!doctype html><html lang=\"zh-CN\"><head><meta charset=\"utf-8\">"
            "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
            f"<title>{escape(title)}</title><link rel=\"stylesheet\" href=\"style.css\"></head>"
            f"<body><main>{body}</main>"
            + ('<script src="app.js" defer></script>' if script else '') + "</body></html>\n")


def render_catalog(records: list[dict], summary: dict) -> str:
    options = ''.join(f'<option value="{escape(name)}">{escape(name)}</option>'
                      for name in summary["categories"])
    items = []
    for row in records:
        tags = " / ".join(row["tags"]) or "未提供"
        search = " ".join([row["title"], row["course"], *row["tags"]])
        items.append(f'<li class="material" data-material data-category="{escape(row["category"])}" '
                     f'data-search="{escape(search)}"><h2>{escape(row["title"])}</h2>'
                     f'<p class="meta"><span>{escape(row["id"])}</span>'
                     f'<span>{escape(row["course"])}</span><span>{escape(row["category"])}</span></p>'
                     f'<p>标签：{escape(tags)}</p><p>更新日期：{escape(row["updated_at"] or "未提供")}</p></li>')
    body = ('<h1>课程资料目录</h1><p class="muted">教学模拟 · 六条清单记录，无原始资料下载。</p>'
            '<p><a href="report.html">查看完整清单报告</a></p>'
            '<div class="filters" data-filters hidden><label for="query">关键词'
            '<input id="query" type="search" placeholder="标题、课程或标签"></label>'
            f'<label for="category">分类<select id="category"><option value="">全部分类</option>{options}</select></label>'
            '<button id="clear" type="button">清除筛选</button></div>'
            f'<p id="status" aria-live="polite">显示 {len(records)} / {len(records)} 条资料</p>'
            '<p id="empty" hidden>没有符合当前条件的资料。请修改条件或清除筛选。</p>'
            '<noscript><p>筛选需要 JavaScript；以下完整清单仍可阅读。</p></noscript>'
            '<ul class="materials">' + ''.join(items) + '</ul>')
    return page("课程资料目录", body, script=True)


def render_report(records: list[dict], summary: dict) -> str:
    counts = "；".join(f"{escape(name)} {count} 条" for name, count in summary["categories"].items())
    rows = ''.join('<tr>' + ''.join(f'<td>{escape(value)}</td>' for value in (
        row["id"], row["title"], row["course"], row["category"], row["updated_at"] or "未提供"))
                   + '</tr>' for row in records)
    body = (f'<h1>课程资料整理报告</h1><p class="muted">教学模拟；统计对象为完整 CSV 清单。</p>'
            f'<p>资料总数：{summary["total"]} 条。分类：{counts}。</p>'
            f'<p>未提供更新日期：{len(summary["missing_dates"])} 条，'
            f'{escape("、".join(summary["missing_dates"]))}。没有推断实际更新时间。</p>'
            '<div class="table-wrap"><table><thead><tr><th scope="col">ID</th><th scope="col">标题</th>'
            '<th scope="col">课程</th><th scope="col">分类</th><th scope="col">更新日期</th></tr></thead>'
            f'<tbody>{rows}</tbody></table></div>'
            '<p>本报告只描述资料清单，不评价原始资料内容。未提供文件大小、下载地址或资料正文。</p>'
            '<p class="screen-only"><a href="index.html">返回资料目录</a>；可使用浏览器打印功能保存 PDF，'
            '保存后再检查实际页数、中文字体和表格。</p>')
    return page("课程资料整理报告", body)


def generate(output: Path, source: Path) -> None:
    """输入完全校验后才创建目标；已有目标一律拒绝，便于保留各次实验。"""
    root = Path(__file__).resolve().parent
    output, source = output.resolve(), source.resolve()
    if output.exists():
        raise FileExistsError(f"产物目录已存在，请指定新目录：{output}")
    if output == source or output in source.parents:
        raise ValueError("产物目录不能包含输入文件")
    records = load_materials(source)
    summary = summarize(records)
    summary["source_sha256"] = hashlib.sha256(source.read_bytes()).hexdigest()
    # 所有 HTML 均先在内存中构造，避免输入错误产生看似完整的页面。
    payloads = {
        "index.html": render_catalog(records, summary),
        "report.html": render_report(records, summary),
        "summary.json": json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
    }
    stream = StringIO(newline="")
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(["category", "count"])
    writer.writerows(summary["categories"].items())
    payloads["summary.csv"] = stream.getvalue()
    output.mkdir(parents=True, exist_ok=False)
    for name, content in payloads.items():
        (output / name).write_text(content, encoding="utf-8")
    for name in ["app.js", "style.css"]:
        shutil.copyfile(root / "src" / name, output / name)
    print(f"已生成 {summary['total']} 条资料，未提供日期 {len(summary['missing_dates'])} 条：{output}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path, help="尚不存在的产物目录")
    parser.add_argument("--input", type=Path, default=Path(__file__).resolve().parent / "data/materials.csv")
    args = parser.parse_args()
    try:
        generate(args.output, args.input)
    except (OSError, ValueError) as error:
        print(f"生成失败：{error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
