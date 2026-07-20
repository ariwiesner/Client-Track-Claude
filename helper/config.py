import os
import sys

# Points at the public Client Tracker server. Change the defaults below to
# your real domain before building the distributable .exe (see build.bat) —
# or override per-machine with the CLIENT_TRACKER_API_URL env var.
API_URL = os.environ.get('CLIENT_TRACKER_API_URL', 'https://tracker.example.com/api')
FRONTEND_URL = os.environ.get('CLIENT_TRACKER_FRONTEND_URL', 'https://tracker.example.com')

# Only needed for a self-signed / private-CA setup (e.g. an internal LAN
# server using mkcert). A real deployment behind Caddy/Let's Encrypt has a
# publicly-trusted certificate, so there's nothing to copy here — this stays
# unset and CA_BUNDLE falls back to normal system cert verification.
_HELPER_DIR = os.path.dirname(os.path.abspath(__file__))
CA_BUNDLE = os.environ.get(
    'CLIENT_TRACKER_CA_BUNDLE',
    os.path.join(_HELPER_DIR, '..', 'certs', 'rootCA.pem'),
)
if not os.path.exists(CA_BUNDLE):
    CA_BUNDLE = True  # fall back to default cert verification

WATCH_POLL_SECONDS = 2.5
SYSTEMS_REFRESH_SECONDS = 60
WIDGET_POLL_SECONDS = 7
MATCH_CONFIDENCE_THRESHOLD = 85

APP_DIR = os.path.join(os.environ.get('LOCALAPPDATA', _HELPER_DIR), 'ClientTracker')
os.makedirs(APP_DIR, exist_ok=True)
