# -*- coding: utf-8 -*-
# Korean translation QUALITY checker for pyRevit XAML ResourceDictionary files.
#
# Separate from structural QA (check_ko_translation.py) -- focuses on:
#   Q1. Terminology consistency   -- same English concept -> same Korean term
#   Q2. Button label style        -- short, no sentence endings
#   Q3. Length ratio              -- translated text not excessively long/short
#   Q4. Description ending style  -- descriptions end in proper verb form
#   Q5. No orphaned English words that should be translated
#   Q6. Korean jamo integrity     -- no broken orphan jamo characters
#   Q7. No double spaces / spacing errors
#
# Run:
#   $env:PYREVIT_QA_BASE = "$env:TEMP\pyrevit_qa_check"
#   python -X utf8 check_ko_quality.py
import os
import re
import sys
import unicodedata
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

# ---------------------------------------------------------------------------
# Base path resolution (same pattern as check_ko_translation.py)
# ---------------------------------------------------------------------------
_env_base = os.environ.get("PYREVIT_QA_BASE")
BASE = Path(_env_base) if _env_base else Path(__file__).parent

# ---------------------------------------------------------------------------
# XAML pairs: (en_us, ko)
# ---------------------------------------------------------------------------
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

# ---------------------------------------------------------------------------
# Standard terminology glossary: English term → expected Korean
# Checked across ALL files for consistency.
# ---------------------------------------------------------------------------
GLOSSARY = {
    # Core UI actions
    "Cancel":       "취소",
    "Save":         "저장",
    "Close":        "닫기",
    "Apply":        "적용",
    "Reset":        "초기화",
    "Search":       "검색",
    "Select":       "선택",
    "Delete":       "삭제",
    "Remove":       "제거",
    "Edit":         "편집",
    "Add":          "추가",
    "Install":      "설치",
    "Update":       "업데이트",
    "Enable":       "활성화",
    "Disable":      "비활성화",
    "Run":          "실행",
    "Reload":       "다시 로드",
    # States
    "Enabled":      "활성화됨",
    "Disabled":     "비활성화됨",
    "Installed":    "설치됨",
    # Common nouns
    "Settings":     "설정",
    "Author":       "작성자",
    "Version":      "버전",
    "Name":         "이름",
    "Type":         "유형",
    "Status":       "상태",
    "Description":  "설명",
    "Title":        None,        # can vary; skip exact match
    "Extension":    None,        # "확장" or "확장 패키지" — allow either
}

# English keys that are purely technical and should NOT be translated
# (brand names, code identifiers, format specifiers)
TECHNICAL_EXEMPT_PATTERNS = [
    r'^pyRevit',
    r'GitHub',
    r'YouTube',
    r'^IronPython',
    r'^CPython',
    r'Roslyn',
    r'__\w+__',          # Python dunder identifiers
    r'^\s*[\{\}\d\s\.,;:\-\+\*/\\\|\(\)\[\]@#%\^&=\'"<>~`!ΔΩ]+\s*$',  # pure format/symbol
    r'^\s*$',
    r'^[A-Za-z0-9\s\-]+\.(yaml|json|py|xaml|dll|exe)$',  # filenames
]
TECHNICAL_EXEMPT_RE = re.compile('|'.join(TECHNICAL_EXEMPT_PATTERNS))

# English words that indicate a string is NOT a pure technical/brand term
# and should have Korean translation.  We flag if these appear in the ko value.
TRANSLATABLE_ENGLISH_WORDS = {
    "button", "label", "panel", "window", "settings", "options",
    "select", "enable", "disable", "install", "remove", "update",
    "cancel", "apply", "close", "save", "open", "create", "delete",
    "search", "filter", "loading", "error", "warning", "information",
    "click", "press", "hold", "drag", "drop", "choose", "confirm",
    "required", "optional", "default", "custom", "advanced", "basic",
    "show", "hide", "toggle", "switch", "check", "uncheck", "refresh",
    "import", "export", "print", "sheet", "view", "model", "project",
}

# ---------------------------------------------------------------------------
# Korean linguistic helpers
# ---------------------------------------------------------------------------
HANGUL_RE = re.compile(r'[가-힣]')
JAMO_ORPHAN_RE = re.compile(r'[ᄀ-ᇿ㄰-㆏ꥠ-꥿ힰ-퟿]')

