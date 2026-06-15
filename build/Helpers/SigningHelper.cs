using Build.Options;
using ModularPipelines.Context;
using ModularPipelines.Models;
using ModularPipelines.Options;

namespace Build.Helpers;

public static class SigningHelper
{
    public static async Task EnsureSignToolInstalledAsync(IModuleContext context, CancellationToken cancellationToken)
    {
        if (File.Exists(GetSignExecutablePath()))
        {
            return;
        }

        await context.Shell.Command.ExecuteCommandLineTool(
            new GenericCommandLineToolOptions("dotnet")
            {
                Arguments = ["tool", "install", "--global", "sign", "--prerelease"],
            },
            cancellationToken: cancellationToken);
    }

    public static string GetSignExecutablePath()
    {
        var userProfile = Environment.GetFolderPath(Environment.SpecialFolder.UserProfile);
        return Path.Combine(userProfile, ".dotnet", "tools", OperatingSystem.IsWindows() ? "sign.exe" : "sign");
    }

    public static async Task<CommandResult> SignFilesAsync(
        IModuleContext context,
        SigningOptions signingOptions,
        BuildOptions buildOptions,
        IEnumerable<string> files,
        CancellationToken cancellationToken)
    {
        var fileList = files.ToArray();
        if (fileList.Length == 0)
        {
            throw new InvalidOperationException("No files were provided for signing.");
        }

        await EnsureSignToolInstalledAsync(context, cancellationToken);

        var signExe = GetSignExecutablePath();
        var arguments = new List<string>
        {
            "code",
            "trusted-signing",
        };
        arguments.AddRange(fileList);
        arguments.AddRange(
        [
            "--trusted-signing-account", signingOptions.SigningAccountName,
            "--trusted-signing-certificate-profile", signingOptions.CertificateProfileName,
            "--trusted-signing-endpoint", signingOptions.Endpoint,
            "--file-digest", "SHA256",
            "--timestamp-url", buildOptions.TimestampUrl,
            "--timestamp-digest", "SHA256",
        ]);

        return await context.Shell.Command.ExecuteCommandLineTool(
            new GenericCommandLineToolOptions(signExe)
            {
                Arguments = arguments,
            },
            new CommandExecutionOptions
            {
                EnvironmentVariables = new Dictionary<string, string?>
                {
                    ["AZURE_TENANT_ID"] = signingOptions.TenantId,
                    ["AZURE_CLIENT_ID"] = signingOptions.ClientId,
                    ["AZURE_CLIENT_SECRET"] = signingOptions.ClientSecret,
                },
            },
            cancellationToken: cancellationToken);
    }

    public static IEnumerable<string> FindPyRevitBinaries(string rootFolder)
    {
        if (!Directory.Exists(rootFolder))
        {
            yield break;
        }

        foreach (var file in Directory.EnumerateFiles(rootFolder, "*.*", SearchOption.AllDirectories))
        {
            var name = Path.GetFileName(file);
            if (!name.StartsWith("pyrevit", StringComparison.OrdinalIgnoreCase)
                && !name.StartsWith("pyRevit", StringComparison.OrdinalIgnoreCase))
            {
                continue;
            }

            var extension = Path.GetExtension(file);
            if (extension.Equals(".exe", StringComparison.OrdinalIgnoreCase)
                || extension.Equals(".dll", StringComparison.OrdinalIgnoreCase))
            {
                yield return file;
            }
        }
    }
}
