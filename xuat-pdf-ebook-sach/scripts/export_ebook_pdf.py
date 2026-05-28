from __future__ import annotations

import argparse
import base64
import html
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path


CHUONG = "Ch\u01b0\u01a1ng"
DEFAULT_SUBTITLE = "Ebook"

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except AttributeError:
    pass


def find_browser() -> str:
    candidates = [
        shutil.which("chrome"),
        shutil.which("google-chrome"),
        shutil.which("chromium"),
        shutil.which("msedge"),
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    ]
    for item in candidates:
        if item and Path(item).exists():
            return str(item)
    raise RuntimeError("Khong tim thay Chrome/Edge de xuat PDF.")


def long_path(path: Path) -> str:
    value = str(path)
    if os.name == "nt" and not value.startswith("\\\\?\\"):
        return "\\\\?\\" + value
    return value


def path_exists(path: Path) -> bool:
    return os.path.exists(long_path(path))


def read_text_utf8(path: Path) -> str:
    with open(long_path(path), "r", encoding="utf-8") as handle:
        return handle.read()


def read_bytes(path: Path) -> bytes:
    with open(long_path(path), "rb") as handle:
        return handle.read()


def inline_markdown(value: str) -> str:
    value = html.escape(value)
    value = re.sub(r"`([^`]+)`", lambda m: f"<code>{m.group(1)}</code>", value)
    value = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", value)
    return value


def split_long_paragraph(paragraph: str, enabled: bool = True) -> list[str]:
    paragraph = paragraph.strip()
    if not enabled or len(paragraph) <= 430:
        return [paragraph]
    safe = paragraph.replace("A.I", "A<dot>I")
    sentences = [
        item.replace("A<dot>I", "A.I").strip()
        for item in re.split(r"(?<=[.!?])\s+", safe)
        if item.strip()
    ]
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0
    for sentence in sentences:
        if current and (current_len + len(sentence) > 360 or len(current) >= 2):
            chunks.append(" ".join(current))
            current = [sentence]
            current_len = len(sentence)
        else:
            current.append(sentence)
            current_len += len(sentence) + 1
    if current:
        chunks.append(" ".join(current))
    return chunks or [paragraph]


def data_uri(path: Path) -> str:
    suffix = path.suffix.lower().lstrip(".") or "png"
    mime = "jpeg" if suffix in {"jpg", "jpeg"} else suffix
    return f"data:image/{mime};base64," + base64.b64encode(read_bytes(path)).decode("ascii")


