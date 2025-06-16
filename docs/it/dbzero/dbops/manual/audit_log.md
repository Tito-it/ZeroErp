## 📘 Documentazione Concettuale – Tabella `dbops.audit_log`

> 👀 **Vedi anche**
>
> Approfondimento tabelle:    
> - [dbops.error_log](/dbzero/dbops/tabelle/error_log)    
> * Campo `tx_id` in `dbops.error_log` e suggerimenti di allineamento

La tabella **`dbops.audit_log`** registra le esecuzioni di processi, funzioni e job, consentendo di tracciare chi ha eseguito cosa, quando e con quali parametri, nonché l’esito e la durata. Il campo **`tx_id`**, definito come UUID generato casualmente, può essere ridefinito per allinearsi al modello di `error_log` (tramite `txid_current()`) se si desidera raggruppare audit e errori in un unico flusso transazionale.

---

### 🎯 Scopo Principale

* Monitorare e storicizzare ogni chiamata a funzioni, job e API interne.
* Fornire dettagli su utente, parametri e performance di esecuzione.
* Consentire il collegamento con `error_log` e altre tabelle transazionali tramite `tx_id`.

---

### 🔍 Significato dei Campi

* **`id`** (`bigint`): chiave primaria, sequenza automatica.
* **`function_name`** (`text`): nome della funzione/method/app che è stata eseguita (può essere generico).
* **`executed_by`** (`text`): utente o ruolo che ha avviato l’esecuzione, default `CURRENT_USER`.
* **`executed_at`** (`timestamp with time zone`): tempo con timezone di inizio esecuzione, default `now()`.
* **`params`** (`jsonb`): JSON con parametri in ingresso o contesto di esecuzione.
* **`status`** (`text`): esito dell’esecuzione, es. `SUCCESS`, `FAILED`, `WARNING`.
* **`message`** (`text`): eventuale messaggio di dettaglio o descrizione dell’esito.
* **`duration_ms`** (`integer`): durata dell’esecuzione in millisecondi.
* **`tx_id`** (`uuid`): identificativo di transazione, default `gen_random_uuid()`.
  *Consiglio*: per correlare audit e errori in un singolo flusso transazionale, è possibile ridefinire il default su `(md5(txid_current()::text))::uuid`, come in `error_log`.

---

### 🔒 Vincoli e Comportamenti di Default

* **PK**: `pk_audit_log (id)`.
* **Default**:

  * `executed_by` → `CURRENT_USER`
  * `executed_at` → `now()`
  * `tx_id` → `gen_random_uuid()` (modificabile per usare `txid_current()`)

---

### ⚙️ Esempi di Utilizzo

1. **Inserimento manuale di un audit**:

   ```sql
   INSERT INTO dbops.audit_log(
     function_name, params, status, duration_ms, tx_id
   ) VALUES (
     'process_orders', '{"order_count": 120}', 'SUCCESS', 3450, (md5(txid_current()::text))::uuid
   );
   ```

2. **Recuperare audit di una transazione specifica**:

   ```sql
   SELECT *
     FROM dbops.audit_log
    WHERE tx_id = '123e4567-e89b-12d3-a456-426614174000';
   ```

3. **Analisi delle performance per funzione**:

   ```sql
   SELECT function_name,
          AVG(duration_ms) AS avg_time_ms,
          COUNT(*)       AS executions
     FROM dbops.audit_log
    WHERE executed_at >= now() - INTERVAL '7 days'
    GROUP BY function_name
    ORDER BY avg_time_ms DESC;
   ```

---

### 💡 Vantaggi Operativi

* **Governance centralizzata**: tracciamento di tutte le esecuzioni in un’unica tabella.
* **Correlazione con errori**: uso coerente di `tx_id` permette di unire audit ed errori.
* **Analisi e monitoraggio**: parametri e durate consentono dashboard di performance.
* **Flessibilità**: `params` in JSONB memorizza contesti eterogenei senza schema fisso.

---

> 🧠 **“Un audit log ben progettato è essenziale per monitorare la salute del sistema, ottimizzare performance e garantire tracciabilità completa delle operazioni.”**
