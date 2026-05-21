#nullable enable
using System;
using System.Diagnostics;
using System.IO;
using pyRevitExtensionParser;
using pyRevitLabs.NLog;

namespace pyRevitAssemblyBuilder.SessionManager
{
    /// <summary>
    /// Helper class for logging using Python's logger.
    /// </summary>
    public class LoggingHelper : ILogger
    {
        private static readonly Logger nlog = LogManager.GetCurrentClassLogger();
        private static readonly object _sidecarLock = new object();
        private readonly dynamic? _pythonLogger;
        private readonly string? _sidecarPath;

        /// <summary>
        /// Initializes a new instance of the <see cref="LoggingHelper"/> class.
        /// </summary>
        /// <param name="pythonLogger">The Python logger instance passed from Python code.</param>
        /// <param name="revitVersion">
        /// Revit version (e.g. "2025") used to build the default sidecar path.
        /// When null/empty the sidecar stays disabled even if config opts in, since we'd have
        /// nowhere conventional to put the file.
        /// </param>
        public LoggingHelper(object? pythonLogger, string? revitVersion = null)
        {
            _pythonLogger = pythonLogger;

            // Sidecar capture: when [core] csharp_filelogging = true in pyrevit_config.ini,
            // mirror every log line to a per-process file alongside runtime.log. Sidesteps
            // the C#-mlogger → Python FileHandler bridge issue where _pythonLogger.debug(...)
            // calls don't reach runtime.log. Swallow any config-read failure so logging never
            // breaks the loader.
            _sidecarPath = ResolveSidecarPath(revitVersion);
        }

        /// <summary>
        /// Returns the per-process sidecar log path when <c>csharp_filelogging</c> is enabled
        /// and the Revit version is known, or <c>null</c> otherwise. The path mirrors the
        /// Python <c>runtime.log</c> convention used by <see cref="PyRevitConfig.FileLogging"/>:
        /// <c>%APPDATA%\pyRevit\{revitVersion}\pyRevit_{revitVersion}_{pid}_csharp_loader.log</c>.
        /// </summary>
        private static string? ResolveSidecarPath(string? revitVersion)
        {
            try
            {
                if (!PyRevitConfig.Load().CSharpFileLogging)
                    return null;

                if (string.IsNullOrWhiteSpace(revitVersion))
                    return null;

                var roaming = Environment.GetEnvironmentVariable("APPDATA");
                if (string.IsNullOrWhiteSpace(roaming))
                    return null;

                var dir = Path.Combine(roaming, "pyRevit", revitVersion);
                Directory.CreateDirectory(dir);

                var pid = Process.GetCurrentProcess().Id;
                var fileName = $"pyRevit_{revitVersion}_{pid}_csharp_loader.log";
                return Path.Combine(dir, fileName);
            }
            catch
            {
                // Intentionally swallowed - sidecar is best-effort.
                return null;
            }
        }

        /// <summary>
        /// Appends a timestamped line to the sidecar log file when configured.
        /// Swallows IO exceptions: instrumentation must never break the loader.
        /// </summary>
        private void WriteSidecar(string level, string message)
        {
            if (_sidecarPath == null)
                return;

            try
            {
                lock (_sidecarLock)
                {
                    File.AppendAllText(
                        _sidecarPath,
                        $"{DateTime.Now:yyyy-MM-dd HH:mm:ss.fff} {level} {message}{Environment.NewLine}");
                }
            }
            catch
            {
                // Intentionally swallowed — sidecar is best-effort.
            }
        }

        /// <summary>
        /// Logs an informational message.
        /// </summary>
        /// <param name="message">The message to log.</param>
        public void Info(string message)
        {
            try
            {
                if (_pythonLogger != null)
                    _pythonLogger.info(message);
                else
                    nlog.Info(message);
            }
            catch (Exception ex)
            {
                nlog.Error(ex, "Logging (Info) failed");
            }
            WriteSidecar("INFO ", message);
        }

        /// <summary>
        /// Logs a debug message.
        /// </summary>
        /// <param name="message">The message to log.</param>
        public void Debug(string message)
        {
            try
            {
                if (_pythonLogger != null)
                    _pythonLogger.debug(message);
                else
                    nlog.Debug(message);
            }
            catch (Exception ex)
            {
                nlog.Error(ex, "Logging (Debug) failed");
            }
            WriteSidecar("DEBUG", message);
        }

        /// <summary>
        /// Logs an error message.
        /// </summary>
        /// <param name="message">The message to log.</param>
        public void Error(string message)
        {
            try
            {
                if (_pythonLogger != null)
                    _pythonLogger.error(message);
                else
                    nlog.Error(message);
            }
            catch (Exception ex)
            {
                nlog.Error(ex, "Logging (Error) failed");
            }
            WriteSidecar("ERROR", message);
        }

        /// <summary>
        /// Logs a warning message.
        /// </summary>
        /// <param name="message">The message to log.</param>
        public void Warning(string message)
        {
            try
            {
                if (_pythonLogger != null)
                    _pythonLogger.warning(message);
                else
                    nlog.Warn(message);
            }
            catch (Exception ex)
            {
                nlog.Error(ex, "Logging (Warning) failed");
            }
            WriteSidecar("WARN ", message);
        }
    }
}
