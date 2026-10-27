# Native owner QR adapter — OpenClaw 2026.9.9 / 2026.10.6

Use only for the native instance selected by the install form. Never run the
Docker/Supervisor `scripts/deploy.py` on Windows or macOS.

Resolve the actual Node executable and the matching OpenClaw `openclaw.mjs` entry
to absolute real paths. Use the instance's existing home, state root, agent and
Telegram/Zalo account IDs. Do not use another globally installed CLI by accident.
Run `scripts/deploy-native.py` with `--root`, `--home`, `--node`, `--cli-entry`,
`--telegram-account`, `--zalo-account`, `--agent` and `--ensure` for a normal install.
This reuses an exact enabled payload or performs one backed-up installation,
instead of repeating dry-run/apply/check CLI validation on every fresh machine.
Explicit `--dry-run`, `--apply`, `--check` remain available for operator diagnosis.
It backs up affected config/plugin files within the selected state,
installs a linked plugin and validates it, without touching services or credentials.
After an authorized apply, use `openclaw plugins reload telegram-zalo-owner-login --json`
and inspect runtime tool/command registration. Never restart when `restartRequired=false`;
stop and ask the owner if a restart is required. Do not use apply in a no-runtime-change audit.
Retain this skill and the instructions from `references/runtime-SKILL.md` in the
selected workspace so the model chooses the tool for explicit login requests.

The native adapter supplies Node plus the matching CLI entry as argv; it does not
depend on a `.ps1` shell wrapper or `/usr/bin/openclaw`. Windows child cancellation
uses the child handle rather than Unix process groups. All attempts are bounded;
locks, private staging, numeric ownership and exact delivery receipts remain.

Run `node tests/test_owner_login.mjs` offline. Owner chat must have started the
correct bot. `/zaloqr` and `telegram_zalo_login_qr` are owner-only, private-chat-only;
public group membership never grants QR access. QR must not be published to a web
directory. No generic-exec workaround for blocked interactive login is permitted.

Deployment/config checks do not certify live delivery. Record native runtime
loading, command/tool authorization and actual Telegram receipt independently.
Until a real owner requests and receives a QR, keep delivery `pending_live_test`.
After scanning, verify the Zalo listener separately; CLI success is not enough.
Unsupported native SDK/CLI paths are `unsupported`, not a successful install.
