---

title: 🚀 backend-dev — Django + Nginx + Gunicorn (LAN + Tailscale)
category: applicazioni
version: 1.0
license: GPL-3.0-or-later
-------------------------

# 🚀 backend-dev — Django + Nginx + Gunicorn (LAN + Tailscale)

Documentazione **ZeroERP-style** per mettere in produzione leggera (dev/stage) Django su `backend-dev` con **Gunicorn** e **Nginx**, accessibile sia da **LAN** (`192.168.X.8`) sia via **Tailscale** (`100.x.x.x`). Include tutte le **correttive** applicate in questa sessione.

---

## 🧱 Architettura finale

* **Gunicorn** esegue Django su `127.0.0.1:8000` (solo loopback)
* **Nginx** ascolta su `:80` (redirect) e `:443` (HTTPS) e fa **proxy_pass** verso Gunicorn
* **Static/Media** servite da Nginx (alias su `/var/www/ZeroErp`)
* **Variabili applicative** caricate da `env.sh` (per uso manuale) e **wrapper systemd**

```
Client → (HTTP/HTTPS) → Nginx → (HTTP 127.0.0.1:8000) → Gunicorn → Django
```

---

## 📂 Layout progetto (reale)

```
/home/tid/apps/ZeroErp/backend/
 ├─ manage.py
 ├─ env.sh                 # variabili per shell interattiva
 ├─ .venv/                 # venv Python
 ├─ apps/                  # app Django per dominio (business logic/API)
 ├─ zeroerp_backend/
 │   ├─ settings.py        # configurazione progetto
 │   ├─ urls.py            # routing principale
 │   └─ wsgi.py            # entrypoint WSGI
 └─ bin/
     └─ start-gunicorn.sh  # wrapper usato da systemd (sorgente env.sh)
```

### Convenzione struttura (raccomandata)

- `zeroerp_backend/` contiene **solo** configurazione progetto (settings, urls, asgi/wsgi).
- `apps/` contiene le app di dominio (`vendite`, `anagrafiche`, `magazzino`, ecc.).
- Evitare logica business in `zeroerp_backend/`: va sempre in `apps/<dominio>/services`.
- Accesso SQL/DB dedicato in `apps/<dominio>/db` (o `repositories`), API in `apps/<dominio>/api`.
- Test per app in `apps/<dominio>/tests/` con sottocartelle minime:
  - `api/` per test endpoint e contratto risposta
  - `services/` per test logica applicativa/orchestrazione
- Questa separazione e` intenzionale e **non richiede ristrutturazione**: e` gia` coerente con Django e con la crescita del progetto.

---

## 🔐 Variabili d’ambiente (dev)

**`env.sh`** (usata in shell e dal wrapper):

```bash
# ~/apps/ZeroErp/backend/env.sh
export DJANGO_SECRET_KEY="<generare>"
export DJANGO_DEBUG="1"
# Host ammessi: LAN + Tailscale + hostname
export DJANGO_ALLOWED_HOSTS="backend-dev,localhost,127.0.0.1,192.168.X.8,<ts-backend>"
# Database (dbdev)
export DB_NAME="zeroerp"
export DB_USER="zeroerp_user"
export DB_PASSWORD="<PASSWORD>"
export DB_HOST="192.168.X.6"
export DB_PORT="5432"
```

> Carica in shell quando lavori manualmente:

```bash
cd ~/apps/ZeroErp/backend
set -a; source ./env.sh; set +a
```

---

## ⚙️ Gunicorn con systemd (wrapper + service)

### 1) Wrapper di avvio

```bash
# ~/apps/ZeroErp/backend/bin/start-gunicorn.sh
#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/.."
set -a
source ./env.sh
set +a
exec .venv/bin/gunicorn zeroerp_backend.wsgi:application \
  --bind 127.0.0.1:8000 \
  --workers 3
```

```bash
chmod +x ~/apps/ZeroErp/backend/bin/start-gunicorn.sh
```

### 2) Unit systemd

```ini
# /etc/systemd/system/zeroerp-gunicorn.service
[Unit]
Description=ZeroErp Gunicorn
After=network.target

[Service]
User=tid
Group=www-data
WorkingDirectory=/home/tid/apps/ZeroErp/backend
ExecStart=/home/tid/apps/ZeroErp/backend/bin/start-gunicorn.sh
Restart=on-failure
RestartSec=3

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now zeroerp-gunicorn
sudo systemctl status zeroerp-gunicorn --no-pager
```

---

## 🌐 Nginx (vhost finale)

**File:** `/etc/nginx/sites-available/zeroerp` → link in `sites-enabled`

```nginx
# HTTPS (proxy a Gunicorn)
server {
    listen 443 ssl http2;
    server_name backend-dev.tailXXXX.ts.net backend-dev 192.168.X.8 <ts-backend>;

    ssl_certificate     /etc/ssl/certs/backend-dev.crt;
    ssl_certificate_key /etc/ssl/private/backend-dev.key;

    # Static & media
    location /static/ { alias /var/www/ZeroErp/static/;  expires 7d; }
    location /media/  { alias /var/www/ZeroErp/media/;   expires off; }

    location / {
        include proxy_params;
        proxy_set_header Host              $host;
        proxy_set_header X-Real-IP         $remote_addr;
        proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_pass http://127.0.0.1:8000;
    }
}

