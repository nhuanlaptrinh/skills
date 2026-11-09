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

if ([string]::IsNullOrWhiteSpace($ProfileId) -or $ProfileId -match '[\\/:*?"<>|]' -or $ProfileId -match '\.\.') {
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
    [void]$childArguments.Add($argument)
}

if (-not [string]::IsNullOrWhiteSpace($UserDataDir)) {
    $resolvedUserDataDir = [System.IO.Path]::GetFullPath($UserDataDir)
    New-Item -ItemType Directory -Force -Path $resolvedUserDataDir | Out-Null
    [void]$childArguments.Add("--user-data-dir=$resolvedUserDataDir")
}
else {
    Write-Warning 'No UserDataDir was supplied. Use a dedicated Antigravity/browser profile to avoid sharing ChatGPT cookies.'
}

$oldCodexHome = $env:CODEX_HOME
try {
    $env:CODEX_HOME = $codexHome
    $process = Start-Process -FilePath $resolvedAntigravity -ArgumentList $childArguments -PassThru -Wait:$Wait
}
finally {
    if ($null -eq $oldCodexHome) {
        Remove-Item Env:CODEX_HOME -ErrorAction SilentlyContinue
    }
    else {
        $env:CODEX_HOME = $oldCodexHome
    }
}

Write-Output "Antigravity PID: $($process.Id)"
Write-Output "CODEX_HOME: $codexHome"
Write-Output 'API key and browser cookies are not printed.'