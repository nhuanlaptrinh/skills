#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT=""
PROFILE_DIR=""
DOMAIN=""
URL_PATH="/zalo-login/"
UPSTREAM_PORT="18790"
DEBUG_PORT="9223"
REFRESH_SECONDS="5"
DISPLAY_NUM="98"
SERVICE_NAME=""
CHROME_BIN=""

usage() {
  cat <<USAGE
Usage: $0 --project-root DIR --profile-dir DIR --domain DOMAIN [options]

Options:
  --path PATH                  Public URL path, default /zalo-login/
  --upstream-port PORT         Local QR server port, default 18790
  --debug-port PORT            Chrome DevTools port, default 9223
  --refresh-seconds SECONDS    Page/screenshot refresh interval, default 5
  --display-num NUM            Xvfb display number, default 98
  --service-name NAME          systemd service name, default zalo-web-qr-<domain>
  --chrome-bin PATH            Chrome binary path
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --project-root) PROJECT_ROOT="$2"; shift 2 ;;
    --profile-dir) PROFILE_DIR="$2"; shift 2 ;;
    --domain) DOMAIN="$2"; shift 2 ;;
    --path) URL_PATH="$2"; shift 2 ;;
    --upstream-port) UPSTREAM_PORT="$2"; shift 2 ;;
    --debug-port) DEBUG_PORT="$2"; shift 2 ;;
    --refresh-seconds) REFRESH_SECONDS="$2"; shift 2 ;;
    --display-num) DISPLAY_NUM="$2"; shift 2 ;;
    --service-name) SERVICE_NAME="$2"; shift 2 ;;
    --chrome-bin) CHROME_BIN="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
done

if [[ -z "$PROJECT_ROOT" || -z "$PROFILE_DIR" || -z "$DOMAIN" ]]; then
  usage >&2
  exit 2
fi

PROJECT_ROOT="$(readlink -f "$PROJECT_ROOT")"
PROFILE_DIR="$(readlink -f "$PROFILE_DIR")"
URL_PATH="/${URL_PATH#/}"
[[ "$URL_PATH" == */ ]] || URL_PATH="$URL_PATH/"
SAFE_PATH="${URL_PATH#/}"
SAFE_PATH="${SAFE_PATH%/}"
SAFE_NAME="$(echo "$DOMAIN-$SAFE_PATH" | tr -c 'A-Za-z0-9_' '-')"
SERVICE_NAME="${SERVICE_NAME:-zalo-web-qr-$SAFE_NAME}"
PUBLIC_DIR="/var/www/html/$SAFE_PATH"
BACKUP_DIR="/root/_Backups/zalo_web_qr_$(date +%Y%m%d_%H%M%S)"
NGINX_SITE="/etc/nginx/sites-available/$DOMAIN"

if [[ ! -d "$PROJECT_ROOT" ]]; then echo "PROJECT_ROOT not found: $PROJECT_ROOT" >&2; exit 1; fi
if [[ ! -d "$PROFILE_DIR" ]]; then echo "PROFILE_DIR not found: $PROFILE_DIR" >&2; exit 1; fi
if [[ ! -f "$NGINX_SITE" ]]; then echo "Nginx site not found: $NGINX_SITE" >&2; exit 1; fi
if ss -ltn | awk '{print $4}' | grep -q ":$UPSTREAM_PORT$"; then echo "Port already in use: $UPSTREAM_PORT" >&2; exit 1; fi

mkdir -p "$BACKUP_DIR" "$PROJECT_ROOT/script" "$PUBLIC_DIR"
cp -a "$NGINX_SITE" "$BACKUP_DIR/"
[[ -f "/etc/systemd/system/$SERVICE_NAME.service" ]] && cp -a "/etc/systemd/system/$SERVICE_NAME.service" "$BACKUP_DIR/"

cat > "$PROJECT_ROOT/script/zalo_web_qr_server.py" <<PY
#!/usr/bin/env python3
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse
import html
import subprocess
import time

