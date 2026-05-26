# Releasing pyRevit

pyRevit uses a tag-driven release pipeline. CI builds unsigned DLLs on pushes to `develop` / `master` (and on `v*` tag pushes) **when changes touch build-related paths** (e.g. `bin/`, `dev/`, `extensions/`, `pyrevitlib/`, `release/`, `site-packages/`) and uploads them as `unsigned-bin-<sha>`. Two follow-up workflows consume that artifact and produce the final signed installers:

- `wip.yml`: downloads `unsigned-bin-<sha>`, signs DLLs, builds Inno + MSI installers (so signed DLLs are packed inside), signs installers, builds the Chocolatey package (its embedded SHA is taken over the signed installer), signs the `.nupkg` (NuGet author signature via Azure Trusted Signing), uploads the WIP artifact, and notifies issue threads.
- `release.yml`: same sign-then-build-then-sign-then-pack-then-sign flow as `wip.yml`, plus release-notes generation, draft GitHub release publishing, and Chocolatey push.

This split guarantees that:

- every DLL shipped inside an installer carries an Authenticode signature,
- the installer `.exe`/`.msi` themselves are Authenticode-signed,
- the `.nupkg`'s embedded checksum matches the signed installer users actually download, and
- the `.nupkg` itself carries a NuGet author signature so Chocolatey clients can verify it.

This document captures the manual maintainer ritual that the old `main.yml` used to automate inline (auto-commit, auto-tag, next-version bump).

## Pre-flight

- Confirm `develop` is green (latest CI run on `develop` succeeded and `wip.yml` produced the signed artifact).
- Confirm `pyrevitlib/pyrevit/version` and `release/version` reflect the version you intend to publish. `release.yml` will hard-fail if the tag name does not match `pyrevitlib/pyrevit/version`.
- Make sure required secrets are configured in the `production` environment:
  - `AZURE_TENANT_ID`, `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`, `AZURE_ENDPOINT`, `AZURE_CODE_SIGNING_NAME`, `AZURE_CERT_PROFILE_NAME`
  - `CHOCO_TOKEN`

## Refreshing vendored dependencies (maintainer-only)

The DLLs under `dev/libs/netfx/` and `dev/libs/netcore/` (`pyRevitLabs.MahAppsMetro.dll`, `pyRevitLabs.NLog.dll`, `pyRevitLabs.Json.dll`, `pyRevitLabs.PythonNet.dll`, `ControlzEx.dll`, ...) are vendored: projects that consume these DLLs reference them via `HintPath="$(PyRevitDevLibsDir)\..."`, and the files are committed to git. CI does **not** rebuild them — `pipenv run pyrevit build products` only invokes labs / engines / runtime / telem / autocmp.

When you bump a submodule under `dev/modules/` (MahApps.Metro, NLog, Newtonsoft.Json, Python.Net, IronPython2/3), you need to refresh the vendored output **locally** and commit the result:

```bash
# one-time setup: install the .NET Core 3.1 SDK (MahApps.Metro netcore TFM
# targets netcoreapp3.1; it's EOL but still publicly available)
winget install Microsoft.DotNet.SDK.3_1

# refresh dev/libs/{netfx,netcore} from the submodule sources
pipenv run pyrevit build deps

# review and commit the diff
git add dev/libs
git commit -m "chore(libs): refresh vendored deps for <submodule> bump"
```

This keeps the CI hot path on the SDKs preinstalled on `windows-2025` (.NET 4.8 + .NET 8 + .NET 10) and avoids depending on the EOL 3.1 archives in a hosted runner. If a submodule ever ships only via NuGet (e.g. modern MahApps.Metro), retire the local build from `_labs.build_deps` and switch the `.csproj` to a `PackageReference` instead of `HintPath`.

## Cut a release

1. From a clean local clone on `develop`, stamp the build as a release:
   ```bash
   pipenv run pyrevit set build release
   ```
   This updates `pyrevitlib/pyrevit/version` and related build info files.

2. Commit the version changes and merge them into `master` via your normal PR flow (or push directly if your branch protection allows it).
   ```bash
   git add -A
   git commit -m "release: vX.Y.Z"
   git push
   ```

