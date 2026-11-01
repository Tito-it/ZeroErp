# backend-dev — Django + Gunicorn + Nginx (LAN + Tailscale)

> **Ultimo aggiornamento**: 1 novembre 2026
>
> **Destinatari**: chi configura o mantiene la macchina `backend-dev`, e chi deve
> replicarla su un'altra macchina.
>
> **Vedi anche**:
>
> * [Gunicorn in sviluppo — ricarica del codice](gunicorn-dev-autoreload.md) — `kill -HUP` e `--reload`
> * [Provisioning ruoli DB](provisioning-db-roles.md) — `zeroerp_app`, migratore, RLS
> * [Playbook operativo backend](play-book-operativo-backend.md) — la macchina da zero, solo comandi; timer e worker (§15-§16)
> * [Sicurezza e qualità statica](../sicurezza-e-qualita-statica.md) — segreti, `.env`, `check --deploy`

---

## 🧱 Architettura

* **Nginx** ascolta su `:80` (solo redirect) e `:443` (HTTPS): è l'**unico
  ingresso**, anche in sviluppo.
* **Gunicorn** esegue Django su `127.0.0.1:8000` (solo loopback), come servizio
  systemd `zeroerp-gunicorn`, direttamente sul working tree del repository.
* **Vite** (sviluppo) gira su `127.0.0.1:5173`; Nginx gli passa tutto ciò che non
  è `/api/` e `/health`. In produzione al suo posto c'è la build statica.
* **Static/Media** le serve Nginx.
* **Variabili d'ambiente** in file per-host, non versionati (sotto, «Variabili
  d'ambiente»).

```
Browser → Nginx :443 ─┬─ /api/, /health → Gunicorn 127.0.0.1:8000 → Django → PostgreSQL (dbdev)
                      └─ tutto il resto → Vite 127.0.0.1:5173   (produzione: build statica)
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

## 📂 Layout del backend

```
/home/tid/apps/ZeroErp/backend/
 ├─ manage.py
 ├─ manage-env.sh          # manage.py con l'env di .env.systemd
 ├─ manage-test.sh         # test Django con l'env di .env.systemd
 ├─ env.sh                 # env per-host (export), letto dai wrapper di bin/ — NON versionato
 ├─ .env.systemd           # env per-host (KEY=VALUE), letto da systemd — NON versionato
 ├─ .env                   # env per la shell interattiva — NON versionato
 ├─ .env.example           # modello versionato: solo i nomi delle variabili
 ├─ .venv/
 ├─ apps/                  # un'app Django per dominio (api/, services/, repository, tests/)
 ├─ zeroerp_backend/       # solo configurazione: settings.py, urls.py, wsgi.py
 ├─ deploy/
 │   ├─ systemd/           # template versionati degli unit (timer, worker)
 │   └─ sveglie.json       # cadenza e comando di ogni timer
 └─ bin/
     ├─ start-gunicorn.sh  # ExecStart del servizio web
     ├─ run-command.sh     # ExecStart dei timer: un management command headless
     ├─ install-timers.sh  # installa gli unit da deploy/systemd
     └─ dev-guni-aliases.sh
