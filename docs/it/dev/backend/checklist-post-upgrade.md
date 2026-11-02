# 💻 Zero ERP – VM wrk1-dev – Configurazione Desktop di Sviluppo e Accesso Remoto

> **Ultimo aggiornamento**: 2 novembre 2026

> 🔧 **Scopo principale**
> La VM **wrk1-dev** funge da postazione di sviluppo grafico principale per l'ambiente Zero ERP.
> È progettata per fornire un ambiente **leggero, stabile e multi-utente**, capace di gestire sessioni XFCE indipendenti, connessioni RDP simultanee, doppio schermo e integrazione diretta con i server `dbdev` e `backend-dev` tramite **VS Code remoto**.
> In aggiunta, offre accesso alternativo tramite **NoMachine** e connessione sicura con **Tailscale**, per garantire produttività anche in contesti remoti o multi-sede.

---

## 🧰 Specifiche Tecniche VM

Questa sezione descrive la configurazione base della macchina virtuale, utile come riferimento per manutenzione o replica dell'ambiente.

| Campo                 | Valore                                                    |
| --------------------- | --------------------------------------------------------- |
| **Nome VM**           | wrk1-dev                                                  |
| **Sistema Operativo** | Debian 13 (XFCE) / Ubuntu 24.04 LTS (minimized)           |
| **Machine Type**      | Q35, BIOS UEFI (OVMF)                                     |
| **Storage**           | local-lvm – 80 GB SSD (qcow2, discard=on, IO thread=yes)  |
| **RAM**               | 12 GB                                                     |
| **CPU**               | 4 vCore                                                   |
| **Network**           | Bridge vmbr0, DHCP → 192.168.X.50                         |
| **Hostname interno**  | wrk1-dev                                                  |
| **Ruolo**             | Workstation di sviluppo grafico e accesso remoto Zero ERP |

> 💡 *Nota:* questa configurazione bilancia prestazioni e leggerezza. È pensata per lavorare fluidamente anche su nodi Proxmox con risorse moderate.

---

## 🖥️ 1. Ambiente Grafico XFCE e Accesso Remoto

### Installazione XFCE e RDP

XFCE è un ambiente desktop leggero e affidabile, ideale per VM headless o server remoti.
Il protocollo RDP consente a più utenti di collegarsi contemporaneamente alla stessa macchina, ciascuno con la propria sessione.

```bash
sudo apt update
sudo apt install -y xfce4 xfce4-goodies xrdp
sudo systemctl enable xrdp
sudo systemctl start xrdp
```

### Imposta XFCE come sessione predefinita

Per evitare conflitti con GNOME o altri desktop manager, forziamo XFCE come ambiente di default.

```bash
echo xfce4-session > ~/.xsession
sudo sed -i 's/^test -x/#&/' /etc/xrdp/startwm.sh
echo "startxfce4" | sudo tee -a /etc/xrdp/startwm.sh
```

> 💡 In alcune installazioni il sistema predefiniva gnome-session.
> Questi comandi risolvono l’errore *“Start to failed session”* e assicurano il corretto avvio di XFCE.

### Multi-utente (RDP)

Per permettere accesso contemporaneo a più utenti (es. sviluppatore principale e assistente di test):

```bash
sudo adduser dev2
sudo usermod -aG sudo dev2
sudo passwd tid
sudo passwd dev2
```

Ogni utente avrà la propria sessione isolata:

* tid → sessione principale di sviluppo
* dev2 → sessione di test o secondo schermo

### Doppio schermo

La VM può gestire due monitor virtuali o fisici tramite configurazione XFCE.

1. Aprire **Impostazioni > Display**
2. Configurare *Mirror* (duplicato) o *Extend* (affiancati)
3. Salvare la configurazione per ciascun utente

Per forzare una risoluzione specifica:

```bash
xrandr --output Virtual-1 --mode 1920x1080
```

> 🧩 *Suggerimento:* in ambienti Proxmox, assicurarsi che la console video sia impostata su SPICE/QXL per un migliore supporto multi-monitor.

---

## 🔒 2. Accesso Remoto – RDP vs NoMachine

RDP e NoMachine sono due soluzioni complementari: RDP è preferito per le sessioni multiple, NoMachine per la qualità grafica.

| Funzione                | RDP        | NoMachine                 |
| ----------------------- | ---------- | ------------------------- |
| Multi-utente simultaneo | ✅          | ❌ (1 sessione per utente) |
| Supporto doppio schermo | ✅          | ✅ (ma sessione singola)   |
| Performance grafica     | ⚙️         | 🧩 Superiore su LAN       |
| Compatibilità client    | Universale | Alta                      |

> ✅ **Configurazione adottata:** RDP come metodo principale (per doppio schermo e multi-utenza), NoMachine mantenuto come alternativa per accesso diretto o test grafici.

---

## ⚙️ 3. Configurazione NoMachine

NoMachine offre una connessione grafica fluida, utile soprattutto per lavori grafici o presentazioni remote.

Verifica stato del servizio:

```bash
sudo /usr/NX/bin/nxserver --status
```

Output atteso:

