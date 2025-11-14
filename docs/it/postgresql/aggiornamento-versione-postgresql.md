# 📘 Manuale Aggiornamento PostgreSQL 

> **ZeroERP — Linee guida tecniche**
> Aggiornamento del cluster PostgreSQL in ambiente di sviluppo o produzione.
> Questo è un esempio eseguito per passare dalla 17 a 18.
> 
---

## 🎯 Scopo del Documento

Questo manuale descrive la procedura **ufficiale, sicura e ripetibile** per aggiornare PostgreSQL da una versione maggiore alla successiva, utilizzando l'approccio Debian/Ubuntu basato su:

* pacchetti *postgresql-X*
* strumenti nativi *pg_upgradecluster*
* separazione totale tra cluster vecchio e nuovo

L’esempio riportato si riferisce all’upgrade **da PostgreSQL 17 → PostgreSQL 18**, ma la procedura è valida per qualsiasi upgrade maggiore (es. 16 → 17, 18 → 19, ...).

---

## 🧩 Concetti Chiave

### 🔹 Installazione multi-versione

Su Debian/Ubuntu è possibile installare **più versioni di PostgreSQL in parallelo**, senza conflitti. Ogni versione crea un proprio *cluster*:

```
/var/lib/postgresql/17/main
/var/lib/postgresql/18/main
```

### 🔹 Non si aggiorna "in-place"

PostgreSQL **non aggiorna** i dati all’interno dello stesso cluster. L’upgrade crea un cluster nuovo e migra:

* dati
* configurazioni
* estensioni (incluse PostGIS)
* utenti e privilegi

### 🔹 Strumento ufficiale: `pg_upgradecluster`

È il tool raccomandato da Debian/Ubuntu per aggiornamenti maggiori.

---

## 🧭 Prerequisiti

* Backup completo della VM o snapshot Proxmox
* Nessun servizio in esecuzione che utilizzi il database (fermare applicazioni backend)
* Account sudo sulla macchina che ospita PostgreSQL

---

## 🛠️ Step 1 — Aggiornare il Sistema Operativo

Assicurati che il sistema sia aggiornato:

```bash
sudo apt update
sudo apt full-upgrade -y
```

Questo passaggio installerà automaticamente:

* PostgreSQL 18
* PostGIS compatibile (se presente)
* librerie `postgresql-common` aggiornate

---

## 🧪 Step 2 — Verificare i Cluster Installati

Dopo l’aggiornamento:

```bash
pg_lsclusters
```

Esempio (solo cluster 17 presente):

```
17  main    5432 online ...
```

Se manca il cluster 18, il pacchetto lo crea da solo. In caso contrario:

```bash
sudo pg_createcluster 18 main
```

---

## 🧱 Step 3 — Allineamento Estensioni (PostGIS, pgtap, ecc.)

Se il cluster 17 utilizza estensioni aggiuntive, assicurati che siano presenti anche per la versione 18.

Esempio (pgtap mancante):

```bash
sudo apt install postgresql-18-pgtap
```

Se non necessario:

```bash
sudo apt remove postgresql-17-pgtap
```

---

## 🚚 Step 4 — Eseguire l’Upgrade del Cluster

Comando principale:

```bash
sudo pg_upgradecluster 17 main
```

Cosa fa:

* crea `/var/lib/postgresql/18/main`
* copia configurazioni dal 17
* migra dati, indici e estensioni
* sposta il cluster 18 su porta 5432
* spegne il cluster 17 (porta diversa, es. 5433)

---

## 🔍 Step 5 — Verifica Post-Upgrade

Controllo dei cluster:

```bash
pg_lsclusters
```

Output atteso:

```
17  main    5433 down   ...
18  main    5432 online ...
```

Verifica versione DB:

```bash
psql -U postgres -c "SHOW server_version;"
```

Se presente PostGIS:

```sql
SELECT postgis_full_version();
```

---

## 🧹 Step 6 — Pulizia del Cluster Precedente (Opzionale)

Solo dopo aver verificato tutto:

```bash
sudo pg_dropcluster 17 main
```

Rimuove definitivamente il cluster vecchio.

---

## 🔧 Step 7 — Riavvio dei Servizi Applicativi

Se il DB è usato da un’applicazione (es. backend Django):

```bash
sudo systemctl restart nginx
sudo systemctl restart zeroerp-gunicorn.service
```

---

## 🧭 Step 8 — Verifica Applicazioni Esterne (Django, API, ecc.)

### Test tramite Django:

```bash
python manage.py dbshell
SHOW server_version;
```

### Oppure:

```bash
python manage.py shell -c "from django.db import connection; cur = connection.cursor(); cur.execute('SHOW server_version;'); print(cur.fetchone())"
```

Se il risultato è `18.x`, la migrazione è conclusa.

---

## 📌 Note Aggiuntive

* Gli upgrade maggiori **non cancellano mai** automaticamente un cluster vecchio.
* L’uso di `pg_dump` non è necessario: `pg_upgradecluster` gestisce tutto.
* PostgreSQL 18 è pienamente compatibile con PostGIS 3.6.
* L’upgrade può essere ripetuto in ambienti staging/produzione con le stesse procedure.

---

## ✅ Conclusione

L’aggiornamento del cluster PostgreSQL da 17 a 18 è un’operazione sicura, ripetibile e completamente supportata sugli ambienti Debian/Ubuntu. Seguendo questa procedura, l’ambiente ZeroERP può essere aggiornato senza downtime significativo e senza necessità di dump/restore manuali.

Se utilizzi più ambienti (dev, test, staging, produzione), il consiglio è:

* eseguire l’upgrade in ordine crescente di criticità
* verificare sempre la presenza delle estensioni
* lasciare il cluster precedente per qualche giorno prima della rimozione definitiva

---

## 🏁 Fine Documento

Manuale pronto per essere inserito nella documentazione ufficiale ZeroERP.
