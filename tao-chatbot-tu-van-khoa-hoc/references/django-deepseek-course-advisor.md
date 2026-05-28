# Django DeepSeek Course Advisor Pattern

Use this reference when implementing the chatbot in a Django website.

## Mode Selection

- **Single-course landing page:** keep `COURSE_FOLDERS` to the current course only, insert the advisor immediately before the registration form, and render chat + a compact course info panel. Do not add a broad course search UI unless requested.
- **Multi-course portal:** include all owner-approved courses, selected-course state, and searchable course cards.
- For both modes, the official registration URL must come from `12 - Dữ liệu làm website.../00 - Thông tin website và link đăng ký.md`; do not rely on a hardcoded URL map for link questions.

## Backend Shape

Create a `course_advisor` view and route it as:

```python
path('api/course-advisor/', views.course_advisor, name='course_advisor')
```

Use these imports:

```python
import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
```

Use this context-reading pattern. For a single-course page, keep only the current course in `COURSE_FOLDERS`; for a portal, include the approved course list:

```python
TRAINING_ROOT = Path('/root/Second_Brain/01Chuong_Trinh_Dao_Tao/01 - Chương trình đào tạo')

COURSE_FOLDERS = {
    '02_domain_tlai': '02_domain_tlai',
    '03_domain_oplw': '03_domain_oplw',
    '05_domain_vibepython': '05_domain_vibepython',
    '13_domain_fbs': '13_domain_fbs',
    '15_domain_tlzalo': '15_domain_tlzalo',
    '18_domain_opc': '18_domain_opc',
    '19_domain_ancl': '19_domain_ancl',
    '20_domain_anob': '20_domain_anob',
}

def _read_course_context(course_code):
    folder_name = COURSE_FOLDERS.get(course_code)
    if not folder_name:
        return ''

    course_dir = TRAINING_ROOT / folder_name
    if not course_dir.exists():
        return ''

    website_files = []
    for website_dir in sorted(course_dir.glob('12 - Dữ liệu làm website*')):
        if website_dir.is_dir():
            website_files.extend(sorted(website_dir.glob('*.md')))

    preferred_files = website_files + [
        course_dir / '01 - Tổng quan chương trình' / '00 - Tổng hợp - Tổng quan chương trình.md',
        course_dir / '02 - Lộ trình đào tạo' / '00 - Tổng hợp - Kích hoạt và onboarding.md',
        course_dir / '02 - Lộ trình đào tạo' / '00 - Tổng hợp - Lộ trình đào tạo.md',
        course_dir / '03 - Q&A và xử lý phản đối' / '00 - Tổng hợp - Q&A và xử lý phản đối.md',
        course_dir / '11 - Đối tượng khách hàng hướng tới' / '00 - Tổng hợp - Đối tượng khách hàng hướng tới.md',
    ]

    chunks = []
    for file_path in preferred_files:
        if file_path.exists():
            text = file_path.read_text(encoding='utf-8', errors='ignore').strip()
            if text:
                chunks.append(f'## {file_path.name}\n{text[:5000]}')

    return '\n\n'.join(chunks)[:16000]
```

Prompt rule:

```python
prompt = (
    'Bạn là trợ lý tư vấn khóa học của Anh Lập Trình. '
    'Chỉ tư vấn dựa trên dữ liệu chương trình được cung cấp, không bịa thêm khóa học ngoài danh sách. '
    'Trả lời tiếng Việt, thực tế, ngắn gọn, giọng tư vấn thân thiện. '
    'Không dùng Markdown, không dùng dấu ** để in đậm, không dùng ký hiệu heading #. '
    'Nêu: khóa phù hợp, ai nên học, học xong làm được gì, bước tiếp theo. '
    'Nếu khách hỏi link, website, đăng ký, trang học hoặc cách vào khóa, hãy tìm URL trong dữ liệu chương trình và đưa đúng URL đó.\n\n'
    f'Khóa đang chọn: {course_title} ({course_code})\n'
    f'Câu hỏi/nhu cầu khách hàng: {question or "Khách hàng vừa chọn khóa học."}\n\n'
    f'Dữ liệu chương trình:\n{course_context}'
)
```

Do not put `DEEPSEEK_API_KEY` in this file. Read it from `os.environ`.

Clean AI answers before returning them to the frontend or Telegram. This prevents raw Markdown markers like `**` from appearing in plain-text chat UIs:

