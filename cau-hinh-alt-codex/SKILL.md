---
name: cau-hinh-alt-codex
description: Separate an ALT/9Router API-backed Codex extension from a customer's ChatGPT or Codex desktop account while preserving credentials, shortcuts, and existing data. Use for installation, migration, account mix-ups, and extension updates; history separation is optional.
---

# Isolated ALT Codex Configuration

This skill incorporates model, provider, backup, and validation conventions from:
`https://github.com/nhuanlaptrinh/cau-hinh-alt-codex_new`

Always isolate identities before changing a model or copying configuration.

## Goals

- Codex Extension uses the vendor API key/service account in its own Codex profile.
- Customer ChatGPT or Codex desktop uses the customer's account, not the vendor router.
- Do not change, move, delete, or deliberately split existing chat history, Recents, or Folders when separating accounts.
- Antigravity/extension updates do not delete the profile configuration or credential.
- Each customer has a dedicated persistent `CODEX_HOME` for the extension.
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
9. Never reuse the customer's ChatGPT data directory. Do not create a new Antigravity `UserDataDir` solely to split history. When a separate IDE directory is required for safe authentication, explain that its local list can start empty while the old data stays untouched. Reuse a working isolated instance when available.
10. Never delete, edit, or copy the old `state.vscdb`, `storage.json`, workspace state, cookies, or OAuth data to the new profile. Leave nonempty target directories intact and choose a new empty target.
11. Do not claim account separation until both actual applications, their effective providers and identities, and an API request have been checked. History isolation is optional and must be reported separately. Do not promise API-key mode includes ChatGPT-only or cloud features.
12. Treat ChatGPT in a browser and Codex desktop as different surfaces: protecting browser cookies alone does not protect the Codex desktop provider or its `CODEX_HOME`. Never point desktop at the vendor router or modify its authentication silently.
13. If desktop already uses a router or forced API login, inspect its effective configuration and provenance. With explicit approval, back up sensitive configuration privately and make only the minimum reviewed change needed to restore customer account access. Never delete or replace `auth.json`, sign out automatically, or assume the customer is still signed in. The customer performs any required login.
14. Reuse an already functioning, verified isolated API profile; never reprovision it merely to change history. Do not update an Antigravity shortcut before validating the isolated extension and both identities; after updating, test a genuinely fresh launch and restore the backup if it fails.

## Isolation Architecture

```text
Antigravity/Codex process
  CODEX_HOME = <dedicated-Codex-directory>
  --user-data-dir = unchanged by default; separate only if needed and approved
  config.toml = API provider + model + forced API auth
  auth.json  = profile credential only if this build needs a file auth store
  User/globalStorage and User/workspaceStorage = existing IDE state by default

Customer ChatGPT browser profile
  cookies/local storage/OAuth = customer account

Customer Codex desktop, if present
  effective CODEX_HOME + provider + login = customer's account
  must not inherit the vendor API profile or forced API-only settings

Extension installation/update directory
  extension code only; no long-lived credential
```

Default Windows root:
`%LOCALAPPDATA%\\YourProduct\\codex-profiles\\<profile-id>\\.codex`

Override it with `ALT_CODEX_PROFILE_ROOT`. On Linux/macOS use:
`${XDG_STATE_HOME:-$HOME/.local/state}/your-product/codex-profiles/<profile-id>/.codex`.

Pass `CODEX_HOME` to the Antigravity process and its local extension rather than setting it globally. The preferred mode preserves the existing Antigravity user-data directory and only changes `CODEX_HOME`. Do not claim this alone isolates IDE extension storage, browser cookies, remote extension hosts, or cloud sessions. A separate Antigravity `--user-data-dir` remains an optional fallback if necessary for verified identity isolation and the customer accepts its consequences.

## Preferred CODEX_HOME-Only Workflow

