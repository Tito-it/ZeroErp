---

title: 🚀 backend-dev — Django + Nginx + Gunicorn (LAN + Tailscale)
category: applicazioni
version: 1.0
license: GPL-3.0-or-later
---

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

## 🔒 Sicurezza della superficie pubblica — regole, non opzioni

> ⚠️ **Questa macchina non e' produzione, ma le regole qui sotto valgono da
> subito e vanno in produzione tal quali.** Un'esposizione «tanto e' dev» e'
> quella che si dimentica al momento del deploy: il presidio si costruisce dove
> si sviluppa. Rilievo del 2026-09-21: `/admin/` rispondeva **200** a chiunque
> raggiungesse il proxy, e la root `/` ci redirigeva.

| # | Regola | Dove sta il presidio | Come si verifica |
| --- | --- | --- | --- |
| 1 | **Django e Vite non sono mai raggiungibili direttamente.** Gunicorn ascolta **solo su loopback** (`127.0.0.1:8000`), e cosi' il dev server Vite (`127.0.0.1:5173`); le porte 8000 e 5173 **non si aprono mai** in UFW ne' in Proxmox. L'unico ingresso e' Nginx, anche in sviluppo: il browser apre `https://<host>/`. ⛔ Niente `npm run dev -- --host` e niente `proxy` `/api` in Vite: era una seconda strada verso Django che scavalcava Nginx (rate limit, HTTPS, IP del client), chiusa il 2026-09-25 | `bin/start-gunicorn.sh` (`ZEROERP_GUNICORN_BIND`, default loopback), `frontend/vite.config.js` (`server.host`), UFW (`80/443` soltanto) | `ss -ltnp \| grep -E ':8000\|:5173'` → **solo** `127.0.0.1`; da un altro host `curl http://<IP>:8000/health` e `curl http://<IP>:5173/` **devono fallire** |
| 2 | **Nginx fa rate limiting**, piu' stretto sugli endpoint di autenticazione (token, reset password, attivazione): sono anonimi per natura e sono il bersaglio del brute-force | `/etc/nginx/conf.d/zeroerp-ratelimit.conf` + `limit_req` nel vhost (sotto) | 15 `curl` in fila su `/api/v1/admin/token/` → dal 6°/7° in poi **429** |
| 3 | **L'admin Django non esiste.** `django.contrib.admin` non e' in `INSTALLED_APPS`: zero `ModelAdmin`, il FE non lo usa, l'autenticazione e' JWT. Era una form di login a sessione aperta a chiunque | `settings.py` («Superficie pubblica»), `urls.py`; test `apps/core/tests/api/test_superficie_pubblica.py` | `/admin/login/` → **404**; `/` → **404** |
| 4 | **Swagger/OpenAPI e' uno strumento di sviluppo**: `/api/docs/` e `/api/schema/` elencano l'intera superficie API senza token. Esistono solo con `API_DOCS_ENABLED` (default = `DEBUG`), altrove **404** | `settings.API_DOCS_ENABLED`, `apps/core/api/api_docs_gate.py`; stesso test | `/api/docs/` → **404** con flag spento |
| 5 | **Cintura in Nginx** su 3 e 4: cio' che Django gia' non serve resta chiuso anche se un giorno lato Django ricomparisse | `location ~ ^/(admin\|api/docs\|api/schema)(/\|$) { return 404; }` nel vhost | come sopra; con Gunicorn fermo la risposta e' comunque il 404 di Nginx |

Il superuser (`createsuperuser`) serve ancora: e' il primo utente `auth_user` con
cui si entra **dal frontend**, non da un pannello.

### Rate limiting — file `http {}` (una tantum)

Le zone vanno nel contesto `http`, quindi fuori dal vhost:

```nginx
# /etc/nginx/conf.d/zeroerp-ratelimit.conf
# Chiave: IP del client. Dietro NAT aziendale piu' utenti condividono l'IP:
# per questo la zona "api" e' larga e quella "auth" stretta ma con burst.
limit_req_zone $binary_remote_addr zone=zeroerp_auth:10m rate=10r/m;
limit_req_zone $binary_remote_addr zone=zeroerp_api:10m  rate=20r/s;
limit_req_status 429;
limit_req_log_level warn;
```

