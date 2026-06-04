using System.Text.RegularExpressions;
using Build.Helpers;
using Build.Models;
using Build.Options;
using Microsoft.Extensions.Options;
using ModularPipelines.Attributes;
using ModularPipelines.Context;
using ModularPipelines.Git.Extensions;
using ModularPipelines.Git.Options;
using ModularPipelines.GitHub.Attributes;
using ModularPipelines.GitHub.Extensions;
using ModularPipelines.Modules;
using ModularPipelines.Options;

namespace Build.Modules;

[SkipIfNoGitHubToken]
public sealed class NotifyIssuesModule(IOptions<BuildOptions> buildOptions) : Module
{
    protected override async Task ExecuteModuleAsync(IModuleContext context, CancellationToken cancellationToken)
    {
        var versionInfo = VersionHelper.CreateVersionInfo(VersionHelper.ReadBuildVersion());
        var notifyUrl = buildOptions.Value.NotifyUrl;
        if (string.IsNullOrWhiteSpace(notifyUrl))
        {
            throw new InvalidOperationException("NotifyUrl is required for issue notifications.");
        }

        var channel = buildOptions.Value.Channel;
        var previousTag = channel.Equals("release", StringComparison.OrdinalIgnoreCase)
            ? await FindPreviousTagAsync(context, cancellationToken)
            : await FindLatestTagAsync(context, cancellationToken);

        var comment = channel.Equals("release", StringComparison.OrdinalIgnoreCase)
            ? $":package: New public release is available for [{versionInfo.BuildVersion}]({notifyUrl})"
            : $":package: New work-in-progress (wip) builds are available for [{versionInfo.BuildVersion}]({notifyUrl})";

        var changes = await CollectChangesAsync(context, previousTag, cancellationToken);
        var repositoryInfo = context.GitHub().RepositoryInfo;

        foreach (var ticket in changes.Select(change => change.Ticket).Where(ticket => ticket is not null).Distinct())
        {
            await context.GitHub().Client.Issue.Comment.Create(
                repositoryInfo.Owner,
                repositoryInfo.RepositoryName,
                int.Parse(ticket!, System.Globalization.CultureInfo.InvariantCulture),
                comment);
        }
    }

    private static async Task<string> FindLatestTagAsync(IModuleContext context, CancellationToken cancellationToken)
    {
        var result = await context.Git().Commands.ForEachRef(
            new GitForEachRefOptions
            {
                Sort = "-creatordate",
                Format = "%(refname)",
                Count = "1",
                Arguments = ["refs/tags/v*"],
            },
            new CommandExecutionOptions { LogSettings = CommandLoggingOptions.Silent },
            cancellationToken);

        return result.StandardOutput
            .Split('\n', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries)
            .Select(tag => tag.Replace("refs/tags/", string.Empty, StringComparison.Ordinal))
            .FirstOrDefault() ?? "HEAD~1";
    }

    private static async Task<string> FindPreviousTagAsync(IModuleContext context, CancellationToken cancellationToken)
    {
        var result = await context.Git().Commands.ForEachRef(
            new GitForEachRefOptions
            {
                Sort = "-creatordate",
                Format = "%(refname)",
                Count = "2",
                Arguments = ["refs/tags/v*"],
            },
            new CommandExecutionOptions { LogSettings = CommandLoggingOptions.Silent },
            cancellationToken);

        var tags = result.StandardOutput
            .Split('\n', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries)
            .Select(tag => tag.Replace("refs/tags/", string.Empty, StringComparison.Ordinal))
            .ToArray();

        return tags.Length >= 2 ? tags[1] : tags.FirstOrDefault() ?? "HEAD~1";
    }

    private static async Task<IReadOnlyList<ChangeTicket>> CollectChangesAsync(
        IModuleContext context,
        string previousTag,
        CancellationToken cancellationToken)
    {
        var result = await context.Git().Commands.Log(
            new GitLogOptions
            {
                Pretty = "format:%h %s%n%b%n/",
                Arguments = [$"{previousTag}..HEAD"],
            });

        return ParseTickets(result.StandardOutput);
    }

    internal static IReadOnlyList<ChangeTicket> ParseTickets(string gitLog)
    {
        var tickets = new List<ChangeTicket>();
        var lines = gitLog.Split('\n');
        var index = 0;
        while (index < lines.Length)
        {
            var line = lines[index];
            if (string.IsNullOrWhiteSpace(line))
            {
                index++;
                continue;
            }

            var parts = line.Split(' ', 2);
            if (parts.Length == 2)
            {
                var match = Regex.Match(parts[1], @"#(\d+)");
                if (match.Success)
                {
                    tickets.Add(new ChangeTicket(match.Groups[1].Value));
                }
            }

            index++;
            while (index < lines.Length && !lines[index].StartsWith("/", StringComparison.Ordinal))
            {
                index++;
            }

            if (index < lines.Length)
            {
                index++;
            }
        }

        return tickets;
    }

    internal sealed record ChangeTicket(string Ticket);
}
