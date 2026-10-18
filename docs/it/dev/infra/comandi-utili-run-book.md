# Runbook dettagliato – Nodo Proxmox + VM (dbdev/backend)

## Indice

1. Panoramica rapida (cheatsheet)
2. Rete & DNS end‑to‑end
3. Proxmox Firewall vs UFW (scelta e regole)
4. Unbound sul nodo (DNS locale per le VM)
5. Tailscale (nodo/VM, exit node)
6. PostgreSQL 17/main (avvio affidabile e accessi)
7. Git/GitHub da VS Code (SSH 22/443, HTTPS)
8. Checklist post‑riavvio
9. Comandi veloci (appendice)
10. Sblocco del secondo fattore (DBA)
11. Smoke bash: gli utenti di sviluppo, secondo fattore, login unico

---

## 1) Panoramica rapida (cheatsheet)

1. **Connettività IP (VM):**

   * `ping -c 4 8.8.8.8` → IP ok
2. **DNS (VM):**

   * `getent hosts github.com` → se fallisce, DNS rotto
   * `cat /etc/resolv.conf` → atteso `nameserver 192.168.X.4`
3. **Firewall:**

   * **Usa SOLO pve-firewall** sul nodo; **UFW disabilitato**.
4. **Unbound (nodo):**

   * Deve ascoltare su `0.0.0.0:53` (UDP/TCP)
5. **Tailscale:**

   * `tailscale status` (nodo/VM); opzionale **exit node**.
6. **PostgreSQL:**

   * `pg_lsclusters` / `systemctl status postgresql@17-main`
7. **Git/GitHub:**

   * Se SSH bloccato: usa **443 (`ssh.github.com`)** o **HTTPS**.

---

## 2) Rete & DNS end‑to‑end

### 2.1 VM: connettività base

```bash
ip -4 addr show
ip route
ping -c 4 192.168.X.1       # router
ping -c 4 192.168.X.4       # nodo Proxmox
ping -c 4 8.8.8.8           # internet IP
```

### 2.2 VM: risoluzione DNS

```bash
cat /etc/resolv.conf        # atteso: nameserver 192.168.X.4
grep '^hosts:' /etc/nsswitch.conf  # atteso: files dns
getent hosts google.com
```

Blocca/sblocca modifiche a `resolv.conf`:

```bash
sudo chattr +i /etc/resolv.conf     # blocca
sudo chattr -i /etc/resolv.conf     # sblocca
```

### 2.3 Nodo: Unbound è in ascolto

```bash
sudo ss -lunp | grep ':53'   # atteso: 0.0.0.0:53 (UDP)
sudo ss -ltnp | grep ':53'   # atteso: 0.0.0.0:53 (TCP)
```

Test dal nodo e da VM:

```bash
# sul nodo
dig @192.168.X.4 google.com +short

# dalla VM
echo "nameserver 192.168.X.4" | sudo tee /etc/resolv.conf
getent hosts google.com
```

Se **VM non risolve ma nodo sì** → probabile blocco su pve‑firewall **HOST**.

---

## 3) Proxmox Firewall vs UFW

### 3.1 Scelta

* **Consigliato:** usare **solo pve‑firewall** (integrato Proxmox).
* **Disabilita UFW** (evita catene concorrenti che rompono DNS delle VM):

```bash
sudo ufw disable
sudo systemctl disable --now ufw
# opzionale: sudo systemctl mask ufw
# opzionale: sudo apt-get purge -y ufw
```

### 3.2 Regole minime su **HOST** (nodo Proxmox)

GUI: *Datacenter → proxmox-node1 → Firewall → Rules*
Oppure file: `/etc/pve/nodes/proxmox-node1/host.fw`

```ini
[OPTIONS]
enable: 1

[RULES]
# DNS per le VM verso Unbound sul nodo
IN ACCEPT -i vmbr0 -source 192.168.X.0/24 -p udp -dport 53 -log nolog
IN ACCEPT -i vmbr0 -source 192.168.X.0/24 -p tcp -dport 53 -log nolog

# Gestione (LAN/Tailscale)
IN ACCEPT -i vmbr0 -source 192.168.X.0/24 -p tcp -dport 22   -log nolog
IN ACCEPT -i vmbr0 -source 192.168.X.0/24 -p tcp -dport 8006 -log nolog
IN ACCEPT -i tailscale0 -p tcp -dport 22   -log nolog
# opzionale: IN ACCEPT -i tailscale0 -p tcp -dport 8006 -log nolog

# Tailscale (servizio locale)
IN ACCEPT -p udp -dport 41641 -log nolog
```

