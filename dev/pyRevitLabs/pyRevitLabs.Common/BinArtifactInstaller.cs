using System;
using System.IO;
using System.IO.Compression;

using pyRevitLabs.NLog;

namespace pyRevitLabs.Common {
    public enum BinArtifactInstallMode {
        Clone,
        Update,
    }

    public static class BinArtifactInstaller {
        private static readonly Logger logger = LogManager.GetCurrentClassLogger();

        public static void InstallForClone(
            string clonePath,
            string repoId,
            string commitSha,
            string branchName,
            BinArtifactInstallMode mode = BinArtifactInstallMode.Clone,
            bool allowBranchFallback = true) {
            if (string.IsNullOrWhiteSpace(clonePath))
                throw new PyRevitException("Clone path can not be null.");

            if (mode == BinArtifactInstallMode.Update
                && GitInstaller.IsValidRepo(clonePath)
                && GitInstaller.IsLocalAheadOfTrackingBranch(clonePath)) {
                logger.Warn(
                    "Local clone is ahead of its remote tracking branch. Skipping binary download. "
                    + "Build locally with \"dotnet run -- ci\" in the repository root, "
                    + "or push your commits and wait for CI.");
                return;
            }

            var normalizedSha = NormalizeSha(commitSha);
            logger.Info("Downloading pre-built binaries for commit {0}...", normalizedSha);

            var tempZip = Path.Combine(
                Path.GetTempPath(),
                string.Format("pyrevit-bin-{0}.zip", Guid.NewGuid().ToString("N")));
            var tempExtract = Path.Combine(
                Path.GetTempPath(),
                string.Format("pyrevit-bin-{0}", Guid.NewGuid().ToString("N")));

            var usedBranchFallback = false;
            var downloaded = false;

            try {
                downloaded = TryDownloadPublicRelease(repoId, normalizedSha, branchName, mode, clonePath,
                    allowBranchFallback, tempZip, out usedBranchFallback);

                if (!downloaded)
                    downloaded = TryDownloadFromActionsArtifact(
                        repoId,
                        normalizedSha,
                        branchName,
                        mode,
                        clonePath,
                        allowBranchFallback,
                        tempZip,
                        out usedBranchFallback);

                if (!downloaded) {
                    throw new pyRevitBinArtifactNotFoundException(
                        string.Format(
                            "Could not find pre-built binaries for commit \"{0}\" on branch \"{1}\". "
                            + "Push the commit and wait for CI, or run \"dotnet run -- ci\" in the clone root.",
                            normalizedSha,
                            branchName));
                }

                ExtractArtifactIntoClone(tempExtract, tempZip, clonePath);
                if (usedBranchFallback)
                    logger.Info("Installed pre-built binaries from branch fallback.");
                else
                    logger.Info("Clone ready — no local build required.");
            }
            finally {
                SafeDelete(tempZip);
                SafeDeleteDirectory(tempExtract);
            }
        }

        public static void InstallForRepoClone(string clonePath, string repoUrl, BinArtifactInstallMode mode) {
            var repoId = GithubRepoHelper.ParseRepoId(repoUrl ?? GitInstaller.GetRemoteUrl(
                clonePath,
                PyRevitLabsConsts.DefaultRemoteName));
            var branchName = GitInstaller.GetCheckedoutBranch(clonePath) ?? PyRevitLabsConsts.TargetBranch;
            var commitSha = GitInstaller.GetHeadCommit(clonePath);
            InstallForClone(clonePath, repoId, commitSha, branchName, mode: mode);
        }

        public static void InstallForImageClone(
            string clonePath,
            string repoId,
            string branchName,
            BinArtifactInstallMode mode = BinArtifactInstallMode.Clone) {
            var commitSha = GithubActionsAPI.GetCommitShaForBranch(repoId, branchName);
            InstallForClone(clonePath, repoId, commitSha, branchName, mode: mode);
        }

