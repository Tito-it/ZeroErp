# **Documento di Avvio e Struttura di Liquibase (v2)**

> 👀 **Vedi anche**
> Approfondimento SQL
>
> Tutte le attività SQL generate tramite Liquibase devono rispettare le convenzioni definite nel documento:
> *[Linee Guida SQL](linee-guida-sql.md)*
>
> *Verisone iniziale  [liquibase-setup-and-workflow_v1](../liquibase-setup-workflow_v1.md)*

---

> ⚠️ **Importante**
> Tutti i file di changelog devono avere estensione **`.yaml`** (non `.yml`).
> Entrambe le estensioni sono valide per Liquibase, ma in **ZeroErp** si adotta **`.yaml`** come standard unico per consistenza con CI/CD e documentazione.

---

## 1. Obiettivo

Descrivere configurazione e workflow di **Liquibase** per **ZeroErp**:

* Avvio su PostgreSQL
* Struttura dei changelog (**master v2** e cartelle `migrations_v2/…`)
* Esecuzione comandi base (`validate`, `update`)
* Gestione evoluzioni con nuovi changeSet (`00_schema`, `20_code`, …)

---

## 2. Prerequisiti

* Java 11+
* Liquibase 4.33.x (o superiore)
* Driver JDBC PostgreSQL presente nel classpath
* Accesso a un DB di sviluppo/test

---

## 3. Struttura dei Changelog e delle Cartelle

```
ZeroErp/db/changelog/
├─ changelog-master-v2.yaml     # NUOVO master (in uso)
├─ changelog-master.yaml        # master storico (v1) — incluso da v2
│
├─ migrations_v2/               # nuove migrazioni da oggi in poi
│  ├─ 00_schema/                # DDL: tabelle/indici/FK/VIEW ecc.
│  │  ├─ anagrafiche/
│  │  ├─ vendite/
│  │  └─ … (acquisti, catalogo, contabilita, internal, magazzino, maintenance, pagamenti)
│  ├─ 20_code/                  # codice DB: funzioni/trigger/procedure
│  │  ├─ anagrafiche/
│  │  ├─ vendite/
│  │  └─ … (stessi schemi)
│  ├─ 80_data/                  # import dati/config (CSV + loadUpdateData)
│  │  └─ config/
│  ├─ 85_pgagent/               # job di scheduling (pgAgent)
│  └─ 90_end/                   # step finali (runAlways / operazioni di chiusura)
│
├─ migrations/                  # **LEGACY v1** (non modificare)
├─ baseline/                    # **LEGACY v1** (non modificare)
└─ legacy/                      # archivio eventuali file dismessi/spostati
```

**Regole operative (v2):**

* **Nuovo lavoro** solo in `migrations_v2/…`.
* La **storia precedente** rimane dove si trova (migrations/baseline) e viene **inclusa** dal master v2: utile per nuovi ambienti e per consultazione.

---

## 4. Master Changelog (v2)

```yaml
databaseChangeLog:
  # 1) Storia esistente (v1): lasciata com'è, semplicemente inclusa
  - include:
      file: changelog-master.yaml
      relativeToChangelogFile: true

  # 2) Nuove migrazioni (v2): ordine garantito
  - includeAll:
      path: migrations_v2/00_schema
      relativeToChangelogFile: true
  - includeAll:
      path: migrations_v2/20_code
      relativeToChangelogFile: true
  - includeAll:
      path: migrations_v2/80_data
      relativeToChangelogFile: true
  - includeAll:
      path: migrations_v2/85_pgagent
      relativeToChangelogFile: true
  - includeAll:
      path: migrations_v2/90_end
      relativeToChangelogFile: true
```

**Ordine d’esecuzione**: `00_schema` → `20_code` → `80_data` → `85_pgagent` → `90_end`.

---

## 5. File `liquibase.properties` (esempio)

