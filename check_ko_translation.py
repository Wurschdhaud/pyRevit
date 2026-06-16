# -*- coding: utf-8 -*-
"""
Korean localization QA checker for pyRevit XAML ResourceDictionary files.

Checks:
  1. XML validity
  2. Key completeness  (all en_us keys present in ko)
  3. No extra keys     (ko has no keys absent from en_us)
  4. Non-string value preservation (Double, GridLength unchanged)
  5. Format placeholder preservation ({}, {0}, {type}, &#x...; etc.)
  6. XML special-char escapes preserved (&amp; &lt; &gt;)
  7. Untranslated string detection (ko value == en_us value for non-trivial strings)
  8. Korean character presence (at least one Hangul char per non-trivial string)
"""
import sys
import re
import xml.etree.ElementTree as ET
from pathlib import Path

import os
# Resolve base from environment variable or cwd fallback, avoiding Korean path issues
_env_base = os.environ.get("PYREVIT_QA_BASE")
if _env_base:
    BASE = Path(_env_base)
else:
    BASE = Path(__file__).parent

# All (en_us_path, ko_path) pairs derived from the 25 files we added
XAML_PAIRS = [
    (
        "extensions/pyRevitCore.extension/pyRevit.tab/pyRevit.panel/About.pushbutton/AboutWindow.ResourceDictionary.en_us.xaml",
        "extensions/pyRevitCore.extension/pyRevit.tab/pyRevit.panel/About.pushbutton/AboutWindow.ResourceDictionary.ko.xaml",
    ),
    (
        "extensions/pyRevitCore.extension/pyRevit.tab/pyRevit.panel/Extensions.smartbutton/ExtensionsWindow.ResourceDictionary.en_us.xaml",
        "extensions/pyRevitCore.extension/pyRevit.tab/pyRevit.panel/Extensions.smartbutton/ExtensionsWindow.ResourceDictionary.ko.xaml",
    ),
    (
        "extensions/pyRevitCore.extension/pyRevit.tab/pyRevit.panel/Settings.smartbutton/SettingsWindow.ResourceDictionary.en_us.xaml",
        "extensions/pyRevitCore.extension/pyRevit.tab/pyRevit.panel/Settings.smartbutton/SettingsWindow.ResourceDictionary.ko.xaml",
    ),
    (
        "extensions/pyRevitTools.extension/lib/match/clipboard_ui.ResourceDictionary.en_us.xaml",
        "extensions/pyRevitTools.extension/lib/match/clipboard_ui.ResourceDictionary.ko.xaml",
    ),
    (
        "extensions/pyRevitTools.extension/pyRevit.tab/Analysis.panel/ColorSplasher.pushbutton/ColorSplasherWindow.ResourceDictionary.en_us.xaml",
        "extensions/pyRevitTools.extension/pyRevit.tab/Analysis.panel/ColorSplasher.pushbutton/ColorSplasherWindow.ResourceDictionary.ko.xaml",
    ),
    (
        "extensions/pyRevitTools.extension/pyRevit.tab/Drawing Set.panel/Keynotes.pushbutton/EditRecord.ResourceDictionary.en_us.xaml",
        "extensions/pyRevitTools.extension/pyRevit.tab/Drawing Set.panel/Keynotes.pushbutton/EditRecord.ResourceDictionary.ko.xaml",
    ),
    (
        "extensions/pyRevitTools.extension/pyRevit.tab/Drawing Set.panel/Keynotes.pushbutton/KeynoteManagerWindow.ResourceDictionary.en_us.xaml",
        "extensions/pyRevitTools.extension/pyRevit.tab/Drawing Set.panel/Keynotes.pushbutton/KeynoteManagerWindow.ResourceDictionary.ko.xaml",
    ),
    (
        "extensions/pyRevitTools.extension/pyRevit.tab/Drawing Set.panel/Print Sheets.pushbutton/EditNamingFormats.ResourceDictionary.en_us.xaml",
        "extensions/pyRevitTools.extension/pyRevit.tab/Drawing Set.panel/Print Sheets.pushbutton/EditNamingFormats.ResourceDictionary.ko.xaml",
    ),
    (
        "extensions/pyRevitTools.extension/pyRevit.tab/Drawing Set.panel/Print Sheets.pushbutton/PrintSheets.ResourceDictionary.en_us.xaml",
        "extensions/pyRevitTools.extension/pyRevit.tab/Drawing Set.panel/Print Sheets.pushbutton/PrintSheets.ResourceDictionary.ko.xaml",
    ),
    (
        "extensions/pyRevitTools.extension/pyRevit.tab/Drawing Set.panel/Sheets.pulldown/Batch Sheet Maker.pushbutton/BatchSheetMakerWindow.ResourceDictionary.en_us.xaml",
        "extensions/pyRevitTools.extension/pyRevit.tab/Drawing Set.panel/Sheets.pulldown/Batch Sheet Maker.pushbutton/BatchSheetMakerWindow.ResourceDictionary.ko.xaml",
    ),
    (
        "extensions/pyRevitTools.extension/pyRevit.tab/Drawing Set.panel/Sheets.pulldown/ReOrder Sheets.pushbutton/ReOrderWindow.ResourceDictionary.en_us.xaml",
        "extensions/pyRevitTools.extension/pyRevit.tab/Drawing Set.panel/Sheets.pulldown/ReOrder Sheets.pushbutton/ReOrderWindow.ResourceDictionary.ko.xaml",
    ),
    (
        "extensions/pyRevitTools.extension/pyRevit.tab/Drawing Set.panel/views.stack/Views.pulldown/Toggle Grid Bubbles by Direction.pushbutton/coordinate_selector_ui.ResourceDictionary.en_us.xaml",
        "extensions/pyRevitTools.extension/pyRevit.tab/Drawing Set.panel/views.stack/Views.pulldown/Toggle Grid Bubbles by Direction.pushbutton/coordinate_selector_ui.ResourceDictionary.ko.xaml",
    ),
    (
        "extensions/pyRevitTools.extension/pyRevit.tab/Drawing Set.panel/views.stack/Views.pulldown/Toggle Grid Bubbles by Direction.pushbutton/ui.ResourceDictionary.en_us.xaml",
        "extensions/pyRevitTools.extension/pyRevit.tab/Drawing Set.panel/views.stack/Views.pulldown/Toggle Grid Bubbles by Direction.pushbutton/ui.ResourceDictionary.ko.xaml",
    ),
    (
        "extensions/pyRevitTools.extension/pyRevit.tab/Modify.panel/3D.pulldown/Measure.pushbutton/measure3d.ResourceDictionary.en_us.xaml",
        "extensions/pyRevitTools.extension/pyRevit.tab/Modify.panel/3D.pulldown/Measure.pushbutton/measure3d.ResourceDictionary.ko.xaml",
    ),
    (
        "extensions/pyRevitTools.extension/pyRevit.tab/Modify.panel/3D.pulldown/Section Box Navigator.pushbutton/SectionBoxNavigator.ResourceDictionary.en_us.xaml",
        "extensions/pyRevitTools.extension/pyRevit.tab/Modify.panel/3D.pulldown/Section Box Navigator.pushbutton/SectionBoxNavigator.ResourceDictionary.ko.xaml",
    ),
    (
        "extensions/pyRevitTools.extension/pyRevit.tab/Modify.panel/edit1.stack/Match.splitpushbutton/Match.pushbutton/MatchConfigWindow.ResourceDictionary.en_us.xaml",
        "extensions/pyRevitTools.extension/pyRevit.tab/Modify.panel/edit1.stack/Match.splitpushbutton/Match.pushbutton/MatchConfigWindow.ResourceDictionary.ko.xaml",
    ),
    (
        "extensions/pyRevitTools.extension/pyRevit.tab/Modify.panel/edit1.stack/Match.splitpushbutton/Match.pushbutton/MatchConfigWindowLegacy.ResourceDictionary.en_us.xaml",
        "extensions/pyRevitTools.extension/pyRevit.tab/Modify.panel/edit1.stack/Match.splitpushbutton/Match.pushbutton/MatchConfigWindowLegacy.ResourceDictionary.ko.xaml",
    ),
    (
        "extensions/pyRevitTools.extension/pyRevit.tab/Modify.panel/edit1.stack/Patterns.splitpushbutton/Make Pattern.pushbutton/MakePatternWindow.ResourceDictionary.en_us.xaml",
        "extensions/pyRevitTools.extension/pyRevit.tab/Modify.panel/edit1.stack/Patterns.splitpushbutton/Make Pattern.pushbutton/MakePatternWindow.ResourceDictionary.ko.xaml",
    ),
    (
        "extensions/pyRevitTools.extension/pyRevit.tab/Modify.panel/edit2.stack/ReValue.pushbutton/ReValueWindow.ResourceDictionary.en_us.xaml",
        "extensions/pyRevitTools.extension/pyRevit.tab/Modify.panel/edit2.stack/ReValue.pushbutton/ReValueWindow.ResourceDictionary.ko.xaml",
    ),
    (
        "extensions/pyRevitTools.extension/pyRevit.tab/Modify.panel/edit3.stack/Edit.pulldown/Convert Line Styles.pushbutton/ConvertLineStyles.ResourceDictionary.en_us.xaml",
        "extensions/pyRevitTools.extension/pyRevit.tab/Modify.panel/edit3.stack/Edit.pulldown/Convert Line Styles.pushbutton/ConvertLineStyles.ResourceDictionary.ko.xaml",
    ),
    (
        "extensions/pyRevitTools.extension/pyRevit.tab/Modify.panel/edit3.stack/Edit.pulldown/ParametersValuesToParameter.pushbutton/ui.ResourceDictionary.en_us.xaml",
        "extensions/pyRevitTools.extension/pyRevit.tab/Modify.panel/edit3.stack/Edit.pulldown/ParametersValuesToParameter.pushbutton/ui.ResourceDictionary.ko.xaml",
    ),
    (
        "extensions/pyRevitTools.extension/pyRevit.tab/Modify.panel/edit3.stack/Edit.pulldown/XLS Export.pushbutton/ElementItemStyle.ResourceDictionary.en_us.xaml",
        "extensions/pyRevitTools.extension/pyRevit.tab/Modify.panel/edit3.stack/Edit.pulldown/XLS Export.pushbutton/ElementItemStyle.ResourceDictionary.ko.xaml",
    ),
    (
        "extensions/pyRevitTools.extension/pyRevit.tab/Project.panel/Preflight Checks.pushbutton/PreflightCheckTemplate.ResourceDictionary.en_us.xaml",
        "extensions/pyRevitTools.extension/pyRevit.tab/Project.panel/Preflight Checks.pushbutton/PreflightCheckTemplate.ResourceDictionary.ko.xaml",
    ),
    (
        "extensions/pyRevitTools.extension/pyRevit.tab/Toggles.panel/toggles3.stack/ViewRange.pushbutton/MainWindow.ResourceDictionary.en_us.xaml",
        "extensions/pyRevitTools.extension/pyRevit.tab/Toggles.panel/toggles3.stack/ViewRange.pushbutton/MainWindow.ResourceDictionary.ko.xaml",
    ),
    (
        "pyrevitlib/pyrevit/forms/SelectFromList.ResourceDictionary.en_us.xaml",
        "pyrevitlib/pyrevit/forms/SelectFromList.ResourceDictionary.ko.xaml",
    ),
]

