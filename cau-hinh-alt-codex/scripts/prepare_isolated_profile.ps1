[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$ProfileId,

    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[A-Za-z0-9][A-Za-z0-9._-]*$')]
    [string]$Model,

    [Parameter(Mandatory = $true)]
    [string]$BaseUrl,

    [ValidatePattern('^[A-Za-z0-9_-]+$')]
    [string]$ProviderName = 'router',

    [ValidatePattern('^[A-Za-z_][A-Za-z0-9_]*$')]
    [string]$EnvKey,

    [string]$ProfileRoot = $env:ALT_CODEX_PROFILE_ROOT,

    [switch]$SetApiKey,

    [string]$SourceCodexHome
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

if ([string]::IsNullOrWhiteSpace($ProfileRoot)) {
    $ProfileRoot = Join-Path $env:LOCALAPPDATA 'YourProduct\codex-profiles'
}

if ($ProfileId -notmatch '^[A-Za-z0-9][A-Za-z0-9._-]*$' -or $ProfileId -match '\.\.' -or $ProfileId.EndsWith('.')) {
    throw 'ProfileId is invalid. Use a simple profile name without a path or special characters.'
}

$baseUri = $null
if (-not [Uri]::TryCreate($BaseUrl, [UriKind]::Absolute, [ref]$baseUri) -or $baseUri.Scheme -notin @('http', 'https') -or $baseUri.UserInfo -or $BaseUrl -match '["\x00-\x1f]') {
    throw 'BaseUrl must be an absolute HTTP(S) URL without embedded credentials or control characters.'
}

$resolvedRoot = [System.IO.Path]::GetFullPath($ProfileRoot)
$profilePath = Join-Path $resolvedRoot $ProfileId
$codexHome = Join-Path $profilePath '.codex'
$configPath = Join-Path $codexHome 'config.toml'
$authPath = Join-Path $codexHome 'auth.json'
if ($SetApiKey -and -not [string]::IsNullOrWhiteSpace($SourceCodexHome)) {
    throw 'Choose either SetApiKey or SourceCodexHome, not both.'
}
if ($EnvKey -and ($SetApiKey -or -not [string]::IsNullOrWhiteSpace($SourceCodexHome))) {
    throw 'Choose an environment key or file-based authentication, not both.'
}

Write-Output "Destination CODEX_HOME: $codexHome"
New-Item -ItemType Directory -Force -Path $codexHome | Out-Null

if (Test-Path -LiteralPath $configPath -PathType Leaf) {
    throw "Config already exists: $configPath. Preserve and update it explicitly instead of replacing it."
}

$envKeyLine = if ($EnvKey) { "`nenv_key = `"$EnvKey`"" } else { '' }
$config = @"
model_provider = "$ProviderName"
model = "$Model"
forced_login_method = "api"
cli_auth_credentials_store = "file"

[model_providers.$ProviderName]
name = "$ProviderName"
base_url = "$BaseUrl"$envKeyLine
wire_api = "responses"
"@

[System.IO.File]::WriteAllText($configPath, $config.TrimStart(), [System.Text.UTF8Encoding]::new($false))

$authStatus = if ($EnvKey) { 'env_key_reference_not_verified' } else { 'missing' }
if (Test-Path -LiteralPath $authPath) {
    $authStatus = 'existing_not_verified'
}
elseif (-not [string]::IsNullOrWhiteSpace($SourceCodexHome)) {
    $sourceAuthPath = Join-Path ([System.IO.Path]::GetFullPath($SourceCodexHome)) 'auth.json'
    if (-not (Test-Path -LiteralPath $sourceAuthPath -PathType Leaf)) {
        throw 'Source auth.json not found. No API key was copied.'
    }
    try {
        $sourceAuth = Get-Content -LiteralPath $sourceAuthPath -Raw -Encoding UTF8 | ConvertFrom-Json -ErrorAction Stop
    }
    catch {
        throw 'Source auth.json is not valid JSON. No API key was copied.'
    }
    $apiKeyProperty = $sourceAuth.PSObject.Properties['OPENAI_API_KEY']
    $tokensProperty = $sourceAuth.PSObject.Properties['tokens']
    $modeProperty = $sourceAuth.PSObject.Properties['auth_mode']
    if ($null -eq $apiKeyProperty -or $apiKeyProperty.Value -isnot [string] -or
        [string]::IsNullOrWhiteSpace($apiKeyProperty.Value) -or
        ($null -ne $tokensProperty -and $null -ne $tokensProperty.Value) -or
        ($null -ne $modeProperty -and $modeProperty.Value -notin @('apikey', 'api_key'))) {
        throw 'Source is not an API-key-only Codex login. No API key was copied.'
    }
    try {
        $authJson = [ordered]@{ OPENAI_API_KEY = $apiKeyProperty.Value } | ConvertTo-Json -Compress
        $bytes = [System.Text.UTF8Encoding]::new($false).GetBytes($authJson)
        $stream = [System.IO.File]::Open($authPath, [System.IO.FileMode]::CreateNew, [System.IO.FileAccess]::Write, [System.IO.FileShare]::None)
        try { $stream.Write($bytes, 0, $bytes.Length) } finally { $stream.Dispose() }
        $authStatus = 'api_key_copied'
    }
    finally {
        if (Get-Variable bytes -ErrorAction SilentlyContinue) { [Array]::Clear($bytes, 0, $bytes.Length) }
        Remove-Variable sourceAuth, apiKeyProperty, authJson, bytes -ErrorAction SilentlyContinue
    }
}
elseif ($SetApiKey) {
    $secureKey = Read-Host 'Enter the API key for this profile' -AsSecureString
    $plainKey = [System.Net.NetworkCredential]::new('', $secureKey).Password
    try {
        if ([string]::IsNullOrWhiteSpace($plainKey)) {
            throw 'API key cannot be empty.'
        }

        $authJson = [ordered]@{ OPENAI_API_KEY = $plainKey } | ConvertTo-Json -Compress
        $bytes = [System.Text.UTF8Encoding]::new($false).GetBytes($authJson)
        $stream = [System.IO.File]::Open($authPath, [System.IO.FileMode]::CreateNew, [System.IO.FileAccess]::Write, [System.IO.FileShare]::None)
        try { $stream.Write($bytes, 0, $bytes.Length) } finally { $stream.Dispose() }
        $authStatus = 'api_key_entered'
    }
    finally {
        if (Get-Variable bytes -ErrorAction SilentlyContinue) { [Array]::Clear($bytes, 0, $bytes.Length) }
        Remove-Variable plainKey, secureKey, authJson, bytes -ErrorAction SilentlyContinue
    }
}

Write-Output "ProfileId: $ProfileId"
Write-Output "CODEX_HOME: $codexHome"
Write-Output "Config: $configPath"
Write-Output "AuthStatus: $authStatus"
Write-Output 'The API key and auth.json contents are not printed.'
