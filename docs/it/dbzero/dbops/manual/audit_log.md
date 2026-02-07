## 📘 Documentazione Concettuale – Tabella `dbops.audit_log`

> 👀 **Vedi anche**
>
> Guide:
>     
> [Audit Logging](/guide/messagggi_audit)
>
> Approfondimento tabelle:   
> 
> * [dbops.error_log](/dbzero/dbops/tabelle/error_log)    
>
> Approfondimento funzioni:    
>
> * [dbops.trgfn_tx_id_managed](/dbzero/dbops/funzioni/trgfn_tx_id_managed)    

La tabella **`dbops.audit_log`** registra le esecuzioni di processi, funzioni e job, consentendo di tracciare chi ha eseguito cosa, quando e con quali parametri, nonché l’esito e la durata. Il campo **`tx_id`** non possiede più un valore di default: viene assegnato **automaticamente** dal **trigger**  utilizzando la trigger function `dbops.trgfn_tx_id_managed()`, garantendo coerenza con il modello di `error_log`.

---

### 🎯 Scopo Principale

(latest review 10-01-26)
* Monitorare e storicizzare ogni chiamata a funzioni, job e API interne.
* Fornire dettagli su utente, parametri e performance di esecuzione.
* Collegare gli eventi di audit agli errori e ad altri log tramite `tx_id` gestito dal trigger.

---

### 🔍 Significato dei Campi

| Campo           | Tipo                | Descrizione                                                                              |
| --------------- | ------------------- | ---------------------------------------------------------------------------------------- |
| `id`            | `bigint`            | Chiave primaria, sequenza automatica.                                                    |
| `function_name` | `text`              | Nome della funzione/method/app che è stata eseguita.                                     |
| `executed_by`   | `text`              | Utente o ruolo che ha avviato l’esecuzione (default `CURRENT_USER`).                     |
| `executed_at`   | `timestamp with tz` | Timestamp di inizio esecuzione (default `now()`).                                        |
| `params`        | `jsonb`             | Parametri in ingresso o contesto di esecuzione (JSONB).                                  |
| `status`        | `text`              | Esito dell’esecuzione (`SUCCESS`, `FAILED`, `WARNING`).                                  |
| `message`       | `text`              | Messaggio descrittivo dell’esito.                                                        |
| `duration_ms`   | `integer`           | Durata dell’esecuzione in millisecondi.                                                  |
| `tx_id`         | `uuid`              | Identificativo di transazione: valorizzato **dal trigger**  con `trgfn_tx_id_managed()`. |
| `cleanup_at`    | `timestamptz`        | Timestamp opzionale per la pulizia programmata dei log.                                  |

---

### 🔒 Vincoli e Comportamenti di Default

* **PK**: `pk_audit_log` su `id`.
* **Default** (solo se non assegnati da applicazione o trigger):

  * `executed_by` → `CURRENT_USER`
  * `executed_at` → `now()`
  * **`tx_id`** non ha default DDL: il valore è sempre gestito dal trigger **`trg_assign_tx_id_audit_log`**.

---

### ⚙️ Esempi di Utilizzo

1. **Inserimento manuale** (il trigger assegna `tx_id`):

   ```sql
   INSERT INTO dbops.audit_log(
     function_name, params, status, duration_ms
   ) VALUES (
     'process_invoices', '{"count":200}'::jsonb, 'SUCCESS', 1200
   );
   ```

2. **Recuperare audit di una transazione**:

   ```sql
   SELECT *
     FROM dbops.audit_log
    WHERE tx_id = '123e4567-e89b-12d3-a456-426614174000';
   ```

3. **Performance media per funzione**:

   ```sql
   SELECT function_name,
          AVG(duration_ms) AS avg_ms,
          COUNT(*)       AS executions
     FROM dbops.audit_log
    WHERE executed_at >= now() - INTERVAL '7 days'
    GROUP BY function_name
    ORDER BY avg_ms DESC;
   ```

---

### 💡 Vantaggi Operativi

* **Coerenza transazionale**: `tx_id` è sempre allineato al registro centrale e a `error_log`.
* **Centralizzazione**: nessuna logica di generazione/assegnazione duplicata in tabelle diverse.
* **Tracciabilità integrata**: un unico flusso di audit ed errori tramite `tx_id`.
* **Analisi semplificata**: i campi `params` e `duration_ms` permettono metriche e dashboard di performance.

---

> 🧠 **“Con la colonna `tx_id`, ogni record di audit è automaticamente correlato al contesto transazionale, semplificando debug, monitoraggio e analisi dei processi.”**

---

### 🧹 Pulizia programmata (`cleanup_at`)

Il campo **`cleanup_at`** è destinato a **job periodici di pulizia** dei log storici.  
Non rappresenta una scadenza funzionale dell’evento di audit.
