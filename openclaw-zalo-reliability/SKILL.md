---
name: openclaw-zalo-reliability
description: Diagnose, recover, harden, and operate OpenClaw Zalo Personal on Docker member VPS systems. Use when Zalo receives no reply, inbound or outbound delivery fails, the listener exits, sessions become long-running or oversized, both Telegram and Zalo stop because the member Gateway is absent or unmanaged, Supervisor configuration drifts, recurring failures need Shared Watchdog prevention, files or heavy tasks are delivered unreliably, or Zalo QR login is required as a last resort.
---

For installing this reliability layer on another Docker member, use the
companion deployment skill at
`/root/.agents/skills/openclaw-zalo-reliability-deploy/SKILL.md`. Its installer
is dry-run by default and registers the delivery watchdog through the shared
watchdog center without copying credentials.

# OpenClaw Zalo Reliability

Use this as the single entry point for Zalo Personal incidents and prevention on
OpenClaw member VPS containers. For a new connection or a new member, first
run `openclaw-zalouser-onboarding-standard`; use this skill for the channel
diagnosis and recovery layers. Diagnose the failure layer before changing
production, preserve pairing and transcripts, and use QR login only after safer
recovery paths fail.

## Boundaries

- Keep `/root/Automation/watchdog/shared_self_healing` as the shared runtime and
  registry for all projects. Do not copy or merge that center into this skill.
- Use `/root/.agents/skills/shared-watchdog-center/SKILL.md` only when changing
  the generic center architecture or adding non-OpenClaw projects.
- Do not modify `/root/.agents/skills/self-healing-watchdog` as part of a Zalo
  incident.
- Use this skill for member data under
  `/root/Apps/member_vps/docker-users/data`, not automatically for the root
  OpenClaw runtime.

## Required Preflight

1. Read the VPS Second AI Brain, production checklist, nearest `AGENTS.md`, and
   the affected member project note.
2. Resolve the exact `CONTAINER`, internal `MEMBER_HOME`, host directory that
   directly contains `.openclaw`, member label, and unique watchdog keys.
3. Confirm whether the Gateway parent is Supervisor, tmux, systemd, or absent.
4. Back up every file that may change, the session index, affected plugin
   bundle, watchdog registry, cron, and relevant project note.
5. Never print `.env`, tokens, cookies, passwords, QR payloads, pairing data,
   private sender/group IDs, or message contents.

## Start With Read-Only Diagnosis

```bash
bash /root/.agents/skills/openclaw-zalo-reliability/scripts/diagnose.sh \
  <container> <member-home> [zalo-id]
```

The diagnostic loads Gateway auth internally, redacts common secrets, checks
core/plugin versions, probes Zalo, inspects only recent provider logs, detects
listener/outbound/cipher/session symptoms, and does not change production.

## Route The Incident

- **Telegram works, Zalo is silent or outbound fails:** read
  [references/zalo-no-response.md](references/zalo-no-response.md).
- **Both Telegram and Zalo stop, port 18789 is absent, or proxy returns 502:**
  read [references/gateway-recovery.md](references/gateway-recovery.md), then
  [references/supervisor-watchdog.md](references/supervisor-watchdog.md) when
  process-manager drift caused the incident.
- **Sessions, long tool output, files, voice, or heavy tasks cause delayed or
  missing replies:** read
  [references/delivery-and-session.md](references/delivery-and-session.md).
- **Credential/cipher/login still fails after version alignment and a clean
  Gateway restart:** read
  [references/zalo-qr-login.md](references/zalo-qr-login.md). Applying QR login
  requires an explicit owner request because it replaces the active Zalo
  session.
- **Before declaring completion or rolling back:** read
  [references/verification-and-rollback.md](references/verification-and-rollback.md).

Read only the references required for the current failure path. For incidents
that cross layers, follow this order: Gateway process, plugin/listener, inbound
and outbound, session, then authentication.

## Durable Prevention

### Cache inbound Zalo image URLs before vision tools