```

La struttura interna di un'app (`api/`, `services/`, `repository`, `tests/api/`,
`tests/services/`) e le regole di layer stanno in [api.md](../api.md).

---

## 🔐 Variabili d'ambiente

### Chi legge quale file

Gli stessi nomi vivono in **tre** file per-host, perché i tre consumatori leggono
formati diversi:

| File | Formato | Chi lo legge |
| --- | --- | --- |
| `backend/.env.systemd` | `KEY=VALUE`, senza `export` | systemd, con `EnvironmentFile=`: il servizio `zeroerp-gunicorn` (drop-in `override.conf`) e tutti i timer/worker installati da `install-timers.sh`; inoltre `manage-env.sh` e `manage-test.sh` |
| `backend/env.sh` | `export KEY=…` | `bin/start-gunicorn.sh` e `bin/run-command.sh`, con `source`, **dopo** che systemd ha già caricato `.env.systemd` |
| `backend/.env` | `export KEY=…` | la shell interattiva e gli smoke: `set -a; source ./.env; set +a` |

⚠️ **Per il servizio web e per i timer, su una variabile presente in entrambi
vince `env.sh`**: viene letto per ultimo e sovrascrive quello che systemd ha
messo. Una modifica fatta solo in `.env.systemd` a una variabile che c'è anche
in `env.sh` **non ha effetto**, senza nessun errore. Si cambia in tutti e due, o
la si tiene in uno solo.

Il modello versionato è **`backend/.env.example`**: si copia e si valorizza.

> ⛔ **I file veri non si committano**: contengono i segreti della macchina. Li
> tiene fuori `.gitignore` e, se ci rientrassero, li ferma gitleaks al commit.
> Regole e strumenti: [Sicurezza e qualità statica](../sicurezza-e-qualita-statica.md).

Dopo una modifica: `sudo systemctl restart zeroerp-gunicorn` (un `kill -HUP`
**non** rilegge l'ambiente: ricarica solo il codice).

### Le variabili

La fonte unica, con i default, è `zeroerp_backend/settings.py`: qui c'è cosa
fanno, non i valori.

| Variabile | Obbligatoria | Cosa decide |
| --- | --- | --- |
| `DJANGO_SECRET_KEY` | ✅ | firma JWT e sessioni. Nessun ripiego. Si genera con `python -c "import secrets; print(secrets.token_urlsafe(64))"` |
| `DJANGO_FIELD_ENCRYPTION_KEYS` | ✅ | chiavi Fernet dei segreti cifrati nel DB (`crypto_service`: password SMTP), **separate** dalla `SECRET_KEY`. Più chiavi separate da virgola: cifra la prima, decifrano tutte. Nessun ripiego; il backend non parte con una chiave non Fernet o ripetuta. Si genera con `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`. Rotazione: [sicurezza](../sicurezza-e-qualita-statica.md#le-chiavi-dei-dati-cifrati) |
| `DB_NAME`, `DB_USER`, `DB_PASSWORD` | ✅ | connessione PostgreSQL. `DB_USER` è **`zeroerp_app`**, mai un ruolo owner o `BYPASSRLS`: vedi [Provisioning ruoli DB](provisioning-db-roles.md) |
| `DB_HOST`, `DB_PORT`, `CONN_MAX_AGE` | | host (su `backend-dev`: `dbdev`), porta, riuso della connessione in secondi (`0` con pgbouncer in transaction mode) |
| `DJANGO_TRUSTED_PROXY_COUNT` | ✅ | quanti proxy fidati stanno davanti al backend (Nginx = `1`). Decide di quale `X-Forwarded-For` fidarsi: sbagliato è un difetto **muto** in tutti e due i versi. Si aggiorna se la catena cambia |
| `FRONTEND_URL` | ✅ | base dei link nelle email (invito, reset, attivazione): l'ingresso Nginx. Sbagliato non dà errore, manda link rotti |
| `DJANGO_DEBUG` | | default **spento** |
| `DJANGO_ALLOWED_HOSTS` | | host ammessi, separati da virgola: IP **e** nome MagicDNS di Tailscale, perché Nginx passa a Django il nome che il browser ha usato |
| `DJANGO_API_DOCS_ENABLED` | | Swagger/OpenAPI (`/api/docs/`, `/api/schema/`); segue `DEBUG` salvo scelta esplicita |
| `DJANGO_API_EXPOSE_TECHNICAL_DETAILS` | | dettaglio tecnico nell'envelope di errore: vedi [error-handling-api](../../backend/core/manual/error-handling-api.md). Solo sviluppo |
| `DJANGO_API_STRONG_IDEMPOTENCY_ENABLED`, `DJANGO_API_RETRY_AFTER_SECONDS`, `DJANGO_API_SEARCH_THROTTLE_RATE`, `DJANGO_API_LOGIN_THROTTLE_RATE`, `DJANGO_API_SECONDO_FATTORE_THROTTLE_RATE`, `DJANGO_API_EXCEPTION_MIDDLEWARE_ENABLED`, `DJANGO_REQUEST_LOG_ENABLED` | | comportamento dell'API: idempotenza forte, `Retry-After`, freno sulle ricerche e sul login (default `5/5m`, il presidio di produzione: si alza solo in sviluppo, per gli smoke), middleware delle eccezioni, giornale delle richieste |
| `CACHE_BACKEND`, `REDIS_URL`, `PERMISSIONS_CACHE_TTL` | | cache: Redis di default, `CACHE_BACKEND=locmem` in CI/test |
| `DOCUMENTI_STORAGE_ROOT` | | cartella dei documenti generati (default `backend/var/documenti`) |
| `LOG_DIR` | | cartella dei log applicativi (default `backend/logs/`, file `app.log`) |
| `ZEROERP_PRESIDI_DIGEST_DESTINATARIO` | | chi riceve il digest dei presidi. È un dato di **questa installazione**: sta qui e non nel repo. Vuoto vuol dire «non configurato», non «spento» |
| `AI_*` | | assistente AI (`AI_ENABLED`, `AI_PROVIDER`, `AI_API_KEY`, `AI_MODEL`, …) |
| `DJANGO_DEPRECATION_GATE` | | `1` in CI: le deprecation di Django 7 diventano errori |

Un esempio per `backend-dev` (i segreti restano segnaposto):

```bash
# backend/env.sh — stesso elenco, senza `export`, in backend/.env.systemd
export DJANGO_SECRET_KEY="<generata>"
export DJANGO_FIELD_ENCRYPTION_KEYS="<generata>"
export DJANGO_DEBUG=0
export DJANGO_API_DOCS_ENABLED=1
export DJANGO_ALLOWED_HOSTS="backend-dev,backend-dev.tailXXXX.ts.net,localhost,127.0.0.1,192.168.X.8,<ts-backend>"
export DJANGO_TRUSTED_PROXY_COUNT=1
export FRONTEND_URL="https://backend-dev.tailXXXX.ts.net"
export DB_HOST=dbdev
export DB_PORT=5432
export DB_NAME="zeroerp"
export DB_USER="zeroerp_app"
export DB_PASSWORD="<password>"
```

---

## ⚙️ Gunicorn con systemd

### Wrapper di avvio

`backend/bin/start-gunicorn.sh` (versionato): entra in `backend/`, fa `source`
di `env.sh` e lancia Gunicorn. Bind, numero di worker, timeout e `--reload` si
regolano con le variabili `ZEROERP_GUNICORN_*`, descritte in
[Gunicorn in sviluppo](gunicorn-dev-autoreload.md). Il default è
`127.0.0.1:8000`, 3 worker, timeout 60 s, niente reload.

⛔ **Il timeout non si alza da solo.** Gunicorn carica da sé `backend/gunicorn.conf.py`
(dalla directory di lavoro: `backend/` qui, `/app` nel Dockerfile), che all'avvio e a ogni
`kill -HUP` (gli hook `on_starting` e `on_reload`), con la modalità forte accesa, rifiuta di
partire se `SYSTEM_IDEMPOTENZA_IN_CORSO_SECONDI` non supera il timeout **effettivo** di almeno 30 secondi, se il timeout è 0 o se il worker non è `sync`.
Il motivo: oltre quella soglia una Idempotency-Key «in corso» si riprende, e una richiesta ancora
viva verrebbe eseguita due volte. ⚠️ Il controllo gira in un **processo figlio** usa e getta
(`manage.py verifica_presidi_avvio`), mai nel master: un master che carica Django passa ai worker di
un `kill -HUP` i moduli vecchi, e il codice nuovo non entra (successo dal 2026-10-24 al 2026-10-31). Timeout e soglia si cambiano insieme
([API — Idempotency-Key](../api.md), guida
[Le operazioni che non si ripetono](/guide/operazioni-che-non-si-ripetono)).

### Unit systemd

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

```ini
# /etc/systemd/system/zeroerp-gunicorn.service.d/override.conf
[Service]
EnvironmentFile=/home/tid/apps/ZeroErp/backend/.env.systemd
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now zeroerp-gunicorn
sudo systemctl status zeroerp-gunicorn --no-pager
```

I timer e i worker (fatturazione, code di lavoro e di stampa, email, digest) non
si scrivono a mano: i template sono in `backend/deploy/systemd/` e li installa
`sudo backend/bin/install-timers.sh`. Dettaglio nel
[Playbook operativo](play-book-operativo-backend.md), §15-§16.

---

## 🌐 Nginx (vhost)

**File:** `/etc/nginx/sites-available/zeroerp` → link in `sites-enabled`.
Le zone del rate limiting stanno in `/etc/nginx/conf.d/zeroerp-ratelimit.conf`
(sopra, «Rate limiting»).

```nginx
# HTTPS: /api/ e /health a Gunicorn, il resto al frontend (Vite in sviluppo)
server {
    listen 443 ssl;
    http2 on;
    server_name backend-dev.tailXXXX.ts.net backend-dev 192.168.X.8 <ts-backend>;

    ssl_certificate     /etc/ssl/certs/backend-dev.crt;
    ssl_certificate_key /etc/ssl/private/backend-dev.key;

    # Header di pagina. La CSP sta QUI e non in Django: la pagina HTML la
    # servono Vite (sviluppo) o la build statica (produzione), non Django.
    # HSTS e redirect invece sono in settings.py (sotto, «Settings Django»).
    # ⚠️ Nessuna `location` qui sotto ha un proprio `add_header`: se una ne
    #    aggiungesse uno, perderebbe TUTTI questi (regola di ereditarieta' di
    #    Nginx) e andrebbero ripetuti li'.
    # ✅ APPLICATA su backend-dev dal 2026-09-28, dopo un giro in `-Report-Only`
    # (collaudo a video: anteprime PDF ed email, gestione documenti con upload e
    # download, console pulita; violazione provocata con `fetch` esterno
    # segnalata, poi bloccata). Una macchina nuova rifa' lo stesso giro:
    # `Content-Security-Policy-Report-Only`, console, poi si toglie `-Report-Only`.
    #
    # SVILUPPO (Vite): l'HMR inietta script e apre un websocket sulla porta
    # della pagina, quindi rispetto alla produzione servono
    # `script-src 'unsafe-inline'` e `connect-src wss:`. ⛔ Le due politiche
    # differiscono SOLO in quei due punti: chi ne cambia una cambia l'altra.
    add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; font-src 'self' data:; connect-src 'self' wss:; frame-src 'self' blob:; object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'" always;
    # PRODUZIONE (build statica), al posto della riga sopra:
    # add_header Content-Security-Policy "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; font-src 'self' data:; connect-src 'self'; frame-src 'self' blob:; object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'" always;
    #
    # Perche' ogni voce: `style-src 'unsafe-inline'` per gli <style> che
    # PrimeVue inietta a runtime; `frame-src blob:` per l'anteprima PDF
    # (DocumentoEmissioneDialog, `URL.createObjectURL` in un iframe);
    # l'anteprima email (`srcdoc` con `sandbox=""`) e' gia' isolata.
    # `frame-ancestors 'none'` vale come l'X-Frame-Options: DENY di Django.
    add_header Referrer-Policy "same-origin" always;
    add_header Permissions-Policy "camera=(), microphone=(), geolocation=()" always;

    # Static & media: gli stessi percorsi di STATIC_ROOT / MEDIA_ROOT in settings.py
    location /static/ { alias /var/www/ZeroErp/static/;  expires 7d; }
    location /media/  { alias /var/www/ZeroErp/media/;   expires off; }

    # Cintura: cio' che Django gia' non serve (admin rimosso, Swagger spento
    # fuori da DEBUG) resta chiuso anche se un giorno lato Django ricomparisse.
    # Swagger in sviluppo: togliere `api/docs|api/schema` qui E accendere
    # `DJANGO_API_DOCS_ENABLED=1` nell'env.
    location ~ ^/(admin|api/docs|api/schema)(/|$) { return 404; }

    # Rate limiting: autenticazione stretta, resto largo.
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
        # ⛔ Senza questa riga Nginx accetta corpi fino a 1 MB (il suo
        #    default) e risponde 413 PRIMA di Django: un logo da 2 MB non
        #    arriva mai al backend, nel log di Django non resta traccia e il
        #    FE riceve un errore senza envelope. Mancava fino al 2026-10-01.
        #    Da quel giorno il FE traduce il 413 in «file troppo grande»
        #    (`MESSAGGI_STATO_PROXY` in useApiHandler), senza scrivere il
        #    limite: il numero vive qui e nei parametri.
        # Il valore segue i limiti dell'applicazione, che sono PARAMETRI
        # (`config.parameters`): `documenti_asset_upload_max_mb` e
        # `documenti_allegato_upload_max_mb`, 25 MB ciascuno, piu' il margine
        # del multipart. ⚠️ Chi alza uno di quei parametri alza anche questo,
        # o il limite vero resta quello di Nginx, senza errori parlanti.
        client_max_body_size 30m;
        include proxy_params;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_pass http://127.0.0.1:8000;
    }
    # Senza X-Forwarded-Proto: `/health` e' esente dal redirect HTTPS di
    # Django (SECURE_REDIRECT_EXEMPT), e risponde anche in HTTP diretto.
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

