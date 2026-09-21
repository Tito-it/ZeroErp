# Playbook operativo (SOLO COMANDI)

> Copia‑incolla sequenziale per creare un CT `backend-*` come `backend-dev` (Django + Gunicorn + Nginx, Redis, PostgreSQL esterno, Tailscale, UFW). Sostituisci i **⚠️ segnaposto**.

## Variabili (adatta e poi esegui)

```bash
export CTID=⚠️102
export HOSTNAME=backend-dev
export TAIL_NAME=backend-dev.tailXXXX.ts.net
export APP_USER=tid
export DB_NAME=⚠️yourdb
export DB_USER=zeroerp_app
export DB_PASS=⚠️StrongPassword
export DB_HOST=⚠️dbdev.tailXXXX.ts.net
export DB_PORT=5432
export DB_BATCH_PASS=⚠️StrongBatchPassword   # ruolo zeroerp_batch_fatturazione (§15, batch fatturazione)
```

## 0) Host Proxmox – abilita TUN e riavvia CT

```bash
echo "lxc.cgroup2.devices.allow: c 10:200 rwm" >> /etc/pve/lxc/$CTID.conf
echo "lxc.mount.entry: /dev/net/tun dev/net/tun none bind,create=file" >> /etc/pve/lxc/$CTID.conf
pct restart $CTID
```

## 1) Base nel CT (Debian 12)

```bash
apt update && apt -y upgrade
apt install -y locales openssh-server sudo curl gnupg ufw
sed -i '/it_IT.UTF-8 UTF-8/s/^# *//' /etc/locale.gen
sed -i '/en_US.UTF-8 UTF-8/s/^# *//' /etc/locale.gen
locale-gen && update-locale LANG=it_IT.UTF-8
adduser $APP_USER && usermod -aG sudo $APP_USER
printf '
PermitRootLogin no
' >> /etc/ssh/sshd_config && systemctl restart ssh
```

## 2) Tailscale + UFW

```bash
curl -fsSL https://tailscale.com/install.sh | sh
systemctl enable --now tailscaled
# login manuale o con auth-key
# tailscale up --auth-key=tskey-XXXX --hostname=$HOSTNAME
ufw allow 22/tcp
ufw default deny incoming && ufw default allow outgoing
ufw allow 80/tcp && ufw allow 443/tcp
# ⛔ MAI `ufw allow 8000`: Django si raggiunge SOLO attraverso Nginx
# (configurazione-django.md, «Sicurezza della superficie pubblica»).
ufw enable
```

*(opzionale) Limita SSH solo su Tailscale*

```bash
ufw delete allow 22/tcp || true
ufw allow in on tailscale0 to any port 22 proto tcp
ufw status verbose
```

## 3) Stack applicativo

```bash
apt install -y \
  python3-venv python3-pip python3-dev build-essential libpq-dev pkg-config \
  postgresql-client nginx redis-server git ca-certificates unzip
systemctl enable --now nginx redis-server
```

## 4) App Django

```bash
sudo -u $APP_USER bash -lc '
  mkdir -p ~/apps/zeroerp && cd ~/apps/zeroerp && \
  python3 -m venv .venv && source .venv/bin/activate && \
  pip install --upgrade pip && \
  pip install django gunicorn "psycopg[binary]" django-redis djangorestframework && \
  django-admin startproject zeroerp_backend .
'
```

## 5) Static/Media

```bash
mkdir -p /var/www/zeroerp/static /var/www/zeroerp/media
chown -R $APP_USER:$APP_USER /var/www/zeroerp
sudo -u $APP_USER bash -lc 'cd ~/apps/zeroerp && source .venv/bin/activate && python manage.py collectstatic --noinput'
```

## 6) Env sicuro (no password nel codice)

```bash
install -d -m 0750 /etc/zeroerp
cat > /etc/zeroerp/zeroerp.env <<EOF
DJANGO_SECRET_KEY=$(openssl rand -base64 48)
DJANGO_DEBUG=1
# Swagger (/api/docs/): segue DEBUG; con DEBUG=0 serve DJANGO_API_DOCS_ENABLED=1 (e il vhost aperto)
DJANGO_ALLOWED_HOSTS=${HOSTNAME},${TAIL_NAME},localhost,127.0.0.1
DB_NAME=${DB_NAME}
DB_USER=${DB_USER}
DB_PASSWORD='${DB_PASS}'
DB_HOST=${DB_HOST}
DB_PORT=${DB_PORT}
EOF
chown root:$APP_USER /etc/zeroerp/zeroerp.env && chmod 640 /etc/zeroerp/zeroerp.env
```

## 7) PostgreSQL (su VM `dbdev`) – una tantum

