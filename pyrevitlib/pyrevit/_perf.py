# -*- coding: utf-8 -*-
"""Lightweight Python-side perf instrumentation.

Writes [PERF:py] lines to the same per-process sidecar log used by the C#
loader's LoggingHelper when [core] csharp_filelogging = true in
pyrevit_config.ini, so Python startup-script timings interleave with the
C# [PERF] timeline in a single file:

    %APPDATA%\\pyRevit\\{revit_version}\\pyRevit_{revit_version}_{pid}_csharp_loader.log

Self-contained on purpose: imports only stdlib so it can be the first
line of pyrevit/__init__.py without triggering circular loads.

When csharp_filelogging is off (default), every call is a near-zero-cost
no-op past the first resolution attempt.
"""
import os
import os.path as op
import time
import datetime

try:
    import configparser as _cfgp  # py3
except ImportError:
    import ConfigParser as _cfgp  # py2 / ironpython 2.7

# perf_counter exists on IronPython 2.7.6+ and CPython 3.3+; fall back to
# time.time() so a stripped-down engine still gets coarse-grained data.
_now = getattr(time, "perf_counter", None) or time.time

# Tracks the wall-clock time of the previous mark() call so we can emit a
# delta-since-last-mark. Cumulative-since-start can be computed off the
# timestamps that prefix every line.
_LAST = [_now()]

_RESOLVED = False
_ENABLED = False
_SIDECAR_PATH = None


def _read_csharp_filelogging():
    """Best-effort read of [core] csharp_filelogging from pyrevit_config.ini."""
    appdata = os.getenv("APPDATA")
    if not appdata:
        return False
    cfg_dir = op.join(appdata, "pyRevit")
    if not op.isdir(cfg_dir):
        return False
    # Mirror PyRevitConfig.TryFindConfigIniInDirectory: pick the first
    # *.ini whose filename contains "pyrevit" or "config", else fall back
    # to pyRevit_config.ini.
    cfg_path = None
    try:
        for name in os.listdir(cfg_dir):
            low = name.lower()
            if low.endswith(".ini") and ("pyrevit" in low or "config" in low):
                cfg_path = op.join(cfg_dir, name)
                break
    except OSError:
        return False
    if cfg_path is None:
        cfg_path = op.join(cfg_dir, "pyRevit_config.ini")
    if not op.isfile(cfg_path):
        return False
    parser = _cfgp.RawConfigParser()
    try:
        parser.read(cfg_path)
    except Exception:
        return False
    try:
        return parser.getboolean("core", "csharp_filelogging")
    except Exception:
        return False


def _revit_version():
    """Pull VersionNumber off the __revit__ global injected by the executor."""
    try:
        return str(__revit__.Application.VersionNumber)  # noqa: F821
    except Exception:
        return None


def _resolve_sidecar_path():
    appdata = os.getenv("APPDATA")
    if not appdata:
        return None
    rv = _revit_version()
    if not rv:
        return None
    cfg_dir = op.join(appdata, "pyRevit", rv)
    if not op.isdir(cfg_dir):
        try:
            os.makedirs(cfg_dir)
        except OSError:
            return None
    return op.join(cfg_dir, "pyRevit_{}_{}_csharp_loader.log".format(rv, os.getpid()))


def _resolve():
    global _RESOLVED, _ENABLED, _SIDECAR_PATH
    if _RESOLVED:
        return
    _RESOLVED = True
    try:
        if not _read_csharp_filelogging():
            return
        _SIDECAR_PATH = _resolve_sidecar_path()
        _ENABLED = _SIDECAR_PATH is not None
    except Exception:
        _ENABLED = False


def mark(label):
    """Record a perf checkpoint.

    Writes one DEBUG line to the sidecar log with elapsed time since the
    previous mark. Format mirrors the C# `[PERF]` lines for visual parity
    in the interleaved log. No-op when csharp_filelogging is disabled.
    """
    if not _RESOLVED:
        _resolve()
    if not _ENABLED:
        return
    now = _now()
    delta_ms = (now - _LAST[0]) * 1000.0
    _LAST[0] = now
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    line = "{} DEBUG [PERF:py] {}: {:.0f}ms\n".format(ts, label, delta_ms)
    try:
        f = open(_SIDECAR_PATH, "a")
        try:
            f.write(line)
        finally:
            f.close()
    except (IOError, OSError):
        pass


class time_block(object):
    """Context manager: time a block independently of the running timeline.

    Emits one DEBUG `[PERF:py]` line at exit, indented two extra spaces past
    `mark()` lines to mirror C# sub-item indentation (`[PERF]   <name>:`).
    """

    def __init__(self, label):
        self.label = label
        self._t0 = None

    def __enter__(self):
        if not _RESOLVED:
            _resolve()
        if _ENABLED:
            self._t0 = _now()
        return self

    def __exit__(self, exc_type, exc, tb):
        if not _ENABLED or self._t0 is None:
            return False
        elapsed_ms = (_now() - self._t0) * 1000.0
        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        line = "{} DEBUG [PERF:py]   {}: {:.0f}ms\n".format(
            ts, self.label, elapsed_ms
        )
        try:
            f = open(_SIDECAR_PATH, "a")
            try:
                f.write(line)
            finally:
                f.close()
        except (IOError, OSError):
            pass
        return False