`include proxy_params` passa `Host`, `X-Real-IP` e `X-Forwarded-For`
(`$proxy_add_x_forwarded_for`): è la catena che `DJANGO_TRUSTED_PROXY_COUNT=1`
presuppone. Chi scrive gli header a mano invece di includerli deve passare gli
stessi tre.

**Abilita e ricarica:**

```bash
sudo ln -sf /etc/nginx/sites-available/zeroerp /etc/nginx/sites-enabled/zeroerp
sudo rm -f /etc/nginx/sites-enabled/default     # altrimenti risponde lui agli host non elencati
sudo nginx -t && sudo systemctl reload nginx
```

---

## 🧩 Settings Django — le scelte che contano

Il file è `zeroerp_backend/settings.py`, commentato riga per riga: qui c'è solo
la mappa, non una copia.

* **Nessun ripiego sui segreti e sulle variabili che non possono essere
  sbagliate** (`DJANGO_SECRET_KEY`, `DB_*`, `DJANGO_TRUSTED_PROXY_COUNT`,
  `FRONTEND_URL`): se mancano, il backend **non parte** (`ImproperlyConfigured`).
* **Niente `python -O`**: il backend rifiuta di partire con gli `assert` spenti,
  perché il codice li usa per restringere i tipi.
* **`search_path`** della connessione:
  `django,public,config,dbops,script,anagrafiche`. È lo stesso che il
  provisioning imposta sul ruolo `zeroerp_app`.
