#!/usr/bin/env python3
"""One bounded pandas coordinator for an Excel/CSV request.

The default path reads headers only. A filtered run reads only the requested
sheet/columns and at most max_scan_rows, writes the complete artifact, and
prints one compact JSON summary. It never writes the source workbook.
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import math
import os
import signal
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any

MAX_STDOUT = 2000
MAX_HEADERS = 80
MAX_SHEETS = 20


class TaskError(Exception):
    pass


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise TaskError("invalid_arguments")


def emit(payload: dict[str, Any], code: int = 0) -> int:
    """Emit one bounded valid JSON record; never slice serialized JSON."""
    payload = dict(payload)
    payload.setdefault("ok", code == 0)
    text = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), default=str)
    if len(text.encode("utf-8")) + 1 > MAX_STDOUT:
        # Preserve status and artifact location while dropping optional samples.
        for key in ("sample", "headers", "headers_by_sheet", "sheets", "columns", "totals_in_window"):
            payload.pop(key, None)
        payload["output_truncated"] = True
        text = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), default=str)
    if len(text.encode("utf-8")) + 1 > MAX_STDOUT:
        text = json.dumps({"ok": False, "error": "summary_output_limit"}, separators=(",", ":"))
        code = 1
    print(text)
    return code


def serial(value: Any) -> Any:
    if hasattr(value, "item"):
        value = value.item()
    if value is None or isinstance(value, (str, int, bool)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return str(value)


def parse_args() -> argparse.Namespace:
    p = Parser(description=__doc__)
    p.add_argument("input", help="CSV/XLSX/XLSM input path")
    p.add_argument("--sheet", help="exact workbook sheet for a filtered run")
    p.add_argument("--contains", nargs=2, metavar=("COLUMN", "TEXT"), help="case-insensitive literal filter")
    p.add_argument("--columns", nargs="+", help="columns to retain in the artifact/sample")
    p.add_argument("--header-row", type=int, default=0)
    p.add_argument("--max-scan-rows", type=int, default=10000)
    p.add_argument("--limit", type=int, default=5, help="summary sample size (1..5); artifact keeps all matches in the bounded window")
    p.add_argument("--sum", nargs="+", dest="sum_columns", default=[], help="numeric columns to total inside the matched window")
    p.add_argument("--task-id", default="excel-task")
    p.add_argument("--timeout-seconds", type=int, default=60, help="total run deadline (5..90 seconds)")
    p.add_argument("--output", help="artifact path, required for filtered runs; must be under workspace/output")
    return p.parse_args()


def workspace_root() -> Path:
    return Path(__file__).resolve().parents[1]


def output_path(raw: str | None, task_id: str, filtered: bool) -> Path | None:
    if not filtered:
        return None
    if not raw:
        raise TaskError("output_required_for_filtered_run")
    root = (workspace_root() / "output").resolve()
    candidate = Path(raw)
    if not candidate.is_absolute():
        candidate = workspace_root() / candidate
    candidate = candidate.resolve()
    if not candidate.is_relative_to(root):
        raise TaskError("output_must_be_under_workspace_output")
    if candidate.suffix.lower() != ".json":
        raise TaskError("output_must_be_json")
    candidate.parent.mkdir(parents=True, exist_ok=True)
    return candidate


def import_pandas():
    try:
        import pandas as pd  # type: ignore
        return pd
    except Exception as exc:  # dependency details must not enter group context
        raise TaskError("pandas_unavailable_use_member_excel_venv") from exc


def read_headers(pd, path: Path, header_row: int) -> dict[str, Any]:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        frame = pd.read_csv(path, header=header_row, nrows=0, encoding="utf-8-sig")
        return {"sheets": [], "headers": [str(x) for x in frame.columns][:MAX_HEADERS]}
    if suffix not in {".xlsx", ".xlsm"}:
        raise TaskError("unsupported_file_type")
    with pd.ExcelFile(path) as book:
        sheet_count = len(book.sheet_names)
        sheets = [str(x) for x in book.sheet_names[:MAX_SHEETS]]
        headers: dict[str, list[str]] = {}
        for sheet in sheets:
            frame = pd.read_excel(book, sheet_name=sheet, header=header_row, nrows=0)
            headers[sheet] = [str(x) for x in frame.columns][:MAX_HEADERS]
    return {"sheet_count": sheet_count, "sheets_omitted": sheet_count - len(sheets),
            "sheets": sheets, "headers_by_sheet": headers}


def read_filtered(pd, path: Path, args: argparse.Namespace, out: Path) -> dict[str, Any]:
    if not args.contains:
        raise TaskError("filter_required")
    if args.header_row < 0 or args.header_row > 20:
        raise TaskError("invalid_header_row")
    if not 1 <= args.limit <= 5 or not 1 <= args.max_scan_rows <= 100000:
        raise TaskError("invalid_limits")
    if not all(part.strip() for part in args.contains):
        raise TaskError("empty_filter_not_allowed")
    usecols = list(dict.fromkeys([args.contains[0], *(args.columns or []), *args.sum_columns]))
    if len(usecols) > 40:
        raise TaskError("too_many_columns")
    suffix = path.suffix.lower()
    if suffix in {".xlsx", ".xlsm"} and not args.sheet:
        raise TaskError("sheet_required_for_workbook_filter")
    source = path
    if suffix == ".csv":
        header = pd.read_csv(source, header=args.header_row, nrows=0, encoding="utf-8-sig")
        if any(c not in header.columns for c in usecols):
            raise TaskError("requested_column_not_found")
        frame = pd.read_csv(source, header=args.header_row, usecols=usecols,
                            nrows=args.max_scan_rows, dtype=object, encoding="utf-8-sig")
        sheet = None
    elif suffix in {".xlsx", ".xlsm"}:
        sheet = args.sheet
        with pd.ExcelFile(source) as book:
            if sheet not in book.sheet_names:
                raise TaskError("sheet_not_found")
            header = pd.read_excel(book, sheet_name=sheet, header=args.header_row, nrows=0)
            if any(c not in header.columns for c in usecols):
                raise TaskError("requested_column_not_found")
            frame = pd.read_excel(book, sheet_name=sheet, header=args.header_row,
                                  usecols=usecols, nrows=args.max_scan_rows, dtype=object)
    else:
        raise TaskError("unsupported_file_type")
    frame.columns = [str(c) for c in frame.columns]
    filter_col, filter_text = args.contains
    if filter_col not in frame.columns:
        raise TaskError("filter_column_not_found")
    columns = args.columns or [filter_col]
    missing = [c for c in columns if c not in frame.columns]
    if missing:
        raise TaskError("requested_column_not_found")
    mask = frame[filter_col].fillna("").astype(str).str.contains(filter_text, case=False, regex=False)
    selected = frame.loc[mask, columns]
    totals = {}
    for column in args.sum_columns:
        if column not in frame.columns:
            raise TaskError("sum_column_not_found")
        try:
            totals[column] = serial(pd.to_numeric(frame.loc[mask, column], errors="raise").sum())
        except (ValueError, TypeError) as exc:
            raise TaskError("sum_column_has_non_numeric_values") from exc
    records = [{str(k): serial(v) for k, v in row.items()} for row in selected.to_dict(orient="records")]
    artifact = {
        "task_id": args.task_id,
        "input": path.name,
        "sheet": sheet,
        "filter": {"column": filter_col, "contains": filter_text},
        "columns": columns,
        "rows_scanned": int(len(frame)),
        "matches_in_window": int(mask.sum()),
        "records": records,
        "totals_in_window": totals,
        "scan_limit_reached": len(frame) >= args.max_scan_rows,
        "scope": "matches_within_scanned_window_only",
    }
    temp = out.with_suffix(out.suffix + ".tmp")
    temp.write_text(json.dumps(artifact, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    os.replace(temp, out)
    sample = records[:args.limit]
    return {"ok": True, "task_id": args.task_id, "mode": "filtered", "input": path.name,
            "sheet": sheet, "rows_scanned": int(len(frame)), "matches_in_window": int(mask.sum()),
            "sample": sample, "totals_in_window": totals,
            "scan_limit_reached": len(frame) >= args.max_scan_rows,
            "scope": "matches_within_scanned_window_only",
            "artifact": str(out.relative_to(workspace_root()))}


def digest_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def atomic_json(path: Path, value: dict) -> None:
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    os.replace(temp, path)


def execute_once(pd, path: Path, args: argparse.Namespace, out: Path) -> dict:
    """Reuse a verified result for the same request; restart an interrupted phase."""
    state_path = out.with_suffix(".state.json")
    with out.with_suffix(".lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise TaskError("request_already_running") from exc
        source_digest = digest_file(path)
        spec = {**vars(args), "input": str(path.resolve()), "input_sha256": source_digest}
        fingerprint = hashlib.sha256(json.dumps(spec, sort_keys=True).encode()).hexdigest()
        if state_path.exists():
            state = json.loads(state_path.read_text())
            if state.get("fingerprint") != fingerprint:
                raise TaskError("output_belongs_to_different_request_use_new_output")
            if state.get("phase") == "completed":
                if not out.is_file() or digest_file(out) != state.get("artifact_sha256"):
                    raise TaskError("completed_artifact_changed_use_new_output")
                return {**state["summary"], "cached": True}
        elif out.exists():
            raise TaskError("output_exists_without_request_state_use_new_output")
        atomic_json(state_path, {"fingerprint": fingerprint, "task_id": args.task_id, "phase": "processing"})
        summary = read_filtered(pd, path, args, out)
        if digest_file(path) != source_digest:
            raise TaskError("source_changed_during_processing_use_new_output")
        atomic_json(state_path, {"fingerprint": fingerprint, "task_id": args.task_id,
                                "phase": "completed", "artifact_sha256": digest_file(out), "summary": summary})
        return summary


def main() -> int:
    os.umask(0o077)
    try:
        args = parse_args()
        path = Path(args.input).expanduser()
        if not 5 <= args.timeout_seconds <= 90:
            raise TaskError("invalid_timeout")
        def deadline(signum, frame):
            raise TaskError("task_timeout_reduce_scan_window")
        signal.signal(signal.SIGALRM, deadline)
        signal.alarm(args.timeout_seconds)
        if not path.is_file():
            raise TaskError("input_not_found")
        if args.header_row < 0 or args.header_row > 20:
            raise TaskError("invalid_header_row")
        if not args.task_id or len(args.task_id) > 120:
            raise TaskError("invalid_task_id")
        filtered = bool(args.contains)
        if (args.columns or args.sum_columns) and not filtered:
            raise TaskError("columns_require_filter")
        pd = import_pandas()
        if not filtered:
            meta = read_headers(pd, path, args.header_row)
            return emit({"ok": True, "mode": "headers_only", "input": path.name,
                         "bytes": path.stat().st_size, **meta})
        out = output_path(args.output, args.task_id, True)
        assert out is not None
        if out == path.resolve():
            raise TaskError("output_cannot_replace_source")
        return emit(execute_once(pd, path, args, out))
    except TaskError as exc:
        return emit({"ok": False, "error": str(exc)}, 1)
    except Exception:
        return emit({"ok": False, "error": "excel_task_failed"}, 1)
    finally:
        signal.alarm(0)


if __name__ == "__main__":
    sys.exit(main())
