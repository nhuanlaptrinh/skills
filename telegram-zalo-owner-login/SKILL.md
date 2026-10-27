---
name: telegram-zalo-owner-login
description: Install, upgrade or verify a member-local OpenClaw tool and /zaloqr command so every configured Telegram owner can request a Zalo Personal login QR and receive it privately. Use for enabling this flow on selected Docker member VPS instances; not for granting new owners, bulk rollout, or bypassing generic exec guards.
---

# Telegram owners → Zalo login QR

Supports OpenClaw `2026.10.6` and the previously tested `2026.9.9`. Generic exec rejects interactive `channels login` even with full approvals. Install the declared, owner-gated channel-specific tool instead; do not patch the core guard or hide the command in an exec wrapper.

## Native Windows/macOS/Linux

For a selected native instance, use `scripts/deploy-native.py` and read
`references/native-install.md`. The asset preserves the selected Node/CLI entry
and Windows process handling; do not run the Docker/Supervisor helper on native machines.

## Deploy on a selected member

Read the VPS runbook, project note, nearest AGENTS.md and production checklist. Verify the target container, active HOME/state root, canonical agent, Telegram account and Zalo account. Do not guess among multiple accounts or change bindings to make installation pass.

Run from this skill directory on the Docker host:

```bash
python3 scripts/deploy.py --member MEMBER --dry-run
python3 scripts/deploy.py --member MEMBER --apply
python3 scripts/deploy.py --member MEMBER --check
```

For a different layout, supply `--container`, `--openclaw-root`, `--runtime-home`, `--runtime-root`, `--agent`, `--telegram-account` and `--zalo-account` explicitly. Host/runtime roots must map through the selected container's actual mounts. The helper supports Linux Docker + Supervisor, the two tested stable core releases above, and a workspace inside that runtime state root; it stops before changing unsupported targets. Preserve a Node runtime satisfying the selected core's installed `package.json` engines; this helper does not upgrade Node or OpenClaw.

Plugin package `1.2.0` declares the bounded API range `>=2026.9.9 <=2026.10.6`, not an exact `2026.9.9` pin or an unbounded future-version promise. The old pin makes OpenClaw `2026.10.6` skip the plugin, removing both the tool and `/zaloqr`. `--check` now rejects stale package metadata as well as stale payload/settings. Existing deployments are not updated by editing this host skill; use the selected-target deployment flow only when authorized. Keep the legacy plugin ID when present.

The installed routing SDK must resolve both selected accounts to the canonical agent. An existing default-agent fallback is supported without adding bindings; conflicting account/channel bindings still stop deployment. Select the configured Telegram account explicitly when an empty `default` account also exists. Never change routing or owners merely to pass preflight.

For a legacy-home member such as `nndungct`, run from the Docker host:

```bash
SKILL=/root/.agents/skills/telegram-zalo-owner-login
MEMBER=nndungct
python3 "$SKILL/scripts/deploy.py" --member "$MEMBER" \
  --openclaw-root "/root/Apps/member_vps/docker-users/data/$MEMBER/.openclaw" \
  --runtime-home "/home/$MEMBER" --runtime-root "/home/$MEMBER/.openclaw" \
  --agent main --telegram-account "$MEMBER" --zalo-account default --dry-run
```

After inspecting the plan, rerun the same command with `--apply`, then `--check`. Substitute only values verified from the target's mounts, config and account routing. A different OpenClaw release requires separate compatibility validation, not bypassing the version guard.

The helper privately backs up config, native state and affected files, quiesces only that member Gateway under existing watchdog locks, installs the linked plugin through the official installer, validates, and starts the same Gateway. Known legacy `vuhoainam-telegram-zalo-login` is upgraded in place; no second `/zaloqr` registration. It copies only the runtime skill into the member workspace, not Docker-host administration scripts. Reruns update the managed files without adding duplicate instructions.

## Owner and delivery rules

- Owners come dynamically from the existing `commands.ownerAllowFrom`, numeric IDs or `telegram:ID`. Wildcards and other-channel owners do not qualify. This skill never adds owners or treats public `allowFrom: ["*"]` as ownership.
- Require trusted owner authority, matching account/agent and a private destination matching the requesting sender. Each owner receives their own QR; never send all owners a broadcast or send QR to a group.
- Tool `telegram_zalo_login_qr` handles natural requests; `/zaloqr` is the native, model-independent command. Only explicit login/QR requests start login, not status checks.
- Keep login alive while sending the current image, require an exact Telegram receipt, cap the attempt at 180 seconds and prevent concurrent attempts. An existing lock is not automatically deleted; inspect its PID before any owner-approved recovery.
- The 180-second cap is the attempt timeout, not an extension of Zalo's QR validity. The current helper sends one fresh image per attempt; it does not promise automatic QR renewal. After expiry, wait for the previous attempt to end before requesting `/zaloqr` again. Do not replace a QR while the phone is confirming it.
- Do not logout, replace another member's credentials, open full tools to non-owners, publish QR, or restart other containers. CLI login completion is not proof that the Zalo listener is running.

## Verify and report

Check config validation, plugin doctor, runtime skill readiness, owner/non-owner/group tool assembly, and Telegram status/probe. Deployment does not send a test message or create a QR. Ask an existing owner to try `/zaloqr` or a natural login request, then scan on the phone; distinguish plugin installed, QR receipt and verified Zalo connectivity.

