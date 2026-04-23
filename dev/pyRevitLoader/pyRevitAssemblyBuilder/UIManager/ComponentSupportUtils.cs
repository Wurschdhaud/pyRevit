#nullable enable

using System;
using System.Collections.Generic;
using System.Linq;
using Autodesk.Revit.UI;
using pyRevitAssemblyBuilder.SessionManager;
using pyRevitExtensionParser;

namespace pyRevitAssemblyBuilder.UIManager
{
    /// <summary>
    /// Shared helpers for evaluating whether a parsed component should be visible
    /// in the current Revit session.
    /// </summary>
    public static class ComponentSupportUtils
    {
        /// <summary>
        /// Reads the current build settings that affect component visibility.
        /// </summary>
        public static (string CurrentVersion, bool LoadBeta) ReadBuildSettings(
            UIApplication uiApplication,
            ILogger logger)
        {
            var currentVersion = uiApplication?.Application?.VersionNumber ?? string.Empty;
            var loadBeta = false;

            try
            {
                loadBeta = PyRevitConfig.Load().LoadBeta;
            }
            catch (Exception ex)
            {
                logger?.Debug($"Failed to read LoadBeta config. Defaulting to false: {ex.Message}");
            }

            return (currentVersion, loadBeta);
        }

        /// <summary>
        /// Checks if a component is supported based on beta and Revit version constraints.
        /// </summary>
        public static bool IsSupported(
            ParsedComponent? component,
            string currentVersion,
            bool loadBeta,
            ILogger? logger = null)
        {
            if (component == null)
                return false;

            var displayName = component.DisplayName ?? component.Name ?? component.Type.ToString();

            if (component.IsBeta)
            {
                if (!loadBeta)
                {
                    logger?.Debug($"Skipping beta component '{displayName}' - beta tools not enabled.");
                    return false;
                }

                logger?.Debug($"Component '{displayName}' is beta and will be shown.");
            }

            if (string.IsNullOrEmpty(currentVersion))
            {
                logger?.Warning("Could not determine Revit version. Allowing all components.");
                return true;
            }

            var currentVersionNum = NormalizeVersionNumber(currentVersion);

            if (!string.IsNullOrEmpty(component.MinRevitVersion))
            {
                var minVersionNum = NormalizeVersionNumber(component.MinRevitVersion);
                if (currentVersionNum < minVersionNum)
                {
                    logger?.Debug(
                        $"Component '{displayName}' requires Revit {component.MinRevitVersion} or later. " +
                        $"Current version: {currentVersion}. Skipping.");
                    return false;
                }
            }

            if (!string.IsNullOrEmpty(component.MaxRevitVersion))
            {
                var maxVersionNum = NormalizeVersionNumber(component.MaxRevitVersion);
                if (currentVersionNum > maxVersionNum)
                {
                    logger?.Debug(
                        $"Component '{displayName}' supports up to Revit {component.MaxRevitVersion}. " +
                        $"Current version: {currentVersion}. Skipping.");
                    return false;
                }
            }

            return true;
        }

        /// <summary>
        /// Returns visible children for pulldowns and split buttons, while collapsing
        /// orphan separators created by filtered-out items.
        /// </summary>
        public static List<ParsedComponent> GetVisibleButtonGroupChildren(
            IEnumerable<ParsedComponent>? children,
            string currentVersion,
            bool loadBeta,
            ILogger? logger = null)
        {
            var visibleChildren = new List<ParsedComponent>();
            var pendingSeparator = false;

            if (children == null)
                return visibleChildren;

            foreach (var child in children)
            {
                if (child == null)
                    continue;

                if (child.Type == ExtensionParser.CommandComponentType.Separator)
                {
                    if (visibleChildren.Count > 0)
                        pendingSeparator = true;
                    continue;
                }

                if (!IsSupported(child, currentVersion, loadBeta, logger))
                    continue;

                if (pendingSeparator)
                {
                    visibleChildren.Add(new ParsedComponent
                    {
                        Name = "---",
                        DisplayName = "---",
                        Type = ExtensionParser.CommandComponentType.Separator,
                        Directory = child.Directory
                    });
                    pendingSeparator = false;
                }

                visibleChildren.Add(child);
            }

            return visibleChildren;
        }

        /// <summary>
        /// Checks if a button group has at least one visible command child.
        /// </summary>
        public static bool HasVisibleButtonGroupChildren(
            ParsedComponent? component,
            string currentVersion,
            bool loadBeta,
            ILogger? logger = null)
        {
            if (component?.Children == null)
                return false;

            return GetVisibleButtonGroupChildren(component.Children, currentVersion, loadBeta, logger)
                .Exists(child => child.Type != ExtensionParser.CommandComponentType.Separator);
        }

        /// <summary>
        /// Normalizes a Revit version string for numeric comparison.
        /// </summary>
        public static int NormalizeVersionNumber(string? version)
        {
            if (string.IsNullOrEmpty(version))
                return 0;

            var digits = new string(version.Where(char.IsDigit).ToArray());

            if (string.IsNullOrEmpty(digits))
                return 0;

            if (!int.TryParse(digits, out var versionNum))
                return 0;

            if (versionNum < 100)
                versionNum = 2000 + versionNum;

            return versionNum;
        }
    }
}
