[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$ProfileId,

    [Parameter(Mandatory = $true)]
    [string]$ExistingCodexHome,

    [string]$CustomerChatGPTDataDir,

    [string]$ExistingAntigravityUserDataDir,

    [string]$AntigravityUserDataDir,

    [ValidateSet('gpt-5.4', 'gpt-5.5', 'GPT-5.6', 'GPT-5.6-sol', 'GPT-5.6-terra', 'GPT-5.6-luna')]
    [string]$Model = 'GPT-5.6-sol',

    [Parameter(Mandatory = $true)]
    [string]$BaseUrl,

    [string]$ProviderName = 'router',

    [string]$ProviderEnvKey,

    [string]$ProfileRoot = $env:ALT_CODEX_PROFILE_ROOT,

    [string]$SourceSkillPath,

    [string]$AntigravityPath,

    [Alias('ExistingShortcutPath')]
    [string]$ShortcutPath,

    [switch]$CopyReviewedAntigravitySettings,

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
    throw 'Do not change the shortcut during migration. Verify both identities and API access first, then update the existing shortcut separately.'
}
if ($SetApiKey -or [string]::IsNullOrWhiteSpace($ProviderEnvKey) -or $ProviderEnvKey -notmatch '^[A-Za-z_][A-Za-z0-9_]*$') {
    throw 'Supply only the provider credential environment variable name with -ProviderEnvKey; file-based key setup is not supported.'
}

$targetCodexHome = [System.IO.Path]::GetFullPath((Join-Path (Join-Path $ProfileRoot $ProfileId) '.codex')).TrimEnd('\', '/')
$sourceCodexHome = [System.IO.Path]::GetFullPath($ExistingCodexHome).TrimEnd('\', '/')
$defaultCodexHome = [System.IO.Path]::GetFullPath((Join-Path $env:USERPROFILE '.codex')).TrimEnd('\', '/')
foreach ($profilePathToCheck in @($targetCodexHome, $sourceCodexHome)) {
    $candidate = $profilePathToCheck
    while (-not [string]::IsNullOrWhiteSpace($candidate)) {
        if ((Test-Path -LiteralPath $candidate) -and ((Get-Item -LiteralPath $candidate -Force).Attributes -band [System.IO.FileAttributes]::ReparsePoint)) {
            throw 'A source or target profile path contains a junction or symbolic link; inspect it before migration.'
        }
        $parent = Split-Path -Parent $candidate
        if ([string]::IsNullOrWhiteSpace($parent) -or $parent -eq $candidate) { break }
        $candidate = $parent
    }
}
$separator = [System.IO.Path]::DirectorySeparatorChar
if ([System.StringComparer]::OrdinalIgnoreCase.Equals($targetCodexHome, $sourceCodexHome) -or
    $targetCodexHome.StartsWith($sourceCodexHome + $separator, [System.StringComparison]::OrdinalIgnoreCase) -or
    $sourceCodexHome.StartsWith($targetCodexHome + $separator, [System.StringComparison]::OrdinalIgnoreCase) -or
    [System.StringComparer]::OrdinalIgnoreCase.Equals($targetCodexHome, $defaultCodexHome) -or
    $targetCodexHome.StartsWith($defaultCodexHome + $separator, [System.StringComparison]::OrdinalIgnoreCase) -or
    $defaultCodexHome.StartsWith($targetCodexHome + $separator, [System.StringComparison]::OrdinalIgnoreCase) -or
    (Test-Path -LiteralPath (Join-Path $targetCodexHome 'config.toml'))) {
    throw 'Target Codex profile overlaps a customer profile or already has a config. Preserve it and inspect before continuing.'
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

if (-not [string]::IsNullOrWhiteSpace($CustomerChatGPTDataDir)) {
    $resolvedChatGPTDataDir = [System.IO.Path]::GetFullPath($CustomerChatGPTDataDir).TrimEnd([System.IO.Path]::DirectorySeparatorChar, [System.IO.Path]::AltDirectorySeparatorChar)
    $normalizedTarget = $resolvedAntigravityUserDataDir.TrimEnd([System.IO.Path]::DirectorySeparatorChar, [System.IO.Path]::AltDirectorySeparatorChar)
    $separator = [System.IO.Path]::DirectorySeparatorChar
    if ([System.StringComparer]::OrdinalIgnoreCase.Equals($resolvedChatGPTDataDir, $normalizedTarget) -or
        $resolvedChatGPTDataDir.StartsWith($normalizedTarget + $separator, [System.StringComparison]::OrdinalIgnoreCase) -or
        $normalizedTarget.StartsWith($resolvedChatGPTDataDir + $separator, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw 'CustomerChatGPTDataDir and AntigravityUserDataDir must be different, unrelated directories.'
    }
}

if (-not [string]::IsNullOrWhiteSpace($ExistingAntigravityUserDataDir)) {
    $isolateScript = Join-Path $PSScriptRoot 'isolate_antigravity_profile.ps1'
    $isolateArguments = @{
        ProfileId = $ProfileId
        SourceUserDataDir = $ExistingAntigravityUserDataDir
        TargetUserDataDir = $resolvedAntigravityUserDataDir
        CopyReviewedSettings = $CopyReviewedAntigravitySettings
    }
    & $isolateScript @isolateArguments | ForEach-Object { Write-Output $_ }
}
else {
    if ((Test-Path -LiteralPath $resolvedAntigravityUserDataDir) -and @(Get-ChildItem -LiteralPath $resolvedAntigravityUserDataDir -Force).Count -gt 0) {
        throw "AntigravityUserDataDir is not empty: $resolvedAntigravityUserDataDir. Supply ExistingAntigravityUserDataDir to isolate state; do not reuse an unknown profile."
    }
    New-Item -ItemType Directory -Force -Path $resolvedAntigravityUserDataDir | Out-Null
}

$prepareScript = Join-Path $PSScriptRoot 'prepare_isolated_profile.ps1'
$prepareArguments = @{
    ProfileId = $ProfileId
    Model = $Model
    BaseUrl = $BaseUrl
    ProviderName = $ProviderName
    ProviderEnvKey = $ProviderEnvKey
    ProfileRoot = $ProfileRoot
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
    existing_antigravity_user_data_dir = if ($ExistingAntigravityUserDataDir) { [System.IO.Path]::GetFullPath($ExistingAntigravityUserDataDir) } else { $null }
    antigravity_user_data_dir = $resolvedAntigravityUserDataDir
    new_codex_home = $codexHome
    auth_migration = 'not_copied'
    browser_cookie_migration = 'not_copied'
    antigravity_state_migration = if ($ExistingAntigravityUserDataDir -and $CopyReviewedAntigravitySettings) { 'reviewed_settings_only' } else { 'fresh_profile' }
    created_utc = [DateTime]::UtcNow.ToString('o')
} | ConvertTo-Json -Depth 3
[System.IO.File]::WriteAllText($manifestPath, $manifest, [System.Text.UTF8Encoding]::new($false))

Write-Output "Existing Codex config backup: $backupPath"
Write-Output "New CODEX_HOME: $codexHome"
Write-Output "Antigravity UserDataDir: $resolvedAntigravityUserDataDir"
Write-Output "Migration manifest: $manifestPath"
Write-Output 'No auth.json, API key, OAuth token, or browser cookie was copied.'

Write-Output 'No shortcut was changed. Verify both identities and API access before updating the existing shortcut separately.'
