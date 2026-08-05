---
name: khu-token-api-secret
description: Scan and sanitize API keys, tokens, secrets, cookies, browser profiles, real emails, and private local data before Codex creates, updates, reviews, commits, or prepares any skill/project for GitHub. Use whenever creating a new Codex skill, updating an existing skill, standardizing a skill, preparing code for GitHub, resolving GitHub secret scanning, or checking whether files should be replaced with placeholders such as Nhap_API_Cua_Ban.
---

# Khu Token API Secret

## Rule

Always run this skill before saying a skill/project is ready for GitHub. Do not wait for the user to ask again.

Use placeholders:
- API key, bot token, auth token, access token, refresh token, secret: `Nhap_API_Cua_Ban`
- Personal email in examples or logs: `email_cua_ban@example.com`
- Password sample: `Nhap_Mat_Khau_Cua_Ban`
- Private IDs, admin URLs, account names, or values that should not be public: `Nhap_Gia_Tri_Cua_Ban`

## Workflow

1. Inspect the repo or skill folder.
2. Add or update `.gitignore` for local/private files.
3. Scan text/config/code files for common secret patterns.
4. Replace real values with placeholders.
5. Remove tracked private generated files from Git index with `git rm --cached`, keeping local files intact.
6. Re-scan staged/current tree.
7. If the repo has existing commits, check whether secrets remain in Git history and warn the user before push.

## Files To Ignore

Ensure `.gitignore` blocks:

```gitignore
.env
.env.*
!.env.example
credentials.json
client_secret*.json
*token*
*secret*
*credential*
**/zalo-chrome-profile/
**/chrome-profile/
**/user-data-dir/
**/__pycache__/
*.pyc
*.pyo
venv/
*.log
```

Also remove browser/session data from Git index if tracked:
- `Cookies`
- `Login Data`
- `Local Storage`
- `IndexedDB`
- `Session Storage`
- `Secure Preferences`
- `Preferences`
- `Web Data`
- Chrome or Zalo profile folders

Use:

```powershell
git rm --cached -r -- path/to/private-file-or-folder
```

Never delete the user's local file unless explicitly requested.

## Fast Commands

Scan current files:

```powershell
python khu-token-api-secret/scripts/secret_sanitizer.py --path . --scan
```

Replace common secrets in text files:

```powershell
python khu-token-api-secret/scripts/secret_sanitizer.py --path . --fix
```

Check tracked private files:

```powershell
git ls-files | rg -i "zalo-chrome-profile|chrome-profile|user-data-dir|cookies|login data|local storage|indexeddb|session storage|secure preferences|web data|__pycache__|\.pyc$|\.env$|client_secret|credentials\.json"
```

Check history before pushing an existing repo:

```powershell
git grep -n -E "(sk-proj-[A-Za-z0-9_-]+|sk-[A-Za-z0-9_-]{20,}|AIza[0-9A-Za-z_-]{25,}|gh[pousr]_[0-9A-Za-z_]{20,}|github_pat_[A-Za-z0-9_]+|xox[baprs]-[0-9A-Za-z-]{10,}|[0-9]{7,}:[A-Za-z0-9_-]{25,})" $(git rev-list --all)
```

## Required Final Check

Before final response, confirm:
- No common secret patterns remain in current/staged text files.
- Sensitive browser/profile/log/cache files are ignored or removed from Git index.
- JSON/YAML files touched by sanitization still parse if relevant.
- The user is warned if Git history still contains a secret.
