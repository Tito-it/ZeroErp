# Guida operativa Proxmox — Stack DEV

> **Ultimo aggiornamento**: 1 novembre 2026

> 👀 **Vedi anche**    
>    
> * [Comandi utili/Run book](comandi-utili-run-book.md).


**Target**: ambiente di sviluppo con almeno tre macchine su **Proxmox VE**:

* **VM `dbdev`** (PostgreSQL 17 + Liquibase) — *già operativo*
* **LXC `backend-dev`** (Django API) — *già operativo*
* **VM/LXC `frontend-dev`** (Vue + Node.js) — *da creare*

Include: rete, firewall, Tailscale (con **Exit Node** su Proxmox), priorità di avvio, backup su NAS Synology, pratiche di sicurezza e comandi rapidi.

---

## 1) Architettura & principi

* **Proxmox VE**: 1 nodo (GUI `https://<IP>:8006`). Repo **no‑subscription** attivi e aggiornamenti regolari.
* **Rete**: LAN `192.168.X.0/24` + **Tailscale** per accesso remoto (IP 100.x). *Exit Node* disponibile sul nodo Proxmox.
* **Sicurezza**: niente servizi esposti in Internet; accesso alle macchine via Tailscale/SSH. Port knocking minimo: 22 (SSH), 8006 (GUI Proxmox); DB **solo loopback**.
* **Backup**: snapshot VZDump su **NAS Synology** (NFS). Test periodico di restore.
* **Dev tooling**: VS Code Remote‑SSH, workspace multi‑root; documentazione con MkDocs.

---

## 2) Proxmox: impostazioni base

* **Repo no‑subscription** (Debian Bookworm):

  ```bash
  echo 'deb http://download.proxmox.com/debian/pve bookworm pve-no-subscription' | sudo tee /etc/apt/sources.list.d/pve-no-subscription.list
  sudo apt update && sudo apt dist-upgrade -y
  ```
* **Firewall a 3 livelli**: Datacenter / Node / VM|CT → abilita dove serve. Regole minime:

  * SSH 22/tcp da LAN/Tailscale
  * GUI Proxmox 8006/tcp da LAN/Tailscale
  * Evitare aperture 5432 per DB; preferire tunnel SSH
* **Storage**: `local` (ISO/templates), `local-lvm` (dischi VM). Aggiunto NFS `nas-backup` (solo **Backup**).

---

## 3) Tailscale (nodo Proxmox come Exit Node)

### 3.1 Installazione su Proxmox

```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up --advertise-exit-node
```

> Approva l’**Exit Node** dall’admin console di Tailscale.

### 3.2 Uso dell’Exit Node (client)

* Sul **client** (PC/NAS) che vuoi far uscire da Proxmox:

  ```bash
  tailscale set --exit-node=100.<IP-Proxmox> --exit-node-allow-lan-access=true
  ```

  * `--exit-node-allow-lan-access=true`: continui a vedere la LAN locale
* Per **disattivare**: `tailscale set --exit-node=`

### 3.3 Linee guida pratiche

* **Non usare l’Exit Node per tutti**: abilitalo solo dove serve (es. NAS). Per sviluppo quotidiano, meglio accesso diretto Tailscale senza exit.
* **DNS**: se noti lentezze, prova a **non accettare** DNS pushati da Tailscale sul client, o imposta DNS statici.
* **Prestazioni**: l’upload del nodo Proxmox è il collo di bottiglia per il traffico dei client in Exit Node.
* **Sicurezza**: anche con Exit Node, i servizi interni restano non esposti; applica comunque le policy firewall.

---

## 4) VM `dbdev` (PostgreSQL 17 + Liquibase)

### 4.1 Configurazione DB sicura

* `postgresql.conf`:

  ```
  listen_addresses = 'localhost'
  ```
* `pg_hba.conf` *(in cima)*:

  ```
  host  all  all  127.0.0.1/32  scram-sha-256
  host  all  all  ::1/128       scram-sha-256
  # opzionale: LAN/Tailscale
  # host all all 192.168.X.0/24  scram-sha-256
  # host all all 100.0.0.0/8     scram-sha-256
  ```
