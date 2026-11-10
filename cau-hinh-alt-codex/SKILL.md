---
name: cau-hinh-alt-codex
description: Configure Codex Extension/Codex CLI through ALT/9Router while isolating the vendor API credential, the customer ChatGPT session, and Antigravity extension updates. Use for Windows, Linux, macOS, VPS, model changes, profile provisioning, existing two-platform migrations, and auth/provider mix-ups.
---

# Isolated ALT Codex Configuration

This skill incorporates model, provider, backup, and validation conventions from:
`https://github.com/nhuanlaptrinh/cau-hinh-alt-codex_new`

Always isolate identities before changing a model or copying configuration.

## Goals

- Codex Extension uses the vendor API key/service account in its own Codex profile.
- Customer ChatGPT remains in the customer's browser profile.
- Antigravity/extension updates do not delete the profile configuration or credential.
- Every customer has a distinct `profile_id` and `CODEX_HOME`.
- Never write a real API key to this skill, a repository, logs, a response, or a command line.

## Mandatory Rules

1. Do not use `%USERPROFILE%\\.codex` or `$HOME/.codex` for customer-distributed workflows when a dedicated profile can be created.
2. Never copy `auth.json` from the skill, upstream repository, or another machine. Use only sanitized model/provider configuration.
3. Never change the customer's existing ChatGPT cookies, local storage, session, or browser profile.
4. Do not put the API key in User/System environment variables unless required. Pass `CODEX_HOME` and credential only to the Codex process that needs them.
5. Never modify the installed extension directory to persist configuration. Updates overwrite it. Use a launcher/profile root outside that directory.
6. Before writing, resolve and show the destination, reject `profile_id` containing `..`, separators, or control characters, and back up existing files.
7. If the user only asks to update this skill, edit and validate the skill only. Do not create profiles, write credentials, or restart Antigravity.
8. Do not create, rename, or replace customer shortcuts automatically. When an existing Antigravity shortcut is supplied, update that shortcut in place; never modify the customer ChatGPT shortcut.

## Isolation Architecture

```text
Antigravity/Codex process
  CODEX_HOME = <persistent-root>\\<profile-id>\\.codex
  config.toml = API provider + model + forced API auth
  auth.json  = profile credential only if this build needs a file auth store

Customer ChatGPT browser profile
  cookies/local storage/OAuth = customer account

Extension installation/update directory
  extension code only; no long-lived credential
```

Default Windows root:
`%LOCALAPPDATA%\\YourProduct\\codex-profiles\\<profile-id>\\.codex`

Override it with `ALT_CODEX_PROFILE_ROOT`. On Linux/macOS use:
`${XDG_STATE_HOME:-$HOME/.local/state}/your-product/codex-profiles/<profile-id>/.codex`.

Pass `CODEX_HOME` to the Codex process rather than setting it globally when possible. After an extension update, restart through `scripts/launch_antigravity_isolated.ps1`; it continues to use the same persistent root.

For a customer who already has shortcuts, do not create a new one. Update the existing Antigravity shortcut in place:

```powershell
pwsh -File .\scripts\update_existing_shortcut.ps1 `
  -ProfileId customer-001 `
  -ExistingShortcutPath "$env:USERPROFILE\Desktop\Antigravity.lnk" `
  -AntigravityPath "C:\Path\To\Antigravity.exe" `
  -UserDataDir "$env:LOCALAPPDATA\Antigravity-Codex\browser\customer-001"
```

The script keeps the existing shortcut name, location, icon, and customer ChatGPT shortcut. It only changes the Antigravity shortcut target so the full application opens with the vendor `CODEX_HOME` and the customer `UserDataDir`; it also saves a timestamped `.bak` copy. Never pass the ChatGPT shortcut to this script.


## Codex Configuration

Preserve unrelated keys in `CODEX_HOME/config.toml` and use a shape like this:

```toml
model_provider = "router"
model = "GPT-5.6-sol"
preferred_auth_method = "apikey"
forced_login_method = "api"
cli_auth_credentials_store = "file"

[model_providers.router]
name = "router"
base_url = "https://codex.anhlaptrinh.vn/v1"
wire_api = "responses"
```

Use only a `base_url` and provider supplied by the user or already present in active configuration. Do not replace a production endpoint by assumption.

`forced_login_method = "api"` prevents Codex from falling back to ChatGPT login for this profile. If the installed Codex version does not support it, stop and report it; do not delete `auth.json` or replace the customer's credential.

With `cli_auth_credentials_store = "file"`, auth data must be inside the profile's `CODEX_HOME`, never next to `SKILL.md`. Use `ephemeral` only if the installed build supports it and the user wants no file credential.

## Customer Already Has ChatGPT

1. Do not open Antigravity with a browser profile containing the vendor ChatGPT account.
2. Keep the customer's existing ChatGPT shortcut and browser profile unchanged; create a dedicated Antigravity `UserDataDir` only for the Antigravity shortcut.
3. Let the customer sign in to ChatGPT in that profile using the customer's account.
4. Start Codex with its own `CODEX_HOME` and `forced_login_method = "api"`.
5. If Antigravity cannot isolate browser profiles/partitions, use a separate Windows user or application instance. Renaming `.codex` alone is not enough if browser cookies remain shared.
6. After an extension update, restart through the same launcher. Do not sign in through ChatGPT when the target is API auth.