PROJECT_ROOT = Path('$PROJECT_ROOT')
PUBLIC_DIR = Path('$PUBLIC_DIR')
URL_PATH = '$URL_PATH'
WORKER = PROJECT_ROOT / 'script' / 'start_zalo_web_qr_worker.sh'
PID_FILE = PROJECT_ROOT / 'zalo_web_qr_worker.pid'
SCREEN_FILE = PUBLIC_DIR / 'screen.png'
STATUS_FILE = PUBLIC_DIR / 'status.txt'
REFRESH_SECONDS = $REFRESH_SECONDS

PUBLIC_DIR.mkdir(parents=True, exist_ok=True)

def worker_running():
    try:
        pid = int(PID_FILE.read_text().strip())
    except Exception:
        return False
    return Path(f'/proc/{pid}').exists()

def start_worker():
    if worker_running():
        return
    subprocess.Popen(
        ['nohup', str(WORKER)],
        cwd=str(PROJECT_ROOT),
        stdout=open(PROJECT_ROOT / 'zalo_web_qr_worker.out', 'ab'),
        stderr=open(PROJECT_ROOT / 'zalo_web_qr_worker.err', 'ab'),
        start_new_session=True,
    )

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        with open(PROJECT_ROOT / 'zalo_web_qr_server.log', 'a', encoding='utf-8') as log:
            log.write('%s - %s\\n' % (time.strftime('%Y-%m-%dT%H:%M:%S'), fmt % args))

    def valid_path(self, parsed):
        return parsed.path.startswith(URL_PATH)

    def do_GET(self):
        parsed = urlparse(self.path)
        if not self.valid_path(parsed):
            self.send_response(404); self.end_headers(); return
        if parsed.path.endswith('/screen.png'):
            return self.serve_screen()
        if parsed.path.endswith('/status.txt'):
            return self.serve_text(STATUS_FILE)
        start_worker()
        return self.serve_page()

    def do_HEAD(self):
        parsed = urlparse(self.path)
        self.send_response(200 if self.valid_path(parsed) else 404)
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
        self.end_headers()

    def serve_text(self, path):
        text = path.read_text(encoding='utf-8') if path.exists() else 'Dang khoi dong...'
        data = text.encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'text/plain; charset=utf-8')
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def serve_screen(self):
        if not SCREEN_FILE.exists():
            return self.serve_svg_placeholder()
        data = SCREEN_FILE.read_bytes()
        self.send_response(200)
        self.send_header('Content-Type', 'image/png')
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def serve_svg_placeholder(self):
        svg = '<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="900"><rect width="100%" height="100%" fill="#0f172a"/><text x="50%" y="48%" dominant-baseline="middle" text-anchor="middle" fill="#fff" font-family="Arial" font-size="36">Dang mo Zalo QR...</text></svg>'.encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'image/svg+xml; charset=utf-8')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Length', str(len(svg)))
        self.end_headers()
        self.wfile.write(svg)

    def serve_page(self):
        status = STATUS_FILE.read_text(encoding='utf-8') if STATUS_FILE.exists() else 'Dang khoi dong Chrome Zalo QR...'
        body = f'''<!doctype html><html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="refresh" content="{REFRESH_SECONDS}"><title>Zalo Automation QR</title><style>body{{margin:0;font-family:Arial,sans-serif;background:#0f172a;color:#e5e7eb}}.wrap{{max-width:980px;margin:0 auto;padding:24px}}.card{{background:#111827;border:1px solid #334155;border-radius:18px;padding:18px;box-shadow:0 10px 30px #0005}}img{{width:100%;border-radius:12px;background:#020617}}.status{{color:#93c5fd;margin:10px 0 16px;white-space:pre-wrap}}.hint{{color:#cbd5e1;line-height:1.5}}</style></head><body><div class="wrap"><h1>Zalo Automation Login QR</h1><div class="card"><div class="status">{html.escape(status)}</div><img src="{URL_PATH}screen.png?t={int(time.time())}" alt="Zalo QR screen"><p class="hint">Mo app Zalo tren dien thoai va quet QR. Trang tu lam moi moi {REFRESH_SECONDS} giay.</p></div></div></body></html>'''
        data = body.encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

