[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$ProfileId,

    [Parameter(Mandatory = $true)]
    [string]$AntigravityPath,

    [string]$ProfileRoot = $env:ALT_CODEX_PROFILE_ROOT,

    [string]$UserDataDir,

    [string[]]$ArgumentList = @(),

    [switch]$Wait
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

if ([string]::IsNullOrWhiteSpace($ProfileRoot)) {
    $ProfileRoot = Join-Path $env:LOCALAPPDATA 'YourProduct\codex-profiles'
}

if ([string]::IsNullOrWhiteSpace($ProfileId) -or $ProfileId -match '[\x00-\x1f\\/:*?"<>|]' -or $ProfileId -match '\.\.') {
    throw 'ProfileId is invalid. Use a simple profile name without a path or special characters.'
}

$resolvedAntigravity = (Resolve-Path -LiteralPath $AntigravityPath -ErrorAction Stop).Path
$codexHome = Join-Path (Join-Path ([System.IO.Path]::GetFullPath($ProfileRoot)) $ProfileId) '.codex'
$configPath = Join-Path $codexHome 'config.toml'

if (-not (Test-Path -LiteralPath $configPath -PathType Leaf)) {
    throw "Profile config not found: $configPath. Run prepare_isolated_profile.ps1 first."
}

$childArguments = [System.Collections.Generic.List[string]]::new()
foreach ($argument in $ArgumentList) {
    if ($argument -match '^--user-data-dir(?:=|$)') {
        throw 'Pass the dedicated directory with -UserDataDir, not through -ArgumentList.'
    }
    [void]$childArguments.Add($argument)
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
[void]$childArguments.Add(('--user-data-dir="{0}"' -f $resolvedUserDataDir))

$oldCodexHome = $env:CODEX_HOME
$oldElectronRunAsNode = [Environment]::GetEnvironmentVariable('ELECTRON_RUN_AS_NODE', 'Process')
try {
    $env:CODEX_HOME = $codexHome
    [Environment]::SetEnvironmentVariable('ELECTRON_RUN_AS_NODE', $null, 'Process')
    $process = Start-Process -FilePath $resolvedAntigravity -ArgumentList $childArguments -PassThru -Wait:$Wait
}
finally {
    [Environment]::SetEnvironmentVariable('ELECTRON_RUN_AS_NODE', $oldElectronRunAsNode, 'Process')
    if ($null -eq $oldCodexHome) {
        Remove-Item Env:CODEX_HOME -ErrorAction SilentlyContinue
    }
    else {
        $env:CODEX_HOME = $oldCodexHome
    }
}

Write-Output "Antigravity PID: $($process.Id)"
Write-Output "CODEX_HOME: $codexHome"
Write-Output "Antigravity UserDataDir: $resolvedUserDataDir"
Write-Output 'API key and browser cookies are not printed.'