* **Una sola connessione, `default`, sul ruolo `zeroerp_app`.** Non esistono più
  alias verso ruoli `BYPASSRLS`: il middleware rifiuta una richiesta la cui
  connessione scavalca la RLS (`E_DB_ROLE_UNSAFE`). Vedi
  [Provisioning ruoli DB](provisioning-db-roles.md).
* **Dietro proxy**: `SECURE_PROXY_SSL_HEADER` si fida di `X-Forwarded-Proto`
  scritto da Nginx; l'IP del client lo ricava un solo building block,
  `core.services.request_context.get_client_ip`, con
  `DJANGO_TRUSTED_PROXY_COUNT`.
* **HSTS e redirect HTTPS**: `DJANGO_SECURE_HSTS_SECONDS` obbligatoria con
  `DEBUG=0`, senza default (`0` con un certificato auto-firmato, come su
  `backend-dev`); redirect acceso di default con `DEBUG=0`, `/health` esente.
  Sottodomini e preload spenti per scelta. Dettaglio e chiamanti diretti di
  Gunicorn: [Sicurezza e qualità statica](../sicurezza-e-qualita-statica.md),
  «HSTS e redirect HTTPS». Cambiarle vuole `systemctl restart`, non `HUP`.
* **Cookie e CSRF**: cookie `Secure` fuori da `DEBUG`; `CSRF_TRUSTED_ORIGINS` è
  l'indirizzo Tailscale di `backend-dev`. L'API autentica con JWT, quindi il CSRF
  riguarda solo le rotte a sessione.
