# pyRevit ModularPipelines build

C# ModularPipelines project that replaces the YAML-heavy CI steps previously driven by `pipenv run pyrevit ...`.

## Prerequisites

- .NET 10 SDK (preinstalled on `windows-2025` runners)
- `dotnet`, `msbuild`, `go` on PATH
- Inno Setup 6 (`ISCC.exe`) for installer builds — preinstalled on `windows-2025`
- WiX Toolset v3.x build tools for the legacy CLI MSI project — preinstalled on `windows-2025`
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

### Build DLLs from the command line

The `ci` pipeline mode replaces `pipenv run pyrevit build products` (and the old CI stamping steps on the main repo). It builds all product DLLs, tools, and engines into `bin/`:

```powershell
cd build

# Unsigned product build (no version stamping; Channel=none by default)
dotnet run -c Release -- ci

# WIP-style stamping + product build (matches develop push on the main repo)
$env:Build__Channel = 'wip'
dotnet run -c Release -- ci

# Release-style stamping + product build (matches master / tag CI on the main repo)
$env:Build__Channel = 'release'
$env:DOTNET_ENVIRONMENT = 'Production'
dotnet run -c Release -- ci
```

Debug configuration (legacy `pipenv run pyrevit build products Debug`):

```powershell
dotnet run -c Debug -- ci
```

Outputs land under `bin/` (`netfx/`, `netcore/`, engines, CLI, doctor, autocomplete, etc.). LibGit2 native DLL verification runs at the end of `ci`.

Run unit tests:

```powershell
dotnet test tests/Build.Tests.csproj -c Release
```

### Pipeline modes

| Args | Purpose |
|------|---------|
| `ci` (default) | Stamp versions, build products, verify LibGit2, stage release metadata |
| `pack` | Restore CI-stamped metadata (if present), build Inno/MSI installers and Chocolatey package (requires `bin/`) |
| `sign` | Sign binaries, installers, and `.nupkg` via `sign code trusted-signing` |
| `publish` | Generate release notes, create draft GitHub release, push Chocolatey |
| `winget` | Submit WinGet manifest PRs (after GitHub release is published) |
| `notify` | Comment on linked GitHub issues |

Combine modes as needed, e.g. WIP pack+sign:

```powershell
dotnet run -c Release -- pack sign
```

After downloading CI artifacts locally (`bin/` + `ci-stamped/` at the repo root), `pack` restores stamped installer/version files from `ci-stamped/` before building installers.

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

On GitHub Actions, version stamping on the main repo is gated by `Build__Channel` **and** `GITHUB_REPOSITORY == pyrevitlabs/pyRevit`.

## GitHub workflows

- [`ci.yml`](../.github/workflows/ci.yml) — `dotnet run -- ci` + unit tests
- [`wip.yml`](../.github/workflows/wip.yml) — `dotnet run -- pack sign`
- [`release.yml`](../.github/workflows/release.yml) — `dotnet run -- release pack sign publish`
- [`winget.yml`](../.github/workflows/winget.yml) — `dotnet run -- winget` (on release published)

The legacy Python CLI in [`dev/pyrevit.py`](../dev/pyrevit.py) remains available for local/manual workflows during transition.
