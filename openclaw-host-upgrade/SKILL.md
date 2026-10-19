---
name: openclaw-host-upgrade
description: Upgrade OpenClaw on the main VPS host with pinned official updates, root-only rollback backups, SQLite checks, plugin convergence and no-delivery verification. Use for the root systemd Gateway, not Docker member upgrades.
---

# Main VPS OpenClaw Upgrade

## Scope And Inputs

- Active state/config: `/root/.openclaw`, not the historical config under `/root/AI_Runtime/openclaw/.openclaw`.
- Global package: `/usr/lib/node_modules/openclaw`; executable: `/usr/bin/openclaw`.
- Manager: root user systemd `openclaw-gateway.service`, port `18789`.
- Project note: `/root/_Second_AI_Brain/projects/AI_runtime.md`.
- Input `TARGET`: exact version authorized by the owner. On 2026-10-15, npm `latest` resolved to `2026.10.3`; recheck for future requests.
- Input `BACKUP`: a new timestamped directory under `/root/_Backups/openclaw/root-upgrade-<UTC>` with mode `0700`.
- Outputs: pinned CLI/Gateway, converged official plugins, healthy baseline channels, backup and sanitized operator notes. No Sheet, upload or social publishing is involved.

Read the VPS operating docs, production checklist and applicable AGENTS.md first. Authorization to upgrade this host covers the necessary package changes and host Gateway stop/start, not member containers, credentials, model/routing changes, or external test messages.

## Read-Only Preflight

```bash
openclaw --version
node --version
npm view openclaw dist-tags --json
npm view "openclaw@$TARGET" version engines dist.integrity --json
openclaw update status --json
openclaw config validate
openclaw gateway status
openclaw update --tag "$TARGET" --dry-run --no-restart --json
```

Inspect `openclaw channels status --probe --json` and `openclaw plugins list --json` through allowlisted metadata filters; do not print credentials or private message content. Record individual configured accounts, not just the Telegram top-level fallback account. Note pre-existing failures rather than changing their tokens or starting QR login.

A transient npm cache ENOENT during dry-run can be retried once after confirming no updater is active. Do not delete the shared npm cache, disable a working plugin, or force reinstall as the first response. Stop before production writes if plugin targets or Node engines are incompatible.

## Back Up And Apply

Create the root-only backup before modifying production. Save the complete existing global package including local patches, managed plugin projects under `/root/.openclaw/npm/projects`, config and its last-good/pre-update companions, and the systemd unit with all drop-ins. Preserve the Telegram offset pre-start guard.

Stop only the host Gateway before the database snapshot and actual update:

```bash
systemctl --user stop openclaw-gateway.service
systemctl --user show openclaw-gateway.service -p ActiveState -p MainPID
```

Require inactive state and no host Gateway writer. Copy `/root/.openclaw/state` and all `agents/<id>/agent/openclaw-agent.sqlite` with existing WAL/SHM companions together. Back up agent model/auth catalogs, credential state, identity and pairing state without printing their contents. Do not recurse into unrelated Codex state unless needed for rollback. Run read-only SQLite `PRAGMA quick_check` on the snapshots.

```bash
openclaw update --tag "$TARGET" --channel stable --no-restart --yes --json
```

The updater stages a package and may run an isolated loopback canary. Do not mistake that process for a duplicate production Gateway. Wait for its final status before another mutation.

### Proven Updater Swap Failure

The 2026.9.4 updater has a hard 30-second package-integrity scan limit. On this host its staging, migration rehearsal and Gateway canary passed, but the global-install swap failed with `Package rollback verification timed out`. It retained the old package; this does not itself prove package corruption.

For this specific verified failure, keep the host Gateway stopped, confirm the old tree and launcher are usable and match the backup, and retain the full package/plugin/database backups. An exact npm install is a supported recovery path without patching the updater or using `--force`:

```bash
npm install -g "openclaw@$TARGET" --no-fund --no-audit --loglevel=error --min-release-age=0
openclaw --version
openclaw update repair --channel stable --yes --no-restart --json
```