3. Tag the release commit on `master`. The tag name must exactly match `pyrevitlib/pyrevit/version` prefixed with `v`:
   ```bash
   git checkout master
   git pull
   git tag "v$(cat pyrevitlib/pyrevit/version)"
   git push origin "v$(cat pyrevitlib/pyrevit/version)"
   ```

4. Pushing the tag triggers two workflows in parallel:
   - `ci.yml` rebuilds DLLs on the tagged commit and uploads `unsigned-bin-<sha>` (DLLs only; installers are no longer built in CI).
   - `release.yml` starts immediately and polls for the matching CI run (via `gh run watch`). Once CI finishes it downloads `unsigned-bin-<sha>`, signs the DLLs, runs `pipenv run pyrevit build installers` so the Inno + MSI installers pack signed DLLs, signs the resulting installer `.exe`/`.msi`, runs `pipenv run pyrevit build choco` so the `.nupkg` checksum is computed over the signed installer, signs the `.nupkg` with a NuGet author signature, generates release notes, publishes a draft GitHub release, notifies issue threads, and pushes to Chocolatey.

5. Open the draft release on GitHub, review the auto-generated notes, then publish it.

## Post-release

Bump `develop` to the next development version so subsequent WIP builds carry the right number:

```bash
git checkout develop
git pull --rebase origin develop
pipenv run pyrevit set next-version
git add -A
git commit -m "chore: bump next version"
git push origin develop
```

## Hotfix flow

Same as above, but cut the release commit from `master` (or a `hotfix/*` branch off `master`) instead of `develop`. After tagging and publishing, cherry-pick the version bump back into `develop`.

## Troubleshooting

- **Release fails on `Validate tag matches version`**: the tag (e.g. `v4.8.16`) doesn't match `pyrevitlib/pyrevit/version`. Delete and recreate the tag with the right name, or update the version file and re-tag.
- **Release fails on `Wait for CI to complete on tagged commit`**: CI either failed or didn't start within 10 minutes of the tag push. Investigate the CI run for the tagged SHA; once it is green, re-run `release.yml`.
- **Release fails on `Download unsigned bin artifact`**: the CI run exists but the expected `unsigned-bin-<sha>` artifact is missing (most often because CI failed before the upload step). Fix CI and re-run `release.yml`.
- **Release fails on `Build Installers`**: Inno Setup (`iscc`) or MSBuild on the AIP files failed. Both run on `windows-2025`, which preinstalls Inno Setup 6; MSBuild is provisioned via `microsoft/setup-msbuild`. Check the step log for the underlying compiler error.
- **Release fails on `Build Choco Package`**: `choco pack` failed, or the upstream signed installer was missing when the SHA was computed. Confirm `Sign installers` produced the expected `dist/*.exe`/`.msi` outputs before this step ran.
- **Release fails on `Sign Choco Package`**: this step uses the `dotnet sign` CLI (installed via `dotnet tool install --global sign --prerelease`) and authenticates to Azure Trusted Signing via the `AZURE_TENANT_ID` / `AZURE_CLIENT_ID` / `AZURE_CLIENT_SECRET` env vars (DefaultAzureCredential chain). Common causes: (a) the certificate profile lacks the `1.3.6.1.5.5.7.3.3` Code Signing EKU required for NuGet author signing; (b) the App Registration is missing the `Trusted Signing Certificate Profile Signer` role on the Signing Account; (c) the `--prerelease` flag was removed and `sign` is no longer marked prerelease (drop `--prerelease` once the tool has a stable GA release). The previous attempt used `Azure/artifact-signing-action`, but its v2.0.0 PowerShell module routes `.nupkg` to `signtool.exe`, which doesn't recognize the format. Don't switch back without verifying upstream support for NuGet via that action.
- **Signing step fails**: verify the `production` environment secrets above are present and not expired.
- **Choco push fails**: check `CHOCO_TOKEN` and that `dist/pyrevit-cli.<version>.nupkg` was actually produced by `Build Choco Package`.
