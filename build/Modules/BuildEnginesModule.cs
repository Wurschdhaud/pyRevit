using Build.Helpers;
using Build.Options;
using Microsoft.Extensions.Options;
using ModularPipelines.Attributes;
using ModularPipelines.Context;
using ModularPipelines.DotNet.Extensions;
using ModularPipelines.DotNet.Options;
using ModularPipelines.Modules;

namespace Build.Modules;

[DependsOn<BuildLabsModule>]
public sealed class BuildEnginesModule(IOptions<BuildOptions> buildOptions) : Module
{
    protected override async Task ExecuteModuleAsync(IModuleContext context, CancellationToken cancellationToken)
    {
        await context.DotNet().Build(new DotNetBuildOptions
        {
            ProjectSolution = PyRevitPaths.LoadersSolution,
            Configuration = buildOptions.Value.Configuration,
        }, cancellationToken: cancellationToken);
    }
}
