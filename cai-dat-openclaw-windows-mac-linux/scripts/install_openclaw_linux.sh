#!/usr/bin/env bash
set -euo pipefail

TOKEN="${TOKEN:-chatbot}"
PORT="${PORT:-18789}"
BIND="${BIND:-loopback}"
SKIP_CODEX="${SKIP_CODEX:-0}"
OPENCLAW_VERSION="2026.10.6"
DASHBOARD_URL="http://127.0.0.1:${PORT}/"
TOKEN_CODEX_BASE_URL="https://codex.anhlaptrinh.vn/v1"
TOKEN_CODEX_MODEL_ID="${TOKEN_CODEX_MODEL_ID:-GPT-6.1-sol}"
TOKEN_CODEX_PROVIDER_ID="token-codex"

case "$TOKEN_CODEX_MODEL_ID" in
  GPT-6.1-sol|GPT-6-terra|GPT-6-luna|GPT-6-astra) ;;
  *) echo "Unsupported model. Choose GPT-6.1-sol, GPT-6-terra, GPT-6-luna, or GPT-6-astra." >&2; exit 2 ;;
esac

step() {
  printf '\n==> %s\n' "$1"
}

ensure_linux() {
  if [[ "$(uname -s)" != "Linux" ]]; then
    echo "This installer is for Linux only."
    exit 1
  fi
}

require_supported_node() {
  node -e '
const [major, minor, patch] = process.versions.node.split(".").map(Number);
const supported = (major === 24 && (minor > 22 || (minor === 22 && patch >= 1))) ||
  major > 26 || (major === 26 && (minor > 12 || (minor === 12 && patch >= 1)));
if (!supported) {
  console.error(`Unsupported Node.js ${process.versions.node}. OpenClaw 2026.10.6 requires >=24.22.1 <25 || >=26.12.1. Install a supported Node.js release, then rerun.`);
  process.exit(1);
}
'
}

ensure_node_python() {
  if command -v node >/dev/null 2>&1 && command -v npm >/dev/null 2>&1 && command -v python3 >/dev/null 2>&1; then
    echo "Node found: $(node -v)"
    echo "npm found: $(npm -v)"
    echo "Python found: $(python3 --version)"
  else
    step "Installing Node.js, npm, Python, and pip"
    if command -v apt-get >/dev/null 2>&1; then
      sudo apt-get update
      sudo apt-get install -y curl ca-certificates python3 python3-pip python3-venv
      curl -fsSL https://deb.nodesource.com/setup_24.x | sudo -E bash -
      sudo apt-get install -y nodejs
    elif command -v dnf >/dev/null 2>&1; then
      sudo dnf install -y nodejs npm python3 python3-pip
    elif command -v yum >/dev/null 2>&1; then
      sudo yum install -y nodejs npm python3 python3-pip
    elif command -v pacman >/dev/null 2>&1; then
      sudo pacman -Sy --noconfirm nodejs npm python python-pip
    else
      echo "Unsupported Linux package manager. Install node, npm, python3, and pip manually, then rerun."
      exit 1
    fi
  fi

  require_supported_node

  step "Ensuring pip"
  python3 -m ensurepip --upgrade >/dev/null 2>&1 || true
  python3 -m pip install --upgrade pip --break-system-packages || python3 -m pip install --upgrade pip || true
  python3 -m pip --version || true
}

ensure_openclaw() {
  step "Installing OpenClaw CLI ${OPENCLAW_VERSION}"
  if npm prefix -g >/dev/null 2>&1 && [[ -w "$(npm prefix -g)" ]]; then
    npm install --engine-strict -g "openclaw@${OPENCLAW_VERSION}"
  else
    sudo npm install --engine-strict -g "openclaw@${OPENCLAW_VERSION}"
  fi
  local installed_version
  local version_pattern="(^|[[:space:]])${OPENCLAW_VERSION//./\\.}([[:space:]]|$)"
  installed_version="$(openclaw --version)"
  printf '%s\n' "$installed_version"
  if [[ ! "$installed_version" =~ $version_pattern ]]; then
    echo "Expected OpenClaw ${OPENCLAW_VERSION}; stopping before configuration." >&2
    exit 1
  fi
}

configure_codex_chatgpt_login_preference() {
  step "Preparing Codex CLI ChatGPT account preference"
  mkdir -p "$HOME/.codex"
  local config_path="$HOME/.codex/config.toml"
  touch "$config_path"
  if grep -qE '^forced_login_method[[:space:]]*=' "$config_path"; then
    sed -i.bak 's/^forced_login_method[[:space:]]*=.*$/forced_login_method = "chatgpt"/' "$config_path"
  else
    local tmp
    tmp="$(mktemp)"
    printf 'forced_login_method = "chatgpt"\n\n' > "$tmp"
    cat "$config_path" >> "$tmp"
    mv "$tmp" "$config_path"
  fi
}