```sql
CREATE ROLE ${DB_USER} LOGIN PASSWORD '${DB_PASS}' NOCREATEDB NOCREATEROLE;
CREATE SCHEMA IF NOT EXISTS django AUTHORIZATION ${DB_USER};
ALTER ROLE ${DB_USER} IN DATABASE ${DB_NAME}
  SET search_path = django, public, config, anagrafiche, vendite, acquisti, dbops;
REVOKE CREATE ON SCHEMA public FROM ${DB_USER};
-- In pg_hba.conf (IP Tailscale del CT):
-- host  ${DB_NAME}  ${DB_USER}  100.x.y.z/32  scram-sha-256
```

## 7-bis) Ruoli DB — il passo che non si vede

⛔ **Il `CREATE ROLE` del §7 è il minimo per collegarsi, non il provisioning.**
I `GRANT` sul perimetro applicativo, la policy del ruolo migratore e i **ruoli
batch** (`zeroerp_batch_*`, che hanno `BYPASSRLS`) li scrive uno script dedicato,
e **Liquibase non può farlo**: quei ruoli vogliono un **superuser**, mentre le
migrazioni girano come `zeroerp`.

⚠️ **Perché sta qui e non altrove**: la procedura è documentata per intero in
[provisioning-db-roles.md](provisioning-db-roles.md) — con le verifiche dei grant
e della postura RLS — ma fino al 2026-09-11 **questo play-book non la nominava**,
e chi lo seguiva dall'alto in basso incontrava il ruolo batch solo al §15, dove è
già dato per esistente (`DB_BATCH_PASS` sta fra le variabili in cima).
*Un documento giusto, non agganciato al passo in cui serve, è invisibile quanto
uno che non c'è.*

**a) Ruolo applicativo e policy migratore — subito dopo il §7**

```bash
psql "host=${DB_HOST} port=5432 dbname=${DB_NAME} user=<ADMIN_DB_USER>" \
  -v app_role=${DB_USER} \
  -v app_password='${DB_PASS}' \
  -v migrator_role=titodb \
  -f scripts/sql/provision_db_roles.sql
```

**b) Ruolo batch della fatturazione — ⛔ DOPO le migrazioni del §11**

L'ordine non è una preferenza: lo script **concede sul perimetro**, e il
perimetro (schemi e tabelle) deve già esistere.

```bash
psql "host=${DB_HOST} port=5432 dbname=${DB_NAME} user=<ADMIN_DB_USER>" \
  -v batch_role=zeroerp_batch_fatturazione \
  -v batch_password='${DB_BATCH_PASS}' \
  -f scripts/sql/provision_db_role_batch_fatturazione.sql
```

⚠️ **Va rilanciato quando serve un privilegio in più**: una tabella nuova non
concessa fallisce **rumorosamente** (`permission denied`), che è il comportamento
voluto — ⛔ e il rimedio è aggiungere il grant *qui*, mai in un changeSet, che
nominando un ruolo inesistente fermerebbe la pipeline (`linee-guida-sql §11.6`).

> ✅ **Come so che è andata bene**: le due sezioni di verifica in
> [provisioning-db-roles.md](provisioning-db-roles.md) — «Verifica grant runtime»
> e «Verifica postura RLS».

## 8) Gunicorn (systemd)

```bash
cat > /etc/systemd/system/zeroerp-gunicorn.service <<EOF
[Unit]
Description=ZeroERP Django (Gunicorn)
After=network.target

[Service]
User=${APP_USER}
Group=${APP_USER}
WorkingDirectory=/home/${APP_USER}/apps/zeroerp
Environment="PATH=/home/${APP_USER}/apps/zeroerp/.venv/bin"
EnvironmentFile=/etc/zeroerp/zeroerp.env
ExecStart=/home/${APP_USER}/apps/zeroerp/.venv/bin/gunicorn zeroerp_backend.wsgi:application --bind 127.0.0.1:8000 --workers 3 --timeout 60
Restart=always

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload && systemctl enable --now zeroerp-gunicorn
```

## 9) Nginx (HTTPS self‑signed + redirect)

