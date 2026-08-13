#!/usr/bin/env python3

import json
import pathlib
import subprocess
import tempfile


SCRIPT = pathlib.Path(__file__).with_name("grant_telegram_admin.py")


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    path.chmod(0o600)


def run(*arguments, expected=0):
    result = subprocess.run(
        [str(SCRIPT), *map(str, arguments)],
        check=False,
        text=True,
        capture_output=True,
    )
    if result.returncode != expected:
        raise AssertionError(
            f"returncode={result.returncode} expected={expected}\nstdout={result.stdout}\nstderr={result.stderr}"
        )
    return result


def main():
    with tempfile.TemporaryDirectory(prefix="grant-telegram-admin-test-") as temporary:
        root = pathlib.Path(temporary) / ".openclaw"
        workspace = root / "workspace"
        workspace.mkdir(parents=True)
        (root / "agents/main/agent").mkdir(parents=True)
        write_json(
            root / "openclaw.json",
            {
                "agents": {
                    "defaults": {"workspace": str(workspace)},
                    "list": [{"id": "main", "default": True}],
                },
                "bindings": [
                    {
                        "agentId": "main",
                        "match": {"channel": "telegram", "accountId": "bot"},
                    }
                ],
                "channels": {
                    "telegram": {
                        "dmPolicy": "pairing",
                        "allowFrom": [],
                        "accounts": {
                            "bot": {"dmPolicy": "pairing", "allowFrom": []}
                        },
                    }
                },
                "commands": {"ownerAllowFrom": []},
                "tools": {"profile": "full"},
            },
        )
        write_json(
            root / "exec-approvals.json",
            {
                "version": 1,
                "socket": {"path": str(root / "exec.sock"), "token": "fixture-secret"},
                "defaults": {},
                "agents": {},
            },
        )
        common = [
            "--telegram-id",
            "123456",
            "--openclaw-root",
            root,
            "--runtime-openclaw-root",
            root,
            "--account-id",
            "bot",
            "--agent-id",
            "main",
            "--backup-dir",
            pathlib.Path(temporary) / "backups",
        ]
        dry = run(*common)
        assert "status=changes-required" in dry.stdout
        run(*common, "--apply")
        check = run(*common, "--check")
        assert "status=compliant" in check.stdout

        config = json.loads((root / "openclaw.json").read_text(encoding="utf-8"))
        assert [entry["id"] for entry in config["agents"]["list"]] == ["main"]
        assert len(config["bindings"]) == 1
        assert config["bindings"][0]["match"] == {"channel": "telegram", "accountId": "bot"}
        main = config["agents"]["list"][0]
        assert main["workspace"] == str(workspace)
        assert main["tools"]["toolsBySender"]["channel:telegram:123456"] == {}
        assert "group:runtime" in main["tools"]["toolsBySender"]["*"]["deny"]
        assert config["tools"]["elevated"]["allowFrom"]["telegram"] == ["123456"]
        assert config["channels"]["telegram"]["execApprovals"]["target"] == "dm"
        assert "commands" not in config["channels"]["telegram"]
        assert config["approvals"]["plugin"]["targets"] == [
            {"channel": "telegram", "to": "123456", "accountId": "bot"}
        ]

        approvals = json.loads((root / "exec-approvals.json").read_text(encoding="utf-8"))
        assert approvals["socket"]["token"] == "fixture-secret"
        assert approvals["agents"]["main"]["security"] == "allowlist"
        assert approvals["agents"]["main"]["allowlist"] == []

    print("grant_telegram_admin_test=ok")


if __name__ == "__main__":
    main()
