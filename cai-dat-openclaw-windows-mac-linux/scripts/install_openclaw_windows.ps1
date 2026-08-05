param(
  [string]$Token = "chatbot",
  [int]$Port = 18789,
  [string]$Bind = "loopback",
  [switch]$SkipPythonPip,
  [switch]$SkipCodex,
  [switch]$SkipDeepSeek
)

$ErrorActionPreference = "Stop"
$DashboardUrl = "http://127.0.0.1:$Port/"
$OpenClawVersion = "2026.7.1-2"
$TokenCodexBaseUrl = "https://codex.anhlaptrinh.vn/v1"
$TokenCodexModelId = "GPT-5.6-sol"
$TokenCodexProviderId = "token-codex"

function Write-Step {
  param([string]$Message)
  Write-Host ""
  Write-Host "==> $Message"
}

function Refresh-Path {
  $machine = [Environment]::GetEnvironmentVariable("Path", "Machine")
  $user = [Environment]::GetEnvironmentVariable("Path", "User")
  $npmBin = Join-Path $env:APPDATA "npm"
  $env:Path = "$machine;$user;$npmBin"
}

function Add-UserPath {
  param([string]$PathToAdd)
  if (-not (Test-Path $PathToAdd)) {
    return
  }
  $current = [Environment]::GetEnvironmentVariable("Path", "User")
  $parts = @()
  if ($current) {
    $parts = $current -split ";" | Where-Object { $_ }
  }
  if ($parts -notcontains $PathToAdd) {
    $updated = (($parts + $PathToAdd) -join ";")
    [Environment]::SetEnvironmentVariable("Path", $updated, "User")
  }
}

function Require-Winget {
  if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
    throw "winget is required. Install App Installer from Microsoft Store, then run this script again."
  }
}

function Ensure-Node {
  Refresh-Path
  $node = Get-Command node -ErrorAction SilentlyContinue
  if ($node) {
    Write-Host "Node found: $(node -v)"
    Write-Host "npm found: $(npm -v)"
    return
  }

  Require-Winget
  Write-Step "Installing Node.js LTS"
  winget install --id OpenJS.NodeJS.LTS --exact --accept-package-agreements --accept-source-agreements --disable-interactivity
  Refresh-Path
  if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    throw "Node.js was installed but node is still not available in PATH. Open a new PowerShell window and rerun this script."
  }
  Write-Host "Node installed: $(node -v)"
  Write-Host "npm installed: $(npm -v)"
}

function Get-PythonCommand {
  Refresh-Path
  $python = Get-Command python -ErrorAction SilentlyContinue
  if ($python) {
    return "python"
  }
  $py = Get-Command py -ErrorAction SilentlyContinue
  if ($py) {
    return "py -3"
  }
  return $null
}

function Ensure-PythonPip {
  if ($SkipPythonPip) {
    Write-Host "Skipping Python/pip setup."
    return
  }

  $pythonCmd = Get-PythonCommand
  if (-not $pythonCmd) {
    Require-Winget
    Write-Step "Installing Python for pip"
    winget install --id Python.Python.3.12 --exact --accept-package-agreements --accept-source-agreements --disable-interactivity
    Refresh-Path
    $pythonCmd = Get-PythonCommand
  }

  if (-not $pythonCmd) {
    throw "Python was installed but is still not available in PATH. Open a new PowerShell window and rerun this script."
  }

  Write-Step "Ensuring pip"
  Invoke-Expression "$pythonCmd --version"
  Invoke-Expression "$pythonCmd -m ensurepip --upgrade"
  Invoke-Expression "$pythonCmd -m pip install --upgrade pip"
  Invoke-Expression "$pythonCmd -m pip --version"
}

function Ensure-OpenClaw {
  Refresh-Path
  Add-UserPath (Join-Path $env:APPDATA "npm")
  Refresh-Path

  Write-Step "Installing OpenClaw CLI $OpenClawVersion"
  npm install -g "openclaw@$OpenClawVersion"
  Refresh-Path

  if (-not (Get-Command openclaw -ErrorAction SilentlyContinue)) {
    throw "OpenClaw was installed but openclaw is not available in PATH. Open a new PowerShell window and rerun this script."
  }
  openclaw --version
}

