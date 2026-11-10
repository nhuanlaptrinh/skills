[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$ProfileId,

    [Parameter(Mandatory = $true)]
    [string]$ExistingShortcutPath,

    [string]$AntigravityPath,

    [string]$ProfileRoot = $env:ALT_CODEX_PROFILE_ROOT,

    [string]$UserDataDir,

    [switch]$ReplaceReviewedShortcutArguments
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

if ([string]::IsNullOrWhiteSpace($ProfileRoot)) {
    $ProfileRoot = Join-Path $env:LOCALAPPDATA 'YourProduct\codex-profiles'
}

if ([string]::IsNullOrWhiteSpace($ProfileId) -or $ProfileId -match '[\x00-\x1f\\/:*?"<>|]' -or $ProfileId -match '\.\.') {
    throw 'ProfileId is invalid. Use a simple profile name without a path or special characters.'
}

$resolvedShortcutPath = [System.IO.Path]::GetFullPath($ExistingShortcutPath)
if (-not (Test-Path -LiteralPath $resolvedShortcutPath -PathType Leaf)) {
    throw "Existing shortcut was not found: $resolvedShortcutPath"
}
if ((Split-Path -Leaf $resolvedShortcutPath) -match '(?i)chatgpt') {
    throw "Refusing to modify a ChatGPT-named shortcut: $resolvedShortcutPath"
}

$resolvedProfileRoot = [System.IO.Path]::GetFullPath($ProfileRoot)
$codexHome = Join-Path (Join-Path $resolvedProfileRoot $ProfileId) '.codex'
$configPath = Join-Path $codexHome 'config.toml'
if (-not (Test-Path -LiteralPath $configPath -PathType Leaf)) {
    throw "Profile config not found: $configPath. Run prepare_isolated_profile.ps1 first."
}

$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($resolvedShortcutPath)
$originalTarget = $shortcut.TargetPath
if ([string]::IsNullOrWhiteSpace($originalTarget)) {
    throw "Shortcut has no target: $resolvedShortcutPath"
}

if ([string]::IsNullOrWhiteSpace($AntigravityPath)) {
    if ($originalTarget -match '\.exe$' -and $originalTarget -notmatch '(?i)\\(powershell|pwsh)\.exe$') {
        $AntigravityPath = $originalTarget
    }
    else {
        throw 'AntigravityPath is required when the existing shortcut does not directly target Antigravity.exe.'
    }
}
$resolvedAntigravity = (Resolve-Path -LiteralPath $AntigravityPath -ErrorAction Stop).Path
if ((Split-Path -Leaf $resolvedAntigravity) -notmatch '^(?i:Antigravity(?: IDE)?\.exe)$') {
    throw "AntigravityPath does not appear to be an Antigravity executable: $resolvedAntigravity"
}

$resolvedOriginalTarget = $null
if (Test-Path -LiteralPath $originalTarget -PathType Leaf) {
    $resolvedOriginalTarget = (Resolve-Path -LiteralPath $originalTarget -ErrorAction Stop).Path
}
$directAntigravityShortcut = $null -ne $resolvedOriginalTarget -and [System.StringComparer]::OrdinalIgnoreCase.Equals($resolvedOriginalTarget, $resolvedAntigravity)
$managedAntigravityShortcut = $originalTarget -match '(?i)\\(powershell|pwsh)\.exe$' -and $shortcut.Arguments -match '(?i)launch_antigravity_isolated\.ps1'
if (-not $directAntigravityShortcut -and -not $managedAntigravityShortcut) {
    throw "Shortcut does not target the specified Antigravity executable or this skill's launcher: $resolvedShortcutPath"
}
if (-not [string]::IsNullOrWhiteSpace($shortcut.Arguments) -and -not $ReplaceReviewedShortcutArguments) {
    throw 'Existing shortcut has arguments. Review their purpose and preserve required behavior; use -ReplaceReviewedShortcutArguments only with the customer consent to replace them.'
}

if ([string]::IsNullOrWhiteSpace($UserDataDir)) {
    $UserDataDir = Join-Path $env:LOCALAPPDATA "Antigravity-Codex\browser\$ProfileId"
}
$resolvedUserDataDir = [System.IO.Path]::GetFullPath($UserDataDir)

$defaultAntigravityDataDir = $null
if (-not [string]::IsNullOrWhiteSpace($env:APPDATA)) {
    $defaultAntigravityDataDir = [System.IO.Path]::GetFullPath((Join-Path $env:APPDATA 'Antigravity IDE'))
}
if ($null -ne $defaultAntigravityDataDir -and [System.StringComparer]::OrdinalIgnoreCase.Equals(
        $resolvedUserDataDir.TrimEnd([System.IO.Path]::DirectorySeparatorChar, [System.IO.Path]::AltDirectorySeparatorChar),
        $defaultAntigravityDataDir.TrimEnd([System.IO.Path]::DirectorySeparatorChar, [System.IO.Path]::AltDirectorySeparatorChar))) {
    throw "Refusing the shared Antigravity UserDataDir: $resolvedUserDataDir. Use a profile-specific directory."
}

New-Item -ItemType Directory -Force -Path $resolvedUserDataDir | Out-Null

$launcherPath = Join-Path $PSScriptRoot 'launch_antigravity_isolated.ps1'
$powershellPath = Join-Path $PSHOME 'powershell.exe'
if (-not (Test-Path -LiteralPath $powershellPath -PathType Leaf)) {
    $powershellPath = Join-Path $PSHOME 'pwsh.exe'
}
if (-not (Test-Path -LiteralPath $powershellPath -PathType Leaf)) {
    throw 'Could not find a PowerShell executable for the shortcut.'
}

$shortcutArguments = @(
    '-NoLogo', '-NoProfile', '-WindowStyle', 'Hidden', '-ExecutionPolicy', 'Bypass', '-File',
    ('"{0}"' -f $launcherPath), '-ProfileId', ('"{0}"' -f $ProfileId),
    '-AntigravityPath', ('"{0}"' -f $resolvedAntigravity),
    '-ProfileRoot', ('"{0}"' -f $resolvedProfileRoot),
    '-UserDataDir', ('"{0}"' -f $resolvedUserDataDir)
) -join ' '

$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$backupPath = "$resolvedShortcutPath.bak-$stamp"
Copy-Item -LiteralPath $resolvedShortcutPath -Destination $backupPath

$originalIconLocation = $shortcut.IconLocation
$originalWorkingDirectory = $shortcut.WorkingDirectory
$originalDescription = $shortcut.Description
$shortcut.TargetPath = $powershellPath
$shortcut.Arguments = $shortcutArguments
$shortcut.WorkingDirectory = if ([string]::IsNullOrWhiteSpace($originalWorkingDirectory)) { Split-Path -Parent $resolvedAntigravity } else { $originalWorkingDirectory }
$shortcut.IconLocation = if ([string]::IsNullOrWhiteSpace($originalIconLocation)) { "$resolvedAntigravity,0" } else { $originalIconLocation }
$shortcut.Description = $originalDescription
$shortcut.Save()

Write-Output "Updated existing shortcut: $resolvedShortcutPath"
Write-Output "Shortcut backup: $backupPath"
Write-Output "Target profile: $ProfileId"
Write-Output "CODEX_HOME: $codexHome"
Write-Output "Antigravity UserDataDir: $resolvedUserDataDir"
Write-Output 'The existing shortcut name, location, icon, and customer ChatGPT shortcut are preserved.'
if ($ReplaceReviewedShortcutArguments) {
    Write-Output 'The reviewed prior shortcut arguments were replaced; they remain in the shortcut backup.'
}
Write-Output 'No API key, cookie, or token is stored in the shortcut.'
