---
name: cau-hinh-alt-codex
description: Configure Codex Extension/Codex CLI through ALT/9Router while separating the vendor API credential, customer ChatGPT session, and Antigravity local Recents/Folders state. Use for new installs, existing-platform migrations, auth or history mix-ups, and extension updates.
---

# Isolated ALT Codex Configuration

This skill incorporates model, provider, backup, and validation conventions from:
`https://github.com/nhuanlaptrinh/cau-hinh-alt-codex_new`

Always isolate identities before changing a model or copying configuration.

## Goals

- Codex Extension uses the vendor API key/service account in its own Codex profile.
- Customer ChatGPT remains in the customer's browser profile.
- Antigravity/Codex uses its own IDE user-data directory and local Recents/Folders state.
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
9. Do not reuse the customer ChatGPT data directory or old Antigravity user-data directory for the isolated Codex instance. Separate `CODEX_HOME` alone does not isolate IDE state.
10. Never delete, edit, or copy the old `state.vscdb`, `storage.json`, workspace state, cookies, or OAuth data to the new profile. Leave nonempty target directories intact and choose a new empty target.
11. Do not claim complete separation until actual processes, authentication, Recents and Folders are tested. Do not promise that API-key mode includes ChatGPT-only or cloud features.

## Isolation Architecture

```text
Antigravity/Codex process
  CODEX_HOME = <persistent-root>\\<profile-id>\\.codex
  --user-data-dir = <separate-persistent-Antigravity-user-data-dir>
  config.toml = API provider + model + forced API auth
  auth.json  = profile credential only if this build needs a file auth store
  User/globalStorage and User/workspaceStorage = isolated IDE/extension state

Customer ChatGPT browser profile
  cookies/local storage/OAuth = customer account

Extension installation/update directory
  extension code only; no long-lived credential
```

Default Windows root:
`%LOCALAPPDATA%\\YourProduct\\codex-profiles\\<profile-id>\\.codex`

Override it with `ALT_CODEX_PROFILE_ROOT`. On Linux/macOS use:
`${XDG_STATE_HOME:-$HOME/.local/state}/your-product/codex-profiles/<profile-id>/.codex`.

Pass `CODEX_HOME` to the Codex process rather than setting it globally when possible. Always launch Antigravity with its dedicated `--user-data-dir`, not the customer's ChatGPT profile or the old/default Antigravity directory. After an extension update, restart through `scripts/launch_antigravity_isolated.ps1`; it continues to use both persistent paths.

For a customer who already has shortcuts, do not create a new one. Update the existing Antigravity shortcut in place:

```powershell
pwsh -File .\scripts\update_existing_shortcut.ps1 `
  -ProfileId customer-001 `
  -ExistingShortcutPath "$env:USERPROFILE\Desktop\Antigravity.lnk" `
  -AntigravityPath "C:\Path\To\Antigravity.exe" `
  -UserDataDir "$env:LOCALAPPDATA\Antigravity-Codex\browser\customer-001"
```

The script keeps the existing shortcut name, location, icon, and customer ChatGPT shortcut. It changes the Antigravity shortcut target to use the vendor `CODEX_HOME` and a dedicated Antigravity `UserDataDir`; it also saves a timestamped `.bak` copy. It refuses shortcuts that do not target the specified Antigravity executable or this skill's launcher. Never pass the ChatGPT shortcut to this script. For an existing Antigravity install, isolate its state first as described below; changing a shortcut alone does not clean an already-used target directory.

If the shortcut already has arguments, the script stops rather than silently discarding them. Inspect the arguments and confirm that all required launch behavior is retained; do not proceed if it cannot be preserved. Only with the customer's consent to replace the reviewed arguments, pass `-ReplaceReviewedShortcutArguments`. A previously configured shortcut from this skill also has arguments and requires that review. The original remains in the shortcut backup.


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

`forced_login_method = "api"` restricts Codex to API authentication in supported versions. A mismatched active login may be logged out, so verify the effective `CODEX_HOME` and credential store are the dedicated profile before launch. If the installed build does not support the setting, stop and report it; do not delete `auth.json` or replace the customer's credential.

With `cli_auth_credentials_store = "file"`, auth data must be inside the profile's `CODEX_HOME`, never next to `SKILL.md`. Use `ephemeral` only if the installed build supports it and the user wants no file credential.

## Customer Already Has ChatGPT

1. Keep the customer's existing ChatGPT shortcut, account, browser/app data and history unchanged.
2. Create a dedicated Antigravity `UserDataDir` for the API-only Codex instance, distinct from both the customer ChatGPT profile and the old Antigravity directory.
3. Start Codex with its own `CODEX_HOME` and `forced_login_method = "api"`; do not sign the customer's ChatGPT account into that Codex instance.
4. Update the existing Antigravity shortcut in place only after the isolated profile is prepared. Do not create a replacement ChatGPT shortcut.
5. If Antigravity cannot isolate its user data, use a separate application instance or OS user. Renaming `.codex` alone is insufficient.
6. After an extension update, restart through the same launcher and verify both paths and both histories again.

