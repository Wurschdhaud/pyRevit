using Build.Helpers;
using ModularPipelines.Attributes;
using ModularPipelines.Context;
using ModularPipelines.Models;
using ModularPipelines.Modules;
using ModularPipelines.Options;

namespace Build.Modules;

[DependsOn<BuildRuntimeModule>]
public sealed class BuildTelemModule : Module{
    protected override async Task ExecuteModuleAsync(IModuleContext context, CancellationToken cancellationToken)
    {
        await context.Shell.Command.ExecuteCommandLineTool(
            new GenericCommandLineToolOptions("git")
            {
                Arguments = ["config", "--global", "http.https://pkg.re.followRedirects", "true"],
            },
            cancellationToken: cancellationToken);

        await context.Shell.Command.ExecuteCommandLineTool(
            new GenericCommandLineToolOptions("go")
            {
                Arguments = ["get", "./..."],
            },
            new CommandExecutionOptions
            {
                WorkingDirectory = PyRevitPaths.TelemetryServerPath,
            },
            cancellationToken: cancellationToken);

        await context.Shell.Command.ExecuteCommandLineTool(
            new GenericCommandLineToolOptions("go")
            {
                Arguments = ["build", "-o", PyRevitPaths.TelemetryServerBin, PyRevitPaths.TelemetryServerMain],
            },
            new CommandExecutionOptions
            {
                WorkingDirectory = PyRevitPaths.TelemetryServerPath,
            },
            cancellationToken: cancellationToken);
    }
}