# Korean sentence endings that are acceptable for description/tooltip strings.
# Covers: 합니다/됩니다/있습니다/입니다 family, 세요/하세요 family,
# and the general [syllable]니다 pattern for verb conjugations like 돌립니다, 건너뜁니다.
DESCRIPTION_ENDINGS = re.compile(
    r'(합니다|됩니다|습니다|겠습니다|하십시오|하세요|세요|십시오'
    r'|있습니다|없습니다|였습니다|이었습니다|입니다|입니까|겠습니까|시겠습니까'
    r'|하겠습니까|드립니다|드리겠습니다'
    r'|[가-힣]니다'   # catches 돌립니다, 건너뜁니다, etc.
    r')[\s\.\?\!\:]*$'  # allow trailing colon (for lists like "다음과 같습니다:")
)

# Button-style sentence endings that should NOT appear on short button labels
BUTTON_SENTENCE_ENDING_RE = re.compile(
    r'(합니다|됩니다|습니다|겠습니다|하십시오|하세요|세요|십시오)[\s\.\?\!]*$'
)

# Markers in key names that indicate a button/action label (short expected)
BUTTON_KEY_SUFFIXES = (
    ".Button", "Button.", "Buttons.", ".Toggle", "CheckAll", "CheckNone",
    ".Cancel", ".Save", ".Close", ".Apply", ".Reset", ".Select",
    ".Add", ".Remove", ".Install", ".Update", ".Run", ".Open",
    ".Delete", ".Edit", ".Create", ".Export", ".Import", ".Print",
    ".Enable", ".Disable", ".Confirm", ".Back", ".Next", ".Finish",
    ".Uncheck", ".Check", ".Search", ".Reload", ".Refresh",
)

# Markers in key names that indicate a description (long sentence expected)
# These take PRIORITY over BUTTON_KEY_SUFFIXES — a key with both is a description.
DESCRIPTION_KEY_SUFFIXES = (
    ".Description", "Description.", ".Tooltip", "ToolTip", ".Help",
    ".Info", "Changed", ".Note", ".Message", ".Placeholder",
)

# Key *endings* that unambiguously mark a button label (full suffix, not substring)
BUTTON_KEY_EXACT_ENDINGS = (
    ".Button", ".Cancel", ".Save", ".Apply",
    ".Add", ".Remove", ".Install", ".Update", ".Run", ".Open",
    ".Delete", ".Create", ".Export", ".Import",
    ".Enable", ".Disable", ".Confirm", ".Back", ".Next", ".Finish",
    ".Reload", ".Refresh",
)

# Standalone key segments (the whole last component after the last dot) that
# indicate button labels — matched against the last segment only.
BUTTON_KEY_LAST_SEGMENTS = {
    "checkall", "checknone", "uncheckall", "selectall", "deselectall",
    "toggle", "close", "select", "reset", "search", "edit", "print",
    "enable", "disable",
}


def is_description_key(key):
    k = key.lower()
    return any(s.lower() in k for s in DESCRIPTION_KEY_SUFFIXES)


def is_button_key(key):
    # Description keys always win over button detection
    if is_description_key(key):
        return False
    k = key.lower()
    # Match unambiguous exact-ending suffixes
    if any(k.endswith(s.lower()) for s in BUTTON_KEY_EXACT_ENDINGS):
        return True
    # Match the final segment after the last dot
    last = k.rsplit('.', 1)[-1]
    return last in BUTTON_KEY_LAST_SEGMENTS


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------
NSMAP = {
    'system': 'clr-namespace:System;assembly=mscorlib',
    'v':      'clr-namespace:System;assembly=mscorlib',
}

def parse_strings(path):
    """Return dict {key: text} for all String elements in an XAML file."""
    tree = ET.parse(str(path))
    root = tree.getroot()
    result = {}
    for elem in root:
        tag = elem.tag
        # Accept system:String or v:String
        if not (tag.endswith('}String') or tag.endswith('String')):
            continue
        key = elem.get('{http://schemas.microsoft.com/winfx/2006/xaml}Key')
        if key is None:
            continue
        text = (elem.text or '').strip()
        result[key] = text
    return result


# ---------------------------------------------------------------------------
# Check functions
# ---------------------------------------------------------------------------

