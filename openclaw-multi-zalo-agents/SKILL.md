---
name: openclaw-multi-zalo-agents
description: Create multiple isolated OpenClaw Zalo personal-account assistants with separate workspaces, account profiles, and routing on Windows, macOS, Linux, or Docker. Use when adding or inspecting another Zalo assistant without resetting existing accounts.
---

# Multiple Zalo assistants

Set up one OpenClaw agent, workspace, Zalo account ID, and Zalo profile per assistant. Preserve every existing account and its routing. A workspace separates agent files and context; it is not an OS security sandbox or an independent OpenClaw gateway. Use separate OS/container isolation if security isolation is required.

## Before changing anything

1. Identify the target installation, OS, service user, actual OpenClaw state directory, service manager/container, plugin and core versions, and account IDs. Resolve paths in the runtime's filesystem; do not assume `/root`, Docker, a particular supervisor, or a global npm location. On Windows use PowerShell and `$env:USERPROFILE`; on macOS/Linux use the service user's home. Check installed CLI help and plugin schema before using version-specific commands.
2. Read applicable repository and local safety instructions. Inspect `openclaw agents list`, `openclaw agents bindings`, `openclaw channels status --channel zalouser --probe --json`, and the existing config, without revealing credentials, QR images, user IDs or personal message contents. Record account health and current group/DM policies. `linked` is not the same as `connected`.
3. Ask for the new assistant name/agent ID, workspace, Zalo account/profile ID, model and requested access policies when missing. Ask explicitly before opening DMs, expanding group permissions, giving exec access, or copying skills from another workspace. Copy only explicitly selected skill files; never copy credentials, Zalo profiles, session databases, model tokens, or owner IDs. Note that per-workspace skills may shadow shared skills.
4. Back up the config and any files to be modified to a private location; protect permissions on the target OS. Preserve existing state and account data; never reset or log out another account. Plan rollback without restoring old Zalo credential/session databases over live state. Check whether activating changes needs a gateway restart and get consent for the disruption.

## Configure

- Use the installed OpenClaw version's documented agent and channel APIs. In a compatible CLI, `openclaw agents add <agent-id> --workspace <workspace>` creates an agent, and `openclaw agents bind --agent <agent-id> --bind zalouser:<account-id>` adds an account-specific binding. Inspect `--help` first and verify no duplicate/conflicting binding. Do not repurpose an existing agent or the default Zalo account.
- Add a distinct `channels.zalouser.accounts.<account-id>` entry with an independent `profile`, using the installed schema. Preserve account and global policy fields. Set DM/group/mention and sender allowlists exactly as requested; do not assume a group name or requireMention setting. A Zalo profile is not a workspace.
- Validate the resulting configuration (`openclaw config validate` when supported), inspect routing and permissions, then activate through the existing service manager. Do not start a second gateway or restart the host/container as a shortcut. Recheck all previously connected accounts.
- With the owner's consent, log in **only the new profile**. `openclaw channels login --channel zalouser --account <account-id>` is available in some versions; inspect help and verify the plugin supports the flow first. `/zaloqr` may be a local customization, not a universal OpenClaw command. Generate a fresh QR for the correct account, deliver it only over an explicitly authorized secure channel, never reuse stale QR material, and do not log out other profiles.
- Verify account-to-agent binding, distinct workspace/profile, agent skills, existing group policies and probe results. Ask the user to perform an authorized test per account; do not send messages to real people or groups merely to test. Report linked/running/connected/probe separately and identify anything unverified.

On Windows, macOS and Linux the steps are the same, but paths, service-control commands, authentication, and plugin support differ. Docker commands must run in the correct container and use persistent mounts. Do not claim an untested OS or Zalo plugin version is compatible.
