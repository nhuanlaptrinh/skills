---
name: professional-website-ui
description: Redesign and standardize polished, conversion-focused website interfaces for Django landing pages and course websites, with an intentional color system, expressive typography, accessible interactions, and responsive desktop/mobile layouts. Use when Codex needs to refresh a website's template, CSS, or frontend JavaScript without changing its business logic, or when a reusable UI treatment should be carried into another website.
---

# Professional Website UI

Use this skill to turn an existing Django website into a coherent visual system that feels deliberate on desktop and mobile. Preserve backend behavior, forms, routes, data, and credentials unless the user explicitly asks for a functional change.

## Scope and defaults

- Treat the existing website as the source of truth for content and behavior.
- Prefer editing the project template (`templates/**`) and source assets (`static/**`); do not hand-edit generated `staticfiles/**` unless the project's deployment process requires it.
- Use a small, named token set for colors, spacing, radii, shadows, and typography. Avoid appending contradictory override blocks or blanket selectors such as `body * { color: ... !important; }`.
- Choose one clear visual direction and keep it in a single token layer. The default for new course, business, and AI landing pages is the ALT light-teal theme described below; the deep ink/navy + cobalt/coral treatment remains an optional preset when an existing brand requires it.
- Use an expressive display face already approved by the project (for example Bricolage Grotesque) with a highly readable Vietnamese body face (for example Be Vietnam Pro). Do not add a font dependency without checking network/fallback behavior.
- Keep decorative motion purposeful and provide a `prefers-reduced-motion` path.

## Theme baseline: ALT light-teal

Use this light, high-contrast palette as the reusable baseline for ALT-style websites and as the first option when a project has no established brand colors. It is adapted from the visual language of `/root/Apps/course_websites/10Web_BH/28_domain_alt`.

```css
:root {
  --color-primary: #008577;
  --color-primary-strong: #006b61;
  --color-primary-support: #0f766e;
  --color-ink: #0f172a;
  --color-body: #334155;
  --color-text-secondary: #475569;
  --color-muted: #64748b;
  --color-surface: #ffffff;
  --color-surface-soft: #f8fbfc;
  --color-surface-mint: #e9fbf8;
  --color-border: #d9e6e4;
  --color-border-soft: #edf2f2;
  --color-info-surface: #e0f2fe;
  --color-info: #0369a1;
  --color-status-surface: #fff8d8;
  --color-status: #6b5b00;
}
```

Apply the tokens semantically: white header/cards and `--color-surface-soft` section bands, dark ink for headings, body/secondary text for copy, teal for links and primary actions, and mint only for supporting panels or highlights. Use white text on `--color-primary` or (preferably for dense labels) `--color-primary-strong`; never place white text on a pale mint surface. Keep yellow limited to status/attention states rather than primary actions.

The key combinations are intentionally readable: white on `#008577` is about `4.54:1`, white on `#006b61` about `6.41:1`, `#0f172a` on white about `17.85:1`, `#475569` on white about `7.58:1`, and `#64748b` on white about `4.76:1`. Check any new color pair with a contrast tool; target at least `4.5:1` for normal text and `3:1` for large text or UI boundaries. Keep a visible `:focus-visible` ring (for example `--color-primary-support`) with enough separation from the component surface.

Prefer explicit surface/component selectors such as `.site-header`, `.hero`, `.section`, `.card`, `.panel`, `.btn-primary`, `.btn-secondary`, `.status`, and `.note`. Do not force a palette with `body *`, broad `!important`, or a second override block that can recolor icons, form errors, or disabled controls unexpectedly. If a dark/cobalt preset is selected, swap the same semantic tokens in one place and retain the same contrast and focus requirements; do not mix two full presets ad hoc.

## Required preflight

Before editing a production project, read:

1. `/root/_Second_AI_Brain/START_HERE.md`
2. `/root/_Second_AI_Brain/01_Ban_Do_VPS.md`
3. `/root/_Second_AI_Brain/02_Danh_Sach_Project.md`
4. The matching note in `/root/_Second_AI_Brain/projects/`, when present
5. `/root/_Second_AI_Brain/checklists/truoc_khi_sua_production.md`
6. The nearest project `AGENTS.md`

Then inspect the template, source CSS/JS, routes/forms, Docker/compose commands, and current service status. Never print `.env`, database contents, API keys, cookies, tokens, passwords, or private keys.

## Workflow

### 1. Baseline and backup

Record the current URL, container/service, source files, and responsive breakpoints. Capture a desktop and a narrow mobile screenshot when Chromium is available:

```bash
chromium --headless --no-sandbox --disable-gpu --hide-scrollbars \
  --virtual-time-budget=2500 --window-size=1440,1100 \
  --screenshot=/tmp/site-desktop.png https://example.invalid/
chromium --headless --no-sandbox --disable-gpu --hide-scrollbars \
  --virtual-time-budget=2500 --window-size=390,844 \
  --screenshot=/tmp/site-mobile.png https://example.invalid/
```

