import logging
import threading
import time

import psutil
import win32gui
import win32process

import config
from api_client import ApiError
from matching import extract_candidate_name, match_client

log = logging.getLogger('watcher')

PROMPT_SNOOZE_SECONDS = 5 * 60


def all_open_windows():
    """Return (pid, title) for every visible, titled top-level window on the
    machine — covers both browser windows (title includes the active tab's
    page title) and standalone apps.
    """
    results = []

    def _callback(hwnd, _):
        if not win32gui.IsWindowVisible(hwnd):
            return True
        title = win32gui.GetWindowText(hwnd)
        if not title:
            return True
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        results.append((pid, title))
        return True

    win32gui.EnumWindows(_callback, None)
    return results


def foreground_window():
    """Return (pid, title) for whatever window the user is actually looking
    at right now, or (None, None) if there isn't one with a title.
    """
    hwnd = win32gui.GetForegroundWindow()
    if not hwnd:
        return None, None
    title = win32gui.GetWindowText(hwnd)
    if not title:
        return None, None
    _, pid = win32process.GetWindowThreadProcessId(hwnd)
    return pid, title


def _system_matches_title(system, title, pid):
    """Does this window (title + owning pid) belong to the tracked system?

    Matched by the system's name appearing in the window title — this is
    what makes a browser tab (title 'Google Translate - Google Chrome') or a
    standalone app (title 'Netflix') both detectable without ever naming a
    process. If an optional process_name is configured, it additionally
    restricts matches to windows owned by that process, for systems where
    the office wants more precision (e.g. a dedicated accounting program).
    """
    name = (system.get('name') or '').strip().lower()
    if not name or name not in title.lower():
        return False
    process_name = (system.get('process_name') or '').strip().lower()
    if process_name:
        try:
            if psutil.Process(pid).name().lower() != process_name:
                return False
        except psutil.Error:
            return False
    return True


def windows_matching_system(system, windows=None):
    """All currently open windows (anywhere, not just foreground) that
    belong to this tracked system — used after confirmation to extract the
    client name, where we don't care if focus shifted in the meantime.
    """
    if windows is None:
        windows = all_open_windows()
    return [(pid, title) for pid, title in windows if _system_matches_title(system, title, pid)]


