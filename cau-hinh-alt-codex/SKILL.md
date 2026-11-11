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
- Codex desktop may sign in separately with the customer's ChatGPT account; browser ChatGPT remains untouched.
- Antigravity/extension updates do not delete the profile configuration or credential.
- Every customer has a distinct `profile_id` and `CODEX_HOME`.
- Never write a real API key to this skill, a repository, logs, a response, or a command line.

## Mandatory Rules

1. Do not use `%USERPROFILE%\\.codex` or `$HOME/.codex` for customer-distributed workflows when a dedicated profile can be created.
2. Never copy `auth.json` from the skill, upstream repository, or another machine. When the user authorizes reuse of an existing API key on this same machine, extract only `OPENAI_API_KEY` from an explicitly selected local Codex home; never transfer OAuth tokens, cookies, or the entire source file.
3. Never change the customer's ChatGPT browser cookies, local storage, session, or browser profile. Only sign out of Codex desktop or replace its authentication when explicitly requested; do not sign out a working ChatGPT identity merely to isolate the extension.
4. Do not put the API key in User/System environment variables unless required. Pass `CODEX_HOME` and credential only to the Codex process that needs them.
5. Never modify the installed extension directory to persist configuration. Updates overwrite it. Use a launcher/profile root outside that directory.
6. Before writing, resolve and show the destination, reject `profile_id` containing `..`, separators, or control characters, and back up existing files.
7. If the user only asks to update this skill, edit and validate the skill only. Do not create profiles, write credentials, or restart Antigravity.
8. Reuse the customer's original Antigravity shortcuts; never create an additional shortcut for this workflow. Back up each shortcut before modifying it in place. Preserve the original Antigravity icon, working directory, relevant arguments, and existing user data. If a shortcut targets PowerShell or a launcher, explicitly set its icon to the installed Antigravity executable so Start search does not show the launcher icon. Start the installed application independently of the terminal without exposing credentials.

## Isolation Architecture

```text
Antigravity/Codex process
  CODEX_HOME = <persistent-root>\\<profile-id>\\.codex
  config.toml = API provider + model + forced API auth
  auth.json  = profile credential only if this build needs a file auth store

Customer ChatGPT browser profile
  cookies/local storage/OAuth = customer account

Codex desktop
  CODEX_HOME = its existing independent profile
  authentication = customer's ChatGPT login when requested

Extension installation/update directory
  extension code only; no long-lived credential
```

Default Windows root:
`%LOCALAPPDATA%\\YourProduct\\codex-profiles\\<profile-id>\\.codex`

Override it with `ALT_CODEX_PROFILE_ROOT`. On Linux/macOS use:
`${XDG_STATE_HOME:-$HOME/.local/state}/your-product/codex-profiles/<profile-id>/.codex`.

Pass `CODEX_HOME` to the Codex process rather than setting it globally when possible. On Windows, restart through `scripts/launch_antigravity_isolated.ps1`; on macOS/Linux use `scripts/launch_antigravity_isolated.sh`. Both use the persistent profile after an extension update.

For macOS/Linux provisioning, credentials, launch integration, and validation, follow [macOS and Linux](references/macos-linux.md). The Unix helpers do not change desktop/browser credentials, globally exported variables, shortcuts, or running processes.

## Codex Configuration

Preserve unrelated keys in `CODEX_HOME/config.toml` and use a shape like this:

```toml
model_provider = "router"
model = "GPT-5.6-sol"
forced_login_method = "api"
cli_auth_credentials_store = "file"

[model_providers.router]
name = "router"
base_url = "https://codex.anhlaptrinh.vn/v1"
wire_api = "responses"
```

Use only a `base_url` and provider supplied by the user or already present in active configuration. Do not replace a production endpoint by assumption.

Choose the exact model supplied by the user or provider, preserving the active model if no change was requested. The example model is illustrative only. Do not infer available models from a hard-coded list. The provisioning helper accepts `-EnvKey ALT_KEY` only to reference an existing environment variable by name; it neither creates nor prints a credential. Keep an existing `env_key` when required by the provider, and note that it may take precedence over file authentication. Do not add undocumented configuration keys such as `preferred_auth_method`. Check compatibility with the installed Codex build.

`forced_login_method = "api"` prevents Codex from falling back to ChatGPT login for this profile. If the installed Codex version does not support it, stop and report it; do not delete `auth.json` or replace the customer's credential.

With `cli_auth_credentials_store = "file"`, auth data must be inside the profile's `CODEX_HOME`, never next to `SKILL.md`. Use `ephemeral` only if the installed build supports it and the user wants no file credential.

## Customer Already Has ChatGPT

