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

ensure_macos() {
  if [[ "$(uname -s)" != "Darwin" ]]; then
    echo "This installer is for macOS/MacBook only."
    exit 1
  fi
}

load_homebrew_path() {
  if [[ -x /opt/homebrew/bin/brew ]]; then
    eval "$(/opt/homebrew/bin/brew shellenv)"
  elif [[ -x /usr/local/bin/brew ]]; then
    eval "$(/usr/local/bin/brew shellenv)"
  fi
}

ensure_homebrew() {
  load_homebrew_path
  if command -v brew >/dev/null 2>&1; then
    echo "Homebrew found: $(brew --version | head -n 1)"
    return
  fi

  step "Installing Homebrew"
  NONINTERACTIVE=1 /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  load_homebrew_path

  if ! command -v brew >/dev/null 2>&1; then
    echo "Homebrew installed, but brew is not in PATH yet."
    echo "Open a new Terminal window and rerun this script."
    exit 1
  fi
}

ensure_node() {
  if command -v node >/dev/null 2>&1 && command -v npm >/dev/null 2>&1; then
    echo "Node found: $(node -v)"
    echo "npm found: $(npm -v)"
    return
  fi

  step "Installing Node.js"
  brew install node@24
  export PATH="$(brew --prefix node@24)/bin:$PATH"
  echo "Node installed: $(node -v)"
  echo "npm installed: $(npm -v)"
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

ensure_python_pip() {
  if ! command -v python3 >/dev/null 2>&1; then
    step "Installing Python"
    brew install python
  fi

  step "Ensuring pip"
  python3 --version
  python3 -m ensurepip --upgrade >/dev/null 2>&1 || true
  python3 -m pip install --upgrade pip --break-system-packages || python3 -m pip install --upgrade pip
  python3 -m pip --version
}

ensure_openclaw() {
  step "Installing OpenClaw CLI ${OPENCLAW_VERSION}"
  npm install --engine-strict -g "openclaw@${OPENCLAW_VERSION}"
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

configure_codex_account() {
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

configure_providers() {
  if [[ "$SKIP_CODEX" != "1" ]]; then
    configure_codex_account
  fi


  configure_token_codex "${TOKEN_CODEX_API_KEY:-${CUSTOM_PROVIDER_API_KEY:-}}"

  openclaw config set gateway.auth.token "$TOKEN"
  openclaw config validate
}

restart_gateway() {
  step "Restarting OpenClaw Gateway"
  openclaw gateway restart
  sleep 10
  openclaw gateway status
}

step "OpenClaw macOS classroom installer"
echo "Dashboard will be: ${DASHBOARD_URL}"
echo "Gateway token will be: ${TOKEN}"
echo "OpenClaw version will be: ${OPENCLAW_VERSION}"

ensure_macos
ensure_homebrew
ensure_node
require_supported_node
ensure_python_pip
ensure_openclaw
configure_codex_chatgpt_login_preference
configure_openclaw
configure_providers
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
