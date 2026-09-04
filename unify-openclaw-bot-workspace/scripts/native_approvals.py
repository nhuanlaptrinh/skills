"""Small adapter for OpenClaw 2026.8 native exec-approval storage.

OpenClaw 2026.8 stores the approval document in
``state/openclaw.sqlite#exec_approvals_config``.  Older releases used
``exec-approvals.json``.  The owner helpers need to understand both without
printing the socket token or creating a legacy file on a native install.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import shutil
import sqlite3
import stat
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from typing import Any


class NativeApprovalsError(RuntimeError):
    """Raised when the native approval store cannot be read or updated."""


@dataclass(frozen=True)
class ApprovalSnapshot:
    backend: str
    root: pathlib.Path
    path: pathlib.Path
    legacy_path: pathlib.Path
    db_path: pathlib.Path
    exists: bool
    raw: str | None
    document: dict[str, Any]

    @property
    def hash(self) -> str:
        value = self.raw.encode("utf-8") if self.raw is not None else b""
        return hashlib.sha256(value).hexdigest()

    @property
    def locator(self) -> str:
        if self.backend == "sqlite":
            return f"{self.db_path}#exec_approvals_config"
        return str(self.legacy_path)


def _default_document() -> dict[str, Any]:
    return {"version": 1, "defaults": {}, "agents": {}}


def _assert_safe_file(path: pathlib.Path, label: str) -> None:
    if path.is_symlink():
        raise NativeApprovalsError(f"Refusing symlinked {label}: {path}")
    if path.exists() and not path.is_file():
        raise NativeApprovalsError(f"{label} is not a regular file: {path}")


def _assert_safe_state_dir(root: pathlib.Path) -> None:
    state_dir = root / "state"
    if state_dir.is_symlink():
        raise NativeApprovalsError(f"Refusing symlinked native state directory: {state_dir}")
    if state_dir.exists() and not state_dir.is_dir():
        raise NativeApprovalsError(f"Native state path is not a directory: {state_dir}")


def _read_sqlite_document(db_path: pathlib.Path) -> tuple[bool, str | None]:
    if not db_path.exists():
        return False, None
    _assert_safe_file(db_path, "native approvals database")
    try:
        # Read through SQLite's URI mode so a dry-run never creates a database.
        connection = sqlite3.connect(
            f"file:{db_path}?mode=ro", uri=True, timeout=2
        )
    except sqlite3.Error as error:
        raise NativeApprovalsError(f"Cannot open native approvals database: {error}") from error
    try:
        connection.execute("PRAGMA query_only=ON")
        table = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='exec_approvals_config'"
        ).fetchone()
        if not table:
            # A non-OpenClaw SQLite file must not be overwritten accidentally.
            return False, None
        row = connection.execute(
            "SELECT raw_json FROM exec_approvals_config WHERE config_key = ?",
            ("current",),
        ).fetchone()
        return True, (str(row[0]) if row and row[0] is not None else None)
    except sqlite3.Error as error:
        raise NativeApprovalsError(f"Cannot inspect native approvals database: {error}") from error
    finally:
        connection.close()


def load_approvals(openclaw_root: pathlib.Path | str) -> ApprovalSnapshot:
    """Load the active approval document without creating legacy files."""

    requested_root = pathlib.Path(openclaw_root).expanduser()
    if requested_root.is_symlink():
        raise NativeApprovalsError(f"Refusing symlinked OpenClaw root: {requested_root}")
    root = requested_root.resolve()
    _assert_safe_state_dir(root)
    legacy_path = root / "exec-approvals.json"
    db_path = root / "state" / "openclaw.sqlite"
    _assert_safe_file(legacy_path, "legacy approvals file")
    native_available, raw = _read_sqlite_document(db_path)
    if native_available:
        document = _default_document() if raw is None else _parse(raw, db_path)
        return ApprovalSnapshot(
            "sqlite", root, db_path, legacy_path, db_path, raw is not None, raw, document
        )

    if legacy_path.exists():
        with legacy_path.open("r", encoding="utf-8") as handle:
            raw = handle.read()
        document = _parse(raw, legacy_path)
        return ApprovalSnapshot(
            "legacy", root, legacy_path, legacy_path, db_path, True, raw, document
        )

    if db_path.exists() and not native_available:
        raise NativeApprovalsError(
            f"Native approvals database has no OpenClaw schema: {db_path}"
        )

    # A fresh 2026.8 install has no row yet; the first native write creates it.
    return ApprovalSnapshot(
        "sqlite", root, db_path, legacy_path, db_path, False, None, _default_document()
    )


def _parse(raw: str, path: pathlib.Path) -> dict[str, Any]:
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as error:
        raise NativeApprovalsError(f"Invalid approvals JSON at {path}: {error.msg}") from error
    if not isinstance(value, dict):
        raise NativeApprovalsError(f"Approvals JSON root must be an object: {path}")
    return value


def _cli_environment(
    snapshot: ApprovalSnapshot,
    config_path: pathlib.Path | None,
    runtime_home: str | None,
) -> dict[str, str]:
    environment = os.environ.copy()
    environment["OPENCLAW_STATE_DIR"] = str(snapshot.root)
    environment["OPENCLAW_CONFIG_PATH"] = str(config_path or snapshot.root / "openclaw.json")
    # Empty profile prevents a caller's unrelated profile from redirecting state.
    environment.pop("OPENCLAW_PROFILE", None)
    if runtime_home:
        environment["HOME"] = runtime_home
    return environment


def _direct_sqlite_write(snapshot: ApprovalSnapshot, document: dict[str, Any]) -> None:
    """Fallback writer for an already initialized native database.

    Normally the OpenClaw CLI is used.  This fallback is deliberately limited
    to an existing, recognized schema and never creates a new SQLite schema.
    """

    if not snapshot.db_path.is_file():
        raise NativeApprovalsError("OpenClaw CLI is required to initialize a native approvals database")
    connection = sqlite3.connect(snapshot.db_path, timeout=5)
    try:
        columns = {
            row[1]
            for row in connection.execute("PRAGMA table_info(exec_approvals_config)")
        }
        required = {"config_key", "raw_json"}
        if not required.issubset(columns):
            raise NativeApprovalsError("Unsupported native approvals SQLite schema")
        # Keep the native socket credential when a fallback writer is needed
        # and the transformed document intentionally omitted the socket block.
        effective_document = document
        if "socket" not in effective_document and isinstance(snapshot.document.get("socket"), dict):
            effective_document = dict(effective_document)
            effective_document["socket"] = dict(snapshot.document["socket"])
        normalized = json.dumps(effective_document, ensure_ascii=False, indent=2) + "\n"
        defaults = effective_document.get("defaults") if isinstance(effective_document.get("defaults"), dict) else {}
        agents = effective_document.get("agents") if isinstance(effective_document.get("agents"), dict) else {}
        values: dict[str, Any] = {
            "config_key": "current",
            "raw_json": normalized,
            "socket_path": (effective_document.get("socket") or {}).get("path") if isinstance(effective_document.get("socket"), dict) else None,
            "has_socket_token": 1 if isinstance(effective_document.get("socket"), dict) and effective_document["socket"].get("token") else 0,
            "default_security": defaults.get("security"),
            "default_ask": defaults.get("ask"),
            "default_ask_fallback": defaults.get("askFallback"),
            "auto_allow_skills": (1 if defaults.get("autoAllowSkills") is True else 0) if "autoAllowSkills" in defaults else None,
            "agent_count": len(agents),
            "allowlist_count": sum(
                len(value.get("allowlist", []))
                for value in agents.values()
                if isinstance(value, dict) and isinstance(value.get("allowlist", []), list)
            ),
            "updated_at_ms": int(__import__("time").time() * 1000),
        }
        writable = {key: value for key, value in values.items() if key in columns}
        names = ", ".join(writable)
        placeholders = ", ".join("?" for _ in writable)
        updates = ", ".join(
            f"{key}=excluded.{key}" for key in writable if key != "config_key"
        )
        connection.execute(
            f"INSERT INTO exec_approvals_config ({names}) VALUES ({placeholders}) "
            f"ON CONFLICT(config_key) DO UPDATE SET {updates}",
            tuple(writable.values()),
        )
        connection.commit()
    except sqlite3.Error as error:
        connection.rollback()
        raise NativeApprovalsError(f"Cannot write native approvals database: {error}") from error
    finally:
        connection.close()


def save_approvals(
    snapshot: ApprovalSnapshot,
    document: dict[str, Any],
    *,
    config_path: pathlib.Path | None = None,
    runtime_home: str | None = None,
) -> ApprovalSnapshot:
    """Persist a transformed approval document using the active backend."""

    if not isinstance(document, dict):
        raise NativeApprovalsError("Approvals document must be an object")
    if snapshot.backend == "legacy":
        destination = snapshot.legacy_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(prefix=".exec-approvals.", dir=destination.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(document, handle, ensure_ascii=False, indent=2)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.chmod(temporary, stat.S_IRUSR | stat.S_IWUSR)
            if destination.exists():
                os.chmod(temporary, stat.S_IMODE(destination.stat().st_mode))
                os.chown(temporary, destination.stat().st_uid, destination.stat().st_gid)
            os.replace(temporary, destination)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
        return load_approvals(snapshot.root)

    executable = os.environ.get("OPENCLAW_BIN") or shutil.which("openclaw")
    payload = (json.dumps(document, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    if executable:
        try:
            result = subprocess.run(
                [executable, "approvals", "set", "--stdin", "--json"],
                input=payload,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=_cli_environment(snapshot, config_path, runtime_home),
                check=False,
            )
        except OSError:
            # An overridden/missing binary must not prevent the safe direct
            # writer from handling an already initialized native database.
            cli_error = True
        else:
            if result.returncode == 0:
                return load_approvals(snapshot.root)
            # Do not expose CLI output; it can contain the socket locator/token.
            cli_error = True
    else:
        cli_error = False
    try:
        _direct_sqlite_write(snapshot, document)
    except NativeApprovalsError as error:
        detail = "OpenClaw approvals CLI failed" if cli_error else str(error)
        raise NativeApprovalsError(f"Native approvals update failed: {detail}") from error
    return load_approvals(snapshot.root)


def backup_approvals(
    snapshot: ApprovalSnapshot, destination_dir: pathlib.Path, label: str = "exec-approvals"
) -> dict[str, Any]:
    """Create a private rollback snapshot and return sanitized metadata."""

    destination_dir.mkdir(parents=True, mode=0o700, exist_ok=True)
    os.chmod(destination_dir, 0o700)
    if destination_dir.is_symlink() or not destination_dir.is_dir():
        raise NativeApprovalsError("Approval backup directory is unsafe")
    if snapshot.backend == "legacy":
        if not snapshot.legacy_path.is_file():
            marker = destination_dir / f"{label}.missing"
            marker.touch(mode=0o600)
            return {
                "backend": "legacy",
                "path": str(marker),
                "exists": False,
                "document_sha256": snapshot.hash,
            }
        target = destination_dir / f"{label}.json"
        _assert_safe_file(target, "approval backup")
        shutil.copy2(snapshot.legacy_path, target)
        os.chmod(target, 0o600)
        return {
            "backend": "legacy",
            "path": str(target),
            "exists": True,
            "sha256": _sha256(target),
            "document_sha256": snapshot.hash,
        }

    target = destination_dir / f"{label}.sqlite"
    _assert_safe_file(target, "approval backup")
    if snapshot.db_path.is_file():
        # Gateway is required to be quiesced by callers before this operation.
        source = sqlite3.connect(f"file:{snapshot.db_path}?mode=ro", uri=True)
        try:
            destination = sqlite3.connect(target)
            try:
                source.backup(destination)
            finally:
                destination.close()
        finally:
            source.close()
        os.chmod(target, 0o600)
        return {
            "backend": "sqlite",
            "path": str(target),
            "exists": True,
            "sha256": _sha256(target),
        }
    marker = destination_dir / f"{label}.missing"
    _assert_safe_file(marker, "approval backup marker")
    marker.touch(mode=0o600)
    return {
        "backend": "sqlite",
        "path": str(marker),
        "exists": False,
        "document_sha256": snapshot.hash,
    }


def restore_approvals(
    snapshot: ApprovalSnapshot,
    backup: dict[str, Any],
    *,
    config_path: pathlib.Path | None = None,
    runtime_home: str | None = None,
) -> None:
    """Restore a snapshot; native stores are restored through OpenClaw CLI."""

    requested_backup_path = pathlib.Path(str(backup.get("path", ""))).expanduser()
    if requested_backup_path.is_symlink():
        raise NativeApprovalsError("Approval rollback snapshot is a symlink")
    backup_path = requested_backup_path.resolve()
    if not backup_path.is_file():
        raise NativeApprovalsError("Approval rollback snapshot is missing or unsafe")
    backend = backup.get("backend")
    if backend != snapshot.backend:
        raise NativeApprovalsError(
            "Approval rollback backend does not match the active OpenClaw store"
        )
    if backend == "legacy":
        if backup.get("exists"):
            destination = snapshot.legacy_path
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(backup_path, destination)
            os.chmod(destination, 0o600)
        else:
            snapshot.legacy_path.unlink(missing_ok=True)
        return
    # A SQLite backup is a complete state snapshot; restoring the file keeps
    # unrelated state tables and the socket token byte-for-byte intact.
    if backend != "sqlite":
        raise NativeApprovalsError("Unknown approvals rollback backend")
    if backup.get("exists"):
        destination = snapshot.db_path
        _assert_safe_file(destination, "active native approvals database")
        destination.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(prefix=".openclaw-approvals-restore-", dir=destination.parent)
        os.close(fd)
        try:
            shutil.copy2(backup_path, temporary)
            os.chmod(temporary, 0o600)
            os.replace(temporary, destination)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
        # A stale WAL from the failed operation must not be replayed over the
        # restored snapshot on the next OpenClaw connection.
        for suffix in ("-wal", "-shm"):
            destination.with_name(destination.name + suffix).unlink(missing_ok=True)
    else:
        destination = snapshot.db_path
        _assert_safe_file(destination, "active native approvals database")
        destination.unlink(missing_ok=True)
        for suffix in ("-wal", "-shm"):
            destination.with_name(destination.name + suffix).unlink(missing_ok=True)


def _sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_private_json(path: pathlib.Path, value: dict[str, Any]) -> None:
    """Write a temporary approval document without making it world-readable."""
    path = path.expanduser()
    if not path.is_absolute():
        raise NativeApprovalsError("Approval export path must be absolute")
    if path.exists() and path.is_symlink():
        raise NativeApprovalsError("Refusing symlinked approval export path")
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
        os.chmod(path, 0o600)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _cli() -> int:
    """Small private CLI used by shell helpers; never prints the JSON document."""
    parser = argparse.ArgumentParser(description="OpenClaw approval backend helper")
    subparsers = parser.add_subparsers(dest="command", required=True)

    export = subparsers.add_parser("export")
    export.add_argument("--root", required=True)
    export.add_argument("--output", required=True)
    export.add_argument("--json", action="store_true", dest="as_json")

    save = subparsers.add_parser("save")
    save.add_argument("--root", required=True)
    save.add_argument("--input", required=True)
    save.add_argument("--config")
    save.add_argument("--runtime-home")

    backup = subparsers.add_parser("backup")
    backup.add_argument("--root", required=True)
    backup.add_argument("--destination", required=True)
    backup.add_argument("--label", default="exec-approvals")

    restore = subparsers.add_parser("restore")
    restore.add_argument("--root", required=True)
    restore.add_argument("--backend", required=True, choices=("legacy", "sqlite"))
    restore.add_argument("--path", required=True)
    restore.add_argument("--exists", action="store_true")
    restore.add_argument("--config")
    restore.add_argument("--runtime-home")

    args = parser.parse_args()
    try:
        root = pathlib.Path(args.root).expanduser().resolve()
        if args.command == "export":
            snapshot = load_approvals(root)
            _write_private_json(pathlib.Path(args.output), snapshot.document)
            metadata = {
                "backend": snapshot.backend,
                "locator": snapshot.locator,
                "exists": snapshot.exists,
                "document_sha256": snapshot.hash,
            }
            print(json.dumps(metadata, separators=(",", ":")))
            return 0
        if args.command == "save":
            snapshot = load_approvals(root)
            input_path = pathlib.Path(args.input).expanduser().resolve()
            if input_path.is_symlink() or not input_path.is_file():
                raise NativeApprovalsError("Approval input file is missing or unsafe")
            with input_path.open("r", encoding="utf-8") as handle:
                document = _parse(handle.read(), input_path)
            updated = save_approvals(
                snapshot,
                document,
                config_path=pathlib.Path(args.config).expanduser().resolve()
                if args.config
                else None,
                runtime_home=args.runtime_home,
            )
            print(
                json.dumps(
                    {
                        "backend": updated.backend,
                        "locator": updated.locator,
                        "exists": updated.exists,
                        "document_sha256": updated.hash,
                    },
                    separators=(",", ":"),
                )
            )
            return 0
        if args.command == "backup":
            snapshot = load_approvals(root)
            metadata = backup_approvals(
                snapshot, pathlib.Path(args.destination).expanduser().resolve(), args.label
            )
            print(json.dumps(metadata, separators=(",", ":")))
            return 0
        if args.command == "restore":
            snapshot = load_approvals(root)
            restore_approvals(
                snapshot,
                {
                    "backend": args.backend,
                    "path": str(pathlib.Path(args.path).expanduser().resolve()),
                    "exists": bool(args.exists),
                },
                config_path=pathlib.Path(args.config).expanduser().resolve()
                if args.config
                else None,
                runtime_home=args.runtime_home,
            )
            print(json.dumps({"backend": args.backend, "restored": True}, separators=(",", ":")))
            return 0
        raise NativeApprovalsError("Unknown approval helper command")
    except (OSError, ValueError, NativeApprovalsError) as error:
        # Keep diagnostics free of CLI output, which can contain socket data.
        print(f"error={error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(_cli())
