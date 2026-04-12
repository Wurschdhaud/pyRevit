#nullable enable
using System;
using System.Collections.Generic;
using System.Linq;
using System.Security.Principal;
using pyRevitExtensionParser;

namespace pyRevitAssemblyBuilder.SessionManager
{
    /// <summary>
    /// Service for managing and querying installed pyRevit extensions.
    /// </summary>
    public class ExtensionManagerService : IExtensionManagerService
    {
        private readonly int _revitYear;
        private readonly ILogger? _logger;
        private List<ParsedExtension>? _cachedExtensions;

        public ExtensionManagerService(int revitYear = 0, ILogger? logger = null)
        {
            _revitYear = revitYear;
            _logger = logger;
        }

        /// <summary>
        /// Gets all parsed extensions (cached).
        /// </summary>
        private List<ParsedExtension> GetAllExtensionsCached()
        {
            return _cachedExtensions ??= ExtensionParser.ParseInstalledExtensions(_revitYear).ToList();
        }

        /// <summary>
        /// Clears the extension cache, forcing a re-parse on next access.
        /// </summary>
        public void ClearCache()
        {
            _cachedExtensions = null;
        }
        
        /// <summary>
        /// Clears all parser caches including the static caches in ExtensionParser.
        /// This ensures newly installed or enabled extensions are discovered on reload.
        /// </summary>
        public void ClearParserCaches()
        {
            _cachedExtensions = null;
            ExtensionParser.ClearAllCaches();
        }

        /// <summary>
        /// Checks if the current user has access to the extension based on:
        /// 1. Whether the extension is disabled in config
        /// 2. Whether authorized users are defined and current user is in the list
        /// 3. Whether authorized groups are defined and user is member of at least one
        /// 
        /// This replicates the logic in Python's extpkgs.ExtensionPackage.is_enabled + user_has_access
        /// matching pyrevitlib/pyrevit/extensions/extensionmgr.py:_is_extension_enabled()
        /// </summary>
        private bool IsExtensionAllowed(ParsedExtension ext)
        {
            // Check if extension is disabled in config
            if (ext.Config?.Disabled == true)
            {
                _logger?.Debug($"Extension '{ext.Name}' is disabled in config");
                return false;
            }

            // Check authorized users list
            if (ext.AuthorizedUsers != null && ext.AuthorizedUsers.Count > 0)
            {
                var currentUser = Environment.UserName;
                if (!ext.AuthorizedUsers.Contains(currentUser, StringComparer.OrdinalIgnoreCase))
                {
                    _logger?.Debug($"Extension '{ext.Name}' restricted to specific users. Current user '{currentUser}' not in list");
                    return false;
                }
            }

            // Check authorized groups list (groups are stored as SID strings)
            if (ext.AuthorizedGroups != null && ext.AuthorizedGroups.Count > 0)
            {
                bool inAnyGroup = false;
                foreach (var groupSid in ext.AuthorizedGroups)
                {
                    if (UserIsInSecurityGroup(groupSid))
                    {
                        inAnyGroup = true;
                        break;
                    }
                }
                if (!inAnyGroup)
                {
                    _logger?.Debug($"Extension '{ext.Name}' restricted to specific security groups. Current user not member of any");
                    return false;
                }
            }

            return true;
        }

        /// <summary>
        /// Checks if the current Windows user is a member of the specified security group.
        /// Uses the same implementation as pyRevitLabs.Common.Security.UserAuth.UserIsInSecurityGroup.
        /// </summary>
        /// <param name="targetSid">The SID of the security group to check</param>
        /// <returns>True if user is member of the group</returns>
        private static bool UserIsInSecurityGroup(string targetSid)
        {
            if (string.IsNullOrEmpty(targetSid))
                return false;

            try
            {
                var wi = WindowsIdentity.GetCurrent();
                foreach (var sid in wi.Groups)
                {
                    // Null check and safe string comparison for group SID matching
                    if (sid != null && string.Equals(sid.Value, targetSid, StringComparison.Ordinal))
                        return true;
                }
            }
            catch
            {
                // Ignore errors in security group enumeration
            }
            return false;
        }

        /// <summary>
        /// Gets all installed extensions that are not disabled and pass authorization checks.
        /// </summary>
        /// <returns>An enumerable collection of parsed extensions.</returns>
        public IEnumerable<ParsedExtension> GetInstalledExtensions()
        {
            return GetAllExtensionsCached()
                .Where(ext => IsExtensionAllowed(ext));
        }

        /// <summary>
        /// Gets all installed UI extensions (extensions ending with .extension) that are not disabled
        /// and pass authorization checks.
        /// </summary>
        /// <returns>An enumerable collection of parsed UI extensions.</returns>
        public IEnumerable<ParsedExtension> GetInstalledUIExtensions()
        {
            return GetAllExtensionsCached()
                .Where(ext => IsExtensionAllowed(ext) &&
                       ext.Directory.EndsWith(ExtensionConstants.UI_EXTENSION_SUFFIX, System.StringComparison.OrdinalIgnoreCase));
        }

        /// <summary>
        /// Gets all installed library extensions (extensions ending with .lib) that are not disabled
        /// and pass authorization checks.
        /// </summary>
        /// <returns>An enumerable collection of parsed library extensions.</returns>
        public IEnumerable<ParsedExtension> GetInstalledLibraryExtensions()
        {
            return GetAllExtensionsCached()
                .Where(ext => IsExtensionAllowed(ext) &&
                       ext.Directory.EndsWith(ExtensionConstants.LIBRARY_EXTENSION_SUFFIX, System.StringComparison.OrdinalIgnoreCase));
        }
    }
}
