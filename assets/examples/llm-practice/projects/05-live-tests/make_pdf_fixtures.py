"""生成同内容的文本 PDF 与无文字层的栅格 PDF，并实际抽取、渲染。"""
import argparse
import hashlib
import json
import platform
import subprocess
from importlib.metadata import version
from pathlib import Path

import fitz
from pypdf import PdfReader
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--font", type=Path, default=Path("C:/Windows/Fonts/simsun.ttc"))
    parser.add_argument("--pdftoppm", default="pdftoppm")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    pdfmetrics.registerFont(TTFont("Chinese", str(args.font), subfontIndex=0))
    digital = args.out / "digital-report.pdf"
    document = canvas.Canvas(str(digital), pagesize=A4)
    _, height = A4
    document.setTitle("D5 PDF and OCR controlled fixture")
    document.setAuthor("LLM practice tutorial")
    document.setFont("Chinese", 20)
    document.drawString(42, height - 65, "文件整理测试报告")
    document.setFont("Chinese", 11)
    lines = [("教学模拟资料；实际创建 PDF，不代表真实工具性能。", height - 105),
             ("P1:L1：下表 duration 的单位为秒（s），输出毫秒时乘以 1000。", height - 145),
             ("P1:L2：破折号“—”表示未记录；0 表示已记录零值。", height - 180),
             ("P1:L3：本文件为独立实测夹具，按 P5/E5 内容重新制作。", height - 215)]
    for text, y in lines:
        document.drawString(42, y, text)
    # 表格提供明确行列关系；提取器仍可能按列输出，不能凭纯文字顺序猜配对。
    xs, top, row_height = [42, 230, 350, 550], height - 270, 44
    for index in range(5):
        document.line(xs[0], top - index * row_height, xs[-1], top - index * row_height)
    for x in xs:
        document.line(x, top, x, top - 4 * row_height)
    rows = [["run_id", "duration", "record status"], ["sim-01", "1.25", "已记录"],
            ["sim-02", "—", "未记录"], ["sim-03", "0", "已记录零值"]]
    for i, row in enumerate(rows):
        for j, text in enumerate(row):
            document.drawString(xs[j] + 12, top - (i + 1) * row_height + 15, text)
    document.setFont("Chinese", 10)
    document.drawString(42, 85, "读取边界：文本 PDF 与栅格 PDF 的内容相同；栅格版没有文字层。")
    document.drawString(42, 60, "Page 1 / 1")
    document.showPage()
    document.save()
    # 整页转成图像后嵌入另一 PDF，不写入隐藏文字或 OCR 结果。
    with fitz.open(digital) as source:
        page = source[0]
        pixels = page.get_pixmap(matrix=fitz.Matrix(2, 2))
        with fitz.open() as raster:
            raster_page = raster.new_page(width=page.rect.width, height=page.rect.height)
            raster_page.insert_image(raster_page.rect, stream=pixels.tobytes("png"))
            raster.save(args.out / "raster-report.pdf")
    results = []
    for stem in ("digital-report", "raster-report"):
        pdf = args.out / (stem + ".pdf")
        # Poppler 独立渲染保存后的文件；OCR 使用 150 dpi 的栅格版渲染图。
        subprocess.run([args.pdftoppm, "-f", "1", "-singlefile", "-r", "150", "-png",
                        str(pdf), str(args.out / (stem + "-render"))], check=True)
        reader = PdfReader(pdf)
        text = reader.pages[0].extract_text() or ""
        (args.out / (stem + "-extracted.txt")).write_text(text, encoding="utf-8", newline="\n")
        results.append({"file": pdf.name, "pages": len(reader.pages), "text_chars": len(text),
                        "sha256": hashlib.sha256(pdf.read_bytes()).hexdigest()})
    metadata = {"system": platform.system(), "python": platform.python_version(),
                "versions": {key: version(key) for key in ("pypdf", "reportlab", "PyMuPDF")},
                "render_dpi": 150, "ocr_input": "raster-report-render.png", "pdfs": results}
    (args.out / "pdf-result.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2)
        + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(metadata, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