When a Zalo image arrives only as a short-lived `photo-stal-*.zdn.vn` or
`file-stal-*.dlfl.vn`/`*.flchat.vn` URL, preserve the exact URL and cache it
through OpenClaw's guarded media runtime before dispatching the agent turn.
Pass the resulting local media path to the vision tool; do not ask the model to
copy the signed URL into a second tool call. Use a bounded size (20 MiB), HTTPS,
header/body idle deadlines, one fetch retry, and redact URLs from logs. On a
cache failure retain the original inbound text and report the bounded failure;
never claim the URL expired until the exact original URL has been tested.

#### Maintained implementation for Docker members

For a member using the bundled `@openclaw/zalouser` monitor, the maintained
implementation is an inbound pre-dispatch wrapper around `saveRemoteMedia`.
Locate the active bundle under
`<member-data>/.openclaw/npm/projects/*/node_modules/@openclaw/zalouser/dist/`
and patch only its `monitor-*.js`; do not edit the global OpenClaw install or a
stale npm project. The wrapper must:

- extract at most four exact HTTPS `photo-stal-*`/`file-stal-*` URLs;
- call `saveRemoteMedia` with `subdir: "inbound/zalo"`, 20 MiB maximum,
  20-second total timeout, 10-second header/read-idle deadlines, and one
  bounded retry;
- replace each successfully cached URL with the returned local path before
  agent dispatch, while retaining the original body if caching fails;
- log only size/content type or a bounded error string, never the signed URL.

Before applying: back up `openclaw.json` and the active monitor bundle under
`/root/_Backups/<member>-zalo-image-cache/<UTC timestamp>/`. Validate with
`node --check <monitor-file>`, `openclaw config validate`, and
`openclaw channels status` inside the member container. After reload/restart,
require Zalo `linked, running, connected` and scan recent logs for plugin import
or media-cache errors. Do not send a real group test unless the owner requests
one. Record the backup, target bundle, validation, and rollback path in the
Second AI Brain change log.

### Mandatory group-target guard (Zalo Personal)

For every outbound reply, file, reminder, or proactive message whose current
session key is `agent:<agent>:zalouser:group:<group-id>`, preserve the group
type in the target: use `group:<numeric-group-id>` (or `g:<numeric-group-id>`).
Never pass a bare numeric ID. The Zalo adapter parses a bare number as a User
thread (`isGroup=false`); it can return an API-level `sent` receipt while the
message is routed away from the group and the transcript is rebound to a
`...:direct:<id>` session. Treat such a receipt as unverified group delivery.

Before declaring delivery, require all of these: non-empty platform
`messageId`, `deliveryStatus: sent`, and `receipt.threadId` or
`conversationId` matching the current numeric group ID. If the target was
bare numeric or the receipt lacks the group proof, do not replay blindly;
inspect the delivery record, then send once with the explicit `group:` target
when safe. Keep `NO_REPLY` only after that explicit native send is verified.

### Maintained group route helper

When the active `@openclaw/zalouser` bundle emits `to: zalouser:<id>` even
though the inbound event is a group, use the exact-anchor helper below. It is
dry-run by default, edits only the group adapter branch, and never restarts a
Gateway or sends a message:

```bash
/root/.agents/skills/openclaw-zalo-reliability/scripts/patch_zalo_group_route.sh \
  --member-data-dir /root/Apps/member_vps/docker-users/data/<member> --dry-run
```

Apply only during a controlled maintenance window:

```bash
/root/.agents/skills/openclaw-zalo-reliability/scripts/patch_zalo_group_route.sh \
  --member-data-dir /root/Apps/member_vps/docker-users/data/<member> --apply
```

The helper refuses ambiguous bundles and changed anchors, stores a timestamped
backup plus SHA-256 under `/root/_Backups/<member>-zalo-group-route-fix/`, and
preserves direct-user routing. Run `node --check` on the changed channel bundle,
then `openclaw plugins doctor` and a probed channel status before reloading the
existing Supervisor-owned Gateway.

#### Scoped core normalizer guard

If the member core bundle lacks the scoped normalizer guard, use the container
helper (dry-run by default). It backs up the exact core bundle before applying,
requires matching Zalo group context and IDs, and never touches credentials:

```bash
/root/.agents/skills/openclaw-zalo-reliability/scripts/patch_zalo_core_group_guard.sh \
  --container user-<member> --dry-run
/root/.agents/skills/openclaw-zalo-reliability/scripts/patch_zalo_core_group_guard.sh \
  --container user-<member> --apply
```

