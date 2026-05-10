using System.Diagnostics;
using Microsoft.Web.WebView2.WinForms;

namespace DroidShield.Desktop;

internal static class Program
{
    private const int Port = 8765;
    private static readonly Uri AppUri = new($"http://127.0.0.1:{Port}/");

    [STAThread]
    private static void Main()
    {
        try
        {
            DesktopLog.Write("Starting DroidShield desktop host.");
            ApplicationConfiguration.Initialize();
            using var server = LocalServer.EnsureRunning(Port);
            Application.Run(new MainForm(AppUri));
            DesktopLog.Write("Desktop host exited normally.");
        }
        catch (Exception ex)
        {
            DesktopLog.Write("Fatal startup error: " + ex);
            MessageBox.Show(
                ex.Message,
                "DroidShield failed to start",
                MessageBoxButtons.OK,
                MessageBoxIcon.Error
            );
        }
    }
}

internal sealed class MainForm : Form
{
    private readonly Uri _appUri;
    private readonly WebView2 _webView = new()
    {
        Dock = DockStyle.Fill,
        DefaultBackgroundColor = Color.FromArgb(245, 247, 250),
    };

    public MainForm(Uri appUri)
    {
        _appUri = appUri;
        Text = "DroidShield";
        Width = 1280;
        Height = 820;
        MinimumSize = new Size(980, 640);
        StartPosition = FormStartPosition.CenterScreen;

        var iconPath = Path.Combine(AppContext.BaseDirectory, "droidshield.ico");
        if (File.Exists(iconPath))
        {
            Icon = new Icon(iconPath);
        }

        Controls.Add(_webView);
        Shown += async (_, _) => await InitializeWebView();
    }

    private async Task InitializeWebView()
    {
        try
        {
            DesktopLog.Write("Initializing WebView2.");
            await _webView.EnsureCoreWebView2Async();
            _webView.CoreWebView2.Settings.AreDefaultContextMenusEnabled = false;
            _webView.CoreWebView2.Settings.AreDevToolsEnabled = false;
            _webView.CoreWebView2.Navigate(_appUri.ToString());
            DesktopLog.Write("WebView2 navigated to " + _appUri);
        }
        catch (Exception ex)
        {
            DesktopLog.Write("WebView2 initialization error: " + ex);
            MessageBox.Show(
                ex.Message,
                "DroidShield window failed to load",
                MessageBoxButtons.OK,
                MessageBoxIcon.Error
            );
        }
    }
}

internal sealed class LocalServer : IDisposable
{
    private static readonly HttpClient HttpClient = new()
    {
        Timeout = TimeSpan.FromSeconds(2.5),
    };

    private readonly Process? _process;

    private LocalServer(Process? process)
    {
        _process = process;
    }

    public static LocalServer EnsureRunning(int port)
    {
        if (IsHealthy(port))
        {
            DesktopLog.Write("Existing UI server is healthy.");
            return new LocalServer(null);
        }

        var repoRoot = FindRepoRoot();
        DesktopLog.Write("Starting Python UI server from " + repoRoot);
        var process = Process.Start(
            new ProcessStartInfo
            {
                FileName = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.Windows), "py.exe"),
                Arguments = $"-3.11 -m droidshield.cli ui --port {port} --no-open",
                WorkingDirectory = repoRoot,
                UseShellExecute = false,
                CreateNoWindow = true,
                WindowStyle = ProcessWindowStyle.Hidden,
            }
        );

        var deadline = DateTimeOffset.UtcNow.AddSeconds(10);
        while (DateTimeOffset.UtcNow < deadline)
        {
            if (IsHealthy(port))
            {
                DesktopLog.Write("Python UI server is healthy.");
                return new LocalServer(process);
            }
            Thread.Sleep(250);
        }

        throw new InvalidOperationException("DroidShield UI did not start.");
    }

    public void Dispose()
    {
        if (_process is { HasExited: false })
        {
            _process.Kill(entireProcessTree: true);
        }
    }

    private static bool IsHealthy(int port)
    {
        try
        {
            using var response = HttpClient.GetAsync($"http://127.0.0.1:{port}/").GetAwaiter().GetResult();
            return response.IsSuccessStatusCode;
        }
        catch
        {
            return false;
        }
    }

    private static string FindRepoRoot()
    {
        var current = new DirectoryInfo(AppContext.BaseDirectory);
        while (current is not null)
        {
            if (File.Exists(Path.Combine(current.FullName, "pyproject.toml")) && Directory.Exists(Path.Combine(current.FullName, "src")))
            {
                return current.FullName;
            }
            current = current.Parent;
        }

        return @"C:\repos\Pro-AI-Server";
    }
}

internal static class DesktopLog
{
    private static readonly string LogPath = Path.Combine(
        Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
        "DroidShield",
        "desktop.log"
    );

    public static void Write(string message)
    {
        try
        {
            Directory.CreateDirectory(Path.GetDirectoryName(LogPath)!);
            File.AppendAllText(LogPath, $"{DateTimeOffset.Now:u} {message}{Environment.NewLine}");
        }
        catch
        {
            // Logging must never prevent app startup.
        }
    }
}