```python
def _clean_chatbot_answer(text):
    cleaned = str(text or '').strip()
    cleaned = re.sub(r'^\s{0,3}#{1,6}\s*', '', cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r'(\*\*|__)(.*?)\1', r'\2', cleaned, flags=re.DOTALL)
    cleaned = re.sub(r'`{1,3}([^`]*)`{1,3}', r'\1', cleaned, flags=re.DOTALL)
    cleaned = cleaned.replace('**', '').replace('__', '').replace('`', '')
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
    return cleaned.strip()
```

Use it after receiving the model response:

```python
answer = _clean_chatbot_answer(data.get('choices', [{}])[0].get('message', {}).get('content', ''))
```

If the project already uses `requests`, it is fine to call DeepSeek with `requests.post(...)` instead of `urllib.request`; keep the same payload, timeout, and environment-variable secret handling.

## Markdown Link File

For each course, create:

`12 - Dữ liệu làm website <domain>/00 - Thông tin website và link đăng ký.md`

Template:

```markdown
# Thông tin website và link đăng ký

- Mã chương trình: `20_domain_anob`
- Tên chương trình: Bộ Não AI Cá Nhân: Obsidian x Antigravity
- Website đăng ký chính thức: https://anob.anhlaptrinh.vn/
- Link tư vấn/đăng ký nên gửi cho khách khi hỏi website, link, trang đăng ký hoặc cách vào học: https://anob.anhlaptrinh.vn/

Khi khách hỏi xin link website hoặc link đăng ký của chương trình này, trả lời đúng link chính thức ở trên.
```

## Frontend Contract

The JS should call:

```js
fetch('/api/course-advisor/', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    course_code: course.code,
    course_title: course.title,
    question
  })
})
```

Include:

- loading message while waiting
- Enter-to-submit
- send button
- fallback error message
- cache-busting query string after static file edits

If Telegram notification is requested, add a boolean flag only on real customer-submitted questions:

```js
body: JSON.stringify({
  course_code: course.code,
  course_title: course.title,
  question,
  notify_telegram: true
})
```

Do not set `notify_telegram: true` for page load, initial greeting, or course selection auto-replies unless the user explicitly wants every interaction sent.

Single-course landing page placement:

```html
<!-- Course Advisor Section -->
<section class="course-advisor-section" id="tu-van">
  <div class="container">
    <div class="advisor-layout" data-course-advisor>
      <div class="advisor-chat">
        <div data-advisor-selected></div>
        <div data-advisor-messages aria-live="polite"></div>
        <div data-advisor-chips></div>
        <form data-advisor-form>
          <input type="text" data-advisor-input autocomplete="off">
          <button type="submit" aria-label="Gửi câu hỏi">Gửi</button>
        </form>
      </div>
      <aside data-course-list></aside>
    </div>
  </div>
</section>
```

Put this block immediately before the existing registration section/form. Keep class names compatible with the target CSS style; do not create an unrelated visual theme.

## Docker Compose

Use:

```yaml
env_file:
  - .env
volumes:
  - .:/app
  - "/root/Second_Brain/01Chuong_Trinh_Dao_Tao/01 - Chương trình đào tạo:/root/Second_Brain/01Chuong_Trinh_Dao_Tao/01 - Chương trình đào tạo:ro"
```

Use `.env.example`:

```env
DEEPSEEK_API_KEY=Nhap_API_Cua_Ban
DEEPSEEK_MODEL=deepseek-chat
TELEGRAM_BOT_TOKEN=Nhap_API_Cua_Ban
TELEGRAM_CHAT_ID=Nhap_Gia_Tri_Cua_Ban
PROJECT_FOLDER_NAME=ten_folder_du_an
PROJECT_PUBLIC_URL=https://example.anhlaptrinh.vn/
```

If a sibling project already has a working local `.env`, you may copy it on the VPS for runtime only. Keep `.env` ignored and never print or commit real values.

After changing `env_file` or volumes, recreate the service:

```bash
docker compose up -d --force-recreate <service-name>
```

## Optional Telegram Notification

Only implement this section when the user asks to notify Telegram from chatbot conversations.

Environment variables:

```env
TELEGRAM_BOT_TOKEN=Nhap_API_Cua_Ban
TELEGRAM_CHAT_ID=Nhap_Gia_Tri_Cua_Ban
PROJECT_FOLDER_NAME=28_domain_alt
PROJECT_PUBLIC_URL=https://alt.anhlaptrinh.vn/
```

Backend behavior:

- After DeepSeek returns an answer, send one Telegram message containing: project folder name, website URL, selected course, customer question, and chatbot answer.
- Return `telegram_notified: true` when Telegram accepts the message; otherwise return `false` without breaking the chatbot response.
- Keep the Telegram call best-effort. Telegram failures should not make `/api/course-advisor/` fail for the customer.
- Truncate the Telegram text to stay below Telegram message limits.
- If `TELEGRAM_CHAT_ID` is empty, it is acceptable to try `getUpdates` to find the latest chat, but the reliable fix is to ask the user to send `/start` to the bot and set `TELEGRAM_CHAT_ID`.

Minimal helper shape:

```python
TELEGRAM_MAX_MESSAGE_LENGTH = 3900
PROJECT_FOLDER_NAME = os.environ.get('PROJECT_FOLDER_NAME', 'ten_folder_du_an').strip() or 'ten_folder_du_an'
PROJECT_PUBLIC_URL = os.environ.get('PROJECT_PUBLIC_URL', '').strip()

