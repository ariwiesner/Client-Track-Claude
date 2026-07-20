import logging
import tkinter as tk

import theme
from api_client import ApiError

log = logging.getLogger('popup')


def _shell(root, width, height, bottom_margin=90):
    """Borderless white card, rounded corners, docked above the floating
    widget in the bottom-right corner — same corner and surface language as
    the web app's cards, just native.
    """
    win = tk.Toplevel(root)
    win.title('Client Tracker')
    win.overrideredirect(True)
    win.attributes('-topmost', True)
    win.configure(bg=theme.BORDER_STRONG)

    sw = win.winfo_screenwidth()
    sh = win.winfo_screenheight()
    x = sw - width - 24
    y = sh - height - bottom_margin
    win.geometry(f'{width}x{height}+{x}+{y}')

    card = tk.Frame(win, bg=theme.SURFACE)
    card.place(x=1, y=1, width=width - 2, height=height - 2)

    theme.round_window_corners(win, radius=16)
    theme.make_draggable(win, card)
    return win, card


def _button(parent, text, command, primary=True, width=None):
    if primary:
        bg, fg, active_bg = theme.ACCENT, theme.ACCENT_TEXT, theme.ACCENT_HOVER
    else:
        bg, fg, active_bg = theme.SURFACE, theme.TEXT_MUTED, '#eceef6'
    return tk.Button(
        parent, text=text, command=command, bg=bg, fg=fg,
        activebackground=active_bg, activeforeground=fg,
        relief='flat', bd=0, font=(theme.FONT, 10, 'bold'),
        padx=14, pady=8, width=width, cursor='hand2',
        highlightthickness=0,
    )


def _start_timer(api, client, system, widget=None):
    try:
        api.start_time_entry(client['id'], source='auto', system_id=system['id'])
        log.info('Started timer for %s via popup (%s)', client['name'], system['name'])
    except ApiError as exc:
        log.warning('Could not start timer from popup: %s', exc)
    if widget is not None:
        widget.refresh_now()


def show_start_popup(root, watcher, api, system, widget=None):
    """First ask about the *system* ('I see you're working on X — start
    counting?'). Only once the user says yes do we try to name the client:
    if the window title confidently names one, start right away; otherwise
    fall back to the search-and-pick list. Nothing is billed until the user
    has clicked through both the system prompt and (if needed) the picker.
    """
    win, card = _shell(root, 320, 150)

    tk.Label(
        card, text=f"אני רואה שאתה עובד על {system['name']}",
        bg=theme.SURFACE, fg=theme.TEXT, font=(theme.FONT, 11, 'bold'),
        justify='right', wraplength=280,
    ).pack(anchor='e', padx=16, pady=(16, 4))
    tk.Label(
        card, text='להתחיל לספור לך זמן?',
        bg=theme.SURFACE, fg=theme.TEXT_MUTED, font=(theme.FONT, 9),
        justify='right', wraplength=280,
    ).pack(anchor='e', padx=16)

    def yes():
        win.destroy()
        client = watcher.preview_client_match(system)
        if client is not None:
            _start_timer(api, client, system, widget)
        else:
            _show_picker(root, api, system, watcher.clients, widget)

    def no():
        win.destroy()

    button_row = tk.Frame(card, bg=theme.SURFACE)
    button_row.pack(fill='x', padx=16, pady=(14, 16))
    _button(button_row, 'לא עכשיו', no, primary=False).pack(side='left')
    _button(button_row, 'התחלת מדידה', yes, primary=True).pack(side='right')

    win.protocol('WM_DELETE_WINDOW', no)


def _show_picker(root, api, system, clients, widget=None):
    win, card = _shell(root, 300, 360)

    tk.Label(
        card, text='על מי מהלקוחות זה עבור?',
        bg=theme.SURFACE, fg=theme.TEXT, font=(theme.FONT, 11, 'bold'),
        justify='right',
    ).pack(anchor='e', padx=16, pady=(16, 2))
    tk.Label(
        card, text=f"זיהינו פעילות ב-{system['name']}",
        bg=theme.SURFACE, fg=theme.TEXT_MUTED, font=(theme.FONT, 9),
        justify='right',
    ).pack(anchor='e', padx=16, pady=(0, 10))

    search_var = tk.StringVar()
    search_entry = tk.Entry(
        card, textvariable=search_var, font=(theme.FONT, 10), justify='right',
        relief='flat', bg=theme.BG, fg=theme.TEXT, insertbackground=theme.TEXT,
        highlightthickness=1, highlightbackground=theme.BORDER, highlightcolor=theme.ACCENT,
    )
    search_entry.pack(fill='x', padx=16, pady=(0, 8), ipady=6)
    search_entry.focus_set()

    listbox = tk.Listbox(
        card, font=(theme.FONT, 10), relief='flat', bd=0, justify='right',
        bg=theme.SURFACE, fg=theme.TEXT, selectbackground=theme.ACCENT_TINT,
        selectforeground=theme.TEXT, activestyle='none', highlightthickness=0,
    )
    listbox.pack(fill='both', expand=True, padx=16, pady=(0, 8))

    names = [c['name'] for c in clients]

    def refresh_list(*_):
        query = search_var.get().lower()
        listbox.delete(0, tk.END)
        for name in names:
            if query in name.lower():
                listbox.insert(tk.END, name)
        if listbox.size():
            listbox.selection_set(0)

    refresh_list()
    search_var.trace_add('write', refresh_list)

    def confirm(event=None):
        selection = listbox.curselection()
        if not selection:
            return
        name = listbox.get(selection[0])
        client = next((c for c in clients if c['name'] == name), None)
        if not client:
            return
        _start_timer(api, client, system, widget)
        win.destroy()

    listbox.bind('<Double-Button-1>', confirm)
    search_entry.bind('<Return>', confirm)

    button_row = tk.Frame(card, bg=theme.SURFACE)
    button_row.pack(fill='x', padx=16, pady=(0, 16))
    _button(button_row, 'לא עכשיו', win.destroy, primary=False).pack(side='left')
    _button(button_row, 'התחלת מדידה', confirm, primary=True).pack(side='right')

    win.protocol('WM_DELETE_WINDOW', win.destroy)


def show_leave_popup(root, system, on_stop, on_keep):
    """Shown when a timer auto-started for `system` is running but the user
    has switched away from it. Closing the window (the X button) counts as
    'keep counting' so an accidental dismiss can't lose a running timer.
    """
    win, card = _shell(root, 320, 160)

    tk.Label(
        card, text=f"עזבת את {system['name']}?", bg=theme.SURFACE, fg=theme.TEXT,
        font=(theme.FONT, 11, 'bold'), justify='right', wraplength=280,
    ).pack(anchor='e', padx=16, pady=(16, 4))
    tk.Label(
        card, text='להמשיך למדוד או לעצור את הטיימר?', bg=theme.SURFACE, fg=theme.TEXT_MUTED,
        font=(theme.FONT, 9), justify='right', wraplength=280,
    ).pack(anchor='e', padx=16)

    def stop():
        win.destroy()
        on_stop()

    def keep():
        win.destroy()
        on_keep()

    button_row = tk.Frame(card, bg=theme.SURFACE)
    button_row.pack(fill='x', padx=16, pady=(14, 16))
    _button(button_row, 'עצירת הטיימר', stop, primary=False).pack(side='left')
    _button(button_row, 'המשך מדידה', keep, primary=True).pack(side='right')

    win.protocol('WM_DELETE_WINDOW', keep)