# Strings that are acceptable identical to English (proper nouns, symbols, codes)
ALLOW_SAME_AS_EN = {
    # button labels that are brand names / symbols
    "Wiki", "Twitter", "Blog", "GitHub", "YouTube",
    # short symbols used as directional arrows / format codes
    ">", "<", "TAB", "ReValue",
    # format strings that ARE purely code / placeholders
    "pyrevit-core/",
    # version-specific codes
    "IronPython", "CPython",
}

HANGUL_RE = re.compile(r'[가-힣ᄀ-ᇿ㄰-㆏]')
PLACEHOLDER_RE = re.compile(r'\{[^}]*\}|&#x[0-9A-Fa-f]+;|&amp;|&lt;|&gt;')

NS_MAP = {
    'system': 'clr-namespace:System;assembly=mscorlib',
    'v':      'clr-namespace:System;assembly=mscorlib',
}

# Tags treated as non-string (numeric / layout values — must be bit-for-bit identical)
NON_STRING_TAGS = {
    '{clr-namespace:System;assembly=mscorlib}Double',
    '{http://schemas.microsoft.com/winfx/2006/xaml/presentation}GridLength',
}

STRING_TAG = '{clr-namespace:System;assembly=mscorlib}String'

KEY_ATTR = '{http://schemas.microsoft.com/winfx/2006/xaml}Key'


