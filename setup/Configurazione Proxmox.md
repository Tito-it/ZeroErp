# Proxmox – Nodo, Template e VM **DBDEV** (PostgreSQL)

> **Ultimo aggiornamento**: 1 novembre 2026

> **Obiettivo**: documentare lo stato attuale dell’infrastruttura Proxmox, il ruolo del nodo, il template di base **100–db01**, la VM **101–dbdev** con PostgreSQL, le regole firewall, e le linee guida per clonare le prossime VM (backend Django, frontend Vue).

---

## 1) Panoramica

* **Nodo Proxmox**: `proxmox-node1` (LAN `192.168.X.4`, Tailscale attivo).
* **Bridge**: `vmbr0` collegato alla LAN `192.168.X.0/24`.
* **VM Template**: `100 – db01` (base Debian, guest agent, aggiornamenti).
* **VM attiva**: `101 – dbdev` (LAN `192.168.X.6`, Tailscale `<ts-dbdev>`) con **PostgreSQL 17**.
* **Accessi**: amministrazione via **Tailscale** (preferita) o LAN.

---

## 2) Ruolo del nodo Proxmox (`proxmox-node1`)

* Esegue l’hypervisor **Proxmox VE** e **ospita tutte le VM** (compute, RAM, storage locale o remoto).
* Espone **bridge di rete** (`vmbr0`) verso la LAN per le VM.
* Ha **Tailscale** per l’accesso remoto sicuro all’host e alla Web UI (porta 8006).
* **Firewall PVE** a tre livelli (Datacenter / Node / VM) per segmentare traffico e ridurre la superficie di attacco.
* Gestisce **backup programmati** delle VM (nota: a seguito di riavvii/reload, il firewall PVE applica le policy di default → vedi sezione firewall per le regole OUT necessarie).

---

## 3) Topologia rete

* **LAN**: `192.168.X.0/24`

  * Nodo Proxmox: `192.168.X.4` (`vmbr0`)
  * VM dbdev: `192.168.X.6`
* **Tailscale** (WireGuard E2E):

  * Nodo Proxmox: `<ts-proxmox>`
  * VM dbdev: `<ts-dbdev>`
* **Risoluzione nomi**: consigliato MagicDNS Tailscale o entry in `hosts` sui client.

---

## 4) Template VM **100 – db01** (base)

* OS: **Debian stable** minimal.
* **qemu-guest-agent** installato e abilitato (per shutdown, IP reporting, ecc.).
* Aggiornamenti di sicurezza applicati.
* Utente amministrativo configurato (SSH, sudo).
* **Scopo**: base “pulita” per generare nuove VM con ruolo applicativo (DB, backend, frontend).

> Le prossime VM (backend Django, frontend Vue) verranno **clonate** da questo template e poi personalizzate (pacchetti, firewall, servizi).

---

## 5) VM **101 – dbdev** (PostgreSQL)

**Origine**: clone del template `100–db01`.

### Software installato

* **PostgreSQL 17** (cluster `17-main`).
* **Tailscale** (`tailscaled` abilitato all’avvio).
* Locale di sistema **it\_IT.UTF-8** generata.

### Configurazione PostgreSQL

* File: `/etc/postgresql/17/main/postgresql.conf`

  * `listen_addresses = '127.0.0.1,<ts-dbdev>'`
    *(ascolto solo su loopback + IP Tailscale della VM)*
  * (consigliato) `password_encryption = scram-sha-256`
  * `lc_messages|lc_monetary|lc_numeric|lc_time = 'it_IT.UTF-8'`
* File: `/etc/postgresql/17/main/pg_hba.conf`

  ```
  # loopback
  host  all  all  127.0.0.1/32      scram-sha-256
  # Tailscale tailnet
  host  all  all  100.64.0.0/10     scram-sha-256
  # LAN (se necessario)
  host  all  all  192.168.X.0/24    scram-sha-256
  ```
* **Riavvio**: `sudo systemctl restart postgresql@17-main`

### Verifiche

```bash
# dalla VM
ess -ltnp | grep 5432
sudo -u postgres psql -c "select version(), current_setting('lc_messages');"
# da un client Tailscale
psql "host=<ts-dbdev> port=5432 dbname=<DB> user=<USER> sslmode=prefer"
```

---

## 6) Firewall Proxmox – Regole **definitive**

> Razionalizzazione: **Datacenter = solo OUT generali**, **Node = accesso host**, **VM = accesso servizi della VM**.

### Datacenter (`/etc/pve/firewall/datacenter.fw`)

