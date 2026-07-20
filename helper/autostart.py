import logging
import sys
import winreg

log = logging.getLogger('autostart')

_RUN_KEY = r'Software\Microsoft\Windows\CurrentVersion\Run'
_VALUE_NAME = 'ClientTrackerHelper'


def _command():
    if getattr(sys, 'frozen', False):
        # PyInstaller onefile build: sys.executable *is* the helper.
        return f'"{sys.executable}"'
    return f'"{sys.executable}" "{sys.argv[0]}"'


def ensure_registered():
    """Add (or refresh) a per-user Run-key entry so the helper launches
    automatically at login — no admin rights or separate installer needed.
    Safe to call on every startup: it's a no-op once the stored command
    already matches the current executable's path.
    """
    command = _command()
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY, 0, winreg.KEY_ALL_ACCESS) as key:
            try:
                existing, _ = winreg.QueryValueEx(key, _VALUE_NAME)
            except FileNotFoundError:
                existing = None
            if existing != command:
                winreg.SetValueEx(key, _VALUE_NAME, 0, winreg.REG_SZ, command)
                log.info('Registered autostart: %s', command)
    except OSError as exc:
        log.warning('Could not register autostart: %s', exc)
