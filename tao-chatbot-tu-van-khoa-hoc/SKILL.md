---
name: tao-chatbot-tu-van-khoa-hoc
description: Create or adapt a course-advisor chatbot for Anh Lap Trinh websites, including multi-course portals and single-course landing pages. Use when Codex needs to add a chatbot before a registration form, connect it to DeepSeek, read course knowledge from /root/Second_Brain/01_chuong_trinh_dao_tao, optionally notify Telegram when requested, or reuse the preferred advisor UI pattern from /root/10Web_BH/05_domain_vibepython, /root/10Web_BH/19_domain_ancl, /root/10Web_BH/28_domain_alt, or an existing course site.
---

# Tao Chatbot Tu Van Khoa Hoc

## Goal

Build a reusable website chatbot for Anh Lập Trình course sites:

- Multi-course portal like `alt.anhlaptrinh.vn`: selected-course advisor, searchable course list, and backend API.
- Single-course landing page like `tlai.anhlaptrinh.vn`: compact advisor for one course, usually inserted directly before the registration form.

The backend answers from markdown knowledge in:

`/root/Second_Brain/01_chuong_trinh_dao_tao`

The chatbot must not hardcode API keys or invent course links. It should read website/register links from markdown in each course folder, especially `01_du_lieu_website_chatbot...`.

## Default Architecture

Use this pattern unless the target project clearly uses another stack:

- Frontend: HTML/CSS/JS in the target app, matching existing design.
- Backend: Django endpoint `/api/course-advisor/`.
- AI provider: DeepSeek chat completions.
- Secrets: `.env` only, never JS/HTML.
- Knowledge source: markdown files under the course folder in `Second_Brain`.

## Preferred Advisor UI Pattern

Default to the chatbot interface used by `05_domain_vibepython` and `19_domain_ancl` unless the target site already has a stronger local design:

- Section id: use `id="course-advisor"` for single-course sites, or the site's existing advisor anchor if already established.
- Top heading: centered `advisor-heading` with a rounded `advisor-kicker` containing the Font Awesome comments icon and text `Chatbot tư vấn`.
- Main layout: `advisor-layout` two-column grid on desktop, chat card left and compact course panel right; stack to one column on mobile.
- Chat card structure: `advisor-chat`, `advisor-chat-header`, `advisor-agent`, circular `advisor-avatar` with robot icon, status dot, `advisor-small` text `Vướng đâu gỡ đó`.
- Selected course box: `advisor-selected` with `advisor-selected-top`, label `Đang tư vấn`, course code, and course title.
- Conversation area: `advisor-messages` using `advisor-message-bot` and `advisor-message-user`; bot answers may render line breaks, but sanitize Markdown markers before display.
- Quick chips: `advisor-chip-row` with rounded `advisor-chip` buttons. Default chips: `Học phí bao nhiêu?`, `Người không biết code học được không?`, `Học xong làm được gì?`, `Cho tôi xin link đăng ký`.
- Input row: `advisor-form`, rounded text input placeholder `Nhập câu hỏi của anh/chị...`, circular green submit button with Font Awesome paper-plane icon.
- Course panel: `advisor-course-panel`, `advisor-panel-heading`, and one or more `advisor-course-item` cards with number badge, `tag · level`, title, short description, and outcome.
- Loading state: `advisor-typing` text `Đang kiểm tra dữ liệu chương trình...` with animated dots.
- Floating CTA: if the site has a sticky/floating register button, hide or disable it while `course-advisor` or the registration section is in view so it does not cover the chat UI.
- Static cache: after editing static JS/CSS, update cache busting, e.g. `?v=YYYYMMDD-advisor-ui`.

For a concrete source, inspect:

- `/root/10Web_BH/05_domain_vibepython/vibepython/templates/vibepython/index.html`
- `/root/10Web_BH/05_domain_vibepython/vibepython/static/vibepython/css/style.css`
- `/root/10Web_BH/05_domain_vibepython/vibepython/static/vibepython/js/script.js`
- `/root/10Web_BH/19_domain_ancl/trolyai/templates/trolyai/index.html`

If the target is not Django, keep the same frontend/backend contract:

```json
{
  "course_code": "20_domain_anob",
  "course_title": "Bộ Não AI Cá Nhân: Obsidian x Antigravity",
  "question": "cho tôi xin link website"
}
```

## Workflow

1. Inspect the target website structure.
   - Identify template/static JS/CSS files.
   - Identify Docker Compose or server startup.
   - Check whether there are separate root static files and Django static files; update both if the project uses both.
   - Find the registration form/section id. If the user says "trước phần nhập thông tin đăng ký", insert the chatbot immediately before that form section.

2. Choose the chatbot mode.
   - **Single-course page:** use one course only, matching the current website/domain, with no search box unless the page naturally needs it.
   - **Multi-course portal:** use only courses requested by the website owner and include a searchable course list.
   - Each course object needs `code`, `title`, `tag`, `level`, `tools`, `url`, `short`, `fit`, `outcome`, and `keywords`.
   - Match `code` to a folder under the training root, e.g. `02_domain_tlai` or `20_domain_anob`.

