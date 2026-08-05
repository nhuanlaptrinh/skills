#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path


def replace_once(text: str, old: str, new: str, path: Path) -> str:
    if old not in text:
        raise SystemExit(f"Pattern not found in {path}: {old[:80]!r}")
    return text.replace(old, new, 1)


def ensure(path: Path, marker: str, patcher) -> bool:
    text = path.read_text()
    if marker in text:
        return False
    new_text = patcher(text, path)
    path.write_text(new_text)
    return True


def patch_settings(path: Path) -> bool:
    def patch(text: str, p: Path) -> str:
        text = replace_once(text, 'APP_NAME = "', 'APP_NAME = "', p)
        lines = text.splitlines()
        out = []
        for line in lines:
            out.append(line)
            if line.startswith('APP_NAME = '):
                out.append('BOT_REPLY_METADATA = f"{APP_NAME}:auto_reply"')
            if line.startswith('META_PAGE_ID = '):
                out.append('META_APP_ID = os.getenv("META_APP_ID", "").strip()')
            if line.startswith('AI_TIMEOUT_SECONDS = '):
                out.append('HUMAN_PAUSE_MINUTES = int(os.getenv("HUMAN_PAUSE_MINUTES", "60"))')
        return "\n".join(out) + "\n"
    return ensure(path, 'HUMAN_PAUSE_MINUTES', patch)


def patch_facebook(path: Path) -> bool:
    def patch(text: str, p: Path) -> str:
        text = replace_once(text, 'from .settings import (\n', 'from .settings import (\n    BOT_REPLY_METADATA,\n', p)
        text = replace_once(text, '"message": {"text": part},', '"message": {"text": part, "metadata": BOT_REPLY_METADATA},', p)
        return text
    return ensure(path, 'BOT_REPLY_METADATA', patch)


def patch_database(path: Path) -> bool:
    def patch(text: str, p: Path) -> str:
        text = replace_once(text, 'from datetime import datetime', 'from datetime import datetime, timedelta', p)
        text = replace_once(text, '                paused INTEGER NOT NULL DEFAULT 0,\n                updated_at TEXT NOT NULL', '                paused INTEGER NOT NULL DEFAULT 0,\n                manual_pause_until TEXT,\n                updated_at TEXT NOT NULL', p)
        text = replace_once(text, '            """\n        )\n', '            """\n        )\n        columns = {\n            row["name"] for row in db.execute("PRAGMA table_info(conversations)")\n        }\n        if "manual_pause_until" not in columns:\n            db.execute("ALTER TABLE conversations ADD COLUMN manual_pause_until TEXT")\n', p)
        text = replace_once(text, '            "SELECT paused FROM conversations WHERE psid = ?", (psid,)\n        ).fetchone()\n    return bool(row and row["paused"])', '            "SELECT paused, manual_pause_until FROM conversations WHERE psid = ?", (psid,)\n        ).fetchone()\n    if not row:\n        return False\n    if row["paused"]:\n        return True\n    pause_until = row["manual_pause_until"]\n    if not pause_until:\n        return False\n    try:\n        return datetime.fromisoformat(pause_until) > datetime.now(VIETNAM_TZ)\n    except ValueError:\n        return False', p)
        text += '\n\ndef set_manual_pause(psid, minutes):\n    now = datetime.now(VIETNAM_TZ)\n    pause_until = (now + timedelta(minutes=minutes)).isoformat()\n    with _connect() as db:\n        db.execute(\n            """\n            INSERT INTO conversations(psid, paused, manual_pause_until, updated_at)\n            VALUES (?, 0, ?, ?)\n            ON CONFLICT(psid) DO UPDATE SET\n                manual_pause_until = excluded.manual_pause_until,\n                updated_at = excluded.updated_at\n            """,\n            (psid, pause_until, now.isoformat()),\n        )\n    return pause_until\n'
        return text
    return ensure(path, 'manual_pause_until', patch)


