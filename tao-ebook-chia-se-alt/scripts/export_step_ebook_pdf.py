#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw
from pypdf import PdfReader
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph


FONT_REG = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
pdfmetrics.registerFont(TTFont("DejaVu", FONT_REG))
pdfmetrics.registerFont(TTFont("DejaVuBold", FONT_BOLD))

W, H = A4
M = 18 * mm
TEXT_W = W - 2 * M


def rel(base: Path, value: str | None) -> Path | None:
    if not value:
        return None
    path = Path(value)
    return path if path.is_absolute() else base / path


def rounded_logo(src: Path, dst: Path) -> Path:
    img = Image.open(src).convert("RGBA")
    pad_x, pad_y = 26, 18
    bg = Image.new("RGBA", (img.width + pad_x * 2, img.height + pad_y * 2), (255, 255, 255, 255))
    bg.alpha_composite(img, (pad_x, pad_y))
    mask = Image.new("L", bg.size, 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle((0, 0, bg.width, bg.height), radius=24, fill=255)
    bg.putalpha(mask)
    dst.parent.mkdir(parents=True, exist_ok=True)
    bg.save(dst)
    return dst


def para(c, text, x, y, width, size=10.0, leading=14, color="#203040", bold=False, align=0):
    style = ParagraphStyle(
        "p",
        fontName="DejaVuBold" if bold else "DejaVu",
        fontSize=size,
        leading=leading,
        textColor=colors.HexColor(color),
        alignment=align,
    )
    item = Paragraph(str(text), style)
    _, h = item.wrap(width, 260 * mm)
    item.drawOn(c, x, y - h)
    return y - h


def card(c, x, y, w, h, fill="#ffffff", stroke="#d1d5db", radius=9):
    c.setFillColor(colors.HexColor(fill))
    c.setStrokeColor(colors.HexColor(stroke))
    c.roundRect(x, y, w, h, radius, fill=1, stroke=1)


def heading(c, text, y, page_no):
    c.setFillColor(colors.HexColor("#0f766e"))
    c.setFont("DejaVuBold", 18)
    c.drawString(M, y, f"{page_no}. {text}")
    c.setStrokeColor(colors.HexColor("#99f6e4"))
    c.line(M, y - 5, W - M, y - 5)
    return y - 17


def footer(c, spec, page_no):
    c.setFillColor(colors.HexColor("#64748b"))
    c.setFont("DejaVu", 7.8)
    c.drawString(M, 11 * mm, spec.get("footer") or "Anh Lập Trình - Cứ ứng dụng vào công việc đi, vướng đâu gỡ đó.")
    c.drawRightString(W - M, 11 * mm, f"Trang {page_no}")


def draw_browser_mockup(c, x, y, block):
    card(c, x, y, TEXT_W, 70 * mm, "#f8fafc", "#cbd5e1", 10)
    c.setFillColor(colors.HexColor("#e5e7eb"))
    c.roundRect(x, y + 58 * mm, TEXT_W, 12 * mm, 10, fill=1, stroke=0)
    for i, col in enumerate(["#ef4444", "#f59e0b", "#22c55e"]):
        c.setFillColor(colors.HexColor(col))
        c.circle(x + (8 + i * 6) * mm, y + 64 * mm, 2 * mm, fill=1, stroke=0)
    card(c, x + 28 * mm, y + 60.5 * mm, TEXT_W - 34 * mm, 6 * mm, "#ffffff", "#d1d5db", 4)
    c.setFont("DejaVu", 7.5)
    c.setFillColor(colors.HexColor("#475569"))
    c.drawString(x + 31 * mm, y + 62.3 * mm, block.get("url", "example.com"))
    c.setFont("DejaVuBold", 18)
    c.setFillColor(colors.HexColor("#111827"))
    c.drawString(x + 10 * mm, y + 42 * mm, block.get("title", "Minh họa màn hình"))
    c.setFont("DejaVu", 9)
    c.setFillColor(colors.HexColor("#475569"))
    c.drawString(x + 10 * mm, y + 34 * mm, block.get("subtitle", "Ảnh minh họa mô phỏng."))
    options = block.get("options", [])
    for i, opt in enumerate(options[:3]):
        bx = x + 10 * mm + i * 52 * mm
        card(c, bx, y + 10 * mm, 46 * mm, 18 * mm, opt.get("fill", "#dbeafe"), "#cbd5e1", 8)
        c.setFillColor(colors.HexColor("#111827"))
        c.setFont("DejaVuBold", 9.5)
        c.drawString(bx + 5 * mm, y + 20 * mm, opt.get("title", "Option"))
        c.setFont("DejaVu", 7.4)
        c.setFillColor(colors.HexColor("#475569"))
        c.drawString(bx + 5 * mm, y + 14 * mm, opt.get("body", ""))


def draw_terminal(c, x, y, lines):
    card(c, x, y, TEXT_W, 50 * mm, "#0f172a", "#0f172a", 10)
    c.setFillColor(colors.HexColor("#1e293b"))
    c.roundRect(x, y + 38 * mm, TEXT_W, 12 * mm, 10, fill=1, stroke=0)
    for i, col in enumerate(["#ef4444", "#f59e0b", "#22c55e"]):
        c.setFillColor(colors.HexColor(col))
        c.circle(x + (8 + i * 6) * mm, y + 44 * mm, 2 * mm, fill=1, stroke=0)
    c.setFont("DejaVu", 8)
    for i, line in enumerate(lines[:5]):
        c.setFillColor(colors.HexColor("#5eead4") if str(line).startswith("$") else colors.HexColor("#e2e8f0"))
        c.drawString(x + 9 * mm, y + (30 - i * 7) * mm, str(line))


def draw_page(c, spec, page, page_no):
    y = H - M
    y = heading(c, page.get("heading", "Nội dung"), y, page_no - 1)
    for text in page.get("paragraphs", []):
        y = para(c, text, M, y, TEXT_W)
        y -= 4
    if "browser_mockup" in page:
        draw_browser_mockup(c, M, y - 76 * mm, page["browser_mockup"])
        y -= 86 * mm
    if "cards" in page:
        for item in page["cards"][:4]:
            card(c, M, y - 24 * mm, TEXT_W, 20 * mm, "#ffffff", "#dbe3ea", 9)
            c.setFillColor(colors.HexColor("#0f766e"))
            c.setFont("DejaVuBold", 10)
            c.drawString(M + 7 * mm, y - 11 * mm, item.get("title", "Mục"))
            para(c, item.get("body", ""), M + 7 * mm, y - 15 * mm, TEXT_W - 14 * mm, 8.4, 11.5, "#475569")
            y -= 27 * mm
    if "steps" in page:
        card(c, M, y - 45 * mm, TEXT_W, 38 * mm, "#f8fafc", "#dbe3ea", 12)
        for i, step in enumerate(page["steps"][:4]):
            bx = M + 8 * mm + i * 40 * mm
            card(c, bx, y - 33 * mm, 34 * mm, 18 * mm, "#ffffff", "#cbd5e1", 8)
            c.setFillColor(colors.HexColor("#0f766e"))
            c.circle(bx + 7 * mm, y - 23 * mm, 4 * mm, fill=1, stroke=0)
            c.setFillColor(colors.white)
            c.setFont("DejaVuBold", 8)
            c.drawCentredString(bx + 7 * mm, y - 25.3 * mm, str(i + 1))
            c.setFillColor(colors.HexColor("#111827"))
            c.drawString(bx + 13 * mm, y - 24.8 * mm, str(step)[:18])
        y -= 52 * mm
    if "terminal" in page:
        draw_terminal(c, M, y - 55 * mm, page["terminal"])
        y -= 65 * mm
    if "table" in page:
        rows = page["table"]
        card(c, M, y - (12 + 10 * len(rows)) * mm, TEXT_W, (8 + 10 * len(rows)) * mm, "#ffffff", "#dbe3ea", 10)
        for i, row in enumerate(rows):
            yy = y - (16 + i * 10) * mm
            c.setFont("DejaVuBold" if i == 0 else "DejaVu", 7.8)
            c.setFillColor(colors.HexColor("#0f766e" if i == 0 else "#203040"))
            for j, cell in enumerate(row[:4]):
                c.drawString(M + (8 + j * 40) * mm, yy, str(cell)[:28])
        y -= (22 + 10 * len(rows)) * mm
    if "checklist" in page:
        card(c, M, y - 70 * mm, TEXT_W, 62 * mm, "#fff7ed", "#fed7aa", 12)
        c.setFont("DejaVuBold", 11)
        c.setFillColor(colors.HexColor("#ea580c"))
        c.drawString(M + 8 * mm, y - 19 * mm, "Checklist")
        c.setFont("DejaVu", 8.5)
        c.setFillColor(colors.HexColor("#7c2d12"))
        for i, item in enumerate(page["checklist"][:6]):
            yy = y - (31 + i * 7.5) * mm
            c.rect(M + 9 * mm, yy - 1 * mm, 4 * mm, 4 * mm, stroke=1, fill=0)
            c.drawString(M + 17 * mm, yy, str(item)[:90])
        y -= 76 * mm
    if page.get("note"):
        card(c, M, 32 * mm, TEXT_W, 24 * mm, "#ecfeff", "#99f6e4", 10)
        para(c, page["note"], M + 7 * mm, 48 * mm, TEXT_W - 14 * mm, 9, 12.5, "#115e59", True, 1)
    footer(c, spec, page_no)
    c.showPage()


def draw_cover(c, spec, logo_path: Path | None):
    c.setFillColor(colors.HexColor("#0f172a"))
    c.rect(0, 0, W, H, fill=1, stroke=0)
    if logo_path and logo_path.exists():
        c.drawImage(str(logo_path), M, H - 34 * mm, width=58 * mm, height=16 * mm, mask="auto")
    c.setFillColor(colors.HexColor("#5eead4"))
    c.setFont("DejaVuBold", 14)
    c.drawString(M, H - 65 * mm, spec.get("kicker", "EBOOK CHIA SẺ").upper())
    c.setFillColor(colors.white)
    c.setFont("DejaVuBold", 32)
    title = spec.get("title", "Ebook")
    parts = title.split(" ", 2)
    c.drawString(M, H - 91 * mm, " ".join(parts[:2]).upper())
    if len(parts) > 2:
        c.drawString(M, H - 109 * mm, parts[2].upper())
    para(c, spec.get("subtitle", ""), M, H - 130 * mm, TEXT_W, 12.2, 16, "#dbeafe")
    card(c, M, H - 168 * mm, TEXT_W, 23 * mm, "#12364a", "#2dd4bf", 13)
    para(c, spec.get("slogan", "Cứ ứng dụng vào công việc đi, vướng đâu gỡ đó."), M + 6 * mm, H - 156 * mm, TEXT_W - 12 * mm, 13, 16, "#a7f3d0", True, 1)
    c.setFillColor(colors.HexColor("#cbd5e1"))
    c.setFont("DejaVu", 9.2)
    c.drawString(M, 25 * mm, f"{spec.get('author', 'Anh Lập Trình')} | Phiên bản {spec.get('version', '')}")
    c.showPage()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    base = args.spec.resolve().parent
    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    logo = rel(base, spec.get("logo"))
    rounded = None
    if logo and logo.exists():
        rounded = rounded_logo(logo, logo.with_name(logo.stem + "_bo_tron.png"))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(args.output), pagesize=A4)
    draw_cover(c, spec, rounded)
    for idx, page in enumerate(spec.get("pages", []), start=2):
        draw_page(c, spec, page, idx)
    c.save()
    pages = len(PdfReader(str(args.output)).pages)
    print(f"{args.output} ({pages} pages)")


if __name__ == "__main__":
    main()
