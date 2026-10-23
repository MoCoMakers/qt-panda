"""settings_store — the one place the GUI's persisted settings live.

Qt's ``QSettings`` defaults to ``NativeFormat``, which means the SAME source
lands in three different off-project places:

    Windows   HKEY_CURRENT_USER\\Software\\qt-panda\\dans-port   (the registry)
    macOS     ~/Library/Preferences/com.qt-panda.dans-port.plist
    Linux     ~/.config/qt-panda/dans-port.conf

That breaks platform isolation and takes instrument state out of the project:
on Windows there is not even a file to copy, diff or back up, and a fresh
machine silently falls back to the CODE defaults — which differ from a
configured bench (operator audit 2026-09-18; ``preamp/gain`` was 5 in the
registry against a 1.0 code default, ``row_align_on`` true against false,
``drift_corr_y`` -3 against -4).

This module pins storage to ONE ini file inside the project, the same way
``data_paths.py`` pins the data root — single authority, repo-relative,
env-overridable.  The file is created on first write and never otherwise
touched; nothing here reads or writes the registry except the one-time
migration below.

    import settings_store
    self._settings = settings_store.settings()

Location, in order:
  1. ``QTPANDA_SETTINGS``            — full path to an .ini (explicit override)
  2. ``<this folder>/qtpanda.ini``   — the normal case, beside the code

The team-share bundle (``make_bundle.py``) does not ship the GUI and contains
no ``QSettings`` user at all, so it needs nothing from this module; the
resolution still works if it is ever copied there, because it is relative to
this file rather than the working directory.

Migration from the old native store runs automatically the first time, and
can be re-run by hand afterwards (useful if a GUI was still running and wrote
fresh values to the registry on exit):

    python settings_store.py --migrate        # only fills in missing keys
    python settings_store.py --migrate --force
    python settings_store.py --show
"""
import os
import sys

from PySide6.QtCore import QSettings

# The legacy native identity — kept ONLY so the one-time migration can find
# the old values.  Nothing else in the codebase may construct this.
_LEGACY_ORG = "qt-panda"
_LEGACY_APP = "dans-port"

_HERE = os.path.dirname(os.path.abspath(__file__))


def _writable(d):
    return os.path.isdir(d) and os.access(d, os.W_OK)


def settings_path():
    """Absolute path of the ini file backing every GUI setting.

    Pure os.path work — no drive letters, no separators, no platform
    branches — so the same call resolves correctly on Windows, macOS and
    Linux.  The ini FORMAT is identical on all three as well, which is the
    whole point: one file you can copy between benches.
    """
    env = os.environ.get("QTPANDA_SETTINGS")
    if env:
        p = os.path.abspath(os.path.expanduser(env))
        d = os.path.dirname(p)
        if d and not os.path.isdir(d):
            os.makedirs(d, exist_ok=True)
        return p
    if _writable(_HERE):
        return os.path.join(_HERE, "qtpanda.ini")
    # Read-only checkout / network share / installed copy: keep it local to
    # the machine rather than failing, and say so — this is the only case in
    # which settings live outside the project.
    from PySide6.QtCore import QStandardPaths
    d = QStandardPaths.writableLocation(
        QStandardPaths.StandardLocation.AppConfigLocation) or os.getcwd()
    d = os.path.join(d, "qt-panda")
    os.makedirs(d, exist_ok=True)
    print("[settings] %s is not writable; using %s" % (_HERE, d))
    return os.path.join(d, "qtpanda.ini")


_migrated = False


def settings():
    """The project-local QSettings.  Same API as before — only the backing
    store moves, so every existing value()/setValue() call site is unchanged.
    Qt creates the file on the first write.

    If the ini does not exist yet, the old native store is drained into it
    once, so an already-configured bench keeps its DAC operating point,
    preamp gain and port instead of silently falling back to code defaults.
    """
    global _migrated
    if not _migrated and not os.path.isfile(settings_path()):
        _migrated = True
        try:
            migrate_from_native(verbose=False)
        except Exception as e:                     # never block the GUI
            print("[settings] migration skipped: %s" % e)
    return QSettings(settings_path(), QSettings.IniFormat)


def _legacy():
    return QSettings(_LEGACY_ORG, _LEGACY_APP)


def migrate_from_native(force=False, verbose=True):
    """Copy values out of the old per-platform native store into the ini.

    Returns (copied, skipped).  Without ``force`` an existing key in the ini
    wins, so re-running is safe and never clobbers a newer local value.
    """
    src, dst = _legacy(), settings()
    keys = src.allKeys()
    copied, skipped = [], []
    for k in keys:
        if not force and dst.contains(k):
            skipped.append(k)
            continue
        dst.setValue(k, src.value(k))
        copied.append(k)
    dst.sync()
    if verbose:
        for k in copied:
            print("  copied  %-20s = %s" % (k, src.value(k)))
        for k in skipped:
            print("  kept    %-20s = %s  (already set locally)"
                  % (k, dst.value(k)))
        if not keys:
            print("  nothing in the legacy native store")
        print("settings file: %s" % settings_path())
    return copied, skipped


def _main(argv):
    if "--show" in argv:
        s = settings()
        print("settings file: %s  (exists=%s)"
              % (settings_path(), os.path.isfile(settings_path())))
        for k in s.allKeys():
            print("  %-20s = %s" % (k, s.value(k)))
        return 0
    if "--migrate" in argv:
        migrate_from_native(force="--force" in argv)
        return 0
    print(__doc__)
    return 0


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