```
NX> 111 New connections to NoMachine server are enabled.
NX> 161 Enabled service: nxserver.
NX> 161 Enabled service: nxnode.
NX> 161 Enabled service: nxd.
```

Accesso client consigliato:

* Host: <ts-wrk> *(via Tailscale)*
* Porta: 4000
* Protocollo: NX
* Utente: tid

---

## 🌐 4. Rete e Sicurezza

Questa sezione documenta la configurazione di rete e i meccanismi di sicurezza usati per mantenere stabile l’ambiente.

| Rete            | Range          | Uso                                                 | Routing                 |
| --------------- | -------------- | --------------------------------------------------- | ----------------------- |
| **LAN interna** | 192.168.X.0/24 | Comunicazioni tra VM (dbdev, backend-dev, wrk1-dev) | Diretto su bridge vmbr0 |
| **Tailscale**   | <ts-wrk>  | Accesso remoto sicuro via Internet                  | Tunnel WireGuard        |

**Firewall:** disattivato nella VM; sicurezza gestita da Proxmox e ACL Tailscale.
**Servizi principali:** xrdp, nxserver, tailscaled.

Configurazione persistente Tailscale (`/etc/systemd/system/tailscaled.service.d/override.conf`):

```ini
[Service]
ExecStartPost=/usr/bin/tailscale up --accept-dns=false --accept-routes=false --hostname=wrk1-dev --reset
```

> 🔐 *Scopo:* impedire che Tailscale modifichi DNS e routing interno, mantenendo LAN e tunnel indipendenti.

---

## 💻 5. Configurazione VS Code Remoto

VS Code viene utilizzato per lo sviluppo simultaneo su `dbdev` e `backend-dev`, sfruttando SSH remoto e ambienti virtuali Python dedicati.

### Estensioni consigliate

* Remote - SSH (ms-vscode-remote.remote-ssh)
* Python (ms-python.python)
* YAML (redhat.vscode-yaml)
* SQLTools (per connessioni dirette opzionali)

### Configurazione SSH (~/.ssh/config)

#### ➤ dbdev

```bash
Host dbdev
    HostName 192.168.X.6
    User tid
    IdentityFile ~/.ssh/id_rsa
```

#### ➤ backend-dev

```bash
Host backend-dev
    HostName 192.168.X.8
    User tid
    IdentityFile ~/.ssh/id_rsa
```

Dopo il collegamento:

* Selezionare **Python interpreter**: `~/apps/ZeroErp/backend/.venv/bin/python`
* Impostare **Liquibase path** nel workspace
* Utilizzare workspace multi-root `ZeroErp.code-workspace` per gestire entrambi gli ambienti.

> 💡 *Obiettivo:* mantenere sincronizzato il lavoro tra frontend (VS Code) e backend Django, con controllo diretto sul database e sugli script Liquibase.

---

## 🧠 6. Manutenzione e Best Practice

Per garantire la stabilità del sistema, si raccomanda di:

* Aggiornare periodicamente pacchetti e ambienti XFCE / NoMachine
* Eseguire snapshot Proxmox dopo modifiche o aggiornamenti
* Usare Tailscale solo per accesso remoto (`--accept-dns=false --accept-routes=false`)
* Mantenere comunicazioni interne su IP LAN (`192.168.X.x`)

Pulizia post-upgrade per liberare spazio e log vecchi:

```bash
sudo apt autoremove --purge
sudo apt clean
sudo journalctl --vacuum-time=10d
```

Backup configurazioni principali:

```bash
tar -czf /root/wrk1dev-configs-$(date +%F).tar.gz \
  /etc/xrdp /etc/lightdm /etc/systemd/system/tailscaled.service.d \
  /home/tid/.ssh/config /etc/hosts
```

---

## 🧩 Stato finale verificato

| Componente     | Stato          | Verifica              |
| -------------- | -------------- | --------------------- |
| XFCE Desktop   | ✅ funzionante  | Avvio automatico      |
| RDP            | ✅ multi-utente | systemctl status xrdp |
| NoMachine      | ✅ running      | nxserver --status     |
| Tailscale      | ✅ connesso     | tailscale status      |
| VS Code remoto | ✅ operativo    | SSH multiplo          |

---

## 🏁 Conclusione

La VM **wrk1-dev** è ora completamente operativa come workstation di sviluppo grafico principale per Zero ERP.
Offre un ambiente stabile, multi-utente e facilmente manutenibile, con:

* doppio accesso RDP (tid, dev2)
* doppio schermo configurabile
* accesso alternativo via NoMachine + Tailscale
* VS Code remoto integrato con dbdev e backend-dev

> 📘 Tutti i passaggi sono progettati per ridurre il tempo di setup e garantire coerenza con le linee guida Zero ERP per ambienti di sviluppo distribuiti.

📁 *Posizione consigliata:* `docs/it/infrastruttura/virtual-machines/workstation-dev.md`
✳️ **Autore:** M.C. Titini (tid)
📅 **Data configurazione:** 2025-10-15
🔖 **Licenza:** AGPL v3 – Zero ERP Documentation
