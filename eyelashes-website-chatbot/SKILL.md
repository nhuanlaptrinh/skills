---
name: eyelashes-website-chatbot
description: Operate, verify, update, or integrate the OpenClaw-backed chatbot for the remote WordPress site eyelashes.vn.
---

# Eyelashes Website Chatbot

Use this skill when changing the Eyelashes VN chatbot relay, its approved
knowledge, the WordPress plugin package, or the OpenClaw Bridge project used by
that site.

## Architecture

```text
eyelashes.vn browser
  -> WordPress plugin same-origin AJAX
  -> https://chatbot.anhlaptrinh.vn/v1/eyelashes/chat
  -> relay container 127.0.0.1:8890
  -> private Bridge 172.18.0.1:18890
  -> OpenClaw project eyelashes / agent website-eyelashes
```

The relay project is:

`/root/Apps/website_chatbot/eyelashes_chatbot`

Important files:

- `app/main.py`: authenticated FastAPI relay.
- `knowledge/eyelashes.md`: operator-approved public facts.
- `docker-compose.yml`: one-worker container on external network
  `root_traefik`.
- `wordpress-plugin/eyelashes-chatbot/`: plugin source.
- `wordpress-plugin/eyelashes-chatbot.zip`: uploadable plugin archive.
- `/root/AI_Runtime/openclaw_bridge/config/projects.json`: Bridge allowlist.
- `/root/.openclaw/openclaw.json`: restricted agent registration.

## When to use

- Verify relay health or a public chat request.
- Update approved product, wholesale, OEM/ODM, shipping, or contact facts.
- Rebuild the WordPress ZIP after plugin changes.
- Recreate the relay after code or knowledge changes.
- Audit that the relay token stays server-side and the Bridge remains private.

## Configuration and secrets

- Real relay settings are only in
  `/root/Apps/website_chatbot/eyelashes_chatbot/.env` (mode `600`).
- `.env.example` contains placeholders only.
- Never copy the relay token, OpenClaw gateway token, provider key, cookie, or
  private credential into JavaScript, PHP source, ZIP archives, README files,
  skill files, logs, or chat messages.
- The WordPress plugin stores the relay token in WordPress server options and
  sends it only through `wp_remote_post()`; it must not be localized to the
  browser.

## Current plugin placement

The deployed package is version `1.0.4`. The widget is standalone at the
bottom-left and does not depend on any third-party chat widget. On narrow
viewports (up to 520px), `assets/chatbot.js` measures the visible right-side
contact lane (`#button-contact-vr`, `#zalo-vr`, or `#whatsapp-vr`) and caps the
opened panel width so the panel remains usable without covering those controls.
The measurement is refreshed after resize, orientation/visual viewport changes,
and bounded DOM mutations; desktop removes the temporary width override.

## Dry run

These checks do not call the model or modify production:

```bash
cd /root/Apps/website_chatbot/eyelashes_chatbot
python3 -m py_compile app/main.py
PYTHONPATH=. python3 -m unittest discover -s tests -v
docker compose --env-file .env.example config --quiet
node --check wordpress-plugin/eyelashes-chatbot/assets/chatbot.js
```

PHP CLI may not be installed on the AI VPS. If available, also run:

```bash
php -l wordpress-plugin/eyelashes-chatbot/eyelashes-chatbot.php
php -l wordpress-plugin/eyelashes-chatbot/uninstall.php
```

## Build and run

The build script refuses to overwrite an existing archive. Move the old archive
to a dated backup before rebuilding, then run:

```bash
cd /root/Apps/website_chatbot/eyelashes_chatbot
mv wordpress-plugin/eyelashes-chatbot.zip /root/_Backups/eyelashes_chatbot/<timestamp>/eyelashes-chatbot.zip
./wordpress-plugin/build_zip.sh
docker compose up -d --build --force-recreate
docker compose ps
```

Use an explicit, recoverable backup path; do not delete the old archive merely
to make the build pass.

## Verification

Local health:

```bash
curl -sS http://127.0.0.1:8890/health
```

Public health:

```bash
curl -sS https://chatbot.anhlaptrinh.vn/health
```

Expected health fields are `status: ok`, `configured: true`, and
`project: eyelashes`.

For a real smoke test, load the token from the local `.env` in process memory
and send a synthetic, non-notifying question. Do not place the token in shell
history or output:

```bash
cd /root/Apps/website_chatbot/eyelashes_chatbot
set -a; . ./.env; set +a
python3 - <<'PY'
import json, os
from urllib.request import Request, urlopen

request = Request(
    'https://chatbot.anhlaptrinh.vn/v1/eyelashes/chat',
    data=json.dumps({
        'question': 'Cho toi xin link trang ban si cua Eyelashes VN',
        'session_id': 'verify-synthetic-20260903',
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
assert payload.get('answer')
assert payload.get('request_id')
print('chat smoke ok; answer is non-empty')
PY
```

Also verify missing credentials returns HTTP 401 and that the container can
reach the private Bridge health endpoint. Never test with Telegram or customer
notifications.

## API input and output

The relay accepts only this fixed public contract:

```json
{
  "question": "Tôi muốn nhận bảng giá sỉ",
  "session_id": "opaque-browser-session"
}
```

Successful responses contain `answer`, `configured`, `project`, `request_id`,
and `session_id`. Error responses contain a short `error` code. The service does
not write to Google Sheets, a CRM, Telegram, or a customer database; lead
capture remains outside this integration.

## Knowledge updates

Edit only facts that have been checked and approved by the site owner in
`knowledge/eyelashes.md`. Keep prices, stock, MOQ, lead times, certifications,
taxes, shipping, and promises qualified unless the source explicitly confirms
them. Restart/recreate the container after changing the mounted knowledge file.
Run the full dry-run and one non-notifying smoke test afterward.

## WordPress installation

The separate WordPress VPS is not managed by this project. A WordPress admin
uploads `wordpress-plugin/eyelashes-chatbot.zip`, activates it, opens
`Settings -> Eyelashes Chatbot`, enters the HTTPS relay endpoint and token, and
enables `Tự hiện chatbot` (or inserts `[eyelashes_chatbot]`). Disable the old
Pancake widget first if both floating widgets would overlap.

The plugin uses a nonce, same-origin validation, server-side proxying, and a
WordPress transient rate limit. Its current default is a standalone
bottom-left safe-area placement and it does not depend on any third-party chat
widget. It is compatible with standard WordPress, WooCommerce, Flatsome, and
UX Builder because it does not require Elementor. Use the reusable
`wordpress-openclaw-chatbot` skill for optional third-party stacking modes.

## OpenClaw and Bridge changes

If the agent or allowlist must change:

1. Read the production checklist and the `openclaw-course-website-bridge`
   skill.
2. Back up `openclaw.json`, `projects.json`, the Bridge service configuration,
   and any affected Nginx/UFW files under `/root/_Backups`.
3. Keep the agent restricted and deny filesystem, runtime, browser, gateway,
   web, and messaging tools.
4. Validate with `openclaw config validate`; restart only the affected service.
5. Test the Bridge from the relay container, then run the public smoke test.

Never expose or mount the OpenClaw gateway token in the WordPress project or
relay container. Do not accept a caller-selected project or model.

## Rollback

Use the matching dated backup under `/root/_Backups/eyelashes_chatbot/` for
relay/config rollback. Restore only the file being reverted, recreate the
container if its code or environment changed, run health and smoke checks, and
record the result in `/root/_Second_AI_Brain/06_Nhat_Ky_Thay_Doi.md`.

## Outputs and handoff

- Relay: HTTPS API and health endpoint above.
- Plugin archive: `/root/Apps/website_chatbot/eyelashes_chatbot/wordpress-plugin/eyelashes-chatbot.zip`.
- Source and knowledge: project directory above.
- Change record: `/root/_Second_AI_Brain/06_Nhat_Ky_Thay_Doi.md`.

Record only paths, statuses, hashes, and redacted metadata. Never record real
secrets or customer conversations.
