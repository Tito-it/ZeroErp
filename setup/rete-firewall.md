# 🔒 Configurazione rete stabile – ZeroERP

> **Ultimo aggiornamento**: 1 novembre 2026

⚠️ Non modificare più firewall / modalità di connessione se non strettamente necessario.
Sistema attuale testato e funzionante.


---

## 🌐 Connessioni

* **SSH** via Tailscale (porta 22).
* **Postgres** via Tailscale (porta 5432).
* **LAN** usata solo per backup e gestione interna.
* **Visual code** SSh via tailscale  

---

## 🧱 Firewall Proxmox

* **Datacenter** → solo regole **OUT** (`vmbr0` + `tailscale0`).
* **Nodo (proxmox-node1)** → `IN 22` + `IN 8006`, `OUT` per aggiornamenti.
* **VM (dbdev)** → `IN 22` da LAN/Tailscale, `IN 5432` da LAN/Tailscale, `OUT Internet`.

---

## 🐘 PostgreSQL

* `listen_addresses = '127.0.0.1,<tailscale_ip>'`
* `pg_hba.conf` include:

  ```
  host all all 192.168.X.0/24 scram-sha-256
  host all all 100.64.0.0/10  scram-sha-256
  ```

---

✅ Configurazione stabile → non modificare senza motivo.
