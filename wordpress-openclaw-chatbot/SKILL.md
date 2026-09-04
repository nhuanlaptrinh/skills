---
name: wordpress-openclaw-chatbot
description: Deploy, configure, reposition, verify, update, and roll back a secure OpenClaw-backed chatbot plugin on remote WordPress sites and separate VPSs. Use when installing a site chatbot through WordPress Admin or WP-CLI, connecting a site to a shared HTTPS relay and private OpenClaw Bridge, storing relay credentials server-side, stacking the widget with existing chat/contact buttons, purging WordPress caches, or checking the public result without exposing secrets.
---

# WordPress OpenClaw Chatbot

Use this skill to repeat the small, safe deployment pattern used by the
Eyelashes VN integration on another WordPress site or VPS. Keep the WordPress
installation and the AI runtime separate:

```text
visitor browser
  -> WordPress plugin (same-origin AJAX)
  -> HTTPS relay for one site/project
  -> private OpenClaw AI Bridge
  -> one restricted website agent
```

The browser must never receive an OpenClaw gateway token, provider key, or
relay bearer token. The public route must not accept a caller-selected project,
agent, model, or raw message list.

## Apply the right scope

- **Existing relay:** reuse the site relay project and plugin package when the
  owner only wants installation, settings, placement, or verification.
- **New site on this AI VPS:** create a unique relay project key, restricted
  `website-<slug>` agent/workspace, allowlist entry, HTTPS route, and plugin
  configuration. Read `openclaw-course-website-bridge` before changing the
  Bridge or OpenClaw config.
- **Different AI/VPS host:** keep the same fixed request contract and private
  Bridge boundary. Do not copy gateway credentials to the WordPress VPS; use a
  dedicated HTTPS relay or an approved private network path.
- **Widget-only change:** update the plugin assets/package and remote plugin,
  then verify geometry and cache behavior. Do not alter the AI agent or
  knowledge unless requested.

## Required inputs

Collect these values from the owner or approved project note. Ask the owner to
enter passwords and tokens into a secure prompt or admin form, never into chat:

- WordPress public URL and login URL.
- Admin access mode: browser, authenticated HTTP session, or authorized SSH /
  WP-CLI. Stop if 2FA, CAPTCHA, or an unknown login flow cannot be handled.
- Local plugin ZIP/source path and expected package checksum.
- Fixed HTTPS relay endpoint and project identifier.
- Relay token, entered interactively and held only in process memory while
  configuring the server-side WordPress option.
- Desired widget mode: standalone edge, stack above an existing target, or
  move an approved third-party widget and stack both on one side.
- Cache/CDN plugins that may need purging and a non-notifying synthetic test
  question.

Never infer credentials, project IDs, agent IDs, or a production URL from an
unrelated site.

## Production preflight

Before modifying any production project, read:

1. `/root/AGENTS.md`.
2. `/root/_Second_AI_Brain/START_HERE.md`.
3. `/root/_Second_AI_Brain/01_Ban_Do_VPS.md`.
4. `/root/_Second_AI_Brain/02_Danh_Sach_Project.md`.
5. The matching note under `/root/_Second_AI_Brain/projects/`.
6. `/root/_Second_AI_Brain/checklists/truoc_khi_sua_production.md`.
7. Any nearer `AGENTS.md` in the project being changed.

For the reference implementation, inspect:

`/root/.agents/skills/eyelashes-website-chatbot/SKILL.md`

Confirm the target site is reachable, HTTPS is valid, and the current public
page before logging in:

```bash
curl -fsSIL --max-time 20 https://example.com/
curl -fsS --max-time 20 https://example.com/ | tee /tmp/wp-public-before.html >/dev/null
```

Do not put credentials in those commands. Inspect the public HTML for existing
chat/contact widgets, cache markers, plugin assets, and duplicate instances.

## Snapshot and backup

Create a root-only, timestamped transaction before each production mutation:

```bash
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
backup_dir="/root/_Backups/wordpress-openclaw-chatbot/<site-slug>/$stamp"
install -d -m 700 "$backup_dir"
```

