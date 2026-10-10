---
name: telegram-zalo-owner-login
description: Install, upgrade or verify a member-local OpenClaw tool and /zaloqr command so every configured Telegram owner can request a Zalo Personal login QR and receive it privately. Use for enabling this flow on selected Docker member VPS instances; not for granting new owners, bulk rollout, or bypassing generic exec guards.
---

# Telegram owners → Zalo login QR

Generic exec in tested OpenClaw `2026.9.9` rejects interactive `channels login` even with full approvals. Install the declared, owner-gated channel-specific tool instead; do not patch the core guard or hide the command in an exec wrapper.

## Deploy on a selected member

Read the VPS runbook, project note, nearest AGENTS.md and production checklist. Verify the target container, active HOME/state root, canonical agent, Telegram account and Zalo account. Do not guess among multiple accounts or change bindings to make installation pass.

Run from this skill directory on the Docker host:

```bash
python3 scripts/deploy.py --member MEMBER --dry-run
python3 scripts/deploy.py --member MEMBER --apply
python3 scripts/deploy.py --member MEMBER --check
```

For a different layout, supply `--container`, `--openclaw-root`, `--runtime-home`, `--runtime-root`, `--agent`, `--telegram-account` and `--zalo-account` explicitly. Host/runtime roots must map through the selected container's actual mounts. The helper supports Linux Docker + Supervisor, exact tested core `2026.9.9`, and a workspace inside that runtime state root; it stops before changing unsupported targets.

The helper privately backs up config, native state and affected files, quiesces only that member Gateway under existing watchdog locks, installs the linked plugin through the official installer, validates, and starts the same Gateway. Known legacy `vuhoainam-telegram-zalo-login` is upgraded in place; no second `/zaloqr` registration. It copies only the runtime skill into the member workspace, not Docker-host administration scripts. Reruns update the managed files without adding duplicate instructions.

## Owner and delivery rules

- Owners come dynamically from the existing `commands.ownerAllowFrom`, numeric IDs or `telegram:ID`. Wildcards and other-channel owners do not qualify. This skill never adds owners or treats public `allowFrom: ["*"]` as ownership.
- Require trusted owner authority, matching account/agent and a private destination matching the requesting sender. Each owner receives their own QR; never send all owners a broadcast or send QR to a group.
- Tool `telegram_zalo_login_qr` handles natural requests; `/zaloqr` is the native, model-independent command. Only explicit login/QR requests start login, not status checks.
- Keep login alive while sending the current image, require an exact Telegram receipt, cap the attempt at 180 seconds and prevent concurrent attempts. An existing lock is not automatically deleted; inspect its PID before any owner-approved recovery.
- Do not logout, replace another member's credentials, open full tools to non-owners, publish QR, or restart other containers. CLI login completion is not proof that the Zalo listener is running.

## Verify and report

Check config validation, plugin doctor, runtime skill readiness, owner/non-owner/group tool assembly, and Telegram status/probe. Deployment does not send a test message or create a QR. Ask an existing owner to try `/zaloqr` or a natural login request, then scan on the phone; distinguish plugin installed, QR receipt and verified Zalo connectivity.

The helper reports but tolerates the exact existing `duckduckgo` provenance-only warning when plugin errors, source shadowing, compatibility findings and configuration warnings are empty. It does not change that plugin's trust or config; other doctor failures still stop deployment.

Backups are recorded by the helper under `/root/_Backups/telegram-zalo-owner-login/`. On deployment failure it restores its affected files/config/native snapshot while the Gateway is stopped, then restores the previous running state. Review the private backup if rollback itself fails. Update the target project note and change journal without IDs or secrets.

The source asset `assets/index.mjs` and helper are portable to another Docker VPS host. Do not rollout elsewhere without a selected target and owner authorization. Revalidate SDK/CLI before supporting a different core release.
