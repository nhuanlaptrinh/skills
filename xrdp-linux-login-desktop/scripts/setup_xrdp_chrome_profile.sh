#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT=""
PROFILE_DIR=""
SHORTCUT_NAME="Chrome Login Profile"
TARGET_USER="root"
TARGET_URL="https://www.facebook.com/"
INSTALL_MISSING="false"

usage() {
  cat <<'USAGE'
Usage:
  setup_xrdp_chrome_profile.sh --project-root PATH --profile-dir PATH [options]

Options:
  --shortcut-name NAME   Desktop shortcut name (default: Chrome Login Profile)
  --user USER            Linux user for RDP desktop files (default: root)
  --url URL              URL to open in Chrome (default: https://www.facebook.com/)
  --install-missing      Install xrdp/XFCE/dbus-x11 if missing on apt systems
USAGE
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --project-root) PROJECT_ROOT="${2:-}"; shift 2 ;;
    --profile-dir) PROFILE_DIR="${2:-}"; shift 2 ;;
    --shortcut-name) SHORTCUT_NAME="${2:-}"; shift 2 ;;
    --user) TARGET_USER="${2:-}"; shift 2 ;;
    --url) TARGET_URL="${2:-}"; shift 2 ;;
    --install-missing) INSTALL_MISSING="true"; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage >&2; exit 2 ;;
  esac
done

if [ -z "$PROJECT_ROOT" ] || [ -z "$PROFILE_DIR" ]; then
  usage >&2
  exit 2
fi

PROJECT_ROOT="$(readlink -f "$PROJECT_ROOT")"
PROFILE_DIR="$(readlink -m "$PROFILE_DIR")"

if [ ! -d "$PROJECT_ROOT" ]; then
  echo "Project root not found: $PROJECT_ROOT" >&2
  exit 1
fi

mkdir -p "$PROFILE_DIR" "$PROJECT_ROOT/script"

missing=()
command -v xrdp >/dev/null 2>&1 || missing+=("xrdp")
command -v startxfce4 >/dev/null 2>&1 || missing+=("xfce4")
command -v google-chrome-stable >/dev/null 2>&1 || command -v google-chrome >/dev/null 2>&1 || command -v chromium >/dev/null 2>&1 || missing+=("google-chrome-stable")

if [ "${#missing[@]}" -gt 0 ]; then
  if [ "$INSTALL_MISSING" = "true" ] && command -v apt-get >/dev/null 2>&1; then
    apt-get update
    apt-get install -y xrdp xfce4 xfce4-terminal dbus-x11
  else
    echo "Missing command/package(s): ${missing[*]}" >&2
    echo "Install xrdp, xfce4, dbus-x11, and Chrome; or rerun with --install-missing." >&2
    exit 1
  fi
fi

if command -v google-chrome-stable >/dev/null 2>&1; then
  CHROME_BIN="$(command -v google-chrome-stable)"
elif command -v google-chrome >/dev/null 2>&1; then
  CHROME_BIN="$(command -v google-chrome)"
else
  CHROME_BIN="$(command -v chromium)"
fi

USER_HOME="$(getent passwd "$TARGET_USER" | cut -d: -f6)"
if [ -z "$USER_HOME" ] || [ ! -d "$USER_HOME" ]; then
  echo "Could not determine home directory for user: $TARGET_USER" >&2
  exit 1
fi

printf 'xfce4-session\n' > "$USER_HOME/.xsession"
chown "$TARGET_USER:$TARGET_USER" "$USER_HOME/.xsession" 2>/dev/null || true

systemctl enable --now xrdp xrdp-sesman >/dev/null 2>&1 || true

if command -v ufw >/dev/null 2>&1 && ufw status | grep -q '^Status: active'; then
  ufw allow 3389/tcp >/dev/null
fi

LAUNCHER="$PROJECT_ROOT/script/open_chrome_login_rdp.sh"
cat > "$LAUNCHER" <<SCRIPT
#!/usr/bin/env bash
set -euo pipefail

PROFILE_DIR="$PROFILE_DIR"

rm -f "\$PROFILE_DIR"/SingletonCookie "\$PROFILE_DIR"/SingletonLock "\$PROFILE_DIR"/SingletonSocket

exec "$CHROME_BIN" \\
  --user-data-dir="\$PROFILE_DIR" \\
  --no-default-browser-check \\
  --disable-notifications \\
  --disable-dev-shm-usage \\
  --no-sandbox \\
  --lang=vi-VN \\
  "$TARGET_URL"
SCRIPT
chmod +x "$LAUNCHER"

DESKTOP_DIR="$USER_HOME/Desktop"
mkdir -p "$DESKTOP_DIR"
DESKTOP_FILE="$DESKTOP_DIR/${SHORTCUT_NAME}.desktop"
cat > "$DESKTOP_FILE" <<DESKTOP
[Desktop Entry]
Type=Application
Name=$SHORTCUT_NAME
Comment=Open Chrome with project automation profile
Exec=$LAUNCHER
Icon=google-chrome
Terminal=false
Categories=Network;WebBrowser;
DESKTOP
chmod +x "$DESKTOP_FILE"
chown -R "$TARGET_USER:$TARGET_USER" "$DESKTOP_DIR" 2>/dev/null || true

echo "XRDP/Chrome profile login desktop prepared."
echo "RDP: <host-or-ip>:3389"
echo "User: $TARGET_USER"
echo "Shortcut: $DESKTOP_FILE"
echo "Profile: $PROFILE_DIR"