Create a timestamped backup before changing production-facing UI files. Keep the backup outside the project, for example:

```bash
backup_dir="/root/_Backups/ui_<project>_<timestamp>"
mkdir -p "$backup_dir"
cp -p templates/website/home.html static/website/css/style.css static/website/js/site.js "$backup_dir/"
```

### 2. Design pass

- Map the page into a clear hierarchy: header, hero, proof/value, catalog or features, process, advisor/form, FAQ, final CTA, footer.
- Make the first viewport communicate who the site serves, the outcome, and one primary action. Keep the main interactive/demo panel visible on desktop where useful.
- Use alternating white, soft-gray, and pale-mint surfaces to create rhythm in the ALT preset; reserve a dark section for a deliberate emphasis band. Keep body copy at readable contrast and line length.
- Use grids with `minmax()`/`auto-fit` where appropriate, but choose explicit card widths when the composition needs editorial control.
- Make status pills, progress bars, buttons, inputs, FAQ disclosure, and hover/focus states visually distinct and keyboard accessible.
- Add a lightweight local favicon/brand mark when the project has no favicon, so the browser does not request a missing asset; keep it free of external tracking or secrets.

### 3. Implementation pass

- Consolidate the source stylesheet into one canonical token/theme layer and one responsive breakpoint strategy. Remove stale appended overrides that fight the design.
- Preserve Django template variables, CSRF fields, form names, URL tags, and existing data attributes.
- Add or retain: smooth anchor scrolling, an active navigation state, a mobile menu with `aria-expanded`/`aria-controls`, a visible mobile CTA, and a scroll-to-top control for long pages.
- Bind smooth scrolling with `scrollIntoView({ behavior: 'smooth' })` (falling back to `auto` for reduced motion), and close mobile navigation after selecting a link or pressing Escape.
- Reveal below-fold content with `IntersectionObserver`, but make the hero usable immediately so a delayed script cannot leave the first viewport blank.
- Keep JavaScript behavior progressive: if an observer or optional endpoint fails, content and forms must remain usable.
- Do not add authentication, payment, analytics, external API calls, or credentials merely as part of a visual redesign.

### 4. Dry-run validation

Run checks before restarting production:

```bash
python3 -m compileall -q config website
docker compose config >/tmp/<project>-compose-config.txt
docker compose run --rm web python manage.py check
docker compose run --rm web python manage.py test
node --check static/website/js/site.js
```

Inspect the rendered HTML for expected static URLs and form action/CSRF fields. If host Django dependencies are unavailable, run the Django checks inside the project container.

### 5. Apply and verify

Only apply a production restart when it is in the user's requested scope:

```bash
docker compose up -d --build
docker compose ps
docker compose logs --tail=120
curl -fsS -o /dev/null -w '%{http_code}\n' https://example.invalid/
curl -fsS https://example.invalid/healthz/
nginx -t
```

The container must remain bound to its existing loopback port; do not expose Django directly. If the project uses WhiteNoise or another asset manifest, let its normal `collectstatic` step regenerate hashed files. Re-capture desktop (1440px), tablet (~900px), and mobile (390px) screenshots after the restart and check for horizontal overflow, clipped text, low contrast, hidden hero content, unusable controls, and fixed CTA overlap.

### 6. Handoff and rollback

- Report exactly which source files changed, what was verified, and the backup location.
- Update `/root/_Second_AI_Brain/06_Nhat_Ky_Thay_Doi.md` after a material production change.
- If the new UI causes a regression, stop traffic-changing work and restore only the backed-up UI files, rebuild through the normal compose command, and re-run health/tests. Never delete unrelated project data.

## Reusable quality checklist

- Desktop first viewport shows headline, supporting copy, primary CTA, and the key visual/demo without excessive empty space.
- Mobile first viewport has readable type, full-width tap targets, a working menu, visible CTA text, and no horizontal scroll.
- Text colors are defined by component/surface rather than a global `!important` rule.
- ALT light-teal combinations meet readable contrast targets for headings, body copy, buttons, status labels, and focus indicators.
- Buttons and links have hover and `:focus-visible` states; form controls retain labels and error text.
- Accent colors communicate hierarchy instead of giving every card a competing neon color.
- Animations are subtle, do not block content, and stop or simplify under reduced motion.
- Existing backend tests, form submission, advisor/chat endpoint, health endpoint, and static asset delivery still work.
- Favicon and other referenced static assets return successfully; browser console has no unexpected errors.

## Project-specific example

The AIA reference implementation lives at `/root/Apps/course_websites/10Web_BH/36_domain_aia`:

- Template: `templates/website/home.html`
- Source CSS: `static/website/css/style.css`
- Source JS: `static/website/js/site.js`
- Production check: `docker compose run --rm web python manage.py check` and `docker compose run --rm web python manage.py test`
- Production URL: `https://aia.anhlaptrinh.vn/`

Use the reference only for layout and interaction patterns. Do not copy its `.env`, database, knowledge files, bridge settings, or any credential.
