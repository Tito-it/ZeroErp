# Playbook operativo (SOLO COMANDI)

> **Ultimo aggiornamento**: 26 settembre 2026
>
> **Destinatari**: chi crea da zero un CT `backend-*` come `backend-dev`.
>
> Copia-incolla in sequenza: Django + Gunicorn + Nginx, Redis, PostgreSQL
> esterno, Tailscale, UFW. Sostituisci i **⚠️ segnaposto**. Il **perché** di ogni
> scelta sta in [Configurazione Django](configurazione-django.md) e in
> [Provisioning ruoli DB](provisioning-db-roles.md): qui solo i comandi.

---

## Variabili (adatta e poi esegui)

```bash
export CTID=⚠️102
export HOSTNAME=backend-dev
export TAIL_NAME=backend-dev.tailXXXX.ts.net
export APP_USER=tid
export APP_DIR=/home/$APP_USER/apps/ZeroErp        # clone del repository
export DB_NAME=zeroerp
export DB_USER=zeroerp_app                          # ruolo runtime, MAI owner né BYPASSRLS
export DB_PASS=⚠️StrongPassword
export DB_MIGRATOR=zeroerp_owner                    # owner degli oggetti: Liquibase e manage.py migrate
                                                     # (ruolo di sistema; sullo sviluppo un utente personale che ne
                                                     #  è membro e lavora come lui)
export DB_HOST=⚠️dbdev
export DB_PORT=5432
```

## 0) Host Proxmox – abilita TUN e riavvia CT

```bash
echo "lxc.cgroup2.devices.allow: c 10:200 rwm" >> /etc/pve/lxc/$CTID.conf
echo "lxc.mount.entry: /dev/net/tun dev/net/tun none bind,create=file" >> /etc/pve/lxc/$CTID.conf
pct restart $CTID
```

## 1) Base nel CT (Debian)

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
# ⛔ MAI `ufw allow 8000` né 5173: Django e Vite si raggiungono SOLO attraverso Nginx
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
  build-essential libpq-dev pkg-config libssl-dev zlib1g-dev libbz2-dev \
  libreadline-dev libsqlite3-dev libffi-dev liblzma-dev \
  postgresql-client nginx redis-server git ca-certificates unzip
systemctl enable --now nginx redis-server
```

Python si installa con **pyenv**, alla versione scritta in `.python-version` del
repository: la distribuzione non la porta. Il render PDF (WeasyPrint) vuole
anche le sue librerie di sistema: vedi la documentazione di WeasyPrint.

## 4) Codice e ambiente Python

```bash
sudo -u $APP_USER bash -lc '
  curl -fsSL https://pyenv.run | bash
  mkdir -p ~/apps && cd ~/apps && git clone git@github.com:Tito-it/ZeroErp.git
  cd ZeroErp && pyenv install -s "$(cat .python-version)"
  cd backend && "$(pyenv root)/versions/$(cat ../.python-version)/bin/python" -m venv .venv
  .venv/bin/pip install --upgrade pip && .venv/bin/pip install -r requirements.txt
