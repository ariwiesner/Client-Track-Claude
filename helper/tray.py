from PIL import Image, ImageDraw
import pystray


def _make_icon_image():
    size = 64
    img = Image.new('RGB', (size, size), '#17c1e8')  # same accent as the web app
    draw = ImageDraw.Draw(img)
    draw.text((size * 0.22, size * 0.22), 'CT', fill='white')
    return img


def create_tray_icon(on_open_dashboard, on_relogin, on_quit):
    menu = pystray.Menu(
        pystray.MenuItem('Open Dashboard', lambda: on_open_dashboard()),
        pystray.MenuItem('Re-login', lambda: on_relogin()),
        pystray.MenuItem('Quit', lambda: on_quit()),
    )
    return pystray.Icon('client_tracker', _make_icon_image(), 'Client Tracker', menu)
