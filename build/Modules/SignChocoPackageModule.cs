using Build.Helpers;
using Build.Models;
using Build.Options;
using Microsoft.Extensions.Options;
using ModularPipelines.Attributes;
using ModularPipelines.Configuration;
using ModularPipelines.Context;
using ModularPipelines.Modules;

namespace Build.Modules;

[DependsOn<BuildChocoModule>]
public sealed class SignChocoPackageModule(
    IOptions<BuildOptions> buildOptions,
    IOptions<SigningOptions> signingOptions) : Module
{
    protected override ModuleConfiguration Configure()
        => ModuleConfiguration.Create().WithSigningGate(signingOptions).Build();
    protected override async Task ExecuteModuleAsync(IModuleContext context, CancellationToken cancellationToken)
    {
        var versionInfo = await GetVersionInfoAsync(context);
        var nupkgPath = Path.Combine(
            PyRevitPaths.DistPath,
            string.Format(PyRevitPaths.PyRevitChocoNupkgName, versionInfo.InstallVersion));

        if (!File.Exists(nupkgPath))
        {
            throw new FileNotFoundException("Chocolatey package was not found for signing.", nupkgPath);
        }

        await SigningHelper.SignFilesAsync(
            context,
            signingOptions.Value,
            buildOptions.Value,
            [nupkgPath],
            cancellationToken);
    }

    private static async Task<VersionInfo> GetVersionInfoAsync(IModuleContext context)
    {
        var stampResult = await context.GetModule<StampVersionModule>();
        if (stampResult.ValueOrDefault is not null)
        {
            return stampResult.ValueOrDefault;
        }

        return VersionHelper.CreateVersionInfo(VersionHelper.ReadBuildVersion());
    }
}