* Utenti/ownership: `titodb` owner delle tabelle **Liquibase**; estensioni (`postgis`, `postgis_topology`, `dblink`) create da superuser.

### 4.2 Accesso e migrazioni

* **SSH tunnel** dal PC:

  ```bash
  ssh -L 5432:localhost:5432 tid@100.<IP-dbdev>
  # pgAdmin/liquibase: host=localhost, port=5432
  ```
* **Liquibase** (su dbdev):

  ```properties
  # db/liquibase.properties
  url=jdbc:postgresql://127.0.0.1:5432/zeroerp
  username=titodb
  password=*****
  changeLogFile=changelog/changelog-master.yaml
  ```

  Comandi: `liquibase validate | status --verbose | updateSQL | update`

### 4.3 Avvio/Shutdown & Agent

* Abilita **QEMU Guest Agent** (VM → Options) e installa in guest:

  ```bash
  sudo apt-get install -y qemu-guest-agent && sudo systemctl enable --now qemu-guest-agent
  ```
* Priorità (esempio VMID 100):

  ```bash
  qm set 100 -onboot 1 -startup order=20,up=60,down=120
  ```

---

## 5) LXC `backend-dev` (Django API)

### 5.1 Container & runtime

* LXC Debian/Ubuntu con risorse adeguate (CPU/RAM moderata, filesystem `rootfs` su `local-lvm`).
* Python 3 + `venv`, dipendenze installate nel container.
* Server applicativo: `uvicorn`/`gunicorn` (es. porta 8000 su loopback), eventualmente dietro Nginx.

### 5.2 Sicurezza & rete

* Evita di esporre porte del container verso Internet/LAN.
* Accesso via Tailscale (SSH al nodo + `pct enter <CTID>` oppure Tailscale diretto se installato nel CT).
* Firewall Proxmox livello **CT**: consenti solo ciò che serve (es. traffico interno dal reverse‑proxy se presente).

### 5.3 Service di sistema (esempio uvicorn)

```bash
sudo tee /etc/systemd/system/backend.service >/dev/null <<'UNIT'
[Unit]
Description=Django API (backend-dev)
After=network.target

[Service]
User=www-data
WorkingDirectory=/srv/backend
Environment="DJANGO_SETTINGS_MODULE=core.settings.dev"
ExecStart=/srv/backend/.venv/bin/uvicorn core.asgi:application --host 127.0.0.1 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
UNIT

sudo systemctl enable --now backend.service
```

> Esporre a rete solo tramite reverse‑proxy o Tailscale; altrimenti lascia su `127.0.0.1` e usa port‑forward/SSH.

---

## 6) `frontend-dev` (Vue) — da creare

### 6.1 Scelta VM o LXC

* **LXC**: più leggero per dev; **VM** se vuoi isolamento completo.

### 6.2 Provisioning

* Node.js LTS + pnpm/yarn:

  ```bash
  curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -
  sudo apt-get install -y nodejs
  npm install -g pnpm
  ```
* Clona repo frontend; sviluppo:

  ```bash
  pnpm install
  pnpm dev -- --host 127.0.0.1 --port 5173
  ```
* Build & hosting statico (Nginx):

  ```bash
  pnpm build
  sudo apt-get install -y nginx
  sudo rm -f /etc/nginx/sites-enabled/default
  # copia dist/ su /var/www/frontend e crea vhost 80 interno (opz. dietro reverse‑proxy)
  ```
* Accesso: via Tailscale/SSH port‑forward VS Code. Non esporre su Internet.

### 6.3 Ordine di avvio

* Dopo `dbdev` e `backend-dev`:

  ```bash
  qm set <VMID_frontend> -onboot 1 -startup order=40,up=15,down=30
  # oppure pct set <CTID_frontend> -onboot 1 -startup order=40,up=15,down=30
  ```

---

## 7) Backup Proxmox → NAS Synology (NFS)