class Watcher:
    """Background-thread poller that watches configured systems. A system
    only triggers the confirm popup while its window is the one the user is
    actually looking at (the foreground window) — merely having it open in
    the background (e.g. a Google Translate tab sitting behind VS Code)
    doesn't count. Nothing starts silently: only after the user confirms
    does it try to auto-match a client from the window title, falling back
    to a manual picker if it can't tell.
    """

    def __init__(self, api, ui_schedule, on_system_detected, on_system_left):
        self.api = api
        self.ui_schedule = ui_schedule
        self.on_system_detected = on_system_detected
        self.on_system_left = on_system_left
        self._stop = threading.Event()
        self._thread = None

        self._systems = []
        self._clients = []
        self._last_config_refresh = 0
        # system id -> last time we asked "start tracking?", so we don't nag
        # every poll cycle while the system stays open/foreground.
        self._last_prompted = {}
        self._seen_open_system_ids = set()

        # State for detecting "stepped away from a running auto timer's system".
        self._monitored_entry_id = None
        self._was_on_system = False
        self._leave_prompt_open = False

    def start(self):
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()

    def _refresh_config(self):
        try:
            self._systems = [s for s in self.api.list_systems() if s['is_active']]
            self._clients = [c for c in self.api.list_clients() if c['is_active']]
            self._last_config_refresh = time.time()
        except ApiError as exc:
            log.warning('Could not refresh systems/clients: %s', exc)

    def _run(self):
        while not self._stop.is_set():
            if time.time() - self._last_config_refresh > config.SYSTEMS_REFRESH_SECONDS:
                self._refresh_config()

            windows = all_open_windows()
            currently_open = {
                system['id'] for system in self._systems
                if windows_matching_system(system, windows)
            }
            # Systems that closed entirely since last poll get a clean slate
            # to prompt again next time they're opened.
            closed = self._seen_open_system_ids - currently_open
            for system_id in closed:
                self._last_prompted.pop(system_id, None)
            self._seen_open_system_ids = currently_open

            fg_pid, fg_title = foreground_window()

            try:
                current_entry = self.api.current_time_entry()
            except ApiError as exc:
                log.warning('Could not check current timer: %s', exc)
                self._stop.wait(config.WATCH_POLL_SECONDS)
                continue

            if current_entry:
                # A timer's already running — watch for the user stepping
                # away from its system, and don't also offer to start a new
                # one on top of it.
                self._check_left_system(current_entry, fg_pid, fg_title)
            else:
                self._monitored_entry_id = None
                self._was_on_system = False
                # Only the system the user is actually looking at right now
                # can trigger a prompt — being open in another, unfocused
                # window doesn't count.
                if fg_title:
                    for system in self._systems:
                        if system['id'] in currently_open and _system_matches_title(system, fg_title, fg_pid):
                            self._maybe_prompt(system)
                            break  # one foreground window, at most one relevant prompt

            self._stop.wait(config.WATCH_POLL_SECONDS)

    def _maybe_prompt(self, system):
        last = self._last_prompted.get(system['id'])
        if last and time.time() - last < PROMPT_SNOOZE_SECONDS:
            return
        self._last_prompted[system['id']] = time.time()
        self.ui_schedule(lambda: self.on_system_detected(system))

    def _check_left_system(self, entry, fg_pid, fg_title):
        system_id = entry.get('system')
        if not system_id:
            # Manual entry (or a resumed one) — nothing to monitor.
            self._monitored_entry_id = None
            self._was_on_system = False
            return

        if entry['id'] != self._monitored_entry_id:
            # Newly-noticed running entry — they were just on its system a
            # moment ago (that's how auto-start happens), so start from "on".
            self._monitored_entry_id = entry['id']
            self._was_on_system = True
            self._leave_prompt_open = False
            return

        system = next((s for s in self._systems if s['id'] == system_id), None)
        if not system:
            return

        on_system_now = bool(fg_title) and _system_matches_title(system, fg_title, fg_pid)

        if self._was_on_system and not on_system_now and not self._leave_prompt_open:
            self._leave_prompt_open = True
            self.ui_schedule(lambda: self.on_system_left(system, entry))

        self._was_on_system = on_system_now

    def mark_leave_resolved(self):
        """Called once the user has answered the 'stepped away' popup, so a
        future leave (after returning to the system first) can ask again.
        """
        self._leave_prompt_open = False

    @property
    def clients(self):
        return self._clients

    def _match_client_for_system(self, system):
        """Try to name the client from the system's currently open window
        title(s). Read-only — makes no API calls and starts nothing."""
        for _pid, title in windows_matching_system(system):
            candidate = extract_candidate_name(title, system)
            client = match_client(candidate, self._clients) if candidate else None
            if client:
                return client
        return None

    def preview_client_match(self, system):
        """Used by the popup to decide, before showing anything, whether it
        can ask a plain yes/no ('start for {client}?') or needs the manual
        picker instead. Never starts a timer by itself."""
        return self._match_client_for_system(system)

    def resolve_and_start(self, system):
        """Auto-matches a client for `system` and starts a timer for it.
        Returns None once a timer is running (either just started here, or
        one was already running and this leaves it alone). Returns the
        cached client list if no confident match was found, so the caller
        can show the manual picker.
        """
        try:
            current = self.api.current_time_entry()
        except ApiError as exc:
            log.warning('Could not check current timer: %s', exc)
            return None
        if current is not None:
            return None  # a timer's already running — leave it alone

        client = self._match_client_for_system(system)
        if client:
            try:
                self.api.start_time_entry(client['id'], source='auto', system_id=system['id'])
                log.info('Auto-started timer for %s via %s', client['name'], system['name'])
            except ApiError as exc:
                log.warning('Could not auto-start timer: %s', exc)
            return None

        return self._clients
