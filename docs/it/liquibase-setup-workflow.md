**Documento di Avvio e Struttura di Liquibase**

> 👀 **Vedi anche**    
> Approfondimento SQL  
> Tutte le attività SQL generate tramite Liquibase devono rispettare le convenzioni definite nel documento:  
> [Linee Guida SQL](linee-guida-sql.md).

---
> ⚠️ **Importante (Visione Futura)**   
> Data la scelta di utilizzare `includeAll` nel master changelog e la struttura a cartelle, **tutti gli sviluppi di oggetti che precedono altri (es. tabelle)** devono essere inseriti **nella cartella `00_bootstrap`**.
> In questo modo le trigger e le trigger function verranno applicate **dopo** la creazione delle tabelle, garantendo coerenza e permettendo future evoluzioni senza conflitti.

---

#### 1. Obiettivo

Descrivere la configurazione iniziale e il workflow di Liquibase per il progetto **ZeroErp**:

* Avviare Liquibase su PostgreSQL
* Definire struttura dei changelog (baseline vs migrations)
* Eseguire le operazioni di base (`validate`, `changelogSync`, `update`)
* Gestire evoluzioni future con nuovi changeSet

---

#### 2. Prerequisiti

* Java 11+ installato
* Liquibase 4.31.1 (o superiore) scaricato e configurato
* Driver JDBC PostgreSQL (`postgresql-<version>.jar`) disponibile
* Accesso a un DB di sviluppo/test e a quello esistente (Zero)

---

#### 3. Struttura dei Changelog e delle Cartelle

```
ZeroErp/db/changelog/
├─ changelog-master.yaml         # master changelog
├─ baseline/                     # snapshot iniziale (punto 0)
│   ├─ 000-tables-config.yaml    # schema config
│   ├─ 001-tables-anagrafiche.yaml
│   └─ sql/<schema>/…            # script SQL originali
└─ migrations/                   # step 00–99 (changelog generici)
    ├─ 00_bootstrap/            ← primi steps (script di base)
    │   ├─ 20250514-01-fn-trigger-audit-generic.yaml
    │   └─ sql/<schema>/…        # script SQL di quel changeSet
    ├─ 10_scripts/              # script di utilità e trigger
    │   ├─ 20250507-01-trgfn-blocco-colonna-mctit.yaml
    │   └─ sql/<schema>/…        # script SQL di quel changeSet
    ├─ 20_config/               # configurazioni iniziali personalizzate
    │   └─ sql/<schema>/…        # script SQL di configurazione
    ├─ 30_anagrafiche/          # evoluzioni anagrafiche
    │   └─ sql/<schema>/…        
    ├─ 40_storico/              # evoluzioni storico
    │   └─ sql/<schema>/…        
    ├─ 50_dbops/                # evoluzioni DBOps
    │   └─ sql/<schema>/…        
    └─ …
    └─ 90_end/                  # script finali da eseguire sempre per ultimi
        └─ apply-fk-index-policy.yaml
```

* **Baseline**: snapshot iniziale; `changelogSync` li marca eseguiti e non saranno riapplicati automaticamente.
* **Migrations**: file numerati definiscono le modifiche incrementalmente. Ogni folder numerato (00–50…) contiene YAML e script SQL.
* **Cartella *90\_end***: dedicata ai changeSet che devono **sempre** essere eseguiti **per ultimi**, indipendentemente dalle date. Qui si collocano:

  * changeSet con `runAlways: true` o `runAlways: false` per operazioni di chiusura
  * richiamo di procedure/funzioni di popolamento o aggiornamento di tabelle (es. `CALL dbops.apply_fk_index_policy();`)
  * eventuali cleanup o sync finali delle policy

> 🔔 *Consiglio*:   
> Nomina il file con prefisso la data iniziale seguito da descrizione, es. `20250630-01-end-apply-fk-policy.yaml`. In questo modo l’ordine alfabetico di Liquibase garantisce la priorità d’esecuzione. Nel caso sia necessario far eseguire un changelog prima di uno esistente immettere la data precedente.

---

#### 4. Master Changelog (`changelog-master.yaml`)

```yaml
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

* Caricamento in ordine alfabetico.
* Usare `include` per eccezioni di ordine specifico.

---

#### 5. File `liquibase.properties`

```properties
# Connessione PostgreSQL
driver=org.postgresql.Driver
classpath=/path/to/postgresql-42.x.jar
url=jdbc:postgresql://localhost:5432/Zero
username=<utente>
password=<password>

# Changelog principale
changeLogFile=db/changelog/changelog-master.yaml

# Schema per DATABASECHANGELOG*
defaultSchemaName=config
liquibaseSchemaName=config
```

* **Suggerimento**: script shell/batch per caricare credenziali a runtime.

---

#### 6. Workflow Iniziale

1. **Validate**: `liquibase validate`
2. **Sync Baseline**: `liquibase changelogSync`
3. **Update su DB Vuoto**: `liquibase update`

---

#### 7. Evoluzioni Future (Migrations)

1. **Creare YAML** in `migrations/<area>/YYYYMMDD-XX-descrizione.yaml`
2. **Utilizzare changeSet Liquibase** o `sqlFile`
3. **Rollback**: opzionale o esplicito
4. **Script SQL**: in `migrations/<area>/sql/`
5. **Eseguire**: `validate` → `update`

---

#### 8. Comandi Principali

* `liquibase validate`
* `liquibase changelogSync`
* `liquibase update`
* `liquibase updateSql`
* `liquibase rollback`

---

#### 9. Rollback e Reverse

* Rollback automatico per change types nativi
* `rollback` esplicito con blocco `rollback`
* `rollbackToDate`, `rollbackCount`, `rollback tag`

---

#### 10. Convenzioni e Best Practice

* Utilizzo cartella `00_boostrab` (esempio generazione tabelle)
* Numerazione progressiva
* ID univoci con autore
* Contexts/Labels
* CI/CD: `validate` e `updateSql` in pipeline
* Versioning: excl. credenziali

---

*Documento redatto e condiviso con il team ZeroErp.*