* **Superficie pubblica**: niente `django.contrib.admin`, Swagger solo con
  `API_DOCS_ENABLED` (sopra, «Sicurezza della superficie pubblica»).
* **Email**: la posta dell'applicazione **non** passa dal mailer di Django.
  `EmailService` usa `config.email_account`; il mailer Django è in console, come
  rete per la sola posta che manda Django stesso.
* **Log**: su console e su file ruotato (`LOG_DIR/app.log`, 10 MB × 5). Ogni
  riga porta `req=<request_id>`; fuori da una richiesta vale `-`.

---

## 📦 Static & Media

```bash
sudo mkdir -p /var/www/ZeroErp/{static,media}
cd ~/apps/ZeroErp/backend && ./manage-env.sh collectstatic --noinput
sudo chown -R www-data:www-data /var/www/ZeroErp
```

Il percorso è quello di `STATIC_ROOT` / `MEDIA_ROOT` in `settings.py`, e il
vhost deve puntare lo stesso.

---

## ✅ Test di validazione

```bash
# Gunicorn e Vite solo su loopback
ss -ltnp | grep -E ':8000|:5173'                # solo 127.0.0.1
# Nginx: HTTP → HTTPS, poi il backend risponde
curl -I http://192.168.X.8/                     # 308
curl -ksi https://192.168.X.8/health            # 200
curl -ksi https://<IP_TAILSCALE>/health         # 200
# Superficie pubblica: 404 attesi, un 200 e' un'esposizione
curl -I -k https://192.168.X.8/admin/login/     # 404
curl -I -k https://192.168.X.8/api/docs/        # 404, salvo DJANGO_API_DOCS_ENABLED=1 + vhost aperto
# Header di pagina (CSP, Referrer-Policy, Permissions-Policy) dal vhost
curl -ksI https://192.168.X.8/ | grep -iE 'content-security|referrer|permissions'
# Redirect di Django: Gunicorn diretto in HTTP → 301, /health esente → 200
curl -sI http://127.0.0.1:8000/api/v1/core/me/ | head -1     # 301
curl -sI http://127.0.0.1:8000/health | head -1              # 200
# Django non esposto: da fuori la 8000 non risponde
curl -m 3 http://192.168.X.8:8000/health        # deve FALLIRE (timeout/refused)
# Rate limiting sull'autenticazione: dal 6°/7° tentativo 429
for i in $(seq 1 15); do curl -sk -o /dev/null -w "%{http_code} " -X POST https://192.168.X.8/api/v1/admin/token/ -H 'Content-Type: application/json' -d '{}'; done; echo
```