def patch_main(path: Path) -> bool:
    def patch(text: str, p: Path) -> str:
        text = replace_once(text, '    is_paused,\n    set_paused,', '    is_paused,\n    set_manual_pause,\n    set_paused,', p)
        text = replace_once(text, '    APP_NAME,\n    FALLBACK_MESSAGE,', '    APP_NAME,\n    BOT_REPLY_METADATA,\n    FALLBACK_MESSAGE,', p)
        text = replace_once(text, '    FALLBACK_MESSAGE,\n    HISTORY_LIMIT,', '    FALLBACK_MESSAGE,\n    HUMAN_PAUSE_MINUTES,\n    HISTORY_LIMIT,', p)
        text = replace_once(text, '    HISTORY_LIMIT,\n    META_PAGE_ID,', '    HISTORY_LIMIT,\n    META_APP_ID,\n    META_PAGE_ID,', p)
        marker = '        except Exception:\n            logger.exception("Could not send fallback for psid=%s", psid)\n'
        handler = marker + '\n\ndef _handle_echo(event, message):\n    recipient_id = str(event.get("recipient", {}).get("id", "")).strip()\n    app_id = str(message.get("app_id") or "").strip()\n    metadata = str(message.get("metadata") or "").strip()\n    text = str(message.get("text") or "").strip()\n\n    if not recipient_id or not text:\n        return\n    if META_PAGE_ID and recipient_id == META_PAGE_ID:\n        return\n    if metadata == BOT_REPLY_METADATA or (META_APP_ID and app_id == META_APP_ID):\n        logger.info("Ignored bot echo for psid=%s app_id=%s", recipient_id, app_id)\n        return\n\n    pause_until = set_manual_pause(recipient_id, HUMAN_PAUSE_MINUTES)\n    add_message(recipient_id, "human", text)\n    logger.info(\n        "Human reply detected; paused auto-reply psid=%s until=%s",\n        recipient_id,\n        pause_until,\n    )\n'
        text = replace_once(text, marker, handler, p)
        text = replace_once(text, '            if not sender_id or not text or message.get("is_echo"):\n                continue', '            if message.get("is_echo"):\n                if event_id and not claim_event(event_id):\n                    continue\n                _handle_echo(event, message)\n                continue\n\n            if not sender_id or not text:\n                continue', p)
        return text
    return ensure(path, '_handle_echo', patch)


def patch_env_example(path: Path) -> bool:
    text = path.read_text()
    changed = False
    if 'META_APP_ID=' not in text:
        text = text.replace('META_PAGE_ID=Nhap_Page_ID\n', 'META_PAGE_ID=Nhap_Page_ID\nMETA_APP_ID=Nhap_Meta_App_ID_De_Bo_Qua_Echo_Tu_Bot\n')
        changed = True
    if 'HUMAN_PAUSE_MINUTES=' not in text:
        text = text.replace('AI_TIMEOUT_SECONDS=30\n', 'AI_TIMEOUT_SECONDS=30\nHUMAN_PAUSE_MINUTES=60\n')
        changed = True
    if changed:
        path.write_text(text)
    return changed


def patch_tests(path: Path) -> bool:
    if not path.exists() or 'test_human_echo_sets_manual_pause' in path.read_text():
        return False
    text = path.read_text()
    text = text.replace('from app.knowledge import load_knowledge  # noqa: E402\n', 'from app.knowledge import load_knowledge  # noqa: E402\nfrom app.main import _handle_echo  # noqa: E402\nfrom app.settings import BOT_REPLY_METADATA  # noqa: E402\n')
    insert_after = '''    def test_pause_and_history(self):\n        database.add_message("customer-1", "user", "Học phí bao nhiêu?")\n        self.assertEqual(database.get_history("customer-1", 5)[0]["role"], "user")\n        database.set_paused("customer-1", True)\n        self.assertTrue(database.is_paused("customer-1"))\n'''
    addition = insert_after + '''\n    def test_manual_pause_expires(self):\n        database.set_manual_pause("customer-manual", 60)\n        self.assertTrue(database.is_paused("customer-manual"))\n        database.set_manual_pause("customer-manual", -1)\n        self.assertFalse(database.is_paused("customer-manual"))\n\n    def test_human_echo_sets_manual_pause(self):\n        event = {"recipient": {"id": "customer-echo"}}\n        message = {"is_echo": True, "text": "Nhân viên đang tư vấn trực tiếp"}\n        with patch("app.main.HUMAN_PAUSE_MINUTES", 60):\n            _handle_echo(event, message)\n        self.assertTrue(database.is_paused("customer-echo"))\n        self.assertEqual(database.get_history("customer-echo", 1)[0]["role"], "human")\n\n    def test_bot_echo_metadata_is_ignored(self):\n        event = {"recipient": {"id": "customer-bot-echo"}}\n        message = {\n            "is_echo": True,\n            "text": "Tin nhắn tự động từ bot",\n            "metadata": BOT_REPLY_METADATA,\n        }\n        _handle_echo(event, message)\n        self.assertFalse(database.is_paused("customer-bot-echo"))\n'''
    text = text.replace(insert_after, addition)
    path.write_text(text)
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply Messenger human takeover auto-pause patch.")
    parser.add_argument("project", type=Path)
    args = parser.parse_args()
    project = args.project.resolve()
    required = [project / "app/main.py", project / "app/database.py", project / "app/settings.py", project / "app/facebook.py"]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise SystemExit("Missing required files: " + ", ".join(missing))
    changed = []
    for label, func, path in [
        ("settings", patch_settings, project / "app/settings.py"),
        ("facebook", patch_facebook, project / "app/facebook.py"),
        ("database", patch_database, project / "app/database.py"),
        ("main", patch_main, project / "app/main.py"),
        ("env_example", patch_env_example, project / ".env.example"),
        ("tests", patch_tests, project / "tests/test_core.py"),
    ]:
        if func(path):
            changed.append(label)
    print("changed=" + (",".join(changed) if changed else "none"))


if __name__ == "__main__":
    main()
