[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$ProfileId,

    [Parameter(Mandatory = $true)]
    [string]$ExistingShortcutPath,

    [string]$AntigravityPath,

    [string]$ProfileRoot = $env:ALT_CODEX_PROFILE_ROOT,

    [string]$UserDataDir
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

if ([string]::IsNullOrWhiteSpace($ProfileRoot)) {
    $ProfileRoot = Join-Path $env:LOCALAPPDATA 'YourProduct\codex-profiles'
}

if ([string]::IsNullOrWhiteSpace($ProfileId) -or $ProfileId -match '[\\/:*?"<>|]' -or $ProfileId -match '\.\.') {
    throw 'ProfileId is invalid. Use a simple profile name without a path or special characters.'
}

$resolvedShortcutPath = [System.IO.Path]::GetFullPath($ExistingShortcutPath)
if (-not (Test-Path -LiteralPath $resolvedShortcutPath -PathType Leaf)) {
    throw "Existing shortcut was not found: $resolvedShortcutPath"
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

if ([string]::IsNullOrWhiteSpace($UserDataDir)) {
    if ($shortcut.Arguments -match '--user-data-dir=(?:"([^"]+)"|([^\s]+))') {
        $UserDataDir = if ($matches[1]) { $matches[1] } else { $matches[2] }
    }
    else {
        $UserDataDir = Join-Path $env:LOCALAPPDATA "Antigravity-Codex\browser\$ProfileId"
    }
}
$resolvedUserDataDir = [System.IO.Path]::GetFullPath($UserDataDir)
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
Write-Output "ChatGPT UserDataDir: $resolvedUserDataDir"
Write-Output 'The existing shortcut name, location, icon, and customer ChatGPT shortcut are preserved.'
Write-Output 'No API key, cookie, or token is stored in the shortcut.'