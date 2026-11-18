#!/usr/bin/env python3
"""Read a small Excel/CSV preview without emitting an unbounded tool result."""

import argparse
import json
import math
import os
from pathlib import Path
import sys


MAX_OUTPUT_BYTES = 4096
MAX_COLUMNS = 12
MAX_TEXT_CHARS = 96


def short_text(value):
    text = str(value)
    return text if len(text) <= MAX_TEXT_CHARS else text[:MAX_TEXT_CHARS - 3] + "..."


def bounded_json(report):
    def encode():
        return json.dumps(report, ensure_ascii=False, allow_nan=False,
                          separators=(",", ":")) + "\n"

    output = encode()
    while len(output.encode("utf-8")) > MAX_OUTPUT_BYTES:
        report["truncated"] = True
        if report.get("sample"):
            report["sample"].pop()
        elif report.get("columns"):
            report["columns"].pop()
        elif report.get("sheet_names"):
            report["sheet_names"].pop()
        else:
            raise ValueError("Preview metadata exceeds output budget")
        output = encode()
    return output


def preview(args):
    source = args.input
    suffix = source.suffix.lower()
    if suffix not in {".xlsx", ".xlsm", ".csv"}:
        raise ValueError("Supported formats: xlsx, xlsm, csv")
    if not source.is_file() or not os.access(source, os.R_OK):
        raise ValueError("Input must be a readable file")
    if args.sheet is not None and suffix == ".csv":
        raise ValueError("Sheet selection applies only to Excel")
    report = {"status": "ready" if args.dry_run else "ok",
              "input_name": short_text(source.name),
              "input_bytes": source.stat().st_size,
              "dry_run": args.dry_run,
              "truncated": len(source.name) > MAX_TEXT_CHARS}
    if args.dry_run:
        return report

    import pandas as pd

    if suffix == ".csv":
        frame = pd.read_csv(source, nrows=args.sample_rows)
    else:
        with pd.ExcelFile(source, engine="openpyxl") as book:
            sheet = args.sheet if args.sheet is not None else book.sheet_names[0]
            if sheet not in book.sheet_names:
                raise ValueError("Requested sheet does not exist")
            report.update(sheet=short_text(sheet), sheet_count=len(book.sheet_names),
                          sheet_names=[short_text(s) for s in book.sheet_names[:10]])
            report["truncated"] = (report["truncated"] or len(book.sheet_names) > 10 or
                                   any(len(s) > MAX_TEXT_CHARS for s in book.sheet_names))
            frame = pd.read_excel(book, sheet_name=sheet, nrows=args.sample_rows)

    def cell(value):
        if pd.isna(value):
            return None
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return value if not isinstance(value, float) or math.isfinite(value) else str(value)
        text = str(value)
        if len(text) > MAX_TEXT_CHARS:
            report["truncated"] = True
        return short_text(text)

    report.update(preview_only=True, total_rows=None, preview_rows_read=len(frame),
                  column_count=len(frame.columns), columns=[], sample=[])
    if len(frame.columns) > MAX_COLUMNS:
        report["truncated"] = True
    for name, dtype in zip(frame.columns[:MAX_COLUMNS], frame.dtypes.iloc[:MAX_COLUMNS]):
        if len(str(name)) > MAX_TEXT_CHARS:
            report["truncated"] = True
        report["columns"].append({"name": short_text(name), "dtype": str(dtype)})
    # Positional rows preserve distinct columns even when preview labels truncate alike.
    report["sample"] = [[cell(v) for v in row] for row in
                        frame.iloc[:, :MAX_COLUMNS].itertuples(index=False, name=None)]
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--sheet")
    parser.add_argument("--sample-rows", type=int, choices=range(0, 6), default=3)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    try:
        sys.stdout.write(bounded_json(preview(args)))
    except Exception as exc:
        # Parser errors can contain private cell contents; expose only the error class.
        sys.stdout.write(json.dumps({"status": "error", "error_type": type(exc).__name__,
                                    "hint": "Check the input format, sheet, encoding and pandas/openpyxl installation."}) + "\n")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