1. Identify the customer-facing ChatGPT/Codex desktop identity and provider, the Antigravity executable, and the actual local or remote extension host. Inspect without exposing keys. A desktop `config.toml` already using the vendor router remains a separate problem; a new extension home does not fix desktop authentication or provider selection.
2. Reuse an existing working dedicated `CODEX_HOME` if verified. Otherwise create a new directory such as `C:\codex-antigravity` or `~/codex-antigravity`, distinct from the customer's home and not inside an extension installation. Do not overwrite a nonempty or unknown profile. A new home has a separate, potentially empty local Codex session index; old history remains untouched and is not automatically copied or merged.
3. Add only the reviewed provider/model/base URL configuration and the provider's `env_key` variable name if required. Do not assume entering a key into `auth.json` satisfies `env_key`. Supply the actual credential through an approved process-scoped secure mechanism; never print it, put it in the shortcut or command line, copy the customer's `auth.json`, or silently alter the customer's login. Verify the credential will be available after a normal shortcut launch.
4. Explain that the user should save work and close all Antigravity instances normally before reusing its existing IDE data, because an already-running instance may reuse its old environment. Never force-close the application or discard unsaved work. If this conversation runs inside Antigravity, prepare the steps first; closing it can interrupt the conversation. Do not promise fully automatic completion if restarting is required.
5. Start the installed Antigravity executable with the dedicated `CODEX_HOME` only for its process, without changing system/user environment variables or the customer's ChatGPT shortcut. Use the Windows helper below, which also removes inherited `ELECTRON_RUN_AS_NODE` for the child. Do not create a separate IDE user-data directory just to change history.
6. Verify the actual local extension process uses the intended `CODEX_HOME`, its provider is the vendor API, and a minimal request succeeds. Verify the desktop uses the customer's intended account and provider, not the vendor router. If the extension host is remote (SSH/WSL/container), local inheritance is not proof: inspect and configure the remote host separately with user approval, or stop and report it unverified. Do not assume a PID or an open window proves authentication.
7. Only after both surfaces work, optionally update an existing Antigravity shortcut in place using the helper below, after reviewing and preserving its arguments. Back it up first; do not create a replacement if missing or touch the customer's ChatGPT shortcut. Reopen via that shortcut after a clean exit, verify the actual provider and credential again, and restore the shortcut backup if the test fails. Do not promise that a key inherited in an interactive shell will be inherited from Explorer.

The direct Windows launcher refuses to start while any Antigravity instance is still running. This prevents it from silently handing off to a process with the old environment; it does not focus an already-open window. Ask the user to save and close normally before relaunching, and do not install this shortcut behavior without explaining that limitation. In shortcut mode the helper runs hidden, so diagnose a failed launch from an interactive PowerShell rather than assuming the app started.

Windows examples using an already prepared directory and the actual installed executable:

```powershell
powershell.exe -File .\scripts\launch_antigravity_isolated.ps1 `
  -CodexHome "C:\codex-antigravity" `
  -AntigravityPath "C:\Path\To\Antigravity IDE.exe"

# Only after successful validation and with the existing shortcut identified:
powershell.exe -File .\scripts\update_existing_shortcut.ps1 `
  -CodexHome "C:\codex-antigravity" `
  -ExistingShortcutPath "$env:USERPROFILE\Desktop\Antigravity IDE.lnk" `
  -AntigravityPath "C:\Path\To\Antigravity IDE.exe"
```

On macOS and Linux, close the existing IDE first and invoke the installed app executable directly from a shell with a process-scoped environment. `open -a` is macOS-only, and Launch Services may not propagate the shell environment; do not assume it works without verifying the extension's actual home. Replace the executable with the observed installed path:

```bash
# macOS: verify the actual .app location and executable name first.
env -u ELECTRON_RUN_AS_NODE CODEX_HOME="$HOME/codex-antigravity" "/Applications/Antigravity.app/Contents/MacOS/Antigravity"

# Linux: use the verified installed executable or command.
env -u ELECTRON_RUN_AS_NODE CODEX_HOME="$HOME/codex-antigravity" antigravity
```

These examples do not configure credentials or assert a particular executable path. Preserve all existing workspace state and settings; when the same IDE user-data directory is reused, cached extension sign-in may persist and must be checked.

When launched from an Electron-hosted extension, `ELECTRON_RUN_AS_NODE` may be inherited and prevent the IDE from starting. The launcher temporarily removes it while starting Antigravity and restores the launcher's own environment afterward. It does not change User/Machine environment settings or guarantee that a provider's `env_key` is available in a later shortcut launch. Verify the actual extension process and API request before updating a shortcut; if authentication is absent, stop and configure an approved secure credential source rather than copying or exposing a key.

For the optional separate-IDE-profile fallback, after verifying both identities and API access, update the existing Antigravity shortcut in place:

```powershell
powershell.exe -File .\scripts\update_existing_shortcut.ps1 `
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
env_key = "NAME_OF_PROVIDER_KEY_VARIABLE"
```

