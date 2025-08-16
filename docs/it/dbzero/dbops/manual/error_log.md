## 📘 Documentazione Concettuale – Tabella `dbops.error_log`

> 👀 **Vedi anche**
>
> Approfondimento tabelle:    
>
> * [config.messaggi_errore](/dbzero/config/tabelle/messaggi_errore)    
> * [dbops.audit_log](/dbzero/dbops/tabelle/audit_log)    
>
> Approfondimento funzioni:    
> * [dbops.trgfn_tx_id_managed](/dbzero/dbops/funzioni/trgfn_tx_id_managed)    
> * [script.trgfn_prevent_modification_generic](/dbzero/script/funzioni/trgfn_prevent_modification_generic)    

La tabella **`dbops.error_log`** serve a **centralizzare la registrazione degli errori** che si verificano nelle diverse aree dell’applicazione (database, backend, frontend, job, ecc.), fornendo un quadro completo del contesto, della fonte e della transazione coinvolta.

---

### 🎯 Scopo Principale

* Raccogliere in un unico punto gli errori generati da funzioni, trigger o applicazioni, permettendo analisi e allineamento con il catalogo di messaggi di errore.
* Consentire il **collegamento transazionale** tramite `tx_id`, per ricostruire l’intero flusso di operazioni (ad esempio un job batch) incrociando tabelle come `dbops.audit_log`.

---

### 🔍 Significato dei Campi Chiave

* **`id`**: identificativo univoco del record di errore.
* **`occurred_at`**: timestamp con timezone dell’evento di errore.
* **`area`**: ambito di origine (es. `database`, `backend`, `frontend`, `job`).
* **`function_name`**: nome della funzione o metodo che ha generato l’errore (trigger, procedure, job, endpoint).
* **`messaggio_errore_id`**: FK verso `config.messaggi_errore(id)`, collega il record al testo di errore e alle eventuali traduzioni.
* **`context`**: campo JSONB in cui si registrano parametri di input, valori di variabili, utente esecutore o altri metadati rilevanti.
* **`tx_id`**: UUID di transazione corrente, utile per tracciare errori in contesti transazionali e correlare con altri log.

---

### 🔒 Vincoli e Relazioni

* **PK**: vincolo `error_log_pkey` su `id`.
* **FK**: `messaggio_errore_id` → `config.messaggi_errore(id)` (senza azioni di update o delete).
* **Generazione automatica**:

  * `occurred_at` default `now()`
  * `tx_id` 
  * `context` default a JSONB vuoto `{}`

---

### 🚨 Trigger

* **`trg_assign_tx_id_error_log`** (BEFORE INSERT OR UPDATE): assegna automaticamente il valore di `tx_id` tramite la trigger function `dbops.trgfn_tx_id_managed()`, garantendo che ogni record di errore sia correlato all’identificativo di transazione.
* **Protezione modifiche**: implementare, se necessario, trigger di tipo `script.trgfn_prevent_modification_generic()` per bloccare UPDATE/DELETE e preservare l’integrità storica.

---

### ⚙️ Esempi di Utilizzo

1. **Recuperare tutti gli errori di una specifica transazione**:

   ```sql
   SELECT *
     FROM dbops.error_log
    WHERE tx_id = '123e4567-e89b-12d3-a456-426614174000';
   ```

2. **Unire gli errori con il catalogo dei messaggi**:

   ```sql
   SELECT e.id, e.occurred_at, m.codice, m.messaggio, e.context
     FROM dbops.error_log e
     JOIN config.messaggi_errore m ON e.messaggio_errore_id = m.id;
   ```

3. **Cronologia completa di una transazione**:

   ```sql
   WITH errs AS (
     SELECT * FROM dbops.error_log WHERE tx_id = :tx
   ), audits AS (
     SELECT * FROM dbops.audit_log WHERE tx_id = :tx
   )
   SELECT * FROM errs
   UNION ALL
   SELECT * FROM audits
   ORDER BY occurred_at;
   ```

---

### 💡 Vantaggi Operativi

* **Tracciabilità a 360°**: unisce errori e transazioni in un unico flusso temporale.
* **Analisi rapida**: il campo `context` permette filtri e aggregazioni sui metadati.
* **Integrità delle informazioni**: i trigger automatici garantiscono corretto popolamento di `tx_id` e audit inalterabile.
* **Coerenza semantica**: l’uso di FK verso `config.messaggi_errore` assicura messaggi uniformi e localizzati.

---

> 🧠 **“Un error log strutturato con identità transazionale e contesto dettagliato semplifica il debug e il monitoraggio degli incidenti applicativi.”**