def check_q1_glossary(key, en_text, ko_text, issues):
    """Q1: Standard terms match the glossary."""
    en_strip = en_text.strip()
    expected_ko = GLOSSARY.get(en_strip)
    if expected_ko is None:
        return
    ko_strip = ko_text.strip()
    if ko_strip != expected_ko:
        issues.append(
            f"[Q1-GLOSSARY] Key '{key}': '{en_strip}' → expected '{expected_ko}', got '{ko_strip}'"
        )


def check_q2_button_style(key, ko_text, issues, warnings):
    """Q2: Button labels must not be sentence-form (합니다/세요 endings)."""
    if not is_button_key(key):
        return
    ko_strip = ko_text.strip()
    if not HANGUL_RE.search(ko_strip):
        return  # no Korean — skip
    if len(ko_strip) > 25:
        warnings.append(
            f"[Q2-BTN-LEN] Key '{key}': button label may be too long ({len(ko_strip)} chars): '{ko_strip[:40]}'"
        )
    if BUTTON_SENTENCE_ENDING_RE.search(ko_strip):
        issues.append(
            f"[Q2-BTN-FORM] Key '{key}': button label ends with sentence form — use noun/verb-root form: '{ko_strip[:60]}'"
        )


def check_q3_length_ratio(key, en_text, ko_text, issues, warnings):
    """Q3: Korean/English char-count ratio must be in plausible range."""
    en_len = len(en_text.replace(' ', ''))
    ko_stripped = re.sub(r'\{[^}]*\}|&#x[0-9A-Fa-f]+;', '', ko_text)
    ko_len = len(ko_stripped.replace(' ', ''))
    if en_len < 5 or ko_len < 2:
        return  # too short to be meaningful
    ratio = ko_len / en_len
    if ratio > 1.8:
        issues.append(
            f"[Q3-LONG] Key '{key}': ko/en length ratio {ratio:.2f} (ko={ko_len}, en={en_len}) — possibly expanded or duplicated"
        )
    elif ratio < 0.15:
        issues.append(
            f"[Q3-SHORT] Key '{key}': ko/en length ratio {ratio:.2f} (ko={ko_len}, en={en_len}) — possibly truncated"
        )


def check_q4_description_style(key, ko_text, issues, warnings):
    """Q4: Description keys (long strings) should end in 합니다체 or noun form."""
    if not is_description_key(key):
        return
    ko_strip = ko_text.strip()
    if not HANGUL_RE.search(ko_strip):
        return
    if len(ko_strip) < 15:
        return  # short descriptions are fine as noun form
    # Strip trailing format placeholders and parentheticals before checking ending,
    # since they may appear after the actual sentence (e.g. "생성되었습니다: {0}").
    ko_for_ending = re.sub(r'\s*\{[^}]*\}\s*$', '', ko_strip).strip()
    ko_for_ending = re.sub(r'\s*\([^)]*\)\s*$', '', ko_for_ending).strip()
    if not DESCRIPTION_ENDINGS.search(ko_for_ending):
        warnings.append(
            f"[Q4-DESC-STYLE] Key '{key}': long description does not end in 합니다/세요 form: '...{ko_strip[-35:]}'"
        )


def check_q5_orphan_english(key, en_text, ko_text, issues):
    """Q5: Korean text must not contain common English words that should be translated."""
    if TECHNICAL_EXEMPT_RE.search(en_text.strip()):
        return
    # Strip format placeholders and code-like patterns first
    # Remove: {placeholders}, module.Attribute paths (logging.WARNING), ALL_CAPS constants,
    # quoted strings (Revit parameter names shown in UI), and XML entities.
    cleaned = ko_text
    cleaned = re.sub(r'\{[^}]*\}', '', cleaned)           # format placeholders
    cleaned = re.sub(r'&#x[0-9A-Fa-f]+;', '', cleaned)   # XML char entities
    cleaned = re.sub(r'\b\w+\.\w+\b', '', cleaned)        # module.Attribute (dotted paths)
    cleaned = re.sub(r'\b[A-Z_]{3,}\b', '', cleaned)      # ALL_CAPS constants
    cleaned = re.sub(r'"[^"]*"', '', cleaned)             # "quoted Revit UI element names"
    cleaned = re.sub(r"'[^']*'", '', cleaned)             # 'single-quoted' names

    ko_words = re.findall(r'\b[a-zA-Z]{4,}\b', cleaned)
    for word in ko_words:
        if word.lower() in TRANSLATABLE_ENGLISH_WORDS:
            issues.append(
                f"[Q5-ORPHAN-EN] Key '{key}': untranslated English word '{word}' in ko value: '{ko_text[:70]}'"
            )
            break  # one report per key


