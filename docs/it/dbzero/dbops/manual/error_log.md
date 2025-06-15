## 📘 Documentazione Concettuale – Tabella `dbops.error_log`

> 👀 **Vedi anche**
>
> Approfondimento tabelle:    
> - [config.messagggi_errore](/dbzero/config/tabelle/messaggi_errore)    
> - [dbops.audit_log](/dbzero/dbops/tabelle/audit_log)    

La tabella **`dbops.error_log`** serve a **centralizzare la registrazione degli errori** che si verificano nelle diverse aree dell’applicazione (database, backend, frontend, job, ecc.), fornendo un quadro completo del contesto, della fonte e della transazione coinvolta.

---

### 🎯 Scopo Principale

* Raccogliere in un unico punto gli errori generati da funzioni, trigger o applicazioni, permettendo analisi e allineamento con il catalogo di messaggi di errore.
* Consentire il **collegamento transazionale** tramite `tx_id`, per ricostruire l’intero flusso di operazioni (ad esempio un job batch) incrociando tabelle come `audit_log`.

---

### 🔍 Significato dei Campi Chiave

* **`id`**: identificativo univoco del record di errore.
* **`occurred_at`**: timestamp con timezone dell’evento di errore.
* **`area`**: ambito di origine (es. `database`, `backend`, `frontend`, `job`).
* **`function_name`**: nome generico della funzione, metodo o applicazione che ha rilevato o propagato l’errore. Può riferirsi a trigger PL/pgSQL, procedure esterne, job schedulati o endpoint di servizio.
* **`messaggio_errore_id`**: FK verso `config.messaggi_errore(id)`, collega il record al testo di errore e alle eventuali traduzioni o codifiche di dettaglio.
* **`context`**: campo JSONB in cui si registrano parametri di input, valori di variabili, utente esecutore, stack trace minimo o altri metadati rilevanti.
* **`tx_id`**: UUID generato sulla base dell’ID di transazione corrente (tramite `txid_current()`). Permette di raggruppare più errori o eventi collegati alla stessa transazione, e di unire la storia di errori a tabelle quali `audit_log` o altre entità di log.

---

### 🔒 Vincoli e Relazioni

* **PK**: vincolo `error_log_pkey` su `id`.
* **FK**: `messaggio_errore_id` → `config.messaggi_errore(id)` (senza azioni automatiche di update o delete).
* **Generazione automatica**:

  * `occurred_at` default `now()`
  * `tx_id` default `md5(txid_current()::text)::uuid`
  * `context` default a oggetto JSONB vuoto `{}`

---

### ⚙️ Esempi di Utilizzo

1. **Recuperare tutti gli errori di una specifica transazione**:

   ```sql
   SELECT *
     FROM dbops.error_log
    WHERE tx_id = '123e4567-e89b-12d3-a456-426614174000';
   ```

2. **Unire gli errori con il catalogo dei messaggi per ottenere la descrizione**:

   ```sql
   SELECT e.id, e.occurred_at, m.codice, m.testo, e.context
     FROM dbops.error_log e
     JOIN config.messaggi_errore m
       ON e.messaggio_errore_id = m.id;
   ```

3. **Costruire la cronologia completa di una transazione**:

   ```sql
   WITH errs AS (
     SELECT * FROM dbops.error_log WHERE tx_id = :tx
   ), audits AS (
     SELECT * FROM audit_log WHERE tx_id = :tx
   )
   SELECT * FROM errs
   UNION ALL
   SELECT * FROM audits
   ORDER BY occurred_at;
   ```

---

### 💡 Vantaggi Operativi

* **Tracciabilità a 360°**: unisce errori e transazioni in un unico flusso temporale.
* **Analisi rapida**: il campo `context` in JSONB consente filtri e aggregazioni sui metadati.
* **Manutenibilità**: uso di FK garantisce coerenza con il catalogo dei messaggi di errore.
* **Flessibilità**: `function_name` è generico e si adatta a molte fonti di errore, dai trigger alle API esterne.

---

> 🧠 **“Un error log ben strutturato, con identificativo transazionale e contesto ricco, agevola debug e monitoraggio degli incidenti applicativi.”**