1. Do not use a browser profile containing the vendor ChatGPT account. Preserve the customer's existing sessions and user-data directory when safe.
2. Start Antigravity's Codex extension with its own `CODEX_HOME` and `forced_login_method = "api"`; keep the customer's ChatGPT or Codex desktop authentication separate.
3. `CODEX_HOME` does not isolate browser cookies. If browser session isolation is required, use a separate user-data directory when supported, or a separate Windows user or application instance; disclose the tradeoff before changing user data.
4. After an extension update, restart through the same launcher. Do not sign in through ChatGPT when the target is API auth.

If ChatGPT still shows the vendor account, inspect browser profile/cookies first. An API key is not a ChatGPT cookie. Do not delete customer browser data.

## Existing Two-Platform Migration

Use this mode when the customer already has both ChatGPT and Antigravity/Codex, and accounts are mixed or the first install used the wrong profile.

1. Close ChatGPT, Antigravity, and the Codex extension before changing the runtime.
2. Do not delete, sign out of, or overwrite the customer ChatGPT browser profile.
3. Do not replace the old `.codex` directory. Back up `config.toml` only. When the user authorizes API key reuse for the same provider and endpoint, use `-ReuseExistingApiKey` to transfer only an API key from the explicitly selected local home, not the whole `auth.json` or a ChatGPT login.
4. Create a new persistent Codex profile for the vendor API identity.
5. Preserve the existing Antigravity user-data directory when the user wants its settings and projects retained. Use a separate `UserDataDir` only when browser/session isolation is actually needed or requested. Never copy browser cookies/local storage between platforms.
6. Run Antigravity through the platform's isolated launcher with the new `CODEX_HOME`. Back up and update the existing shortcut in place to call the launcher; do not create another shortcut. Check pinned shortcuts and alternate launch paths separately, and report any that still bypass the launcher; do not assume changing one shortcut changes the others.
7. Fully close existing Antigravity processes before reopening: an existing single-instance process can take over the launch without inheriting the new `CODEX_HOME`. Do not force-close an editor with unsaved work; ask the user to close it. Test both identities after restart and, if feasible, after an extension update.

### Codex desktop and Antigravity

For a request to use a ChatGPT account in Codex desktop and an API key in Antigravity, inspect the desktop's actual `CODEX_HOME` and provider separately from Antigravity's. Do not assume a browser profile determines Codex desktop authentication. Back up configuration, preserve unrelated settings, and, only if explicitly requested, sign out the desktop API identity using the installed Codex logout mechanism. Switch its provider back to the normal OpenAI provider and remove incompatible custom model overrides only when necessary; use `forced_login_method = "chatgpt"` only if the installed build supports it. Ask the user to complete their own interactive ChatGPT sign-in. Preserve the old credential securely if it must be backed up; never print or copy OAuth credentials into the API profile. Restart the desktop to clear cached state, then verify the displayed identity. Do not change the customer's browser session.

On Windows, use the migration helper:

```powershell
pwsh -File .\\scripts\\repair_existing_platforms.ps1 `
  -ProfileId customer-001 `
  -ExistingCodexHome "$env:USERPROFILE\\.codex" `
  -Model GPT-5.6-sol `
  -CustomerChatGPTDataDir "C:\\Path\\To\\Customer\\ChatGPT\\Profile" `
  -BaseUrl https://codex.anhlaptrinh.vn/v1 `
  -ReuseExistingApiKey `
  -SourceSkillPath "$HOME\\.codex\\skills\\cau-hinh-alt-codex"
```

The helper backs up the old `config.toml`, creates the profile and writes a non-secret manifest. It creates an Antigravity user-data directory only when `-AntigravityUserDataDir` is explicitly supplied. With `-ReuseExistingApiKey`, it creates a destination `auth.json` containing only the existing local API key. It rejects OAuth/token sources and never overwrites existing destination authentication; check `AuthStatus` rather than assuming the credential is usable. Without the switch it does not transfer a key. Never copy ChatGPT cookies or OAuth tokens.

### Windows shortcut without a terminal

For an environment-backed API provider, `scripts/antigravity_gui_launcher.cs` can be compiled as a Windows GUI executable outside the extension and skill directories. Use it only when the configured `env_key` already exists in the launch environment or the current Windows user's environment; do not create a global variable or write its value to the launcher, config, logs, or shortcut. Verify the actual application path, isolated profile, and variable name first. Place `AntigravityLauncher.config` beside the compiled executable as three UTF-8 lines: the installed application path, the isolated `CODEX_HOME`, and the environment variable name. Never put the key itself in the file.