```bash
openssl req -x509 -nodes -newkey rsa:2048 -days 365 \
  -keyout /etc/ssl/private/backend-dev.key \
  -out /etc/ssl/certs/backend-dev.crt \
  -subj "/CN=${TAIL_NAME}"
# Rate limiting: zone nel contesto http (regole e motivazioni in
# configurazione-django.md, «Sicurezza della superficie pubblica»)
cat > /etc/nginx/conf.d/zeroerp-ratelimit.conf <<'EOF'
limit_req_zone $binary_remote_addr zone=zeroerp_auth:10m rate=10r/m;
limit_req_zone $binary_remote_addr zone=zeroerp_api:10m  rate=20r/s;
limit_req_status 429;
limit_req_log_level warn;
EOF
cat > /etc/nginx/sites-available/zeroerp <<'EOF'
server {
  listen 443 ssl http2;
  server_name ${TAIL_NAME} ${HOSTNAME};
  ssl_certificate     /etc/ssl/certs/backend-dev.crt;
  ssl_certificate_key /etc/ssl/private/backend-dev.key;
  location /static/ { alias /var/www/zeroerp/static/; expires 7d; }
  location /media/  { alias /var/www/zeroerp/media/;  expires off; }
  # Cintura: admin Django (non installato) e Swagger (spento fuori da DEBUG)
  # restano chiusi anche se lato Django ricomparissero. Vedi configurazione-django.md.
  location ~ ^/(admin|api/docs|api/schema)(/|$) { return 404; }
  # Autenticazione: anonima per natura, bersaglio del brute-force → zona stretta
  location ~ ^/api/v1/(admin|portale|shop)/token(/|$) {
    limit_req zone=zeroerp_auth burst=5 nodelay;
    proxy_pass http://127.0.0.1:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
  }
  location ~ ^/api/v1/auth/(password-reset-request|password-reset-confirm|attivazione)(/|$) {
    limit_req zone=zeroerp_auth burst=5 nodelay;
    proxy_pass http://127.0.0.1:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
  }
  location / {
    limit_req zone=zeroerp_api burst=100 nodelay;
    proxy_pass http://127.0.0.1:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
  }
}
server { listen 80; server_name ${TAIL_NAME} ${HOSTNAME}; return 308 https://$host$request_uri; }
EOF
ln -s /etc/nginx/sites-available/zeroerp /etc/nginx/sites-enabled/zeroerp || true
nginx -t && systemctl reload nginx
```

## 10) Sicurezza Django dietro proxy (append alla fine di settings.py)

```bash
cat >> /home/${APP_USER}/apps/zeroerp/zeroerp_backend/settings.py <<'EOF'
# --- Proxy HTTPS/Nginx + cookie sicuri ---
CSRF_TRUSTED_ORIGINS = [f"https://${TAIL_NAME}"]
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
# Static/Media best practice
STATIC_URL = "/static/"; MEDIA_URL = "/media/"
STATIC_ROOT = "/var/www/zeroerp/static"; MEDIA_ROOT  = "/var/www/zeroerp/media"
EOF
```

## 11) Migrazioni + superuser

```bash
set -a; source <(sudo cat /etc/zeroerp/zeroerp.env); set +a
sudo -u $APP_USER bash -lc 'cd ~/apps/zeroerp && source .venv/bin/activate && python manage.py migrate && python manage.py createsuperuser'
systemctl restart zeroerp-gunicorn
```

## 12) UFW finale (solo Tailscale per SSH)

```bash
ufw delete allow 22/tcp || true
ufw allow in on tailscale0 to any port 22 proto tcp
ufw status verbose
```

## 13) Check rapido

```bash
curl -kI https://${TAIL_NAME}/static/rest_framework/css/bootstrap.min.css   # 200 OK (collectstatic)
curl -kI https://${TAIL_NAME}/health                    # 200
curl -kI https://${TAIL_NAME}/admin/login/              # 404: l'admin Django non esiste (un 200 e' un'esposizione)
curl -kI https://${TAIL_NAME}/                          # 404: nessun redirect
ss -ltnp | grep :8000                                   # SOLO 127.0.0.1:8000 — Django mai esposto
ufw status | grep 8000 && echo "⛔ 8000 aperta: chiudila" # nessuna riga attesa
systemctl status zeroerp-gunicorn | sed -n '1,5p'
nginx -t
```

## 14) Snapshot Proxmox

```bash
pct snapshot $CTID baseline-$(date +%F) --description "Django ok, HTTPS, UFW, Tailscale"
```

## 15) Batch fatturazione (systemd timer — driver commesse→fattura)

Il driver `manage.py run_fatturazione_batch --modalita immediata|differita` gira **headless**
nel **canale di sistema** (RLS Path A): usa il ruolo DB `zeroerp_batch_fatturazione`
(BYPASSRLS) via l'alias `system_fatturazione`. Serve quindi un env con le **credenziali del
ruolo batch**, isolate dal resto (gunicorn/operatore non le usa).

> **NB**: niente pgAgent (riservato a manutenzione DB). L'anti-overlap è gestito dal command
> stesso (advisory-lock `registered_job`): fire concorrenti del timer sono sicuri (skip se un
> run è già in corso). Ogni run è registrato in `maintenance.job_run_log` (`origine=CRON`).

### 15.1) Env credenziali ruolo batch (overlay)

```bash
cat > /etc/zeroerp/zeroerp-batch.env <<EOF
DB_SYSTEM_FATTURAZIONE_USER=zeroerp_batch_fatturazione
DB_SYSTEM_FATTURAZIONE_PASSWORD='${DB_BATCH_PASS}'
EOF
chown root:$APP_USER /etc/zeroerp/zeroerp-batch.env && chmod 640 /etc/zeroerp/zeroerp-batch.env
```

> Senza `DB_SYSTEM_FATTURAZIONE_PASSWORD` la connessione di sistema **fallisce
> rumorosamente** (nessun fallback silente a `zeroerp_app`): è voluto.