# HTTP → redirect a HTTPS (inclusi IP LAN/Tailscale)
server {
    listen 80;
    server_name backend-dev backend-dev.tailXXXX.ts.net 192.168.X.8 <ts-backend>;
    return 308 https://$host$request_uri;
}
```

**Abilita e ricarica:**

```bash
sudo ln -sf /etc/nginx/sites-available/zeroerp /etc/nginx/sites-enabled/zeroerp
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx
```

---

## 🧩 Settings Django — punti chiave

**`zeroerp_backend/settings.py`** (estratto):

```python
import os
from pathlib import Path
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent

def env(name, default=None, required=False):
    v = os.environ.get(name, default)
    if required and (v is None or v == ""):
        raise ImproperlyConfigured(f"Missing env var: {name}")
    return v

DEBUG = env("DJANGO_DEBUG", "1") == "1"
ALLOWED_HOSTS = [h.strip() for h in env("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")]

LANGUAGE_CODE = "it-it"
TIME_ZONE = "Europe/Rome"
USE_I18N = True
USE_TZ = True

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("DB_NAME", required=True),
        "USER": env("DB_USER", required=True),
        "PASSWORD": env("DB_PASSWORD", required=True),
        "HOST": env("DB_HOST", "127.0.0.1"),
        "PORT": env("DB_PORT", "5432"),
        "OPTIONS": {
            "options": "-c search_path=django,public,config,dbops,script,anagrafiche"
        },
    }
}

STATIC_URL = "/static/"
MEDIA_URL  = "/media/"
STATIC_ROOT = "/var/www/ZeroErp/static"
MEDIA_ROOT  = "/var/www/ZeroErp/media"

if DEBUG:
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE    = False
    CSRF_TRUSTED_ORIGINS = [
        "http://192.168.X.8", "https://192.168.X.8",
        "http://<ts-backend>", "https://<ts-backend>",
        "http://localhost", "http://127.0.0.1"
    ]
else:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE    = True
    CSRF_TRUSTED_ORIGINS = [
        "https://backend-dev.tailXXXX.ts.net"
    ]
```

---

## 📦 Static & Media

```bash
sudo mkdir -p /var/www/ZeroErp/{static,media}
python manage.py collectstatic --noinput
sudo chown -R www-data:www-data /var/www/ZeroErp
```

---

## ✅ Test di validazione

```bash
# Gunicorn in ascolto
ss -ltnp | grep 8000
# Nginx risponde (HTTP→HTTPS)
curl -I http://192.168.X.8/
# HTTPS via LAN (ignora cert self-signed con -k)
curl -I -k https://192.168.X.8/
# Tailscale
curl -I -k https://<IP_TAILSCALE>/
# Admin
curl -I -k https://192.168.X.8/admin/login/
```

---

## 🛠️ Troubleshooting (casi reali risolti)

### 1) **Vedo “Welcome to nginx!”**

* Il vhost `default` è attivo → **rimuovi** `/etc/nginx/sites-enabled/default`
* Il `server_name` non combacia con host/IP → **aggiungi IP/host** ai `server_name`

### 2) **DisallowedHost / 400**

* Aggiungi host/IP a `DJANGO_ALLOWED_HOSTS` in `env.sh`
* Riavvia Gunicorn: `sudo systemctl restart zeroerp-gunicorn`
* In sviluppo, per autoreload con service attivo: vedi `docs/it/dev/backend/gunicorn-dev-autoreload.md`

### 3) **CSRF 403 su IP/HTTPS**

* In `DEBUG` imposta `SESSION_COOKIE_SECURE=False`, `CSRF_COOKIE_SECURE=False`
* Aggiungi IP a `CSRF_TRUSTED_ORIGINS`

### 4) **502 Bad Gateway**

* Gunicorn non in ascolto → `systemctl status zeroerp-gunicorn`
* Verifica `proxy_pass` e socket/porta

### 5) **Conflitto porte (docs VS Code)**

* Mantieni **Gunicorn → 8000**, **docs** su `8001`/`8080`
* Controlla: `ss -ltnp | egrep ':8000|:8001'`

---

## 🧪 Comandi utili

```bash
# Rilanciare app
sudo systemctl restart zeroerp-gunicorn
sudo systemctl reload nginx

# Log
journalctl -u zeroerp-gunicorn -n 100 --no-pager
sudo tail -n 100 /var/log/nginx/error.log

# DB check da Django
python manage.py showmigrations
python manage.py migrate --plan
python manage.py dbshell -c 'SELECT current_database(), current_user;'
```

---

## 📎 Note finali

* Per accesso **Tailscale**, inserisci l’IP `100.x.x.x` in `server_name` Nginx e in `DJANGO_ALLOWED_HOSTS`.
* In produzione: usare certificati validi (Let’s Encrypt su dominio), `DEBUG=0`, header di sicurezza, e reverse proxy hardening.

> Esito: **backend-dev operativo** via `https://192.168.X.8/` e via IP Tailscale, con Nginx↔Gunicorn, statiche servite e fix applicati a `ALLOWED_HOSTS`/`CSRF`.