Run `node --check` through the helper, then `openclaw plugins doctor` and a
probed channel status after the controlled Gateway reload. The core bundle is
in the member image layer and must be re-applied after a container recreate or
image upgrade.

#### Maintained 2026.8.2 route fix

The active `@openclaw/zalouser` 2026.8.2 bundle previously preserved
`chatType: group` but emitted `to: zalouser:<id>`, which the next adapter stage
parsed as a direct-user route. The maintained member patch changes only that
route branch to emit `to: zalouser:group:<id>` for groups and leaves direct
users unchanged. Before applying it, back up the active `channel-*.js` bundle;
afterward run `node --check`, `openclaw plugins doctor`, and a probed channel
status. Do not patch every `zalouser:<id>` occurrence globally because direct
user and pairing paths require their existing form.

The core message-action normalizer also has a scoped guard: it may normalize a
bare numeric target only when trusted `toolContext` proves
`currentChannelProvider=zalouser`, `currentChatType=group`, and the current
channel/messaging target has the same numeric ID. Direct messages, reactions,
other providers, and different IDs remain untouched.
The core bundle is in the member image layer rather than the mounted member
data; reapply this scoped guard after a container recreate or image upgrade,
and verify the bundle hashes during maintenance.

After a recurring incident, use the existing Shared Watchdog Center rather than
creating another watchdog implementation:

- `openclaw_gateway`: host-side Supervisor guard; set `ai_on_failure=false`.
- `openclaw_channel`: Zalo listener/outbound probe with restart cooldown.
- `openclaw_session`: scheduled audit/summary compaction with an explicit
  session pattern.
- `host_resource`: RAM, swap, memory PSI, OOM and member cgroup guard through
  `member-vps-resource-oom-guard`.

The Zalo probe status may include fields such as `linked` between
`configured` and `running`. Health matching must therefore allow intermediate
fields (`configured.*running.*works`) instead of requiring those words to be
adjacent; otherwise a healthy linked account can trigger a false restart and
Telegram warning.

Treat `dm:pairing` as the configured DM access policy, not as an authentication
result. Do not claim that a Zalo session expired from this field, a stale
delivery error, or a retry warning alone; confirm authentication with the live
channel probe/plugin result before recommending QR login.

Cron must call
`/root/Automation/watchdog/shared_self_healing/run_project.sh`; do not call the
underlying scripts directly. Preserve unrelated registry and cron entries.

#### Maintained bounded text-send retry for OpenClaw 2026.9.5+

In OpenClaw `2026.9.5`, the active Zalo sender may be bundled as
`<member-data>/.openclaw/npm/projects/*/node_modules/@openclaw/zalouser/dist/.setup/send-*.mjs`
rather than `dist/send-*.js`. The maintained helper
`/root/Automation/openclaw_member_assistant/scripts/patch_zalouser_send_reliability.sh`
supports both layouts. It adds at most three attempts for text chunks with
bounded backoff and a short inter-chunk delay; media sends remain single-attempt
so an uncertain upload is never replayed blindly. Always run the helper dry-run,
back up the exact active bundle, run `node --check`, then run plugin doctor and a
probed channel status after the controlled Supervisor Gateway reload. If a new
bundle changes the sender anchors, the helper must refuse the mutation rather
than patching by broad string replacement.

When the user sees the exact English text `I couldn’t confirm whether my
previous reply reached this chat...`, trace it as the core lifecycle
`PENDING_DELIVERY_NOTICE`. It means the model run completed but outbound Zalo
delivery ended in `unknown_after_send`; it is not a memory or prompt
generation error. Confirm the model result, sender attempts, and live channel
probe separately. Bounded retries help transient failures, but three failed
attempts require investigating the Zalo API response or recipient target; do
not add unlimited retries or blindly replay a possibly delivered message.
Compare the displayed account's own user ID with the recipient target before
calling it a self-chat issue; do not infer self-chat from the contact name.

## Recovery procedure for an oversized or stalled group session

Use this sequence when logs contain `claim→adoption stalled`,
`reply_operation_aborted`, `skipped:duplicate`, `finalization_stalled`, or
`OutboundDeliveryError` while the live Zalo probe still works:

1. Resolve the exact group session key from the live session list. Do not use a
   broad pattern when applying a repair.