If ChatGPT still shows the vendor account, inspect browser profile/cookies first. An API key is not a ChatGPT cookie. Do not delete customer browser data.

## Existing Two-Platform Migration

Use this mode when the customer already has both ChatGPT and Antigravity/Codex, and accounts are mixed or the first install used the wrong profile.

1. Close ChatGPT, Antigravity, and the Codex extension before changing the runtime.
2. Do not delete, sign out of, or overwrite the customer ChatGPT browser profile.
3. Do not replace the old `.codex` directory. Create a timestamped backup of `config.toml` only; never copy its `auth.json` into the new profile.
4. Create a new persistent Codex profile for the vendor API identity.
5. Create a separate Antigravity `UserDataDir`; the customer can sign in there with the customer's ChatGPT account. Never copy browser cookies/local storage between platforms.
6. Run Antigravity through `scripts/launch_antigravity_isolated.ps1` with the new `CODEX_HOME` and `UserDataDir`.
7. Update the existing Antigravity shortcut in place with `scripts/update_existing_shortcut.ps1`; do not create or replace the customer ChatGPT shortcut.
8. Test both identities after restart and after a simulated extension update.

Use the migration helper:

```powershell
pwsh -File .\\scripts\\repair_existing_platforms.ps1 `
  -ProfileId customer-001 `
  -ExistingCodexHome "$env:USERPROFILE\\.codex" `
  -CustomerChatGPTDataDir "C:\\Path\\To\\Customer\\ChatGPT\\Profile" `
  -AntigravityUserDataDir "$env:LOCALAPPDATA\\Antigravity-Codex\\browser\\customer-001" `
  -BaseUrl https://codex.anhlaptrinh.vn/v1 `
  -SourceSkillPath "$HOME\\.codex\\skills\\cau-hinh-alt-codex" `
  -ExistingShortcutPath "$env:USERPROFILE\\Desktop\\Antigravity.lnk" `
  -AntigravityPath "C:\Path\To\Antigravity.exe"
```

The helper backs up only the old Codex `config.toml`, creates the new isolated profile, creates an empty Antigravity user-data directory, and writes a non-secret migration manifest. It never copies ChatGPT cookies, `auth.json`, API keys, or OAuth tokens.

## Install the Skill Into a Persistent Profile

The skill is installed globally on the development machine, but a customer machine using a separate `CODEX_HOME` must also receive a sanitized copy. Install it under `<CODEX_HOME>\\skills\\cau-hinh-alt-codex`, never inside the Antigravity extension directory.

```powershell
pwsh -File .\\scripts\\install_skill_into_profile.ps1 `
  -SourceSkillPath "$HOME\\.codex\\skills\\cau-hinh-alt-codex" `
  -CodexHome "$env:LOCALAPPDATA\\Antigravity-Codex\\profiles\\customer-001\\.codex"
```

The installer backs up an existing skill directory and excludes `auth.json`, `.env`, PEM files, and key files. This keeps the skill available after extension updates without distributing credentials.

## Provision a Profile

Use:

```powershell
pwsh -File .\\scripts\\prepare_isolated_profile.ps1 `
  -ProfileId customer-001 `
  -Model GPT-5.6-sol `
  -BaseUrl https://codex.anhlaptrinh.vn/v1

```

The script creates the persistent directory, backs up an existing `config.toml`, and writes isolated configuration. It does not discover or print an API key.

To update an existing Antigravity shortcut during provisioning, also pass `-ExistingShortcutPath` and `-AntigravityPath`; the skill updates that shortcut in place. If no existing shortcut is supplied, the skill creates no shortcut and leaves all customer shortcuts unchanged.

If `auth.json` is required, enter the credential directly on the machine or use the OS credential store. Never accept a key in chat or as a command-line argument. Create auth data in the destination profile only.

## Upstream Model Workflow

Keep the upstream model mapping:

- `gpt-5.4`
- `gpt-5.5`
- `GPT-5.6`
- `GPT-5.6-sol`
- `GPT-5.6-terra`
- `GPT-5.6-luna`

Use `scripts/launch_antigravity_isolated.ps1` for every Antigravity restart/update, and use `scripts/set_alt_model.sh` for Codex/OpenClaw shell workflows. It must back up before editing, change only the requested model, validate configuration, and restart the gateway only when requested. Never use it to copy credentials.

Resolve `CODEX_HOME/config.toml` from the active profile; do not fall back to the default `.codex` when the extension is launched with an isolated profile.

## Validation After Install or Update

Report completion only after checking:

- Codex receives the persistent `CODEX_HOME`.
- `config.toml` has the expected provider/model and `forced_login_method = "api"`.
- Credential state is reported as set/missing without printing its value.
- ChatGPT shows the customer's email/avatar in the customer's browser profile.
- Restarting Antigravity preserves both identities.
- Updating/reinstalling the extension does not remove profile data.
- No API key, cookie, `auth.json`, or token appears in logs or reports.

If browser profile or process environment cannot be checked, report that isolation is not fully verified.

## Handoff Safety

- Do not package the vendor API key in an extension distributed to customers. Prefer a backend/service account or customer-specific key with limits and revocation.
- Never commit `auth.json`, `.env`, tokens, cookies, or credential backups.
- Never delete old profiles/configuration automatically. Back up and create a new profile; let the user decide when to revoke old credentials.
- If a repository or skill directory contains a real credential, do not read it; isolate it and report that the key must be rotated/revoked.
