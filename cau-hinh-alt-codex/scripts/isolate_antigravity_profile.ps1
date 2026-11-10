[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$ProfileId,

    [Parameter(Mandatory = $true)]
    [string]$SourceUserDataDir,

    [string]$TargetUserDataDir,

    [switch]$CopyReviewedSettings
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

if ([string]::IsNullOrWhiteSpace($ProfileId) -or $ProfileId -match '[\x00-\x1f\\/:*?"<>|]' -or $ProfileId -match '\.\.') {
    throw 'ProfileId is invalid. Use a simple profile name without a path or special characters.'
}

if ([string]::IsNullOrWhiteSpace($TargetUserDataDir)) {
    $TargetUserDataDir = Join-Path $env:LOCALAPPDATA "Antigravity-Codex\browser\$ProfileId"
}

$resolvedSource = (Resolve-Path -LiteralPath $SourceUserDataDir -ErrorAction Stop).Path
if (-not (Test-Path -LiteralPath $resolvedSource -PathType Container)) {
    throw "SourceUserDataDir is not a directory: $resolvedSource"
}
$resolvedTarget = [System.IO.Path]::GetFullPath($TargetUserDataDir)

function Assert-NoReparsePointAncestor {
    param([Parameter(Mandatory = $true)][string]$Path)

    $candidate = [System.IO.Path]::GetFullPath($Path)
    while (-not [string]::IsNullOrWhiteSpace($candidate)) {
        if (Test-Path -LiteralPath $candidate) {
            $item = Get-Item -LiteralPath $candidate -Force -ErrorAction Stop
            if (($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0) {
                throw "Cannot safely isolate through a junction or symbolic link: $candidate. Use verified non-linked paths."
            }
        }

        $parent = Split-Path -Parent $candidate
        if ([string]::IsNullOrWhiteSpace($parent) -or $parent -eq $candidate) {
            break
        }
        $candidate = $parent
    }
}

Assert-NoReparsePointAncestor -Path $resolvedSource
Assert-NoReparsePointAncestor -Path $resolvedTarget
$sourceWithSeparator = $resolvedSource.TrimEnd([System.IO.Path]::DirectorySeparatorChar, [System.IO.Path]::AltDirectorySeparatorChar) + [System.IO.Path]::DirectorySeparatorChar
$targetWithSeparator = $resolvedTarget.TrimEnd([System.IO.Path]::DirectorySeparatorChar, [System.IO.Path]::AltDirectorySeparatorChar) + [System.IO.Path]::DirectorySeparatorChar

if ([System.StringComparer]::OrdinalIgnoreCase.Equals($resolvedSource.TrimEnd('\', '/'), $resolvedTarget.TrimEnd('\', '/')) -or
    $resolvedTarget.StartsWith($sourceWithSeparator, [System.StringComparison]::OrdinalIgnoreCase) -or
    $resolvedSource.StartsWith($targetWithSeparator, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw 'SourceUserDataDir and TargetUserDataDir must be different, unrelated directories.'
}

function ConvertTo-NormalizedPath {
    param([Parameter(Mandatory = $true)][string]$Path)

    return [System.IO.Path]::GetFullPath($Path).TrimEnd([System.IO.Path]::DirectorySeparatorChar, [System.IO.Path]::AltDirectorySeparatorChar)
}

function Test-RunningAntigravityForPath {
    param([Parameter(Mandatory = $true)][string]$Path)

    $normalizedPath = ConvertTo-NormalizedPath -Path $Path
    $processes = Get-CimInstance Win32_Process -ErrorAction Stop | Where-Object {
        $_.Name -in @('Antigravity IDE.exe', 'Antigravity.exe')
    }

    foreach ($process in $processes) {
        if ([string]::IsNullOrWhiteSpace($process.CommandLine)) {
            throw "Cannot inspect Antigravity process $($process.ProcessId). Close Antigravity or inspect it before continuing."
        }

        $match = [regex]::Match($process.CommandLine, '--user-data-dir(?:=|\s+)(?:"([^"]+)"|([^\s]+))', [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)
        if (-not $match.Success) {
            if (-not [string]::IsNullOrWhiteSpace($env:APPDATA) -and [System.StringComparer]::OrdinalIgnoreCase.Equals($normalizedPath, (ConvertTo-NormalizedPath -Path (Join-Path $env:APPDATA 'Antigravity IDE')))) {
                return $process
            }
            continue
        }

        $processPath = if ($match.Groups[1].Success) { $match.Groups[1].Value } else { $match.Groups[2].Value }
        try {
            $normalizedProcessPath = ConvertTo-NormalizedPath -Path $processPath
        }
        catch {
            continue
        }

        if ([System.StringComparer]::OrdinalIgnoreCase.Equals($normalizedProcessPath, $normalizedPath)) {
            return $process
        }
    }

    return $null
}

if ($CopyReviewedSettings) {
    $sourceProcess = Test-RunningAntigravityForPath -Path $resolvedSource
    if ($null -ne $sourceProcess) {
        throw "Close Antigravity before copying settings. Process $($sourceProcess.ProcessId) still uses $resolvedSource."
    }
}

$targetParent = Split-Path -Parent $resolvedTarget
New-Item -ItemType Directory -Force -Path $targetParent | Out-Null

if (Test-Path -LiteralPath $resolvedTarget) {
    $targetProcess = Test-RunningAntigravityForPath -Path $resolvedTarget
    if ($null -ne $targetProcess) {
        throw "Close Antigravity before replacing the target profile. Process $($targetProcess.ProcessId) still uses $resolvedTarget."
    }

    if (-not (Test-Path -LiteralPath $resolvedTarget -PathType Container)) {
        throw "TargetUserDataDir is not a directory: $resolvedTarget"
    }

    $targetItems = @(Get-ChildItem -LiteralPath $resolvedTarget -Force -ErrorAction Stop)
    if ($targetItems.Count -gt 0) {
        throw "Target profile is not empty: $resolvedTarget. Leave it intact and choose a new empty target directory."
    }
}

New-Item -ItemType Directory -Force -Path $resolvedTarget | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $resolvedTarget 'User\globalStorage') | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $resolvedTarget 'User\workspaceStorage') | Out-Null

$copiedPaths = [System.Collections.Generic.List[string]]::new()
$safeRelativePaths = @(
    'User\settings.json',
    'User\keybindings.json',
    'User\snippets'
)

foreach ($relativePath in $(if ($CopyReviewedSettings) { $safeRelativePaths })) {
    $sourcePath = Join-Path $resolvedSource $relativePath
    if (-not (Test-Path -LiteralPath $sourcePath)) {
        continue
    }

    $targetPath = Join-Path $resolvedTarget $relativePath
    $targetDirectory = Split-Path -Parent $targetPath
    New-Item -ItemType Directory -Force -Path $targetDirectory | Out-Null
    Copy-Item -LiteralPath $sourcePath -Destination $targetPath -Recurse -Force
    [void]$copiedPaths.Add($relativePath)
}

$manifestPath = Join-Path $resolvedTarget 'codex-isolation.json'
$manifest = [ordered]@{
    schema_version = 1
    profile_id = $ProfileId
    intended_auth_mode = 'api-only'
    source_user_data_dir = $resolvedSource
    target_user_data_dir = $resolvedTarget
    copied_paths = @($copiedPaths)
    excluded_state = @(
        'User\globalStorage\state.vscdb',
        'User\globalStorage\storage.json',
        'User\workspaceStorage',
        'Cookies',
        'Local Storage',
        'Session Storage',
        'Network',
        'Service Worker',
        'WebStorage',
        'Cache',
        'Code Cache',
        'blob_storage'
    )
    auth_and_cookie_migration = 'not_copied'
    created_utc = [DateTime]::UtcNow.ToString('o')
} | ConvertTo-Json -Depth 4
[System.IO.File]::WriteAllText($manifestPath, $manifest, [System.Text.UTF8Encoding]::new($false))

Write-Output "Source Antigravity UserDataDir: $resolvedSource"
Write-Output "Isolated Antigravity UserDataDir: $resolvedTarget"
Write-Output "Isolation manifest: $manifestPath"
Write-Output "Copied reviewed settings: $($copiedPaths.Count)"
Write-Output 'The source profile remains untouched. Choose a new target if an earlier target contains data.'
Write-Output 'Excluded state.vscdb, storage.json, workspace state, cookies, local storage, and OAuth/browser data.'
Write-Output 'The Codex profile must remain API-only; do not sign the customer ChatGPT account into this UserDataDir.'
