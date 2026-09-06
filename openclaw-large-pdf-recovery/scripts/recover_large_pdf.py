#!/usr/bin/env python3
"""Validate, split, and extract text from PDFs that exceed OpenClaw's staging limit."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

try:
    import pymupdf as fitz  # PyMuPDF 1.24+
except ImportError:  # pragma: no cover - compatibility with older environments
    try:
        import fitz  # type: ignore
    except ImportError as exc:
        raise SystemExit(
            "Khong tim thay PyMuPDF (fitz). Hay dung document venv: "
            "/root/.openclaw/tools/document-venv/bin/python"
        ) from exc


OPENCLAW_STAGING_LIMIT = 50 * 1024 * 1024
DEFAULT_TARGET_BYTES = 45 * 1024 * 1024
DEFAULT_MAX_DOWNLOAD_BYTES = 2000 * 1024 * 1024


def safe_name(value: str, fallback: str = "source.pdf") -> str:
    """Keep source-derived names harmless and portable."""
    value = Path(value).name
    value = re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("._")
    return value or fallback


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate_pdf(path: Path) -> None:
    if not path.is_file():
        raise ValueError(f"Khong tim thay file: {path}")
    if path.stat().st_size < 5:
        raise ValueError("File qua nho, khong phai PDF hop le")
    with path.open("rb") as handle:
        if handle.read(5) != b"%PDF-":
            raise ValueError("File khong co dau PDF (%PDF-)")


def download_url(url: str, destination: Path, max_bytes: int) -> tuple[str, int]:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https":
        raise ValueError("Chi chap nhan link HTTPS de tranh lo thong tin dang nhap")
    if not parsed.hostname:
        raise ValueError("Link HTTPS khong hop le")

    request = urllib.request.Request(url, headers={"User-Agent": "openclaw-large-pdf-recovery/1"})
    total = 0
    digest = hashlib.sha256()
    try:
        response = urllib.request.urlopen(request, timeout=60)
    except Exception as exc:
        raise RuntimeError(f"Tai file tu HTTPS that bai (host={parsed.hostname})") from exc
    with response:
        final_url = urllib.parse.urlparse(response.geturl())
        if final_url.scheme != "https":
            raise ValueError("Link tai ve bi redirect sang giao thuc khong an toan")
        content_length = response.headers.get("Content-Length")
        if content_length and content_length.isdigit() and int(content_length) > max_bytes:
            raise ValueError(
                f"File tu link vuot gioi han {max_bytes / 1024 / 1024:.0f} MiB"
            )
        with destination.open("wb") as handle:
            while True:
                block = response.read(1024 * 1024)
                if not block:
                    break
                total += len(block)
                if total > max_bytes:
                    handle.close()
                    destination.unlink(missing_ok=True)
                    raise ValueError(
                        f"File tu link vuot gioi han {max_bytes / 1024 / 1024:.0f} MiB"
                    )
                handle.write(block)
                digest.update(block)
    return parsed.hostname, total


def extract_page_text(doc: fitz.Document, page_index: int) -> str:
    try:
        return doc.load_page(page_index).get_text("text")
    except Exception:
        return ""


def ocr_status() -> tuple[bool, str]:
    tesseract = shutil.which("tesseract")
    pdftoppm = shutil.which("pdftoppm")
    if tesseract and pdftoppm:
        return True, "tesseract+pdftoppm"
    missing = ", ".join(name for name, value in (("tesseract", tesseract), ("pdftoppm", pdftoppm)) if not value)
    return False, f"thieu {missing}"


def split_pdf(source: Path, output_dir: Path, target_bytes: int, do_ocr: bool) -> dict:
    validate_pdf(source)
    output_dir.mkdir(parents=True, exist_ok=True)
    digest = sha256_file(source)
    try:
        src = fitz.open(source)
    except Exception as exc:
        raise ValueError("Khong mo duoc PDF; co the file bi hong hoac dat mat khau") from exc
    if src.needs_pass:
        src.close()
        raise ValueError("PDF dat mat khau; can ban khong ma hoa de xu ly tu dong")

    if src.page_count == 0:
        raise ValueError("PDF khong co trang")

    source_size = source.stat().st_size
    ocr_available, ocr_detail = ocr_status()
    manifest = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source": {
            "name": source.name,
            "kind": "local",
            "size_bytes": source_size,
            "sha256": digest,
            "pages": src.page_count,
        },
        "policy": {
            "openclaw_staging_limit_bytes": OPENCLAW_STAGING_LIMIT,
            "target_part_bytes": target_bytes,
            "target_part_mib": round(target_bytes / 1024 / 1024, 2),
        },
        "ocr": {
            "requested": do_ocr,
            "available": ocr_available,
            "detail": ocr_detail,
            "performed": False,
        },
        "parts": [],
        "warnings": [],
    }
    if target_bytes >= OPENCLAW_STAGING_LIMIT:
        manifest["warnings"].append("Target phai nho hon 50 MiB de tranh loi staging OpenClaw")
    if do_ocr and not ocr_available:
        manifest["warnings"].append(f"Khong OCR: {ocr_detail}; van tach PDF va trich text co san")

    stem = safe_name(source.stem, "document")
    start = 0
    part_number = 1
    while start < src.page_count:
        end_exclusive = start
        previous_tmp: Path | None = None
        last_good_end: int | None = None
        while end_exclusive < src.page_count:
            candidate = fitz.open()
            candidate.insert_pdf(src, from_page=start, to_page=end_exclusive)
            fd, tmp_name = tempfile.mkstemp(prefix=".part-", suffix=".pdf", dir=output_dir)
            os.close(fd)
            candidate.save(tmp_name, garbage=3, deflate=True)
            candidate.close()
            candidate_size = os.path.getsize(tmp_name)
            if candidate_size > target_bytes and end_exclusive > start:
                os.unlink(tmp_name)
                break
            if previous_tmp:
                os.unlink(previous_tmp)
            previous_tmp = Path(tmp_name)
            last_good_end = end_exclusive + 1
            end_exclusive += 1
            if candidate_size > target_bytes:
                manifest["warnings"].append(
                    f"Trang {last_good_end} mot minh vuot target ({candidate_size} bytes); khong the tach trong mot trang"
                )
                break

        if previous_tmp is None:
            raise RuntimeError("Khong tao duoc part PDF")
        page_end = last_good_end or (start + 1)
        final_name = f"{stem}.part-{part_number:03d}.pages-{start + 1:03d}-{page_end:03d}.pdf"
        final_path = output_dir / final_name
        os.replace(previous_tmp, final_path)

        part_doc = fitz.open(final_path)
        text = "".join(extract_page_text(part_doc, i) for i in range(part_doc.page_count))
        part_doc.close()
        text_path = output_dir / f"{final_path.stem}.txt"
        text_path.write_text(text, encoding="utf-8")
        part_entry = {
            "file": final_path.name,
            "text_file": text_path.name,
            "page_start": start + 1,
            "page_end": page_end,
            "pages": page_end - start,
            "size_bytes": final_path.stat().st_size,
            "sha256": sha256_file(final_path),
            "extracted_text_chars": len(text),
        }
        manifest["parts"].append(part_entry)
        start = page_end
        part_number += 1

    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def inspect_pdf(source: Path) -> dict:
    validate_pdf(source)
    doc = fitz.open(source)
    text_chars = sum(len(extract_page_text(doc, i)) for i in range(doc.page_count))
    result = {
        "name": source.name,
        "size_bytes": source.stat().st_size,
        "sha256": sha256_file(source),
        "pages": doc.page_count,
        "extracted_text_chars": text_chars,
        "ocr": ocr_status()[1],
    }
    doc.close()
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--input", type=Path, help="Duong dan PDF local")
    source.add_argument("--url", help="Link HTTPS den PDF (khong ghi URL vao manifest/log)")
    parser.add_argument("--output-dir", type=Path, help="Thu muc job output")
    parser.add_argument("--target-mb", type=float, default=45.0, help="Kich thuoc part muc tieu, mac dinh 45 MiB")
    parser.add_argument("--max-download-mb", type=float, default=2000.0, help="Gioi han tai tu link, mac dinh 2000 MiB")
    parser.add_argument("--ocr", action="store_true", help="Kiem tra va ghi nhan kha nang OCR cua container")
    parser.add_argument("--dry-run", action="store_true", help="Chi kiem tra PDF, khong tao part")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.target_mb <= 0 or args.target_mb >= 49:
        raise SystemExit("--target-mb phai nam trong khoang (0, 49), nen dung 45")
    target_bytes = int(args.target_mb * 1024 * 1024)
    max_download_bytes = int(args.max_download_mb * 1024 * 1024)

    temp_dir: Path | None = None
    try:
        if args.url:
            base_dir = args.output_dir or Path.cwd() / "large-pdf-job"
            base_dir.mkdir(parents=True, exist_ok=True)
            temp_dir = Path(tempfile.mkdtemp(prefix=".download-", dir=base_dir))
            source = temp_dir / "source.pdf"
            host, downloaded = download_url(args.url, source, max_download_bytes)
            source_kind = "url"
            source_host = host
            if not args.dry_run:
                job_dir = base_dir / f"job-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
            else:
                job_dir = base_dir
        else:
            source = args.input.resolve()
            source_kind = "local"
            source_host = None
            downloaded = source.stat().st_size if source.exists() else 0
            job_dir = args.output_dir or source.parent / f"{safe_name(source.stem)}-parts"

        summary = inspect_pdf(source)
        summary["source_kind"] = source_kind
        if source_host:
            summary["source_url_host"] = source_host
        if args.url:
            summary["downloaded_bytes"] = downloaded
        if args.dry_run:
            print(json.dumps(summary, ensure_ascii=False, indent=2))
            return 0

        manifest = split_pdf(source, job_dir, target_bytes, args.ocr)
        if source_kind == "url":
            manifest["source"]["kind"] = "url"
            manifest["source"]["url_host"] = source_host
            manifest_path = job_dir / "manifest.json"
            manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({
            "job_dir": str(job_dir),
            "parts": len(manifest["parts"]),
            "source_pages": manifest["source"]["pages"],
            "source_size_bytes": manifest["source"]["size_bytes"],
            "warnings": manifest["warnings"],
        }, ensure_ascii=False, indent=2))
        return 0
    finally:
        if temp_dir:
            shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, RuntimeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