Store only what is needed to restore this transaction:

- The prior plugin ZIP/source or a copy of the exact package being replaced.
- Redacted remote metadata: WordPress version, plugin name/version/active
  state, endpoint host/path, auto-display state, cache plugin, and detected
  widget selectors/rectangles.
- If WP-CLI is used, a targeted option/database export only when rollback
  requires it; keep it mode `600` and mark it as secret-bearing. Never print
  it or put it in the journal.
- Nginx, relay, Bridge, or OpenClaw files only when this operation changes
  them; back up each file before editing it.

Do not save passwords, cookies, session headers, nonces, bearer tokens, full
`.env` contents, customer questions, or AI answers. A token fingerprint or a
boolean such as `token_present: true` is sufficient for a snapshot.

## Prepare the relay and package

For an existing relay, run its project skill and tests first. For a new relay:

1. Create a unique project key and restricted website agent/workspace.
2. Add exactly one explicit project mapping to the Bridge allowlist.
3. Deny filesystem, runtime, browser, gateway, web, and messaging tools unless
   the site use case explicitly requires a reviewed exception.
4. Keep the Bridge private on the Docker/internal network and expose only the
   fixed HTTPS relay route.
5. Put only relay URL, project key, and timeout in the website environment;
   never mount the OpenClaw gateway token into a website container.
6. Validate OpenClaw/Bridge configuration before restarting an affected
   service, then test Bridge health from the relay container.

For the reference plugin project:

```bash
cd /root/Apps/website_chatbot/eyelashes_chatbot
python3 -m py_compile app/main.py
PYTHONPATH=. python3 -m unittest discover -s tests -v
node --check wordpress-plugin/eyelashes-chatbot/assets/chatbot.js
docker compose --env-file .env.example config --quiet
```

If rebuilding an archive, follow the package build script's refusal-to-
overwrite behavior. Move the old archive into the transaction backup first;
do not delete it just to make the build pass. Lint PHP with a matching CLI
container when the host does not provide PHP.

Check the archive before uploading it:

```bash
unzip -t /path/to/plugin.zip
sha256sum /path/to/plugin.zip
```

Keep the checksum in the redacted transaction metadata, not the secret-bearing
settings export.

## Install through WordPress Admin

Use a browser or an HTTP session with a secure, interactive password prompt.
Verify that the login response redirects to the intended `/wp-admin/` and that
the authenticated user can manage plugins before making changes. Never put a
password in a shell argument, URL, script, source file, browser automation
fixture, or log.

Upload and activate the ZIP from **Plugins -> Add New -> Upload Plugin**. If
the same plugin and version are already active, do not overwrite it merely to
repeat the install; inspect settings and update only the requested files.

Open the plugin settings and configure:

- A fixed HTTPS relay endpoint for this site/project.
- The relay token through the password field or a server-side constant. Keep
  the existing token when the field is blank, if the plugin supports that
  behavior.
- Automatic display or an explicit shortcode, but not both unless the plugin
  guards duplicate rendering.

The plugin must proxy requests with `wp_remote_post()` (or an equivalent
server-side request), validate same-origin and nonce data, bound question size,
rate-limit requests, and return a useful error when the relay is unavailable.
Do not localize the token into JavaScript, HTML, data attributes, REST output,
browser storage, or a public option endpoint.

If WP-CLI is the only approved path, use a temporary PHP script that reads the
token from an interactive prompt or an inherited file descriptor, updates only
the target option, and exits without echoing the token. Do not use a literal
`wp option update ... <token>` command because shell history and process lists
can expose it.

## Widget placement and coexistence

Treat placement as a separate, explicit decision. Preserve third-party widgets
unless the owner asks to move or disable them.

Supported modes:

- **standalone-edge:** place the plugin at the requested safe-area edge.
- **stack-above-target:** leave the existing widget unchanged and place the
  plugin above its measured trigger/root with a small gap.
- **move-target-and-stack:** only with owner approval, use the target vendor's
  documented API or CSS to move both widgets to one column, then put the
  plugin above it.