Repair can perform lengthy offline SQLite maintenance and official-plugin convergence. Do not start a second writer or the Gateway while it is active. Intermediate doctor warnings about old plugin versions may clear during the following plugin phase; judge the final result and post-repair plugin checks.

If core activation succeeded but doctor/plugin convergence is explicitly incomplete, keep the Gateway stopped and run:

```bash
openclaw update repair --channel stable --yes --no-restart --json
```

Do not run repair concurrently with an active updater. Review any widened plugin capabilities before adding `--accept-capabilities`. Do not copy old bundled files over a new core. A custom `openclaw-zaloclawbot` installation may have a compatibility patch; preserve it and verify its loader/dependencies after convergence.

### ClawBot 0.1.4 With Core 2026.10.3

The latest ClawBot package remained `0.1.4` on 2026-10-15. Its base path is `/root/.openclaw/npm/projects/zalo-platforms-openclaw-zaloclawbot-3e4205cbbe/node_modules/@zalo-platforms/openclaw-zaloclawbot/`. The following local SDK compatibility updates are required on this inspected host:

- `dist/src/util/logger.js`: import `resolvePreferredOpenClawTmpDir` from `openclaw/plugin-sdk/temp-path`, replacing the removed `infra-runtime` export.
- `dist/src/monitor/process-message.js`: import `createTypingCallbacks` from `openclaw/plugin-sdk/channel-outbound`, replacing the removed `channel-reply-pipeline` export.
- `dist/src/auth/login-flow.js`: replace the removed `config-runtime` load/write pair with `updateConfig` from `openclaw/plugin-sdk/config-mutation`, preserving the same channel timestamp mutation inside its callback. Do not invoke login or the config-writing callback merely to test compatibility.

Patch only these plugin files after backing up their originals; do not add removed exports to the core package. Verify with `node --check` on the changed files, a direct import of `dist/index.js`, and `openclaw plugins doctor`. A plugin metadata list alone can report loaded even when actual Gateway module loading fails. Restart the host Gateway once after loader checks pass, then confirm the existing ClawBot account is running without an import error. Reassess these patches after any future ClawBot package update because reinstalling it can overwrite them.

```bash
openclaw --version
openclaw config validate
openclaw plugins doctor
systemctl --user start openclaw-gateway.service
```

## Acceptance And Rerun

- Require both CLI and live Gateway to report `TARGET`, one production listener on `18789`, service active and stable PID/restart count.
- Probe each previously healthy configured Telegram account, Zalo Bot API and ClawBot; compare known login/token failures against baseline. Do not claim a real reply from a transport probe.
- Repeat the channel check after at least 35 seconds and inspect only post-start error metadata for missing imports, poller conflicts, tombstones and SQLite failures.
- Check active external official plugin versions and `plugins doctor`; read-only SQLite quick-check must pass on the main state and OpenClaw agent databases.
- Verify config model/provider, credentials, bindings, permissions and workspaces remain unchanged except necessary reviewed migrations.
- An internal model smoke test may use a fresh `agent:main:upgrade-check-<unique-id>` session with an instruction to call no tools and send no messages. Omit `--deliver` and all external reply targets.
- Rerun preflight first. If already at the target, verify health and repair only proven incomplete update state; do not reinstall blindly or restore historical sessions.

On failure, inspect the updater's recorded recovery status before acting. Restore the backed-up package/plugin generation and only incident changes as necessary, then bring the affected host Gateway back to a verified working state. Do not overwrite newer sessions or credential changes with historical databases unless migration corruption is demonstrated. Keep rollback archives; do not run update cleanup implicitly.

Update the project note and `/root/_Second_AI_Brain/06_Nhat_Ky_Thay_Doi.md` with version, backup, scope, verification and pre-existing issues. Scan this skill and any new documentation for real keys, tokens, cookies, passwords or private keys before completion.
