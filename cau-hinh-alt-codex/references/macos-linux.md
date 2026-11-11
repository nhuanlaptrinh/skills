# macOS and Linux

Use this workflow when the user asks for a Unix setup or migration. It requires Bash, Python 3.8+, and an installed Codex/Antigravity executable. Paths and commands below are examples: obtain the exact model, provider URL, application executable, and existing skill location from the user or active configuration. Do not assume the same model or endpoint works on another machine.

## Create an isolated API profile

Do not copy an `auth.json`, OAuth tokens, browser data, or a key from another machine. If a local API key is to be reused, obtain the user's explicit authorization and confirm its provider and endpoint first. The Unix provisioning script does not transfer any credentials.

Set `SKILL_DIR` to this skill's actual absolute path, and use the exact requested model and endpoint in place of the placeholders:

```bash
SKILL_DIR="/absolute/path/to/cau-hinh-alt-codex"
PROFILE_ROOT="${ALT_CODEX_PROFILE_ROOT:-${XDG_STATE_HOME:-$HOME/.local/state}/your-product/codex-profiles}"
PROFILE_HOME="$PROFILE_ROOT/customer-001/.codex"
python3 "$SKILL_DIR/scripts/prepare_isolated_profile.py" \
  --profile-id customer-001 --profile-root "$PROFILE_ROOT" \
  --model MODEL_FROM_USER --base-url https://provider.example/v1
```

The helper prints the destination before writing, creates a private configuration, refuses to overwrite an existing config, and does not configure an API key. It accepts `--provider` and `--env-key NAME` when needed. `--env-key` is the variable's name, never its value; it only references an existing credential and does not verify the key. If using an existing exported environment variable, ensure it is inherited by the actual launched process. Do not persist new keys globally just to launch the app.

If the user authorizes entering a new local API key and the installed CLI supports this method, read it privately in a Bash subshell and pass it to the isolated CLI via standard input. The profile uses file-based authentication; the resulting credential is local to this profile. Do not enter a key in chat or put it in shell history, process arguments, or logs:

```bash
( umask 077
  read -r -s -p 'API key: ' profile_key
  printf '\n' >&2
  printf '%s' "$profile_key" | CODEX_HOME="$PROFILE_HOME" codex login --with-api-key
  unset profile_key
)
```

Alternatively use the provider's existing secure credential mechanism. Confirm `forced_login_method = "api"` is supported by the installed build. A valid `env_key` can work even if `codex login status` says not logged in. Check variable presence without revealing its value and use a minimal request only when appropriate; report actual verification limits.

To make this skill available inside the isolated profile, optionally install a sanitized copy:

```bash
python3 "$SKILL_DIR/scripts/install_skill_into_profile.py" \
  --source-skill "$SKILL_DIR" --codex-home "$PROFILE_HOME"
```

The installer refuses to overwrite an existing destination and skips symbolic links and common credential files; inspect the source for other secrets before distributing it.

## Launch without changing the existing desktop account

Identify the actual executable. On Linux it may be a binary or application launcher; on macOS pass the actual executable inside the application bundle (`.../Antigravity.app/Contents/MacOS/<executable>`), not the `.app` directory. Verify the path and how that build handles `--user-data-dir` rather than assuming. Launch it with:

```bash
bash "$SKILL_DIR/scripts/launch_antigravity_isolated.sh" \
  --profile-id customer-001 --profile-root "$PROFILE_ROOT" \
  --app "/absolute/path/to/Antigravity executable"
```

The launcher sets `CODEX_HOME` only for the child, clears `ELECTRON_RUN_AS_NODE`, and retains existing application data by default. If browser partition isolation is needed and supported by that build, pass an absolute `--user-data-dir` path; never copy browser cookies or local storage. Close existing Antigravity instances first, because a running single-instance process may take over a new launch without inheriting its environment. Ask the user to close unsaved work rather than killing processes.

If the user wants to retain an existing Dock, desktop, or application-menu entry, identify what it actually launches and back it up before modifying it. Use an OS-appropriate launcher that reliably invokes the isolated script with the correct environment and preserves existing arguments. Do not assume editing one entry changes pinned Dock icons, Finder launches, Linux `.desktop` files, or other launch paths. Do not create or replace shortcuts without user authorization. Verify the actual new process or extension receives the expected profile; report unverified paths.

Codex desktop ChatGPT authentication is separate from browser data and must use its own `CODEX_HOME`. Only sign out of or reconfigure the existing desktop identity when explicitly requested; back up settings, leave browser sessions untouched, and let the user complete interactive login. Test both identities and extension-update persistence only when safe and available; do not report those checks as passed without observing them.