2. Back up `openclaw.json`, the agent SQLite store and matching `-wal`/`-shm`,
   the shared state SQLite files, the active Zalo send bundle, watchdog JSON,
   and crontab under `/root/_Backups`.
3. Wait until the target session has been idle for at least 600 seconds. Run a
   dry-run first:

   ```bash
   MEMBER_HOME=/home/<member> \
   SESSION_PATTERN='agent:main:zalouser:group:<group-id>' \
   TOKEN_THRESHOLD_64K=18000 TOKEN_THRESHOLD_128K=40000 \
   SESSION_IDLE_SECONDS=600 MAX_COMPACTIONS_PER_RUN=1 \
   COMPACTION_MODE=summary \
   bash /root/Automation/openclaw_member_assistant/scripts/audit_member_sessions.sh \
   user-<member>
   ```

   Apply only after the target is idle and the backups exist, using the same
   command with `--apply`. This preserves the transcript and compacts one
   session at a time; never delete the whole session store.
4. For OpenClaw 2026.8.2, enable only schema-supported prevention settings:

   ```bash
   openclaw config set agents.defaults.contextPruning.mode cache-ttl
   openclaw config set agents.defaults.contextPruning.ttl 5m
   openclaw config set agents.defaults.compaction.mode safeguard
   openclaw config set agents.defaults.compaction.midTurnPrecheck.enabled true
   openclaw config set agents.defaults.compaction.maxActiveTranscriptBytes 2mb
   openclaw config set agents.defaults.compaction.keepRecentTokens 12000
   openclaw config validate
   ```

   `reserveTokensFloor` and `maxHistoryShare` are not valid keys on this
   release; do not leave unsupported keys in production config.
5. If the active bundle is unpatched, run
   `MEMBER_DATA_DIR=/root/Apps/member_vps/docker-users/data/<member> bash /root/Automation/openclaw_member_assistant/scripts/patch_zalouser_send_reliability.sh --apply`, validate with `node --check`
   and `openclaw plugins doctor`, then restart only the existing
   Supervisor-owned `openclaw-gateway`.
6. Add two Shared Watchdog entries for the member: an `openclaw_channel` probe
   every five minutes and an `openclaw_session` audit every two hours with
   `SESSION_PATTERN='agent:main:zalouser:'`, `MAX_COMPACTIONS_PER_RUN=1`,
   `COMPACTION_MODE=summary`, and the 600-second idle gate. Register both in
   `project_config.json` and call them through `run_project.sh` from cron.

After reload, require `config validate`, `plugins doctor`, Zalo probe
`configured/linked/running/connected/works`, one live Gateway under Supervisor,
zero pending delivery-queue entries, and a post-reload log scan with no new
stall/abort/outbound errors. Ask the authorized owner to send the real group
test; do not send a bot-generated test message.

## Safety Rules

- Prefer dry-run, passive probes, syntax validation, and unit tests.
- Never delete credentials, all sessions, or transcripts.
- Never run a second Gateway beside Supervisor or keep a member Gateway in
  tmux after migration.
- Never recreate a container for a Gateway-only repair.
- Do not fault-inject production or send real Telegram/Zalo test messages
  without explicit authorization.
- After production changes, update the affected member note and
  `/root/_Second_AI_Brain/06_Nhat_Ky_Thay_Doi.md` without recording secrets.

## Member maintenance update (2026-09-05)

For member bundles on OpenClaw 2026.8.2, use the explicit member data directory:
`MEMBER_DATA_DIR=/root/Apps/member_vps/docker-users/data/<member> bash /root/Automation/openclaw_member_assistant/scripts/patch_zalouser_send_reliability.sh`
to add bounded three-attempt Zalo text-send retries and a 600 ms delay between
split chunks. The helper accepts both the older bundle with
`DEFAULT_TEXT_CHUNK_MODE` and the current bundle that begins directly at
`ZALO_TEXT_LIMIT`; it backs up the active `send-*.js` bundle before applying.
After patching, run `node --check` on the active bundle, `openclaw plugins doctor`,
then restart only the Supervisor-owned member Gateway.

### Watchdog matcher correction (2026-09-05)

