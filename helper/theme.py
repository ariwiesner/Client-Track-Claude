"""Shared visual constants for the desktop helper — mirrors the web app's
palette (frontend/src/styles/colors.css) so native popups and the floating
widget read as the same product instead of a bolted-on system dialog.
"""

ACCENT = '#17c1e8'
ACCENT_HOVER = '#12a8cb'
ACCENT_TEXT = '#ffffff'
ACCENT_TINT = '#e4f8fc'

BG = '#f4f5fa'
SURFACE = '#ffffff'
BORDER = '#dfe1ec'
BORDER_STRONG = '#c7c9db'

TEXT = '#201f36'
TEXT_MUTED = '#5b5e79'
TEXT_FAINT = '#8f92ab'

SIGNAL_OK = '#2fa86e'
SIGNAL_OK_BG = '#e9f8f0'
SIGNAL_WARN = '#e0554a'
SIGNAL_WARN_BG = '#fdeceb'

# IBM Plex Sans Hebrew (used on the web) is loaded via Google Fonts there and
# isn't installed as a system font, so tkinter can't use it. Segoe UI is the
# closest match actually available on Windows and renders Hebrew cleanly.
FONT = 'Segoe UI'

# A color reserved purely as a chroma-key: any pixel drawn in this exact
# shade becomes fully see-through via -transparentcolor. Never used for
# real UI content, so it's safe to treat as "invisible" everywhere.
CHROMA_KEY = '#ff00fe'


def blend(hex_a, hex_b, t):
    """Linear-interpolate two '#rrggbb' colors; t=0 -> a, t=1 -> b."""
    a = tuple(int(hex_a[i:i + 2], 16) for i in (1, 3, 5))
    b = tuple(int(hex_b[i:i + 2], 16) for i in (1, 3, 5))
    mixed = tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))
    return '#%02x%02x%02x' % mixed


def round_window_corners(win, radius=16):
    """Best-effort rounded corners on Windows via a clip region. Silently
    does nothing where pywin32 isn't available — square corners degrade
    fine, they just look a little less soft."""
    try:
        import win32gui
        win.update_idletasks()
        w = win.winfo_width()
        h = win.winfo_height()
        if w <= 0 or h <= 0:
            return
        hwnd = win.winfo_id()
        region = win32gui.CreateRoundRectRgn(0, 0, w + 1, h + 1, radius, radius)
        win32gui.SetWindowRgn(hwnd, region, True)
    except Exception:
        pass


def round_window_circle(win, size):
    """Clip a window to a perfect circle — used by the collapsed timer dot."""
    try:
        import win32gui
        win.update_idletasks()
        hwnd = win.winfo_id()
        region = win32gui.CreateEllipticRgn(0, 0, size + 1, size + 1)
        win32gui.SetWindowRgn(hwnd, region, True)
    except Exception:
        pass


def make_draggable(win, handle):
    """Let the user drag a borderless (overrideredirect) window by `handle`."""
    state = {'x': 0, 'y': 0}

    def start(event):
        state['x'] = event.x
        state['y'] = event.y

    def drag(event):
        x = win.winfo_x() + event.x - state['x']
        y = win.winfo_y() + event.y - state['y']
        win.geometry(f'+{x}+{y}')

    handle.bind('<ButtonPress-1>', start)
    handle.bind('<B1-Motion>', drag)