### 15.2) Service + timer — ⭐ **versionati nel repo dal 2026-08-16**

⛔ **Gli heredoc che stavano qui sono stati rimossi**: erano l'unica sede delle
due corsie, e una procedura copiata a mano su ogni host non è un deploy
riproducibile — è il punto 7 di `analisi-emissione-fattura-ondemand.md`, ora
chiuso. Le unit sono template versionati:

| File | Corsia | Cadenza |
| --- | --- | --- |
| `backend/deploy/systemd/zeroerp-fatturazione-immediata.{service,timer}` | GIORNALIERO, si ferma a **DEFINITIVA** | `*:0/2` (ogni 2 min) |
| `backend/deploy/systemd/zeroerp-fatturazione-differita.{service,timer}` | MASSIVO, si ferma a **EMESSA** | `*-*-01 02:00` (1° del mese) |

Si installano con l'installer, come i drainer:

```bash
sudo backend/bin/install-timers.sh
```

⚠️ **L'installer le scrive ma NON le abilita**, e i due drainer sì. Non è una
dimenticanza: un drainer a coda vuota non fa nulla, il batch **emette
documenti** — accenderlo di riflesso vorrebbe dire iniziare a fatturare su un
host che nessuno ha dichiarato pronto. Lo script stampa il comando per
accenderle; vedi §15.4.

⚠️ **Modifiche alle unit si fanno sui template**, non qui e non in
`/etc/systemd/system`: l'installer è idempotente e riscrive tutto a ogni run,
quindi una modifica fatta a valle sparisce al primo re-install.

ℹ️ **Le credenziali del ruolo batch stanno in `.env.systemd`** (§15.1), lo
stesso EnvironmentFile del drainer della coda stampa che usa lo stesso ruolo —
non nei due file separati che questa sezione mostrava prima.

### 15.4) Attiva e verifica

```bash
systemctl daemon-reload
systemctl enable --now zeroerp-fatturazione-immediata.timer zeroerp-fatturazione-differita.timer
systemctl list-timers | grep fatturazione          # prossimo run
systemctl start zeroerp-fatturazione-immediata.service   # run manuale di prova
journalctl -u zeroerp-fatturazione-immediata.service -n 50 --no-pager
# Esito persistito: SELECT id, origine, ok, meta FROM maintenance.job_run_log ORDER BY id DESC LIMIT 5;
```

> Si abilitano i **`.timer`** (non i `.service`). Per un run on-demand manuale si lancia il
> `.service`. Endpoint UI on-demand restano l'alternativa interattiva (scope operatore).

---

## 16) Worker code di lavoro (systemd timer — drainer coda generica + coda stampa)

Due worker DRAINER headless della Fase C cockpit fatturazione, entrambi chiamanti sottili
di un core (`registered_job` → `maintenance.job_run_log`, `origine=CRON`):

* **`draina_coda_lavori`** — coda generica `dbops.coda_lavori`. Serve i giri di
  fatturazione **on-demand** accodati dalla UI (`POST /vendite/fatturazione/run/`, job
  `FATTURAZIONE_GIRO` `run_as=OPERATORE`). Gira sulla connessione **app** (`zeroerp_app`,
  RLS attiva con l'identità dell'operatore che ha accodato); passa al ruolo batch solo per
  job `run_as=SISTEMA` (nessuno oggi). Anti-overlap: **nessun lock** — il claim
  `FOR UPDATE SKIP LOCKED` è concorrenza-safe.
* **`draina_coda_stampa`** — coda stampa `vendite.fatture_stampa_coda` (outbox PDF). Gira
  **interamente** nel canale di sistema (ruolo `zeroerp_batch_fatturazione` BYPASSRLS:
  renderizza fatture di ogni emittente, emittente autoritativo dalla riga). Anti-overlap:
  advisory-lock `registered_job` (un solo drainer stampa alla volta).

> ✅ **Gate deploy `draina_coda_stampa` superato (2026-08-04).** I GRANT del ruolo batch
> sul path di render sono applicati — brief archiviato in
> `work-done/brief-db-grant-batch-coda-stampa.md` — e da allora **l'installer abilita
> entrambi i timer**. Se su un host il worker stampa fallisse ancora con «permesso negato»,
> il posto da guardare è il provisioning del ruolo (`scripts/sql/provision_db_role_batch_fatturazione.sql`),
> non questo gate.

Su questa macchina (dev): `User=tid`, app in `/home/tid/apps/ZeroErp/backend`, venv
`backend/.venv`, avvio via il wrapper riusabile **`bin/run-command.sh`** (carica `env.sh`
come `start-gunicorn.sh`); i segreti (incl. `DB_SYSTEM_FATTURAZIONE_*`) arrivano da
`EnvironmentFile=.../.env.systemd`. Adatta `APP_USER`/percorsi ad altri host.

