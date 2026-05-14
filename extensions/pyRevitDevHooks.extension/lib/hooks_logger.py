# pylint: skip-file
import re
import os
import os.path as op
import datetime
HOOK_LOGS = op.join(os.environ.get('APPDATA', op.expandvars('%userprofile%')),
                    'pyRevit', 'hooks.log')


from pyrevit import revit


def _timestamp():
    return datetime.datetime.now().strftime("%m%j%H%M%S%f")


def _write_record(record_str):
    try:
        log_dir = op.dirname(HOOK_LOGS)
        if not op.exists(log_dir):
            os.makedirs(log_dir)
        with open(HOOK_LOGS, 'a') as f:
            f.write(record_str + '\n')
    except (IOError, OSError) as e:
        import sys
        print("hooks_logger: failed to write to {}: {}".format(HOOK_LOGS, e), file=sys.stderr)


def _get_hook_parts(hook_script):
    # finds the two parts of the hook script name
    # e.g command-before-exec[ID_INPLACE_COMPONENT].py
    # ('command-before-exec', 'ID_INPLACE_COMPONENT')
    parts = re.findall(
        r'([a-z -]+)\[?([A-Z _]+)?\]?\..+',
        op.basename(hook_script)
        )
    if parts:
        return parts[0]
    else:
        return '', ''


def log_hook(hook_file, data, log_doc_access=False):
    hook_name, hook_target = _get_hook_parts(hook_file)
    # collect document element count as doc access test if requested
    doc = revit.doc if log_doc_access else None
    count = len(revit.query.get_all_elements(doc=doc)) if doc else 0

    # write log record with data
    record_str = "{} [{}] ".format(_timestamp(), hook_name)
    for k,v in data.items():
        record_str += '{}: "{}" '.format(k, v)
    record_str += 'count: {}'.format(str(count))
    _write_record(record_str)