The shared Zalo watchdog must recognize the stable status sequence
`configured, ... , running, ... works` while allowing optional fields such as
`linked` or `dm:pairing`. Require punctuation or whitespace before the
`running` token so `health:not-running` cannot count as healthy. Do not use an
alternation containing `^` after `.*` in the `grep -E` expression; that pattern
falsely classified healthy members as `channel_not_running` and caused repeated
Gateway restarts. Validate the matcher with both healthy and
`not authenticated/stopped` status fixtures, then run the member watchdog in
`--dry-run` mode before relying on cron.

The member channel watchdog also uses a bounded reconnect grace window after a
Gateway restart. Keep several probe attempts across roughly 60 seconds before
raising a QR/login warning; a single failed probe during listener startup is
not evidence that the saved Zalo session is gone.

When a Zalo send returns an unknown error, distinguish the outbound delivery
failure from authentication: preserve the delivery record, use the bounded
send retry patch, and do not blind-replay a `send_attempt_started` item. Check
Gateway/event-loop and host I/O or swap pressure because those stalls can make
both Zalo and Telegram appear disconnected. Keep a member `host_resource` guard
enabled for early warning, and align or pin the Zalo plugin with the core
release during the next controlled maintenance window.

## Zalo attachment callback guard (2026-09-06)

Use this branch when a Zalo text message works but a DOCX, PDF, ZIP, video, or
other attachment leaves the session in `blocked_tool_call`, `stalled session`,
or `This turn was interrupted because it stopped making progress`.

The known failure in `@openclaw/zalouser` 2026.8.2 with `zca-js` 2.1.2 is an
unbounded Promise in `zca-js/dist/apis/uploadAttachment.js`. For `video` and
`others`, the upload POST registers a callback and waits for a WebSocket
`file_done` event. A missing or early event leaves the Promise pending; the
callback map's five-minute expiry only removes the key and does not settle the
Promise. This is an upload acknowledgement failure, not evidence of a bad Zalo
login or a corrupt document.

### Required delivery path

- Use the running Gateway's native send route, with a Gateway-buffer attachment
  when a local-path allowlist rejects the workspace path. Do not import an
  internal hashed channel runtime from a standalone Node process: it can create
  a second zca context without the Gateway listener and can trigger a duplicate
  connection.
- Treat a send as verified only after the Gateway/Zalo receipt contains a real
  platform message ID and the intended destination. A timeout or unknown result
  is not permission to replay the same `send_attempt_started` queue item.
- Before any retry, inspect the delivery queue and receipt/history. Terminalize
  an orphaned `send_attempt_started` entry only after backing up the queue DB,
  WAL/SHM, and orphan media. Retry once only when no matching successful
  delivery is possible.
- Keep the completion turn `NO_REPLY` after a verified native send so buffered
  assistant text cannot create a second or misleading message.

### Permanent implementation requirement

The plugin/core upgrade or maintained patch must make the attachment wait
bounded (60 seconds is the current operating target), remove the callback from
the map on timeout, reject with a typed upload error, and catch errors from the
async callback (including checksum/read failures). It must also handle a
`file_done` event that arrives before callback registration, either by buffering
that event briefly or by registering the waiter before the upload response can
be delivered. Do not blindly retry a timed-out attachment because the platform
may already have accepted it.

Do not hot-patch a live member package solely to resend one file. During a
controlled maintenance window, back up the active plugin bundle and package,
apply the maintained upstream fix, run syntax/plugin checks, restart only the
existing Gateway owner, and verify the channel before one authorized smoke
send.

### Offline acceptance tests

Use a fake upload response and fake WebSocket listener to prove all three cases:

1. `file_done` arrives normally: the Promise resolves with the file result.
2. No `file_done` arrives: it rejects at the configured timeout and removes the
   callback; the session cannot remain pending forever.
3. `file_done` arrives after timeout: it is ignored and cannot resolve a later
   request.

Then run `node --check` on the changed bundle, `openclaw plugins doctor`,
`openclaw channels status --probe --json`, and a post-reload log scan. Require
zero new `blocked_tool_call`, `stalled session`, or outbound errors and zero
pending delivery-queue entries. A live attachment test must be a single small
file with an owner-approved destination and one receipt check.

