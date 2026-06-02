#nullable enable
using System;
using System.Diagnostics;
using System.IO;
using System.Reflection;
using Autodesk.Revit.UI;

namespace pyRevitAssemblyBuilder.SessionManager
{
    /// <summary>
    /// Owns the C# loader output window without taking a compile-time dependency on the runtime assembly.
    /// </summary>
    public class SessionOutput
    {
        private readonly MethodInfo? _writeMethod;
        private readonly MethodInfo? _selfDestructMethod;

        private SessionOutput(object outputWindow, object outputStream)
        {
            OutputWindow = outputWindow;
            OutputStream = outputStream;
            _writeMethod = outputStream.GetType().GetMethod("write", new[] { typeof(string) });
            _selfDestructMethod = outputWindow.GetType().GetMethod("SelfDestructTimer", new[] { typeof(int) });
        }

        public object OutputWindow { get; }
        public object OutputStream { get; }
        public bool HasErrors { get; private set; }

        public static SessionOutput? TryCreate(UIApplication uiApplication, string title, string outputId)
        {
            try
            {
                var runtimeAssembly = FindRuntimeAssembly();
                if (runtimeAssembly == null)
                    return null;

                var consoleType = runtimeAssembly.GetType("PyRevitLabs.PyRevit.Runtime.ScriptConsole");
                var streamType = runtimeAssembly.GetType("PyRevitLabs.PyRevit.Runtime.ScriptIO");
                if (consoleType == null || streamType == null)
                    return null;

                var outputWindow = Activator.CreateInstance(
                    consoleType,
                    new object?[] { false, uiApplication })
                    ?? throw new InvalidOperationException("Failed to create ScriptConsole.");

                TrySetMember(outputWindow, "OutputTitle", title);
                TrySetMember(outputWindow, "OutputId", outputId);
                TrySetMember(outputWindow, "IsSessionOutput", true);

                var outputStream = Activator.CreateInstance(streamType, new[] { outputWindow })
                    ?? throw new InvalidOperationException("Failed to create ScriptIO.");

                return new SessionOutput(outputWindow, outputStream);
            }
            catch (Exception ex)
            {
                Trace.WriteLine($"Failed to initialize pyRevit session output: {ex}");
                return null;
            }
        }

        public void WriteLine(string message)
        {
            try
            {
                if (_writeMethod != null)
                {
                    var content = message + Environment.NewLine;
                    const int chunkSize = 900;
                    for (var idx = 0; idx < content.Length; idx += chunkSize)
                    {
                        var length = Math.Min(chunkSize, content.Length - idx);
                        _writeMethod.Invoke(OutputStream, new object[] { content.Substring(idx, length) });
                    }
                }
                else
                {
                    Trace.WriteLine(message);
                }
            }
            catch (Exception ex)
            {
                Trace.WriteLine($"Failed to write to pyRevit session output: {ex}");
            }
        }

        public void MarkError()
        {
            HasErrors = true;
        }

        public void SelfDestructTimer(int seconds)
        {
            if (seconds <= 0)
                return;

            try
            {
                _selfDestructMethod?.Invoke(OutputWindow, new object[] { seconds });
            }
            catch (Exception ex)
            {
                Trace.WriteLine($"Failed to set pyRevit session output self-destruct timer: {ex}");
            }
        }

        private static Assembly? FindRuntimeAssembly()
        {
            var assembly = AssemblyCache.GetByPrefix("pyRevitLabs.PyRevit.Runtime");
            if (assembly != null)
                return assembly;

            var binDir = Path.GetDirectoryName(Assembly.GetExecutingAssembly().Location);
            if (string.IsNullOrEmpty(binDir) || !Directory.Exists(binDir))
                return null;

            var runtimeDlls = Directory.GetFiles(binDir, "pyRevitLabs.PyRevit.Runtime*.dll");
            if (runtimeDlls.Length == 0)
                return null;

            var loaded = Assembly.LoadFrom(runtimeDlls[0]);
            AssemblyCache.Add(loaded);
            return loaded;
        }

        private static void TrySetMember(object target, string memberName, object? value)
        {
            var targetType = target.GetType();
            var property = targetType.GetProperty(memberName, BindingFlags.Public | BindingFlags.Instance);
            if (property != null)
            {
                property.SetValue(target, value);
                return;
            }

            var field = targetType.GetField(memberName, BindingFlags.Public | BindingFlags.Instance);
            field?.SetValue(target, value);
        }
    }
}
