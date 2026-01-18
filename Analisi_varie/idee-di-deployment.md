# 🚀 Zero ERP – Idee di Deployment

> 📌 **Obiettivo:** offrire due modelli di installazione/deployment **chiari e replicabili**:
>
> 1. **Economico / semplice**: *tutto su un unico server* con **Docker Compose**
> 2. **Massima sicurezza / scalabilità**: *tre server separati* (DB, Backend, Frontend)
>
> 🧭 **Idea guida**: i componenti restano *logicamente separati* (DB / API / Frontend), ma possono essere distribuiti in modo diverso a seconda di budget e requisiti.

---

## 🟢 Scenario 1 – Economico e semplice (Monoserver con Docker Compose)

### 🎯 Quando sceglierlo

* Piccole realtà (pochi utenti concorrenti)
* Budget limitato
* Priorità: **installazione facile** e **manutenzione minima**
* Accettabile un singolo punto di caduta (mitigato con **backup seri**)

### 🧱 Componenti (tutti sullo stesso host)

* **PostgreSQL** (con PostGIS se necessario)
* **Backend API** (Django + Gunicorn/Uvicorn)
* **Frontend** (Vue buildato e servito da Nginx)
* **Reverse proxy** (Nginx)
* *(Opzionale)* Redis (cache / code Celery)

### 🧩 Topologia (logica)

```
[Utenti] -> HTTPS -> [Nginx] -> /api -> [Backend]
                      |-> / (static) -> [Frontend build]

                [Backend] <-> [PostgreSQL]
                (opz.) [Backend] <-> [Redis]
```

### ✅ Vantaggi

* Un solo server da gestire
* Installazione “quasi one‑click”
* Aggiornamenti semplici (pull immagini + restart)
* Ripristino più diretto

### ⚠️ Svantaggi

* Se il server si ferma, si ferma tutto
* DB e app condividono risorse CPU/RAM/IO

### 🔐 Misure minime di sicurezza (consigliate)

* HTTPS obbligatorio (Nginx + certbot/traefik/caddy)
* Firewall (esporre solo 80/443)
* DB **non esposto** pubblicamente (solo network interno docker)
* Policy password/rotazione segreti (env file protetto)
* Limitazioni di risorse per container (memory/cpu)

### 🧰 “Pacchetto installazione” (proposta concreta)

* `compose.yml`
* `.env.example`
* `install.sh` (bootstrap + primo avvio)
* `backup.sh` (dump DB + config + media)
* `restore.sh` (ripristino guidato)
* `upgrade.sh` (pull + migrate + restart)

### 🔄 Flusso operativo (semi-automatico → automatico)

1. Copia `.env` e imposta: host, dominio, password DB, secret key
2. `docker compose up -d`
3. bootstrap automatico:

   * create DB + user
   * Liquibase migrations
   * creazione utente admin
   * caricamento dati minimi `config.*` (se previsti)
4. servizio pronto su HTTPS

### 🧯 Backup/Restore (fondamentale in monoserver)

**Backup giornaliero**:

* `pg_dump` o `pg_basebackup` (a seconda del target)
* export media/attachments
* export file `.env` (cifrato) + configurazioni

**Restore**:

* stop backend
* restore DB
* run migrations (se serve)
* restart servizi

### 📌 Varianti economiche utili

* Frontend servito da Nginx nello stesso compose
* Oppure frontend su CDN (quando disponibile) mantenendo monoserver per DB+API

---

## 🔵 Scenario 2 – Massima sicurezza (3 server separati)

### 🎯 Quando sceglierlo

* Requisiti di sicurezza elevati
* Utenza più ampia / più clienti / multi-tenant “vero”
* Necessità di separare responsabilità e superfici d’attacco
* Performance e scalabilità più prevedibili

### 🧱 Componenti distribuiti

**Server 1 – Database (DB)**

* PostgreSQL (+ PostGIS)
* Backup/replica
* Hardening OS

**Server 2 – Backend (APP/API)**

* Django + Gunicorn/Uvicorn
* (Opzionale) worker async (Celery)
* (Opzionale) Redis
* Accesso DB solo su rete privata

**Server 3 – Frontend (WEB)**

* Nginx static (Vue build)
* Reverse proxy verso backend
* WAF / rate limit / caching

### 🧩 Topologia (logica)

```
Internet -> [WEB: Nginx + TLS + WAF]
              |-> /       -> static frontend
              |-> /api    -> [APP: Django]
                              |
                              | private network (no public)
                              v
                           [DB: PostgreSQL]
```

### ✅ Vantaggi

* **DB isolato** (molto meno esposto)
* Surface d’attacco ridotta
* Scalabilità: puoi aumentare APP/WEB senza toccare DB
* Performance più stabili (IO DB separato)

### ⚠️ Svantaggi

* Costi maggiori (3 VM/server)
* Maggior complessità operativa (network, cert, deploy)

---

## 🔐 Sicurezza “alta” – checklist pratica

### 🌐 Reti

* DB su **rete privata**, nessuna porta DB esposta su internet
* APP può parlare con DB solo su private network
* WEB espone solo 80/443

### 🧱 Hardening

* SSH solo via VPN o IP whitelist
* Fail2ban / rate limiting
* Aggiornamenti OS e patch pipeline

### 🧾 Segreti

* Segreti non in repo
* `.env` protetti e ruotabili
* (Opzionale) vault (es. pass/ansible vault)

### 🧰 Backup e Disaster Recovery

* Backup DB: dump + WAL / basebackup (se serve RPO basso)
* Backup offsite (S3/NAS remoto)
* Procedure di restore testate

### 🔁 Disponibilità (opzionale, ma “massimo”)

* Replica PostgreSQL (hot standby)
* Load balancer per backend
* CDN per frontend

---

## 🧠 Nota progettuale importante per Zero ERP

### ✅ Frontend quasi mai richiede “server dedicato”

In molti casi, anche nello scenario “sicuro”, il frontend può essere:

* statico su WEB server
* oppure su CDN

Quindi i **3 server** sono spesso:

* **DB**
* **APP**
* **WEB (reverse proxy + static + WAF)**

---

## 📦 Standardizzazione delivery (uguale per entrambi gli scenari)

### 📁 Struttura suggerita in repo

* `deploy/compose/` → compose + env example
* `deploy/scripts/` → install/backup/restore/upgrade
* `deploy/docs/` → guida operativa installatore

### 🏷️ Principi

* Un comando per installare
* Un comando per aggiornare
* Un comando per backup
* Un comando per restore

---

## ✅ Scelta rapida (regola empirica)

* **Monoserver**: fino a quando la priorità è “andare live” e ridurre costi/DevOps
* **3 server**: quando sicurezza, performance e scalabilità diventano requisiti

---

