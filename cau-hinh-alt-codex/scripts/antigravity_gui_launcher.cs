using System;
using System.ComponentModel;
using System.Runtime.InteropServices;
using System.IO;
using System.Text;
using System.Text.RegularExpressions;
using System.Windows.Forms;

internal static class AntigravityGuiLauncher
{
    [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
    private struct StartupInfo
    {
        public int cb;
        public string reserved, desktop, title;
        public int x, y, xSize, ySize, xCountChars, yCountChars, fillAttribute, flags;
        public short showWindow, reserved2Size;
        public IntPtr reserved2, standardInput, standardOutput, standardError;
    }

    [StructLayout(LayoutKind.Sequential)]
    private struct ProcessInformation
    {
        public IntPtr process, thread;
        public uint processId, threadId;
    }

    [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    private static extern bool CreateProcess(string application, StringBuilder commandLine,
        IntPtr processAttributes, IntPtr threadAttributes, bool inheritHandles, uint flags,
        IntPtr environment, string currentDirectory, ref StartupInfo startup,
        out ProcessInformation process);

    [DllImport("kernel32.dll")]
    private static extern bool CloseHandle(IntPtr handle);

    private static string QuoteArgument(string argument)
    {
        StringBuilder result = new StringBuilder("\"");
        int backslashes = 0;
        foreach (char character in argument)
        {
            if (character == '\\')
            {
                backslashes++;
                continue;
            }
            if (character == '"')
            {
                result.Append('\\', backslashes * 2 + 1).Append('"');
                backslashes = 0;
                continue;
            }
            result.Append('\\', backslashes).Append(character);
            backslashes = 0;
        }
        result.Append('\\', backslashes * 2).Append('"');
        return result.ToString();
    }

    [STAThread]
    private static void Main(string[] args)
    {
        try
        {
            string configPath = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "AntigravityLauncher.config");
            string[] settings = File.ReadAllLines(configPath, Encoding.UTF8);
            if (settings.Length != 3)
                throw new InvalidOperationException("Launcher configuration must contain three lines.");
            string application = Path.GetFullPath(settings[0].Trim());
            string codexHome = Path.GetFullPath(settings[1].Trim());
            string keyName = settings[2].Trim();
            if (!File.Exists(application) || !File.Exists(Path.Combine(codexHome, "config.toml")))
                throw new InvalidOperationException("The application or isolated Codex configuration is missing.");
            if (!Regex.IsMatch(keyName, @"^[A-Za-z_][A-Za-z0-9_]*$"))
                throw new InvalidOperationException("The API key environment variable name is invalid.");
            string keyValue = Environment.GetEnvironmentVariable(keyName, EnvironmentVariableTarget.Process);
            if (String.IsNullOrWhiteSpace(keyValue))
                keyValue = Environment.GetEnvironmentVariable(keyName, EnvironmentVariableTarget.User);
            if (String.IsNullOrWhiteSpace(keyValue))
                throw new InvalidOperationException("The API key environment variable is missing.");
            Environment.SetEnvironmentVariable("CODEX_HOME", codexHome);
            Environment.SetEnvironmentVariable(keyName, keyValue);
            Environment.SetEnvironmentVariable("ELECTRON_RUN_AS_NODE", null);
            StringBuilder commandLine = new StringBuilder(QuoteArgument(application));
            foreach (string argument in args)
                commandLine.Append(' ').Append(QuoteArgument(argument));
            StartupInfo startup = new StartupInfo();
            startup.cb = Marshal.SizeOf(typeof(StartupInfo));
            ProcessInformation process;
            if (!CreateProcess(application, commandLine, IntPtr.Zero, IntPtr.Zero, false,
                    0x01000008, IntPtr.Zero, Path.GetDirectoryName(application), ref startup, out process))
                throw new Win32Exception(Marshal.GetLastWin32Error());
            CloseHandle(process.thread);
            CloseHandle(process.process);
        }
        catch (Exception error)
        {
            MessageBox.Show(error.Message, "Antigravity launcher", MessageBoxButtons.OK, MessageBoxIcon.Error);
            Environment.ExitCode = 1;
        }
    }
}