### 16.0) Modo rapido (script idempotente)

Invece dei blocchi manuali §16.1/16.2, un solo comando scrive gli unit, fa
`daemon-reload` e abilita **entrambi** i timer (coda generica e coda stampa):

```bash
sudo /home/tid/apps/ZeroErp/backend/bin/install-timers.sh
```

Deriva `APP_USER`/percorsi dalla cartella app, verifica wrapper+template, è ri-eseguibile.
Dopo i GRANT del ruolo batch:  `sudo systemctl enable --now zeroerp-coda-stampa.timer`.

### 16.1) Dove vivono gli unit (fonte di verità: template versionati)

Gli unit **non si scrivono più a mano**: i template sono versionati in
[`backend/deploy/systemd/`](../../../../backend/deploy/systemd/) —
`zeroerp-coda-lavori.service|.timer` e `zeroerp-coda-stampa.service|.timer` — con
placeholder per-host `__APP_DIR__` / `__APP_USER__` / `__ONCALENDAR__` e, dal
2026-09-14, `__COMANDO__` (la riga di comando, campo `comando` di `sveglie.json`
— §17.6).
`install-timers.sh` (§16.0) li renderizza (sostituzione placeholder) e li copia in
`/etc/systemd/system`. Per cambiare un unit si **edita il template** e si ri-lancia
l'installer: le modifiche passano da PR come qualsiasi codice, e la CI
(`.github/workflows/ci-validate.yaml`, job `validate-deploy`) le valida con
`shellcheck` sugli script e **`systemd-analyze verify`** sugli unit renderizzati
(un unit malformato fa fallire la CI prima di raggiungere un host).