Nel vhost (blocco completo piu' sotto): le `location ~` di autenticazione con
`zone=zeroerp_auth burst=5`, la `location /` con `zone=zeroerp_api burst=100`.
`nodelay` risponde subito 429 invece di accodare: il FE riceve un errore
leggibile, non un timeout. Il `429` arriva da Nginx, quindi **senza** l'envelope
di errore del BE: `useApiHandler` lo tratta come errore HTTP generico.

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

**`backend/.env`** (usata in shell e dal wrapper; il servizio systemd legge la
stessa lista, senza `export`, da `backend/.env.systemd`). Il modello versionato,
con i soli nomi, è **`backend/.env.example`**: si copia e si valorizza.

> ⛔ **I due file veri non si committano**: contengono i segreti della macchina.
> Li tiene fuori `.gitignore` e, se ci rientrassero, li ferma gitleaks al
> commit. Regole e strumenti: [Sicurezza e qualità statica](../sicurezza-e-qualita-statica.md).

```bash
# ~/apps/ZeroErp/backend/.env
# Obbligatoria, senza default: python -c "import secrets; print(secrets.token_urlsafe(64))"
export DJANGO_SECRET_KEY="<generata>"
# Default SPENTO: si accende a mano solo dove serve
export DJANGO_DEBUG="0"
# Swagger/OpenAPI (/api/docs/, /api/schema/): segue DEBUG; "1" per averlo con DEBUG=0
export DJANGO_API_DOCS_ENABLED="1"
# Host ammessi: LAN + Tailscale (IP E nome MagicDNS: Nginx passa a Django il nome
# che il browser ha usato) + hostname
export DJANGO_ALLOWED_HOSTS="backend-dev,backend-dev.tailXXXX.ts.net,localhost,127.0.0.1,192.168.X.8,<ts-backend>"
# Proxy fidati davanti al backend: 1 = Nginx. OBBLIGATORIO, senza il backend non parte.
# Se la catena cambia (un secondo proxy, un bilanciatore), si aggiorna questo numero.
export DJANGO_TRUSTED_PROXY_COUNT="1"
# Base dei link nelle email (invito, reset, attivazione): l'ingresso Nginx.
# OBBLIGATORIO: un valore sbagliato non da' errore, manda link che non funzionano.
export FRONTEND_URL="https://backend-dev.tailXXXX.ts.net"
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
set -a; source ./.env; set +a
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
# HTTPS: /api/ a Gunicorn, il resto al frontend (Vite in sviluppo)
server {
    listen 443 ssl http2;
    server_name backend-dev.tailXXXX.ts.net backend-dev 192.168.X.8 <ts-backend>;

    ssl_certificate     /etc/ssl/certs/backend-dev.crt;
    ssl_certificate_key /etc/ssl/private/backend-dev.key;

    # Static & media
    location /static/ { alias /var/www/ZeroErp/static/;  expires 7d; }
    location /media/  { alias /var/www/ZeroErp/media/;   expires off; }

    # Cintura: cio' che Django gia' non serve (admin rimosso, Swagger spento
    # fuori da DEBUG) resta chiuso anche se un giorno lato Django ricomparisse.
    # Swagger in sviluppo: togliere `api/docs|api/schema` qui E accendere
    # `DJANGO_API_DOCS_ENABLED=1` nell'env.
    location ~ ^/(admin|api/docs|api/schema)(/|$) { return 404; }

    # Rate limiting (zone in /etc/nginx/conf.d/zeroerp-ratelimit.conf):
    # autenticazione stretta, resto largo. Vedi «Sicurezza della superficie pubblica».
    location ~ ^/api/v1/(admin|portale|shop)/token(/|$) {
        limit_req zone=zeroerp_auth burst=5 nodelay;
        include proxy_params;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_pass http://127.0.0.1:8000;
    }
    location ~ ^/api/v1/auth/(password-reset-request|password-reset-confirm|attivazione)(/|$) {
        limit_req zone=zeroerp_auth burst=5 nodelay;
        include proxy_params;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_pass http://127.0.0.1:8000;
    }

    location /api/ {
        limit_req zone=zeroerp_api burst=100 nodelay;
        include proxy_params;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_pass http://127.0.0.1:8000;
    }
    location = /health {
        include proxy_params;
        proxy_pass http://127.0.0.1:8000;
    }

    # Frontend. SVILUPPO: il dev server Vite su loopback (`npm run dev`),
    # websocket dell'HMR compreso (il client lo apre sulla porta della pagina,
    # cioe' questa: nessuna porta scritta in vite.config.js).
    # Niente limit_req: al primo caricamento Vite serve centinaia di moduli.
    # PRODUZIONE: al posto di questo blocco, la build statica —
    #   location / { root /var/www/zeroerp/frontend; try_files $uri $uri/ /index.html; }
    # La catena davanti a Django (/api/) e' la stessa nei due casi: Nginx, 1 proxy.
    location / {
        proxy_pass http://127.0.0.1:5173;
        proxy_http_version 1.1;
        proxy_set_header Upgrade    $http_upgrade;
        proxy_set_header Connection "upgrade";
        # Vite accetta solo host noti (difesa dal DNS rebinding): gli ci si
        # presenta come localhost, il browser resta sull'host di Nginx.
        proxy_set_header Host localhost;
        proxy_read_timeout 1h;   # il websocket HMR resta aperto a lungo
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

SECRET_KEY = env("DJANGO_SECRET_KEY", required=True)   # nessun ripiego
DEBUG = env("DJANGO_DEBUG", "0") == "1"                  # default spento
ALLOWED_HOSTS = [h.strip() for h in env("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")]
# Swagger/OpenAPI: strumento di sviluppo, segue DEBUG salvo scelta esplicita
API_DOCS_ENABLED = env("DJANGO_API_DOCS_ENABLED", "1" if DEBUG else "0") == "1"

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
curl -I -k https://<IP_TAILSCALE>/health
# Superficie pubblica (vedi «Sicurezza della superficie pubblica»): 404 attesi, un 200 e' un'esposizione
curl -I -k https://192.168.X.8/admin/login/     # 404
curl -I -k https://192.168.X.8/                 # 404 (nessun redirect a /admin/)
curl -I -k https://192.168.X.8/api/docs/        # 404, salvo DJANGO_API_DOCS_ENABLED=1 + vhost aperto
# Django non esposto: solo loopback, e da fuori la 8000 non risponde
ss -ltnp | grep :8000                           # solo 127.0.0.1:8000
curl -m 3 http://192.168.X.8:8000/health        # deve FALLIRE (timeout/refused)
# Rate limiting sull'autenticazione: dal 6°/7° tentativo 429
for i in $(seq 1 15); do curl -sk -o /dev/null -w "%{http_code} " -X POST https://192.168.X.8/api/v1/admin/token/ -H 'Content-Type: application/json' -d '{}'; done; echo
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
* Provisioning utenti DB runtime/migrator: `docs/it/dev/backend/provisioning-db-roles.md`
* Debug dettaglio tecnico API: `docs/it/backend/core/manual/error-handling-api.md` (flag `DJANGO_API_EXPOSE_TECHNICAL_DETAILS`)

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
