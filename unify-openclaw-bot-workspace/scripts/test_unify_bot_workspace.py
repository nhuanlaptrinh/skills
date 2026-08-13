#!/usr/bin/env python3

import hashlib
import json
import pathlib
import subprocess
import tempfile


SCRIPT = pathlib.Path(__file__).with_name("unify_bot_workspace.py")


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    path.chmod(0o600)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


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
    with tempfile.TemporaryDirectory(prefix="unify-openclaw-test-") as temporary:
        root = pathlib.Path(temporary) / ".openclaw"
        backup = pathlib.Path(temporary) / "backups"
        main_workspace = root / "workspace"
        source_workspace = root / "workspace-owner-admin"
        main_workspace.mkdir(parents=True)
        source_workspace.mkdir(parents=True)
        (root / "agents/main/agent").mkdir(parents=True)
        (root / "agents/owner-admin/agent").mkdir(parents=True)

        (main_workspace / "AGENTS.md").write_text("main rules\n", encoding="utf-8")
        (source_workspace / "AGENTS.md").write_text("admin rules\n", encoding="utf-8")
        (main_workspace / "same.txt").write_text("same\n", encoding="utf-8")
        (source_workspace / "same.txt").write_text("same\n", encoding="utf-8")
        (main_workspace / "memory").mkdir()
        (source_workspace / "memory").mkdir()
        (main_workspace / "memory/day.md").write_text("main memory\n", encoding="utf-8")
        (source_workspace / "memory/day.md").write_text("admin memory\n", encoding="utf-8")
        (source_workspace / "training.md").write_text("training\n", encoding="utf-8")
        (root / "agents/owner-admin/sessions").mkdir()
        (root / "agents/owner-admin/sessions/session.jsonl").write_text("{}\n", encoding="utf-8")

        config = {
            "agents": {
                "defaults": {"workspace": str(main_workspace)},
                "list": [
                    {"id": "main", "default": True},
                    {
                        "id": "owner-admin",
                        "workspace": str(source_workspace),
                        "agentDir": str(root / "agents/owner-admin/agent"),
                    },
                ],
            },
            "bindings": [
                {"agentId": "main", "match": {"channel": "telegram", "accountId": "bot"}},
                {
                    "agentId": "owner-admin",
                    "match": {
                        "channel": "telegram",
                        "accountId": "bot",
                        "peer": {"kind": "direct", "id": "111111"},
                    },
                },
            ],
            "channels": {
                "telegram": {
                    "allowFrom": ["111111"],
                    "accounts": {"bot": {"allowFrom": ["111111"]}},
                    "execApprovals": {"enabled": "auto", "approvers": ["111111"]},
                }
            },
            "commands": {"ownerAllowFrom": ["telegram:111111", "telegram:222222"]},
            "tools": {"profile": "full"},
            "approvals": {
                "plugin": {
                    "agentFilter": ["owner-admin"],
                    "targets": [{"channel": "telegram", "to": "111111", "accountId": "bot"}],
                }
            },
        }
        approvals = {
            "version": 1,
            "socket": {"path": str(root / "exec.sock"), "token": "fixture-secret"},
            "defaults": {},
            "agents": {
                "owner-admin": {
                    "allowlist": [{"id": "fixture", "pattern": "/usr/bin/curl"}]
                }
            },
        }
        config_path = root / "openclaw.json"
        approvals_path = root / "exec-approvals.json"
        write_json(config_path, config)
        write_json(approvals_path, approvals)
        before_config = digest(config_path)
        before_approvals = digest(approvals_path)

        common = [
            "--openclaw-root",
            root,
            "--runtime-openclaw-root",
            root,
            "--account-id",
            "bot",
            "--target-agent",
            "main",
            "--source-agent",
            "owner-admin",
            "--backup-dir",
            backup,
        ]
        dry_run = run(*common)
        assert "status=changes-required" in dry_run.stdout
        assert digest(config_path) == before_config
        assert digest(approvals_path) == before_approvals

        applied = run(*common, "--apply", "--gateway-stopped")
        manifest_line = next(line for line in applied.stdout.splitlines() if line.startswith("manifest="))
        manifest = pathlib.Path(manifest_line.split("=", 1)[1])
        assert manifest.is_file()
        assert (main_workspace / "training.md").read_text(encoding="utf-8") == "training\n"
        assert (main_workspace / "memory/day.md").read_text(encoding="utf-8") == "main memory\n"
        assert list((main_workspace / "memory").glob("merged-from-owner-admin-*-memory_day.md"))
        assert not source_workspace.exists()
        assert not (root / "agents/owner-admin").exists()

        updated = json.loads(config_path.read_text(encoding="utf-8"))
        assert [entry["id"] for entry in updated["agents"]["list"]] == ["main"]
        assert len(updated["bindings"]) == 1
        assert updated["bindings"][0]["match"] == {"channel": "telegram", "accountId": "bot"}
        assert set(updated["channels"]["telegram"]["allowFrom"]) == {"111111", "222222"}
        assert "commands" not in updated["channels"]["telegram"]
        assert updated["agents"]["list"][0]["tools"]["toolsBySender"]["channel:telegram:111111"] == {}
        assert "group:runtime" in updated["agents"]["list"][0]["tools"]["toolsBySender"]["*"]["deny"]

        updated_approvals = json.loads(approvals_path.read_text(encoding="utf-8"))
        assert "owner-admin" not in updated_approvals["agents"]
        assert updated_approvals["agents"]["main"]["allowlist"] == []
        assert updated_approvals["socket"]["token"] == "fixture-secret"

        checked = run(*common, "--check")
        assert "status=compliant" in checked.stdout

        applied_config = config_path.read_bytes()
        changed_config = json.loads(applied_config)
        changed_config["postMigrationChange"] = True
        write_json(config_path, changed_config)
        refused = run(
            "--rollback-manifest", manifest, "--gateway-stopped", expected=1
        )
        assert "changed after migration" in refused.stderr
        config_path.write_bytes(applied_config)
        config_path.chmod(0o600)

        run("--rollback-manifest", manifest, "--gateway-stopped")
        assert digest(config_path) == before_config
        assert digest(approvals_path) == before_approvals
        assert source_workspace.is_dir()
        assert (root / "agents/owner-admin/sessions/session.jsonl").is_file()
        assert not (main_workspace / "training.md").exists()
        assert not list((main_workspace / "memory").glob("merged-from-owner-admin-*-memory_day.md"))

    print("unify_bot_workspace_test=ok")


if __name__ == "__main__":
    main()
