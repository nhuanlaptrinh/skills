[CmdletBinding(DefaultParameterSetName = 'Profile')]
param(
    [Parameter(Mandatory = $true, ParameterSetName = 'Profile')]
    [string]$ProfileId,

    [Parameter(Mandatory = $true, ParameterSetName = 'Direct')]
    [string]$CodexHome,

    [Parameter(Mandatory = $true)]
    [string]$ExistingShortcutPath,

    [string]$AntigravityPath,

    [Parameter(ParameterSetName = 'Profile')]
    [string]$ProfileRoot = $env:ALT_CODEX_PROFILE_ROOT,

    [Parameter(ParameterSetName = 'Profile')]
    [string]$UserDataDir,

    [switch]$ReplaceReviewedShortcutArguments
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$resolvedShortcutPath = [System.IO.Path]::GetFullPath($ExistingShortcutPath)
if (-not (Test-Path -LiteralPath $resolvedShortcutPath -PathType Leaf)) {
    throw "Existing shortcut was not found: $resolvedShortcutPath"
}
if ((Split-Path -Leaf $resolvedShortcutPath) -match '(?i)chatgpt') {
    throw "Refusing to modify a ChatGPT-named shortcut: $resolvedShortcutPath"
}

if ($PSCmdlet.ParameterSetName -eq 'Direct') {
    if ([string]::IsNullOrWhiteSpace($CodexHome)) { throw 'CodexHome cannot be empty.' }
    $resolvedCodexHome = [System.IO.Path]::GetFullPath($CodexHome).TrimEnd('\', '/')
    $defaultHome = [System.IO.Path]::GetFullPath((Join-Path $env:USERPROFILE '.codex')).TrimEnd('\', '/')
    if ([System.StringComparer]::OrdinalIgnoreCase.Equals($resolvedCodexHome, $defaultHome) -or
        $resolvedCodexHome.StartsWith($defaultHome + [System.IO.Path]::DirectorySeparatorChar, [System.StringComparison]::OrdinalIgnoreCase) -or
        $defaultHome.StartsWith($resolvedCodexHome + [System.IO.Path]::DirectorySeparatorChar, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw 'CodexHome must be separate from the default customer profile.'
    }
    $candidate = $resolvedCodexHome
    while (-not [string]::IsNullOrWhiteSpace($candidate)) {
        if ((Test-Path -LiteralPath $candidate) -and ((Get-Item -LiteralPath $candidate -Force).Attributes -band [System.IO.FileAttributes]::ReparsePoint)) {
            throw 'CodexHome contains a junction or symbolic link; inspect it before updating the shortcut.'
        }
        $parent = Split-Path -Parent $candidate
        if ([string]::IsNullOrWhiteSpace($parent) -or $parent -eq $candidate) { break }
        $candidate = $parent
    }
}
else {
    if ([string]::IsNullOrWhiteSpace($ProfileRoot)) { $ProfileRoot = Join-Path $env:LOCALAPPDATA 'YourProduct\codex-profiles' }
    if ([string]::IsNullOrWhiteSpace($ProfileId) -or $ProfileId -match '[\x00-\x1f\\/:*?"<>|]' -or $ProfileId -match '\.\.') {
        throw 'ProfileId is invalid. Use a simple profile name without a path or special characters.'
    }
    $resolvedProfileRoot = [System.IO.Path]::GetFullPath($ProfileRoot)
    $resolvedCodexHome = Join-Path (Join-Path $resolvedProfileRoot $ProfileId) '.codex'
}
$configPath = Join-Path $resolvedCodexHome 'config.toml'
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

if ($PSCmdlet.ParameterSetName -eq 'Profile') {
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
}

$launcherPath = Join-Path $PSScriptRoot 'launch_antigravity_isolated.ps1'
$powershellPath = Join-Path $PSHOME 'powershell.exe'
if (-not (Test-Path -LiteralPath $powershellPath -PathType Leaf)) {
    $powershellPath = Join-Path $PSHOME 'pwsh.exe'
}
if (-not (Test-Path -LiteralPath $powershellPath -PathType Leaf)) {
    throw 'Could not find a PowerShell executable for the shortcut.'
}

$shortcutArgumentParts = @(
    '-NoLogo', '-NoProfile', '-WindowStyle', 'Hidden', '-ExecutionPolicy', 'Bypass', '-File',
    ('"{0}"' -f $launcherPath), '-AntigravityPath', ('"{0}"' -f $resolvedAntigravity)
)
if ($PSCmdlet.ParameterSetName -eq 'Direct') {
    $shortcutArgumentParts += @('-CodexHome', ('"{0}"' -f $resolvedCodexHome))
}
else {
    $shortcutArgumentParts += @('-ProfileId', ('"{0}"' -f $ProfileId), '-ProfileRoot', ('"{0}"' -f $resolvedProfileRoot), '-UserDataDir', ('"{0}"' -f $resolvedUserDataDir))
}
$shortcutArguments = $shortcutArgumentParts -join ' '

$stamp = Get-Date -Format 'yyyyMMdd-HHmmss-fffffff'
$backupPath = "$resolvedShortcutPath.bak-$stamp"
[System.IO.File]::Copy($resolvedShortcutPath, $backupPath, $false)

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
Write-Output "CODEX_HOME: $resolvedCodexHome"
if ($PSCmdlet.ParameterSetName -eq 'Profile') {
    Write-Output "Target profile: $ProfileId"
    Write-Output "Antigravity UserDataDir: $resolvedUserDataDir"
}
else {
    Write-Output 'Antigravity will use its existing IDE user-data directory. Close running instances normally before launching.'
}
Write-Output 'The existing shortcut name, location, icon, and customer ChatGPT shortcut are preserved.'
if ($ReplaceReviewedShortcutArguments) {
    Write-Output 'The reviewed prior shortcut arguments were replaced; they remain in the shortcut backup.'
}
Write-Output 'No API key, cookie, or token is stored in the shortcut.'
