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

if (-not ('CodexDetachedLaunch' -as [type])) {
    Add-Type -TypeDefinition @"
using System;
using System.ComponentModel;
using System.Runtime.InteropServices;
using System.Text;

public static class CodexDetachedLaunch {
    [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
    private struct StartupInfo {
        public int cb;
        public string reserved;
        public string desktop;
        public string title;
        public int x, y, xSize, ySize, xCountChars, yCountChars, fillAttribute, flags;
        public short showWindow, reserved2Size;
        public IntPtr reserved2, standardInput, standardOutput, standardError;
    }
    [StructLayout(LayoutKind.Sequential)]
    private struct ProcessInformation {
        public IntPtr process, thread;
        public uint processId, threadId;
    }
    [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    private static extern bool CreateProcess(string application, StringBuilder commandLine,
        IntPtr processAttributes, IntPtr threadAttributes, bool inheritHandles, uint flags,
        IntPtr environment, string currentDirectory, ref StartupInfo startup,
        out ProcessInformation process);
    [DllImport("kernel32.dll", SetLastError = true)]
    private static extern uint WaitForSingleObject(IntPtr handle, uint milliseconds);
    [DllImport("kernel32.dll")]
    private static extern bool CloseHandle(IntPtr handle);

    public static uint Start(string executable, string arguments, bool wait) {
        StartupInfo startup = new StartupInfo();
        startup.cb = Marshal.SizeOf(typeof(StartupInfo));
        ProcessInformation process;
        StringBuilder commandLine = new StringBuilder();
        commandLine.Append('"').Append(executable).Append('"');
        if (!String.IsNullOrEmpty(arguments)) commandLine.Append(' ').Append(arguments);
        if (!CreateProcess(executable, commandLine, IntPtr.Zero, IntPtr.Zero, false,
                0x01000008, IntPtr.Zero, null, ref startup, out process))
            throw new Win32Exception(Marshal.GetLastWin32Error());
        try {
            if (wait && WaitForSingleObject(process.process, 0xFFFFFFFF) == 0xFFFFFFFF)
                throw new Win32Exception(Marshal.GetLastWin32Error());
            return process.processId;
        } finally {
            CloseHandle(process.thread);
            CloseHandle(process.process);
        }
    }
}
"@
}

$oldCodexHome = $env:CODEX_HOME
$oldElectronRunAsNode = $env:ELECTRON_RUN_AS_NODE
try {
    $env:CODEX_HOME = $codexHome
    Remove-Item Env:ELECTRON_RUN_AS_NODE -ErrorAction SilentlyContinue
    $processId = [CodexDetachedLaunch]::Start($resolvedAntigravity, ($childArguments -join ' '), [bool]$Wait)
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

Write-Output "Antigravity PID: $processId"
Write-Output "CODEX_HOME: $codexHome"
Write-Output 'API key and browser cookies are not printed.'

