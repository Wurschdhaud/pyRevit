# Releasing pyRevit

pyRevit uses a tag-driven release pipeline. CI builds unsigned artifacts on pushes to `develop` / `master` (and on `v*` tag pushes) **when changes touch build-related paths** (e.g. `bin/`, `dev/`, `extensions/`, `pyrevitlib/`, `release/`, `site-packages/`). Two follow-up workflows consume those artifacts:

- `wip.yml` signs and notifies after a successful `develop` build.
- `release.yml` signs, generates release notes, publishes a draft GitHub release, and pushes to Chocolatey when a `v*` tag is pushed.

This document captures the manual maintainer ritual that the old `main.yml` used to automate inline (auto-commit, auto-tag, next-version bump).

## Pre-flight

- Confirm `develop` is green (latest CI run on `develop` succeeded and `wip.yml` produced the signed artifact).
- Confirm `pyrevitlib/pyrevit/version` and `release/version` reflect the version you intend to publish. `release.yml` will hard-fail if the tag name does not match `pyrevitlib/pyrevit/version`.
- Make sure required secrets are configured in the `production` environment:
  - `AZURE_TENANT_ID`, `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`, `AZURE_ENDPOINT`, `AZURE_CODE_SIGNING_NAME`, `AZURE_CERT_PROFILE_NAME`
  - `CHOCO_TOKEN`

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
   git tag vX.Y.Z
   git push origin vX.Y.Z
   ```

4. Pushing the tag triggers two workflows in parallel:
   - `ci.yml` rebuilds on the tagged commit and uploads `unsigned-build-<sha>`.
   - `release.yml` starts immediately and polls for the matching CI run (via `gh run watch`), then signs, generates release notes (via `pipenv run pyrevit report releasenotes`), publishes a draft GitHub release, notifies issue threads, and pushes to Chocolatey.

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
- **Release fails on `Download unsigned artifacts`**: the CI run exists but the expected `unsigned-build-<sha>` artifact is missing (most often because CI failed before the upload step). Fix CI and re-run `release.yml`.
- **Signing step fails**: verify the `production` environment secrets above are present and not expired.
- **Choco push fails**: check `CHOCO_TOKEN` and that `dist/pyrevit-cli.<version>.nupkg` was actually produced (look at the CI artifact).