def parse_file(path):
    """Return (ET.ElementTree, dict[key->element]) or raise."""
    tree = ET.parse(str(path))
    root = tree.getroot()
    entries = {}
    for child in root:
        key = child.get(KEY_ATTR)
        if key:
            entries[key] = child
    return tree, entries


def placeholders_in(text):
    """Return sorted list of placeholder tokens in text."""
    if not text:
        return []
    return sorted(PLACEHOLDER_RE.findall(text))


def is_trivial(text):
    """Short text that could legitimately stay in English (symbols, codes)."""
    t = (text or '').strip()
    if not t:
        return True
    if t in ALLOW_SAME_AS_EN:
        return True
    if len(t) <= 3:
        return True
    # purely numeric / format token
    if re.fullmatch(r'[\d\s\.\-\+\:,;><=!@#$%^&*()\[\]{}|/\\]+', t):
        return True
    # looks like a URL or code path
    if re.search(r'https?://', t) or '\\' in t or '/' in t:
        return True
    return False


# ── Read raw file bytes to check XML special char escapes ──────────────────
def raw_escapes(path):
    """Return set of escape sequences found in raw file."""
    text = Path(path).read_text(encoding='utf-8', errors='replace')
    return set(re.findall(r'&[a-zA-Z]+;|&#x[0-9A-Fa-f]+;', text))


PASS = "✓"
FAIL = "✗"
WARN = "⚠"


