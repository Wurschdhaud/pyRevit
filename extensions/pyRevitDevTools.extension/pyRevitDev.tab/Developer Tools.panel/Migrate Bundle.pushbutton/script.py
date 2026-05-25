"""Migrate inline script dunders into bundle.yaml across an .extension folder.

Uses pyRevitExtensionParser.ExtensionParser.ReadScriptMetadata to read raw
dunder values from each bundle script, then writes/merges them into the
bundle.yaml beside the script. Picks merge behaviour and optional script
cleanup at runtime. Backs up any existing bundle.yaml as bundle.yaml.bak
before overwriting.

Runs on IronPython (pyrevit.forms.pick_folder is not available under CPython).
"""
# pylint: disable=import-error,invalid-name,broad-except,wrong-import-position
from __future__ import absolute_import, print_function

import codecs
import os
import os.path as op
import shutil
from collections import OrderedDict

import clr
clr.AddReference('pyRevitExtensionParser')
from pyRevitExtensionParser import ExtensionParser  # noqa: E402

from pyrevit import forms, script
from pyrevit.coreutils import yaml as pyryaml


# Bundle directory extensions that can carry a script.py with dunders.
SCRIPT_BUNDLE_EXTS = (
    '.pushbutton', '.smartbutton', '.panelbutton', '.invokebutton',
    '.nobutton', '.linkbutton', '.combobox',
)

# Module-level dunder names the new parser knows how to extract. Used by the
# optional script-cleanup pass to comment matching lines out of script.py.
DUNDER_NAMES = (
    '__title__', '__authors__', '__author__', '__doc__', '__helpurl__',
    '__context__', '__highlight__', '__min_revit_ver__', '__max_revit_ver__',
    '__beta__', '__cleanengine__', '__fullframeengine__', '__persistentengine__',
)

output = script.get_output()


def clr_to_python(value):
    """Recursively convert .NET Dictionary / List values into native Python."""
    if value is None:
        return None
    if isinstance(value, (str, bool, int, float)):
        return value
    if hasattr(value, 'Keys') and hasattr(value, 'TryGetValue'):
        return OrderedDict((str(k), clr_to_python(value[k])) for k in value.Keys)
    if hasattr(value, 'Count') and not isinstance(value, str):
        return [clr_to_python(v) for v in value]
    return value


def find_script_in_bundle(bundle_dir):
    """Return the dunder-bearing .py script inside a bundle dir, or None."""
    try:
        files = os.listdir(bundle_dir)
    except OSError:
        return None
    # Exact "script.py" wins.
    for f in files:
        if f.lower() == 'script.py':
            return op.join(bundle_dir, f)
    # Fall back to the *_script.py / -script.py / .script.py conventions.
    for f in files:
        lower = f.lower()
        if lower.endswith('.py') and (
                lower.endswith('_script.py')
                or lower.endswith('-script.py')
                or lower.endswith('.script.py')):
            return op.join(bundle_dir, f)
    return None


def iter_bundles(extension_root):
    """Yield (bundle_dir, script_path) for every script-carrying bundle."""
    for dirpath, dirnames, _ in os.walk(extension_root):
        for name in dirnames:
            if any(name.lower().endswith(ext) for ext in SCRIPT_BUNDLE_EXTS):
                bundle = op.join(dirpath, name)
                script_path = find_script_in_bundle(bundle)
                if script_path:
                    yield bundle, script_path


def read_script_metadata(script_path):
    """Pull dunders from script_path via the new C# parser, as a native dict."""
    raw = ExtensionParser.ReadScriptMetadata(script_path)
    out = OrderedDict()
    for k in raw.Keys:
        out[str(k)] = clr_to_python(raw[k])
    return out


def merge_yaml(existing, incoming, policy, rel_label):
    """Return (merged, changed).

    policy:
        'yaml_wins'   - keep existing values where keys collide.
        'script_wins' - overwrite existing with incoming on collision.
        'ask'         - prompt per conflicting key.
    """
    existing = existing or OrderedDict()
    merged = OrderedDict(existing)
    changed = False

    for key, new_value in incoming.items():
        if key not in merged:
            merged[key] = new_value
            changed = True
            continue
        if merged[key] == new_value:
            continue
        if policy == 'yaml_wins':
            continue
        if policy == 'script_wins':
            merged[key] = new_value
            changed = True
            continue
        # policy == 'ask'
        choice = forms.CommandSwitchWindow.show(
            ['Keep YAML: {!r}'.format(merged[key]),
             'Use SCRIPT: {!r}'.format(new_value)],
            message='[{}] Conflict on `{}`'.format(rel_label, key),
        )
        if not choice:
            return existing, False  # cancel => skip this bundle entirely
        if choice.startswith('Use SCRIPT'):
            merged[key] = new_value
            changed = True

    return merged, changed


