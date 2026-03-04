# **Documento di Avvio e Struttura di Liquibase (v2)**

> 👀 **Vedi anche**
> Tutte le attività SQL generate tramite Liquibase devono rispettare le convenzioni definite nel documento:
> *[Linee Guida SQL](linee-guida-sql.md)*
>
> *Versione iniziale(solo consultazione): [liquibase-setup-and-workflow_v1](./liquibase-setup-workflow_v1.md)*

---

> ⚠️ **Importante**
> Tutti i file di changelog devono avere estensione **`.yaml`** (non `.yml`).
> Entrambe le estensioni sono valide per Liquibase, ma in **ZeroErp** si adotta **`.yaml`** come standard unico per consistenza con CI/CD e documentazione.

---

## 1. Obiettivo

Descrivere configurazione e workflow di **Liquibase** per **ZeroErp (struttura v2)**:

* Avvio su PostgreSQL
* Struttura dei changelog (**master v2** e cartelle `migrations_v2/…`)
* Ordinamento delle migrazioni tramite **changelog autogenerato**
* Esecuzione comandi base (`validate`, `update`)
* Gestione evoluzioni con nuovi changeSet (`00_schema`, `20_code`, …)

---

## 2. Prerequisiti

* - Java **17 LTS** (obbligatorio per Liquibase 5.x)
* Liquibase **5.x Community**
* Driver JDBC PostgreSQL presente nel classpath
* Accesso a un DB di sviluppo/test

---

## 3. Struttura dei Changelog e delle Cartelle (v2)

```
ZeroErp/db/changelog/
├─ changelog-master-v2.yaml        # Master v2 (attivo)
├─ changelog-master.yaml           # Master storico v1 (incluso)
│
├─ migrations_v2/
│  ├─ changelog-autogen.yaml       # 🔧 AUTOGENERATO (DDL + CODE ordinati)
│  │
│  ├─ 00_schema/                   # DDL (tabelle, indici, FK, view strutturali)
│  │  ├─ anagrafiche/
│  │  ├─ vendite/
│  │  └─ …
│  │
│  ├─ 20_code/                     # Codice DB (funzioni, trigger, procedure, view tecniche)
│  │  ├─ anagrafiche/
│  │  ├─ vendite/
│  │  └─ …
│  │
│  ├─ 80_data/                     # Dati / configurazioni (loadUpdateData)
│  ├─ 85_pgagent/                  # Job di scheduling (pgAgent)
│  └─ 90_end/                      # Step finali (runAlways / apply policy)
│
├─ migrations/                     # LEGACY v1 (non modificare)
├─ baseline/                       # LEGACY v1 (non modificare)
└─ legacy/                         # Archivio file dismessi/spostati
```

### Regole operative (v2)

* Tutto il **nuovo sviluppo** avviene esclusivamente in `migrations_v2/`.

* La **storia pregressa (v1)** rimane invariata ed è inclusa dal master v2.

* Le cartelle `00_schema` e `20_code` **non sono incluse direttamente nel master**.

* L’ordine di esecuzione di DDL e CODE è governato dal file:

  ```
  migrations_v2/changelog-autogen.yaml
  ```

  che viene **generato automaticamente** in base al timestamp nel nome file (`YYYYMMDD-NN`).

* Le cartelle `80_data`, `85_pgagent`, `90_end` sono **escluse dall’autogen** e vengono incluse **a blocchi** nel master v2.

---

## 4. Master Changelog (v2)

```yaml
databaseChangeLog:
  # 1) Storia esistente (v1): lasciata com'è, semplicemente inclusa
  - include:
      file: changelog-master.yaml
      relativeToChangelogFile: true

  # 2) Nuove migrazioni v2 (DDL + CODE ordinati temporalmente)
  - include:
      file: migrations_v2/changelog-autogen.yaml
      relativeToChangelogFile: true

  # 3) Dati, job e step finali (gestiti a blocchi)
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

### Ordine di esecuzione complessivo

1. Storia legacy v1
2. **DDL + CODE v2** (ordine temporale globale)
3. Import dati / configurazioni
4. Job pgAgent
5. Step finali

---

## 5. File `liquibase.properties` (esempio)

```properties
# Connessione PostgreSQL
driver=org.postgresql.Driver

url=jdbc:postgresql://localhost:5432/zeroerp
username=zeroerp
password=secret

# Master in uso
changeLogFile=db/changelog/changelog-master-v2.yaml
```

> ℹ️ Il master v2 include automaticamente il master storico v1.

---

## 6. `changelog-autogen.yaml`

* È **autogenerato** dallo script:

  ```bash
  python scripts/gen_master_autogen.py \
    --root db/changelog/migrations_v2 \
    --out  db/changelog/migrations_v2/changelog-autogen.yaml \
    --strict
  ```

* Contiene **solo** include relativi a:

  * `00_schema/**`
  * `20_code/**`

* È ignorato da Git (`.gitignore`) e **rigenerato automaticamente**:

  * in CI
  * tramite wrapper locale `liquibase5`

---

## 7. Workflow Operativo

### Validazione

```bash
liquibase validate
```

### Update

```bash
liquibase update
```

Il wrapper `liquibase5` garantisce che il file `changelog-autogen.yaml` venga rigenerato prima dell’esecuzione.

---

## 8. Evoluzioni Future (v2)

### Nuovi file

* DDL:

  ```
  migrations_v2/00_schema/<schema>/YYYYMMDD-NN-<tipo>-<descrizione>.yaml
  ```

* CODE:

  ```
  migrations_v2/20_code/<schema>/YYYYMMDD-NN-<tipo>-<descrizione>.yaml
  ```

### Pattern sicuro di refactor

**Expand → Align → Contract**

1. **Expand (00_schema)**: aggiunta nuovo oggetto senza rimuovere il vecchio
2. **Align (20_code)**: funzioni/trigger compatibili con entrambe le versioni
3. **Contract (00_schema)**: rimozione definitiva in release successiva

---

## 9. Convenzioni e Best Practice

* Naming file: `YYYYMMDD-NN-<tipo>-<feature>.yaml`
* Un changeSet coerente per file
* `logicalFilePath` sempre valorizzato
* View diagnostiche (`dbops.diag_*`) preferibilmente:

  * con `preConditions`
  * oppure posizionate dopo i refactor
* `90_end` usato solo per step finali e policy applicative

---

## 10. Struttura Legacy (solo riferimento)

```
ZeroErp/db/changelog/
├─ changelog-master.yaml
├─ baseline/
└─ migrations/
```

> ⚠️ La struttura legacy **non va modificata**.
> Il master v2 la include integralmente per garantire bootstrap completo su nuovi ambienti.

---

*Documento aggiornato per il progetto ZeroErp – Liquibase v2 con autogen timeline.*
