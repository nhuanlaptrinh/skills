[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$ProfileId,

    [ValidateSet('gpt-5.4', 'gpt-5.5', 'GPT-5.6', 'GPT-5.6-sol', 'GPT-5.6-terra', 'GPT-5.6-luna')]
    [string]$Model = 'GPT-5.6-sol',

    [Parameter(Mandatory = $true)]
    [string]$BaseUrl,

    [string]$ProviderName = 'router',

    [string]$ProviderEnvKey,

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

if ([string]::IsNullOrWhiteSpace($ProfileId) -or $ProfileId -match '[\x00-\x1f\\/:*?"<>|]' -or $ProfileId -match '\.\.') {
    throw 'ProfileId is invalid. Use a simple profile name without a path or special characters.'
}

if (-not [string]::IsNullOrWhiteSpace($ShortcutPath)) {
    throw 'Do not change the shortcut during provisioning. Verify both identities and API access first, then update the existing shortcut separately.'
}
if ($SetApiKey) {
    throw 'File-based API authentication is not supported by this provider setup. Supply the provider environment variable name without its value.'
}
if ([string]::IsNullOrWhiteSpace($ProviderEnvKey) -or $ProviderEnvKey -notmatch '^[A-Za-z_][A-Za-z0-9_]*$') {
    throw 'ProviderEnvKey must be the name of the provider credential environment variable, not the key value.'
}
if ($ProviderName -notmatch '^[A-Za-z0-9_-]+$') {
    throw 'ProviderName must contain only letters, numbers, underscores, or hyphens.'
}

$baseUri = $null
if (-not [Uri]::TryCreate($BaseUrl, [UriKind]::Absolute, [ref]$baseUri) -or $baseUri.Scheme -notin @('http', 'https')) {
    throw 'BaseUrl must be an absolute HTTP or HTTPS URL.'
}
if (-not [string]::IsNullOrEmpty($baseUri.UserInfo) -or -not [string]::IsNullOrEmpty($baseUri.Query) -or -not [string]::IsNullOrEmpty($baseUri.Fragment)) {
    throw 'BaseUrl must not contain credentials, a query, or a fragment.'
}

$resolvedRoot = [System.IO.Path]::GetFullPath($ProfileRoot)
$profilePath = Join-Path $resolvedRoot $ProfileId
$codexHome = Join-Path $profilePath '.codex'
$configPath = Join-Path $codexHome 'config.toml'
$defaultCodexHome = [System.IO.Path]::GetFullPath((Join-Path $env:USERPROFILE '.codex')).TrimEnd('\', '/')
$candidate = [System.IO.Path]::GetFullPath($codexHome)
while (-not [string]::IsNullOrWhiteSpace($candidate)) {
    if ((Test-Path -LiteralPath $candidate) -and ((Get-Item -LiteralPath $candidate -Force).Attributes -band [System.IO.FileAttributes]::ReparsePoint)) {
        throw 'The target profile path contains a junction or symbolic link; inspect it before provisioning.'
    }
    $parent = Split-Path -Parent $candidate
    if ([string]::IsNullOrWhiteSpace($parent) -or $parent -eq $candidate) { break }
    $candidate = $parent
}
$normalizedCodexHome = [System.IO.Path]::GetFullPath($codexHome).TrimEnd('\', '/')
if ([System.StringComparer]::OrdinalIgnoreCase.Equals($normalizedCodexHome, $defaultCodexHome) -or
    $normalizedCodexHome.StartsWith($defaultCodexHome + [System.IO.Path]::DirectorySeparatorChar, [System.StringComparison]::OrdinalIgnoreCase) -or
    $defaultCodexHome.StartsWith($normalizedCodexHome + [System.IO.Path]::DirectorySeparatorChar, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw 'Refusing to configure the default customer CODEX_HOME as the vendor profile.'
}
if (Test-Path -LiteralPath $configPath) {
    throw 'The target config already exists. Preserve the existing profile and inspect it; do not overwrite it through provisioning.'
}

New-Item -ItemType Directory -Force -Path $codexHome | Out-Null

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
env_key = "$ProviderEnvKey"
"@

[System.IO.File]::WriteAllText($configPath, $config.TrimStart(), [System.Text.UTF8Encoding]::new($false))

Write-Output "ProfileId: $ProfileId"
Write-Output "CODEX_HOME: $codexHome"
Write-Output "Config: $configPath"
Write-Output 'No API key or auth.json was created or copied. Verify the provider credential is available to the extension.'
Write-Output 'No shortcut was changed. Verify both identities and API access before updating the existing shortcut separately.'