The maintained `zca-js` 2.1.2 patch has two bundle branches. The ESM branch is
applied with `scripts/patch_zca_upload_ack_guard.sh`. OpenClaw loads the
CommonJS branch through `package.exports.require` in some member layouts; apply
and verify that branch with
`scripts/patch_zca_upload_ack_guard_cjs.sh --member-data-dir <member-data-dir>
--dry-run|--apply`. It patches only `dist/cjs/apis/uploadAttachment.cjs`,
`dist/cjs/apis/listen.cjs`, and the dependency-free
`dist/cjs/upload-completion-guard.cjs`, with a root-only backup before apply.
Run `node --check` on all three CommonJS files and the same offline callback
tests before reloading the Supervisor-owned Gateway.

### Maintained attachment guard helper (2026-09-06)

For the `zca-js` 2.1.2 upload acknowledgement stall, use the guarded helper
before any production apply. It requires an explicit member data directory and
is dry-run by default:

```bash
/root/.agents/skills/openclaw-zalo-reliability/scripts/patch_zca_upload_ack_guard.sh \
  --member-data-dir /root/Apps/member_vps/docker-users/data/<member> --dry-run
```

The helper refuses ambiguous member paths, multiple active bundles, versions
other than 2.1.2, or an already-marked bundle. Apply mode backs up the active
bundle (`package.json`, `dist/apis/uploadAttachment.js`, `dist/apis/listen.js`,
`dist/context.js`) and SHA-256 manifest under
`/root/_Backups/<member-basename>-zalo-upload-ack-guard/<UTC-timestamp>/zca-js-2.1.2`, copies the
bounded completion guard, and changes only the upload/listener acknowledgement
branches. It does not restart a Gateway or send a message:

```bash
/root/.agents/skills/openclaw-zalo-reliability/scripts/patch_zca_upload_ack_guard.sh \
  --member-data-dir /root/Apps/member_vps/docker-users/data/<member> --apply
```

The guard waits at most 60 seconds, removes its callback, rejects typed timeout
or checksum/read errors, buffers an early `file_done` for 15 seconds (maximum
128 entries), and suppresses late/duplicate events with bounded tombstones. Run
the offline acceptance suite and syntax checks on a copied fixture first:

```bash
node /root/.agents/skills/openclaw-zalo-reliability/scripts/test_upload_completion_guard.mjs
node --check <fixture>/dist/upload-completion-guard.js
node --check <fixture>/dist/apis/uploadAttachment.js
node --check <fixture>/dist/apis/listen.js
```

After a real apply, run `node --check`, `openclaw plugins doctor`, a probed
Zalo channel status, and the queue/log checks in `verification-and-rollback.md`.
Rollback is file-level from the timestamped backup's `dist/apis/*`,
`dist/context.js`, and `package.json`; stop before rollback if the live bundle
has changed since the recorded SHA-256 manifest. Restart only the existing
Supervisor-owned Gateway after validation. Do not run the helper on an active
bundle to resend one file and do not use it to replay a `send_attempt_started`
queue entry.

## Inbound-without-outbound guard (2026-09-06)

A member can report Zalo `configured/running/works` while a group session's
writer/event loop is stalled. The channel probe alone cannot detect this. The
watchdog must therefore correlate recent redacted inbound and outbound markers:
for each `agent:main:zalouser:group:<id>` event, require a final/receipt marker
within 180 seconds. If an inbound marker remains unmatched for 180 seconds,
record `group_inbound_without_outbound`, acquire the existing gateway lock, and
restart only the Supervisor-owned Gateway after the normal cooldown (minimum
600 seconds). Never inspect or log message text or IDs; persist only counts,
timestamps, group hash, and the reason. After restart require the normal
60-second multi-probe recovery window. A single unmatched event during startup,
manual `NO_REPLY`, or an attachment upload in progress must not trigger a
restart. This guard complements `openclaw_channel` and session maintenance; it
must run through `run_project.sh`, preserve unrelated registry entries, and be
tested with healthy, delayed, `NO_REPLY`, and stalled fixtures before enabling.

## 03.09 upgrade compatibility (2026-09-08)

- The scoped core group helper now resolves exactly one `message-action-normalization-*` `.js` or `.mjs` bundle by its exported implementation anchor, supporting the `2026.9.3` `.mjs` package layout. Dry-run checks both insertion anchors and makes no changes; apply creates a root-only backup, validates a staged file with `node --check`, then replaces only that file.
- Before upgrading a member with existing Zalo patches, archive its managed `npm` tree and current core package. After official upgrade, preserve/reapply only the equivalent scoped group guard and existing upload acknowledgement protection against the new compatible implementation. Never replace the new core with an old hashed bundle.