'
```

Le dipendenze si prendono dal lock `backend/requirements.txt`, mai installando
pacchetti a mano. Per aggiornarle: `backend/scripts/update-venv.sh`.

## 5) Static/Media

Il percorso è quello di `STATIC_ROOT` / `MEDIA_ROOT` in `settings.py`, e il
vhost del §9 punta lo stesso.

```bash
mkdir -p /var/www/ZeroErp/static /var/www/ZeroErp/media
chown -R $APP_USER:www-data /var/www/ZeroErp
```

`collectstatic` si lancia dopo l'env (§11).

## 6) Env (no password nel codice)

Tre file per-host, **non versionati**, in `backend/`: chi legge quale, e perché
su una variabile presente in due vince `env.sh`, sta in
[Configurazione Django](configurazione-django.md), «Variabili d'ambiente».

```bash
sudo -u $APP_USER bash -lc "
cd $APP_DIR/backend
cp .env.example env.sh && chmod 600 env.sh
"
# Poi si valorizza env.sh (DJANGO_SECRET_KEY, DJANGO_FIELD_ENCRYPTION_KEYS,
# DJANGO_ALLOWED_HOSTS, DJANGO_TRUSTED_PROXY_COUNT=1,
# FRONTEND_URL=https://${TAIL_NAME}, DB_*).
# SECRET_KEY: python -c "import secrets; print(secrets.token_urlsafe(64))"
# Chiave Fernet: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# Stesso elenco SENZA `export` in .env.systemd, per systemd:
sudo -u $APP_USER bash -lc "cd $APP_DIR/backend && sed 's/^export //' env.sh > .env.systemd && chmod 600 .env.systemd"
```

⛔ Nessuno dei due file si committa: li tengono fuori `.gitignore` e gitleaks.

## 7) PostgreSQL (su VM `dbdev`) – una tantum

Il ruolo runtime lo crea lo script del §7-bis, non un `CREATE ROLE` a mano. Sul
server PostgreSQL resta solo l'accesso di rete:

```text
# pg_hba.conf — IP Tailscale del CT
host  zeroerp  zeroerp_app  100.x.y.z/32  scram-sha-256
host  zeroerp  zeroerp_log  100.x.y.z/32  scram-sha-256
```

## 7-bis) Ruoli DB — il passo che non si vede

⛔ **Liquibase non dà i privilegi a `zeroerp_app`**: li dà uno script dedicato,
da utente amministrativo. Procedura completa, verifiche e motivazioni:
[provisioning-db-roles.md](provisioning-db-roles.md).

⭐ **Su un database nuovo** i ruoli li crea `scripts/sql/provision_zeroerp.sql`
(ruoli di sistema `zeroerp_owner`, `zeroerp_job`, `zeroerp_app`), in tre fasi
attorno alle migrazioni, e il migratore è `zeroerp_owner`: l'ordine dei passi è
nella pagina qui sopra e, passo per passo, in [Installazione](/installazione).

L'ordine conta: lo script concede **sugli schemi e sulle tabelle che esistono**,
quindi si lancia **dopo** Liquibase **e dopo** `manage.py migrate` (§11), e si
rilancia quando nasce uno schema applicativo nuovo.

```bash
psql "host=${DB_HOST} port=5432 dbname=${DB_NAME} user=<ADMIN_DB_USER>" \
  -v fase=post -f scripts/sql/provision_zeroerp.sql

psql "host=${DB_HOST} port=5432 dbname=${DB_NAME} user=<ADMIN_DB_USER>" \
  -f scripts/sql/provision_dblink_log_channel.sql
```

⛔ **Nessun ruolo `BYPASSRLS`** su un host nuovo: i processi automatici girano
come `zeroerp_app` con un utente tecnico per azienda
([Processi automatici](/guide/processi-automatici-classe-e-identita)), e la
RLS li filtra come un operatore.

> ✅ **Come so che è andata bene**: la sezione «Verifiche» di
> [provisioning-db-roles.md](provisioning-db-roles.md).

## 8) Gunicorn (systemd)

L'avvio è il wrapper versionato `backend/bin/start-gunicorn.sh`, che legge
`env.sh`; systemd aggiunge `.env.systemd`.

```bash
cat > /etc/systemd/system/zeroerp-gunicorn.service <<EOF
[Unit]
Description=ZeroErp Gunicorn
After=network.target

[Service]
User=${APP_USER}
Group=www-data
WorkingDirectory=${APP_DIR}/backend
ExecStart=${APP_DIR}/backend/bin/start-gunicorn.sh
Restart=on-failure
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF
mkdir -p /etc/systemd/system/zeroerp-gunicorn.service.d
cat > /etc/systemd/system/zeroerp-gunicorn.service.d/override.conf <<EOF
[Service]
EnvironmentFile=${APP_DIR}/backend/.env.systemd
EOF
systemctl daemon-reload && systemctl enable zeroerp-gunicorn
```

Si avvia dopo le migrazioni (§11).

## 9) Nginx (HTTPS self‑signed + redirect)

Il vhost completo, commentato, è in [Configurazione Django](configurazione-django.md),
«Nginx (vhost)»: si copia da lì in `/etc/nginx/sites-available/zeroerp`,
sostituendo `server_name`. Qui certificato, zone del rate limiting e
abilitazione.

```bash
openssl req -x509 -nodes -newkey rsa:2048 -days 365 \
  -keyout /etc/ssl/private/backend-dev.key \
  -out /etc/ssl/certs/backend-dev.crt \
  -subj "/CN=${TAIL_NAME}"