function Configure-CodexChatGptLoginPreference {
  Write-Step "Preparing Codex CLI ChatGPT account preference"
  $codexDir = Join-Path $env:USERPROFILE ".codex"
  $configPath = Join-Path $codexDir "config.toml"
  if (-not (Test-Path $codexDir)) {
    New-Item -ItemType Directory -Path $codexDir | Out-Null
  }
  $content = ""
  if (Test-Path $configPath) {
    $content = Get-Content -Raw $configPath
  }
  if ($content -match '(?m)^forced_login_method\\s*=') {
    $content = [regex]::Replace($content, '(?m)^forced_login_method\\s*=.*$', 'forced_login_method = "chatgpt"')
  } else {
    $content = "forced_login_method = `"chatgpt`"`r`n`r`n$content"
  }
  Set-Content -Path $configPath -Value $content -Encoding UTF8
}

function Configure-OpenClaw {
  Write-Step "Configuring OpenClaw local gateway"
  openclaw onboard --non-interactive --accept-risk --mode local --auth-choice skip --skip-channels --skip-search --skip-skills --install-daemon --skip-health --gateway-bind $Bind --gateway-auth token --gateway-port $Port --gateway-token $Token
  openclaw config set gateway.mode local
  openclaw config set gateway.bind $Bind
  openclaw config set gateway.auth.mode token
  openclaw config set gateway.auth.token $Token
  openclaw config set gateway.port $Port --strict-json
  openclaw config validate
}

function Configure-DeepSeek {
  param(
    [string]$ApiKey
  )

  if ([string]::IsNullOrWhiteSpace($ApiKey)) {
    Write-Host "DeepSeek API key not found. Skipping DeepSeek provider."
    return
  }

  Write-Step "Enabling DeepSeek provider"
  & openclaw onboard `
    --non-interactive `
    --accept-risk `
    --mode local `
    --auth-choice deepseek-api-key `
    --deepseek-api-key $ApiKey `
    --skip-channels `
    --skip-search `
    --skip-skills `
    --install-daemon `
    --skip-health `
    --gateway-bind $Bind `
    --gateway-auth token `
    --gateway-port $Port `
    --gateway-token $Token
}

function Configure-TokenCodex {
  param(
    [string]$ApiKey
  )

  if ([string]::IsNullOrWhiteSpace($ApiKey)) {
    Write-Host "Token Codex API key not found. Set TOKEN_CODEX_API_KEY, then rerun this script."
    return
  }

  Write-Step "Configuring Token Codex as the default OpenClaw model"
  $configPath = Join-Path $env:USERPROFILE ".openclaw\openclaw.json"
  $scriptPath = Join-Path $env:TEMP "configure-token-codex-$PID.js"
  $previousRuntimeKey = $env:TOKEN_CODEX_API_KEY_RUNTIME
  $previousConfigPath = $env:TOKEN_CODEX_CONFIG_PATH
  $previousBaseUrl = $env:TOKEN_CODEX_BASE_URL_RUNTIME
  $previousModelId = $env:TOKEN_CODEX_MODEL_ID_RUNTIME
  $previousProviderId = $env:TOKEN_CODEX_PROVIDER_ID_RUNTIME

  try {
    $env:TOKEN_CODEX_API_KEY_RUNTIME = $ApiKey
    $env:TOKEN_CODEX_CONFIG_PATH = $configPath
    $env:TOKEN_CODEX_BASE_URL_RUNTIME = $TokenCodexBaseUrl
    $env:TOKEN_CODEX_MODEL_ID_RUNTIME = $TokenCodexModelId
    $env:TOKEN_CODEX_PROVIDER_ID_RUNTIME = $TokenCodexProviderId
    @'
const fs = require('fs');

const configPath = process.env.TOKEN_CODEX_CONFIG_PATH;
const apiKey = process.env.TOKEN_CODEX_API_KEY_RUNTIME;
const baseUrl = process.env.TOKEN_CODEX_BASE_URL_RUNTIME;
const modelId = process.env.TOKEN_CODEX_MODEL_ID_RUNTIME;
const providerId = process.env.TOKEN_CODEX_PROVIDER_ID_RUNTIME;
const primaryModel = `${providerId}/${modelId}`;
const config = JSON.parse(fs.readFileSync(configPath, 'utf8'));

config.agents ??= {};
config.agents.defaults ??= {};
config.agents.defaults.model = { primary: primaryModel };
config.agents.defaults.models ??= {};
config.agents.defaults.models[primaryModel] ??= {};
config.models ??= {};
config.models.mode = 'merge';
config.models.providers ??= {};
config.models.providers[providerId] = {
  baseUrl,
  apiKey,
  api: 'openai-completions',
  models: [{ id: modelId, name: modelId }]
};

fs.writeFileSync(configPath, `${JSON.stringify(config, null, 2)}\n`);
'@ | Set-Content -Path $scriptPath -Encoding UTF8
    node $scriptPath
    openclaw config validate
    Write-Host "Token Codex configured: $TokenCodexProviderId/$TokenCodexModelId"
  } finally {
    Remove-Item $scriptPath -Force -ErrorAction SilentlyContinue
    $env:TOKEN_CODEX_API_KEY_RUNTIME = $previousRuntimeKey
    $env:TOKEN_CODEX_CONFIG_PATH = $previousConfigPath
    $env:TOKEN_CODEX_BASE_URL_RUNTIME = $previousBaseUrl
    $env:TOKEN_CODEX_MODEL_ID_RUNTIME = $previousModelId
    $env:TOKEN_CODEX_PROVIDER_ID_RUNTIME = $previousProviderId
  }
}

function Configure-CodexAccount {
  if ($SkipCodex) {
    Write-Host "Skipping Codex/OpenAI account notes."
    return
  }

  Write-Step "Codex/OpenAI account login is manual"
  Write-Host "This installer does not install/run Codex login or OpenClaw Codex provider login."
  Write-Host "After install, install/open official Codex CLI when ready, then run:"
  Write-Host "  codex logout"
  Write-Host "  codex login"
  Write-Host "For headless/device flow:"
  Write-Host "  codex login --device-auth"
}

function Configure-Providers {
  if (-not $SkipCodex) {
    Configure-CodexAccount
  }

  if (-not $SkipDeepSeek) {
    Configure-DeepSeek -ApiKey $env:DEEPSEEK_API_KEY
  }

  $tokenCodexApiKey = $env:TOKEN_CODEX_API_KEY
  if ([string]::IsNullOrWhiteSpace($tokenCodexApiKey)) {
    $tokenCodexApiKey = $env:CUSTOM_PROVIDER_API_KEY
  }
  Configure-TokenCodex -ApiKey $tokenCodexApiKey

  openclaw config set gateway.auth.token $Token
  openclaw config validate
}

function Restart-Gateway {
  Write-Step "Restarting OpenClaw Gateway"
  openclaw gateway restart
  Start-Sleep -Seconds 10
  openclaw gateway status
}

Write-Step "OpenClaw Windows classroom installer"
Write-Host "Dashboard will be: $DashboardUrl"
Write-Host "Gateway token will be: $Token"
Write-Host "OpenClaw version will be: $OpenClawVersion"

Ensure-Node
Ensure-PythonPip
Ensure-OpenClaw
Configure-CodexChatGptLoginPreference
Configure-OpenClaw
Configure-Providers
Restart-Gateway

Write-Host ""
Write-Host "DONE"
Write-Host "Dashboard: $DashboardUrl"
Write-Host "Token: $Token"
if (-not $SkipCodex) {
  Write-Host "Codex/OpenAI account login is manual:"
  Write-Host "Install/open official Codex CLI, then run: codex login"
}
if ([string]::IsNullOrWhiteSpace($env:DEEPSEEK_API_KEY)) {
  Write-Host "DeepSeek not enabled yet. Set DEEPSEEK_API_KEY, then rerun this script."
}
$finalTokenCodexApiKey = $env:TOKEN_CODEX_API_KEY
if ([string]::IsNullOrWhiteSpace($finalTokenCodexApiKey)) {
  $finalTokenCodexApiKey = $env:CUSTOM_PROVIDER_API_KEY
}
if (-not [string]::IsNullOrWhiteSpace($finalTokenCodexApiKey)) {
  Write-Host "Primary model: $TokenCodexProviderId/$TokenCodexModelId"
  Write-Host "Base URL: $TokenCodexBaseUrl"
}
