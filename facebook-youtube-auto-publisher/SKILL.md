---
name: facebook-youtube-auto-publisher
description: Operate, configure, install, verify, pause, resume, or repair the standalone Linux VPS publisher that reads PD rows from Google Sheet, queues them in SQLite, posts independently to a Facebook Fanpage and YouTube, and writes statuses back to the source row. Use when the user asks OpenClaw to publish the next Sheet item, inspect or sync the social Sheet/queue, retry one failed platform, run a dry-run, check Facebook/YouTube/Google Sheets connectivity, or manage the facebook_youtube_auto_publisher systemd service.
---

# Facebook YouTube Auto Publisher

## Resolve The Project

Read the project path from:

```text
~/.config/facebook-youtube-auto-publisher/project_path
```

If the marker is missing, check:

```text
/root/Automation/social_publisher/facebook_youtube_auto_publisher
./facebook_youtube_auto_publisher
```

Require `manage.sh`, `.env.example`, and `app/cli.py`. Never print or return `.env` contents.

## Preflight

Run from the project root:

```bash
./manage.sh status
./manage.sh check
```

Use `./manage.sh check --online` only when the user asks to verify credentials or installation. It performs read-only checks for Facebook, YouTube, and the configured Google Sheet.

If installation is requested:

```bash
bash setup_and_start.sh
```

The installer creates the venv, verifies API connections, installs this skill, creates the systemd service, and leaves the scheduler paused. If `OPENCLAW_WORKSPACE` is blank, it installs the skill into every standard OpenClaw workspace already present.

## Read The Source Sheet

Use the original five-column schema:

| Column | Header | Meaning |
|---|---|---|
| A | `Tiêu Đề` | Facebook text first line and YouTube title |
| B | `Ebook` or `Nội Dung` | Text appended after the title |
| C | `Hình ảnh Hoặc Video` | Filename in `media/` or absolute VPS path |
| D | `Status` | `PD` requests Facebook |
| E | `Youtube status` | `PD` requests YouTube |

Use `PD` only for platforms the user wants to publish. Facebook accepts text, image, or video. YouTube requires a supported video.

When the user says to publish the next Sheet item, do not ask for title, caption, or media path again. Read the first eligible `PD` row:

```bash
./manage.sh sheet-sync
```

The default import limit is one source row per Sheet sync. The background service also syncs automatically while `DRY_RUN=false` and the scheduler is not paused.

`run-once` respects `PAUSED=true` and processes the oldest due SQLite job, which may be older than the row just imported. Before a one-shot request, inspect `list` and the job ID returned by `sheet-sync`; preserve FIFO order and never claim that the newly imported row was posted unless its own job status changed. Do not pause immediately before `run-once`. If the scheduler was already paused, resume only after explicit real-post authorization and restore the prior pause state after the requested work.

## Dry Run And Activation

Preview the first `PD` row without creating a job or changing the Sheet:

```bash
./manage.sh sheet-sync --dry-run
./manage.sh run-once --dry-run
```

Treat `DRY_RUN=true` or `PAUSED=true` as a safety stop. Do not edit `.env`, change `DRY_RUN`, or resume unless the user clearly requests real posting.

When real posting is authorized and `.env` is configured:

```bash
systemctl restart facebook-youtube-auto-publisher
./manage.sh resume
```

Never create a real test post merely to verify installation.

## Sheet Status Rules

The project writes platform statuses independently:

- `PD`: requested by the user in Google Sheet.
- `QUEUED`: stored safely in SQLite.
- `PROCESSING`: API upload/post is running.
- `POSTED`: platform succeeded.
- `ERROR`: platform failed; inspect the job/log before retrying.
- `CANCELED`: pending work was canceled.

Never reset a `POSTED` platform to pending automatically. If a posted row is changed back to `PD`, sync the Sheet back to `POSTED` without posting again. To intentionally publish the same content again, require a new duplicated Sheet row.

To retry a failed Sheet platform, either set its status cell from `ERROR` to `PD` or run:

```bash
./manage.sh retry JOB_ID --platform facebook
./manage.sh retry JOB_ID --platform youtube
```

Do not reset `PROCESSING` automatically. First inspect the platform manually, then use `--force-processing` only after confirming no post was created.

## Inspect And Control

```bash
./manage.sh list --limit 20
./manage.sh list --status ERROR
./manage.sh show JOB_ID
./manage.sh status
./manage.sh pause
./manage.sh resume
systemctl status facebook-youtube-auto-publisher --no-pager
```

Use `cancel JOB_ID` only for pending or failed work:

```bash
./manage.sh cancel JOB_ID
```

Manual `./manage.sh add` remains available only when the user explicitly wants a post outside Google Sheet.

## OAuth And Inputs

- Set `GOOGLE_SHEETS_SPREADSHEET_ID` and `GOOGLE_SHEETS_WORKSHEET_NAME` in `.env`.
- Reuse the YouTube OAuth Client and Refresh Token by leaving `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET`, and `GOOGLE_OAUTH_REFRESH_TOKEN` blank.
- Require the Refresh Token scopes `youtube.upload`, `youtube.readonly`, and `spreadsheets`.
- Store media in `media/` or use an absolute path in Sheet column C.
- Keep queue data in `data/publish_queue.db` and redacted logs in `logs/publisher.log`.

## Safety

- Never reveal `.env`, Facebook tokens, OAuth secrets, Refresh Tokens, Telegram tokens, or private Sheet data.
- Never write credentials or real Sheet IDs into the bundled skill, docs, tests, or ZIP.
- Keep Facebook and YouTube results independent; never retry a platform already `POSTED`.
- Keep `DRY_RUN=true` during setup and diagnostics.
- Never edit the old production uploaders or orchestrator while operating this standalone package.
- Before sharing, run `bash scripts/package_release.sh` and confirm the ZIP contains no `.env`, database, logs, media, token, or credential files.
