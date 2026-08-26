# Credential Reuse and Threat Model

## What the pair controls

Telegram Local Bot API needs:

- api_id: numeric identifier of a Telegram application.
- api_hash: application credential used by the server when connecting to Telegram data centers.
- bot token: identity and authorization for one bot; keep it separate from the app pair.

The app pair is not a replacement for bot tokens. Every bot still needs its own token in the OpenClaw configuration or secret provider.

An app pair may be reused across VPSes, but a single bot token must not be polled by two VPSes concurrently. Move a bot with an explicit logOut handover; otherwise Telegram can return 409 Conflict and updates may be lost or processed twice.

## Reuse decision

A single app pair can be used by multiple Local Bot API instances. Telegram identifies those instances as the same application, so reuse is technically valid when all VPSes are controlled by the same operator.

Prefer separate pairs when:

- VPSes belong to different customers, teams, or trust zones.
- One VPS is staging, experimental, or internet-exposed.
- An incident must be contained to one environment.
- Independent rate-limit or suspension behavior is important.

If reusing one pair, keep the same pair in each VPS's mode-600 secret file, never in the skill or compose file. Record only that a shared app credential is in use, not the value.

## Risks

- api_hash leakage can let an attacker use the application credential against Telegram's client API. Treat it as a secret.
- A compromised VPS can expose the pair to every VPS that reuses it.
- Shared app identity can couple rate limits, abuse detection, and suspension impact.
- Copying one bot token to parallel polling gateways creates a second, separate conflict risk even when the app pair is valid.
- Local Bot API data directories may contain bot-token-derived directory names and downloaded media; restrict the parent directory to the service and root.
- The Local Bot API still requires outbound network access to Telegram data centers.

## Mitigations

- Use a dedicated credential file with mode 600 and a narrow parent directory.
- Bind the HTTP listener to 127.0.0.1 and put authentication/reverse proxy in front only if there is a reviewed need.
- Pin the container image digest and update it deliberately.
- Avoid printing environment variables, full URLs containing bot tokens, or docker inspect output in logs.
- Keep a redacted, timestamped OpenClaw config backup before migration.
- Rotate/revoke the app credential through Telegram's application management if compromise is suspected, then update every affected VPS in a coordinated maintenance window.
