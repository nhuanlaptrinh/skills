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

if ($ProfileId -notmatch '^[A-Za-z0-9][A-Za-z0-9._-]*$' -or $ProfileId -match '\.\.' -or $ProfileId.EndsWith('.')) {
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
    [void]$childArguments.Add("`"--user-data-dir=$resolvedUserDataDir`"")
}
else {
    Write-Warning 'Using the existing Antigravity user-data directory; browser sessions are not isolated by CODEX_HOME.'
}

$oldCodexHome = $env:CODEX_HOME
$oldElectronRunAsNode = $env:ELECTRON_RUN_AS_NODE
try {
    $env:CODEX_HOME = $codexHome
    Remove-Item Env:ELECTRON_RUN_AS_NODE -ErrorAction SilentlyContinue
    $process = Start-Process -FilePath $resolvedAntigravity -ArgumentList $childArguments -PassThru -Wait:$Wait
}
finally {
    if ($null -ne $oldElectronRunAsNode) {
        $env:ELECTRON_RUN_AS_NODE = $oldElectronRunAsNode
    }
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