def _truncate_for_telegram(text, max_length=TELEGRAM_MAX_MESSAGE_LENGTH):
    if len(text) <= max_length:
        return text
    return f'{text[:max_length - 120].rstrip()}\n\n... [noi dung da rut gon de gui Telegram]'

def _send_telegram_advisor_notice(course_code, course_title, question, answer):
    bot_token = os.environ.get('TELEGRAM_BOT_TOKEN', '').strip()
    chat_id = os.environ.get('TELEGRAM_CHAT_ID', '').strip()
    if not bot_token or not chat_id:
        return False

    text = (
        'Chatbot tu van co cau hoi moi\n'
        f'Du an: {PROJECT_FOLDER_NAME}\n'
        f'Website: {PROJECT_PUBLIC_URL}\n'
        f'Khoa dang tu van: {course_title or course_code} ({course_code})\n\n'
        f'Cau hoi cua khach:\n{question or "(trong)"}\n\n'
        f'Cau tra loi cua chatbot:\n{answer or "(trong)"}'
    )
    payload = json.dumps({
        'chat_id': chat_id,
        'text': _truncate_for_telegram(text),
        'disable_web_page_preview': True,
    }).encode('utf-8')
    req = urllib.request.Request(
        f'https://api.telegram.org/bot{bot_token}/sendMessage',
        data=payload,
        headers={'Content-Type': 'application/json'},
        method='POST',
    )

    try:
        with urllib.request.urlopen(req, timeout=8):
            return True
    except (urllib.error.URLError, TimeoutError):
        return False
```

In `course_advisor`, read the optional flag and call the helper after `answer` is created:

```python
should_notify_telegram = bool(payload.get('notify_telegram'))

telegram_notified = False
if should_notify_telegram:
    telegram_notified = _send_telegram_advisor_notice(course_code, course_title, question, answer)

return JsonResponse({
    'configured': True,
    'answer': answer,
    'telegram_notified': telegram_notified,
})
```

Troubleshooting:

```bash
# Confirm local .env has the values without printing secrets.
python3 - <<'PY'
from pathlib import Path
p = Path('.env')
for key in ['TELEGRAM_BOT_TOKEN', 'TELEGRAM_CHAT_ID', 'PROJECT_FOLDER_NAME', 'PROJECT_PUBLIC_URL']:
    value = ''
    for line in p.read_text(errors='ignore').splitlines():
        if line.startswith(key + '='):
            value = line.split('=', 1)[1].strip()
    print(f'{key}=' + ('set' if value else 'empty'))
PY

# Confirm Docker actually received .env after service recreation.
docker exec <container-name> sh -c 'for k in TELEGRAM_BOT_TOKEN TELEGRAM_CHAT_ID PROJECT_FOLDER_NAME PROJECT_PUBLIC_URL; do v=$(printenv "$k"); if [ -n "$v" ]; then echo "$k=set"; else echo "$k=empty"; fi; done'
```

If local direct Telegram send works but the chatbot says `telegram_notified: false`, recreate the service:

```bash
docker compose up -d --force-recreate <service-name>
```

## Verification Commands

```bash
python3 manage.py check
docker compose config --quiet
curl -sS -X POST https://example.anhlaptrinh.vn/api/course-advisor/ \
  -H 'Content-Type: application/json' \
  --data '{"course_code":"02_domain_tlai","course_title":"Tạo Trợ Lý AI Cá Nhân Hóa","question":"cho tôi xin link đăng ký"}'
curl -sS -X POST https://example.anhlaptrinh.vn/api/course-advisor/ \
  -H 'Content-Type: application/json' \
  --data '{"course_code":"02_domain_tlai","course_title":"Tạo Trợ Lý AI Cá Nhân Hóa","question":"test telegram","notify_telegram":true}'
curl -sS https://example.anhlaptrinh.vn/ | rg -n "course-advisor-section|data-course-advisor|registrationForm"
```

The advisor line number should be before the registration form line number.
