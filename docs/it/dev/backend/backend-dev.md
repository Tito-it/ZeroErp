# Backend-dev (LXC) – Guida operativa e configurazioni Django + Gunicorn + Nginx

> 👀 **Vedi anche**    
> Approfondimento dettagli installazione     
>
> * [Play-book-operativo](/dev/backend/play-book-operativo-backend).



> **Obiettivo**: contenitore LXC Debian 12 su Proxmox per ospitare il backend **Django** del progetto *Zero ERP*, con **Gunicorn**, **Nginx**, **Redis** (cache/sessioni) e connessione sicura a **PostgreSQL** su VM `dbdev`. Include anche Tailscale per l’accesso amministrativo, UFW per il firewall e best practice di sicurezza.

---

## 1) Architettura in sintesi

* **Proxmox** → CT LXC `backend-dev` (Debian 12, non privilegiato).
* **Rete** → IP LAN + **Tailscale** (MagicDNS). SSH solo per manutenzione.
* **App** → Django in **venv** Python, servito da **Gunicorn**.
* **Reverse proxy** → **Nginx** su 80/443 (HTTPS con self-signed in dev; redirect 80→443).
* **Cache/Sessioni** → **Redis** locale nel CT.
* **DB** → **PostgreSQL** su VM `dbdev` (scram-sha-256), schema dedicato **`django`**.

Schema logico della path richiesta:

```
Client → (HTTPS) Nginx :443 → (HTTP loopback) Gunicorn :8000 → Django → PostgreSQL (VM dbdev)
                                             ↘ static/media da Nginx (alias)
```

---

## 2) Creazione CT (wizard Proxmox)

* **Template**: `debian-12-standard_12.12-1_amd64.tar.zst`
* **Hostname**: `backend-dev`
* **CPU/RAM/Disk**: 2 vCPU / 4GB RAM / 20–30GB disco
* **Features**: *unprivileged*, `keyctl=on` (ok), `nesting` opzionale
* **Rete**: IP statico su `vmbr0` + (in seguito) Tailscale.

> **Nota TUN (Tailscale)** – Su **host Proxmox**, in `/etc/pve/lxc/<CTID>.conf`:

```
lxc.cgroup2.devices.allow: c 10:200 rwm
lxc.mount.entry: /dev/net/tun dev/net/tun none bind,create=file
```

Riavvia CT: `pct restart <CTID>`

---

## 3) Post-install base nel CT

### Locale & SSH

```bash
apt update && apt -y upgrade
apt install -y locales openssh-server sudo
sed -i 's/^# *\(it_IT.UTF-8 UTF-8\)/\1/' /etc/locale.gen
sed -i 's/^# *\(en_US.UTF-8 UTF-8\)/\1/' /etc/locale.gen
locale-gen && update-locale LANG=it_IT.UTF-8
```

**Utente amministrativo** (es. `tid`) + sudo + chiave SSH:

```bash
adduser tid && usermod -aG sudo tid
# ~/.ssh/authorized_keys con permessi (700 dir, 600 file)
```

**Hardening SSH** (`/etc/ssh/sshd_config`):

```
PermitRootLogin no
```

```bash
systemctl enable --now ssh
```

### Tailscale

```bash
apt install -y curl gnupg
curl -fsSL https://tailscale.com/install.sh | sh
systemctl enable --now tailscaled
# login (senza cert automatici):
tailscale up --hostname=backend-dev
```

### DNS/Firewall

* Se apt segnala errori DNS: impostare nameserver (p.es. `1.1.1.1`) o usare `tailscale up --accept-dns=false`.
* **UFW** (sequenza sicura):

```bash
apt install -y ufw
ufw allow 22/tcp
ufw default deny incoming
ufw default allow outgoing
ufw allow 80/tcp
ufw allow 443/tcp
ufw enable
ufw status verbose
```

---

## 4) Software applicativo

```bash
apt install -y \
  python3-venv python3-pip python3-dev \
  build-essential libpq-dev pkg-config \
  postgresql-client \
  nginx redis-server \
  git ca-certificates curl unzip
systemctl enable --now nginx redis-server
```

### Progetto Django

```bash
# workspace app
mkdir -p /home/tid/apps/zeroerp && cd /home/tid/apps/zeroerp
python3 -m venv .venv && source .venv/bin/activate
pip install --upgrade pip
pip install django gunicorn "psycopg[binary]" django-redis djangorestframework

# crea progetto (inner package: zeroerp_backend)
django-admin startproject zeroerp_backend .
# struttura finale appiattita:
# /home/tid/apps/zeroerp/
#   ├─ .venv/
#   ├─ manage.py
#   └─ zeroerp_backend/ (settings.py, urls.py, wsgi.py, asgi.py)
```

---

## 5) Static & media (best practice)

**Django** (`zeroerp_backend/settings.py`):

```python
import os
STATIC_URL = "/static/"
MEDIA_URL  = "/media/"
STATIC_ROOT = "/var/www/zeroerp/static"
MEDIA_ROOT  = "/var/www/zeroerp/media"
```

