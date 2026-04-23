#nullable enable

using System.Collections.Generic;
using NUnit.Framework;
using pyRevitAssemblyBuilder.UIManager;
using pyRevitExtensionParser;
using static pyRevitExtensionParser.ExtensionParser;

namespace pyRevitExtensionParserTest
{
    [TestFixture]
    public class ComponentSupportUtilsTests
    {
        private readonly MockLogger _logger = new MockLogger();

        [SetUp]
        public void SetUp()
        {
            _logger.Debugs.Clear();
            _logger.Infos.Clear();
            _logger.Warnings.Clear();
            _logger.Errors.Clear();
        }

        [Test]
        public void IsSupported_HidesBetaComponent_WhenLoadBetaIsDisabled()
        {
            var component = CreateComponent("BetaTool", CommandComponentType.PushButton, isBeta: true);

            var isSupported = ComponentSupportUtils.IsSupported(component, "2025", loadBeta: false, _logger);

            Assert.IsFalse(isSupported, "Beta component should be hidden when beta tools are disabled.");
        }

        [Test]
        public void IsSupported_HidesVersionIncompatibleComponent()
        {
            var component = CreateComponent(
                "FutureTool",
                CommandComponentType.PushButton,
                minRevitVersion: "2026");

            var isSupported = ComponentSupportUtils.IsSupported(component, "2025", loadBeta: true, _logger);

            Assert.IsFalse(isSupported, "Component should be hidden when the current Revit version is below min_revit_version.");
        }

        [Test]
        public void GetVisibleButtonGroupChildren_RemovesHiddenButtonsAndOrphanSeparators()
        {
            var children = new List<ParsedComponent>
            {
                CreateComponent("VisibleOne", CommandComponentType.PushButton),
                CreateSeparator(),
                CreateComponent("BetaOnly", CommandComponentType.PushButton, isBeta: true),
                CreateSeparator(),
                CreateComponent("VisibleTwo", CommandComponentType.PushButton)
            };

            var visibleChildren = ComponentSupportUtils.GetVisibleButtonGroupChildren(
                children,
                "2025",
                loadBeta: false,
                _logger);

            Assert.That(visibleChildren.Count, Is.EqualTo(3), "Only visible buttons and the separator between them should remain.");
            Assert.That(visibleChildren[0].DisplayName, Is.EqualTo("VisibleOne"));
            Assert.That(visibleChildren[1].Type, Is.EqualTo(CommandComponentType.Separator));
            Assert.That(visibleChildren[2].DisplayName, Is.EqualTo("VisibleTwo"));
        }

        [Test]
        public void HasVisibleButtonGroupChildren_ReturnsFalse_WhenAllChildrenAreFilteredOut()
        {
            var group = CreateComponent("GroupedTools", CommandComponentType.PullDown);
            group.Children = new List<ParsedComponent>
            {
                CreateComponent("BetaOnly", CommandComponentType.PushButton, isBeta: true)
            };

            var hasVisibleChildren = ComponentSupportUtils.HasVisibleButtonGroupChildren(
                group,
                "2025",
                loadBeta: false,
                _logger);

            Assert.IsFalse(hasVisibleChildren, "Pulldown should be considered empty when all child commands are filtered out.");
        }

        private static ParsedComponent CreateComponent(
            string displayName,
            CommandComponentType type,
            bool isBeta = false,
            string? minRevitVersion = null,
            string? maxRevitVersion = null)
        {
            return new ParsedComponent
            {
                Name = displayName,
                DisplayName = displayName,
                Type = type,
                IsBeta = isBeta,
                MinRevitVersion = minRevitVersion,
                MaxRevitVersion = maxRevitVersion,
                Directory = @"C:\test"
            };
        }

        private static ParsedComponent CreateSeparator()
        {
            return new ParsedComponent
            {
                Name = "---",
                DisplayName = "---",
                Type = CommandComponentType.Separator,
                Directory = @"C:\test"
            };
        }
    }
}
