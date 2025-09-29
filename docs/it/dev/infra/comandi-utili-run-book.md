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