3. Put website, registration, and fanpage-training knowledge in one markdown folder.
   - For each course, ensure a single canonical folder like `01_du_lieu_website_chatbot_<domain>` exists.
   - Add or update `03_du_lieu_chatbot_tu_van.md`; include company/program details, FAQ, voice rules, handoff rules, and the official website/register link there.
   - Add or update `04_du_lieu_lam_website.md`; include website/register link, offer, price, CTA, benefits, audience, and public website copy there.
   - If the markdown link conflicts with the live domain in Docker/Traefik, update both `03_du_lieu_chatbot_tu_van.md` and `04_du_lieu_lam_website.md` so link questions return the real website.
   - If Fanpage AI import data is needed, keep `01_du_lieu_nap_ai_fanpage.csv` and a matching readable `02_du_lieu_nap_ai_fanpage.xlsx` in the same folder.
   - Do not depend on backend hardcoded URL maps for links.

4. Build the backend endpoint.
   - Read `DEEPSEEK_API_KEY` and optional `DEEPSEEK_MODEL` from environment.
   - Validate `course_code` against allowed course folders.
   - Read course markdown context in this order:
     1. all `*.md` files recursively inside `01_du_lieu_website_chatbot*`
     2. `01_tong_quan_chuong_trinh/00_tong_hop_tong_quan_chuong_trinh.md`
     3. `02_lo_trinh_dao_tao/00_tong_hop_kich_hoat_va_onboarding.md`
     4. `02_lo_trinh_dao_tao/00_tong_hop_lo_trinh_dao_tao.md`
     5. `03_q_a_va_xu_ly_phan_doi/00_tong_hop_q_a_va_xu_ly_phan_doi.md`
     6. `11_doi_tuong_khach_hang_huong_toi/00_tong_hop_doi_tuong_khach_hang_huong_toi.md`
   - Tell the model: only use supplied program data; if asked for website/link/register, find the URL in the program data.
   - Tell the model not to use Markdown formatting such as `**bold**`, backticks, or heading `#`.
   - Add a small backend cleanup step that strips common Markdown markers from AI answers before returning JSON or sending Telegram, so raw `**` never appears to customers.

5. Build the frontend.
   - Keep the advisor useful as the first visible experience when requested.
   - Use a two-column desktop layout: chat on the left, course list/info panel on the right, unless the user asks otherwise.
   - For single-course landing pages, put chat on the left and a compact "khóa đang tư vấn" panel on the right.
   - On mobile, stack cleanly without horizontal overflow.
   - Show a visible loading state while DeepSeek answers.
   - Support both Enter and the send button.
   - If AI fails, show a helpful fallback, not silence.
   - Keep selected-course header compact so the answer area has room.
   - Add cache-busting query strings after static CSS/JS edits, e.g. `?v=YYYYMMDD-advisor`.

6. Optional Telegram notification.
   - Only add Telegram notification when the user explicitly asks for it.
   - Keep `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `PROJECT_FOLDER_NAME`, and `PROJECT_PUBLIC_URL` in `.env`; use placeholders in `.env.example`.
   - Send the project folder name, website URL, selected course, customer question, and chatbot answer.
   - Trigger Telegram only for real customer-submitted questions. Avoid sending notifications for initial greetings, page load, or merely selecting a course unless the user specifically wants that.
   - If the user provides a real bot token in chat, put it only in local `.env`, never in code, JS, templates, skill files, or docs. Mention that rotating the token is best practice if the project may be shared.
   - When `.env` changes in Docker, recreate the service so the container receives new env vars.
   - For Django implementation details, read `references/django-deepseek-course-advisor.md` and use the "Optional Telegram Notification" section.

7. Configure deployment.
   - Add `.env.example` with placeholders only.
   - Add `.gitignore` entries for `.env`, `.env.*`, logs, caches, tokens, secrets.
   - In Docker Compose, use `env_file: .env`.
   - If running inside Docker, mount the training root read-only so backend can read markdown.
   - If another local project already has a valid `.env`, it is okay to copy it locally on the server, but never print, commit, or place the real key in skill files/templates/JS.
   - Recreate/restart the running service after adding `env_file` or volumes, e.g. `docker compose up -d --force-recreate <service>`.

8. Verify.
   - Run framework checks, e.g. `python3 manage.py check`.
   - Run `docker compose config --quiet` if Compose changed.
   - Test endpoint locally and on the domain with a link question, e.g.:
     `course_code=02_domain_tlai`, question `cho tôi xin link đăng ký`.
   - Confirm answer contains the link from markdown.
   - If Telegram notification was added, verify direct Telegram send first, then verify `/api/course-advisor/` returns `telegram_notified: true` when called with `notify_telegram: true`.
   - If Telegram works outside Docker but not through the website, check env values inside the container and recreate the service after `.env` changes.
   - `curl` the public page and confirm the advisor block appears before the registration form.
   - Confirm static CSS/JS URLs return 200 after cache-busting.
   - Scan for secrets before final response.

## Security Rules

- Never put real API keys in JS, HTML, templates, committed files, or skill files.
- Use `DEEPSEEK_API_KEY=Nhap_API_Cua_Ban` in examples.
- Keep real `.env` local and ignored.
- If the user pasted a real key in chat, warn that rotating the key is best practice.

## References

- For a Django implementation pattern and reusable snippets, read `references/django-deepseek-course-advisor.md`.