* DSM: abilita **NFS**, crea share `proxmox-backup`, *Permessi NFS* per IP del nodo (RW, **Nessuna mappatura**; in caso di problemi: *Mappa tutti su admin*).
* Proxmox → Storage → **Add → NFS**: `nas-backup` (Content: **Backup**).
* Job: Datacenter → **Backup → Add** → Node=nodo, Storage=nas-backup, Mode=`snapshot`, Compression=`zstd`, Retention (es. *Keep last 7*).
* **Test “Run now”** + *restore di prova* su nuovo VMID.

---

## 8) Riavvio automatico & priorità

* **Ordine avvio/chiusura**:

  * `dbdev` (order 20, up 60–120)
  * `backend-dev` (order 30, up 20–30)
  * `frontend-dev` (order 40, up 10–15)
* **Timer reboot nodo** (es. lun 03:30):

  ```bash
  sudo tee /etc/systemd/system/weekly-reboot.service >/dev/null <<'UNIT'
  [Unit]
  Description=Weekly maintenance reboot
  [Service]
  Type=oneshot
  ExecStart=/usr/sbin/reboot
  UNIT
  sudo tee /etc/systemd/system/weekly-reboot.timer >/dev/null <<'UNIT'
  [Unit]
  Description=Weekly maintenance reboot timer
  [Timer]
  OnCalendar=Mon 03:30
  Persistent=true
  Unit=weekly-reboot.service
  [Install]
  WantedBy=timers.target
  UNIT
  sudo systemctl daemon-reload
  sudo systemctl enable --now weekly-reboot.timer
  ```

---

## 9) Workspace multi‑root & MkDocs

* Workspace `.code-workspace` con: `/home/tid/software/ZeroErp`, `/etc/postgresql`, `/var/log/postgresql`, `/home/tid/.ssh`.
* MkDocs in `.venv` locale al repo; task VS Code **“Docs: serve”** con port‑forward 8000.

---

## 10) Sicurezza & best practice

* **DB non esposto**: `listen_addresses='localhost'`, `pg_hba` SCRAM. Accesso via SSH tunnel/Tailscale.
* **Firewall Proxmox**: abilita per Datacenter/Node/VM|CT; regole minime e *default‑deny* dove opportuno.
* **Tailscale Exit Node**: abilitalo solo ai client che ne hanno bisogno. Mantieni “Allow LAN access” se ti serve rete locale.
* **Aggiornamenti**: regolari su Proxmox, guest OS, pacchetti Python/Node.
* **Git & CI**: lavora su branch `tito-dev`, PR verso `main`, protezione branch su GitHub.

---

## 11) Pregi della configurazione

* **Sicura per default**: nessuna porta DB esposta; accessi cifrati via SSH/Tailscale. Exit Node opzionale e puntuale.
* **Manutenibile**: backup centralizzato a livello VM, restore rapido dell’intero ambiente.
* **Scalabile**: aggiungi servizi/VM/CT mantenendo priorità d’avvio e policy comuni.
* **Dev‑friendly**: VS Code Remote, workspace multi‑root, MkDocs con un clic, Liquibase per migrazioni tracciate.
* **Flessibile**: puoi passare da LXC a VM (o viceversa) a seconda delle esigenze di isolamento.
* **Ripetibile**: comandi e ricette standard riducono errori e tempi di setup.

---

## 12) Comandi rapidi (che usiamo spesso)

```bash
# Tailscale exit node (Proxmox)
sudo tailscale up --advertise-exit-node
# client → usa exit node
sudo tailscale set --exit-node=100.<IP-Proxmox> --exit-node-allow-lan-access=true

# Priorità avvio VM/CT
qm set 100 -onboot 1 -startup order=20,up=60,down=120
pct set 101 -onboot 1 -startup order=30,up=20,down=60

# Backup storage NFS (CLI Proxmox)
pvesm add nfs nas-backup --server 192.168.X.20 --export /volume1/proxmox-backup --content backup --mkdir 1

# Liquibase su dbdev
liquibase validate
liquibase status --verbose
liquibase update

# Tunnel DB dal PC
ssh -L 5432:localhost:5432 tid@100.<IP-dbdev>
```