def comment_out_dunders(script_path):
    """Prefix module-level dunder assignments in script.py with '# '.

    Only matches dunders at column 0 to avoid touching identically-named
    assignments inside functions/classes. Continuation lines of a multi-line
    triple-quoted dunder are also commented out.
    """
    try:
        with codecs.open(script_path, 'r', 'utf-8') as f:
            lines = f.readlines()
    except (OSError, IOError):
        return False

    changed = False
    new_lines = []
    in_multiline = False
    multiline_quote = None

    for line in lines:
        if in_multiline:
            new_lines.append(line if line.startswith('# ') else '# ' + line)
            if multiline_quote in line:
                in_multiline = False
                multiline_quote = None
            changed = True
            continue

        starts_dunder = False
        for name in DUNDER_NAMES:
            if line.startswith(name) and len(line) > len(name) and line[len(name)] in (' ', '='):
                starts_dunder = True
                break

        if not starts_dunder:
            new_lines.append(line)
            continue

        new_lines.append('# ' + line)
        changed = True
        for quote in ('"""', "'''"):
            idx = line.find(quote)
            if idx >= 0:
                rest = line[idx + 3:]
                if quote not in rest:
                    in_multiline = True
                    multiline_quote = quote
                break

    if changed:
        with codecs.open(script_path, 'w', 'utf-8') as f:
            f.writelines(new_lines)
    return changed


# === Main ===
target = forms.pick_folder(title='Pick .extension folder to migrate')
if not target:
    script.exit()
if not target.lower().endswith('.extension'):
    forms.alert('Target folder must end with .extension.', exitscript=True)

cleanup_choice = forms.CommandSwitchWindow.show(
    ['Leave script.py alone',
     'Comment-out migrated dunders in script.py'],
    message='Script cleanup mode (applied after yaml write)',
)
if not cleanup_choice:
    script.exit()
strip_after = cleanup_choice.startswith('Comment')

merge_choice = forms.CommandSwitchWindow.show(
    ['YAML wins',
     'Script wins (overwrite YAML)',
     'Ask per-key on conflict'],
    message='Merge policy when bundle.yaml already has a key',
)
if not merge_choice:
    script.exit()
if merge_choice.startswith('YAML'):
    policy = 'yaml_wins'
elif merge_choice.startswith('Script'):
    policy = 'script_wins'
else:
    policy = 'ask'

output.print_md('### Migration started')
output.print_md('- Target: `{}`'.format(target))
output.print_md('- Cleanup: `{}`'.format(cleanup_choice))
output.print_md('- Merge: `{}`'.format(merge_choice))
output.print_md('')

total = migrated = skipped_no_change = errored = 0

for bundle_dir, script_path in iter_bundles(target):
    total += 1
    rel = op.relpath(bundle_dir, target)

    try:
        incoming = read_script_metadata(script_path)
    except Exception as ex:
        errored += 1
        output.print_md('- **ERROR** reading `{}`: `{}`'.format(rel, ex))
        continue

    if not incoming:
        skipped_no_change += 1
        continue

    bundle_yaml = op.join(bundle_dir, 'bundle.yaml')
    existing = None
    if op.isfile(bundle_yaml):
        try:
            existing = pyryaml.load_as_dict(bundle_yaml)
        except Exception as ex:
            errored += 1
            output.print_md('- **ERROR** loading existing yaml in `{}`: `{}`'.format(rel, ex))
            continue

    merged, changed = merge_yaml(existing, incoming, policy, rel)
    if not changed:
        skipped_no_change += 1
        continue

    if op.isfile(bundle_yaml):
        try:
            shutil.copy2(bundle_yaml, bundle_yaml + '.bak')
        except Exception as ex:
            output.print_md('- WARN backup failed for `{}`: `{}`'.format(rel, ex))

    try:
        pyryaml.dump_dict(merged, bundle_yaml)
    except Exception as ex:
        errored += 1
        output.print_md('- **ERROR** writing yaml in `{}`: `{}`'.format(rel, ex))
        continue

    if strip_after:
        try:
            comment_out_dunders(script_path)
        except Exception as ex:
            output.print_md('- WARN strip failed for `{}`: `{}`'.format(rel, ex))

    migrated += 1
    output.print_md('- Migrated `{}` ({} key(s))'.format(rel, len(incoming)))

output.print_md('')
output.print_md('### Done')
output.print_md('- Bundles scanned: **{}**'.format(total))
output.print_md('- Migrated: **{}**'.format(migrated))
output.print_md('- No changes: **{}**'.format(skipped_no_change))
output.print_md('- Errors: **{}**'.format(errored))
