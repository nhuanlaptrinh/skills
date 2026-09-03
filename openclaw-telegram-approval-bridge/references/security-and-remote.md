# Security And Remote Operation

## Approval Types

- Exec and plugin approvals have configurable forwarding targets and native Telegram approval controls on supported OpenClaw versions.
- Delegated persistent `system-agent` proposals may be registered in the Gateway without a Telegram forwarding route. The bridge lets the canonical agent act only after an exact owner explicitly approves in the same DM.
- The proposal hash shown to a user is a mutation fingerprint, not necessarily the pending approval record ID. Always query `openclaw approvals pending --json` and resolve the real `system-agent:<id>` record.
- Every verified exact owner present in the guarded owner layers is approval-authorized by default for Skill Workshop (`plugin`) and persistent `system-agent` proposals. The authority is explicit per live proposal; it does not set `approvalPolicy=auto` or bypass source, agent, expiry, and `allow-once` checks.

## Owner Verification

The installer requires the exact Telegram ID to be present in all guarded owner layers before it writes workspace files. This prevents the bridge from becoming a substitute for proper owner policy.

The runtime helper additionally requires:

- `commands.ownerAllowFrom` contains the exact sender.
- The pending record kind is `system-agent`.
- The record belongs to the configured canonical agent.
- The approving sender is an exact Telegram owner in a direct DM. The proposal source must be an exact owner in a direct Telegram/Zalo DM or an explicitly enabled Zalo group on that agent; unknown groups and non-owner sources are rejected.
- The summary is a persistent `OpenClaw change` and the request has not expired.

These checks do not replace human intent matching. The agent must still compare the pending summary to the proposal the owner explicitly approved.

The runtime helper parses JSON with Python 3's standard library. It must not depend on `jq`: in the legacy shell helper, a missing `jq` made the owner check return false and emitted the misleading message that a correctly configured sender was not an owner.

## Remote VPS Workflow

1. Confirm SSH host identity and the target OpenClaw process before copying or running anything.
2. Copy this skill directory or only its installer/helper to a root-only temporary location on the target.
3. Run inventory and dry-run on the target host. Do not fetch or print credentials to the controller.
4. Apply only after the owner authorizes that target VPS and Telegram ID.
5. Restart or reload only the affected Gateway/channel when required; never recreate an unrelated container.
6. Run checks on the target and retain the printed rollback manifest outside the OpenClaw persistent data directory.

For a container/member VPS, pass host paths to the installer and runtime paths to `--runtime-openclaw-root`. Do not write host paths into the runtime `AGENTS.md` command examples.

## Native Feature Upgrade

Before each new deployment, inspect the installed OpenClaw schema/docs. If `system-agent` becomes a first-class Telegram forwarding kind with owner-authorized buttons or `/approve`, prefer that native route and avoid maintaining a redundant bridge. Preserve the bridge only when it is still required for delegated configuration proposals.

## Rollback Safety

Apply stores before/after checksums. Rollback stops when either managed file changed after installation. Review and merge manually instead of overwriting newer workspace policy.