---

## 🛠️ Troubleshooting

### 1) «Welcome to nginx!»

* Il vhost `default` è attivo → rimuovere `/etc/nginx/sites-enabled/default`.
* L'host usato dal browser non è nei `server_name` → aggiungerlo.

### 2) `DisallowedHost` / 400

* Aggiungere l'host a `DJANGO_ALLOWED_HOSTS` in **`env.sh` e `.env.systemd`**
  (vince `env.sh`, vedi sopra), poi `sudo systemctl restart zeroerp-gunicorn`.

### 3) Una modifica al codice Python non si vede

* I worker girano con il codice vecchio:
  [Gunicorn in sviluppo](gunicorn-dev-autoreload.md).

### 4) Una modifica a una variabile d'ambiente non si vede

* Serve un `restart`, non un `HUP`.
* La variabile è anche in `env.sh`, che vince su `.env.systemd`.

### 5) Il backend non parte: `ImproperlyConfigured: Missing env var: …`

* Manca una delle variabili obbligatorie (tabella sopra).
  `journalctl -u zeroerp-gunicorn -n 50 --no-pager` dice quale.

### 6) 502 Bad Gateway

* Gunicorn non è in ascolto → `systemctl status zeroerp-gunicorn`.
* Su `/` e non su `/api/`: è Vite che non gira (`npm run dev` in `frontend/`).

### 7) 429 dal frontend

* È il rate limiting di Nginx, non il backend: la risposta non ha l'envelope di
  errore.

### 8) Tutte le liste vuote, nessun errore

* Il ruolo della connessione non ha i privilegi o le GUC non arrivano: vedi
  [Provisioning ruoli DB](provisioning-db-roles.md), «Verifica postura RLS».

---

## 🧪 Comandi utili

```bash
# Rilanciare
sudo systemctl restart zeroerp-gunicorn
sudo systemctl reload nginx

# Log
journalctl -u zeroerp-gunicorn -n 100 --no-pager
tail -n 100 ~/apps/ZeroErp/backend/logs/app.log
sudo tail -n 100 /var/log/nginx/error.log

# Django con l'env del servizio
cd ~/apps/ZeroErp/backend
./manage-env.sh check --deploy
./manage-env.sh showmigrations
./manage-env.sh dbshell -- -c 'SELECT current_database(), current_user;'   # atteso: zeroerp_app
./manage-test.sh apps.core.tests -v 2
```

---

## 📎 Produzione

La macchina è di sviluppo, ma le regole della superficie pubblica valgono già
tal quali. In più, in produzione:

* certificati validi (Let's Encrypt su dominio) al posto del self-signed;
* `DJANGO_DEBUG=0` e `DJANGO_API_DOCS_ENABLED=0`, niente
  `DJANGO_API_EXPOSE_TECHNICAL_DETAILS`;
* la build statica del frontend al posto del blocco Vite;
* niente `--reload`;
* `./manage-env.sh check --deploy` pulito
  ([Sicurezza e qualità statica](../sicurezza-e-qualita-statica.md)).
