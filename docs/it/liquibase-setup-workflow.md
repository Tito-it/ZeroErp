**Documento di Avvio e Struttura di Liquibase**

> 👀 **Vedi anche** 

> Approfondimento SQL:  
> Tutte le attività SQL generate tramite Liquibase devono rispettare le convenzioni definite nel documento :
> [Linee Guida SQL](linee-guida-sql.md).


#### 1. Obiettivo

Descrivere la configurazione iniziale e il workflow di Liquibase per il progetto **ZeroErp**:

* Avviare Liquibase su PostgreSQL
* Definire struttura dei changelog (baseline vs migrations)
* Eseguire le operazioni di base (`validate`, `changelogSync`, `update`)
* Gestire evoluzioni future con nuovi changeSet

---

#### 2. Prerequisiti

* Java 11+ installato
* Liquibase 4.31.1 o superiore scaricato e configurato
* Driver JDBC PostgreSQL (`postgresql-<version>.jar`) disponibile
* Accesso a un DB di sviluppo/test e a quello esistente (Zero)

---

#### 3. Struttura dei Changlog e delle Cartelle

```
ZeroErp/db/changelog/
├─ changelog-master.yaml         # master changelog
├─ baseline/                     # snapshot iniziale (punto 0)
│   ├─ 000-tables-config.yaml    # schema config
│   ├─ 001-tables-anagrafiche.yaml
│   └─ sql/<schema>/…            # script SQL originali
└─ migrations/                   # step 0–99 (changelog generici)
    ├─ 00_bootstrap/            ← qui i changelog “primi passi”
    │   ├─ 
    │   ├─ 20250514-01-fn-trigger-audit-generic.yaml
    │   └─ sql/<schema>/… 
    ├─ 10_script/                 # step 0–99 (changelog generici)
    │   ├─ 20250507-01-trgfn-blocco-colonna-mctit.yaml
    │   └─ sql/<schema>/…        # script SQL di quel changeSet
    ├─ 20_config/                # 
    │   └─ sql/<schema>/…        # script SQL di configurazione
    ├─ 30_anagrafiche/           # 
    │   └─ sql/<schema>/…
    ├─ 40_storico/               
    │   └─ sql/<schema>/…
    ├─ 50_dbops/               
    │   └─ sql/<schema>/…
    └─ …
```

* **Baseline**: contiene i file YAML generati per rappresentare lo stato iniziale del DB. Non verranno mai rieseguiti dopo il `changelogSync`.
* **Migrations**: ogni file numerato (YYYYMMDD–XX–descrizione–autore.yaml) definisce una nuova modifica e riferisce script SQL nella cartella corrispondente.

---

#### 4. Master Changelog (`changelog-master.yaml`)

```yaml
databaseChangeLog:
  - includeAll:
      path: baseline
      relativeToChangelogFile: true
      errorIfMissingOrEmpty: true

 - Esempio di eccezioni quando non si può eseguire l'ordine interno in migrations
#  - include:
#      file: migrations/script/20250507-01-trgfn-blocco-colonna-mctit.yaml 


  - includeAll:
      path: migrations
      relativeToChangelogFile: true
      errorIfMissingOrEmpty: false
```

* Il caricamento avviene in ordine alfabetico basato sui nomi dei file.
* Utilizzare la cartella boostrap se serve imporre un ordine diverso, o per attività generiche.
* Se serve imporre un ordine diverso per singoli file, usare `include` anziché `includeAll`. E' consigliato l'utilizzo del metodo descritto al punto precedente.
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

# (Opzionali) Schema per DATABASECHANGELOG*
defaultSchemaName=config
liquibaseSchemaName=config
```

* **Suggerimento**: creare script `.bat`/`.sh` (es. `liquibase-validate`, `liquibase-update`) che carichino in runtime le credenziali, evitando di committarle.

---

#### 6. Workflow Iniziale

1. **Validazione**:

   ```bash
   liquibase validate
   ```

   Verifica sintassi, id duplicati e file mancanti.
2. **Sync Baseline**:

   ```bash
   liquibase changelogSync
   ```

   Marca tutti i changeSet di `baseline/` come già eseguiti.
3. **Test su DB Vuoto**:

   ```bash
   liquibase --url=jdbc:.../devdb --username=dev --password=dev update
   ```

   Verifica applicazione corretta di baseline + migrations già pronte.

---

#### 7. Evoluzioni Future (Migrations)

Per ogni nuova modifica:

1. **Crea file YAML** in `migrations/<area>/YYYYMMDD-XX-descrizione-autore.yaml`.
2. **Usa changeSet Liquibase nativo** (`createTable`, `addColumn`, `sqlFile`, ecc.).
3. **Rollback (opzionale)**: definisci come tornare indietro.
4. **Script SQL**: se necessario, inserisci `.sql` in `migrations/<area>/sql/` e referenzialo con `relativeToChangelogFile: true`.
5. **Esegui**:

   ```bash
   liquibase validate
   liquibase update
   ```

---

#### 8. Comandi Principali

* `liquibase validate` → controlla file e configurazioni
* `liquibase changelogSync` → marca come eseguiti changeSet senza applicarli
* `liquibase update` → applica allineando il DB
* `liquibase updateSql` → genera lo script SQL
* `liquibase rollback` → rollback tramite tag o conteggio

---

#### 9. Rollback e Reverse

   Liquibase supporta il rollback in diversi modi:

   Rollback automatico: per i change types nativi (es. createTable, addColumn, createSequence) Liquibase è in grado di invertire automaticamente l’operazione se non viene fornito un blocco rollback esplicito.

   Rollback esplicito: puoi definire un blocco rollback: all’interno di ogni changeSet per specificare l’esatta logica inversa, utile soprattutto per SQL complessi o funzioni personalizzate:

   - changeSet:
      id: 110-add-column-xyz
      author: mctit
      changes:
         - addColumn:
            tableName: foo
            columns:
               - column: { name: xyz, type: VARCHAR(50) }
      rollback:
         - dropColumn:
            tableName: foo
            columnName: xyz

   Rollback per tag o conteggio:

   liquibase tag v1.0 per marcare uno stato prima di un deploy

   liquibase rollback v1.0 per tornare al tag

   liquibase rollbackCount 2 per annullare gli ultimi 2 changeSet applicati

   liquibase rollbackToDate YYYY-MM-DD per annullare al punto in una data

   Nota: se non definisci rollback esplicito, Liquibase utilizzerà la sua logica predefinita, che copre la maggior parte dei change types comuni. In scenari critici, è consigliabile sempre fornire un rollback custom per avere controllo completo.



#### 10. Convenzioni e Best Practice

* **Numerazione progressiva**: garantisce ordine e evita collisioni
* **ID univoci**: includi autore o suffisso per evitare duplicati in team
* **Tag nativi**: preferisci i changeSet astratti per portabilità
* **Contexts/Labels**: isolare changeSet per feature o ambienti specifici
* **CI/CD**: integra `validate` e `updateSql` nel pipeline, code review con DB owner
* **Versioning**: tutti i cambiamenti nel VCS, escludi credenziali da `liquibase.properties`

---


   

*Documento redatto e condiviso con il team ZeroErp.*