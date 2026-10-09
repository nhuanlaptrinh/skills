---
name: openclaw-zalo-text-delivery-guard
description: Deploy or verify member-local OpenClaw Zalo text splitting, plain-text delivery, receipt-aware retries and failed-delivery context on Docker member VPS instances. Use for long text or OCR replies that are generated but not received; does not repair Zalo login or attachment uploads.
---

# OpenClaw Zalo Text Delivery Guard

## Scope and behavior

Apply only to explicitly requested members. This installer supports the official core/plugin `2026.9.9` with reviewed native ESM sender/monitor anchors. Other releases stop for compatibility review, not automatic upgrade or broad bundle replacement. It resolves the active generation and Docker mount instead of patching all cached bundles.

All text-only Zalo replies, not just OCR, become plain rendered text with visible list numbers/bullets and link destinations. Parts include `[index/total]` and never exceed 1,000 UTF-16 units; grapheme boundaries and every rendered character are preserved. Replies to one destination are serialized, require a platform message ID per part, and have a 600 ms inter-part delay.

Only explicit numeric API rejections without receipts allow one retry after 900 ms. Unknown/timeout/missing-receipt results, attachments and already acknowledged parts must not be blindly replayed. Partial receipts remain available to the native core. This is not cross-restart resume or proof of device receipt/read status.

Private member-local state contains hashed destinations/content, counts, status, timestamps and numeric codes, never plaintext messages, raw sender IDs or credentials. It has 0600 permissions and a 256-destination cap; inactive destination entries and failure context age out after seven days. A fixed failure-status note reaches the next admitted agent context without changing commands, access policies or raw inbound text. An unrelated successful greeting does not erase the unresolved failure record.

The local watchdog gap threshold is raised from 35 to 180 seconds, or preserved if already at the reviewed 180-second setting. Actual socket close/error/handshake recovery stays enabled. This mitigates observed timer-gap disconnects, not underlying host load or every upstream failure.

## Installation

Read the VPS Second AI Brain, member project note, applicable `AGENTS.md` and production checklist. Resolve the member's actual Gateway HOME and host mount; the normal member directory has `root/` and `home/`, and the active HOME may be `/root`, not `/home/<member>`. The standard container name must be `user-<member-label>` so member watchdog locks cannot be acquired for another member. An active watchdog is allowed a bounded idle wait, default 180 seconds, before the installer stops without mutation.

```bash
SKILL=/root/.agents/skills/openclaw-zalo-text-delivery-guard
python3 "$SKILL/scripts/install.py" --container user-<member> --member-data-dir /root/Apps/member_vps/docker-users/data/<member>/root --member-home /root --member-label <member> --dry-run
python3 "$SKILL/scripts/install.py" --container user-<member> --member-data-dir /root/Apps/member_vps/docker-users/data/<member>/root --member-home /root --member-label <member> --apply
```

Dry-run performs compatibility and passive health checks only. Apply holds existing member watchdog locks when available, creates a private timestamped backup, validates staged syntax and all offline tests, installs narrow hooks plus the member-local payload, and restarts only the existing Supervisor Gateway if code changed. Re-running an unchanged installation is idempotent and does not restart it.

Backups include exact bundles, any previous payload, config and consistent existing main/state SQLite snapshots. The installer never changes config, credentials, models, cron, shared core, queues or session content. It fails on ambiguous generation/mount/anchors, changed files during staging, incompatible versions, missing Supervisor ownership or new validation faults. On failure after mutation it restores only its own changed files and the original Gateway service; it never restores live session databases routinely.

If Zalo was already unauthenticated, the guard can be installed, but the report must still say Zalo is not usable. Do not initiate QR login, replace credentials or replay queues without separate owner authorization. A healthy preexisting Zalo/Telegram channel must remain healthy after the controlled reload; the installer uses a reconnect grace window before declaring a regression.

## Verification and handoff

The installed member payload is `<HOME>/.openclaw/tools/zalo-text-delivery-guard/`. `deployment.json` records only paths/version/hashes and lets its tests follow that member's active source instead of a hardcoded member or hashed filename.

```bash
docker exec user-<member> node --experimental-vm-modules --test <HOME>/.openclaw/tools/zalo-text-delivery-guard/test_guard.mjs
```

Tests use synthetic destinations, text and receipts, a mocked native sender, and temporary private state. They never send a live message or create a second authenticated listener. After install, report the backup, offline tests, config validation, each channel's actual status, any preexisting diagnostic and whether a real device test was performed. Update the affected member note and VPS change journal. Live delivery testing requires an authorized recipient and handset receipt check.

An upgrade can replace the active generation or core finalizer. Re-run dry-run and tests after upgrading; stop when anchors or release compatibility change. Do not assume a guard in an old cached generation remains active. Copy this whole skill folder, including assets and scripts, to another authorized host for reuse; no member data or credentials are needed.