Use only a `base_url` and provider supplied by the user or already present in active configuration. Do not replace a production endpoint by assumption.

`forced_login_method = "api"` restricts Codex to API authentication in supported versions. A mismatched active login may be logged out, so verify the effective `CODEX_HOME` and credential store are the dedicated profile before launch. If the installed build does not support the setting, stop and report it; do not delete `auth.json` or replace the customer's credential.

For `env_key`, configure the variable name, never the credential value. `auth.json` is not a substitute for an `env_key` provider. Verify the credential is available to the actual extension after launch and again when starting from the existing shortcut. If a securely supplied credential cannot survive that launch, stop and explain; do not assume an interactive test will persist. This skill's profile helper only supports `env_key` provisioning; other provider auth modes require separate verification and must not be guessed.

## Customer Already Has ChatGPT

1. Identify whether the customer uses ChatGPT browser/app, Codex desktop, or both. Keep existing customer shortcuts, accounts, app data and history unchanged. Check the desktop's effective provider as well as its login.
2. Prefer a dedicated `CODEX_HOME` while preserving the existing Antigravity `UserDataDir`. A separate IDE user-data directory is a fallback only when needed and approved.
3. Start Codex with its own `CODEX_HOME` and `forced_login_method = "api"`; do not sign the customer's ChatGPT account into that Codex instance.
4. Update the existing Antigravity shortcut in place only after both identities and the isolated API request are verified. Do not create a replacement ChatGPT shortcut. Verify the result after a cold shortcut launch and restore the shortcut backup on failure.
5. If actual identity separation cannot be verified with `CODEX_HOME` alone, stop and discuss a separate application profile or OS user; do not claim success.
6. After an extension update, restart through the same launcher and verify both identities and provider paths again. Check history separation only if requested.

If ChatGPT still shows the vendor account, inspect browser profile/cookies first. An API key is not a ChatGPT cookie. Do not delete customer browser data.

## Existing Two-Platform Migration

Use this optional fallback when the preferred `CODEX_HOME`-only mode does not isolate identities and the user explicitly accepts a new Antigravity IDE user-data directory.

1. Identify the actual customer ChatGPT data directory, old Antigravity `UserDataDir`, and target Codex `UserDataDir`; verify they are distinct and not aliases/junctions of one another. Keep Antigravity open when creating an empty profile; copying reviewed settings requires closing the source first.
2. Do not delete, sign out of, or overwrite the customer ChatGPT browser profile.
3. Do not replace the old `.codex` directory. Create a timestamped backup of `config.toml` only; never copy its `auth.json` into the new profile.
4. Create a new persistent Codex profile for the vendor API identity.
5. Create a separate Antigravity `UserDataDir` using `scripts/isolate_antigravity_profile.ps1`. By default copy no settings. Only after reviewing settings, keybindings and snippets for secrets and profile/environment overrides may they be copied; never copy local history, extension state or browser sessions.
6. Run Antigravity through `scripts/launch_antigravity_isolated.ps1` with the new `CODEX_HOME` and `UserDataDir`.
7. Verify the customer desktop is actually on the customer's account/provider and the isolated extension successfully uses the vendor API. Only then update the existing Antigravity shortcut; do not change the customer shortcut.
8. After a cold shortcut launch, test both identities and API access again. Test local Recents/Folders only when requested. Do not claim extension-update behavior was verified without a real update.

Use the migration helper:

```powershell
powershell.exe -File .\scripts\repair_existing_platforms.ps1 `
  -ProfileId customer-001 `
  -ExistingCodexHome "$env:USERPROFILE\.codex" `
  -CustomerChatGPTDataDir "C:\Path\To\Customer\ChatGPT\Profile" `
  -ExistingAntigravityUserDataDir "$env:APPDATA\Antigravity IDE" `
  -AntigravityUserDataDir "$env:LOCALAPPDATA\Antigravity-Codex\browser\customer-001" `
  -BaseUrl https://codex.anhlaptrinh.vn/v1 `
  -ProviderEnvKey NAME_OF_PROVIDER_KEY_VARIABLE `
  -SourceSkillPath "$HOME\.codex\skills\cau-hinh-alt-codex"
```

The helper backs up the old Codex `config.toml`, leaves the old Antigravity and ChatGPT profiles untouched, creates a fresh Antigravity state, and writes non-secret manifests. It never copies `state.vscdb`, `storage.json`, workspace state, ChatGPT cookies, `auth.json`, API keys, or OAuth tokens. If the target already contains data, it stops; choose a new empty target. To preserve settings/keybindings/snippets, review those files without exposing secrets and add `-CopyReviewedAntigravitySettings` only if they contain no credentials or overrides that would reconnect the old profile.

## Recents And Folders Isolation

Do not use this section for the account-separation task. Preserve existing histories and lists; do not split, migrate, clear, or hide them. A distinct `CODEX_HOME` or IDE profile can have an initially empty local list even though the old data still exists. Only consider this separate workflow if the customer later explicitly asks to isolate history and understands that consequence.

On the observed Windows Antigravity build, `User/globalStorage/state.vscdb` contains `history.recentlyOpenedPathsList` and `openai.chatgpt`; other state may exist in `storage.json`, `workspaceStorage`, `CODEX_HOME`, or a service account. File names and keys can change between versions, so treat these as diagnostic clues, not a complete schema. Never edit the database in place.

For an existing profile, `scripts/isolate_antigravity_profile.ps1` prepares a new target without copying those state stores. The installed extension code normally remains in the existing extension installation directory, but profile-specific extension state, workspace history and some settings may need reconfiguration. The old mixed data remains in the source or backup; the helper cannot determine which historical entry belongs to which identity and does not automatically restore or divide it. Confirm the customer accepts this before switching the existing shortcut. Reopen desired folders manually in the appropriate instance.

When identity/API isolation already works, the actual `CODEX_HOME` paths are confirmed distinct, and only Recents/Folders are mixed, do not run full provisioning or rewrite `CODEX_HOME/config.toml`. Preserve the existing `ProfileId`, `ProfileRoot`, credential and ChatGPT shortcut. If the user has requested the switch and accepts the fresh empty IDE state, do the work directly; do not require a separate confirmation or ask them to close the IDE just to create a fresh profile. Verify the current paths and a distinct empty target, then prepare the target with `scripts/isolate_antigravity_profile.ps1` without `-CopyReviewedSettings` while the old window stays open. Launch the isolated instance with `scripts/launch_antigravity_isolated.ps1` using the existing Codex profile and the new target. Do not close, restart, or force-terminate the old window; it may host this conversation and unsaved work.

Verify a running Antigravity process actually uses the target `--user-data-dir` and that the intended Codex profile and API authentication work. If launch is redirected to the old instance, the build refuses multiple profiles, or either profile cannot be verified, stop and report that a safe restart or additional user action is needed; do not report success or change the shortcut. Once the new instance is verified, update the existing Antigravity shortcut using the same `ProfileId`/`ProfileRoot` and new target, subject to the shortcut argument safety checks. If its original arguments cannot be preserved without review, stop and explain rather than silently replacing them. Tell the user the old window remains open and can be closed after saving when convenient; the new window starts with empty local Recents/Folders and may require its own settings or login. Do not claim the current conversation will transfer automatically. Never transfer keys or account data automatically.

The following commands illustrate the preparation and shortcut update; launch and verify the isolated instance between them:

```powershell
powershell.exe -File .\scripts\isolate_antigravity_profile.ps1 `
  -ProfileId customer-001 `
  -SourceUserDataDir "C:\Path\To\Current\Antigravity\UserData" `
  -TargetUserDataDir "$env:LOCALAPPDATA\Antigravity-Codex\browser\customer-001-fresh"

