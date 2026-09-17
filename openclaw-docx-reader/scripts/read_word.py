#!/usr/bin/env python3
"""Safely extract readable text from Word OOXML files for an OpenClaw member.

The OpenClaw media preprocessor currently extracts plain text and PDF, but not
Office OOXML.  This small dependency-free reader is intentionally local-only:
it reads a validated .docx/.docm ZIP, extracts Word XML text, and writes UTF-8
text.  It does not upload, modify, or delete the source document.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import unicodedata
import zipfile
from pathlib import Path
from typing import Iterable
from xml.etree import ElementTree as ET


W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
W = "{" + W_NS + "}"
SUPPORTED_SUFFIXES = {".docx", ".docm", ".dotx", ".dotm"}
MAX_SOURCE_BYTES = 25 * 1024 * 1024
MAX_MEMBERS = 5000
MAX_UNCOMPRESSED_BYTES = 150 * 1024 * 1024
MAX_TEXT_CHARS = 2_000_000


def _safe_relative(name: str) -> bool:
    """Reject absolute and traversal paths inside a ZIP archive."""
    p = Path(name)
    return not p.is_absolute() and ".." not in p.parts


def _norm(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).casefold()
    return "".join(ch for ch in value if ch.isalnum())


def choose_input(path: str | None, inbound_dir: str | None, name: str | None) -> Path:
    if path:
        candidate = Path(path).expanduser().resolve()
        if not candidate.is_file():
            raise FileNotFoundError(f"Không tìm thấy tệp: {candidate}")
        return candidate

    root = Path(inbound_dir or "/root/.openclaw/media/inbound").expanduser().resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"Không tìm thấy thư mục inbound: {root}")
    candidates = [
        p for p in root.iterdir()
        if p.is_file() and p.suffix.casefold() in SUPPORTED_SUFFIXES
    ]
    if name:
        needle = _norm(Path(name).stem)
        filtered = [p for p in candidates if needle and needle in _norm(p.stem)]
        if filtered:
            candidates = filtered
        else:
            raise FileNotFoundError(
                f"Không tìm thấy Word phù hợp với tên '{name}' trong {root}"
            )
    if not candidates:
        raise FileNotFoundError(f"Không có tệp Word trong {root}")
    return max(candidates, key=lambda p: p.stat().st_mtime_ns).resolve()


def _run_legacy_doc(path: Path) -> str:
    antiword = shutil.which("antiword")
    if not antiword:
        raise RuntimeError(
            "Tệp .doc đời cũ không có bộ đọc trên container; hãy lưu lại thành .docx hoặc PDF."
        )
    proc = subprocess.run(
        [antiword, str(path)],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
    )
    if proc.returncode:
        raise RuntimeError(f"antiword không đọc được tệp (mã {proc.returncode})")
    return proc.stdout


def _text_of(node: ET.Element) -> str:
    """Extract text runs while retaining tabs and explicit line breaks."""
    parts: list[str] = []
    for child in node.iter():
        tag = child.tag
        if tag == W + "t" or tag == W + "delText":
            parts.append(child.text or "")
        elif tag == W + "tab":
            parts.append("\t")
        elif tag in {W + "br", W + "cr"}:
            parts.append("\n")
    return "".join(parts)


def _clean_lines(lines: Iterable[str]) -> str:
    cleaned: list[str] = []
    previous_blank = False
    for raw in lines:
        line = raw.replace("\u00a0", " ").replace("\r", "")
        line = " ".join(line.split()) if "\t" not in line else "\t".join(
            " ".join(part.split()) for part in line.split("\t")
        )
        line = line.strip(" \t")
        if not line:
            if not previous_blank:
                cleaned.append("")
            previous_blank = True
            continue
        cleaned.append(line)
        previous_blank = False
    while cleaned and not cleaned[-1]:
        cleaned.pop()
    return "\n".join(cleaned)


def _extract_part(root: ET.Element) -> tuple[list[str], int]:
    lines: list[str] = []
    tables = 0
    body = root.find(W + "body")
    blocks = list(body) if body is not None else list(root)
    for block in blocks:
        if block.tag == W + "tbl":
            tables += 1
            rows: list[str] = []
            for row in block.findall(".//" + W + "tr"):
                cells: list[str] = []
                for cell in row.findall("./" + W + "tc"):
                    cells.append(_text_of(cell).replace("\n", " ").strip())
                if cells:
                    rows.append("\t".join(cells))
            lines.extend(rows)
            lines.append("")
        elif block.tag == W + "p":
            lines.append(_text_of(block))
        else:
            # Headers/footers/notes may not have a w:body wrapper.
            if block.tag in {W + "p", W + "tbl"}:
                lines.append(_text_of(block))
    if not blocks and root.tag == W + "p":
        lines.append(_text_of(root))
    return lines, tables


def extract_docx(path: Path) -> tuple[str, dict[str, int | str]]:
    size = path.stat().st_size
    if size > MAX_SOURCE_BYTES:
        raise ValueError(f"Tệp quá lớn ({size} bytes; giới hạn {MAX_SOURCE_BYTES} bytes)")
    if path.suffix.casefold() not in SUPPORTED_SUFFIXES:
        if path.suffix.casefold() == ".doc":
            return _run_legacy_doc(path), {"source": str(path), "format": ".doc"}
        raise ValueError("Chỉ hỗ trợ .docx/.docm/.dotx/.dotm (hoặc .doc khi có antiword)")

    with zipfile.ZipFile(path) as archive:
        infos = archive.infolist()
        if len(infos) > MAX_MEMBERS:
            raise ValueError("Word ZIP có quá nhiều thành phần")
        total = 0
        for info in infos:
            if not _safe_relative(info.filename):
                raise ValueError("Word ZIP chứa đường dẫn không an toàn")
            total += info.file_size
            if total > MAX_UNCOMPRESSED_BYTES:
                raise ValueError("Word ZIP giải nén vượt giới hạn an toàn")
        bad_member = archive.testzip()
        if bad_member:
            raise ValueError(f"Word ZIP hỏng CRC tại thành phần: {bad_member}")
        names = set(archive.namelist())
        if "word/document.xml" not in names:
            raise ValueError("Không phải Word OOXML hợp lệ: thiếu word/document.xml")

        ordered_parts: list[tuple[str, str]] = [("Nội dung chính", "word/document.xml")]
        for prefix, label in (
            ("word/header", "Đầu trang"),
            ("word/footer", "Chân trang"),
            ("word/footnotes", "Chú thích cuối trang"),
            ("word/endnotes", "Chú thích cuối tài liệu"),
            ("word/comments", "Bình luận"),
        ):
            for member in sorted(n for n in names if n.startswith(prefix) and n.endswith(".xml")):
                ordered_parts.append((label, member))

        all_lines: list[str] = []
        table_count = 0
        for label, member in ordered_parts:
            try:
                root = ET.fromstring(archive.read(member))
            except ET.ParseError as exc:
                raise ValueError(f"XML lỗi trong {member}: {exc}") from exc
            lines, tables = _extract_part(root)
            table_count += tables
            text = _clean_lines(lines)
            if text:
                if label != "Nội dung chính":
                    all_lines.extend([f"[{label}]", text, ""])
                else:
                    all_lines.extend([text, ""])

    text = _clean_lines(all_lines)
    if len(text) > MAX_TEXT_CHARS:
        text = text[:MAX_TEXT_CHARS].rstrip() + "\n[Đã cắt bớt vì vượt giới hạn ký tự]"
    return text, {
        "source": str(path),
        "format": path.suffix.casefold(),
        "bytes": size,
        "characters": len(text),
        "tables": table_count,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Đọc Word cục bộ cho OpenClaw")
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--input", help="Đường dẫn .docx/.docm cụ thể")
    source.add_argument("--name", help="Tên gốc hoặc một phần tên file Telegram")
    parser.add_argument("--inbound-dir", default="/root/.openclaw/media/inbound")
    parser.add_argument("--output", help="Ghi text ra file UTF-8 thay vì stdout")
    parser.add_argument("--json", action="store_true", help="In metadata JSON sau phần text")
    args = parser.parse_args()
    try:
        path = choose_input(args.input, args.inbound_dir, args.name)
        text, meta = extract_docx(path)
        if args.output:
            out = Path(args.output).expanduser().resolve()
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(text + ("\n" if text else ""), encoding="utf-8")
        else:
            sys.stdout.write(text)
            if text:
                sys.stdout.write("\n")
        if args.json:
            sys.stderr.write(json.dumps(meta, ensure_ascii=False) + "\n")
        return 0
    except (OSError, ValueError, RuntimeError, zipfile.BadZipFile) as exc:
        print(f"read_word: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
