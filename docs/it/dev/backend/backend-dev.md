# Backend-dev (LXC) — la macchina

> **Ultimo aggiornamento**: 26 settembre 2026
>
> **Destinatari**: chi crea, clona o mantiene il contenitore `backend-dev`.
>
> **Vedi anche**:
>
> * [Playbook operativo backend](play-book-operativo-backend.md) — la macchina da zero, solo comandi
> * [Configurazione Django su backend-dev](configurazione-django.md) — sicurezza, env, Gunicorn, Nginx, troubleshooting
> * [Provisioning ruoli DB](provisioning-db-roles.md) — `zeroerp_app`, migratore, RLS

---

Questa pagina tiene solo ciò che riguarda **il contenitore**: com'è fatto, come
si crea, come si clona e si salva. L'installazione passo per passo è nel
[Playbook](play-book-operativo-backend.md); la configurazione dell'applicazione
e le sue ragioni in [Configurazione Django](configurazione-django.md). Non si
ricopiano qui: una copia invecchia in silenzio.

## 1) Architettura in sintesi

* **Proxmox** → CT LXC `backend-dev`, Debian, non privilegiato.
* **Rete** → IP LAN + **Tailscale** (MagicDNS). SSH solo per manutenzione.
* **App** → il repository clonato in `/home/tid/apps/ZeroErp`; Django in un venv
  Python (`backend/.venv`, Python da pyenv alla versione di `.python-version`),
  servito da **Gunicorn** su loopback.
* **Frontend in sviluppo** → dev server **Vite** su loopback.
* **Reverse proxy** → **Nginx** su 80/443, unico ingresso (HTTPS self-signed in
  sviluppo, redirect 80→443).
* **Cache** → **Redis** locale.
* **DB** → **PostgreSQL** su VM `dbdev` (scram-sha-256); il backend si collega
  come `zeroerp_app`, soggetto alla RLS.

```text
Browser → Nginx :443 ─┬─ /api/, /health → Gunicorn 127.0.0.1:8000 → Django → PostgreSQL (dbdev)
                      └─ il resto       → Vite 127.0.0.1:5173
```

## 2) Creazione CT (wizard Proxmox)

* **Template**: Debian standard.
* **Hostname**: `backend-dev`.
* **CPU/RAM/Disk**: 2 vCPU / 4 GB RAM / 20–30 GB disco.
* **Features**: *unprivileged*, `keyctl=on`, `nesting` opzionale.
* **Rete**: IP statico su `vmbr0`, poi Tailscale.

> **TUN per Tailscale**: sull'**host Proxmox**, in `/etc/pve/lxc/<CTID>.conf`:

```text
lxc.cgroup2.devices.allow: c 10:200 rwm
lxc.mount.entry: /dev/net/tun dev/net/tun none bind,create=file
```

Poi `pct restart <CTID>` e si prosegue con il [Playbook](play-book-operativo-backend.md), §1.

> **DNS**: se `apt` segnala errori di risoluzione, impostare un nameserver (per
> esempio `1.1.1.1`) oppure usare `tailscale up --accept-dns=false`.

## 3) Snapshot, clone e backup

* **Snapshot Proxmox**: per il rollback della *stessa* istanza. Include identità
  Tailscale e certificato self-signed: non si usa per clonare un ambiente nuovo
  senza sanificarlo.
* **Clone** in un CT nuovo: rigenerare le **SSH host keys** e il **certificato**,
  rifare `tailscale up`, e nei file d'ambiente (`backend/env.sh` e
  `backend/.env.systemd`) cambiare `DJANGO_SECRET_KEY`, le credenziali DB,
  `DJANGO_ALLOWED_HOSTS` e `FRONTEND_URL`; nel vhost Nginx, `server_name`.
* **Backup `vzdump`**: su storage remoto impostare `tmpdir: /var/tmp`, per
  evitare errori `tar | zstd` su share instabili o piene.

## 4) Le scelte della macchina

* **DB separato dall'app**: PostgreSQL su VM dedicata; l'app usa un ruolo a
  privilegi minimi, **non owner** e **senza `BYPASSRLS`**.
* **Segreti fuori dal codice**: file d'ambiente per-host in `backend/`, non
  versionati, letti da systemd e dai wrapper di avvio.
* **Un solo ingresso**: Nginx con HTTPS da subito; Gunicorn, Vite e Redis non
  sono esposti. UFW apre solo 80/443 (e 22, eventualmente solo su Tailscale).
* **Accesso amministrativo**: Tailscale (WireGuard), login root via SSH
  disabilitato.
* **Facile da spostare**: il CT è leggero e il DB esterno evita problemi di dati
  in un redeploy o nel passaggio da CT a VM.

## 5) Checklist rapida

* [ ] CT attivo, TUN abilitato, Tailscale con MagicDNS
* [ ] UFW: deny incoming, allow outgoing; aperte solo 80, 443 (e 22)
* [ ] repository clonato, venv da `requirements.txt`
* [ ] `backend/env.sh` e `backend/.env.systemd` valorizzati, permessi 600
* [ ] ruoli DB dal provisioning ([Provisioning ruoli DB](provisioning-db-roles.md)), `pg_hba` con SCRAM sull'IP del CT
* [ ] migrazioni applicate (Liquibase, poi `manage.py migrate` come migratore)
* [ ] `zeroerp-gunicorn` attivo, in ascolto **solo** su `127.0.0.1:8000`
* [ ] Nginx 443 con il vhost di [Configurazione Django](configurazione-django.md), `default` disabilitato
* [ ] timer e worker installati (`install-timers.sh`)
* [ ] «Test di validazione» di [Configurazione Django](configurazione-django.md) tutti verdi, `check --deploy` pulito
