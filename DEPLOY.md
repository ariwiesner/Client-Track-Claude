# Deploying Client Tracker for real, multi-machine use

This turns the app from "runs on my laptop" into "a real service your dad's
office can use from any computer." Do this once; adding a new worker
afterwards is just step 6.

## 1. Get a VPS and a domain

1. Create an account with a cloud provider (DigitalOcean, Linode, Hetzner —
   any ~$5-6/month box works). Spin up the cheapest Ubuntu 22.04/24.04 droplet.
2. Note its public IP address.
3. Buy a cheap domain (Namecheap, Cloudflare, etc. — a few dollars/year), or
   use a subdomain of one you already own (e.g. `tracker.yourdomain.com`).
4. Point an **A record** for that domain/subdomain at the VPS's IP address.
   Wait a few minutes for DNS to propagate (check with `nslookup tracker.yourdomain.com`).

## 2. Install prerequisites on the VPS

SSH into the server, then:

```bash
sudo apt update && sudo apt install -y python3-venv python3-pip git

# Caddy (reverse proxy + automatic free HTTPS certificate)
sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https curl
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt update && sudo apt install -y caddy
```

## 3. Get the code onto the server

```bash
sudo mkdir -p /opt/client-tracker
sudo chown $USER:$USER /opt/client-tracker
cd /opt/client-tracker
git clone <your-repo-url> .   # or scp the project folder up instead
```

## 4. Backend

```bash
cd /opt/client-tracker/backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
nano .env   # set DJANGO_SECRET_KEY (any long random string),
            # DJANGO_ALLOWED_HOSTS=tracker.yourdomain.com,
            # DJANGO_CORS_ORIGINS=https://tracker.yourdomain.com

python manage.py migrate
python manage.py createsuperuser   # your admin login for /admin/
python manage.py collectstatic --noinput
deactivate
```

Install the systemd service so it runs forever and restarts on reboot:

```bash
sudo cp ../deploy/client-tracker-backend.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now client-tracker-backend
sudo systemctl status client-tracker-backend   # should say "active (running)"
```

## 5. Frontend

Build it **locally on your own computer** (or on the VPS, either works),
pointing at the real domain:

```bash
cd frontend
# .env.production already has VITE_API_URL=https://tracker.example.com/api —
# edit it to your real domain first.
npm install
npm run build
```

This produces `frontend/dist/`. Copy that folder to the VPS at
`/opt/client-tracker/frontend/dist` (e.g. `scp -r dist user@vps:/opt/client-tracker/frontend/dist`).

Then wire up Caddy:

```bash
sudo cp /opt/client-tracker/deploy/Caddyfile /etc/caddy/Caddyfile
sudo nano /etc/caddy/Caddyfile   # replace tracker.example.com with your real domain
sudo systemctl reload caddy
```

Visit `https://tracker.yourdomain.com` — Caddy fetches a free HTTPS
certificate automatically on first request. You should see the login page.

## 6. Adding a worker (including your dad) — the repeatable part

1. On your own machine, edit `helper/config.py`: set `API_URL` and
   `FRONTEND_URL` defaults to your real domain (once, committed to the repo —
   not per worker).
2. Build the helper .exe:
   ```
   cd helper
   python -m venv venv        # first time only
   venv\Scripts\activate
   pip install -r requirements.txt
   build.bat
   ```
   This produces `helper\dist\ClientTrackerHelper.exe`.
3. In the web app (as admin), go to **עובדים** and add the new worker
   (name, username, temporary password).
4. Send `ClientTrackerHelper.exe` to the worker's computer (email, USB,
   shared drive — it's a single portable file, no installer needed).
5. They double-click it, log in once with the username/temp password you
   gave them. It registers itself to auto-start at login from then on.

That's it — steps 1-2 only need redoing if you change the server address;
step 3-5 repeat for every new hire.