Ricarica:

```bash
sudo pve-firewall reload
```

### 3.3 Regole minime su **VM dbdev (101)**

File: `/etc/pve/firewall/101.fw`

```ini
[OPTIONS]
enable: 1

[RULES]
# DNS verso nodo
IN ACCEPT -i net0 -source 192.168.X.0/24 -p udp -dport 53 -log nolog
IN ACCEPT -i net0 -source 192.168.X.0/24 -p tcp -dport 53 -log nolog

# SSH
IN ACCEPT -i net0 -source 192.168.X.0/24 -p tcp -dport 22 -log nolog
IN ACCEPT -i net0 -source 100.0.0.0/8   -p tcp -dport 22 -log nolog

# PostgreSQL
IN ACCEPT -i net0 -source 192.168.X.0/24 -p tcp -dport 5432 -log nolog
IN ACCEPT -i net0 -source 100.0.0.0/8   -p tcp -dport 5432 -log nolog

# Uscita libera
OUT ACCEPT -i net0 -dest 0.0.0.0/0 -log nolog
```

---

## 4) Unbound sul nodo

### 4.1 Config minimal forwarder (→ router o DNS pubblici)

File: `/etc/unbound/unbound.conf`

```ini
server:
  interface: 0.0.0.0
  access-control: 127.0.0.0/8 allow
  access-control: 192.168.X.0/24 allow
  do-tcp: yes

forward-zone:
  name: "."
  forward-addr: 192.168.X.1      # router (consigliato)
  # alternative pubbliche:
  # forward-addr: 1.1.1.1
  # forward-addr: 8.8.8.8
  # forward-addr: 9.9.9.9
```

Controllo e restart:

```bash
sudo unbound-checkconf && sudo systemctl restart unbound
sudo ss -lunp | grep ':53'
```

---

## 5) Tailscale

### 5.1 Stato

```bash
tailscale status
```

### 5.2 Nodo come Exit Node

Sul nodo:

```bash
# forwarding richiesto per exit node (persistente)
echo -e "net.ipv4.ip_forward=1\nnet.ipv6.conf.all.forwarding=1" | sudo tee /etc/sysctl.d/99-tailscale-exit.conf
sudo sysctl --system

# annuncia exit node (poi approva da Admin Console)
sudo tailscale up --reset --advertise-exit-node --ssh
```

### 5.3 VM: usare l’exit node

```bash
sudo tailscale up --reset --exit-node=<IP_TS_nodo> --exit-node-allow-lan-access
# verifica IP pubblico
curl -s ifconfig.io
```

Ripristino:

```bash
sudo tailscale up --exit-node=none
```

---

## 6) PostgreSQL 17/main

### 6.1 Stato cluster e avvio

```bash
sudo pg_lsclusters
sudo systemctl status postgresql@17-main --no-pager
```

### 6.2 Avvio affidabile (dopo rete e Tailscale)

Override systemd:

```bash
sudo mkdir -p /etc/systemd/system/postgresql@17-main.service.d
sudo tee /etc/systemd/system/postgresql@17-main.service.d/override.conf >/dev/null <<'EOF'
[Unit]
After=network-online.target tailscaled.service
Wants=network-online.target

[Service]
Restart=on-failure
RestartSec=5s
EOF

sudo systemctl daemon-reload
sudo systemctl enable postgresql@17-main
sudo systemctl restart postgresql@17-main
```

### 6.3 Listen & accessi

**Opzione A (consigliata):** `listen_addresses='*'` e limito con pg_hba + firewall

```bash
sudo sed -i "s/^#\?listen_addresses.*/listen_addresses = '*'/'" /etc/postgresql/17/main/postgresql.conf
```

`pg_hba.conf` (LAN + Tailscale):

```bash
sudo tee -a /etc/postgresql/17/main/pg_hba.conf >/dev/null <<'EOF'
# LAN 192.168.X.0/24
host    all     all     192.168.X.0/24        md5
# Tailscale 100.64.0.0/10
host    all     all     100.64.0.0/10         md5
EOF

sudo systemctl restart postgresql@17-main
```

Verifica:

```bash
sudo ss -ltnp | grep 5432
pg_isready -h 127.0.0.1 -p 5432
```

