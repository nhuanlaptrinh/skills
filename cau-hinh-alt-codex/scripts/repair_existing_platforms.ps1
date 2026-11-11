[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$ProfileId,

    [Parameter(Mandatory = $true)]
    [string]$ExistingCodexHome,

    [string]$CustomerChatGPTDataDir,

    [string]$AntigravityUserDataDir,

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

    [string]$SourceSkillPath,

    [switch]$SetApiKey,

    [switch]$ReuseExistingApiKey
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

if ([string]::IsNullOrWhiteSpace($ProfileRoot)) {
    $ProfileRoot = Join-Path $env:LOCALAPPDATA 'YourProduct\codex-profiles'
}

if ($ProfileId -notmatch '^[A-Za-z0-9][A-Za-z0-9._-]*$' -or $ProfileId -match '\.\.' -or $ProfileId.EndsWith('.')) {
    throw 'ProfileId is invalid. Use a simple profile name without a path or special characters.'
}

if ($SetApiKey -and $ReuseExistingApiKey) {
    throw 'Choose either SetApiKey or ReuseExistingApiKey, not both.'
}

$resolvedExistingCodexHome = [System.IO.Path]::GetFullPath($ExistingCodexHome)
$existingConfigPath = Join-Path $resolvedExistingCodexHome 'config.toml'
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'

if (Test-Path -LiteralPath $existingConfigPath -PathType Leaf) {
    $backupPath = "$existingConfigPath.migration-backup-$stamp"
    Copy-Item -LiteralPath $existingConfigPath -Destination $backupPath
}
else {
    $backupPath = $null
}

$resolvedAntigravityUserDataDir = $null
if (-not [string]::IsNullOrWhiteSpace($AntigravityUserDataDir)) {
    $resolvedAntigravityUserDataDir = [System.IO.Path]::GetFullPath($AntigravityUserDataDir)
    New-Item -ItemType Directory -Force -Path $resolvedAntigravityUserDataDir | Out-Null
}

$prepareScript = Join-Path $PSScriptRoot 'prepare_isolated_profile.ps1'
$prepareArguments = @{
    ProfileId = $ProfileId
    Model = $Model
    BaseUrl = $BaseUrl
    ProviderName = $ProviderName
    ProfileRoot = $ProfileRoot
}
if ($SetApiKey) {
    $prepareArguments.SetApiKey = $true
}
if ($EnvKey) {
    $prepareArguments.EnvKey = $EnvKey
}
if ($ReuseExistingApiKey) {
    $prepareArguments.SourceCodexHome = $resolvedExistingCodexHome
}
& $prepareScript @prepareArguments | ForEach-Object { Write-Output $_ }

$resolvedProfileRoot = [System.IO.Path]::GetFullPath($ProfileRoot)
$profilePath = Join-Path $resolvedProfileRoot $ProfileId
$codexHome = Join-Path $profilePath '.codex'

if (-not [string]::IsNullOrWhiteSpace($SourceSkillPath)) {
    $installerScript = Join-Path $PSScriptRoot 'install_skill_into_profile.ps1'
    & $installerScript -SourceSkillPath $SourceSkillPath -CodexHome $codexHome | ForEach-Object { Write-Output $_ }
}

$manifestPath = Join-Path $profilePath 'migration.json'
$manifest = [ordered]@{
    profile_id = $ProfileId
    existing_codex_home = $resolvedExistingCodexHome
    old_config_backup = $backupPath
    customer_chatgpt_data_dir = if ($CustomerChatGPTDataDir) { [System.IO.Path]::GetFullPath($CustomerChatGPTDataDir) } else { $null }
    antigravity_user_data_dir = $resolvedAntigravityUserDataDir
    new_codex_home = $codexHome
    auth_migration = if ($ReuseExistingApiKey) { 'api_key_reuse_requested_check_auth_status' } else { 'not_copied' }
    browser_cookie_migration = 'not_copied'
    created_utc = [DateTime]::UtcNow.ToString('o')
} | ConvertTo-Json -Depth 3
[System.IO.File]::WriteAllText($manifestPath, $manifest, [System.Text.UTF8Encoding]::new($false))

Write-Output "Existing Codex config backup: $backupPath"
Write-Output "New CODEX_HOME: $codexHome"
Write-Output "Antigravity UserDataDir: $resolvedAntigravityUserDataDir"
Write-Output "Migration manifest: $manifestPath"
Write-Output 'No OAuth token or browser cookie was copied. See AuthStatus for API key status.'