The helper reports but tolerates the exact existing `duckduckgo` provenance-only warning when plugin errors, source shadowing, compatibility findings and configuration warnings are empty. It does not change that plugin's trust or config; other doctor failures still stop deployment.

Backups are recorded by the helper under `/root/_Backups/telegram-zalo-owner-login/`. On deployment failure it restores its affected files/config/native snapshot while the Gateway is stopped, then restores the previous running state. Review the private backup if rollback itself fails. Update the target project note and change journal without IDs or secrets.

The source asset `assets/index.mjs` and helper are portable to another Docker VPS host. Do not rollout elsewhere without a selected target and owner authorization. Revalidate SDK/CLI before supporting a different core release or prerelease/correction suffix. Offline helper regressions run with `python3 -m unittest discover -s scripts -p 'test_*.py' -v`; they do not log in, send messages or change a live member.

## Inputs, outputs and reruns

- Input: one authorized member/container, verified host/runtime state roots, canonical agent and configured Telegram/Zalo account selectors. Owners are read from existing config; never supply credentials or grant owners through this installer.
- Output: the linked plugin under `<state-root>/tools/telegram-zalo-owner-login`, its non-secret settings/manifest, the runtime skill under `<workspace>/skills/telegram-zalo-owner-login/SKILL.md`, and one managed section in workspace `AGENTS.md`. Existing legacy plugin IDs retain their managed directory.
- Deployment backups/private logs: `/root/_Backups/telegram-zalo-owner-login/<container>/<timestamp>/`. Login-attempt logs: `<state-root>/tmp/telegram-zalo-login/`; temporary outbound QR images: `<state-root>/media/outbound/zalo-login-*`, removed at attempt completion. Protect private logs and QR as credentials; never publish or paste their contents.
- Rerun deployment for the same selected target to update the managed payload. Use `--check` for verification only; neither deployment nor checks create a QR or send messages. Actual login is owner-triggered via `/zaloqr` in the matching bot's private chat.
- No Google Sheet, public QR endpoint, cron, DNS or external dashboard is required or written. Keep host administration code out of member workspace skills; only the runtime instructions belong there.

## Verified deployment

On `2026-10-24`, deployed to `user-nndungct` on `2026.9.9` using legacy HOME `/home/nndungct`, Telegram account `nndungct`, Zalo account `default` and canonical agent `main`. The native `/zaloqr` appeared in the Telegram bot menu; payload/config/plugin checks, owner/non-owner/group/wrong-account authorization checks and Telegram probe passed. Existing owners, credentials, routing and other containers were unchanged. Installation did not generate a QR or log Zalo in; the owner must request `/zaloqr` and scan it.

Before applying to `2026.10.6`, the installed CLI login options, QR-image output contract, native owner-command context, version-2 tool authority and SDK routing were inspected in that release. Run the same deployment/check/channel acceptance for the selected member; these checks never authorize an automatic login or a broader rollout. Other releases and prereleases remain blocked.

## Lỗi đã gặp / Checklist

- Sự cố `/zaloqr` ngày 26/10/2026: `package.json` phải dùng `pluginApi` range, không pin exact `2026.9.9`. Bundle hiện kiểm thử `>=2026.9.9 <=2026.10.6`; kiểm tra core thực tế trước khi nới giới hạn. Giữ plugin ID legacy, không đăng ký trùng tool/command.
- Parser receipt phải lấy từng dòng/khối JSON độc lập bằng `matchAll`, chịu được log thừa trước/sau (kể cả `[state/agent-db] ... clean-close receipt`); vẫn kiểm tra đúng owner/chat, `ok` và message ID. Timeout delivery `60000` ms; không parse toàn bộ phần stdout còn lại bằng `JSON.parse`.
- Khi CLI gửi ảnh đã exit 0 nhưng chỉ đọc receipt lỗi, giữ login sống đến khi hoàn tất/hết hạn (tối đa 180 giây), không để `finally` stop sớm. Báo delivery chưa xác minh (`qrSent: null`), không tự gửi lại hoặc báo giao ảnh/đăng nhập thành công.
- Trước cài: chạy `node --test scripts/test_receipt.mjs` và `python3 -B scripts/test_deploy.py` trong skill `telegram-zalo-owner-login` (offline, không tạo QR/gửi tin). Sau cài: `openclaw plugins list --json` và `openclaw plugins inspect <id> --runtime --json` phải thấy `loaded`, tool `telegram_zalo_login_qr` và command `zaloqr`; có config/doctor sạch không đủ chứng minh plugin load.
- Khi được phép apply runtime, backup từng file `<file>.bak-<timestamp>`, giữ watchdog lock đúng member rồi `openclaw plugins reload <id> --json`; `restartRequired=false` thì KHÔNG restart. Nếu `true` hoặc reload lỗi, dừng và hỏi owner, không tự restart gateway/container/service. Sửa kho skill/template không đồng nghĩa đã reload member; không chạy helper `--apply` có stop/start khi task cấm restart.
- Probe `zalouser` mỗi **30 phút**, lệch phút giữa member; không tự đổi cron production. Không logout, tạo/gửi QR hay gửi tin Telegram/Zalo trong lượt sửa/kiểm thử offline; live test chỉ khi owner yêu cầu riêng.
