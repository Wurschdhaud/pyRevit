# pyRevit ModularPipelines build

C# ModularPipelines project that replaces the YAML-heavy CI steps previously driven by `pipenv run pyrevit ...`.

## Prerequisites

- .NET 10 SDK (preinstalled on `windows-2025` runners)
- `dotnet`, `msbuild`, `go` on PATH
- Inno Setup 6 (`ISCC.exe`) for installer builds
- WiX Toolset v3.x build tools for the legacy CLI MSI project
- `choco` for Chocolatey packaging/publish
- `wingetcreate` for WinGet manifest updates (release publish workflow)
- Azure Trusted Signing credentials for `sign` steps (production only)

Open [`pyRevit.Build.slnx`](pyRevit.Build.slnx) in Visual Studio to inspect or debug the build project.

## Run locally

From the repository root:

```powershell
cd build
dotnet run -c Release -- ci
```

### Pipeline modes

| Args | Purpose |
|------|---------|
| `ci` (default) | Stamp versions, build products, verify LibGit2, stage release metadata |
| `pack` | Build Inno/MSI installers and Chocolatey package (requires `bin/`) |
| `sign` | Sign binaries, installers, and `.nupkg` via `sign code trusted-signing` |
| `publish` | Generate release notes, create draft GitHub release, push Chocolatey |
| `winget` | Submit WinGet manifest PRs (after GitHub release is published) |
| `notify` | Comment on linked GitHub issues |

Combine modes as needed, e.g. WIP pack+sign:

```powershell
dotnet run -c Release -- pack sign
```

Release (tag builds, after CI artifacts are restored):

```powershell
dotnet run -c Release -- release pack sign publish
```

## Configuration

Non-secret defaults live in [`appsettings.json`](appsettings.json). Override via environment variables:

| Variable | Purpose |
|----------|---------|
| `Build__Channel` | `none`, `wip`, or `release` |
| `Build__NotifyUrl` | URL posted to linked issues |
| `Signing__TenantId`, `Signing__ClientId`, `Signing__ClientSecret`, `Signing__Endpoint`, `Signing__SigningAccountName`, `Signing__CertificateProfileName` | Azure Trusted Signing |
| `Publish__ChocoToken` | Chocolatey push token |
| `Publish__WingetToken` | WinGet manifest submit token |
| `GITHUB_TOKEN` | GitHub API access for releases/notify |

Set `DOTNET_ENVIRONMENT=Production` to load [`appsettings.Production.json`](appsettings.Production.json).

## GitHub workflows

- [`ci.yml`](../.github/workflows/ci.yml) — `dotnet run -- ci`
- [`wip.yml`](../.github/workflows/wip.yml) — `dotnet run -- pack sign`
- [`release.yml`](../.github/workflows/release.yml) — `dotnet run -- release pack sign publish`
- [`winget.yml`](../.github/workflows/winget.yml) — `dotnet run -- winget` (on release published)

The legacy Python CLI in [`dev/pyrevit.py`](../dev/pyrevit.py) remains available for local/manual workflows during transition.