if __name__ == '__main__':
    ThreadingHTTPServer(('127.0.0.1', $UPSTREAM_PORT), Handler).serve_forever()
PY
chmod +x "$PROJECT_ROOT/script/zalo_web_qr_server.py"

cat > "$PROJECT_ROOT/script/start_zalo_web_qr_worker.sh" <<SH
#!/usr/bin/env bash
set -euo pipefail
PROJECT_ROOT="$PROJECT_ROOT"
PROFILE_DIR="$PROFILE_DIR"
PUBLIC_DIR="$PUBLIC_DIR"
DISPLAY_VALUE=":$DISPLAY_NUM"
DEBUG_PORT="$DEBUG_PORT"
CHROME_BIN="$CHROME_BIN"
PID_FILE="\$PROJECT_ROOT/zalo_web_qr_worker.pid"
STATUS_FILE="\$PUBLIC_DIR/status.txt"
SCREEN_FILE="\$PUBLIC_DIR/screen.png"
SCREEN_TMP_FILE="\$PUBLIC_DIR/screen.tmp.png"
MANUAL_FLAG="\$PROJECT_ROOT/.zalo_manual_login_active"
CAPTURE_LOG="\$PROJECT_ROOT/zalo_web_qr_capture.log"
CHROME_LOG="\$PROJECT_ROOT/zalo_web_qr_chrome.log"
XVFB_LOG="\$PROJECT_ROOT/zalo_web_qr_xvfb.log"

if [[ -z "\$CHROME_BIN" || ! -x "\$CHROME_BIN" ]]; then
  if [[ -x "\$PROJECT_ROOT/.chrome-for-testing/chrome-linux64/chrome" ]]; then CHROME_BIN="\$PROJECT_ROOT/.chrome-for-testing/chrome-linux64/chrome";
  elif command -v google-chrome-stable >/dev/null 2>&1; then CHROME_BIN="\$(command -v google-chrome-stable)";
  elif command -v chromium >/dev/null 2>&1; then CHROME_BIN="\$(command -v chromium)";
  elif [[ -x /snap/bin/chromium ]]; then CHROME_BIN="/snap/bin/chromium";
  else echo "Chrome not found" >&2; exit 1; fi
fi

mkdir -p "\$PUBLIC_DIR" "\$PROFILE_DIR"
printf 'Dang chuan bi Chrome Zalo QR... %s\n' "\$(date -Is)" > "\$STATUS_FILE"
if [[ -f "\$PID_FILE" ]] && kill -0 "\$(cat "\$PID_FILE")" 2>/dev/null; then exit 0; fi
echo \$\$ > "\$PID_FILE"
trap 'rm -f "\$PID_FILE"' EXIT INT TERM