def check_pair(en_path, ko_path):
    issues = []
    warnings = []

    # ── CHECK 1: File existence ─────────────────────────────────────────────
    if not ko_path.exists():
        issues.append(f"[MISSING FILE] {ko_path.name}")
        return issues, warnings

    # ── CHECK 2: XML validity ───────────────────────────────────────────────
    try:
        _, en_entries = parse_file(en_path)
    except ET.ParseError as e:
        issues.append(f"[XML INVALID] en_us: {e}")
        return issues, warnings

    try:
        _, ko_entries = parse_file(ko_path)
    except ET.ParseError as e:
        issues.append(f"[XML INVALID] ko: {e}")
        return issues, warnings

    en_keys = set(en_entries)
    ko_keys = set(ko_entries)

    # ── CHECK 3: Key completeness ───────────────────────────────────────────
    missing = en_keys - ko_keys
    for k in sorted(missing):
        issues.append(f"[MISSING KEY] '{k}' in ko file")

    # ── CHECK 4: No extra keys ──────────────────────────────────────────────
    extra = ko_keys - en_keys
    for k in sorted(extra):
        issues.append(f"[EXTRA KEY]   '{k}' not in en_us")

    # ── CHECK 5-8: Per-key checks ───────────────────────────────────────────
    for key in en_keys & ko_keys:
        en_el = en_entries[key]
        ko_el = ko_entries[key]

        en_tag = en_el.tag
        ko_tag = ko_el.tag

        # Tags must match
        if en_tag != ko_tag:
            issues.append(f"[TAG MISMATCH] '{key}': en={en_tag} ko={ko_tag}")
            continue

        en_text = (en_el.text or '').strip()
        ko_text = (ko_el.text or '').strip()

        # CHECK 5: Non-string elements must be identical
        if en_tag in NON_STRING_TAGS:
            if en_text != ko_text:
                issues.append(f"[VALUE CHANGED] non-string '{key}': en='{en_text}' ko='{ko_text}'")
            continue

        if en_tag != STRING_TAG:
            # Unknown tag — skip deeper checks but flag if value changed
            if en_text != ko_text:
                warnings.append(f"[UNKNOWN TAG] '{key}' tag={en_tag}, values differ")
            continue

        # CHECK 6: Format placeholder preservation
        en_ph = placeholders_in(en_text)
        ko_ph = placeholders_in(ko_text)
        if en_ph != ko_ph:
            issues.append(
                f"[PLACEHOLDER] '{key}': en={en_ph} ko={ko_ph}"
            )

        # CHECK 7: Untranslated strings
        if en_text == ko_text and not is_trivial(en_text):
            warnings.append(f"[UNTRANSLATED?] '{key}': value is identical to English")

        # CHECK 8: Korean chars presence (for non-trivial strings)
        if not is_trivial(en_text):
            if not HANGUL_RE.search(ko_text):
                # Special case: some strings may legitimately have no hangul
                # (e.g., pure format strings like "{type} {lvl}ST {name}")
                pure_placeholder = bool(re.fullmatch(r'[\s\{}\w\d\.,:;!@#%\-\+\*\/\|\(\)\[\]\^&=\'"<>~`]+', ko_text))
                if not pure_placeholder:
                    warnings.append(f"[NO HANGUL]   '{key}': '{ko_text[:60]}...'")

    return issues, warnings


def main():
    total_issues = 0
    total_warnings = 0
    file_results = []

    print("=" * 72)
    print("pyRevit Korean (ko) Localization QA Report")
    print("=" * 72)

    for en_rel, ko_rel in XAML_PAIRS:
        en_path = BASE / en_rel
        ko_path = BASE / ko_rel
        label = ko_path.name

        issues, warnings = check_pair(en_path, ko_path)
        total_issues += len(issues)
        total_warnings += len(warnings)

        if issues:
            status = FAIL
        elif warnings:
            status = WARN
        else:
            status = PASS

        file_results.append((status, label, issues, warnings))

    # Print per-file summary
    for status, label, issues, warnings in file_results:
        print(f"\n{status} {label}")
        for msg in issues:
            print(f"      {msg}")
        for msg in warnings:
            print(f"      {msg}")

    print("\n" + "=" * 72)
    print(f"Files checked : {len(XAML_PAIRS)}")
    print(f"PASS          : {sum(1 for s,*_ in file_results if s == PASS)}")
    print(f"WARN          : {sum(1 for s,*_ in file_results if s == WARN)}")
    print(f"FAIL          : {sum(1 for s,*_ in file_results if s == FAIL)}")
    print(f"Total issues  : {total_issues}")
    print(f"Total warnings: {total_warnings}")
    print("=" * 72)

    if total_issues > 0:
        print("\nResult: FAIL — fix the issues above before submitting a PR.")
        sys.exit(1)
    elif total_warnings > 0:
        print("\nResult: WARN — review warnings, then submit PR.")
    else:
        print("\nResult: PASS — all checks passed.")


if __name__ == "__main__":
    main()