**FS & collectstatic**:

```bash
mkdir -p /var/www/zeroerp/static /var/www/zeroerp/media
chown -R tid:tid /var/www/zeroerp
source .venv/bin/activate && python manage.py collectstatic --noinput
```

**Nginx (blocchi server)** – `location` per static/media (vedi §8):

```
location /static/ { alias /var/www/zeroerp/static/; expires 7d; }
location /media/  { alias /var/www/zeroerp/media/;  expires off; }
```

---

## 6) Connessione a PostgreSQL (VM `dbdev`)

### Variabili d’ambiente (niente password in settings)

**File** `/etc/zeroerp/zeroerp.env` (permessi 640; gruppo `tid`):

```dotenv
DJANGO_SECRET_KEY=⚠️_metti-chiave-lunga-random
DJANGO_DEBUG=1
DJANGO_ALLOWED_HOSTS=backend-dev,backend-dev.tailXXXX.ts.net,localhost,127.0.0.1

DB_NAME=⚠️_nome_db
DB_USER=zeroerp_app
DB_PASSWORD=⚠️_password_scram
DB_HOST=⚠️_ip_o_hostname_dbdev
DB_PORT=5432
```

Permessi:

```bash
install -d -m 0750 /etc/zeroerp
printf "(vars)" | tee /etc/zeroerp/zeroerp.env >/dev/null
chown root:tid /etc/zeroerp /etc/zeroerp/zeroerp.env
chmod 750 /etc/zeroerp && chmod 640 /etc/zeroerp/zeroerp.env
```

**`settings.py`** – lettura env + DB + cache/sessioni:

```python
import os
from django.core.exceptions import ImproperlyConfigured

def env(name, default=None, required=False):
    v = os.environ.get(name, default)
    if required and (v is None or v == ""):  # utile in prod
        raise ImproperlyConfigured(f"Missing env var: {name}")
    return v

SECRET_KEY = env("DJANGO_SECRET_KEY", "dev-insecure")
DEBUG = env("DJANGO_DEBUG", "1") == "1"
ALLOWED_HOSTS = [h.strip() for h in env("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("DB_NAME", required=True),
        "USER": env("DB_USER", required=True),
        "PASSWORD": env("DB_PASSWORD", required=True),
        "HOST": env("DB_HOST", "127.0.0.1"),
        "PORT": env("DB_PORT", "5432"),
        "OPTIONS": {
            # search_path: primo 'django' così TUTTE le tabelle Django vivono lì
            "options": "-c search_path=django,public,config,anagrafiche,vendite,acquisti,dbops",
        },
    }
}

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": "redis://127.0.0.1:6379/1",
    }
}
SESSION_ENGINE = "django.contrib.sessions.backends.cached_db"

TIME_ZONE = "Europe/Rome"
USE_TZ = True
```

### Lato PostgreSQL (solo una volta, su VM `dbdev`)

```sql
-- ruolo applicativo
CREATE ROLE zeroerp_app LOGIN PASSWORD '⚠️_password_scram' NOCREATEDB NOCREATEROLE;

-- schema dedicato per Django
CREATE SCHEMA IF NOT EXISTS django AUTHORIZATION zeroerp_app;

-- imposta search_path del ruolo (garantisce creazione/lookup nello schema giusto)
ALTER ROLE zeroerp_app IN DATABASE ⚠️yourdb
  SET search_path = django, public, config, anagrafiche, vendite, acquisti, dbops;

-- (consigliato) hardening: evita CREATE accidentali in public
REVOKE CREATE ON SCHEMA public FROM zeroerp_app;

-- pg_hba.conf (solo IP del CT; autenticazione SCRAM)
-- host  ⚠️yourdb  zeroerp_app  ⚠️IP_backend-dev/32  scram-sha-256
```

> **Nota migrazione**: se per errore le prime tabelle Django sono finite in `public`, spostarle con `ALTER TABLE public.<t> SET SCHEMA django;` (sequence collegate incluse se presenti).

**Migrazioni & superuser** (con env caricato):

```bash
# shell: carica env (se permessi 640):
set -a; source <(sudo cat /etc/zeroerp/zeroerp.env); set +a
source .venv/bin/activate
python manage.py migrate
python manage.py createsuperuser
```

---

## 7) Sicurezza Django dietro proxy HTTPS

In `settings.py`:

```python
CSRF_TRUSTED_ORIGINS = [
    "https://backend-dev.tailXXXX.ts.net",
]
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
```

> Se provi login in **HTTP**, i cookie `Secure` non vengono inviati ⇒ errore CSRF atteso. Mantieni redirect 80→443.

---

## 8) Gunicorn (systemd) + Nginx

### Gunicorn come servizio

**Unit** `/etc/systemd/system/zeroerp-gunicorn.service`:

