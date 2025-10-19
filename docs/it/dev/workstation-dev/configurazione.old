
---

title: 🛠️ Configurazione VM `wrk1-dev` — XFCE, Doppio Schermo e VS Code remoto
category: infrastruttura
version: 1.0
license: GPL-3.0-or-later
-------------------------

# 🛠️ Configurazione VM `wrk1-dev` — XFCE, Doppio Schermo e VS Code remoto

## 📚 Scopo Principale

Configurare la VM **`wrk1-dev`** come ambiente di sviluppo grafico principale, dotato di **XFCE**, **RDP multi-utente**, e **VS Code** collegato ai server `dbdev` (PostgreSQL + Liquibase) e `backend-dev` (Django + Gunicorn + Nginx). L'obiettivo è consentire il lavoro su **due schermi** distinti, gestiti da due utenti (`tid`, `dev2`) in sessioni separate.

---

## 🔧 1. Installazione XFCE e Remote Desktop (RDP)

### Installazione ambiente grafico XFCE

```bash
sudo apt update
sudo apt install -y xfce4 xfce4-goodies xrdp
sudo systemctl enable xrdp
sudo systemctl start xrdp
```

### Imposta XFCE come sessione predefinita

```bash
echo xfce4-session > ~/.xsession
sudo sed -i 's/^test -x/#&/' /etc/xrdp/startwm.sh
echo "startxfce4" | sudo tee -a /etc/xrdp/startwm.sh
```

> 💡 **Nota:** in alcune installazioni la VM si avviava con `gnome-session`; questa configurazione forza **XFCE** come desktop predefinito, risolvendo l'errore *“Start to failed session”*.

---

## 👥 2. Gestione utenti e sessioni multiple

### Creazione del secondo utente di supporto

```bash
sudo adduser dev2
sudo usermod -aG sudo dev2
```

Entrambi gli utenti avranno una sessione XFCE indipendente:

* `tid` → sessione principale
* `dev2` → sessione secondaria (per secondo schermo o test paralleli)

### Imposta le password

```bash
sudo passwd tid
sudo passwd dev2
```

---

## 🖥️ 3. Configurazione doppio schermo XFCE

Da ogni sessione:

1. **Apri** → `Impostazioni > Display`
2. **Rileva monitor** → scegli tra:

   * `Mirror` (schermi duplicati)
   * `Extend` (schermi affiancati)
3. **Salva** la configurazione per ogni utente

> 🔧 Se necessario, forza la risoluzione:

```bash
xrandr --output Virtual-1 --mode 1920x1080
```

---

## 🔒 4. RDP e NoMachine — confronto finale

| Funzione                | RDP        | NoMachine                  |
| ----------------------- | ---------- | -------------------------- |
| Multi-utente simultaneo | ✅          | ❌ (1 sessione per utente)  |
| Supporto doppio schermo | ✅          | ✅ (ma con limite sessione) |
| Performance grafica     | ⚙️         | 🧩 Superiore su LAN        |
| Compatibilità client    | Universale | Alta                       |

> ✅ **Configurazione finale adottata:** RDP per doppio schermo (`tid` e `dev2`), NoMachine mantenuto per emergenza.

---

## 💻 5. Configurazione VS Code remoto

### Estensioni installate

* **Remote - SSH** (`ms-vscode-remote.remote-ssh`)
* **Python** (`ms-python.python`)
* **YAML** (`redhat.vscode-yaml`)
* **SQLTools** (per connessione diretta al DB se necessario)

### Connessione ai server remoti

#### ➤ `dbdev`

```bash
Host dbdev
    HostName 192.168.X.6
    User tid
    IdentityFile ~/.ssh/id_rsa
```

#### ➤ `backend-dev`

```bash
Host backend-dev
    HostName 192.168.X.8
    User tid
    IdentityFile ~/.ssh/id_rsa
```

Dopo il collegamento:

* Seleziona **Python interpreter**: `~/apps/ZeroErp/backend/.venv/bin/python`
* Imposta **Liquibase path** (in basso a sinistra → configurazione workspace)

> 📁 Multi-root workspace: `ZeroErp.code-workspace` include entrambi i progetti (`dbdev` e `backend-dev`).

---

## 🧩 6. Correzioni e note finali

* Risolto conflitto iniziale tra `gnome-session` e `xfce4-session` ✅
* Corretto errore “Start to failed session” ✅
* Abilitato doppio accesso contemporaneo tramite RDP ✅
* Configurato VS Code per connessione SSH simultanea ai due ambienti ✅
* Verificato funzionamento Tailscale e rete interna ✅

---

### 📦 Risultato finale

VM `wrk1-dev` pronta come **desktop di sviluppo grafico principale**, con:

* due sessioni RDP simultanee (`tid`, `dev2`)
* doppio schermo operativo
* VS Code connesso a `dbdev` e `backend-dev`
* supporto Liquibase e Python attivo

> 🔰 Tutte le configurazioni rispettano le **linee guida Zero ERP** per ambienti di sviluppo distribuiti.


