# Client Tracker

Office-wide client time-tracking app: Django/DRF backend, a React PWA dashboard, and a Windows desktop helper that auto-detects tracked systems and starts timers.

- `backend/` — Django + Django REST Framework API (SQLite locally; see `DEPLOY.md` for production setup)
- `frontend/` — React PWA (Vite), Hebrew/RTL dashboard for clients, billing, workers, profile
- `helper/` — Windows Tkinter tray app that watches open windows, matches them to a tracked system + client, and starts/stops timers automatically
- `deploy/` — systemd unit + Caddyfile for the production VPS deployment
- `DEPLOY.md` — step-by-step guide for deploying the backend/frontend to a VPS and building/distributing the helper `.exe`

## Git workflow

Repo: `git@github.com:ariwiesner/Client-Track-Claude.git`, branches `main` and `dev` already pushed.

- `dev` is the integration branch. Every new feature gets its **own branch off `dev`**, named after the feature (e.g. `feature/worker-summary`), not a generic name.
- Commit locally as normal while iterating on a feature.
- **Do not push a feature branch until the user explicitly confirms the feature is good** (e.g. "its good", "looks good"). Only push after that approval.
- Merging a feature branch into `dev`/`main` needs separate explicit instruction — don't assume approval of the feature implies approval to merge.