```properties
# Connessione PostgreSQL
driver=org.postgresql.Driver
# classpath=<path>/postgresql-<version>.jar   # se serve

url=jdbc:postgresql://localhost:5432/zeroerp
username=titodb

# Master in uso
changeLogFile=db/changelog/changelog-master-v2.yaml
```

> **Nota**: il master v2 include il master storico v1. Non è necessario modificare/traslocare la storia precedente.

---

## 6. `80_data` (schema `config`) — import dati

* CSV prodotti dalla pipeline in `migrations_v2/80_data/config/…`
* Changelog YAML con `loadUpdateData` (uno per tabella)
* Esempi già presenti (stati/utilities) restano validi

> **Suggerimenti**: usare `runOnChange: true`, `validCheckSums: [ANY]`, e `preConditions` con `tableExists`.

---

## 7. Workflow Iniziale

* **Validazione**: `liquibase validate`
* **Update** su nuovi o esistenti:

  ```bash
  liquibase --defaults-file=db/liquibase.properties \
            --changelog-file=db/changelog/changelog-master-v2.yaml \
            update
  ```

  *Gli ambienti già aggiornati con v1 non rieseguono i changeSet storici, perché sono gli stessi file (stessi checksum).*

---

## 8. Evoluzioni Future (v2)

* **Nuovi file**:

  * `migrations_v2/00_schema/<schema>/YYYYMMDD-NN-<tipo>-<desc>.yaml` (DDL)
  * `migrations_v2/20_code/<schema>/YYYYMMDD-NN-<tipo>-<desc>.yaml` (fn/trg/proc)
  * `migrations_v2/90_end/…` per step finali
* **Header obbligatorio** in ogni file:

  ```yaml
  databaseChangeLog:
    logicalFilePath: db/changelog/migrations_v2/<subpath>/<filename>.yaml
  ```
* **Pattern sicuro per rinomine**: **Expand → Align (20\_code) → Contract**

  * Expand (00\_schema): aggiungi il nuovo senza rimuovere il vecchio
  * Align (20\_code): `CREATE OR REPLACE` funzioni/trigger compatibili col nuovo
  * Contract (00\_schema): rimuovi il vecchio quando sei certo (release successiva)

---

## 9. Comandi Principali

* `liquibase validate`
* `liquibase update`
* `liquibase updateSql`
* `liquibase rollback` / `rollbackCount` / `rollbackToDate` / `rollbackOneChangeSet`

---

## 10. Convenzioni e Best Practice

* **Naming**: `YYYYMMDD-NN-<tipo>-<feature>.yaml` (`tipo`: `tbl/col/fk/idx/view/fn/trg/proc/data/end`)
* **Un changeSet coeso** per oggetto/funzionalità
* **`logicalFilePath`**: sempre impostato; consente spostamenti futuri senza invalidare checksum
* **`includeAll`** + prefisso data garantiscono l’ordine
* **Contexts/Labels** se servono per ambienti diversi
* **`90_end`**: step finali (es. `CALL dbops.apply_fk_index_policy()`), eventualmente `runAlways: true`

---

## 11. Struttura **Legacy** (solo riferimento)

La precedente organizzazione rimane nel repository per **compatibilità e consultazione**:

```
ZeroErp/db/changelog/
├─ changelog-master.yaml         # master storico (v1)
├─ baseline/                     # snapshot iniziale v1
└─ migrations/                   # vecchie migrazioni
   ├─ 00_bootstrap/              # DDL iniziali (storico)
   ├─ 10_scripts/
   ├─ 20_config/
   ├─ 30_anagrafiche/
   ├─ 40_storico/
   ├─ 50_dbops/
   ├─ 55_maintenance/
   ├─ 80_data/
   ├─ 85_pgagent/
   └─ 90_end/
```

> **Uso pratico**: Il **master v2** include il **master storico v1**; quindi i nuovi cloni possono partire direttamente da `changelog-master-v2.yaml`. In caso di necessità, è sempre possibile **recuperare** changeSet o script dal percorso legacy senza modificarlo.

---

*Documento redatto per il progetto ZeroErp (struttura v2).*
