#nullable enable
using System;
using System.IO;
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
        public LoggingHelper(object? pythonLogger)
        {
            _pythonLogger = pythonLogger;

            // Sidecar capture: when PYREVIT_CSHARP_LOG_FILE is set, mirror every log
            // line to a flat text file. Sidesteps the C#-mlogger → Python FileHandler
            // bridge issue where _pythonLogger.debug(...) calls don't reach runtime.log.
            var path = Environment.GetEnvironmentVariable("PYREVIT_CSHARP_LOG_FILE");
            _sidecarPath = string.IsNullOrWhiteSpace(path) ? null : path;
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