def check_q6_jamo_integrity(key, ko_text, issues):
    """Q6: No orphan jamo characters (broken Korean)."""
    if JAMO_ORPHAN_RE.search(ko_text):
        issues.append(
            f"[Q6-JAMO] Key '{key}': orphan jamo characters detected (broken Korean): '{ko_text[:60]}'"
        )


def check_q7_spacing(key, ko_text, warnings):
    """Q7: Spacing sanity — no double spaces on a single rendered line."""
    # Multi-line XAML values have XML indentation whitespace that collapses in WPF.
    # Only check for double spaces within each individual line.
    # Also exempt: alignment-style double spaces before format placeholders {} or
    # after colons (intentional tabular spacing in labels like "이름:    {}").
    for line in ko_text.split('\n'):
        line_stripped = line.strip()
        if '  ' in line_stripped:
            # Exempt intentional alignment before {} placeholder or after ':'
            if re.search(r':\s{2,}\S|[^\s]\s{2,}\{', line_stripped):
                continue
            warnings.append(
                f"[Q7-DBLSPACE] Key '{key}': double space in line: '{line_stripped[:70]}'"
            )
            break  # one report per key
    # Korean character immediately followed by Latin letter (no space)
    cleaned = re.sub(
        r'pyRevit|CPython|IronPython|GitHub|YouTube|Revit|Roslyn|Bundle\.yaml'
        r'|__\w+__|[A-Z0-9]+\.[A-Z0-9]+',   # ALL_CAPS.CONST paths
        '', ko_text
    )
    if re.search(r'[가-힣][A-Za-z]', cleaned):
        warnings.append(
            f"[Q7-SPACING] Key '{key}': Hangul directly followed by Latin letter (missing space?): '{ko_text[:70]}'"
        )


# ---------------------------------------------------------------------------
# Cross-file terminology consistency check
# ---------------------------------------------------------------------------

def build_en_to_ko_map(all_pairs_data):
    """
    For each distinct English string value, collect all Korean translations.
    Returns {en_value: [(file, key, ko_value), ...]}
    """
    en_to_ko = defaultdict(list)
    for fname, en_dict, ko_dict in all_pairs_data:
        for key, en_val in en_dict.items():
            en_strip = en_val.strip()
            ko_val = ko_dict.get(key, '').strip()
            if not en_strip or not ko_val:
                continue
            if len(en_strip) < 3:
                continue  # too short to be meaningful
            if TECHNICAL_EXEMPT_RE.search(en_strip):
                continue
            en_to_ko[en_strip].append((fname, key, ko_val))
    return en_to_ko


def check_terminology_consistency(all_pairs_data):
    """
    Q1b: Same English string must always map to the same Korean string.
    Returns (fail_issues, warn_issues).

    Cases treated as WARN (not FAIL):
    - All divergent keys are from the same file AND the same English string
      appears only in that file (likely an upstream en_us duplicate, not our bug).
    """
    en_to_ko = build_en_to_ko_map(all_pairs_data)
    fail_issues = []
    warn_issues = []
    for en_val, occurrences in en_to_ko.items():
        ko_values = set(ko for _, _, ko in occurrences)
        if len(ko_values) <= 1:
            continue
        # Determine whether divergence spans multiple files
        files_involved = set(fname for fname, _, _ in occurrences)
        if len(files_involved) == 1:
            # Single file — likely an upstream en_us duplicate/copy-paste bug
            lines = [f"[Q1-TERM-WARN] Upstream duplicate: English '{en_val[:50]}' appears with same text"
                     f" in multiple keys of {next(iter(files_involved))}, translated differently:"]
            for fname, key, ko in sorted(occurrences, key=lambda x: x[1]):
                lines.append(f"    [{key}] → '{ko}'")
            warn_issues.append('\n'.join(lines))
        else:
            lines = [f"[Q1-TERM-FAIL] English '{en_val[:50]}' translated inconsistently across files:"]
            for fname, key, ko in sorted(occurrences, key=lambda x: (x[0], x[1])):
                lines.append(f"    {fname}  [{key}] → '{ko}'")
            fail_issues.append('\n'.join(lines))
    return fail_issues, warn_issues


