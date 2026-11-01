# Guida Operativa — Server “dbdev” su Proxmox con PostgreSQL

> **Ultimo aggiornamento**: 1 novembre 2026

> **Obiettivo**
> Preparare e gestire un server *dbdev* (VM) con **PostgreSQL 17** su **Proxmox VE**, accessibile in sicurezza via **Tailscale**/**SSH tunnel**, con **Liquibase** per le migrazioni e **backup Proxmox → NAS Synology**.
>
> **Contesto**
> Le istruzioni sintetizzano e normalizzano quanto fatto nelle sessioni “Proxmox parte 1–3” e successive: rete, Tailscale (exit node *solo se serve*), firewall, Postgres (SCRAM), Liquibase, VS Code remoto, MkDocs, backup su NAS.

---

## 1) Architettura & Linee Generali

* **Host**: Proxmox VE (nodo unico) con accesso web `https://<IP>:8006`.
* **Rete**: LAN `192.168.X.0/24`; opzionale **Tailscale** per accesso remoto sicuro (IP 100.x).
* **VM “dbdev”**: Debian/Ubuntu, ospita PostgreSQL 17 e tooling (Liquibase, MkDocs).
* **Accesso DB**: *solo locale* o via **SSH tunnel**; evitare esposizioni esterne (niente 5432 pubblico).
* **Backup**: **VZDump** Proxmox verso **Synology NAS** via **NFS** (storage `nas-backup`).
* **Dev tools**: VS Code Remote-SSH, workspace multi-root; documentazione con MkDocs + port-forward 8000.

---

## 2) Prerequisiti essenziali

* Proxmox aggiornato e con repository **no-subscription**.
* Accesso **SSH** funzionante su nodo e VM.
* **Tailscale** configurato (solo se richiesto accesso remoto). Evitare *Exit Node* salvo casi particolari.
* NAS Synology con **NFS abilitato** e share dedicata ai backup.

---

## 3) Proxmox: rete & sistema (linee guida)

1. **Accesso Web**: `https://IP_PROXMOX:8006` (utente `root`).
2. **Repo no-subscription**: aggiungi `pve-no-subscription` e fai `apt update && apt dist-upgrade`.
3. **Firewall Proxmox** (se usato): abilita a livello **Datacenter/Node/VM** e definisci regole minime (SSH 22, GUI 8006). Per il DB, preferire tunnel SSH → non aprire 5432.

---

## 4) NAS Synology per Backup Proxmox (NFS)

1. DSM → **Pannello di Controllo → Servizi file → NFS**: abilita NFS (NFSv3 ok; opz. NFSv4.1).
2. Crea **Cartella condivisa** `proxmox-backup` (cestino OFF).
3. **Permessi NFS** su `proxmox-backup` per l’IP del nodo Proxmox:

   * **RW**, **Squash: Nessuna mappatura** (in alternativa, *Mappa tutti su admin* se incontri “Permission denied”).
   * **Sicurezza**: `sys`; **Asincrono**: ON.
4. In **Proxmox → Datacenter → Storage → Add → NFS**:

   * **ID**: `nas-backup` · **Server**: `192.168.X.X` · **Export**: `/volume1/proxmox-backup`.
   * **Content**: **Backup** (solo) · **Nodes**: seleziona il nodo · **NFS Version**: 3 o 4.1.
5. **Job di backup**: Datacenter → **Backup → Add**

   * **Node**: il tuo nodo · **Storage**: `nas-backup` · **Selection**: VM desiderate · **Schedule**: `daily 02:00`.
   * **Mode**: `snapshot` · **Compression**: `zstd` · **Retention**: es. *Keep last 7* (o daily/weekly/monthly).
6. **Test**: *Run now* e verifica file `.vma.zst` su `nas-backup`.

---

## 5) Creazione e impostazioni VM “dbdev”

* **Installazione**: carica ISO Debian/Ubuntu → *Create VM* con risorse adeguate.
* **QEMU Guest Agent**:

  * VM → **Options** → **QEMU Guest Agent**: Enabled.
  * Dentro la VM:

    ```bash
    sudo apt-get update && sudo apt-get install -y qemu-guest-agent
    sudo systemctl enable --now qemu-guest-agent
    ```
* **Ordine di avvio/chiusura** (priorità):

  * Esempio (VMID 100):

    ```bash
    qm set 100 -onboot 1 -startup order=20,up=60,down=120
    ```
  * (*order basso = avvio prima; up = ritardo avvio; down = timeout chiusura*)

---

## 6) Tailscale & accesso remoto

* **Uso consigliato**: Tailscale **solo per il PC e il server**; **no Exit Node** di default (riduce latenza e complessità).
* **SSH tunnel per DB** (sul PC):

  ```bash
  ssh -L 5432:localhost:5432 tid@100.<IP-dbdev>
  # pgAdmin/cli: host=localhost, port=5432
  ```
* **Firewall**: non aprire 5432 su Internet. In `pg_hba.conf` consentire *solo* loopback; LAN/Tailscale opzionali.

---

## 7) PostgreSQL 17 su “dbdev”

### 7.1 Install & base

* Usa repository ufficiali (già in uso) e servizi systemd.
* Verifica porta:

  ```bash
  sudo ss -ltnp | grep 5432
  ```

### 7.2 Sicurezza & autenticazione (SCRAM)

* **`postgresql.conf`**:

  ```
  listen_addresses = 'localhost'   # consigliato, usare tunnel
  ```
* **`pg_hba.conf`** (in cima):

  ```
  host  all  all  127.0.0.1/32  scram-sha-256
  host  all  all  ::1/128       scram-sha-256
  # Opzionali, se proprio servono:
  # host all all 192.168.X.0/24  scram-sha-256
  # host all all 100.0.0.0/8     scram-sha-256
  ```
* **Password SCRAM**:

  ```bash
  sudo -u postgres psql -c "ALTER SYSTEM SET password_encryption='scram-sha-256'; SELECT pg_reload_conf();"
  sudo -u postgres psql -c "ALTER ROLE titodb WITH LOGIN PASSWORD '*****';"
  ```

### 7.3 Ruoli, estensioni, ownership

* **Ruoli applicativi** (es. `titodb`, `zeroerp_app`):

  ```bash
  sudo -u postgres psql -c "DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='zeroerp_app') THEN CREATE ROLE zeroerp_app LOGIN; END IF; END $$;"
  ```
* **Estensioni** (richiedono superuser):

  ```bash
  sudo -u postgres psql -d zeroerp -c "CREATE EXTENSION IF NOT EXISTS postgis;"
  sudo -u postgres psql -d zeroerp -c "CREATE EXTENSION IF NOT EXISTS postgis_topology;"
  sudo -u postgres psql -d zeroerp -c "CREATE EXTENSION IF NOT EXISTS dblink WITH SCHEMA public;"
  ```
* **Ownership tabelle Liquibase**:

  ```bash
  sudo -u postgres psql -d zeroerp -c "ALTER TABLE public.databasechangelog OWNER TO titodb; ALTER TABLE public.databasechangeloglock OWNER TO titodb;"
  ```

---

## 8) Liquibase — configurazione & uso

* **`db/liquibase.properties`** (su *dbdev*):

  ```properties
  url=jdbc:postgresql://127.0.0.1:5432/zeroerp
  username=titodb
  password=*****
  changeLogFile=changelog/changelog-master.yaml
  ```
* **Comandi tipici (sicuri)**:

  ```bash
  liquibase validate
  liquibase status --verbose
  liquibase updateSQL
  ```
* **Esecuzione**:

  ```bash
  liquibase update
  ```
* **Note errori comuni risolti**:

  * *password corretta ma login fallito*: mismatch **SCRAM vs md5** in `pg_hba.conf` o uso IPv6 `::1` → forza 127.0.0.1 e `scram-sha-256`.
  * *estensioni mancanti*: installate come **superuser** prima di `liquibase update`.
  * *`session_replication_role` negato*: eseguire l’UPDATE richiesto come superuser con `SET LOCAL session_replication_role = replica` entro transazione.

---

## 9) VS Code Remote & Workspace multi‑root

* **Connessione**: Remote-SSH → host `dbdev`.
* **Workspace** (file `ZeroErp-dbdev.code-workspace`):

  ```json
  {
    "folders": [
      { "path": "/home/tid/software/ZeroErp" },
      { "path": "/etc/postgresql" },
      { "path": "/var/log/postgresql" },
      { "path": "/home/tid/.ssh" }
    ],
    "settings": {
      "python.defaultInterpreterPath": "/home/tid/software/ZeroErp/.venv/bin/python",
      "python.terminal.activateEnvironment": true,
      "liquibase.java.home": "/usr/lib/jvm/java-17-openjdk-amd64"
    }
  }
  ```
* **Apertura rapida**: `code --remote ssh-remote+dbdev /home/tid/software/ZeroErp/ZeroErp-dbdev.code-workspace`.

---

## 10) Documentazione MkDocs

* **Setup**:

  ```bash
  cd ~/software/ZeroErp
  python3 -m venv .venv && source .venv/bin/activate
  pip install -r requirements.txt   # mkdocs/material inclusi qui
  mkdocs serve -a 127.0.0.1:8000    # VS Code farà port-forward
  ```
* **Task VS Code** (esempio):

  ```json
  { "label": "Docs: serve", "type": "shell", "command": "bash", "args": ["-lc", "source ${workspaceFolder}/.venv/bin/activate && mkdocs serve -a 127.0.0.1:8000" ] }
  ```

---

## 11) Avvio/riavvio automatici

* **Priorità VM/CT**: usa `Start at boot`, `Start/Shutdown order`, `Startup delay` (VM → Options) o `qm/pct set`.
* **Riavvio nodo settimanale** (systemd timer — es. lun 03:30):

  * `/etc/systemd/system/weekly-reboot.service` → `ExecStart=/usr/sbin/reboot`
  * `/etc/systemd/system/weekly-reboot.timer` → `OnCalendar=Mon 03:30`
  * `systemctl enable --now weekly-reboot.timer`

---

## 12) Hardening consigliato

* **Postgres non esposto** (solo loopback; accesso via SSH tunnel).
* **Tailscale**: niente Exit Node per il PC (salvo necessità specifiche).
* **Firewall VM**: regole minime; disattiva aperture inutili (es. 5432) se non richieste.
* **Permessi NAS**: share dedicata, retention nei job, test periodico di **restore**.

---

## 13) Errori comuni & soluzioni (dall’esperienza)

* **PgAdmin “funziona”, CLI no** → in PgAdmin usavi `postgres`, da CLI `titodb`: allinea utente o permessi.
* **Autenticazione fallita su localhost** → psql usa `::1` prima di 127.0.0.1: aggiungi regola IPv6 `::1/128` in `pg_hba.conf` con `scram-sha-256`.
* **Estensioni mancanti (postgis/dblink)** → installale *prima* come superuser; poi `liquibase update` come utente applicativo.
* **`session_replication_role` negato** → fai l’UPDATE come superuser dentro transazione con `SET LOCAL ... = replica`.
* **Storage NFS senza “Backup”** → in Proxmox “Content” deve includere **Backup** (equiv. VZDump); in dubbio, aggiungi via CLI `--content backup`.

---

## 14) Pregi della struttura

* **Sicurezza by design**: DB non esposto; accesso via **SSH tunnel**/**Tailscale**.
* **Affidabilità**: backup *a caldo* delle VM con **snapshot** e **retention** sul NAS.
* **Semplicità operativa**: un unico job Proxmox copre l’intera VM (OS, Postgres, tool, configurazioni).
* **Scalabilità**: facile aggiungere nodi/VM; ordine d’avvio garantisce dipendenze corrette.
* **Dev Experience**: VS Code Remote, workspace multi-root, MkDocs con port-forward; comandi `liquibase` pronti.
* **Governance del DB**: **Liquibase** per migrazioni tracciate e ripetibili; **SCRAM** per auth moderna.
* **Flessibilità**: Tailscale opzionale; possibile Exit Node solo per host specifici (es. NAS), non per tutti.

---

## 15) Allegato — Comandi rapidi

```bash
# Tunnel SSH (PC → dbdev)
ssh -L 5432:localhost:5432 tid@100.<IP-dbdev>

# Liquibase (dbdev)
liquibase validate
liquibase status --verbose
liquibase update

# Postgres (dbdev)
sudo -u postgres psql -c "SHOW hba_file;"
sudo -u postgres psql -d zeroerp -c "CREATE EXTENSION IF NOT EXISTS postgis;"

# Proxmox backup storage (CLI)
pvesm add nfs nas-backup --server 192.168.X.20 --export /volume1/proxmox-backup --content backup --mkdir 1

# VM order/delay
qm set 100 -onboot 1 -startup order=20,up=60,down=120
```

> **Suggerimento finale**: esegui periodicamente un **restore di prova** su un VMID nuovo per validare i backup. Una verifica reale vale più di mille log verdi. ✅