If ChatGPT still shows the vendor account, inspect browser profile/cookies first. An API key is not a ChatGPT cookie. Do not delete customer browser data.

## Existing Two-Platform Migration

Use this mode when the customer already has both ChatGPT and Antigravity/Codex, and accounts are mixed or the first install used the wrong profile.

1. Identify the actual customer ChatGPT data directory, old Antigravity `UserDataDir`, and target Codex `UserDataDir`; verify they are distinct and not aliases/junctions of one another. Keep Antigravity open when creating an empty profile; copying reviewed settings requires closing the source first.
2. Do not delete, sign out of, or overwrite the customer ChatGPT browser profile.
3. Do not replace the old `.codex` directory. Create a timestamped backup of `config.toml` only; never copy its `auth.json` into the new profile.
4. Create a new persistent Codex profile for the vendor API identity.
5. Create a separate Antigravity `UserDataDir` using `scripts/isolate_antigravity_profile.ps1`. By default copy no settings. Only after reviewing settings, keybindings and snippets for secrets and profile/environment overrides may they be copied; never copy local history, extension state or browser sessions.
6. Run Antigravity through `scripts/launch_antigravity_isolated.ps1` with the new `CODEX_HOME` and `UserDataDir`.
7. Update the existing Antigravity shortcut in place with `scripts/update_existing_shortcut.ps1`; do not create or replace the customer ChatGPT shortcut.
8. Test both identities and local Recents/Folders after restart and after a real extension update when available.

Use the migration helper:

```powershell
pwsh -File .\scripts\repair_existing_platforms.ps1 `
  -ProfileId customer-001 `
  -ExistingCodexHome "$env:USERPROFILE\.codex" `
  -CustomerChatGPTDataDir "C:\Path\To\Customer\ChatGPT\Profile" `
  -ExistingAntigravityUserDataDir "$env:APPDATA\Antigravity IDE" `
  -AntigravityUserDataDir "$env:LOCALAPPDATA\Antigravity-Codex\browser\customer-001" `
  -BaseUrl https://codex.anhlaptrinh.vn/v1 `
  -SourceSkillPath "$HOME\.codex\skills\cau-hinh-alt-codex" `
  -ExistingShortcutPath "$env:USERPROFILE\Desktop\Antigravity.lnk" `
  -AntigravityPath "C:\Path\To\Antigravity.exe"