Cadenze default (nell'installer, override via `__ONCALENDAR__`): coda-lavori
`*:0/1` (ogni minuto; tunable a `*:0/30` per uno spinner UI più reattivo — il
polling FE ha timeout ~3 min), coda-stampa `*:0/2` (ogni 2 min, tunable, P-5:
ritardo accettabile tra «Rendi definitive» e PDF disponibile). La coda stampa
richiede `DB_SYSTEM_FATTURAZIONE_*` in `.env.systemd` (già presente su questo host);
i GRANT del ruolo batch sono applicati dal `provision_db_role_batch_fatturazione.sql`,
che la CI esegue — su un host nuovo va lanciato prima dei timer.

> Per validare i template in locale, senza root né systemctl:
> `backend/bin/install-timers.sh --render-only /tmp/units && systemd-analyze verify /tmp/units/*`.

### 16.3) Attiva e verifica

```bash
systemctl daemon-reload
systemctl enable --now zeroerp-coda-lavori.timer        # coda stampa: SOLO dopo i GRANT DB
# systemctl enable --now zeroerp-coda-stampa.timer
systemctl list-timers | grep coda                       # prossimo run
systemctl start zeroerp-coda-lavori.service             # run manuale di prova
journalctl -u zeroerp-coda-lavori.service -n 50 --no-pager
# Esito: SELECT jobname, origine, ok, message FROM maintenance.job_run_log
#        WHERE jobname LIKE 'draina_coda_%' ORDER BY id DESC LIMIT 5;
```

> Convergenza futura (Q-4): `draina_coda_stampa` aggancerà lo stesso motore
> (`QueueDrainEngine`) via un `QueueBackend` sui metodi repo esistenti — la tabella resta,
> si deduplica solo il loop; il worker/timer non cambiano.

---

## 17) Il dichiarato delle sveglie — `deploy/sveglie.json` (dal 2026-09-06)

⭐ **Che cosa si installa non sta più negli script.** L'elenco degli unit, la
cadenza di ciascuno e cosa va acceso si leggono da
[`backend/deploy/sveglie.json`](../../../../backend/deploy/sveglie.json), che è
la **sede unica** del dichiarato di deploy. Lo leggono in due:

| Chi | Cosa ne prende |
| --- | --- |
| `backend/bin/install-timers.sh` | l'`OnCalendar` **e il comando** (`__COMANDO__`, dal 2026-09-14) da sostituire nei template, e la lista di cosa abilitare |
| `apps.core.services.sveglie` (backend) | le unit di ogni processo (per la mail del guardiano del digest), la cadenza da confrontare col contratto (`test_contratto_liveness_vs_deploy`), il `comando` che «Esegui ora» lancia come sottoprocesso (§17.6) e `avvio_manuale` (§17.7). ⚠️ Fino al 2026-09-11 qui c'era «la `tolleranza_minuti`»: il contratto di liveness vive in `dbops.processi`, e il JSON **rifiuta** il campo |

⛔ **Perché è cambiato.** Prima le cadenze erano cablate in quattro chiamate
dentro l'installer, e la tolleranza di liveness degli stessi processi era un
`WORKER_ATTIVO_SOGLIA_MINUTI = 10` in `coda_lavori/gestione_service.py`. Lo
stesso fatto — *«ogni quanto ci si aspetta questo processo»* — scritto in due
posti che non si conoscevano. Due scritture prima o poi dissentono, e lì la
divergenza sarebbe stata **muta**: un pallino verde su un worker fermo.

### 17.1) I sette unit, e i tre nati quel giorno

| Unit | Processo | Forma | Cadenza default | Acceso dall'installer |
| --- | --- | --- | --- | --- |
| `zeroerp-coda-lavori` | `draina_coda_lavori` | timer | `*:0/1` | ✅ |
| `zeroerp-coda-stampa` | `draina_coda_stampa` | timer | `*:0/2` | ✅ |
| `zeroerp-fatturazione-immediata` | `run_fatturazione_batch` | timer | `*:0/2` | ⛔ emette documenti |
| `zeroerp-fatturazione-differita` | `run_fatturazione_batch` | timer | `*-*-01 02:00` | ⛔ idem |
| **`zeroerp-send-pending-emails`** | `send_pending_emails` | timer | `*:0/5` | ✅ |
| **`zeroerp-listen-cambio-reparto`** | `listen_cambio_reparto` | **servizio** | — | ✅ |

🔴 **I due in grassetto non esistevano**, e non è un dettaglio: erano processi a
catalogo in `dbops.processi`, che si registravano su `maintenance.job_run_log`
dal 2026-09-05, e che **nessun artefatto di deploy faceva partire**. Su un host
nuovo non partivano mai. `dbops.vw_processi_programmazione` li classifica
`FUORI_PORTATA` — *«il database non può saperlo»* — quindi il guasto non aveva
nessun modo di manifestarsi se non come assenza.

⚠️ **Erano tre.** Il terzo — `zeroerp-sync-auth-user-active` — è nato spento il
2026-09-06 e ritirato il **2026-09-07**: §17.3.

⭐ **Adesso lo presidia il backend**:
`apps/core/tests/services/test_sveglie.py::test_ogni_processo_del_backend_ha_una_sveglia`
fallisce se un processo che il backend dichiara di eseguire non ha un unit che
lo faccia partire. Gira in CI, senza database.

### 17.2) Due forme, e la differenza conta

* **timer** (`Type=oneshot` + `.timer`) — si abilita il **`.timer`**; per un run
  manuale si lancia il `.service`.
* **servizio** (`Type=simple` + `Restart=always`, **nessun `.timer`**) — oggi
  solo `listen_cambio_reparto`: è un listener `LISTEN/NOTIFY` sempre acceso, non
  ha una cadenza da dichiarare. Si abilita il **`.service`**.
  ⚠️ Scrive **un solo run**, quello di avvio (decisione di Tid, 2026-09-05):
  sul giornale dice *«sono partito alle ore X»*, non *«sono vivo adesso»*. Per
  questo la sua `tolleranza_minuti` è `null` — presidiarne la liveness
  sull'ultimo run direbbe «fermo» su un listener sano partito tre settimane fa.

### 17.3) ✅ `sync-auth-user-active` è stato RITIRATO (2026-09-07)

`dbops.processi` aveva **due righe per lo stesso lavoro**: `sync_auth_user_active`
(id 23, `COMMAND`) e `sync_auth_user_expired_daily` (id 11, `PGAGENT`). Il modello
ammetteva che fossero **accesi tutti e due**, cioè la disattivazione degli utenti
scaduti due volte per notte, e nulla nel database lo impediva né lo segnalava.
Per questo il timer era nato **scritto e spento**.

**Deciso dal team DB** (brief §8.5): si tiene il `PGAGENT`. Il lavoro vero
(`anagrafiche.fn_sync_auth_user_expired`) sta tutto nel database, ha il suo
wrapper di giornale, ed è l'**unica** delle due righe che il confronto a due
fonti riesca a vedere — ritirare quella visibile per tenere l'invisibile
toglierebbe presidio. La riga 23 porta `obsoleto_dal = 2026-09-07`.

**Da questo lato** sono spariti **insieme** unit, voce in `sveglie.json` e
costante `PROCESSO_SYNC_AUTH_USER_ACTIVE`: lasciarne una farebbe dissentire
`test_ogni_processo_del_backend_ha_una_sveglia` e `test_nessun_template_orfano`,
che guardano lo stesso fatto dai due versi.

⭐ **Il management command resta come attrezzo a mano, e NON registra più un
run.** La FK lo accetterebbe sotto il codice superstite, ma la LATERAL di
`dbops.vw_processi_programmazione` legge il giornale con
`processo_codice = codice OR jobname = codice` **senza filtrare `origine`**: una
corsa a mano sposterebbe avanti `giornale_ultima_corsa` e spegnerebbe il
confronto `GIRA_E_NON_REGISTRA` su quel job — cioè il rilevatore di R-12, che su
`apply_storicizza_weekly` ha lavorato indisturbato per sei mesi e mezzo.
⚠️ Il prezzo dichiarato: **un lancio manuale non lascia traccia**
(decisione di Tid, 2026-09-07).

### 17.4) Aggiungere una sveglia

1. una voce in `deploy/sveglie.json` (il **perché** delle scelte va nel template,
   qui il valore — due programmi devono poterlo leggere), **con il suo
   `comando`** (l'argv dopo `run-command.sh`, come lista di token — §17.6);
2. la coppia `deploy/systemd/<unit>.{service,timer}` — solo il `.service` se è un
   servizio sempre acceso; l'`ExecStart` è
   `__APP_DIR__/bin/run-command.sh __COMANDO__`, **mai** la riga scritta a mano;
3. `sudo backend/bin/install-timers.sh`.

⚠️ **Modifiche agli unit si fanno sui template**, mai in `/etc/systemd/system`:
l'installer è idempotente e riscrive tutto a ogni run, quindi una modifica a
valle sparisce al primo re-install.

```bash
# Validazione locale, senza root né systemctl (la stessa che gira in CI):
backend/bin/install-timers.sh --render-only /tmp/units && systemd-analyze verify /tmp/units/*
```

### 17.5) Come si prova, e le due metà

| Prova | Che cosa dice | Dove gira |
| --- | --- | --- |
| `systemd-analyze verify` sui template renderizzati | gli unit **sono validi** | CI, `validate-deploy` |
| `backend/scripts/tests/test-install-timers.sh` | si accendono **quelli giusti** | CI, `validate-deploy` |
| `apps/core/tests/services/test_sveglie.py` | ogni processo ha una sveglia, nessun template orfano | CI, suite Django |

🔴 **Fino al 2026-09-06 c'era solo la prima**, e il difetto è passato di lì:
`install-timers.sh` leggeva i campi con `IFS=$'\t'` — il TAB è IFS-whitespace,
quindi `read` collassa i delimitatori consecutivi. Su un `oncalendar` vuoto (il
caso normale di un servizio sempre acceso) `abilita` diventava il testo della
nota, e `zeroerp-listen-cambio-reparto` veniva **installato e mai avviato**. La
CI renderizzava sette unit corretti e non poteva vederlo: `--render-only` esce
**prima** del ramo che accende.

⭐ Il secondo test apre quel ramo senza inventarne uno nuovo: un `systemctl`
**finto** in testa al `PATH` (lo script lo invoca senza percorso assoluto) e
`ZEROERP_SYSTEMD_DIR` per la destinazione — con cui cade anche il requisito di
root, che serve a scrivere in `/etc/systemd/system` e non «perché è la modalità
install». ⛔ Un `--dry-run` che salta `systemctl` avrebbe provato il ramo che
**non** accende: inutile per questo bug.

```bash
# In locale, senza root e senza toccare il sistema:
bash backend/scripts/tests/test-install-timers.sh
```

⚠️ Resta scoperto il caso «`systemctl enable` fallisce»: lo stub esce sempre `0`.

### 17.6) La riga di comando sta nel JSON — `comando` e `__COMANDO__` (dal 2026-09-14)

⭐ **Perché.** «Esegui ora» dal drawer dei processi
([analisi-riavvio-processi-da-interfaccia.md §4.1-bis](../work-done/analisi-riavvio-processi-da-interfaccia.md),
brief [brief-db-avvio-manuale-di-un-processo.md](../work-done/brief-db-avvio-manuale-di-un-processo.md))
lancia **lo stesso comando del timer, meno l'orario** — e il backend non può
leggerlo da un file `.service`. Fino al 14-09 la riga viveva **solo** lì
(`ExecStart=… run-command.sh digest_presidi --cadenza settimanale`).

⇒ Ogni voce di `sveglie.json` porta `comando` (l'argv dopo `run-command.sh`,
come **lista** di token) e ogni template `.service` porta
`ExecStart=__APP_DIR__/bin/run-command.sh __COMANDO__`, che l'installer rende
come già `__ONCALENDAR__`. **Una sede sola**: la riga che il timer esegue *è*
quella che il pulsante eseguirà, e non possono divergere.

⛔ Un `comando` nel JSON *accanto* a una riga cablata nel template sarebbe la
seconda sede — quella che resta indietro, e qui «indietro» vuol dire un pulsante
che lancia una cosa diversa dal timer, **senza che nessuna delle due fallisca**.
Lo presidia `test-install-timers.sh`: test 6 (nessun template con `ExecStart`
cablato) e test 7 (l'unit reso porta esattamente l'argv del JSON).

| Regola | Perché |
| --- | --- |
| lista di token, mai una stringa | systemd spezza l'`ExecStart` sugli spazi, `subprocess` passa il token intero: «come si spezza» sarebbe una regola scritta due volte |
| whitelist stretta sui token (niente spazi, quote, `%`, `$`, `\|`, `&`) | `%x` è uno specifier systemd, `$VAR` si espande, `\|`/`&` sono del `sed` dell'installer; si allarga quando un comando **vero** ne ha bisogno |
| il primo token è un management command **che esiste** | un refuso non fallisce in CI ma sull'host, alla prima corsa (`test_sveglie.py`, test 13) |
| obbligatorio anche per `forma = servizio` | ogni `.service` ha un `ExecStart`; una regola con un'eccezione sono due regole |

⚠️ Sugli host **non cambia niente**: gli otto `ExecStart` resi sono identici a
prima, perché il campo è nato dalla riga che ogni template eseguiva. Cambia il
template, non l'unit installato — un re-install lo riscrive uguale.

⛔ `timeout_minuti` (D-B dell'analisi) **non è un campo, per decisione**
(Tid, 15-09, piano §3.2 e brief §8.5): il tetto del sottoprocesso è **unico**
e sta nell'handler (`TETTO_SOTTOPROCESSO_SECONDI = 300`, `avvio_manuale.py`),
pinnato da `test_avvio_manuale_tetto` sotto la metà della tolleranza del
drenatore e sotto la soglia del reaper. Un tetto per sveglia non avrebbe un
lettore che lo distingua: chi supera il tetto unico **non è candidato**, e
quella è la riga sotto.

### 17.7) `avvio_manuale` accanto ad `abilita` — e come si vede a video un run lanciato a mano (dal 2026-09-15)

⭐ **Due campi, due domande.** `abilita` dice se il **timer** è acceso su questa
installazione; `avvio_manuale` dice se il **pulsante** «Esegui ora» ha senso su
questa sveglia. Sono indipendenti per modello: i due giri di fatturazione sono
`abilita: false` oggi per un'altra ragione (SDI sospeso) e restano
`avvio_manuale: false` anche il giorno in cui si accendono — un giro di
fatturazione è lungo per natura e terrebbe fermo il drenatore, che mentre
aspetta il sottoprocesso non drena altro (decisione 2a di Tid, brief §8.5).
Il drenatore stesso è `false` («Esegui ora» lo esegue lui); il listener è
`false` per natura (servizio: non c'è una corsa da lanciare, e un `true` è
rifiutato). **Obbligatorio** su ogni voce, come `abilita`: con un default il
silenzio varrebbe qualcosa. L'installer **non** lo legge — non è un fatto di
systemd.

**Chi lo legge**: `avvio_manuale.motivi_esegui_ora` (il predicato «si può
lanciare a mano?»), che risponde alla capability `can_esegui_ora` nel dettaglio
del processo, al rifiuto di `POST processi/<codice>/esegui-ora/` e al
ricontrollo dell'handler nel drenatore — **una sede, tre lettori**, così il
tooltip del pulsante spento e il 4xx non possono dire due cose diverse.

**Come si vede a video un run lanciato a mano**, e dove guardare se non torna:

| Dove | Che cosa si vede |
| --- | --- |
| *Amministrazione → Processi automatici → drawer → «Sveglie»* | la riga della sveglia col pulsante **spento e il motivo** finché il lavoro è vivo («già in coda, lavoro #id»); si riaccende da sé alla riapertura, quando il lavoro è finito |
| *Strumenti → Code di lavoro* | il lavoro `ESEGUI_PROCESSO` con la chiave `esegui:<unit>`: `PENDING` → `IN_CORSO` → `FATTO` (result con `exit_code`, `durata_ms`, `coda_output`) oppure `ERRORE` terminale (`E_PROCESSO_AVVIO_FALLITO` con l'exit code, `E_PROCESSO_AVVIO_TROPPO_LUNGO` oltre i 300 s) |
| *drawer del processo ESEGUITO → «Ultime corse»* | il run del **comando**, con `origine = COMMAND` e lo **username di chi ha premuto** (`registered_job` li legge dall'ambiente del sottoprocesso: `ZEROERP_JOB_ORIGINE`, `ZEROERP_JOB_AUTH_USER_ID`) — non `CRON`, che è la corsa del timer |
| panorama `dbops.vw_processi_programmazione` | `avvio_manuale \| SU_RICHIESTA \| f`: il processo del gesto non ha una cadenza e non ha un run suo (§8.2.1 del brief: l'audit del gesto è la riga di coda) |

⚠️ **Un run a mano mentre il timer sta girando** produce una riga di *skip* nel
giornale del comando (il lock di `fn_job_run_start`), non due corse: il lavoro
esce `FATTO` con exit 0. È ciò che succede oggi a chi lancia da shell.

⛔ **Finché il tipo `ESEGUI_PROCESSO` è `attivo = false`** il verbo risponde
`E_JOB_TYPE_NON_ATTIVO` (501): è il cancello voluto (regola del binding), non
un difetto. L'accensione la chiede il BE a handler in servizio, ed è una riga
del CSV `coda_lavori_tipi` a carico del team DB (brief §10.4).
