import threading
import tkinter as tk
from datetime import datetime

import config
import theme
from api_client import ApiError

COLLAPSED_SIZE = 26          # solid center dot
COLLAPSED_HALO_SIZE = 52     # outer soft-glow footprint (also the window's clip circle)
EXPANDED_WIDTH = 248
EXPANDED_HEIGHT = 112
MARGIN = 20
TASKBAR_ALLOWANCE = 40
AUTO_COLLAPSE_MS = 1000
LEAVE_COLLAPSE_MS = 350


class FloatingWidget:
    """Always-on-top bottom-right widget. Polls the same server truth
    (/time-entries/current/) as the React widget, so it reflects timers
    started from either surface and stays correct across restarts.

    Shows the full card for a beat whenever a timer starts (or stops), then
    collapses into a small dot out of the way — hovering it expands the
    card again to show the client, elapsed time, and the stop button.
    """

    def __init__(self, root, api):
        self.root = root
        self.api = api
        self.entry = None          # server-truth running entry, or None
        self.stopped_entry = None  # local-only "awaiting continue" state
        self._stop_poll = threading.Event()
        self._tick_job = None
        self._collapse_job = None
        self._expanded = True

        self.win = tk.Toplevel(root)
        self.win.overrideredirect(True)
        self.win.attributes('-topmost', True)
        self.win.configure(bg=theme.SURFACE)
        self.win.withdraw()
        self.win.bind('<Enter>', self._on_enter)
        self.win.bind('<Leave>', self._on_leave)
        try:
            # Lets the collapsed dot's halo fade into real transparency
            # instead of sitting on an opaque square — any pixel left at
            # CHROMA_KEY is punched out by Windows, not just drawn white.
            self.win.wm_attributes('-transparentcolor', theme.CHROMA_KEY)
        except tk.TclError:
            pass

        self.canvas = tk.Canvas(self.win, highlightthickness=0, bg=theme.SURFACE)
        self.canvas.pack(fill='both', expand=True)

        self._set_geometry(expanded=True)

        self._poll_thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._poll_thread.start()

    # ---- geometry — anchored to the same bottom-right corner in both states ----
    def _anchor(self):
        sw = self.win.winfo_screenwidth()
        sh = self.win.winfo_screenheight()
        return sw - MARGIN, sh - MARGIN - TASKBAR_ALLOWANCE

    def _set_geometry(self, expanded):
        ax, ay = self._anchor()
        w, h = (EXPANDED_WIDTH, EXPANDED_HEIGHT) if expanded else (COLLAPSED_HALO_SIZE, COLLAPSED_HALO_SIZE)
        x, y = ax - w, ay - h
        self.win.geometry(f'{w}x{h}+{x}+{y}')
        self.canvas.config(width=w, height=h)
        bg = theme.SURFACE if expanded else theme.CHROMA_KEY
        self.win.configure(bg=bg)
        self.canvas.configure(bg=bg)
        if expanded:
            theme.round_window_corners(self.win, radius=18)
        else:
            theme.round_window_circle(self.win, w)

    # ---- hover expand/collapse ----
    def _on_enter(self, _event=None):
        if self._collapse_job:
            self.root.after_cancel(self._collapse_job)
            self._collapse_job = None
        if not self._expanded and (self.entry or self.stopped_entry):
            self._expanded = True
            self._set_geometry(expanded=True)
            self._draw()

    def _on_leave(self, _event=None):
        if self._collapse_job:
            self.root.after_cancel(self._collapse_job)
        self._collapse_job = self.root.after(LEAVE_COLLAPSE_MS, self._collapse)

    def _collapse(self):
        self._collapse_job = None
        if not self._expanded:
            return
        self._expanded = False
        self._set_geometry(expanded=False)
        self._draw()

    def _schedule_auto_collapse(self):
        if self._collapse_job:
            self.root.after_cancel(self._collapse_job)
        self._collapse_job = self.root.after(AUTO_COLLAPSE_MS, self._collapse)

    def stop(self):
        self._stop_poll.set()

    # ---- background polling (server truth) ----
    def _poll_loop(self):
        while not self._stop_poll.is_set():
            self._poll_once()
            self._stop_poll.wait(config.WIDGET_POLL_SECONDS)

    def _poll_once(self):
        try:
            current = self.api.current_time_entry()
            self.root.after(0, self._on_poll_result, current)
        except ApiError:
            pass

    def refresh_now(self):
        """Called right after something else (a popup starting/stopping a
        timer) changes server state, so the widget doesn't sit on stale data
        until the next background poll tick (up to WIDGET_POLL_SECONDS away).
        """
        threading.Thread(target=self._poll_once, daemon=True).start()

    def _on_poll_result(self, current):
        is_new = bool(current) and (not self.entry or self.entry['id'] != current['id'])
        if current:
            self.stopped_entry = None
        self.entry = current
        if is_new:
            self._expanded = True
            self._set_geometry(expanded=True)
            self._schedule_auto_collapse()
        self._draw()

    # ---- rendering (canvas-drawn so the collapsed state can be a true circle) ----
    def _draw(self):
        if self._tick_job:
            self.root.after_cancel(self._tick_job)
            self._tick_job = None

        self.canvas.delete('all')

        if not self.entry and not self.stopped_entry:
            self.win.withdraw()
            return

        self.win.deiconify()

        if not self._expanded:
            self._draw_collapsed()
            if self.entry:
                self._tick()
            return

        if self.entry:
            self._draw_expanded_running()
            self._tick()
        elif self.stopped_entry:
            self._draw_expanded_stopped()

    def _draw_collapsed(self):
        canvas_size = COLLAPSED_HALO_SIZE
        center = canvas_size / 2
        color = theme.ACCENT if self.entry else theme.TEXT_FAINT

        # Two soft, pale rings behind the solid dot — closest approximation
        # of a true alpha-blended glow that plain Tk canvas fills allow.
        for diameter, fade in ((canvas_size, 0.86), (canvas_size * 0.68, 0.6)):
            r = diameter / 2
            ring_color = theme.blend(color, '#ffffff', fade)
            self.canvas.create_oval(
                center - r, center - r, center + r, center + r,
                fill=ring_color, outline='',
            )

        dot_r = COLLAPSED_SIZE / 2
        self.canvas.create_oval(
            center - dot_r, center - dot_r, center + dot_r, center + dot_r,
            fill=color, outline='',
        )

    def _rounded_card(self, w, h, radius=18):
        c = self.canvas
        c.create_rectangle(radius, 1, w - radius, h - 1, fill=theme.SURFACE, outline='')
        c.create_rectangle(1, radius, w - 1, h - radius, fill=theme.SURFACE, outline='')
        for x, y in [(radius, radius), (w - radius, radius), (radius, h - radius), (w - radius, h - radius)]:
            c.create_oval(x - radius, y - radius, x + radius, y + radius, fill=theme.SURFACE, outline='')
        c.create_rectangle(1, 1, w - 1, h - 1, outline=theme.BORDER)

    def _draw_button(self, x, y, w, h, text, command, primary=True):
        bg = theme.ACCENT if primary else theme.SURFACE
        fg = theme.ACCENT_TEXT if primary else theme.TEXT_MUTED
        tag = f'btn{id(command)}'
        self.canvas.create_rectangle(
            x, y, x + w, y + h, fill=bg, outline='' if primary else theme.BORDER, tags=tag,
        )
        self.canvas.create_text(x + w / 2, y + h / 2, text=text, fill=fg, font=(theme.FONT, 9, 'bold'), tags=tag)
        self.canvas.tag_bind(tag, '<Button-1>', lambda _e: command())
        self.canvas.tag_bind(tag, '<Enter>', lambda _e: self.canvas.config(cursor='hand2'))
        self.canvas.tag_bind(tag, '<Leave>', lambda _e: self.canvas.config(cursor=''))

    def _draw_expanded_running(self):
        w, h = EXPANDED_WIDTH, EXPANDED_HEIGHT
        self._rounded_card(w, h)
        self.canvas.create_text(
            w - 18, 16, anchor='e', text=self.entry['client_name'],
            fill=theme.TEXT, font=(theme.FONT, 10, 'bold'),
        )
        self.canvas.create_text(
            w - 18, 32, anchor='e', text=self.entry.get('system_name') or 'ידני',
            fill=theme.TEXT_FAINT, font=(theme.FONT, 8),
        )
        self.clock_text = self.canvas.create_text(
            w - 18, 56, anchor='e', text='00:00:00',
            fill=theme.ACCENT, font=(theme.FONT, 15, 'bold'),
        )
        self._draw_button(16, h - 34, 60, 24, 'עצירה', self._stop_clicked, primary=True)
        self._draw_button(84, h - 34, 24, 24, '✕', self._cancel, primary=False)

    def _draw_expanded_stopped(self):
        w, h = EXPANDED_WIDTH, EXPANDED_HEIGHT
        self._rounded_card(w, h)
        self.canvas.create_text(
            w - 18, 16, anchor='e', text=self.stopped_entry['client_name'],
            fill=theme.TEXT, font=(theme.FONT, 10, 'bold'),
        )
        self.canvas.create_text(
            w - 18, 32, anchor='e', text=self.stopped_entry.get('system_name') or 'ידני',
            fill=theme.TEXT_FAINT, font=(theme.FONT, 8),
        )
        self.canvas.create_text(
            w - 18, 56, anchor='e', text='הטיימר נעצר',
            fill=theme.TEXT_FAINT, font=(theme.FONT, 10),
        )
        self._draw_button(16, h - 34, 66, 24, 'המשך', self._continue, primary=True)
        self._draw_button(90, h - 34, 24, 24, '✕', self._dismiss_stopped, primary=False)

    def _tick(self):
        if not self.entry or not self._expanded:
            return
        start = datetime.fromisoformat(self.entry['start_time'])
        elapsed = datetime.now(start.tzinfo) - start
        total_seconds = max(0, int(elapsed.total_seconds()))
        h, rem = divmod(total_seconds, 3600)
        m, s = divmod(rem, 60)
        if hasattr(self, 'clock_text'):
            self.canvas.itemconfig(self.clock_text, text=f'{h:02d}:{m:02d}:{s:02d}')
        self._tick_job = self.root.after(1000, self._tick)

    # ---- actions (network call on a worker thread, UI update marshaled back) ----
    def _run_action(self, fn, on_done):
        def worker():
            try:
                result = fn()
                self.root.after(0, on_done, result)
            except ApiError:
                pass
        threading.Thread(target=worker, daemon=True).start()

    def _cancel(self):
        entry_id = self.entry['id']

        def on_done(_):
            self.entry = None
            self._draw()

        self._run_action(lambda: self.api.cancel_time_entry(entry_id), on_done)

    def _stop_clicked(self):
        entry_id = self.entry['id']

        def on_done(stopped):
            self.entry = None
            self.stopped_entry = stopped
            self._expanded = True
            self._set_geometry(expanded=True)
            self._schedule_auto_collapse()
            self._draw()

        self._run_action(lambda: self.api.stop_time_entry(entry_id), on_done)

    def _continue(self):
        entry_id = self.stopped_entry['id']

        def on_done(new_entry):
            self.stopped_entry = None
            self.entry = new_entry
            self._draw()

        self._run_action(lambda: self.api.resume_time_entry(entry_id), on_done)

    def _dismiss_stopped(self):
        self.stopped_entry = None
        self._draw()