Compile with PowerShell `Add-Type -Path <source.cs> -OutputAssembly <launcher.exe> -OutputType WindowsApplication -ReferencedAssemblies 'System.dll','System.Windows.Forms.dll'`. Back up existing launcher files and the customer's original Desktop and Start Menu shortcuts before editing. Retarget each existing shortcut to this executable and set the shortcut icon to the original Antigravity executable; preserve working directory and applicable original arguments. Do not create extra shortcuts. The launcher passes the profile and existing key only to the child, removes `ELECTRON_RUN_AS_NODE`, and requests both detached console and job breakaway. If breakaway is prohibited, report the Windows error instead of claiming independence.

`DETACHED_PROCESS` alone does not break inheritance of a terminal job. Verify the actual application survives closing the launching terminal and that its Codex extension receives the expected profile; a test process surviving only its immediate PowerShell parent is insufficient. Preserve the active editor and ask the user to close it before retesting if a single-instance process could take over. Test taskbar pins, Windows Search and file associations separately; never assume they use a modified shortcut. If an alternate path bypasses the launcher, report it rather than changing global `CODEX_HOME` or touching ChatGPT authentication.

## Install the Skill Into a Persistent Profile

Maintain one authoritative, sanitized skill directory per machine, outside the Antigravity extension directory. If a separate `CODEX_HOME` needs to discover that same skill, link its `skills/cau-hinh-alt-codex` directory to the authoritative directory when the OS and skill discovery support it; do not maintain a second live copy. Back up any existing profile skill before replacing it with a link, verify the link target, and never follow it recursively when deleting or updating. If linking or discovery does not work, report the limitation rather than silently creating divergent copies. On a different customer machine, install one sanitized copy there; never distribute credentials.

## Provision a Profile

On Windows, use:

```powershell
pwsh -File .\\scripts\\prepare_isolated_profile.ps1 `
  -ProfileId customer-001 `
  -Model GPT-5.6-sol `
  -BaseUrl https://codex.anhlaptrinh.vn/v1 `
  -SourceCodexHome "$env:USERPROFILE\\.codex"
```

The script creates the persistent directory and new isolated configuration; it refuses to replace an existing `config.toml`. Use `-SourceCodexHome` only when the user has authorized reuse of that local API key and confirmed it belongs to the target provider and endpoint. The script extracts only `OPENAI_API_KEY`, rejects OAuth/token sources, and never overwrites existing destination authentication. If no reusable file key exists, use `-SetApiKey` for secure local entry or an appropriate OS credential store; report the limitation instead of extracting browser or extension secrets. Never accept a key in chat or as a command-line argument. Check `AuthStatus`; `existing_not_verified` does not prove a working key. An `env_key` setting can override file-based authentication, so check the actual active provider configuration and process environment without exposing values.

## Upstream Model Workflow

Use the exact model ID requested or already configured. Legacy aliases are normalized by the shell helper; other valid IDs are passed through unchanged. For OpenClaw, the requested model must already be registered for its provider; do not invent model metadata. With `--all-agents`, only overrides matching the previous default are changed.

Use the appropriate platform launcher for every Antigravity restart/update, and use `scripts/set_alt_model.sh` for Codex/OpenClaw shell workflows. It must back up before editing, change only the requested model, validate configuration, and restart the gateway only when requested. Never use it to copy credentials.

Resolve `CODEX_HOME/config.toml` from the active profile; do not fall back to the default `.codex` when the extension is launched with an isolated profile.

## Validation After Install or Update

Report completion only after checking:

- Codex receives the persistent `CODEX_HOME`.
- `config.toml` has the expected provider/model and `forced_login_method = "api"`.
- Credential state is reported as set/missing without printing its value.
- When requested, Codex desktop shows the customer's ChatGPT identity; browser ChatGPT remains unchanged.
- The original shortcuts and Windows Search retain the Antigravity icon and launch the isolated profile; the application remains open after its launching terminal closes. Test each pinned or alternate entry point separately.
- Restarting Antigravity preserves both identities.
- Updating/reinstalling the extension does not remove profile data.
- No API key, cookie, `auth.json`, or token appears in logs or reports.

An environment-backed provider can work even when `codex login status` says not logged in. Check the variable's presence without exposing its value and, if appropriate, make a minimal authorized API request. If identity, restart, update persistence, or the launched process environment cannot be checked, report the exact limitation rather than claiming full isolation.

## Handoff Safety

- Do not package the vendor API key in an extension distributed to customers. Prefer a backend/service account or customer-specific key with limits and revocation.
- Never commit `auth.json`, `.env`, tokens, cookies, or credential backups.
- Never delete old profiles/configuration automatically. Back up and create a new profile; let the user decide when to revoke old credentials.
- If a repository or skill directory contains a real credential, do not read it; isolate it and report that the key must be rotated/revoked.