---

## 7) Git/GitHub da VS Code

### 7.1 SSH bloccato → usare 443 o HTTPS

**SSH via 443:** `~/.ssh/config`

```ssh
Host github.com
  HostName ssh.github.com
  Port 443
  User git
  IdentityFile ~/.ssh/id_ed25519
  PreferredAuthentications publickey
  ServerAliveInterval 60
  ServerAliveCountMax 5
  StrictHostKeyChecking accept-new
  UpdateHostKeys yes
```

Pre‑accetta host key:

```bash
ssh-keyscan -p 443 ssh.github.com >> ~/.ssh/known_hosts
chmod 700 ~/.ssh; chmod 600 ~/.ssh/config ~/.ssh/id_ed25519; chmod 644 ~/.ssh/id_ed25519.pub ~/.ssh/known_hosts
```

Test:

```bash
ssh -T git@github.com
```

**HTTPS alternativa:**

```bash
git remote set-url origin https://github.com/<org>/<repo>.git
git ls-remote origin
git pull
```

(usa un **Personal Access Token** come password quando richiesto)

### 7.2 Repo disallineato

```bash
git remote -v
git status -sb
git fetch origin
# allineo il ramo di lavoro (es. Tito-dev)
git pull --rebase origin Tito-dev
# se serve, reset distruttivo:
# git reset --hard origin/Tito-dev
```

---

## 8) Checklist post‑riavvio

1. **UFW disabilitato** sul nodo:

   ```bash
   sudo ufw status verbose   # Status: inactive
   ```
2. **pve-firewall attivo** e regole host caricate:

   ```bash
   pve-firewall status
   ```
3. **Unbound** in ascolto su `0.0.0.0:53`:

   ```bash
   sudo ss -lunp | grep ':53'
   ```
4. **DNS VM** punta al nodo:

   ```bash
   cat /etc/resolv.conf
   getent hosts google.com
   ```
5. **Tailscale** up (e exit node se serve):

   ```bash
   tailscale status
   ```
6. **PostgreSQL** up e listening:

   ```bash
   systemctl status postgresql@17-main --no-pager
   sudo ss -ltnp | grep 5432
   ```
7. **Git**:

   * Via SSH/443: `ssh -T git@github.com`
   * Via HTTPS: `git ls-remote origin`

---

## 9) Appendice – Comandi veloci

### Firewall Proxmox

```bash
sudo pve-firewall reload
sudo iptables -L -n -v | less
```

### DNS troubleshooting

```bash
# VM
nc -zu 192.168.X.4 53 && echo "UDP 53 reach OK" || echo "UDP 53 reach FAIL"
dig @192.168.X.4 google.com +time=2 +tries=1

# Nodo
sudo journalctl -u unbound --no-pager -n 50
```

### Tailscale

```bash
# Nodo → annuncia exit node
sudo tailscale up --reset --advertise-exit-node --ssh
# VM → usa exit node
a) sudo tailscale up --reset --exit-node=<IP_TS_nodo> --exit-node-allow-lan-access
b) sudo tailscale up --exit-node=none   # disattiva
```

### PostgreSQL

```bash
sudo pg_lsclusters
sudo systemctl status postgresql@17-main --no-pager
sudo systemctl restart postgresql@17-main
sudo -u postgres psql -c 'select version();'
```

### Git

```bash
# HTTPS
git remote set-url origin https://github.com/<org>/<repo>.git
# SSH 443 test
essh -vvv -p 443 -i ~/.ssh/id_ed25519 -o HostName=ssh.github.com git@github.com
```

---

**Nota finale**
Questo runbook è pensato per “stabilizzare” le componenti critiche (DNS, firewall, Tailscale, Postgres, Git) con passi minimi e reversibili. In caso di incidenti futuri, parti dal §1 (cheatsheet) e percorri nell’ordine: rete → DNS → firewall → servizi.

---

## 10) Sblocco del secondo fattore (DBA)

**Quando serve.** Una persona ha perso il telefono **e** i codici di recupero, e
nessun SUPER_ADMIN può disattivarle il secondo fattore dall'applicazione (drawer
operatore → «Disattiva il secondo fattore») — tipicamente perché è l'unico
SUPER_ADMIN. In ogni altro caso si usa l'applicazione.