cat > /etc/nginx/conf.d/zeroerp-ratelimit.conf <<'EOF'
limit_req_zone $binary_remote_addr zone=zeroerp_auth:10m rate=10r/m;
limit_req_zone $binary_remote_addr zone=zeroerp_api:10m  rate=20r/s;
limit_req_status 429;
limit_req_log_level warn;
EOF
# ⚠️ ora /etc/nginx/sites-available/zeroerp dal vhost di configurazione-django.md
ln -sf /etc/nginx/sites-available/zeroerp /etc/nginx/sites-enabled/zeroerp
rm -f /etc/nginx/sites-enabled/default    # altrimenti risponde lui agli host non elencati
nginx -t && systemctl reload nginx
```

## 10) Sicurezza Django dietro proxy

⛔ **Non si accoda niente a `settings.py`**: il file è versionato e contiene già
proxy fidati, cookie `Secure` e `CSRF_TRUSTED_ORIGINS`. Una modifica fatta sulla
macchina si perde al primo `git pull`, o peggio diverge in silenzio. Le
impostazioni e la loro verifica: [Configurazione Django](configurazione-django.md),
«Sicurezza della superficie pubblica».

## 11) Migrazioni, privilegi, superuser, avvio

L'ordine: **Liquibase** (lo applica chi ha i diritti sul DB, da `db/`, vedi
[liquibase-setup-workflow](/liquibase-setup-workflow)) → **`manage.py migrate`
come migratore** → **provisioning** (§7-bis) → superuser e avvio.

`manage.py migrate` crea le tabelle dello schema `django`, che appartengono al
migratore come il resto: si lancia con le credenziali del migratore, **non** con
quelle di `zeroerp_app`.

```bash
sudo -u $APP_USER bash -lc "
cd $APP_DIR/backend
set -a; source ./env.sh; set +a
DB_USER=${DB_MIGRATOR} DB_PASSWORD='⚠️PasswordMigratore' .venv/bin/python manage.py migrate --noinput
"
# → ora il §7-bis
sudo -u $APP_USER bash -lc "
cd $APP_DIR/backend
./manage-env.sh collectstatic --noinput
./manage-env.sh createsuperuser
"
systemctl start zeroerp-gunicorn
```

Il superuser è il primo utente con cui si entra **dal frontend**: l'admin
Django non esiste.

## 12) UFW finale (solo Tailscale per SSH)

```bash
ufw delete allow 22/tcp || true
ufw allow in on tailscale0 to any port 22 proto tcp
ufw status verbose
```

## 13) Check rapido

```bash
curl -kI https://${TAIL_NAME}/health                    # 200
curl -kI https://${TAIL_NAME}/admin/login/              # 404: l'admin Django non esiste (un 200 e' un'esposizione)
curl -kI https://${TAIL_NAME}/api/docs/                 # 404 con DJANGO_API_DOCS_ENABLED spento
ss -ltnp | grep -E ':8000|:5173'                        # SOLO 127.0.0.1 — Django e Vite mai esposti
ufw status | grep -E '8000|5173' && echo "⛔ porta aperta: chiudila" # nessuna riga attesa
systemctl status zeroerp-gunicorn | sed -n '1,5p'
nginx -t
cd ${APP_DIR}/backend && ./manage-env.sh check --deploy
```

La lista completa, con il rate limiting: [Configurazione Django](configurazione-django.md),
«Test di validazione».

## 14) Snapshot Proxmox

```bash
pct snapshot $CTID baseline-$(date +%F) --description "Django ok, HTTPS, UFW, Tailscale"
```

---

## 15) Processi automatici — timer, worker, servizi

Tutti i processi headless (fatturazione, code di lavoro e di stampa, email,
digest dei presidi, listener) girano come **`zeroerp_app`**, con l'identità
dell'utente tecnico del processo per ciascuna azienda: il batch di fatturazione
**accoda un lavoro per azienda**, il drenatore della coda stampa itera il roster
(`dbops.vw_processi_roster`). Non servono credenziali in più: `.env.systemd`
basta. Il modello: [Processi automatici](/guide/processi-automatici-classe-e-identita).

Gli unit sono **template versionati** in
[`backend/deploy/systemd/`](../../../../backend/deploy/systemd/), e cosa si
installa, con che cadenza e che comando, sta in **`backend/deploy/sveglie.json`**
(§16). Li installa uno script idempotente:

```bash
sudo ${APP_DIR}/backend/bin/install-timers.sh
```

Lo script renderizza i template (placeholder `__APP_DIR__`, `__APP_USER__`,
`__ONCALENDAR__`, `__COMANDO__`), li copia in `/etc/systemd/system`,
**spegne e toglie** le sveglie installate che `sveglie.json` non dichiara più
(§16.3-bis), fa `daemon-reload` e **accende ogni sveglia dichiarata**. Se un
processo lavora **non lo decide l'installer**: dal 2026-10-16 ogni `.service`
porta `ExecCondition=… e_dovuto <unit>`, che a ogni sveglia chiede al database
se il processo è acceso su questa installazione (`maintenance.fn_sveglia_accesa`:
la scelta a mano dal drawer dei processi, altrimenti il default del processo
per l'ambiente dell'installazione). Spento: systemd salta senza errore. Ambiente
non dichiarato: l'unit fallisce, visibile. Ogni unit
lancia `bin/run-command.sh <comando>`, che legge `env.sh` come
`start-gunicorn.sh`; systemd aggiunge `EnvironmentFile=.env.systemd`.

⚠️ **I due giri di fatturazione sono SPENTI di default** (a catalogo, in tutti e
due gli ambienti): un drenatore a coda vuota non fa nulla, il batch **emette
documenti**. Accenderlo di riflesso vorrebbe dire iniziare a fatturare su un host
che nessuno ha dichiarato pronto. Si accende dal drawer dei processi, col motivo,
quando l'installazione è pronta per SDI.

⚠️ **Le modifiche agli unit si fanno sui template**, mai in
`/etc/systemd/system`: l'installer riscrive tutto a ogni run.

Ogni corsa si registra su `maintenance.job_run_log` (`registered_job`), con un
lock anti-overlap: due fire concorrenti dello stesso timer sono sicuri (il
secondo è uno *skip*). pgAgent resta riservato alla manutenzione DB.

### 15.1) Attiva e verifica

```bash
systemctl list-timers | grep zeroerp                       # prossimi run
systemctl start zeroerp-coda-lavori.service                # run manuale di prova
journalctl -u zeroerp-coda-lavori.service -n 50 --no-pager
# Fatturazione, quando l'host è pronto:
systemctl enable --now zeroerp-fatturazione-immediata.timer zeroerp-fatturazione-differita.timer
# Esito: SELECT jobname, origine, ok, message FROM maintenance.job_run_log ORDER BY id DESC LIMIT 10;
```

Si abilitano i **`.timer`**; un run manuale si fa col `.service`. Dall'interfaccia
c'è «Esegui ora» (§16.5).

Tutti i comandi per servizio (start, stop, log, ricette): [Servizi ZeroERP — i comandi](servizi-zeroerp-comandi.md).

### 15.2) Validare i template in locale

Senza root né systemctl, la stessa prova che gira in CI (job `validate-deploy`):

```bash
backend/bin/install-timers.sh --render-only /tmp/units && systemd-analyze verify /tmp/units/*
bash backend/scripts/tests/test-install-timers.sh
```

---

## 16) Il dichiarato delle sveglie — `deploy/sveglie.json`

⭐ **Che cosa si installa non sta negli script.** L'elenco degli unit, la
cadenza, il comando e cosa va acceso si leggono da
[`backend/deploy/sveglie.json`](../../../../backend/deploy/sveglie.json), sede
unica del dichiarato di deploy. Lo leggono in due:

| Chi | Cosa ne prende |
| --- | --- |
| `backend/bin/install-timers.sh` | `oncalendar` e `comando` da sostituire nei template, e per differenza cosa ritirare dall'host (§16.3-bis) |
| `apps.core.services.sveglie` (backend) | le unit di ogni processo (per la mail del guardiano del digest), la cadenza da confrontare col contratto (`test_contratto_liveness_vs_deploy`), il `comando` che «Esegui ora» lancia (§16.4) e `avvio_manuale` (§16.5) |

⛔ La **tolleranza di liveness** non sta qui: è un contratto del processo e vive
in `dbops.processi`. Il JSON **rifiuta** il campo, perché lo stesso fatto scritto
in due posti prima o poi dissente.

### 16.1) Le sveglie

| Unit | Comando | Forma | Cadenza default | Default del processo (sviluppo / produzione) |
| --- | --- | --- | --- | --- |
| `zeroerp-coda-lavori` | `draina_coda_lavori` | timer | `*:0/1` | acceso / acceso — non si spegne |
| `zeroerp-coda-stampa` | `draina_coda_stampa` | timer | `*:0/2` | acceso / acceso |
| `zeroerp-fatturazione-immediata` | `run_fatturazione_batch --modalita immediata` | timer | `*:0/2` | spento / spento — emette documenti |
| `zeroerp-fatturazione-differita` | `run_fatturazione_batch --modalita differita` | timer | `*:00` + dovuto: il 1° dalle 00:00 aziendali | spento / spento — idem |
| `zeroerp-send-pending-emails` | `send_pending_emails` | timer | `*:0/5` | acceso / acceso — non si spegne |
| `zeroerp-digest-presidi-giornaliero` | `digest_presidi --cadenza giornaliera` | timer | `*:00` + dovuto: ogni giorno dalle 07:00 aziendali | acceso / acceso — non si spegne |
| `zeroerp-digest-presidi-settimanale` | `digest_presidi --cadenza settimanale` | timer | `*:00` + dovuto: il lunedi' dalle 07:30 aziendali | acceso / acceso — non si spegne |
| `zeroerp-listen-permessi` | `listen_permessi` | **servizio** | — | acceso / acceso — non si spegne |
| `zeroerp-smoke-notturno` | `smoke_notturno` | timer | `*:00` + dovuto: ogni giorno dalle 02:30 aziendali | acceso / **spento** — scrive dati di prova |

⭐ La colonna dei default è il catalogo (`dbops.processi`: `acceso_in_sviluppo`,
`acceso_in_produzione`, `spegnibile`), letto qui come fatto del 2026-10-16: la sede è il seed
`80_data/sql/dbops/processi.csv`. Una macchina può scavalcare il default dal drawer dei processi
(«Spegni» / «Accendi» / «Torna al default», col motivo), salvo i processi che non si spengono.

⭐ **Il giro notturno degli smoke** (`smoke_notturno`, dal 2026-10-13) è acceso in **sviluppo** e
spento in **produzione** (default del processo, dal 2026-10-16). In più vuole
`SMOKE_NOTTURNO_CONSENTITO=1` in `.env.systemd`. Senza il comando rifiuta di partire, prima di aprire la corsa: è la
difesa che tiene il giro fuori dalla produzione anche se qualcuno accende il timer. Con
regressioni la corsa chiude `ok=false` (`SMOKE_REGRESSIONI`) e il digest delle 07:00 la riporta
per 7 giorni; nel `meta` della corsa c'è la cartella con l'output dei rossi,
`backend/var/smoke-notturno/<data-ora>` (fuori da git). Non sta in `/tmp`, che è un tmpfs svuotato
a ogni riavvio: il comando la conserva quanto il digest mostra la corsa, 7 giorni, e a ogni giro
toglie le più vecchie. Il giro lanciato a mano con `scripts/smoke-baseline.sh` resta su `/tmp`.

La fonte è il JSON: questa tabella lo descrive, non lo sostituisce.

⭐ **Le sveglie calendariali** (dal 2026-10-09, brief un-solo-fuso-aziendale T-4/T-9): il timer
si sveglia ogni ora (`*:00`, nel fuso dell'host, che non conta) e il `.service` porta
`ExecCondition=… run-command.sh e_dovuto <unit>`, che esce 0 se il periodo **aziendale** è
cominciato e la corsia non ha ancora una corsa riuscita, 1 (salta, senza errore) altrimenti,
255 (unit fallita) su un guasto. Per vedere cosa ha deciso: `journalctl -u <unit>` (la riga
«dovuto dal …» / «non ancora dovuto» / «già fatto dal …»). «Esegui ora» lancia il `comando`
e non passa dall'`ExecCondition`: esegue sempre. ⚠️ Dopo l'aggiornamento serve
`sudo backend/bin/install-timers.sh` per rendere i template nuovi.

Lo presidia il backend:
`apps/core/tests/services/test_sveglie.py::test_ogni_processo_del_backend_ha_una_sveglia`
fallisce se un processo che il backend dichiara di eseguire non ha un unit che
lo faccia partire; `test_nessun_template_orfano` guarda il verso opposto.

### 16.2) Due forme, e la differenza conta

* **timer** (`Type=oneshot` + `.timer`): si abilita il **`.timer`**; per un run
  manuale si lancia il `.service`.
* **servizio** (`Type=simple` + `Restart=always`, **nessun `.timer`**): oggi
  solo `listen_permessi`, un listener `LISTEN/NOTIFY` sempre acceso sui canali
  `cambio_reparto` e `permessi_catalogo`. Si abilita il **`.service`**. Scrive
  **un solo run**, quello di avvio: sul giornale dice «sono partito alle ore
  X», non «sono vivo adesso». Per questo la sua `tolleranza_minuti` è `null`.
  ⭐ Dal 2026-10-09 **sonda la connessione** (`SELECT 1` a ogni giro del
  poll; non scrive sul giornale, il segno di vita resta la sessione): un riavvio
  della macchina del DB lasciava il socket «aperto» lato client, e il
  listener restava acceso per systemd ma sordo, segnato `MUTO` finché
  qualcuno non lo riavviava. Ora si riconnette da solo in pochi secondi
  (header di `notify_listener.py`).

ℹ️ Fino al 2026-10-05 si chiamava `zeroerp-listen-cambio-reparto` (command
`listen_cambio_reparto`). Sugli host già installati l'unità vecchia la spegne e
la toglie `install-timers.sh` al primo giro (§16.3-bis). Finché il servizio non
riparte col nome nuovo, il panorama dei processi segna `listen_permessi`
`MUTO`: la riga 46 di `dbops.processi` cerca una sessione con quel nome.

### 16.3) Aggiungere una sveglia

1. una voce in `deploy/sveglie.json`, **con il suo `comando`** (§16.4) e
   `avvio_manuale` (⛔ niente `abilita`: dal 2026-10-16 è rifiutato, l'accensione
   è del processo a catalogo, con `acceso_in_sviluppo`, `acceso_in_produzione` e
   `spegnibile` — al team DB);
2. la coppia `deploy/systemd/<unit>.{service,timer}` (solo il `.service` se è un
   servizio sempre acceso), con
   `ExecStart=__APP_DIR__/bin/run-command.sh __COMANDO__`, **mai** la riga
   scritta a mano;
3. `sudo backend/bin/install-timers.sh`.

### 16.3-bis) Togliere o rinominare una sveglia

Si toglie (o si rinomina) la voce in `deploy/sveglie.json` e il suo template in
`deploy/systemd/`, poi si lancia `sudo backend/bin/install-timers.sh`. Niente
passi a mano sull'host: l'installer cerca in `/etc/systemd/system` le
**sveglie** installate, cioè gli unit il cui `ExecStart` **comincia** con
`backend/bin/run-command.sh` di questo checkout (la firma di ogni template,
§16.4). Decide la firma, non il nome. Quelle che il dichiarato non produce più
le **spegne e toglie** (`systemctl disable --now`, poi il file), col loro
`.timer`, prima del `daemon-reload`. Si ritira anche il `.timer` rimasto a una
sveglia dichiarata, per esempio quando una voce passa da `timer` a `servizio`. Il piano le
stampa come `RITIRA`, anche in `--render-only`.

* i `.timer` si spengono prima dei `.service`, così un timer non rilancia il
  servizio che si sta spegnendo;
* se uno spegnimento fallisce, l'installer si ferma senza cancellare il file;
* ⛔ **un unit che non lancia `run-command.sh` non si tocca**: per esempio
  `zeroerp-gunicorn` (§8) o un altro unit del play-book. Gli `zeroerp-*` di
  questo tipo il piano li stampa come `ESTRANEO`, per chi legge. Una citazione
  del wrapper in un commento non conta: si guarda la sola riga `ExecStart=`. 🔴 La prima versione (2026-10-05) guardava il solo prefisso,
  e al primo giro sul dbdev ha spento e cancellato `zeroerp-gunicorn.service`:
  backend giù, ripristinato dal §8. Il test 8 ora semina proprio quel caso;
* ⚠️ una sveglia creata a mano sull'host (wrapper `run-command.sh`) fuori da
  `sveglie.json`, al giro successivo viene ritirata. Una sveglia si dichiara;
* ℹ️ cosa fa il processo sul catalogo DB (`dbops.processi`: riga ritirata con
  `obsoleto_dal`) è un'altra metà, del team DB.

| Prova | Che cosa dice | Dove gira |
| --- | --- | --- |
| `systemd-analyze verify` sui template renderizzati | gli unit **sono validi** | CI, `validate-deploy` |
| `backend/scripts/tests/test-install-timers.sh` | si accendono **quelli giusti**; nessun template con `ExecStart` cablato; l'unit reso porta esattamente l'argv del JSON; una sveglia non più dichiarata si spegne e si toglie, `zeroerp-gunicorn` e il resto no (test 8) | CI, `validate-deploy` |
| `apps/core/tests/services/test_sveglie.py` | ogni processo ha una sveglia, nessun template orfano, il comando esiste | CI, suite Django |

⚠️ `test-install-timers.sh` usa un `systemctl` finto che esce sempre `0`: il
caso «`systemctl enable` fallisce» resta scoperto.

### 16.4) La riga di comando sta nel JSON — `comando` e `__COMANDO__`

«Esegui ora» lancia **lo stesso comando del timer, meno l'orario**, e il
backend non può leggerlo da un file `.service`. Quindi ogni voce di
`sveglie.json` porta `comando` e ogni template porta
`ExecStart=__APP_DIR__/bin/run-command.sh __COMANDO__`: la riga che il timer
esegue *è* quella che il pulsante esegue, e non possono divergere.

| Regola | Perché |
| --- | --- |
| lista di token, mai una stringa | systemd spezza l'`ExecStart` sugli spazi, `subprocess` passa il token intero: «come si spezza» sarebbe una regola scritta due volte |
| whitelist stretta sui token (niente spazi, quote, `%`, `$`, `\|`, `&`) | `%x` è uno specifier systemd, `$VAR` si espande, `\|`/`&` sono del `sed` dell'installer; si allarga quando un comando **vero** ne ha bisogno |
| il primo token è un management command **che esiste** | un refuso non fallirebbe in CI ma sull'host, alla prima corsa (`test_sveglie.py`) |
| obbligatorio anche per `forma = servizio` | ogni `.service` ha un `ExecStart`; una regola con un'eccezione sono due regole |

Il tetto del sottoprocesso di «Esegui ora» è **unico** e sta nell'handler
(`TETTO_SOTTOPROCESSO_SECONDI = 300`, `avvio_manuale.py`), non per sveglia:
`timeout_minuti` non è un campo, per decisione.

### 16.5) `avvio_manuale` accanto all'accensione — «Esegui ora»

**Due fatti, due domande.** L'accensione (database, dal 2026-10-16) dice se il
**processo** è acceso su questa installazione; `avvio_manuale` dice se il
**pulsante** «Esegui ora» ha senso su questa sveglia. Sono indipendenti, e il
pulsante li vuole tutti e due: su un processo spento «Esegui ora» è rifiutato
(P-2 del brief-db-processi-accensione-per-ambiente), prima lo si riaccende.
Indipendenti vuol dire: i giri di fatturazione restano
`avvio_manuale: false` anche il giorno in cui si accendono, perché un giro è
lungo per natura e terrebbe fermo il drenatore che aspetta il sottoprocesso.
Il drenatore della coda lavori è `false` («Esegui ora» lo esegue lui), il
listener è `false` per natura (un `true` è rifiutato). **Obbligatorio** su ogni
voce. L'installer non lo legge.

**Chi lo legge**: `avvio_manuale.motivi_esegui_ora`, che risponde alla
capability `can_esegui_ora` nel dettaglio del processo, al rifiuto di
`POST processi/<codice>/esegui-ora/` e al ricontrollo dell'handler nel
drenatore: una sede, tre lettori.

**Come si vede un run lanciato a mano:**

| Dove | Che cosa si vede |
| --- | --- |
| *Amministrazione → Processi automatici → drawer → «Sveglie»* | il pulsante **spento, con il motivo**, finché il lavoro è vivo («già in coda, lavoro #id») |
| *Strumenti → Code di lavoro* | il lavoro `ESEGUI_PROCESSO` con chiave `esegui:<unit>`: `PENDING` → `IN_CORSO` → `FATTO` (con `exit_code`, `durata_ms`, `coda_output`) oppure `ERRORE` (`E_PROCESSO_AVVIO_FALLITO`, `E_PROCESSO_AVVIO_TROPPO_LUNGO` oltre i 300 s) |
| *drawer del processo → «Ultime corse»* | il run del comando con `origine = COMMAND` e lo **username di chi ha premuto** (`registered_job` li legge da `ZEROERP_JOB_ORIGINE`, `ZEROERP_JOB_AUTH_USER_ID`), non `CRON` |
| `dbops.vw_processi_programmazione` | `avvio_manuale \| SU_RICHIESTA`: il gesto non ha una cadenza e non ha un run suo; l'audit è la riga di coda |

⚠️ Un run a mano mentre il timer sta girando produce una riga di *skip* nel
giornale del comando, non due corse: il lavoro esce `FATTO` con exit 0.