```

The helper backs up the old Codex `config.toml`, leaves the old Antigravity and ChatGPT profiles untouched, creates a fresh Antigravity state, and writes non-secret manifests. It never copies `state.vscdb`, `storage.json`, workspace state, ChatGPT cookies, `auth.json`, API keys, or OAuth tokens. If the target already contains data, it stops; choose a new empty target. To preserve settings/keybindings/snippets, review those files without exposing secrets and add `-CopyReviewedAntigravitySettings` only if they contain no credentials or overrides that would reconnect the old profile.

## Recents And Folders Isolation

On the observed Windows Antigravity build, `User/globalStorage/state.vscdb` contains `history.recentlyOpenedPathsList` and `openai.chatgpt`; other state may exist in `storage.json`, `workspaceStorage`, `CODEX_HOME`, or a service account. File names and keys can change between versions, so treat these as diagnostic clues, not a complete schema. Never edit the database in place.

For an existing profile, `scripts/isolate_antigravity_profile.ps1` prepares a new target without copying those state stores. The installed extension code normally remains in the existing extension installation directory, but profile-specific extension state, workspace history and some settings may need reconfiguration. The old mixed data remains in the source or backup; the helper cannot determine which historical entry belongs to which identity and does not automatically restore or divide it. Confirm the customer accepts this before switching the existing shortcut. Reopen desired folders manually in the appropriate instance.

When identity/API isolation already works, the actual `CODEX_HOME` paths are confirmed distinct, and only Recents/Folders are mixed, do not run full provisioning or rewrite `CODEX_HOME/config.toml`. Preserve the existing `ProfileId`, `ProfileRoot`, credential and ChatGPT shortcut. If the user has requested the switch and accepts the fresh empty IDE state, do the work directly; do not require a separate confirmation or ask them to close the IDE just to create a fresh profile. Verify the current paths and a distinct empty target, then prepare the target with `scripts/isolate_antigravity_profile.ps1` without `-CopyReviewedSettings` while the old window stays open. Launch the isolated instance with `scripts/launch_antigravity_isolated.ps1` using the existing Codex profile and the new target. Do not close, restart, or force-terminate the old window; it may host this conversation and unsaved work.

Verify a running Antigravity process actually uses the target `--user-data-dir` and that the intended Codex profile and API authentication work. If launch is redirected to the old instance, the build refuses multiple profiles, or either profile cannot be verified, stop and report that a safe restart or additional user action is needed; do not report success or change the shortcut. Once the new instance is verified, update the existing Antigravity shortcut using the same `ProfileId`/`ProfileRoot` and new target, subject to the shortcut argument safety checks. If its original arguments cannot be preserved without review, stop and explain rather than silently replacing them. Tell the user the old window remains open and can be closed after saving when convenient; the new window starts with empty local Recents/Folders and may require its own settings or login. Do not claim the current conversation will transfer automatically. Never transfer keys or account data automatically.

The following commands illustrate the preparation and shortcut update; launch and verify the isolated instance between them:

```powershell
pwsh -File .\scripts\isolate_antigravity_profile.ps1 `
  -ProfileId customer-001 `
  -SourceUserDataDir "C:\Path\To\Current\Antigravity\UserData" `
  -TargetUserDataDir "$env:LOCALAPPDATA\Antigravity-Codex\browser\customer-001-fresh"

pwsh -File .\scripts\launch_antigravity_isolated.ps1 `
  -ProfileId customer-001 `
  -ProfileRoot "C:\Path\To\Existing\Codex\ProfileRoot" `
  -AntigravityPath "C:\Path\To\Antigravity.exe" `
  -UserDataDir "$env:LOCALAPPDATA\Antigravity-Codex\browser\customer-001-fresh"

# Verify the actual process path, Codex profile, and API authentication before continuing.
pwsh -File .\scripts\update_existing_shortcut.ps1 `
  -ProfileId customer-001 `
  -ProfileRoot "C:\Path\To\Existing\Codex\ProfileRoot" `
  -ExistingShortcutPath "$env:USERPROFILE\Desktop\Antigravity.lnk" `
  -AntigravityPath "C:\Path\To\Antigravity.exe" `
  -UserDataDir "$env:LOCALAPPDATA\Antigravity-Codex\browser\customer-001-fresh"
```

The target starts with empty IDE state, not necessarily empty data in the retained `CODEX_HOME` or a cloud account. Add `-CopyReviewedSettings` to the first command only after reviewing the candidate files for credentials and profile/environment overrides. If the target is nonempty, choose another directory instead of clearing it. Preserve a separate backup of old profiles when requested; such backups can contain sensitive data and must not be published.

Use the customer's existing ChatGPT shortcut/profile for their account and use the isolated Antigravity instance for API-only Codex. If a list is server-synchronized through a ChatGPT account, a local profile split or API key cannot guarantee separate cloud lists for two surfaces signed into that same account. If the customer needs ChatGPT inside Antigravity as well, use a separate app/user-data profile for that session and verify it; if the same cloud account still merges the lists, a separate account or a product-supported separation is required. Do not sign out of or replace the customer's existing account without consent.

If entries still cross after the IDE state split, inspect the effective `CODEX_HOME` for both running surfaces and the active account/provider. A retained or shared `CODEX_HOME` can itself contain history; stop and choose a distinct profile if paths overlap. Do not delete sessions or copy credentials automatically. If paths and API authentication are distinct but cloud data still appears, report the remaining account/service synchronization rather than claiming success.

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
- The running Antigravity process actually uses the dedicated `--user-data-dir`; confirm it differs from the customer's ChatGPT and old Antigravity paths, including junctions/aliases.
- Customer ChatGPT retains its expected existing Recents/Folders. Create distinct test entries in ChatGPT and API-only Codex, restart both, and verify they do not cross; do not expose private names in reports.
- The Codex instance starts without copied `openai.chatgpt` or workspace state, uses API authentication, and does not silently reconnect the customer's ChatGPT session.
- Restarting Antigravity preserves both identities.
- Updating/reinstalling the extension does not remove profile data.
- No API key, cookie, `auth.json`, or token appears in logs or reports.

If either identity, actual process paths, API authentication, history behavior, or extension-update behavior cannot be checked, report the unverified items. A fresh local state alone is not proof of cloud separation or feature parity.

## Handoff Safety

- Do not package the vendor API key in an extension distributed to customers. Prefer a backend/service account or customer-specific key with limits and revocation.
- Never commit `auth.json`, `.env`, tokens, cookies, or credential backups.
- Never delete old profiles/configuration automatically. Back up and create a new profile; let the user decide when to revoke old credentials.
- If a repository or skill directory contains a real credential, do not read it; isolate it and report that the key must be rotated/revoked.
