##  📘 Estensioni PostgreSQL Utilizzate in Zero ERP

Zero ERP utilizza diverse estensioni PostgreSQL per migliorare le funzionalità e soddisfare specifiche esigenze applicative. Di seguito è riportata una panoramica delle estensioni attualmente in uso:

### Estensioni installate

* **`plpgsql`**
  Linguaggio procedurale integrato in PostgreSQL per definire funzioni, trigger e procedure stored direttamente nel database, garantendo logiche di business efficienti e robuste.

* **`postgis`**
  Aggiunge supporto per la gestione e analisi avanzata dei dati geografici e spaziali, consentendo query geospaziali e operazioni di calcolo territoriale complesse.

* **`postgis_topology`**
  Estensione complementare a PostGIS che fornisce strumenti per gestire e analizzare topologie spaziali, essenziali per la modellazione di reti o aree contigue.

* **[`pgcrypto`](/postgresql/pgcrypto)**
  Fornisce funzionalità crittografiche per la gestione sicura di dati sensibili, come crittografia simmetrica e asimmetrica, hashing sicuro e generazione di UUID.

* **`btree_gist`**
  Permette l’uso di indici GiST con tipi di dati standard, abilitando implementazioni avanzate e flessibili di indici multicolonna e personalizzati.

* **[`dblink`](/postgresql/dblink)**
  Consente connessioni e query cross-database tra diverse istanze PostgreSQL, utilizzata principalmente per attività di logging remoto e integrazioni di dati distribuiti.

* **[`pgagent`](/postgresql/pgagent)**
  Agente di schedulazione per PostgreSQL che esegue job programmati lato DB. Archivia job, schedule, step e log nello schema pgagent ed è utilizzato in Zero ERP per orchestrare tutte le attività periodiche di manutenzione del database.


---

Queste estensioni sono parte integrante della struttura tecnologica di Zero ERP, ognuna scelta per specifiche funzionalità e necessità progettuali, contribuendo alla sicurezza, efficienza e versatilità del sistema.

---


---
{% include-markdown "signature-core.md" %}
