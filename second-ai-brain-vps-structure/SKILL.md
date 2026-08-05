---
name: second-ai-brain-vps-structure
description: Set up, audit, or standardize a VPS "Second AI Brain" operating structure modeled after /root/_Second_AI_Brain, including START_HERE.md, VPS folder map, project registry, service notes, change log, production checklist, and safe working rules for Codex/AI agents. Use when moving to a new VPS, creating /root/_Second_AI_Brain, documenting projects, standardizing /root/Apps /root/Automation /root/Data /root/AI_Runtime /root/_Infra /root/_Backups /root/_Archive, or asking AI to follow this VPS documentation structure.
metadata:
  short-description: Chuẩn bộ não thứ hai cho VPS
---

# Second AI Brain VPS Structure

Use this skill when the user wants to create, copy, audit, or enforce a reusable VPS documentation structure like `/root/_Second_AI_Brain`.

## Core Rule

`/root/AGENTS.md` is the entrypoint that makes this structure enforceable for future Codex/AI sessions. It must exist at the VPS root and point agents to `_Second_AI_Brain` before any project edits.

Treat the Second AI Brain as the VPS operating manual for AI agents. Before changing projects, agents should read:

1. `/root/_Second_AI_Brain/START_HERE.md`
2. `/root/_Second_AI_Brain/01_Ban_Do_VPS.md`
3. `/root/_Second_AI_Brain/02_Danh_Sach_Project.md`
4. Relevant project note in `/root/_Second_AI_Brain/projects/` if it exists
5. `/root/_Second_AI_Brain/checklists/truoc_khi_sua_production.md` before production changes

Never copy real API keys, tokens, cookies, passwords, private keys, real browser profiles, or private credential files into the documentation or final answer.

## Standard VPS Folders

Create or preserve these root folders:

- `/root/_Second_AI_Brain` — AI operating manual, registry, checklists, history
- `/root/Apps` — websites, web apps, N8N, video factories, member apps
- `/root/Automation` — bots, crawlers, Selenium, social automation, scheduled scripts
- `/root/Data` — datasets, documents, second-brain content, synced data
- `/root/AI_Runtime` — AI runtime/workspace folders that are safe to manage
- `/root/_Infra` — nginx, cron, Docker, system notes and snapshots
- `/root/_Backups` — manual backups before risky edits
- `/root/_Archive` — old projects no longer active

Keep sensitive runtime folders such as `/root/.ssh`, `/root/.codex`, `/root/.agents`, and provider credential folders untouched unless the user explicitly asks.

## Required File Layout

Minimum structure:

```text
/root/AGENTS.md
/root/_Second_AI_Brain/
├── START_HERE.md
├── README.md
├── 00_overview.md
├── 01_Ban_Do_VPS.md
├── 02_Danh_Sach_Project.md
├── 03_Dich_Vu_Dang_Chay.md
├── 04_Lenh_Van_Hanh.md
├── 05_Canh_Bao_Bao_Mat.md
├── 06_Nhat_Ky_Thay_Doi.md
├── 07_Su_Co_Da_Gap.md
├── 08_Quy_Uoc_Lam_Viec.md
├── 09_Ke_Hoach_Chuan_Hoa_Folder.md
├── 10_ai_workflow.md
├── checklists/truoc_khi_sua_production.md
├── projects/
├── services/cron.md
├── services/docker.md
├── services/nginx.md
├── templates/project_profile.md
├── inventories/
└── backups/
```

Optional English aliases may exist (`01_folder_map.md`, `02_projects.md`, etc.), but Vietnamese names above are the canonical default.

## Workflow: Set Up On A New VPS

1. Inspect current folders with `find /root -maxdepth 2 -type d` and avoid printing secrets.
2. Create standard root folders and `_Second_AI_Brain` structure.
3. Generate the core files from `references/file_templates.md` or run `scripts/bootstrap_second_ai_brain.py`.
4. Populate `01_Ban_Do_VPS.md` with actual root groups and paths.
5. Populate `02_Danh_Sach_Project.md` with project path, status, and notes.
6. Record active services in `03_Dich_Vu_Dang_Chay.md` and `services/*.md` using sanitized output.
7. Add or update root `/root/AGENTS.md` from `references/file_templates.md` so future agents read `_Second_AI_Brain` before edits.
8. Append a dated entry to `06_Nhat_Ky_Thay_Doi.md`.

## Workflow: Audit Existing Structure

1. Check that required files/folders exist.
2. Verify project registry paths still exist or are marked archived/missing.
3. Check whether production projects have project notes in `projects/`.
4. Confirm production checklist exists before editing cron, nginx, Docker, websites, or automations.
5. Report gaps; do not move or delete production folders without explicit permission.

## Safety Rules

- Backup production config files to `/root/_Backups` before editing cron, nginx, Docker Compose, systemd, or payment/webhook configs.
- Do not expose `.env`, credential JSON, cookies, Chrome/Selenium profiles, SSH keys, or real tokens.
- Do not run live social posting, messaging, payment, destructive cleanup, or broad `rm -rf` commands unless explicitly requested.
- If a project has its own `AGENTS.md`, read it and follow the closest applicable instructions.
- After important changes, update `/root/_Second_AI_Brain/06_Nhat_Ky_Thay_Doi.md`.

## Bundled Resources

- `references/file_templates.md` — ready-to-use Markdown templates for `/root/AGENTS.md` and each required `_Second_AI_Brain` file.
- `scripts/bootstrap_second_ai_brain.py` — creates `/root/AGENTS.md` and the folder/file skeleton without overwriting existing files by default.

## Quick Commands

Create the skeleton on a VPS:

```bash
python3 /path/to/second-ai-brain-vps-structure/scripts/bootstrap_second_ai_brain.py --root /root
```

Preview without writing:

```bash
python3 /path/to/second-ai-brain-vps-structure/scripts/bootstrap_second_ai_brain.py --root /root --dry-run
```
