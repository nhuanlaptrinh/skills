[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$ProfileId,

    [ValidateSet('gpt-5.4', 'gpt-5.5', 'GPT-5.6', 'GPT-5.6-sol', 'GPT-5.6-terra', 'GPT-5.6-luna')]
    [string]$Model = 'GPT-5.6-sol',

    [Parameter(Mandatory = $true)]
    [string]$BaseUrl,

    [string]$ProviderName = 'router',

    [string]$ProfileRoot = $env:ALT_CODEX_PROFILE_ROOT,

    [string]$AntigravityPath,

    [string]$UserDataDir,

    [Alias('ExistingShortcutPath')]
    [string]$ShortcutPath,

    [switch]$ReplaceReviewedShortcutArguments,

    [switch]$SetApiKey
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

if ([string]::IsNullOrWhiteSpace($ProfileRoot)) {
    $ProfileRoot = Join-Path $env:LOCALAPPDATA 'YourProduct\codex-profiles'
}

if ([string]::IsNullOrWhiteSpace($ProfileId) -or $ProfileId -match '[\\/:*?"<>|]' -or $ProfileId -match '\.\.') {
    throw 'ProfileId is invalid. Use a simple profile name without a path or special characters.'
}

$baseUri = $null
if (-not [Uri]::TryCreate($BaseUrl, [UriKind]::Absolute, [ref]$baseUri) -or $baseUri.Scheme -notin @('http', 'https')) {
    throw "BaseUrl is invalid: $BaseUrl"
}

$resolvedRoot = [System.IO.Path]::GetFullPath($ProfileRoot)
$profilePath = Join-Path $resolvedRoot $ProfileId
$codexHome = Join-Path $profilePath '.codex'
$configPath = Join-Path $codexHome 'config.toml'
$authPath = Join-Path $codexHome 'auth.json'
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'

New-Item -ItemType Directory -Force -Path $codexHome | Out-Null

if (Test-Path -LiteralPath $configPath -PathType Leaf) {
    Copy-Item -LiteralPath $configPath -Destination "$configPath.bak-$stamp"
}

$config = @"
model_provider = "$ProviderName"
model = "$Model"
preferred_auth_method = "apikey"
forced_login_method = "api"
cli_auth_credentials_store = "file"

[model_providers.$ProviderName]
name = "$ProviderName"
base_url = "$BaseUrl"
wire_api = "responses"
"@

[System.IO.File]::WriteAllText($configPath, $config.TrimStart(), [System.Text.UTF8Encoding]::new($false))

$apiKeyConfigured = $false
if ($SetApiKey) {
    $secureKey = Read-Host 'Enter the API key for this profile' -AsSecureString
    $plainKey = [System.Net.NetworkCredential]::new('', $secureKey).Password
    try {
        if ([string]::IsNullOrWhiteSpace($plainKey)) {
            throw 'API key cannot be empty.'
        }

        if (Test-Path -LiteralPath $authPath -PathType Leaf) {
            Copy-Item -LiteralPath $authPath -Destination "$authPath.bak-$stamp"
        }

        $authJson = [ordered]@{ OPENAI_API_KEY = $plainKey } | ConvertTo-Json -Compress
        [System.IO.File]::WriteAllText($authPath, $authJson, [System.Text.UTF8Encoding]::new($false))
        $apiKeyConfigured = $true
    }
    finally {
        Remove-Variable plainKey, secureKey -ErrorAction SilentlyContinue
    }
}

Write-Output "ProfileId: $ProfileId"
Write-Output "CODEX_HOME: $codexHome"
Write-Output "Config: $configPath"
Write-Output "ApiKeyConfigured: $apiKeyConfigured"
Write-Output 'The API key and auth.json contents are not printed.'

if (-not [string]::IsNullOrWhiteSpace($ShortcutPath)) {
    $shortcutScript = Join-Path $PSScriptRoot 'update_existing_shortcut.ps1'
    & $shortcutScript -ProfileId $ProfileId -ExistingShortcutPath $ShortcutPath -AntigravityPath $AntigravityPath -ProfileRoot $ProfileRoot -UserDataDir $UserDataDir -ReplaceReviewedShortcutArguments:$ReplaceReviewedShortcutArguments | ForEach-Object { Write-Output $_ }
}
elseif (-not [string]::IsNullOrWhiteSpace($AntigravityPath)) {
    Write-Output 'No shortcut was changed. Pass -ExistingShortcutPath to update the customer existing Antigravity shortcut.'
}
