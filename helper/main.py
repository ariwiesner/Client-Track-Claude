import logging
import os
import sys
import threading
import tkinter as tk
from tkinter import messagebox
import webbrowser

import config
import auth
import autostart
import popup
import tray
from api_client import ApiClient, ApiError
from watcher import Watcher
from widget import FloatingWidget

log = logging.getLogger('main')

_SINGLE_INSTANCE_MUTEX_NAME = 'Global\\ClientTrackerHelperSingleInstance'


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s %(name)s: %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(os.path.join(config.APP_DIR, 'helper.log'), encoding='utf-8'),
        ],
    )


def _acquire_single_instance_lock():
    """Refuse to run a second copy of the helper. Two instances watching
    the same machine used to mean two independent popups (often out of
    sync — one old style, one new) for the same detection, and whichever
    instance was logged in as a different/stale user would silently start
    timers under that account instead of the one actually sitting at the
    keyboard. Returns (mutex_handle, already_running).
    """
    try:
        import win32event
        import win32api
        import winerror
    except ImportError:
        return None, False  # pywin32 missing — degrade to "always allowed"

    mutex = win32event.CreateMutex(None, False, _SINGLE_INSTANCE_MUTEX_NAME)
    already_running = win32api.GetLastError() == winerror.ERROR_ALREADY_EXISTS
    return mutex, already_running


def main():
    setup_logging()

    mutex, already_running = _acquire_single_instance_lock()
    if already_running:
        log.warning('Another instance of the helper is already running — exiting.')
        alert_root = tk.Tk()
        alert_root.withdraw()
        messagebox.showinfo(
            'Client Tracker',
            'העוזר כבר פועל ברקע (בדוק את סמל המגש). לא נפתח עותק נוסף.',
        )
        alert_root.destroy()
        return

    autostart.ensure_registered()

    token = auth.get_token()
    if not token:
        log.info('Login cancelled, exiting.')
        return

    api = ApiClient(token=token)

    root = tk.Tk()
    root.withdraw()  # no visible main window — only the floating widget/popups

    widget = FloatingWidget(root, api)

    def on_system_detected(system):
        # One window: a yes/no if the window title names the client, or a
        # single search-and-pick list if it doesn't. Nothing starts until
        # the user clicks a button inside it.
        popup.show_start_popup(root, watcher, api, system, widget)

    def on_system_left(system, entry):
        def on_stop():
            watcher.mark_leave_resolved()
            try:
                api.stop_time_entry(entry['id'])
            except ApiError as exc:
                log.warning('Could not stop timer: %s', exc)
            widget.refresh_now()

        def on_keep():
            watcher.mark_leave_resolved()

        popup.show_leave_popup(root, system, on_stop, on_keep)

    watcher = Watcher(
        api,
        ui_schedule=lambda fn: root.after(0, fn),
        on_system_detected=on_system_detected,
        on_system_left=on_system_left,
    )
    watcher.start()

    def open_dashboard():
        root.after(0, lambda: webbrowser.open(config.FRONTEND_URL))

    def relogin():
        def do_relogin():
            auth.clear_token()
            new_token = auth.get_token()
            if new_token:
                api.token = new_token
                log.info('Re-logged in.')
            else:
                log.info('Re-login cancelled.')
        root.after(0, do_relogin)

    def quit_app():
        watcher.stop()
        widget.stop()
        tray_icon.stop()
        root.after(0, root.quit)

    tray_icon = tray.create_tray_icon(open_dashboard, relogin, quit_app)
    threading.Thread(target=tray_icon.run, daemon=True).start()

    root.mainloop()


if __name__ == '__main__':
    main()