        private static bool TryDownloadPublicRelease(
            string repoId,
            string normalizedSha,
            string branchName,
            BinArtifactInstallMode mode,
            string clonePath,
            bool allowBranchFallback,
            string destPath,
            out bool usedBranchFallback) {
            usedBranchFallback = false;

            var shaAsset = GithubReleaseBinAPI.BuildShaAssetName(normalizedSha);
            if (GithubReleaseBinAPI.TryDownloadReleaseAsset(repoId, shaAsset, destPath))
                return true;

            if (!allowBranchFallback)
                return false;

            if (mode == BinArtifactInstallMode.Update
                && GitInstaller.IsValidRepo(clonePath)
                && !GitInstaller.IsSyncedWithTrackingBranch(clonePath)) {
                logger.Warn(
                    "No public release asset for commit {0} and clone is not synced with remote. "
                    + "Skipping branch fallback. Build locally or push and wait for CI.",
                    normalizedSha);
                return false;
            }

            logger.Warn(
                "No release asset for {0}; trying latest CI build on {1} "
                + "(warning: may differ slightly from source).",
                normalizedSha,
                branchName);

            var branchAsset = GithubReleaseBinAPI.BuildBranchLatestAssetName(branchName);
            usedBranchFallback = GithubReleaseBinAPI.TryDownloadReleaseAsset(repoId, branchAsset, destPath);
            return usedBranchFallback;
        }

        private static bool TryDownloadFromActionsArtifact(
            string repoId,
            string normalizedSha,
            string branchName,
            BinArtifactInstallMode mode,
            string clonePath,
            bool allowBranchFallback,
            string destPath,
            out bool usedBranchFallback) {
            usedBranchFallback = false;

            if (string.IsNullOrWhiteSpace(GithubAPI.AuthToken)) {
                logger.Debug(
                    "Skipping GitHub Actions artifact fallback (GITHUBTOKEN not set). "
                    + "Use a public fork with Release assets or build locally.");
                return false;
            }

            var artifactName = GithubActionsAPI.UnsignedBinArtifactPrefix + normalizedSha;
            var artifact = GithubActionsAPI.FindArtifactByName(repoId, artifactName);

            if (artifact == null && allowBranchFallback) {
                if (mode == BinArtifactInstallMode.Update
                    && GitInstaller.IsValidRepo(clonePath)
                    && !GitInstaller.IsSyncedWithTrackingBranch(clonePath)) {
                    logger.Warn(
                        "No CI artifact for commit {0} and clone is not synced with remote. "
                        + "Skipping branch fallback.",
                        normalizedSha);
                    return false;
                }

                logger.Warn(
                    "No Actions artifact for {0}; using latest successful CI build on {1}.",
                    normalizedSha,
                    branchName);
                artifact = GithubActionsAPI.FindLatestBranchArtifact(repoId, branchName);
                usedBranchFallback = artifact != null;
            }

            if (artifact == null)
                return false;

            GithubActionsAPI.DownloadArtifactZip(repoId, artifact.Id, destPath);
            return true;
        }

        private static void ExtractArtifactIntoClone(string tempExtract, string artifactZipPath, string clonePath) {
            if (Directory.Exists(tempExtract))
                CommonUtils.DeleteDirectory(tempExtract, verbose: false);

            ZipFile.ExtractToDirectory(artifactZipPath, tempExtract);

            var binSource = ResolveBinSourceRoot(tempExtract);
            var binDest = Path.Combine(clonePath, "bin");

            if (CommonUtils.VerifyPath(binDest))
                CommonUtils.DeleteDirectory(binDest);

            CommonUtils.CopyDirectory(binSource, binDest);
        }

        private static string ResolveBinSourceRoot(string extractRoot) {
            var directBin = Path.Combine(extractRoot, "bin");
            if (CommonUtils.VerifyPath(directBin))
                return directBin;

            if (Directory.GetFiles(extractRoot).Length > 0 || Directory.GetDirectories(extractRoot).Length > 1)
                return extractRoot;

            var subDirs = Directory.GetDirectories(extractRoot);
            if (subDirs.Length == 1) {
                var nestedBin = Path.Combine(subDirs[0], "bin");
                if (CommonUtils.VerifyPath(nestedBin))
                    return nestedBin;
                return subDirs[0];
            }

            return extractRoot;
        }

        private static string NormalizeSha(string commitSha) {
            if (string.IsNullOrWhiteSpace(commitSha))
                throw new PyRevitException("Commit SHA is required to resolve CI binaries.");
            return commitSha.Trim();
        }

        private static void SafeDelete(string path) {
            try {
                if (CommonUtils.VerifyFile(path))
                    File.Delete(path);
            }
            catch (Exception ex) {
                logger.Debug("Could not delete temp file \"{0}\" | {1}", path, ex.Message);
            }
        }

        private static void SafeDeleteDirectory(string path) {
            try {
                if (CommonUtils.VerifyPath(path))
                    CommonUtils.DeleteDirectory(path, verbose: false);
            }
            catch (Exception ex) {
                logger.Debug("Could not delete temp directory \"{0}\" | {1}", path, ex.Message);
            }
        }
    }
}