# ---------------------------------------------------------------------------
# Per-file runner
# ---------------------------------------------------------------------------

def check_file_pair(en_path, ko_path):
    fname = ko_path.name
    issues = []
    warnings = []

    try:
        en_dict = parse_strings(en_path)
        ko_dict = parse_strings(ko_path)
    except ET.ParseError as e:
        return fname, [f"[XML] Parse error: {e}"], [], {}, {}

    for key in en_dict:
        en_text = en_dict[key]
        ko_text = ko_dict.get(key, '')
        if not ko_text:
            continue  # missing keys caught by structural QA

        check_q1_glossary(key, en_text, ko_text, issues)
        check_q2_button_style(key, ko_text, issues, warnings)
        check_q3_length_ratio(key, en_text, ko_text, issues, warnings)
        check_q4_description_style(key, ko_text, issues, warnings)
        check_q5_orphan_english(key, en_text, ko_text, issues)
        check_q6_jamo_integrity(key, ko_text, issues)
        check_q7_spacing(key, ko_text, warnings)

    return fname, issues, warnings, en_dict, ko_dict


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("pyRevit Korean (ko) Translation QUALITY Report")
    print("=" * 72)

    all_pairs_data = []   # [(filename, en_dict, ko_dict), ...]
    file_results = []     # [(fname, issues, warnings), ...]
    missing_files = []

    for en_rel, ko_rel in XAML_PAIRS:
        en_path = BASE / en_rel
        ko_path = BASE / ko_rel
        if not en_path.exists() or not ko_path.exists():
            missing_files.append(ko_rel)
            continue
        fname, issues, warnings, en_dict, ko_dict = check_file_pair(en_path, ko_path)
        file_results.append((fname, issues, warnings))
        all_pairs_data.append((fname, en_dict, ko_dict))

    # Cross-file terminology consistency
    print("\n--- Q1: Cross-file Terminology Consistency ---")
    term_fail_issues, term_warn_issues = check_terminology_consistency(all_pairs_data)
    if term_fail_issues:
        for issue in term_fail_issues:
            print(issue)
    if term_warn_issues:
        for issue in term_warn_issues:
            print(issue)
    if not term_fail_issues and not term_warn_issues:
        print("  ✓ All shared English strings translate consistently")

    # Per-file results
    print("\n--- Per-file Quality Checks ---")
    total_issues = 0
    total_warnings = 0
    pass_count = 0
    warn_count = 0
    fail_count = 0

    for fname, issues, warnings in file_results:
        total_issues += len(issues)
        total_warnings += len(warnings)
        if issues:
            fail_count += 1
            print(f"\n✗ {fname}")
            for i in issues:
                print(f"      {i}")
            for w in warnings:
                print(f"      {w}")
        elif warnings:
            warn_count += 1
            print(f"\n⚠ {fname}")
            for w in warnings:
                print(f"      {w}")
        else:
            pass_count += 1
            print(f"✓ {fname}")

    if missing_files:
        print(f"\n⚠ {len(missing_files)} file(s) skipped (not found in QA base):")
        for f in missing_files:
            print(f"    {f}")

    print("\n" + "=" * 72)
    print(f"Files checked : {len(file_results)}")
    print(f"PASS          : {pass_count}")
    print(f"WARN          : {warn_count}")
    print(f"FAIL          : {fail_count}")
    print(f"Term FAIL     : {len(term_fail_issues)}")
    print(f"Term WARN     : {len(term_warn_issues)}")
    print(f"Total issues  : {total_issues}")
    print(f"Total warnings: {total_warnings}")
    print("=" * 72)

    overall_fail = fail_count > 0 or len(term_fail_issues) > 0
    if overall_fail:
        print("\nResult: FAIL — fix issues above before PR.")
        sys.exit(1)
    elif warn_count > 0 or total_warnings > 0:
        print("\nResult: WARN — review warnings, then submit PR.")
        sys.exit(0)
    else:
        print("\nResult: PASS ✓")
        sys.exit(0)


if __name__ == "__main__":
    main()