**Chi.** Solo la sessione del **migratore** (il ruolo che esegue le migrazioni,
`zeroerp_migration`, o un superuser): il verbo la riconosce
(`dbops.fn_sessione_del_migratore`); l'applicazione non raggiunge questo ramo
(decisione D-T4, brief-db-secondo-fattore-totp).

**Come**, dal server, collegati col ruolo del migratore:

```sql
-- 1. la credenziale
SELECT id, username FROM auth_user WHERE username = '<username>';

-- 2. lo sblocco: il motivo è OBBLIGATORIO (E_TOTP_MOTIVO_OBBLIGATORIO)
SELECT script.fn_totp_disabilita_device(<id>, '<motivo: es. telefono e codici persi, richiesta del <data>>');

-- 3. la verifica: device assente, e la traccia scritta dal verbo
SELECT stato FROM script.fn_get_totp_device(<id>);          -- atteso: ASSENTE
SELECT data_insert, dettaglio
  FROM dbops.sessioni_utente
 WHERE auth_user_id = <id> AND evento = 'TOTP_DISABILITATO'
 ORDER BY data_insert DESC LIMIT 1;                           -- via SERVER, chi, motivo
```

* **Non** impostare `app.current_user_id`: la sessione agisce come migratore.
* La traccia (`dettaglio = {via: SERVER, sessione, chi_agisce, motivo}`) la
  scrive il verbo nella stessa istruzione: se non si scrive, lo sblocco si annulla.
* **Dopo**: al login successivo la persona entra con la sola password e, se ha
  l'obbligo (il SUPER_ADMIN ce l'ha sempre), la pagina «Sicurezza dell'accesso»
  le fa configurare subito un dispositivo nuovo. Le sessioni già aperte restano.
* Guida d'uso: `docs/it/guide/risorse-umane-e-accessi.md`, «Secondo fattore di
  autenticazione».

---

## 11) Smoke bash: gli utenti di sviluppo, secondo fattore, login unico

Gli smoke bash (`backend/scripts/tests/smoke-test-*.sh`) fanno il login con un
solo building block, `smoke_login` di `_smoke_auth.sh`: credenziali da
`SMOKE_USER` / `SMOKE_PASSWORD` (o primo argomento), secondo fattore da
`SMOKE_TOTP_SECRET`, e il riuso di `SMOKE_TOKEN` (§11.4).

### 11.1 Gli utenti di sviluppo e `dev.smoke`

