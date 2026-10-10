---
name: telegram-zalo-owner-login
description: Create and privately deliver a Zalo Personal login QR when an existing Telegram owner explicitly requests login. Prefer telegram_zalo_login_qr or /zaloqr; not for status-only requests or non-owner/group QR delivery.
---

# Zalo login QR from Telegram

When a configured Telegram owner explicitly asks for a Zalo Personal login QR in the bot's private chat, call `telegram_zalo_login_qr` with `confirm: true`. It sends the current QR image immediately to the requesting owner and keeps login alive up to 180 seconds. The owner may use `/zaloqr` directly without model planning.

The plugin reads the existing Telegram owners dynamically. Never use an ID supplied by message text as the recipient, broadcast QR to other owners, or send it to a group. Non-owner/group/wrong-account tools are intentionally unavailable.

OpenClaw generic exec blocks interactive channel login independently of full permissions. Do not retry the blocked command through wrappers or insist on dashboard use. If the dedicated tool is unavailable in an owner DM, report the missing plugin/account/authority so the operator can check it.

Report only the tool's actual receipt and outcome. `login_completed` means the CLI completed; check the correct Zalo account's status before saying the listener is connected. A QR sent without confirmation is not a successful login. An active lock means no concurrent login; never delete locks/credentials blindly. Do not start login just to inspect status.
