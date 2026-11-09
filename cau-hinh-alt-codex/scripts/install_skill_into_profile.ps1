[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$SourceSkillPath,

    [Parameter(Mandatory = $true)]
    [string]$CodexHome,

    [string]$SkillName = 'cau-hinh-alt-codex'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

if ([string]::IsNullOrWhiteSpace($SkillName) -or $SkillName -match '[\\/:*?"<>|]' -or $SkillName -match '\.\.') {
    throw 'SkillName is invalid.'
}

$source = (Resolve-Path -LiteralPath $SourceSkillPath -ErrorAction Stop).Path
$sourceSkillFile = Join-Path $source 'SKILL.md'
if (-not (Test-Path -LiteralPath $sourceSkillFile -PathType Leaf)) {
    throw "SKILL.md not found in source skill path: $source"
}

$resolvedCodexHome = [System.IO.Path]::GetFullPath($CodexHome)
$skillsRoot = Join-Path $resolvedCodexHome 'skills'
$destination = Join-Path $skillsRoot $SkillName
$destinationParent = [System.IO.Path]::GetFullPath($skillsRoot)
$resolvedDestination = [System.IO.Path]::GetFullPath($destination)
if (-not $resolvedDestination.StartsWith($destinationParent + [System.IO.Path]::DirectorySeparatorChar, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Destination is outside CODEX_HOME skills directory: $resolvedDestination"
}

$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
if (Test-Path -LiteralPath $destination) {
    Move-Item -LiteralPath $destination -Destination "$destination.bak-$stamp"
}
New-Item -ItemType Directory -Force -Path $destination | Out-Null

$sourcePrefix = $source.TrimEnd([System.IO.Path]::DirectorySeparatorChar, [System.IO.Path]::AltDirectorySeparatorChar) + [System.IO.Path]::DirectorySeparatorChar
$excludedNames = @('auth.json', '.env')
foreach ($file in Get-ChildItem -LiteralPath $source -Recurse -File) {
    if ($excludedNames -contains $file.Name -or $file.Name -like '*.pem' -or $file.Name -like '*.key') {
        continue
    }

    $relativePath = $file.FullName.Substring($sourcePrefix.Length)
    $targetPath = Join-Path $destination $relativePath
    $targetDirectory = Split-Path -Parent $targetPath
    New-Item -ItemType Directory -Force -Path $targetDirectory | Out-Null
    Copy-Item -LiteralPath $file.FullName -Destination $targetPath -Force
}

Write-Output "Installed skill: $destination"
Write-Output 'Excluded auth.json, .env, PEM files, and key files.'