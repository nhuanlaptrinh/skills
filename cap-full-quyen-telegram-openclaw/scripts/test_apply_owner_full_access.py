#!/usr/bin/env python3

import importlib.util
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest


SCRIPT = pathlib.Path(__file__).with_name("apply_owner_full_access.py")
SPEC = importlib.util.spec_from_file_location("owner_full_access", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def compliant_fixture(telegram_id="123456789"):
    config = {
        "agents": {
            "list": [
                {
                    "id": "main",
                    "workspace": "/root/.openclaw/workspace",
                    "agentDir": "/root/.openclaw/agents/main/agent",
                    "tools": {
                        "profile": "full",
                        "exec": {
                            "host": "gateway",
                            "mode": "full",
                            "strictInlineEval": False,
                        },
                        "toolsBySender": {
                            f"channel:telegram:{telegram_id}": {},
                            "*": {"deny": sorted(MODULE.REQUIRED_NON_OWNER_DENY)},
                        },
                    },
                }
            ]
        },
        "bindings": [
            {
                "agentId": "main",
                "match": {"channel": "telegram", "accountId": "demo"},
            }
        ],
        "channels": {
            "telegram": {
                "allowFrom": [telegram_id],
                "accounts": {"demo": {"allowFrom": [telegram_id]}},
                "execApprovals": {"approvers": [telegram_id]},
            }
        },
        "commands": {"ownerAllowFrom": [f"telegram:{telegram_id}"]},
        "tools": {
            "fs": {"workspaceOnly": True},
            "elevated": {"allowFrom": {"telegram": [telegram_id]}},
        },
        "approvals": {
            "plugin": {
                "targets": [
                    {"channel": "telegram", "to": telegram_id, "accountId": "demo"}
                ]
            }
        },
    }
    approvals = {
        "agents": {
            "main": {
                "security": "full",
                "ask": "off",
                "askFallback": "full",
                "autoAllowSkills": True,
            }
        }
    }
    return config, approvals


class WorkflowTests(unittest.TestCase):
    def make_context(self, telegram_id="123456789"):
        temp = pathlib.Path(tempfile.mkdtemp())
        return MODULE.Context(
            member="demo",
            telegram_ids=[telegram_id],
            account_id="demo",
            agent_id="main",
            source_agent=None,
            routing_requires_unify=False,
            member_data_root=temp,
            openclaw_root=temp / ".openclaw",
            runtime_openclaw_root=pathlib.PurePosixPath("/root/.openclaw"),
            runtime_home="/root",
            container="user-demo",
            skills_root=temp / "skills",
            backup_root=temp / "backups",
            config_path=temp / ".openclaw/openclaw.json",
            approvals_path=temp / ".openclaw/exec-approvals.json",
            workspace_host=temp / ".openclaw/workspace",
        )

    def test_infer_single_account(self):
        config = {"channels": {"telegram": {"accounts": {"only": {}}}}}
        self.assertEqual(MODULE.infer_account_id(config, "demo", None), "only")

    def test_infer_prefers_member_account(self):
        config = {
            "channels": {"telegram": {"accounts": {"demo": {}, "other": {}}}}
        }
        self.assertEqual(MODULE.infer_account_id(config, "demo", None), "demo")

    def test_detects_owner_admin_legacy(self):
        config = {
            "agents": {"list": [{"id": "main"}, {"id": "owner-admin"}]},
            "bindings": [
                {
                    "agentId": "owner-admin",
                    "match": {"channel": "telegram", "accountId": "demo"},
                }
            ],
        }
        source, required = MODULE.detect_source_agent(config, "demo", "main", "auto")
        self.assertEqual(source, "owner-admin")
        self.assertTrue(required)

    def test_final_compliance(self):
        config, approvals = compliant_fixture()
        self.assertEqual(MODULE.final_violations(self.make_context(), config, approvals), [])

    def test_missing_owner_is_reported(self):
        config, approvals = compliant_fixture()
        config["commands"]["ownerAllowFrom"] = []
        self.assertIn(
            "owner_missing_command_permission",
            MODULE.final_violations(self.make_context(), config, approvals),
        )

    def test_output_redacts_owner_and_secret(self):
        telegram_id = "123456789"
        bot_token = telegram_id + ":" + ("A" * 35)
        value = f"telegram_id={telegram_id} token={bot_token}"
        sanitized = MODULE.sanitize_output(value, [telegram_id])
        self.assertNotIn(telegram_id, sanitized)
        self.assertNotIn("A" * 20, sanitized)

    def test_apply_workflow_with_fake_dependencies(self):
        telegram_id = "123456789"
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            openclaw_root = root / "data/demo/root/.openclaw"
            workspace = openclaw_root / "workspace"
            workspace.mkdir(parents=True)
            config = {
                "agents": {
                    "list": [
                        {
                            "id": "main",
                            "workspace": "/root/.openclaw/workspace",
                            "agentDir": "/root/.openclaw/agents/main/agent",
                            "tools": {"profile": "minimal"},
                        }
                    ]
                },
                "bindings": [],
                "channels": {
                    "telegram": {
                        "allowFrom": [],
                        "accounts": {"demo": {"allowFrom": []}},
                        "execApprovals": {"approvers": []},
                    }
                },
                "commands": {"ownerAllowFrom": []},
                "tools": {
                    "fs": {"workspaceOnly": False},
                    "elevated": {"allowFrom": {"telegram": []}},
                },
                "approvals": {"plugin": {"targets": []}},
            }
            approvals = {"agents": {"main": {}}}
            original_config = json.loads(json.dumps(config))
            original_approvals = json.loads(json.dumps(approvals))
            (openclaw_root / "openclaw.json").write_text(
                json.dumps(config), encoding="utf-8"
            )
            (openclaw_root / "exec-approvals.json").write_text(
                json.dumps(approvals), encoding="utf-8"
            )
            skills_root = root / "skills"
            for skill_name in MODULE.SKILL_NAMES:
                skill_dir = skills_root / skill_name
                (skill_dir / "scripts").mkdir(parents=True)
                (skill_dir / "SKILL.md").write_text(
                    f"---\nname: {skill_name}\ndescription: fixture\n---\n",
                    encoding="utf-8",
                )
            dependency_files = {
                "unify-openclaw-bot-workspace": "unify_bot_workspace.py",
                "cap-quyen-telegram-admin-openclaw": "grant_telegram_admin.py",
                "set-openclaw-agent-full-exec": "set_openclaw_agent_full_exec.sh",
            }
            for skill_name, filename in dependency_files.items():
                (skills_root / skill_name / "scripts" / filename).write_text(
                    "fixture\n", encoding="utf-8"
                )
            ctx = MODULE.Context(
                member="demo",
                telegram_ids=[telegram_id],
                account_id="demo",
                agent_id="main",
                source_agent=None,
                routing_requires_unify=True,
                member_data_root=root / "data",
                openclaw_root=openclaw_root,
                runtime_openclaw_root=pathlib.PurePosixPath("/root/.openclaw"),
                runtime_home="/root",
                container="user-demo",
                skills_root=skills_root,
                backup_root=root / "backups",
                config_path=openclaw_root / "openclaw.json",
                approvals_path=openclaw_root / "exec-approvals.json",
                workspace_host=workspace,
            )

            class FakeRunner(MODULE.Runner):
                def __init__(self):
                    self.pid = "100"

                def save(self, value, path):
                    path.write_text(json.dumps(value), encoding="utf-8")

                def guarded(self, add_owner=False):
                    current = json.loads(ctx.config_path.read_text(encoding="utf-8"))
                    target = current["agents"]["list"][0]
                    target["tools"] = {
                        "profile": "full",
                        "exec": {
                            "host": "gateway",
                            "mode": "auto",
                            "strictInlineEval": True,
                        },
                        "toolsBySender": {
                            "*": {"deny": sorted(MODULE.REQUIRED_NON_OWNER_DENY)}
                        },
                    }
                    current["bindings"] = [
                        {
                            "agentId": "main",
                            "match": {"channel": "telegram", "accountId": "demo"},
                        }
                    ]
                    current["tools"]["fs"]["workspaceOnly"] = True
                    if add_owner:
                        target["tools"]["toolsBySender"][
                            f"channel:telegram:{telegram_id}"
                        ] = {}
                        current["channels"]["telegram"]["allowFrom"] = [telegram_id]
                        current["channels"]["telegram"]["accounts"]["demo"][
                            "allowFrom"
                        ] = [telegram_id]
                        current["channels"]["telegram"]["execApprovals"][
                            "approvers"
                        ] = [telegram_id]
                        current["commands"]["ownerAllowFrom"] = [
                            f"telegram:{telegram_id}"
                        ]
                        current["tools"]["elevated"]["allowFrom"]["telegram"] = [
                            telegram_id
                        ]
                        current["approvals"]["plugin"]["targets"] = [
                            {
                                "channel": "telegram",
                                "to": telegram_id,
                                "accountId": "demo",
                            }
                        ]
                    self.save(current, ctx.config_path)
                    self.save(
                        {
                            "agents": {
                                "main": {
                                    "security": "allowlist",
                                    "ask": "on-miss",
                                    "askFallback": "deny",
                                    "autoAllowSkills": False,
                                }
                            }
                        },
                        ctx.approvals_path,
                    )

                def full_exec(self):
                    current = json.loads(ctx.config_path.read_text(encoding="utf-8"))
                    current["agents"]["list"][0]["tools"]["exec"] = {
                        "host": "gateway",
                        "mode": "full",
                        "strictInlineEval": False,
                    }
                    self.save(current, ctx.config_path)
                    self.save(
                        {
                            "agents": {
                                "main": {
                                    "security": "full",
                                    "ask": "off",
                                    "askFallback": "full",
                                    "autoAllowSkills": True,
                                }
                            }
                        },
                        ctx.approvals_path,
                    )

                def run(self, command, check=True):
                    joined = " ".join(command)
                    output = "status=pass\n"
                    if "docker inspect" in joined:
                        output = "true\n"
                    elif "pgrep -o" in joined:
                        output = self.pid + "\n"
                    elif "parent=$(ps" in joined:
                        output = "supervisord\n"
                    elif "ps -o stat=" in joined:
                        output = "Tl\n"
                    elif command[:4] == ["docker", "exec", "user-demo", "kill"]:
                        if "-STOP" not in command and "-CONT" not in command:
                            self.pid = str(int(self.pid) + 100)
                    elif "unify_bot_workspace.py" in joined and "--apply" in command:
                        self.guarded()
                        manifest = root / "fake-unify-manifest.json"
                        manifest.write_text("{}", encoding="utf-8")
                        output = f"manifest={manifest}\nstatus=applied\n"
                    elif "unify_bot_workspace.py" in joined and "--rollback-manifest" in command:
                        self.save(original_config, ctx.config_path)
                        self.save(original_approvals, ctx.approvals_path)
                        output = "status=rolled-back\n"
                    elif "grant_telegram_admin.py" in joined and "--apply" in command:
                        self.guarded(add_owner=True)
                        output = "status=applied\n"
                    elif "set_openclaw_agent_full_exec.sh" in joined and "--apply" in command:
                        self.full_exec()
                        output = "apply=pass\n"
                    elif "openclaw skills check" in joined:
                        output = "cap-full-quyen-telegram-openclaw\n"
                    elif "openclaw channels status --probe" in joined:
                        output = (
                            "- Telegram demo: running, connected, works, audit ok\n"
                        )
                    return subprocess.CompletedProcess(command, 0, output)

            runner = FakeRunner()
            MODULE.apply_workflow(ctx, runner)
            final_config = json.loads(ctx.config_path.read_text(encoding="utf-8"))
            final_approvals = json.loads(ctx.approvals_path.read_text(encoding="utf-8"))
            self.assertEqual(MODULE.final_violations(ctx, final_config, final_approvals), [])
            manifests = list((root / "backups/demo").glob("*/operation.json"))
            self.assertEqual(len(manifests), 1)
            self.assertEqual(
                json.loads(manifests[0].read_text(encoding="utf-8"))["status"],
                "applied",
            )
            MODULE.rollback_operation(ctx, runner, manifests[0], dry_run=False)
            self.assertEqual(
                json.loads(ctx.config_path.read_text(encoding="utf-8")), original_config
            )
            self.assertEqual(
                json.loads(ctx.approvals_path.read_text(encoding="utf-8")),
                original_approvals,
            )
            self.assertEqual(
                json.loads(manifests[0].read_text(encoding="utf-8"))["status"],
                "rolled-back",
            )


if __name__ == "__main__":
    unittest.main()
