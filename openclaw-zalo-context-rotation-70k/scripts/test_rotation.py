#!/usr/bin/env python3
from types import SimpleNamespace
from unittest.mock import patch
import importlib.util
from pathlib import Path


path = Path(__file__).with_name("rotate_zalo_sessions.py")
spec = importlib.util.spec_from_file_location("rotation", path)
rotation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rotation)
args = SimpleNamespace(
    container="fixture", member_home="/root", agent="main",
    key_prefix="agent:main:zalouser:", threshold=70000,
    active_window_seconds=180, dry_run=False, state_dir=Path("/tmp"),
    max_resets_per_run=1,
)
base = {
    "key": "agent:main:zalouser:direct:fixture", "totalTokens": 70000,
    "updatedAt": 700000, "sessionId": "old", "status": "done",
    "hasActiveRun": False, "activeRunIds": [], "totalTokensFresh": True,
    "archived": False,
}
assert rotation.candidate(base, args, 1000000)
for changes in (
    {"totalTokens": 69999}, {"hasActiveRun": True},
    {"activeRunIds": ["run"]}, {"status": "running"},
    {"updatedAt": 900000}, {"totalTokensFresh": False},
    {"archived": True}, {"sessionId": None},
):
    assert not rotation.candidate(dict(base, **changes), args, 1000000)
with patch.object(rotation, "list_sessions", side_effect=[[base], [base]]), \
     patch.object(rotation, "run_rpc", return_value={"ok": True, "entry": {"sessionId": "new"}}):
    assert rotation.rotate(args) == 0
args.dry_run = True
with patch.object(rotation, "list_sessions", return_value=[base]), \
     patch.object(rotation, "run_rpc") as rpc:
    assert rotation.rotate(args) == 0
    rpc.assert_not_called()
print("rotation_fixtures=11_passed")