```ini
[Unit]
Description=ZeroERP Django (Gunicorn)
After=network.target

[Service]
User=tid
Group=tid
WorkingDirectory=/home/tid/apps/zeroerp
Environment="PATH=/home/tid/apps/zeroerp/.venv/bin"
EnvironmentFile=/etc/zeroerp/zeroerp.env
ExecStart=/home/tid/apps/zeroerp/.venv/bin/gunicorn zeroerp_backend.wsgi:application \
  --bind 127.0.0.1:8000 --workers 3 --timeout 60
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
systemctl daemon-reload
systemctl enable --now zeroerp-gunicorn
systemctl status zeroerp-gunicorn
```

### Nginx (HTTPS self‑signed + redirect)

**Cert self-signed (solo dev)**:

```bash
openssl req -x509 -nodes -newkey rsa:2048 -days 365 \
  -keyout /etc/ssl/private/backend-dev.key \
  -out /etc/ssl/certs/backend-dev.crt \
  -subj "/CN=backend-dev.tailXXXX.ts.net"
```

**Virtual host** `/etc/nginx/sites-available/zeroerp`:

```nginx
server {
    listen 443 ssl http2;
    server_name backend-dev.tailXXXX.ts.net backend-dev;

    ssl_certificate     /etc/ssl/certs/backend-dev.crt;
    ssl_certificate_key /etc/ssl/private/backend-dev.key;

    # STATIC & MEDIA
    location /static/ { alias /var/www/zeroerp/static/; expires 7d; }
    location /media/  { alias /var/www/zeroerp/media/;  expires off; }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host              $host;
        proxy_set_header X-Real-IP         $remote_addr;
        proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

# redirect permanente HTTP→HTTPS (usa 308 per preservare metodo)
server {
    listen 80;
    server_name backend-dev.tailXXXX.ts.net backend-dev;
    return 308 https://$host$request_uri;
}
```

```bash
ln -s /etc/nginx/sites-available/zeroerp /etc/nginx/sites-enabled/zeroerp
nginx -t && systemctl reload nginx
```

---

## 9) Snapshot & backup

* **Snapshot Proxmox**: comodo per rollback della *stessa* istanza (include identità Tailscale e cert self-signed; non usare per clonare nuovi ambienti senza sanificazione).
* **Clone**: crea un nuovo CT; rigenerare **SSH host keys**, **cert**, rifare `tailscale up`, aggiornare `.env` (SECRET\_KEY/DB), `ALLOWED_HOSTS` e `server_name`.
* **Backup `vzdump`**: se storage remoto, impostare `tmpdir: /var/tmp` per evitare errori `tar | zstd` su share instabili o piene.

---

## 10) Punti di forza della configurazione

* **Separazione netta DB ↔ App**: PostgreSQL su VM dedicata; l’app usa un **ruolo applicativo** a privilegi minimi.
* **Schema dedicato `django`**: tutte le tabelle/framework Django in uno schema isolato; **`search_path`** coerente (settings + ruolo DB).
* **Segreti fuori dal codice**: file env `/etc/zeroerp/zeroerp.env` (permessi 640) caricato da **systemd**.
* **HTTPS da subito**: Nginx 443 con self-signed; redirect 80→443; impostazioni Django per proxy HTTPS (cookie `Secure`, CSRF trusted origins).
* **Firewall minimale**: UFW solo **22/80/443** in ingresso; Redis e Gunicorn non esposti.
* **Accesso amministrativo sicuro**: **Tailscale** (WireGuard) + SSH disabilitato per root.
* **Static/media serviti da Nginx**: performance e separazione rispetto all’app.
* **Facile migrazione**: CT leggero; DB esterno evita problemi dati in redeploy o spostamento CT→VM.

---

## 11) Checklist rapida

* [ ] LXC `backend-dev` attivo (TUN abilitato) + Tailscale con MagicDNS
* [ ] UFW: deny incoming / allow outgoing; allow 22,80,443
* [ ] Python venv + pacchetti (Django, Gunicorn, psycopg, redis)
* [ ] `settings.py`: env vars, cache Redis, `search_path` con `django` primo
* [ ] `/etc/zeroerp/zeroerp.env` creato (640) e referenziato in systemd unit
* [ ] PostgreSQL: ruolo `zeroerp_app`, schema `django`, `pg_hba` con SCRAM e IP CT
* [ ] `migrate` ok; (se necessario) tabelle spostate `public`→`django`
* [ ] Gunicorn systemd attivo su 127.0.0.1:8000
* [ ] Nginx 443 con self-signed, redirect 80→443, alias `/static` `/media`
* [ ] Admin Django raggiungibile in HTTPS, CSS ok, login CSRF ok

---

## 12) Prossimi passi (facoltativi)

* **TLS pubblico** (Let’s Encrypt) su dominio reale; **HSTS** e `SECURE_SSL_REDIRECT` con `DEBUG=False`.
* **Log & metriche** (journald → file, logrotate, access/error Nginx); health-check di Gunicorn.
* **Celery/beat** se servono job asincroni; unit systemd dedicate.
* **RLS/GUC** su Postgres per policy row-level, se multi-tenant.
* **Pipeline CI/CD** per deploy ripetibili (migrazioni gestite in release).