- **disabled-target:** verify the third-party widget is actually absent after
  cache purge; do not assume an admin toggle took effect.

Do not hardcode a vendor selector as the only strategy. Discover the target by
configured selectors, stable IDs, iframe/container attributes, or a documented
vendor API. Third-party scripts may inject asynchronously, so use a bounded
`MutationObserver`, then recompute on `resize`, orientation changes, and
`visualViewport` changes.

For each fixed root, measure `getBoundingClientRect()` and computed styles.
For a target with bottom offset `b`, height `h`, and gap `g`, the plugin's
bottom offset for a vertical stack is approximately `b + h + g`. Align the
same left or right edge. When right-aligned, the panel must use `right: 0` and
`left: auto`; when left-aligned, use the inverse. Cap panel width to the
viewport and include `env(safe-area-inset-*)` on mobile.

For a Pancake target specifically, its public API may be used only when moving
it was approved:

```js
window.PancakeChatPlugin.setStyle({
  root: { left: '20px', right: 'auto', bottom: '20px' }
});
```

Treat this API as optional; test that it exists and that the root remains in
the intended position after the vendor script finishes. Never disable a
customer-contact widget silently. Keep z-index ordering intentional: the
opened plugin panel must remain usable, while the third-party trigger remains
clickable when both are visible.

## Cache purge

After saving settings or replacing assets, purge the caches that can serve the
old footer, nonce, CSS, or JavaScript:

- LiteSpeed Cache: use the authenticated **Purge All** action and confirm the
  success response.
- Other cache plugins: use their documented admin/CLI purge operation only
  after identifying the installed plugin.
- CDN/proxy cache: purge only the target site and only when authorized.

Do not flush unrelated sites or delete cache directories blindly. Fetch the
public page with a cache-busting query after purging and verify the asset
version/hash changed as expected.

## Verification

Run checks in this order and record redacted statuses:

1. Relay health returns `status: ok` and configured project metadata.
2. Bridge health succeeds from inside the relay container; the Bridge is not
   publicly reachable.
3. Plugin CSS and JavaScript return HTTP 200 from the WordPress domain.
4. Public HTML contains the expected widget exactly once (or the approved
   shortcode count), and no relay token, gateway token, provider key, cookie,
   or password.
5. Obtain a fresh WordPress nonce and submit one synthetic, non-notifying
   question through the same-origin AJAX endpoint. Require HTTP success, a
   non-empty answer, and a request ID; do not test via Telegram, Messenger, or
   a customer account.
6. Missing/invalid credentials and invalid nonce return the expected safe error
   without leaking upstream details.
7. At desktop and mobile viewports, verify widget rectangles do not intersect,
   stay inside the viewport, and leave the contact/consent controls usable.

### CDP geometry check

When Chromium and a WebSocket CDP client are available, launch a temporary
headless browser with a fresh profile and evaluate the following expression at
desktop and mobile sizes. The exact selectors are site-specific; substitute
the selectors from the redacted snapshot:

```js
(() => {
  const selectors = [
    '.eyelashes-chatbot',
    '#pancake-chat-plugin-root',
    '#button-contact-vr'
  ];
  const result = { width: innerWidth, height: innerHeight };
  for (const selector of selectors) {
    const node = document.querySelector(selector);
    if (!node) { result[selector] = null; continue; }
    const r = node.getBoundingClientRect();
    const c = getComputedStyle(node);
    result[selector] = {
      left: r.left, top: r.top, right: r.right, bottom: r.bottom,
      width: r.width, height: r.height,
      position: c.position, zIndex: c.zIndex
    };
  }
  return result;
})()
```

Use any trusted CDP client (for example, the system Chromium plus Python's
already-installed `websocket` module). Do not install a large browser stack on
production solely for this check. A rectangle intersection is a failure unless
the overlap is intentional and documented.

For an authenticated relay smoke test, load the token into process memory from
the local `.env`; never echo it, put it in shell history, or interpolate it into
a saved command:

```bash
cd /path/to/relay
set -a; . ./.env; set +a
python3 - <<'PY'
import json, os
from urllib.request import Request, urlopen

request = Request(
    os.environ['RELAY_ENDPOINT'],
    data=json.dumps({
        'question': 'Synthetic health check: please return the official site link.',
        'session_id': 'verify-synthetic-session',
    }).encode(),
    headers={
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ' + os.environ['RELAY_API_TOKEN'],
    },
    method='POST',
)
with urlopen(request, timeout=75) as response:
    payload = json.load(response)
assert payload.get('answer') and payload.get('request_id')
print('non-notifying chat smoke ok')
PY
```

The endpoint and token variables must come from a mode-600 local `.env`; do
not copy this example with real values into a skill, ticket, or log.

The fixed relay contract is deliberately small:

```text
POST <relay-endpoint>
Authorization: Bearer <server-side-token>
{"question":"...","session_id":"..."}
-> {"answer":"...","configured":true,"project":"...","request_id":"..."}
```

The WordPress integration does not write to Google Sheets, a CRM, Telegram,
Messenger, or a customer database by default. Add lead capture or
notifications only as a separately approved change with its own data-retention
and secret review.

## Rollback

Rollback only the transaction that failed or the exact change the owner asks
to undo:

1. Save a fresh failure snapshot and stop making further mutations.
2. Deactivate the target plugin if it is the source of the regression.
3. Restore the matching plugin ZIP/source and targeted WordPress option/settings
   from the timestamped backup. Never run a broad database reset.
4. Restore relay, Bridge, Nginx, or OpenClaw files only when they belong to the
   same transaction; validate before restarting the affected service.
5. Purge the relevant cache and repeat health, public HTML, nonce/AJAX, and
   geometry checks.
6. Keep the backup until the owner confirms stability. Do not delete customer
   data, sessions, credentials, or unrelated widgets as part of rollback.

If the plugin has a clean uninstall routine, prefer deactivation over deletion
until the rollback is accepted. Do not restore an old token when only CSS,
placement, or cache behavior changed.

## Rerun, handoff, and journal

Rerun starts with a fresh preflight and compares the current redacted snapshot
with the previous one. Make operations idempotent: one plugin instance, one
fixed relay route, one project allowlist entry, and one restricted website
agent. Do not upload the same package repeatedly when version and checksum
already match.

After a successful change, hand off:

- Site URL and plugin/version status.
- Relay health URL and fixed route (not its token).
- Placement mode, target selector/API, and verification viewport results.
- Cache purge result and the transaction backup path.
- Any unresolved 2FA, CDN, widget, or access caveat.

Update the matching project note, registry, and
`/root/_Second_AI_Brain/06_Nhat_Ky_Thay_Doi.md` with paths, hashes, statuses,
and redacted metadata only. Never record credentials, cookies, customer
conversation text, or full AI answers.

## Secret scan before completion

Read and follow the global `khu-token-api-secret` skill before declaring a new
skill or project ready. At minimum, scan current text files and tracked files:

```bash
rg -uuu -n --glob '!**/.git/**' \
  '(sk-proj-[A-Za-z0-9_-]+|sk-[A-Za-z0-9_-]{20,}|AIza[0-9A-Za-z_-]{25,}|gh[pousr]_[0-9A-Za-z_]{20,}|github_pat_[A-Za-z0-9_]+|xox[baprs]-[A-Za-z0-9-]{10,}|[0-9]{7,}:[A-Za-z0-9_-]{25,})' \
  /root/.agents/skills/wordpress-openclaw-chatbot
```

Ensure `.env`, logs, credentials, browser profiles, caches, `__pycache__`,
and `*.pyc` are ignored or outside the skill. Replace examples with
placeholders, validate YAML/JSON touched by the operation, and run the skill
validator before handoff.

## Related skills

- `eyelashes-website-chatbot`: reference relay, plugin contract, and knowledge
  workflow.
- `openclaw-course-website-bridge`: restricted agents, project allowlist, and
  private Bridge operations.
- `khu-token-api-secret`: mandatory secret scan and sanitization.
- `skill-creator`: initialize and validate reusable global skills.