def build_html(markdown: str, logo: Path | None, subtitle: str, split_paragraphs: bool) -> str:
    lines = markdown.splitlines()
    title = None
    body_lines: list[str] = []
    for line in lines:
        if title is None and line.startswith("# "):
            title = line[2:].strip()
        else:
            body_lines.append(line)
    title = title or "Ebook"

    match = re.match(CHUONG + r"\s+(\d+)\s+-\s+(.+)", title, flags=re.I)
    chapter_no = match.group(1) if match else "01"
    chapter_title = match.group(2) if match else title
    logo_html = f'<img class="cover-logo" src="{data_uri(logo)}" alt="logo">' if logo else ""

    parts: list[str] = [
        (
            '<section class="cover">'
            f"{logo_html}"
            f'<div class="kicker">{CHUONG} {html.escape(chapter_no)}</div>'
            f"<h1>{html.escape(chapter_title)}</h1>"
            f'<div class="subtitle">{html.escape(subtitle)}</div>'
            "</section>"
        )
    ]

    in_ul = False
    in_code = False
    code: list[str] = []
    paragraph: list[str] = []
    opened = False
    first = True

    def close_paragraph() -> None:
        nonlocal paragraph, first
        if not paragraph:
            return
        text = " ".join(item.strip() for item in paragraph if item.strip())
        for chunk in split_long_paragraph(text, split_paragraphs):
            cls = ' class="lead"' if first else ""
            parts.append(f"<p{cls}>{inline_markdown(chunk)}</p>")
            first = False
        paragraph = []

    def close_ul() -> None:
        nonlocal in_ul
        if in_ul:
            parts.append("</ul>")
            in_ul = False

    def open_section(kind: str = "normal") -> None:
        nonlocal opened
        if opened:
            parts.append("</section>")
        cls = "content-section" if kind == "normal" else f"content-section {kind}"
        parts.append(f'<section class="{cls}">')
        opened = True

    open_section()
    for raw in body_lines:
        line = raw.rstrip()
        if line.startswith("```"):
            close_paragraph()
            close_ul()
            if not in_code:
                in_code = True
                code = []
            else:
                parts.append("<pre><code>" + html.escape("\n".join(code)) + "</code></pre>")
                in_code = False
                code = []
            continue
        if in_code:
            code.append(line)
            continue
        if not line.strip():
            close_paragraph()
            close_ul()
            continue
        if line.startswith("## "):
            close_paragraph()
            close_ul()
            heading = line[3:].strip()
            lower = heading.lower()
            kind = "normal"
            if "chi can nho" in lower or "ch\u1ec9 c\u1ea7n nh\u1edb" in lower:
                kind = "remember"
            elif "bai tap cuoi chuong" in lower or "b\u00e0i t\u1eadp cu\u1ed1i ch\u01b0\u01a1ng" in lower:
                kind = "exercise"
            open_section(kind)
            parts.append(f"<h2>{inline_markdown(heading)}</h2>")
            continue
        if line.startswith("- "):
            close_paragraph()
            if not in_ul:
                parts.append("<ul>")
                in_ul = True
            parts.append(f"<li>{inline_markdown(line[2:].strip())}</li>")
            continue
        paragraph.append(line)

    close_paragraph()
    close_ul()
    if opened:
        parts.append("</section>")

    css = r'''
@page { size: A4; margin: 20mm 19mm 22mm 19mm; }
*{box-sizing:border-box} html,body{margin:0;padding:0}
body{font-family:"Segoe UI",Arial,sans-serif;font-size:11.2pt;line-height:1.68;color:#25313d;background:#fff;text-rendering:optimizeLegibility}
.cover{page-break-after:always;min-height:246mm;display:flex;flex-direction:column;justify-content:center;border-left:5mm solid #1f5f7a;padding-left:16mm;position:relative}
.cover-logo{position:absolute;top:13mm;right:7mm;width:42mm;height:auto;object-fit:contain}
.cover .kicker{color:#1f5f7a;font-size:12pt;font-weight:700;margin-bottom:13mm}
.cover h1{font-size:32pt;line-height:1.18;color:#13293d;margin:0 0 12mm 0;font-weight:750;max-width:150mm}
.cover .subtitle{font-size:13pt;color:#52616f;border-top:1px solid #d7dee6;padding-top:6mm;width:76%}
.content-section{margin:0 0 15pt 0}
p{margin:0 0 11pt 0;text-align:justify;orphans:3;widows:3}
p.lead{font-size:12.4pt;line-height:1.62;color:#16324a;font-weight:500;text-align:left;border-left:3px solid #1f5f7a;padding-left:11pt;margin-bottom:15pt}
h2{break-after:avoid;page-break-after:avoid;font-size:16.5pt;line-height:1.28;color:#1f5f7a;margin:24pt 0 10pt 0;padding-top:7pt;border-top:1px solid #dce5eb}
ul{margin:0 0 13pt 18pt;padding:0}
li{margin:5pt 0;padding-left:2pt;line-height:1.58}
li::marker{color:#1f5f7a}
code{font-family:Consolas,"Courier New",monospace;font-size:.92em;background:#eef4f6;color:#0f3d4d;padding:.8pt 2.5pt;border-radius:3pt}
pre{background:#f4f7f9;border:1px solid #d7dee6;border-radius:6pt;padding:10pt 12pt;white-space:pre-wrap;line-height:1.45;margin:0 0 13pt 0}
.remember,.exercise{border:1px solid #d7e5ea;border-left:4pt solid #1f5f7a;background:#f7fbfc;padding:0 12pt 8pt 12pt;margin-top:18pt;break-inside:avoid;page-break-inside:avoid}
.remember h2,.exercise h2{border-top:0;margin-top:12pt;padding-top:0}
.exercise{background:#fbfaf7;border-left-color:#b7791f}
.exercise h2{color:#9a5b11}
@media print{body{-webkit-print-color-adjust:exact;print-color-adjust:exact}}
'''
    return (
        "<!doctype html><html lang=\"vi\"><head><meta charset=\"utf-8\">"
        f"<title>{html.escape(title)}</title><style>{css}</style></head><body>"
        + "".join(parts)
        + "</body></html>"
    )


def export_pdf(input_path: Path, output_path: Path, logo: Path | None, subtitle: str, split_paragraphs: bool) -> None:
    browser = find_browser()
    markdown = read_text_utf8(input_path)
    rendered = build_html(markdown, logo, subtitle, split_paragraphs)
    with tempfile.TemporaryDirectory() as tmpdir:
        html_path = Path(tmpdir) / "ebook_print.html"
        pdf_path = Path(tmpdir) / "ebook_print.pdf"
        html_path.write_text(rendered, encoding="utf-8")
        uri = html_path.resolve().as_uri()
        subprocess.run(
            [
                browser,
                "--headless=new",
                "--disable-gpu",
                "--no-first-run",
                "--disable-extensions",
                "--no-pdf-header-footer",
                f"--print-to-pdf={pdf_path}",
                uri,
            ],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        deadline = time.time() + 20
        while not pdf_path.exists():
            if time.time() > deadline:
                raise RuntimeError("Chrome/Edge khong tao file PDF dung han.")
            time.sleep(0.25)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(str(pdf_path), long_path(output_path))


def main() -> int:
    parser = argparse.ArgumentParser(description="Xuat Markdown chuong sach thanh PDF ebook de doc.")
    parser.add_argument("--input", required=True, type=Path, help="File Markdown nguon.")
    parser.add_argument("--output", type=Path, help="File PDF dich. Mac dinh cung ten voi Markdown.")
    parser.add_argument("--logo", type=Path, help="Logo PNG/JPG chen vao trang bia.")
    parser.add_argument("--subtitle", default=DEFAULT_SUBTITLE, help="Dong phu de tren trang bia.")
    parser.add_argument("--no-split-long-paragraphs", action="store_true", help="Khong tach doan dai trong ban PDF.")
    args = parser.parse_args()

    input_path = args.input.resolve()
    output_path = (args.output or input_path.with_suffix(".pdf")).resolve()
    logo_path = args.logo.resolve() if args.logo else None
    if not path_exists(input_path):
        raise FileNotFoundError(input_path)
    if logo_path and not path_exists(logo_path):
        raise FileNotFoundError(logo_path)
    export_pdf(input_path, output_path, logo_path, args.subtitle, not args.no_split_long_paragraphs)
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