if [[ -x "\$PROJECT_ROOT/script/check_zalo_profile_available.sh" ]]; then "\$PROJECT_ROOT/script/check_zalo_profile_available.sh" manual-login >> "\$CAPTURE_LOG" 2>&1 || true; fi
if ! pgrep -f "Xvfb \$DISPLAY_VALUE" >/dev/null 2>&1; then nohup Xvfb "\$DISPLAY_VALUE" -screen 0 1280x900x24 -ac +extension RANDR >> "\$XVFB_LOG" 2>&1 & sleep 2; fi
export DISPLAY="\$DISPLAY_VALUE"
export XDG_RUNTIME_DIR="\${XDG_RUNTIME_DIR:-/run/user/0}"
mkdir -p "\$XDG_RUNTIME_DIR"; chmod 700 "\$XDG_RUNTIME_DIR" || true
SESSION_DIR="\$PROFILE_DIR/Default/Sessions"
if [[ -d "\$SESSION_DIR" ]]; then mkdir -p "\$PROFILE_DIR/Default/Sessions.backup"; find "\$SESSION_DIR" -type f -maxdepth 1 -exec mv {} "\$PROFILE_DIR/Default/Sessions.backup/" \; 2>/dev/null || true; fi
nohup setsid "\$CHROME_BIN" --user-data-dir="\$PROFILE_DIR" --profile-directory=Default --remote-debugging-address=127.0.0.1 --remote-debugging-port="\$DEBUG_PORT" --no-default-browser-check --disable-notifications --disable-dev-shm-usage --no-sandbox --disable-gpu --disable-background-timer-throttling --disable-renderer-backgrounding --disable-session-crashed-bubble --hide-crash-restore-bubble --disable-infobars --lang=vi-VN --window-size=1280,900 --new-window "https://chat.zalo.me/" >> "\$PROJECT_ROOT/zalo_web_qr_chrome.out" 2>> "\$CHROME_LOG" &
sleep 8
while true; do
  if import -window root "png:\$SCREEN_TMP_FILE" >> "\$CAPTURE_LOG" 2>&1; then mv "\$SCREEN_TMP_FILE" "\$SCREEN_FILE"; chmod 644 "\$SCREEN_FILE"; printf 'Cap nhat anh luc %s.\n' "\$(date -Is)" > "\$STATUS_FILE"; fi
  if curl -fsS "http://127.0.0.1:\$DEBUG_PORT/json" 2>/dev/null | grep -q '"url": "https://chat.zalo.me'; then
    printf 'Zalo da dang nhap thanh cong luc %s. Da dong Chrome QR de nha profile.\n' "\$(date -Is)" > "\$STATUS_FILE"
    pkill -TERM -f "\$CHROME_BIN.*\$PROFILE_DIR" 2>/dev/null || true; sleep 2; pkill -KILL -f "\$CHROME_BIN.*\$PROFILE_DIR" 2>/dev/null || true
    rm -f "\$MANUAL_FLAG"; exit 0
  fi
  sleep $REFRESH_SECONDS
done
SH
chmod +x "$PROJECT_ROOT/script/start_zalo_web_qr_worker.sh"

cat > "/etc/systemd/system/$SERVICE_NAME.service" <<UNIT
[Unit]
Description=Zalo Web QR Login for $DOMAIN$URL_PATH
After=network.target nginx.service

[Service]
Type=simple
WorkingDirectory=$PROJECT_ROOT
ExecStart=/usr/bin/python3 $PROJECT_ROOT/script/zalo_web_qr_server.py
Restart=always
RestartSec=5
User=root

[Install]
WantedBy=multi-user.target
UNIT

python3 - "$NGINX_SITE" "$URL_PATH" "$UPSTREAM_PORT" <<'PY'
from pathlib import Path
import sys
site = Path(sys.argv[1])
path = sys.argv[2]
port = sys.argv[3]
text = site.read_text()
if f'location {path}' not in text:
    marker = 'server {\n'
    block = f'''server {{
    location {path} {{
        proxy_pass http://127.0.0.1:{port};
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_buffering off;
        add_header Cache-Control "no-store, no-cache, must-revalidate, max-age=0" always;
    }}
'''
    text = text.replace(marker, block, 1)
    site.write_text(text)
PY

cat > "$PROJECT_ROOT/zalo_web_qr_link.txt" <<LINK
https://$DOMAIN$URL_PATH
LINK

systemctl daemon-reload
systemctl enable --now "$SERVICE_NAME.service"
nginx -t
systemctl reload nginx

echo "Installed: https://$DOMAIN$URL_PATH"
echo "Service: $SERVICE_NAME.service"
echo "Backup: $BACKUP_DIR"