configure_openclaw() {
  step "Configuring OpenClaw local gateway"
  openclaw onboard \
    --non-interactive \
    --accept-risk \
    --mode local \
    --auth-choice skip \
    --skip-channels \
    --skip-search \
    --skip-skills \
    --install-daemon \
    --skip-health \
    --gateway-bind "$BIND" \
    --gateway-auth token \
    --gateway-port "$PORT" \
    --gateway-token "$TOKEN"

  openclaw config set gateway.mode local
  openclaw config set gateway.bind "$BIND"
  openclaw config set gateway.auth.mode token
  openclaw config set gateway.auth.token "$TOKEN"
  openclaw config set gateway.port "$PORT" --strict-json
  openclaw config validate
}

configure_codex_account_note() {
  if [[ "$SKIP_CODEX" == "1" ]]; then
    echo "Skipping Codex/OpenAI account notes."
    return
  fi

  step "Codex/OpenAI account login is manual"
  echo "This installer does not install/run Codex login or OpenClaw Codex provider login."
  echo "After install, install/open official Codex CLI when ready, then run:"
  echo "  codex logout"
  echo "  codex login"
  echo "For headless/device flow:"
  echo "  codex login --device-auth"
}

configure_token_codex() {
  local api_key="$1"

  if [[ -z "$api_key" ]]; then
    echo "Token Codex API key not found. Set TOKEN_CODEX_API_KEY, then rerun this script."
    return
  fi

  step "Configuring Token Codex as the default OpenClaw model"
  TOKEN_CODEX_API_KEY_RUNTIME="$api_key" \
  TOKEN_CODEX_CONFIG_PATH="$HOME/.openclaw/openclaw.json" \
  TOKEN_CODEX_BASE_URL_RUNTIME="$TOKEN_CODEX_BASE_URL" \
  TOKEN_CODEX_MODEL_ID_RUNTIME="$TOKEN_CODEX_MODEL_ID" \
  TOKEN_CODEX_PROVIDER_ID_RUNTIME="$TOKEN_CODEX_PROVIDER_ID" \
  node <<'NODE'
const fs = require('fs');

const configPath = process.env.TOKEN_CODEX_CONFIG_PATH;
const apiKey = process.env.TOKEN_CODEX_API_KEY_RUNTIME;
const baseUrl = process.env.TOKEN_CODEX_BASE_URL_RUNTIME;
const modelId = process.env.TOKEN_CODEX_MODEL_ID_RUNTIME;
const providerId = process.env.TOKEN_CODEX_PROVIDER_ID_RUNTIME;
const primaryModel = `${providerId}/${modelId}`;
const modelIds = ['GPT-6.1-sol', 'GPT-6-terra', 'GPT-6-luna', 'GPT-6-astra'];
if (!modelIds.includes(modelId)) throw new Error('Unsupported Token Codex model');
const config = JSON.parse(fs.readFileSync(configPath, 'utf8'));

config.agents ??= {};
config.agents.defaults ??= {};
config.agents.defaults.model = { primary: primaryModel };
config.agents.defaults.models ??= {};
config.agents.defaults.models = Object.fromEntries(
  Object.entries(config.agents.defaults.models).filter(([reference]) => !reference.startsWith(`${providerId}/`))
);
for (const supportedModelId of modelIds) {
  config.agents.defaults.models[`${providerId}/${supportedModelId}`] = {};
}
config.models ??= {};
config.models.mode = 'merge';
config.models.providers ??= {};
config.models.providers[providerId] = {
  baseUrl,
  apiKey,
  api: 'openai-completions',
  models: modelIds.map(supportedModelId => ({ id: supportedModelId, name: supportedModelId }))
};

fs.writeFileSync(configPath, `${JSON.stringify(config, null, 2)}\n`, { mode: 0o600 });
fs.chmodSync(configPath, 0o600);
NODE
  openclaw config validate
  echo "Token Codex configured: ${TOKEN_CODEX_PROVIDER_ID}/${TOKEN_CODEX_MODEL_ID}"
}

restart_gateway() {
  step "Restarting OpenClaw Gateway"
  openclaw gateway restart
  sleep 10
  openclaw gateway status
}

step "OpenClaw Linux classroom installer"
echo "Dashboard will be: ${DASHBOARD_URL}"
echo "Gateway token will be: ${TOKEN}"
echo "OpenClaw version will be: ${OPENCLAW_VERSION}"

ensure_linux
ensure_node_python
ensure_openclaw
configure_codex_chatgpt_login_preference
configure_openclaw
configure_codex_account_note
configure_token_codex "${TOKEN_CODEX_API_KEY:-${CUSTOM_PROVIDER_API_KEY:-}}"
openclaw config set gateway.auth.token "$TOKEN"
openclaw config validate
restart_gateway

printf '\nDONE\n'
echo "Dashboard: ${DASHBOARD_URL}"
echo "Token: ${TOKEN}"
if [[ "$SKIP_CODEX" != "1" ]]; then
  echo "Codex/OpenAI account login is manual:"
  echo "Install/open official Codex CLI, then run: codex login"
fi
if [[ -n "${TOKEN_CODEX_API_KEY:-${CUSTOM_PROVIDER_API_KEY:-}}" ]]; then
  echo "Primary model: ${TOKEN_CODEX_PROVIDER_ID}/${TOKEN_CODEX_MODEL_ID}"
  echo "Base URL: ${TOKEN_CODEX_BASE_URL}"
fi