Dal 2026-10-18 gli smoke entrano con **`dev.smoke`**, uno degli utenti di
sviluppo che crea il **provisioning di sviluppo** (prima: l'utente `smoke`,
creato a mano il 2026-10-02; prima ancora l'utente personale `tid`). Dal
2026-10-16 non c'è ripiego: senza `SMOKE_USER` lo smoke si ferma e lo dice.
Perché un utente suo e non uno personale:

* il **secondo fattore** è della credenziale: il DB accetta un codice per
  intervallo di 30 s (anti-replay), quindi il passo che usa lo smoke non lo
  può usare la persona (e viceversa);
* un codice già usato o sbagliato conta come **tentativo fallito** sul freno di
  login della credenziale: un giro di smoke andato storto frenerebbe l'accesso
  di chi lavora;
* i due fattori dell'utente stanno in `env.sh`: meglio quelli di un'utenza di
  prova che quelli di un SUPER_ADMIN personale;
* le scritture degli smoke (audit, `user_insert`, sessioni) non si confondono
  con quelle della persona.

Gli utenti e i dati di prova li decide il database (il verbo
`anagrafiche.fn_provisiona_dati_di_sviluppo`, pagina manual omonima): portano
l'**etichetta di prova**, in un'installazione `PRODUZIONE` non si creano, e la
lista Operatori li nasconde finché non si chiede di vederli.

| Utente | Che cos'è | Per provare |
| --- | --- | --- |
| `dev.smoke` | operatore SUPER_ADMIN, secondo fattore attivo, emittente attivo l'emittente di prova A (`DEVA`) | gli smoke |
| `dev.lettura` | operatore, lettura su tutte le aree, solo A | sola lettura, login senza secondo passo |
| `dev.bloccato` | come `dev.lettura`, contratti bloccati | il pannello dell'accesso bloccato |
| `dev.emittente` | operatore, tutto su tutte le aree, **solo A** | la RLS (`smoke-test-rls-emittente-operatore.sh`) |
| `dev.portale1`, `dev.portale2` | portale clienti sui clienti di prova 1 e 2 | che un cliente non veda l'altro |
| `dev.fornitore` | portale fornitori sul fornitore di prova 1 | il portale fornitori |
| `dev.multiveste` | operatore (come `dev.lettura`) e portale sul cliente di prova 3 | il token multi-veste |

Le email sono `<username>@sviluppo.invalid` (dominio riservato: nessuna email
esce davvero); i portali entrano con l'email.

### 11.2 Crearli, o rimetterli a posto

```bash
cd backend
./manage-env.sh provision_utenti_sviluppo                   # crea o riallinea
./manage-env.sh provision_utenti_sviluppo --nuove-password  # e password nuove per tutti
```

* Si può rilanciare: ritrova gli utenti dalla loro etichetta e rimette a posto
  vesti, profili (su tutte le aree che ci sono in quel momento), emittenti,
  eccezioni ed emittente attivo.
* Le **password** le genera il comando: per gli utenti appena creati, e per
  tutti con `--nuove-password`. Gli altri tengono la loro.
* Il **secondo fattore** di `dev.smoke` lo configura il comando, già
  confermato. Se è già attivo non lo tocca: la chiave buona è quella in
  `env.sh`. Per rifarlo, un amministratore lo disattiva dal drawer
  dell'operatore («Secondo fattore»), poi si rilancia il comando.
* Si ferma, dicendo perché, se l'ambiente dell'installazione non è dichiarato
  o è `PRODUZIONE`. Si ferma anche se uno username o una sigla dell'elenco
  esistono già senza etichetta (`E_RADICE_DI_PROVA_SENZA_ETICHETTA`): un
  omonimo nato a mano non si adotta.
* ⚠️ L'emittente di prova A è **vuoto** (listini, articoli, registri): gli
  smoke che contavano sui dati di `EMITEST` lo faranno vedere al primo giro.

### 11.3 Le variabili, in `backend/env.sh`

`env.sh` è fuori da git (`backend/.gitignore`) e con permessi `600`. Il comando
stampa in fondo le righe **nuove** (password e chiavi date in quella corsa), da
mettere al posto di quelle con lo stesso nome:

```bash
export SMOKE_USER='dev.smoke'
export SMOKE_PASSWORD='<stampata dal comando>'
export SMOKE_TOTP_SECRET='<stampata dal comando>'
export DEV_LETTURA_PASSWORD='<stampata dal comando>'   # e cosi' per gli altri dev.*
```

* I codici di recupero di `dev.smoke` escono una volta sola, come commento.
* Opzionali: `SMOKE_TOKEN_MARGINE` (secondi, default 180, §11.4),
  `SMOKE_PYTHON` (il python che calcola il codice, default il venv del backend).
* `smoke-test-rls-emittente-operatore.sh` vuole l'operatore ristretto:
  `SMOKE_USER=dev.emittente SMOKE_PASSWORD="$DEV_EMITTENTE_PASSWORD"` sulla riga
  di comando.

### 11.4 Il login unico di una sessione di smoke

```bash
eval "$(backend/scripts/tests/smoke-login.sh)"     # un login (e un codice TOTP)
backend/scripts/tests/smoke-test-catalogo.sh        # nessun login
backend/scripts/tests/smoke-test-vendite.sh         # nessun login
```

* `smoke-login.sh` fa il login vero e stampa solo `export SMOKE_TOKEN=...`;
  domanda della password e messaggi vanno sul terminale.
* Ogni smoke riusa `SMOKE_TOKEN` se vale ancora più di `SMOKE_TOKEN_MARGINE`
  secondi (claim `exp`), se `GET /api/v1/core/me/` lo accetta (una sessione
  revocata lo invalida prima) e se è proprio di `SMOKE_USER`. Altrimenti dice
  perché e fa il login da sé, come sempre.
* ⚠️ L'access dura **10 minuti** (`SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"]` in
  `backend/zeroerp_backend/settings.py`): col margine di default il riuso vale
  per ~7 minuti, poi ogni smoke torna al login proprio. Per ripartire si
  rilancia `smoke-login.sh`.
* Fanno **sempre** il login vero, perché provano proprio quello:
  `smoke-test-core.sh` (refresh e logout), `smoke-test-audit-logging.sh`
  (sessione LOGIN, refresh, login rifiutato), `smoke-test-jwt-audit-guc.sh`
  (refresh), `smoke-test-email-auth.sh` (risposta del login).
