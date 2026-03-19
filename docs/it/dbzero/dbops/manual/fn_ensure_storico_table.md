## 📘 Documentazione Funzione –  `dbops.fn_ensure_storico_table`

---

> 👀 **Vedi anche**
>
Approfondimento tabelle:
>
[`dbops.audit_log`](/dbzero/dbops/tabelle/audit_log)
> [`dbops.error_log`](/dbzero/dbops/tabelle/error_log)
>
Approfondimento funzioni:
>
[`dbops.fn_run_automations_storico_provision`](/dbzero/dbops/funzioni/fn_run_automations_storico_provision)
> [`dbops.fn_audit_log_once`](/dbzero/dbops/funzioni/fn_audit_log_once)
> [`script.fn_log_and_raise_error`](/dbzero/dbops/funzioni/fn_log_and_raise_error)

---
### 🎯 Scopo Principale
(latest review 16-01-26)
La funzione **`fn_ensure_storico_table`** si occupa di **creare** (se non esiste) la **tabella di storico** nello schema `storico` corrispondente ad una tabella base (`p_schema_base.p_table_base`), con **colonna FK** coerente al **tipo** della PK della tabella padre, **indici** necessari e **logging** integrato. Supporta modalità **dry‑run** e la creazione opzionale di un **indice GIN** sullo `snapshot`.

---

### Dettagli

* **Firma**

  ```sql
  CREATE OR REPLACE FUNCTION dbops.fn_ensure_storico_table(
    p_schema_base text,
    p_table_base text,
    p_fk_col text,
    p_create_gin_index boolean,
    p_dry_run boolean
  ) RETURNS void
  ```

* **Comportamento**

  * Verifica l’esistenza di `storico.<p_table_base>`; se **esiste** → **RETURN**.
  * Ricava **PK** (assunta **mono‑colonna**; fallback su `id`) e **tipo** della tabella padre.
  * Genera DDL per creare la tabella storico con colonne: `id BIGSERIAL` (PK), `p_fk_col <tipo padre> NOT NULL`, `change_type char(1)`, `tipo_operazione smallint`, `snapshot jsonb`, metadati (`user_insert`, `data_insert`, `tx_id`, `valid_from`, `valid_to`).
  * **Non** crea la **FK** verso la tabella base (commentata nel DDL) per evitare blocchi in cancellazione; crea invece **indice** su `p_fk_col` (`ix_<table>_<fk>_fk`).
  * Se `p_create_gin_index = true`, crea indice **GIN** su `snapshot` (`ix_<table>_snapshot_gin`).
  * Se `p_dry_run = true`, **non esegue** il DDL; registra un evento **DRYRUN** tramite `dbops.fn_audit_log_once` e termina.
  * Se avviene un errore, invoca `script.fn_log_and_raise_error` con codice ed oggetti di contesto.

* **Naming vincoli/indici**

  * PK storico: `pk_storico_<table>`
  * FK (commentata): `fk_<table>`
  * Indice FK: `ix_<table>_<fk_col>_fk`
  * Indice GIN snapshot: `ix_<table>_snapshot_gin`

---

### Utilizzo tipico

1. **Provisioning dello storico** per una tabella nuova: chiamata con `p_create_gin_index=true`, `p_dry_run=false`.
2. **Automazione** in `fn_run_automations_storico_provision`: creazione on‑demand della tabella storico durante un ciclo di regole.
3. **Simulazione** di impatto (CI/CD): stessa chiamata con `p_dry_run=true` per audit non invasivo.

---

### Collegamento con automazione

La funzione è progettata per integrarsi nei flussi `STORICO_PROVISION` di `fn_run_automations_storico_provision`, emettendo log **OK/DRYRUN** tramite `fn_audit_log_once` e instradando errori coerenti su `error_log` con `fn_log_and_raise_error`.

---

### Esempio pratico

Creare (se manca) la tabella storico per `anagrafiche.soggetti`, con FK `soggetto_id`, indice GIN su `snapshot`, **senza** dry‑run:

```sql
SELECT dbops.fn_ensure_storico_table(
  'anagrafiche',
  'soggetti',
  'soggetto_id',
  true,   -- crea indice GIN su snapshot
  false   -- esecuzione reale (no dry‑run)
);
```

Esecuzione in **dry‑run** (solo log, nessun DDL):

```sql
SELECT dbops.fn_ensure_storico_table(
  'anagrafiche',
  'soggetti',
  'soggetto_id',
  false,  -- niente GIN
  true    -- DRYRUN: non crea la tabella
);
```

---

> **In sintesi**: `fn_ensure_storico_table` standardizza la creazione delle tabelle di storico, garantendo coerenza di tipi, indici utili alla consultazione e integrazione con il framework di **audit**/**error handling** dell’automazione.