```text
[OPTIONS]
log_level: nolog

enable: 1

[RULES]
# Permetti traffico in uscita per tutte le VM/host via LAN & Tailscale
OUT ACCEPT -i vmbr0   -d 0.0.0.0/0 -p all -log nolog  # Allow VM outbound via LAN
OUT ACCEPT -i tailscale0 -d 0.0.0.0/0 -p all -log nolog  # Allow outbound via Tailscale
```

### Nodo `proxmox-node1` (`/etc/pve/firewall/<node>.fw`)

```text
[OPTIONS]
log_level: nolog
enable: 1

[RULES]
# Accesso amministrativo all’host
IN  ACCEPT -i vmbr0     -s 192.168.X.0/24 -p tcp -dport 22   -log nolog  # SSH LAN
IN  ACCEPT -i tailscale0 -s 100.64.0.0/10 -p tcp -dport 22   -log nolog  # SSH Tailscale
IN  ACCEPT -i vmbr0     -s 192.168.X.0/24 -p tcp -dport 8006 -log nolog  # Proxmox Web UI
# Uscite host
OUT ACCEPT -p all -log nolog
```

### VM `101 – dbdev` (`/etc/pve/firewall/101.fw`)

```text
[OPTIONS]
log_level: nolog
enable: 1

[RULES]
# Uscite necessarie (DNS, apt, Tailscale handshake)
OUT ACCEPT -i net0 -d 0.0.0.0/0 -p all -log nolog  # Allow Internet

# Ingressi consentiti
IN  ACCEPT -i net0 -s 192.168.X.0/24 -p tcp -dport 22   -log nolog  # SSH da LAN
IN  ACCEPT -i net0 -s 100.0.0.0/8   -p tcp -dport 22   -log nolog  # SSH da Tailscale (match lato bridge)
IN  ACCEPT -i net0 -s 192.168.X.0/24 -p tcp -dport 5432 -log nolog  # Postgres da LAN
IN  ACCEPT -i net0 -s 100.0.0.0/8   -p tcp -dport 5432 -log nolog  # Postgres via Tailscale
```

> Nota: le regole Tailscale a livello VM matchano comunque sul traffico che arriva al bridge; il controllo di interfaccia nativa `tailscale0` si gestisce a livello **Datacenter/Node**.

### Ricarico firewall

```bash
sudo pve-firewall restart
sudo pve-firewall status  # atteso: enabled/running
```

---

## 7) Procedure operative

**SSH**

* Tailscale: `ssh tid@<tailscale-ip>`
* LAN: `ssh tid@192.168.X.6`

**pgAdmin**

* Host: `<ts-dbdev>` (Tailscale) o `dbdev` se MagicDNS
* Port: `5432` – **SSH Tunnel: OFF** – Auth SCRAM

**Tailscale** (VM)

```bash
sudo systemctl enable --now tailscaled
sudo tailscale status
sudo tailscale up
```

---

## 8) Troubleshooting rapido

* **Tailscale offline / DNS KO**:

  * Verifica uscita: `ping 8.8.8.8` (se fallisce → firewall/bridge).
  * Se ICMP ok ma DNS KO: assicurati regole **OUT** presenti a Datacenter e VM.
* **pgAdmin non si collega**:

  * VM: `ss -ltnp | grep 5432` (deve mostrare `127.0.0.1` e `<ts-dbdev>`).
  * `pg_hba.conf` con `100.64.0.0/10` e `192.168.X.0/24` (SCRAM).
* **SSH LAN KO ma ping OK**:

  * Verifica regola VM `IN 22` da `192.168.X.0/24` e stato `pve-firewall`.
* **Dopo riavvio/backup si blocca l’uscita**:

  * Controlla che a **Datacenter** esistano le due regole **OUT** (`vmbr0` + `tailscale0`).

---

## 9) Roadmap – VM future

* **Backend** (Django): clone dal template `100–db01` → installa Python/Poetry, app Django, gunicorn, Tailscale, regole VM: `IN 22`, `IN 8000/8080` (se debug) o `IN 443` dietro reverse proxy.
* **Frontend** (Vue): clone dal template `100–db01` → Node.js, build tooling; pubblicazione su web server o container; Tailscale per accesso admin.

> Tutte le nuove VM erediteranno le policy firewall: **OUT consentito**, **IN minimo indispensabile** (22 + porte applicative mirate) e accesso preferenziale via **Tailscale**.

---

## 10) Note finali

* Evitare modifiche “creative” a firewall/rete finché non necessarie.
* Documentare ogni variazione in questo file e nel repository (changelog).
* In caso di problemi urgenti di rete: verificare per primo **pve-firewall** (Datacenter OUT), poi servizi nella VM.
