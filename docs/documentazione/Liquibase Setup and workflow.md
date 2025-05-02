**Documento di Avvio e Struttura di Liquibase**

**1. Obiettivo**  
Fornire una guida operativa per:
- Inizializzare Liquibase su un progetto PostgreSQL  
- Definire la struttura dei changelog (baseline e migrations)  
- Eseguire le prime attività (`validate`, `changelogSync`, `update`)  
- Gestire le evoluzioni future con nuovi changeSet

---

**2. Prerequisiti**  
- Java 11+ installato
- Liquibase 4.31.1 (o versione successiva) scaricato e configurato
- Driver JDBC PostgreSQL (es. `postgresql-42.5.0.jar`) disponibile
- Accesso a DB di sviluppo/test e DB esistente (prod/preesistente)

---

**3. Layout dei file**  
```plaintext
src/main/resources/db/
├─ changelog-master.yaml       # master changelog unico
├─ baseline/                   # snapshot iniziale (punto 0)
│   ├─ 000-tables-config.yaml  # schema config
│   ├─ 001-tables-anagraf.yaml # schema anagrafiche
│   └─ sql/                    # script SQL originali
│       ├─ config/…
│       └─ anagrafiche/…
└─ migrations/                 # tutte le future modifiche
    ├─ 100-add-new-table.yaml  # primo changeSet evolutivo
    └─ sql/                    # script SQL di migrazione
        ├─ config/…
        └─ anagrafiche/…
```

---

**4. File `liquibase.properties`**  
```properties
# Changelog principale
changeLogFile=src/main/resources/db/changelog-master.yaml

# Connessione PostgreSQL
driver=org.postgresql.Driver
classpath=/path/to/postgresql-42.5.0.jar
url=jdbc:postgresql://localhost:5432/Zero
username=tuo_utente
password=tuo_password

# Schema per DATABASECHANGELOG*
liquibaseSchemaName=config
defaultSchemaName=config
```

---

**5. Master changelog (`changelog-master.yaml`)**  ```yaml
databaseChangeLog:
  - includeAll:
      path: baseline
      relativeToChangelogFile: true
      errorIfMissingOrEmpty: true

  - includeAll:
      path: migrations
      relativeToChangelogFile: true
      errorIfMissingOrEmpty: false
```

---

**6. Bootstrap iniziale (baseline)**  
1. Creare i file YAML in `baseline/` con changeSet che referenziano script SQL originali (`baseline/sql/...`).  
2. Eseguire:
   ```bash
   liquibase validate    # controlla sintassi e consistenza
   liquibase changelogSync    # marca tutti i baseline come applicati
   ```  

---

**7. Test su DB pulito**  
Usare un database di sviluppo vuoto per verificare la correttezza dei changeSet iniziali e delle migrazioni:
```bash
liquibase \
  --url=jdbc:postgresql://dev-server:5432/devdb \
  --username=dev \
  --password=dev \
  update
```

---

**8. Evoluzioni future (migrations)**  
1. Creare in `migrations/` un nuovo file numerato (es. `100-add-tabella-xyz.yaml`) con:
   - Tag Liquibase nativi (`createTable`, `addColumn`, `createIndex`, `sqlFile`, ecc.)  
   - `rollback` opzionale per revert  
2. Aggiungere eventuali script SQL in `migrations/sql/<schema>/…` e referenziarli con `relativeToChangelogFile`.  
3. Eseguire:
   ```bash
   liquibase validate
   liquibase update
   ```
Solo i nuovi changeSet verranno applicati.

---

**9. Comandi chiave**  
- `liquibase validate` → verifica sintassi e coerenza dei changelog
- `liquibase changelogSync` → marca i changeSet come applicati senza eseguirli
- `liquibase update` → applica i changeSet non ancora eseguiti
- `liquibase updateSql` → genera script SQL senza applicarlo
- `liquibase rollback <tag|count>` → rollback basati su tag o conteggio

---

**10. Best Practice**  
- Usare tag Liquibase nativi per massima portabilità
- Numerare file YAML per ordine deterministico
- Separare snapshot iniziale da migrazioni evolutive
- Testare sempre in ambiente DEV/TEST prima di produrre in prod
- Versionare `liquibase.properties` e tutti i changelog nel VCS

---