powershell.exe -File .\scripts\launch_antigravity_isolated.ps1 `
  -ProfileId customer-001 `
  -ProfileRoot "C:\Path\To\Existing\Codex\ProfileRoot" `
  -AntigravityPath "C:\Path\To\Antigravity.exe" `
  -UserDataDir "$env:LOCALAPPDATA\Antigravity-Codex\browser\customer-001-fresh"

# Verify the actual process path, Codex profile, and API authentication before continuing.
powershell.exe -File .\scripts\update_existing_shortcut.ps1 `
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
powershell.exe -File .\\scripts\\install_skill_into_profile.ps1 `
  -SourceSkillPath "$HOME\\.codex\\skills\\cau-hinh-alt-codex" `
  -CodexHome "$env:LOCALAPPDATA\\Antigravity-Codex\\profiles\\customer-001\\.codex"
```

The installer backs up an existing skill directory and excludes `auth.json`, `.env`, PEM files, and key files. This keeps the skill available after extension updates without distributing credentials.

## Provision a Profile

Use:

```powershell
powershell.exe -File .\\scripts\\prepare_isolated_profile.ps1 `
  -ProfileId customer-001 `
  -Model GPT-5.6-sol `
  -BaseUrl https://codex.anhlaptrinh.vn/v1 `
  -ProviderEnvKey NAME_OF_PROVIDER_KEY_VARIABLE

```

The script creates a new isolated configuration and refuses to overwrite an existing one, use the default customer `CODEX_HOME`, set a file-based key, or change a shortcut. It accepts only the credential variable's name, not its value. Existing working profiles must be preserved. Update a shortcut separately only after both identities and the API have been verified.

## Upstream Model Workflow

Keep the upstream model mapping:

- `gpt-5.4`
- `gpt-5.5`
- `GPT-5.6`
- `GPT-5.6-sol`
- `GPT-5.6-terra`
- `GPT-5.6-luna`

Use `scripts/launch_antigravity_isolated.ps1` with the verified direct `-CodexHome` mode for the preferred restart workflow, or its existing `-ProfileId` mode for the separate-IDE fallback. Use `scripts/set_alt_model.sh` for Codex/OpenClaw shell workflows. It must back up before editing, change only the requested model, validate configuration, and restart the gateway only when requested. Never use it to copy credentials.

Resolve `CODEX_HOME/config.toml` from the active profile; do not fall back to the default `.codex` when the extension is launched with an isolated profile.

## Validation After Install or Update

Report completion only after checking:

- Codex receives the persistent `CODEX_HOME`.
- `config.toml` has the expected provider/model and `forced_login_method = "api"`.
- Credential state is reported as set/missing without printing its value.
- The customer-facing ChatGPT or Codex desktop shows the customer's account and uses the intended customer provider, not the vendor router.
- When the separate-IDE fallback was chosen, verify its actual `--user-data-dir`; in preferred mode confirm the existing IDE data was preserved and do not require a separate IDE directory.
- Existing customer history and folders remain intact. Only if history separation was requested, test for cross-visibility without exposing private names.
- The Codex instance starts without copied `openai.chatgpt` or workspace state, uses API authentication, and does not silently reconnect the customer's ChatGPT session.
- Starting Antigravity afresh from the updated shortcut preserves API authentication and both identities. The launcher inheriting a key in an interactive test does not prove the shortcut will inherit it.
- Updating/reinstalling the extension does not remove profile data.
- No API key, cookie, `auth.json`, or token appears in logs or reports.

If either identity, actual process paths, API authentication, or extension-update behavior cannot be checked, report it as unverified. Report history behavior separately if requested. A fresh local state alone is not proof of cloud separation or feature parity.

## Handoff Safety

- Do not package the vendor API key in an extension distributed to customers. Prefer a backend/service account or customer-specific key with limits and revocation.
- Never commit `auth.json`, `.env`, tokens, cookies, or credential backups.
- Never delete old profiles/configuration automatically. Back up and create a new profile; let the user decide when to revoke old credentials.
- If a repository or skill directory contains a real credential, do not read it; isolate it and report that the key must be rotated/revoked.
