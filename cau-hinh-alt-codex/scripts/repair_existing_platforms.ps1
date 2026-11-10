[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$ProfileId,

    [Parameter(Mandatory = $true)]
    [string]$ExistingCodexHome,

    [string]$CustomerChatGPTDataDir,

    [string]$AntigravityUserDataDir,

    [ValidateSet('gpt-5.4', 'gpt-5.5', 'GPT-5.6', 'GPT-5.6-sol', 'GPT-5.6-terra', 'GPT-5.6-luna')]
    [string]$Model = 'GPT-5.6-sol',

    [Parameter(Mandatory = $true)]
    [string]$BaseUrl,

    [string]$ProviderName = 'router',

    [string]$ProfileRoot = $env:ALT_CODEX_PROFILE_ROOT,

    [string]$SourceSkillPath,

    [string]$AntigravityPath,

    [Alias('ExistingShortcutPath')]
    [string]$ShortcutPath,

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

if ([string]::IsNullOrWhiteSpace($AntigravityUserDataDir)) {
    $AntigravityUserDataDir = Join-Path $env:LOCALAPPDATA "Antigravity-Codex\browser\$ProfileId"
}
$resolvedAntigravityUserDataDir = [System.IO.Path]::GetFullPath($AntigravityUserDataDir)
New-Item -ItemType Directory -Force -Path $resolvedAntigravityUserDataDir | Out-Null

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
    auth_migration = 'not_copied'
    browser_cookie_migration = 'not_copied'
    created_utc = [DateTime]::UtcNow.ToString('o')
} | ConvertTo-Json -Depth 3
[System.IO.File]::WriteAllText($manifestPath, $manifest, [System.Text.UTF8Encoding]::new($false))

Write-Output "Existing Codex config backup: $backupPath"
Write-Output "New CODEX_HOME: $codexHome"
Write-Output "Antigravity UserDataDir: $resolvedAntigravityUserDataDir"
Write-Output "Migration manifest: $manifestPath"
Write-Output 'No auth.json, API key, OAuth token, or browser cookie was copied.'

if (-not [string]::IsNullOrWhiteSpace($ShortcutPath)) {
    $shortcutScript = Join-Path $PSScriptRoot 'update_existing_shortcut.ps1'
    & $shortcutScript -ProfileId $ProfileId -ExistingShortcutPath $ShortcutPath -AntigravityPath $AntigravityPath -ProfileRoot $ProfileRoot -UserDataDir $resolvedAntigravityUserDataDir | ForEach-Object { Write-Output $_ }
}
else {
    Write-Output 'No shortcut was changed. Pass -ExistingShortcutPath to update the customer existing Antigravity shortcut.'
}
