# 💻 Configurazione VM `wrk1-dev` (Workstation Ubuntu Desktop)

> 🔧 **Zero ERP – Infrastruttura di sviluppo**
>
> Configurazione completa della VM **Ubuntu Desktop “wrk1-dev”** ospitata sul nodo Proxmox, utilizzata come workstation di sviluppo e accesso remoto.

---

## 🎯 Scopo Principale

Fornire una **postazione desktop remota leggera e stabile** basata su **Ubuntu 24.04 LTS**, con accesso grafico tramite **NoMachine**, interconnessione **Tailscale** e integrazione diretta con l’ambiente di sviluppo Zero ERP (`backend-dev`, `dbdev`).

---

## ⚙️ Specifiche Tecniche VM

| Campo                 | Valore                                                                             |
| --------------------- | ---------------------------------------------------------------------------------- |
| **Nome VM**           | `wrk1-dev`                                                                         |
| **Sistema Operativo** | Ubuntu Server 24.04 LTS (installazione “minimized”)                                |
| **Modalità BIOS**     | OVMF (UEFI)                                                                        |
| **Machine Type**      | Q35                                                                                |
| **EFI Disk**          | attivo su `local` (no enrolled keys)                                               |
| **Display**           | SPICE (QXL)                                                                        |
| **Audio**             | Intel HDA (ICH9)                                                                   |
| **Storage**           | `local-lvm` – 80 GB (`qcow2`, cache Write-back, SSD=on, discard=on, IO thread=yes) |
| **RAM**               | 12 GB                                                                              |
| **CPU**               | 4 vCore                                                                            |
| **Network**           | Bridge `vmbr0`, DHCP → 192.168.X.50                                                |
| **Hostname interno**  | `wrk1-dev`                                                                         |
| **Accesso remoto**    | NoMachine (porta TCP 4000) + Tailscale                                             |
| **Ruolo**             | Workstation di sviluppo remota e browser ChatGPT                                   |

---

## 🧩 Software Installato

### 🪶 Base System

* Ubuntu 24.04 LTS – *server minimized*
* OpenSSH Server
* QEMU Guest Agent
* Spice VD Agent

### 🖥️ Desktop Environment – **XFCE4**

* XFCE 4 + LightDM
  → desktop leggero, stabile, con avvio automatico in `graphical.target`
* File di configurazione personalizzato per LightDM:

```ini
[Seat:*]
user-session=xfce
greeter-session=lightdm-gtk-greeter
```

Percorso: `/usr/share/lightdm/lightdm.conf.d/50-xfce.conf`

### 🔧 Associazione predefinita della sessione grafica

Durante l’installazione minimale, il sistema tende a usare `ubuntu` (GNOME) come sessione predefinita.
Per forzare XFCE come ambiente desktop:

```bash
sudo update-alternatives --config x-session-manager
```

Scegliere `startxfce4`, quindi creare il file utente:

```bash
echo "startxfce4" > ~/.xsession
chmod +x ~/.xsession
```

Questa configurazione assicura che LightDM e NoMachine avviino correttamente la sessione **XFCE**.

---

## 🌐 Browser Predefinito (Firefox)

Per impostare Firefox come browser predefinito in XFCE:

```bash
sudo apt install -y firefox
xdg-settings set default-web-browser firefox.desktop
```

Oppure tramite interfaccia grafica:

> Menu → Impostazioni → Applicazioni preferite → Internet → Firefox Web Browser

---

## 🔒 Rete e Sicurezza

| Rete            | Range            | Uso                                                 | Routing                   |
| --------------- | ---------------- | --------------------------------------------------- | ------------------------- |
| **LAN interna** | `192.168.X.0/24` | Comunicazioni tra VM (dbdev, backend-dev, wrk1-dev) | Diretto su bridge `vmbr0` |
| **Tailscale**   | `<ts-wrk>`  | Accesso remoto sicuro via Internet                  | Tunnel WireGuard          |

**Firewall:** disattivato (nessuna regola UFW).
Il controllo sicurezza è delegato al nodo Proxmox e alla rete Tailscale.

---

## 🔁 Persistenza e Automazione

### Tailscale override systemd

File: `/etc/systemd/system/tailscaled.service.d/override.conf`

```ini
[Service]
ExecStartPost=/usr/bin/tailscale up --accept-dns=false --accept-routes=false --hostname=wrk1-dev --reset
```

Comandi di attivazione:

```bash
sudo systemctl daemon-reexec
sudo systemctl daemon-reload
sudo systemctl enable --now tailscaled
sudo systemctl restart tailscaled
```

✅ Al riavvio, Tailscale riparte automaticamente con le opzioni corrette, mantenendo il traffico LAN interno escluso dal tunnel.

---

## ⚙️ Configurazione NoMachine

**Verifica stato:**

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

**Accesso da client:**

* Host: `<ts-wrk>` *(via Tailscale)*
* Porta: `4000`
* Protocollo: NX
* Utente: `tid` (o utente assegnato)
* Password: password VM

---

## 🧠 Best Practice

* 🔹 Usare **Tailscale** solo per accesso remoto → `--accept-dns=false --accept-routes=false`
* 🔹 Tra le VM usare sempre IP LAN (192.168.X.x)
* 🔹 Eseguire snapshot Proxmox “wrk1-dev-clean-base” dopo ogni configurazione stabile
* 🔹 Evitare UFW interno: la protezione è garantita da Proxmox bridge e ACL Tailscale

---

## 🧾 Riepilogo rapido comandi utili

```bash
# Stato Tailscale
tailscale status
tailscale ip -4

# Stato NoMachine
sudo /usr/NX/bin/nxserver --status

# Riavvio desktop
sudo systemctl restart lightdm

# Snapshot Proxmox consigliato
wrk1-dev-clean-base
```

---

## 🧩 Stato finale (verificato)

| Componente      | Stato         | Verifica                   |
| --------------- | ------------- | -------------------------- |
| LightDM         | ✅ running     | `systemctl status lightdm` |
| XFCE Desktop    | ✅ funzionante | Avvio automatico           |
| NoMachine       | ✅ running     | Accesso via NX 4000        |
| Tailscale       | ✅ connesso    | IP <ts-wrk>           |
| LAN 192.168.X.x | ✅ attiva      | Comunicazione diretta      |
| Firewall        | ✅ disattivo   | nessuna restrizione        |

---

## 🏁 Conclusione

La VM `wrk1-dev` è ora **completamente operativa** come workstation remota Zero ERP:

* accessibile via **NoMachine + Tailscale**,
* integrata nella **rete interna 192.168.X.0/24**,
* con **XFCE come ambiente grafico predefinito**,
* e **configurazione persistente e ottimizzata** per prestazioni e stabilità su Proxmox 9.

---

📁 *Posizione consigliata nel repository documentazione:*
`docs/it/infrastruttura/virtual-machines/workstation-dev.md`

---

✳️ **Autore:** M.C. Titini (tid)
📅 **Data configurazione:** 2025-10-15
🏷️ **Versione documento:** 1.1
🔖 **Licenza:** GPL v3 – Zero ERP Documentation
