[CmdletBinding(DefaultParameterSetName = 'Profile')]
param(
    [Parameter(Mandatory = $true, ParameterSetName = 'Profile')]
    [string]$ProfileId,

    [Parameter(Mandatory = $true, ParameterSetName = 'Direct')]
    [string]$CodexHome,

    [Parameter(Mandatory = $true)]
    [string]$AntigravityPath,

    [Parameter(ParameterSetName = 'Profile')]
    [string]$ProfileRoot = $env:ALT_CODEX_PROFILE_ROOT,

    [Parameter(ParameterSetName = 'Profile')]
    [string]$UserDataDir,

    [string[]]$ArgumentList = @(),

    [switch]$Wait
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$resolvedAntigravity = (Resolve-Path -LiteralPath $AntigravityPath -ErrorAction Stop).Path
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
            throw 'CodexHome contains a junction or symbolic link; inspect it before launching.'
        }
        $parent = Split-Path -Parent $candidate
        if ([string]::IsNullOrWhiteSpace($parent) -or $parent -eq $candidate) { break }
        $candidate = $parent
    }
    $runningIde = @(Get-CimInstance Win32_Process -ErrorAction Stop | Where-Object { $_.Name -in @('Antigravity.exe', 'Antigravity IDE.exe') })
    if ($runningIde.Count -gt 0) {
        throw 'Antigravity is still running. Save work and close it normally before using the existing IDE profile; no process was closed.'
    }
}
else {
    if ([string]::IsNullOrWhiteSpace($ProfileRoot)) { $ProfileRoot = Join-Path $env:LOCALAPPDATA 'YourProduct\codex-profiles' }
    if ([string]::IsNullOrWhiteSpace($ProfileId) -or $ProfileId -match '[\x00-\x1f\\/:*?"<>|]' -or $ProfileId -match '\.\.') {
        throw 'ProfileId is invalid. Use a simple profile name without a path or special characters.'
    }
    $resolvedCodexHome = Join-Path (Join-Path ([System.IO.Path]::GetFullPath($ProfileRoot)) $ProfileId) '.codex'
}
$configPath = Join-Path $resolvedCodexHome 'config.toml'

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
    [void]$childArguments.Add(('--user-data-dir="{0}"' -f $resolvedUserDataDir))
}

$oldCodexHome = $env:CODEX_HOME
$oldElectronRunAsNode = [Environment]::GetEnvironmentVariable('ELECTRON_RUN_AS_NODE', 'Process')
try {
    $env:CODEX_HOME = $resolvedCodexHome
    [Environment]::SetEnvironmentVariable('ELECTRON_RUN_AS_NODE', $null, 'Process')
    if ($childArguments.Count -gt 0) {
        $process = Start-Process -FilePath $resolvedAntigravity -ArgumentList $childArguments -PassThru -Wait:$Wait
    }
    else {
        $process = Start-Process -FilePath $resolvedAntigravity -PassThru -Wait:$Wait
    }
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
Write-Output "CODEX_HOME: $resolvedCodexHome"
if ($PSCmdlet.ParameterSetName -eq 'Profile') {
    Write-Output "Antigravity UserDataDir: $resolvedUserDataDir"
}
else {
    Write-Output 'Antigravity uses its existing IDE user-data directory.'
}
Write-Output 'Verify the running extension uses this CODEX_HOME and can authenticate; process start alone is not proof.'
Write-Output 'API key and browser cookies are not printed.'