## Verified CLI versus Gateway attachment path (2026-09-23)

On anhlaptrinhthu, OpenClaw/plugin 2026.9.5 with zca-js 2.1.2 and both
acknowledgement guards present, standalone CLI message send --media timed out.
The same DOCX sent through the running Gateway message tool using buffer,
filename and mimeType returned deliveryStatus sent, a media message ID and
the expected group receipt. Prefer this existing native tool path; do not
create a second standalone Zalo sender/listener. Guard presence or a healthy
channel probe is not an attachment delivery test. The receipt field via: direct
alone does not indicate a user-thread misroute: explicit target and receipt
threadId/conversationId determine the destination. No QR login was required.

## Portable Gateway-buffer attachment route (2026-09-23)

The reusable `zalo-buffer-file-send` skill and `scripts/send_buffer_attachment.py` are the preferred delivery path for every member VPS when the ordinary local-media route reports `Timed out waiting for upload acknowledgement`. The failure signature is a message action carrying a local `media` path while `buffer` is empty; the running `zca-js` upload then waits for `file_done` even though text and channel probes are healthy. This is a media hydration/acknowledgement path failure, not by itself proof that the Zalo login expired.

Deploy the global skill and helper into the target member workspace after backing up the existing skill/AGENTS files. Resolve the exact member data directory, container name, and member home from its project note; never hardcode another member's home or credentials. Run the helper's `--dry-run`, then send with an explicit `user:<id>` or `group:<id>` target. The helper reads the existing Gateway token in memory, supplies `buffer`, `filename`, and `mimeType` to `/tools/invoke`, and does not create a second Zalo connection.

Accept a result only with `status: sent`, a platform message ID, and a receipt thread/conversation ID equal to the requested numeric target. For groups, also reject `via: direct` or any receipt that does not identify media; this prevents an accidental private-message fallback. Never report a file sent from a timeout or a missing receipt. Do not use `openclaw message send --media <local-path>` or standalone `zca-js` for this case.

The helper is independent of the optional bounded `zca-js` acknowledgement guard. If the guard is changed, follow the backup, fixture test, syntax check, plugin doctor, probe, and Supervisor rollback procedure already documented above. The helper can be rolled back by restoring its timestamped member-workspace backup and does not require a Gateway restart.

## Permanent local-media hydration guard (2026-09-23)

For a member that previously passed `media=<local path>` with an empty `buffer`, install the reusable `zalo-buffer-file-send/scripts/patch_openclaw_buffer_hydration.sh`. The patch is intentionally narrow: in the OpenClaw `message-action-normalization-*` bundle, `message.send` hydrates a local media/file path into the bounded base64 buffer, filename, and content type before the Gateway Zalo plugin dispatches it. This prevents the old path from reaching `zca-js` without bytes. It does not bypass media access policy, size limits, or credentials.

Run the script's dry-run, apply it with the required member container, run `node --check`, then restart only the Supervisor-owned `openclaw-gateway`. The script stores the original bundle and SHA-256 under `/root/_Backups/<member>-zalo-buffer-hydration/<UTC-timestamp>/`. After an OpenClaw upgrade, rerun the dry-run because hashed bundle names and anchors can change. Rollback is file-level from that backup followed by the same gateway restart; stop if the live bundle hash no longer matches the backup baseline.

Acceptance requires one owner-approved attachment sent through the ordinary message action with a local media path, `deliveryStatus: sent`, a media receipt, and a matching user/group thread ID. Keep the buffer helper as the fallback and never claim success from text health, a queued request, or a timeout.

### Guard v2: stage the hydrated attachment (2026-09-23)

The first local-media guard set `buffer` but retained the original `media` path. That was insufficient for a Zalo plugin branch that prefers `mediaUrl`. The current portable patch is v2: it reads the local path with the normal media policy, validates the bounded base64, stages the bytes in the canonical outbound media store, and replaces `media`, `mediaUrl`, and `mediaUrls` with the staged path before dispatch. This closes the remaining path-specific upload timeout.
